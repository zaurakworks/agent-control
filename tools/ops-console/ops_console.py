#!/usr/bin/env python3
"""Publish a compact GitHub Issue card from the two operations report files."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence
from urllib.parse import quote


TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from report_formats import (  # noqa: E402
    MetricsView,
    ReportFormatError,
    WorkerView,
    load_metrics_view,
    load_worker_view,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = Path("tools/worker_snapshot/current.md")
METRICS_PATH = Path("tools/ops-metrics/current.md")
SNAPSHOT_VIEW_PATH = Path("tools/worker_snapshot/current.json")
METRICS_VIEW_PATH = Path("tools/ops-metrics/current.json")


class ConsoleError(RuntimeError):
    """Raised when the card cannot truthfully represent its inputs."""


@dataclass(frozen=True)
class ConsoleSnapshot:
    observed_at: datetime
    metrics_at: datetime
    running_count: int
    pending_count: int
    anomaly_count: int
    active_anomaly_count: int


def run_text(command: Sequence[str], *, cwd: Path = REPO_ROOT) -> str:
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", None) or str(error)
        raise ConsoleError(f"command failed: {' '.join(command)}: {detail.strip()}") from error
    return result.stdout


def parse_timestamp(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ConsoleError(f"invalid timestamp: {value}") from error
    if parsed.tzinfo is None:
        raise ConsoleError(f"timestamp has no timezone: {value}")
    return parsed.astimezone(timezone.utc)


def load_current_views(
    worker_path: Path, metrics_path: Path
) -> tuple[WorkerView, MetricsView]:
    try:
        return load_worker_view(worker_path), load_metrics_view(metrics_path)
    except ReportFormatError as error:
        raise ConsoleError(f"invalid structured operations view: {error}") from error


def load_project_items(path: Path | None, owner: str, number: int) -> dict[str, Any]:
    if path is not None:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ConsoleError(f"cannot read project items: {error}") from error
    output = run_text(
        [
            "gh",
            "project",
            "item-list",
            str(number),
            "--owner",
            owner,
            "--format",
            "json",
            "--limit",
            "1000",
        ]
    )
    try:
        return json.loads(output)
    except json.JSONDecodeError as error:
        raise ConsoleError("GitHub Project returned invalid JSON") from error


def count_pending_items(payload: dict[str, Any]) -> int:
    items = payload.get("items")
    if not isinstance(items, list):
        raise ConsoleError("GitHub Project payload has no items list")
    return sum(
        1
        for item in items
        if isinstance(item, dict) and item.get("status") in {"待决定", "验收中"}
    )


def resolve_source_commit(source_commit: str) -> str:
    sha = run_text(["git", "rev-parse", "--verify", f"{source_commit}^{{commit}}"])
    sha = sha.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        raise ConsoleError("git returned an invalid source commit")
    return sha


def verify_inputs_at_commit(sha: str, paths: Sequence[Path]) -> None:
    for relative_path in paths:
        local_path = REPO_ROOT / relative_path
        try:
            local_text = local_path.read_text(encoding="utf-8")
        except OSError as error:
            raise ConsoleError(f"cannot read {relative_path.as_posix()}: {error}") from error
        committed_text = run_text(
            ["git", "show", f"{sha}:{relative_path.as_posix()}"], cwd=REPO_ROOT
        )
        if local_text.splitlines() != committed_text.splitlines():
            raise ConsoleError(
                f"{relative_path.as_posix()} does not match source commit {sha[:12]}"
            )


def format_time(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def detail_url(repo: str, sha: str, path: Path) -> str:
    return f"https://github.com/{repo}/blob/{sha}/{quote(path.as_posix(), safe='/')}"


def _finish_card(lines: list[str]) -> str:
    if sum(1 for line in lines if line.strip()) > 10:
        raise ConsoleError("operations card exceeds the 10-line first-screen limit")
    return "\n".join(lines) + "\n"


def render_card(
    snapshot: ConsoleSnapshot,
    *,
    repo: str,
    sha: str,
    now: datetime,
    fresh_minutes: int,
) -> str:
    cutoff = min(snapshot.observed_at, snapshot.metrics_at)
    fresh_until = cutoff + timedelta(minutes=fresh_minutes)
    stale = now.astimezone(timezone.utc) > fresh_until
    if stale:
        status = "🔴 已失效：数据过期，需刷新"
        counts = (
            f"过期样本：工作的 Worker {snapshot.running_count} 个｜"
            f"曾等您决定 {snapshot.pending_count} 项｜"
            f"当天异常记录 {snapshot.anomaly_count} 项"
        )
    else:
        if snapshot.active_anomaly_count:
            status = "🔴 当前有异常"
        elif snapshot.pending_count:
            status = "🟡 有事项等您决定"
        else:
            status = "🟢 正常"
        counts = (
            f"正在工作的 Worker：{snapshot.running_count} 个｜"
            f"等您决定：{snapshot.pending_count} 项｜"
            f"今天异常记录：{snapshot.anomaly_count} 项"
            f"（当前仍有 {snapshot.active_anomaly_count} 项）"
        )

    highlights: list[str] = []
    if stale:
        highlights.append(f"这份数据已过 {fresh_minutes} 分钟有效期；请先刷新，再据此行动。")
    if snapshot.pending_count:
        highlights.append(
            f"有 {snapshot.pending_count} 项等您决定；请到 Project 或对应合同 Issue 查看并回复。"
        )
    if snapshot.anomaly_count:
        highlights.append(
            f"今天记录 {snapshot.anomaly_count} 项运行异常，其中 "
            f"{snapshot.active_anomaly_count} 项仍在发生；详情见下方明细。"
        )
    if not highlights:
        highlights.append("现在没有事项等您决定，也没有正在发生的异常。")
    highlights = highlights[:3]

    lines = [
        "# 运营台",
        (
            f"状态：{status}｜数据截至：{format_time(cutoff)}｜"
            f"新鲜至：{format_time(fresh_until)}（超时即视为已失效）"
        ),
        counts,
        "## 要事",
        *(f"- {item}" for item in highlights),
        (
            f"[Worker 明细]({detail_url(repo, sha, SNAPSHOT_PATH)})｜"
            f"[运营明细]({detail_url(repo, sha, METRICS_PATH)})｜精确提交 `{sha[:12]}`"
        ),
        "> 观察面非权威；吞吐≠价值；评论只用于高注意力事件。",
        "> 两周试行止损：负责人查找成本未下降、任一次陈旧误导行动，或单次维护成本持续超过 5 分钟。",
    ]
    return _finish_card(lines)


def render_unavailable(*, repo: str, sha: str | None) -> str:
    if sha is None:
        details = "Worker 明细：不可用｜运营明细：不可用｜精确提交：不可用"
    else:
        details = (
            f"[Worker 明细]({detail_url(repo, sha, SNAPSHOT_PATH)})｜"
            f"[运营明细]({detail_url(repo, sha, METRICS_PATH)})｜精确提交 `{sha[:12]}`"
        )
    lines = [
        "# 运营台",
        "状态：🔴 已失效：卡片生成失败｜数据截至：未观察到｜新鲜至：未观察到",
        "正在工作的 Worker：未观察到｜等您决定：未观察到｜今天异常记录：未观察到",
        "## 要事",
        "- 数据源未观察到；旧数据已停止显示，请手动重试后再行动。",
        "- 具体失败原因保留在调用端，避免把环境信息写入本卡片。",
        details,
        "> 观察面非权威；吞吐≠价值；评论只用于高注意力事件。",
        "> 两周试行止损：负责人查找成本未下降、任一次陈旧误导行动，或单次维护成本持续超过 5 分钟。",
    ]
    return _finish_card(lines)


def publish_issue_body(repo: str, issue: int, body: str) -> None:
    run_text(
        [
            "gh",
            "api",
            f"repos/{repo}/issues/{issue}",
            "--method",
            "PATCH",
            "-f",
            f"body={body}",
        ]
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="GitHub owner/repository")
    parser.add_argument("--issue", type=int, required=True, help="Operations-console Issue")
    parser.add_argument("--project-owner", help="Project owner; defaults to repository owner")
    parser.add_argument("--project-number", type=int, default=3)
    parser.add_argument("--project-items-file", type=Path, help="Offline Project JSON for tests")
    parser.add_argument("--source-commit", required=True, help="Commit containing both inputs")
    parser.add_argument("--fresh-minutes", type=int, default=15)
    parser.add_argument("--trigger", choices=("manual", "tick"), default="manual")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--now", help="RFC 3339 clock override for deterministic verification")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.fresh_minutes <= 0:
        raise ConsoleError("--fresh-minutes must be positive")
    if args.now and not args.dry_run:
        raise ConsoleError("--now is only allowed with --dry-run")
    if "/" not in args.repo:
        raise ConsoleError("--repo must be owner/repository")
    owner = args.project_owner or args.repo.split("/", 1)[0]
    paths = (SNAPSHOT_PATH, SNAPSHOT_VIEW_PATH, METRICS_PATH, METRICS_VIEW_PATH)
    sha: str | None = None
    failure: ConsoleError | None = None
    try:
        sha = resolve_source_commit(args.source_commit)
        verify_inputs_at_commit(sha, paths)
        worker_view, metrics_view = load_current_views(
            REPO_ROOT / SNAPSHOT_VIEW_PATH,
            REPO_ROOT / METRICS_VIEW_PATH,
        )
        project = load_project_items(args.project_items_file, owner, args.project_number)
        current = ConsoleSnapshot(
            observed_at=worker_view.observed_at,
            metrics_at=metrics_view.snapshot_at,
            running_count=worker_view.running_count,
            pending_count=count_pending_items(project),
            anomaly_count=(
                worker_view.active_anomaly_count + metrics_view.anomaly_count
            ),
            active_anomaly_count=worker_view.active_anomaly_count,
        )
        now = parse_timestamp(args.now) if args.now else datetime.now(timezone.utc)
        body = render_card(
            current,
            repo=args.repo,
            sha=sha,
            now=now,
            fresh_minutes=args.fresh_minutes,
        )
    except (ConsoleError, OSError) as error:
        failure = error if isinstance(error, ConsoleError) else ConsoleError(str(error))
        body = render_unavailable(repo=args.repo, sha=sha)

    if args.dry_run:
        sys.stdout.write(body)
    else:
        publish_issue_body(args.repo, args.issue, body)
        print(f"updated https://github.com/{args.repo}/issues/{args.issue} ({args.trigger})")
    if failure is not None:
        print(f"error: {failure}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ConsoleError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
