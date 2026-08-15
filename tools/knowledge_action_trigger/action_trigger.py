"""Explicitly query a small set of current knowledge sources by action name.

The command has two modes:

* query mode accepts ``--action`` (the supported entry point) or explicit text
  and returns the relevant current knowledge route;
* ``--hook`` is a retained compatibility adapter.  It is not installed or
  adopted by this Agent system, and failures remain fail-open.

The router is deterministic.  It does not search historical material, modify
knowledge, grant permission, execute the proposed action, or trigger itself.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


TOOL_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = TOOL_ROOT.parents[1]
DEFAULT_ROUTES_PATH = TOOL_ROOT / "routes.json"
SUPPORTED_EVENTS = {"UserPromptSubmit", "PreToolUse"}
MAX_HOOK_INPUT_BYTES = 1024 * 1024


class TriggerError(ValueError):
    """The route catalog or manual invocation is invalid."""


@dataclass(frozen=True)
class Route:
    identifier: str
    events: frozenset[str]
    all_of: tuple[tuple[str, ...], ...]
    source: str
    checkpoint: str


@dataclass(frozen=True)
class Match:
    route: Route
    source_path: Path


def _require_non_empty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TriggerError(f"{field} must be a non-empty string")
    return value.strip()


def _load_route(raw: Any, index: int, repository_root: Path) -> Route:
    if not isinstance(raw, dict):
        raise TriggerError(f"routes[{index}] must be an object")
    identifier = _require_non_empty_string(raw.get("id"), f"routes[{index}].id")
    source = _require_non_empty_string(raw.get("source"), f"routes[{index}].source")
    checkpoint = _require_non_empty_string(
        raw.get("checkpoint"), f"routes[{index}].checkpoint"
    )

    events_raw = raw.get("events")
    if not isinstance(events_raw, list) or not events_raw:
        raise TriggerError(f"routes[{index}].events must be a non-empty array")
    events = frozenset(
        _require_non_empty_string(value, f"routes[{index}].events")
        for value in events_raw
    )
    unsupported = events - SUPPORTED_EVENTS
    if unsupported:
        raise TriggerError(
            f"routes[{index}].events contains unsupported values: {sorted(unsupported)}"
        )

    groups_raw = raw.get("allOf")
    if not isinstance(groups_raw, list) or not groups_raw:
        raise TriggerError(f"routes[{index}].allOf must be a non-empty array")
    groups: list[tuple[str, ...]] = []
    for group_index, group_raw in enumerate(groups_raw):
        if not isinstance(group_raw, list) or not group_raw:
            raise TriggerError(
                f"routes[{index}].allOf[{group_index}] must be a non-empty array"
            )
        groups.append(
            tuple(
                _require_non_empty_string(
                    alias, f"routes[{index}].allOf[{group_index}]"
                ).casefold()
                for alias in group_raw
            )
        )

    source_path = (repository_root / source).resolve()
    try:
        source_path.relative_to(repository_root.resolve())
    except ValueError as error:
        raise TriggerError(f"routes[{index}].source escapes the repository") from error
    if not source_path.is_file():
        raise TriggerError(f"routes[{index}].source does not exist: {source}")

    return Route(identifier, events, tuple(groups), source, checkpoint)


def load_routes(
    routes_path: Path = DEFAULT_ROUTES_PATH,
    repository_root: Path = REPOSITORY_ROOT,
) -> tuple[Route, ...]:
    try:
        catalog = json.loads(routes_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TriggerError(f"cannot read route catalog: {error}") from error
    if not isinstance(catalog, dict):
        raise TriggerError("route catalog root must be an object")
    if catalog.get("schema") != "agent-control.knowledge-action-routes":
        raise TriggerError("route catalog schema is unsupported")
    if catalog.get("version") != 1:
        raise TriggerError("route catalog version is unsupported")
    routes_raw = catalog.get("routes")
    if not isinstance(routes_raw, list) or not routes_raw:
        raise TriggerError("route catalog routes must be a non-empty array")
    routes = tuple(
        _load_route(raw, index, repository_root)
        for index, raw in enumerate(routes_raw)
    )
    identifiers = [route.identifier for route in routes]
    if len(set(identifiers)) != len(identifiers):
        raise TriggerError("route identifiers must be unique")
    return routes


# The historical public class name is retained for compatibility. Its supported
# Agent-system role is an explicitly invoked named-route query.
class KnowledgeActionTrigger:
    def __init__(
        self,
        routes: Sequence[Route],
        repository_root: Path = REPOSITORY_ROOT,
    ) -> None:
        self.routes = tuple(routes)
        self.repository_root = repository_root.resolve()

    def match_text(self, event: str, text: str) -> tuple[Match, ...]:
        normalized = text.casefold()
        return tuple(
            Match(route, (self.repository_root / route.source).resolve())
            for route in self.routes
            if event in route.events
            and all(any(alias in normalized for alias in group) for group in route.all_of)
        )

    def match_action(self, identifier: str) -> Match:
        for route in self.routes:
            if route.identifier == identifier:
                return Match(route, (self.repository_root / route.source).resolve())
        raise TriggerError(f"unknown action: {identifier}")

    @staticmethod
    def context(matches: Sequence[Match]) -> str:
        if not matches:
            return ""
        lines = ["Agent 系统知识按名问路查询结果："]
        for match in matches:
            lines.append(
                f"- {match.route.identifier}：{match.route.checkpoint}，当前知识源为 "
                f"{match.source_path}（仓内 {match.route.source}）。"
            )
        lines.append(
            "如需采用，请主动读取知识源并按其失效条件做最少复核；本查询结果不改变任务合同、权限或产品决定。"
        )
        return "\n".join(lines)


# Retained compatibility adapter only. 本系统不安装；原因是注入式投递已被
# 负责人否决（见 251-D1）。Do not present this code as an automatic trigger or
# Hook-mounting recommendation; the supported path is an explicit --action query.
def hook_text(payload: dict[str, Any]) -> tuple[str, str]:
    event = payload.get("hook_event_name")
    if event not in SUPPORTED_EVENTS:
        return "", ""
    if event == "UserPromptSubmit":
        prompt = payload.get("prompt")
        return event, prompt if isinstance(prompt, str) else ""
    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    pieces = [tool_name] if isinstance(tool_name, str) else []
    if isinstance(tool_input, (dict, list)):
        pieces.append(json.dumps(tool_input, ensure_ascii=False, sort_keys=True))
    elif isinstance(tool_input, str):
        pieces.append(tool_input)
    return event, " ".join(pieces)


def hook_response(payload: dict[str, Any], trigger: KnowledgeActionTrigger) -> dict[str, Any]:
    event, text = hook_text(payload)
    if not event or not text:
        return {}
    context = trigger.context(trigger.match_text(event, text))
    if not context:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": event,
            "additionalContext": context,
        }
    }


def read_hook_payload() -> dict[str, Any]:
    raw = sys.stdin.buffer.read(MAX_HOOK_INPUT_BYTES + 1)
    if len(raw) > MAX_HOOK_INPUT_BYTES:
        raise TriggerError("hook input exceeds 1 MiB")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise TriggerError(f"hook input is not UTF-8 JSON: {error}") from error
    if not isinstance(payload, dict):
        raise TriggerError("hook input root must be an object")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--hook",
        action="store_true",
        help="retained compatibility adapter; not installed or adopted",
    )
    mode.add_argument("--action", help="explicitly query one registered action id")
    mode.add_argument("--text", help="explicitly query with supplied text")
    mode.add_argument(
        "--text-file", type=Path, help="explicitly query UTF-8 text from a file"
    )
    parser.add_argument(
        "--event",
        choices=sorted(SUPPORTED_EVENTS),
        default="UserPromptSubmit",
        help="event used with --text or --text-file",
    )
    parser.add_argument("--json", action="store_true", help="emit manual results as JSON")
    parser.add_argument("--routes", type=Path, default=DEFAULT_ROUTES_PATH)
    return parser


def manual_result(matches: Sequence[Match], trigger: KnowledgeActionTrigger) -> dict[str, Any]:
    return {
        "matched": bool(matches),
        "routes": [
            {
                "id": match.route.identifier,
                "source": match.route.source,
                "sourcePath": str(match.source_path),
                "checkpoint": match.route.checkpoint,
            }
            for match in matches
        ],
        "additionalContext": trigger.context(matches),
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.hook:
        try:
            trigger = KnowledgeActionTrigger(load_routes(args.routes))
            response = hook_response(read_hook_payload(), trigger)
        except TriggerError:
            response = {}
        print(json.dumps(response, ensure_ascii=False, separators=(",", ":")))
        return 0

    try:
        trigger = KnowledgeActionTrigger(load_routes(args.routes))
        if args.action:
            matches = (trigger.match_action(args.action),)
        else:
            if args.text_file is not None:
                try:
                    text = args.text_file.read_text(encoding="utf-8")
                except OSError as error:
                    raise TriggerError(f"cannot read text file: {error}") from error
            else:
                text = args.text or ""
            matches = trigger.match_text(args.event, text)
        result = manual_result(matches, trigger)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["additionalContext"])
        return 0
    except TriggerError as error:
        print(f"knowledge-action-trigger: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
