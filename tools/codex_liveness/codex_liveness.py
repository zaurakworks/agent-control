#!/usr/bin/env python3
"""Report Codex submission/start evidence for one Orca Dispatch."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence


STATUS_LABELS = {
    "not_submitted": "未提交",
    "submitted": "已提交",
    "started": "已开始",
}
STATUS_RANK = {"not_submitted": 0, "submitted": 1, "started": 2}
SCHEMA_RANK = {
    "response_item/message.user": 0,
    "event_msg/user_message": 1,
    "event_msg/item_completed.UserMessage": 2,
}
TASK_ID = re.compile(r"^task_[A-Za-z0-9]+$")
DISPATCH_ID = re.compile(r"^ctx_[A-Za-z0-9]+$")


@dataclass
class Observation:
    status_code: str
    task_id: str
    dispatch_id: str
    source_kind: str
    source_path: str | None = None
    session_id: str | None = None
    codex_version: str | None = None
    thread_id: str | None = None
    turn_id: str | None = None
    submitted_at: str | None = None
    started_at: str | None = None
    schema: str | None = None
    files_scanned: int = 0
    candidate_files: int = 0
    warnings: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        return STATUS_LABELS[self.status_code]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["status"] = self.status
        payload["observed_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        return payload


def validate_ids(task_id: str, dispatch_id: str) -> None:
    if not TASK_ID.fullmatch(task_id):
        raise ValueError(f"invalid task id: {task_id!r}")
    if not DISPATCH_ID.fullmatch(dispatch_id):
        raise ValueError(f"invalid dispatch id: {dispatch_id!r}")


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


def _contains_identifier(text: str, identifier: str) -> bool:
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(identifier)}(?![A-Za-z0-9_])"
    return re.search(pattern, text) is not None


def _matches_dispatch(value: Any, task_id: str, dispatch_id: str) -> bool:
    text = "\n".join(_strings(value))
    return _contains_identifier(text, task_id) and _contains_identifier(text, dispatch_id)


def _json_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    try:
        with path.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    warnings.append(
                        f"{path.name}:{line_number}: ignored malformed JSONL record ({error.msg})"
                    )
                    continue
                if not isinstance(row, dict):
                    warnings.append(f"{path.name}:{line_number}: ignored non-object JSONL record")
                    continue
                row["_line_number"] = line_number
                rows.append(row)
    except OSError as error:
        warnings.append(f"{path}: could not read JSONL ({error})")
    return rows, warnings


def inspect_rollout(path: Path, task_id: str, dispatch_id: str) -> Observation:
    """Inspect one persisted Codex rollout without printing conversation content."""

    validate_ids(task_id, dispatch_id)
    rows, warnings = _json_rows(path)
    session_id: str | None = None
    codex_version: str | None = None
    turn_starts: dict[str, str | None] = {}
    active_turn_id: str | None = None
    matches: list[Observation] = []

    for row in rows:
        row_type = row.get("type")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        timestamp = row.get("timestamp") if isinstance(row.get("timestamp"), str) else None

        if row_type == "session_meta":
            raw_session_id = payload.get("session_id") or payload.get("id")
            if isinstance(raw_session_id, str):
                session_id = raw_session_id
            if isinstance(payload.get("cli_version"), str):
                codex_version = payload["cli_version"]
            continue

        subtype = payload.get("type")
        if row_type == "event_msg" and subtype == "task_started":
            raw_turn_id = payload.get("turn_id")
            if isinstance(raw_turn_id, str):
                active_turn_id = raw_turn_id
                turn_starts[raw_turn_id] = timestamp or _milliseconds_timestamp(
                    payload.get("started_at")
                )
            continue

        if row_type == "event_msg" and subtype in {"task_complete", "turn_aborted"}:
            if payload.get("turn_id") == active_turn_id:
                active_turn_id = None
            continue

        matched = False
        matched_turn_id: str | None = None
        schema: str | None = None

        if row_type == "event_msg" and subtype == "item_completed":
            item = payload.get("item")
            if isinstance(item, dict) and item.get("type") == "UserMessage":
                matched = _matches_dispatch(item.get("content"), task_id, dispatch_id)
                if isinstance(payload.get("turn_id"), str):
                    matched_turn_id = payload["turn_id"]
                schema = "event_msg/item_completed.UserMessage"
        elif row_type == "event_msg" and subtype == "user_message":
            matched = _matches_dispatch(payload.get("message"), task_id, dispatch_id)
            matched_turn_id = active_turn_id
            schema = "event_msg/user_message"
        elif row_type == "response_item" and subtype == "message" and payload.get("role") == "user":
            matched = _matches_dispatch(payload.get("content"), task_id, dispatch_id)
            matched_turn_id = active_turn_id
            schema = "response_item/message.user"

        if not matched:
            continue

        started_at = turn_starts.get(matched_turn_id) if matched_turn_id else None
        status_code = "started" if matched_turn_id in turn_starts else "submitted"
        matches.append(
            Observation(
                status_code=status_code,
                task_id=task_id,
                dispatch_id=dispatch_id,
                source_kind="rollout_session",
                source_path=str(path),
                session_id=session_id,
                codex_version=codex_version,
                turn_id=matched_turn_id,
                submitted_at=timestamp,
                started_at=started_at,
                schema=schema,
                warnings=list(warnings),
            )
        )

    if not matches:
        return Observation(
            status_code="not_submitted",
            task_id=task_id,
            dispatch_id=dispatch_id,
            source_kind="rollout_session",
            source_path=str(path),
            session_id=session_id,
            codex_version=codex_version,
            warnings=warnings,
        )
    return max(matches, key=_observation_rank)


def _milliseconds_timestamp(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat().replace("+00:00", "Z")


def _observation_rank(observation: Observation) -> tuple[int, int, str]:
    return (
        STATUS_RANK[observation.status_code],
        SCHEMA_RANK.get(observation.schema or "", -1),
        observation.submitted_at or "",
    )


def default_sessions_root() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    return (Path(codex_home) if codex_home else Path.home() / ".codex") / "sessions"


def scan_sessions(
    task_id: str,
    dispatch_id: str,
    *,
    sessions_root: Path | None = None,
    session_paths: Sequence[Path] = (),
) -> Observation:
    """Find the strongest exact Dispatch evidence across persisted rollouts."""

    validate_ids(task_id, dispatch_id)
    warnings: list[str] = []
    if session_paths:
        paths = list(dict.fromkeys(path.resolve() for path in session_paths))
    else:
        root = (sessions_root or default_sessions_root()).resolve()
        if not root.is_dir():
            raise ValueError(f"Codex sessions root does not exist: {root}")
        paths = list(root.rglob("*.jsonl"))

    task_bytes = task_id.encode("utf-8")
    dispatch_bytes = dispatch_id.encode("utf-8")
    candidate_paths: list[Path] = []
    for path in paths:
        try:
            raw = path.read_bytes()
        except OSError as error:
            warnings.append(f"{path}: could not prefilter JSONL ({error})")
            continue
        if task_bytes in raw and dispatch_bytes in raw:
            candidate_paths.append(path)

    observations = [inspect_rollout(path, task_id, dispatch_id) for path in candidate_paths]
    matches = [item for item in observations if item.status_code != "not_submitted"]
    if matches:
        selected = max(matches, key=_observation_rank)
        selected.files_scanned = len(paths)
        selected.candidate_files = len(candidate_paths)
        selected.warnings = warnings + selected.warnings
        return selected

    for item in observations:
        warnings.extend(item.warnings)
    return Observation(
        status_code="not_submitted",
        task_id=task_id,
        dispatch_id=dispatch_id,
        source_kind="rollout_scan",
        files_scanned=len(paths),
        candidate_files=len(candidate_paths),
        warnings=warnings,
    )


def inspect_bound_events(path: Path, task_id: str, dispatch_id: str) -> Observation:
    """Inspect a dispatch-specific capture of ``codex exec --json`` stdout."""

    validate_ids(task_id, dispatch_id)
    rows, warnings = _json_rows(path)
    thread_id: str | None = None
    submitted_at: str | None = None
    started_at: str | None = None
    started_seen = False
    schema: str | None = None

    for row in rows:
        event_type = row.get("type")
        timestamp = row.get("timestamp") if isinstance(row.get("timestamp"), str) else None
        if event_type == "thread.started":
            if isinstance(row.get("thread_id"), str):
                thread_id = row["thread_id"]
            submitted_at = submitted_at or timestamp
            schema = "thread.started"
        elif event_type == "turn.started":
            started_seen = True
            started_at = started_at or timestamp
            schema = "thread.started+turn.started" if thread_id else "turn.started"
        elif event_type == "event_msg" and isinstance(row.get("payload"), dict):
            payload = row["payload"]
            if payload.get("type") == "task_started":
                started_seen = True
                started_at = started_at or timestamp or _milliseconds_timestamp(
                    payload.get("started_at")
                )
                schema = "event_msg/task_started"

    if started_seen:
        status_code = "started"
    elif thread_id is not None or submitted_at is not None:
        status_code = "submitted"
    else:
        status_code = "not_submitted"
    return Observation(
        status_code=status_code,
        task_id=task_id,
        dispatch_id=dispatch_id,
        source_kind="bound_exec_events",
        source_path=str(path),
        thread_id=thread_id,
        submitted_at=submitted_at,
        started_at=started_at,
        schema=schema,
        files_scanned=1,
        candidate_files=1,
        warnings=warnings,
    )


def build_exec_argv(
    *,
    executable: str = "codex",
    prompt: str = "-",
    ephemeral: bool = True,
    ignore_user_config: bool = True,
    ignore_rules: bool = True,
) -> list[str]:
    """Build the Codex 0.147-compatible read-only JSONL probe shape.

    Approval and sandbox are global flags and intentionally precede ``exec``;
    exec-only flags intentionally follow it.
    """

    argv = [executable, "-a", "never", "-s", "read-only", "exec"]
    if ephemeral:
        argv.append("--ephemeral")
    if ignore_user_config:
        argv.append("--ignore-user-config")
    if ignore_rules:
        argv.append("--ignore-rules")
    argv.extend(["--json", prompt])
    return argv


def _print_observation(observation: Observation, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(observation.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(observation.status)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    sessions = subparsers.add_parser(
        "sessions", help="scan persisted Codex rollout JSONL for an exact Dispatch"
    )
    sessions.add_argument("--task-id", required=True)
    sessions.add_argument("--dispatch-id", required=True)
    sessions.add_argument("--sessions-root", type=Path)
    sessions.add_argument("--session", type=Path, action="append", default=[])
    sessions.add_argument("--json", action="store_true")

    events = subparsers.add_parser(
        "events", help="inspect one explicitly dispatch-bound codex exec --json capture"
    )
    events.add_argument("--task-id", required=True)
    events.add_argument("--dispatch-id", required=True)
    events.add_argument("--input", type=Path, required=True)
    events.add_argument("--json", action="store_true")

    argv = subparsers.add_parser(
        "exec-argv", help="print the local-version-compatible read-only JSONL argv"
    )
    argv.add_argument("--codex", default="codex")
    argv.add_argument("--prompt", default="-")
    argv.add_argument("--persist", action="store_true")
    argv.add_argument("--load-user-config", action="store_true")
    argv.add_argument("--load-rules", action="store_true")
    argv.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "sessions":
            observation = scan_sessions(
                args.task_id,
                args.dispatch_id,
                sessions_root=args.sessions_root,
                session_paths=args.session,
            )
            _print_observation(observation, as_json=args.json)
        elif args.command == "events":
            observation = inspect_bound_events(args.input, args.task_id, args.dispatch_id)
            _print_observation(observation, as_json=args.json)
        else:
            command = build_exec_argv(
                executable=args.codex,
                prompt=args.prompt,
                ephemeral=not args.persist,
                ignore_user_config=not args.load_user_config,
                ignore_rules=not args.load_rules,
            )
            if args.json:
                print(json.dumps(command, ensure_ascii=False))
            else:
                print(subprocess.list2cmdline(command))
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
