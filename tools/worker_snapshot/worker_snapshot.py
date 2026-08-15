#!/usr/bin/env python3
"""Render a point-in-time, read-only view of active Orca workers."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, Sequence


TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from report_formats import (  # noqa: E402
    WorkerView,
    parse_view_timestamp,
    write_current,
)


ISSUE_PATTERNS = (
    re.compile(r"合同\s*=\s*(?:[\w.-]+/)?[\w.-]+#(\d+)", re.IGNORECASE),
    re.compile(r"关联\s+(?:[\w.-]+/)?[\w.-]+#(\d+)", re.IGNORECASE),
    re.compile(r"(?:[\w.-]+/)?[\w.-]+#(\d+)", re.IGNORECASE),
    re.compile(r"(?<![\w/])#(\d+)"),
)


class SnapshotError(RuntimeError):
    """Raised when a complete snapshot cannot be collected safely."""


class OrcaReader(Protocol):
    def root(self, arguments: Sequence[str]) -> dict[str, Any]: ...

    def orchestration(self, arguments: Sequence[str]) -> dict[str, Any]: ...


class OrcaClient:
    """Small read-only wrapper around the version-matched Orca CLI."""

    def __init__(self, command: Sequence[str], timeout_seconds: float) -> None:
        if not command:
            raise SnapshotError("Orca command cannot be empty")
        self.command = list(command)
        self.timeout_seconds = timeout_seconds

    def _json(self, arguments: Sequence[str]) -> dict[str, Any]:
        command = [*self.command, *arguments, "--json"]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as error:
            raise SnapshotError(f"Orca CLI not found: {self.command[0]}") from error
        except subprocess.TimeoutExpired as error:
            raise SnapshotError(
                f"Orca read timed out after {self.timeout_seconds:g}s: {' '.join(arguments)}"
            ) from error
        output = (completed.stdout or completed.stderr).strip()
        try:
            payload = json.loads(output)
        except json.JSONDecodeError as error:
            detail = output[:240] or "no output"
            raise SnapshotError(
                f"Orca did not return JSON for {' '.join(arguments)}: {detail}"
            ) from error
        if completed.returncode or not payload.get("ok"):
            failure = payload.get("error", {})
            code = failure.get("code", f"exit_{completed.returncode}")
            message = failure.get("message", "unknown Orca error")
            raise SnapshotError(f"Orca {' '.join(arguments)} failed: {code}: {message}")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise SnapshotError(f"Orca {' '.join(arguments)} returned no result object")
        result["_runtime_id"] = payload.get("_meta", {}).get("runtimeId")
        return result

    def root(self, arguments: Sequence[str]) -> dict[str, Any]:
        return self._json(arguments)

    def orchestration(self, arguments: Sequence[str]) -> dict[str, Any]:
        return self._json(["orchestration", *arguments])


def resolve_orca_command(override: str | None) -> list[str]:
    configured = override or os.environ.get("ORCA_CLI_COMMAND")
    if configured:
        command = shlex.split(configured)
        if not command:
            raise SnapshotError("configured Orca command is empty")
        return command
    if os.environ.get("ORCA_DEV_REPO_ROOT"):
        return ["orca-dev"]
    if sys.platform.startswith("linux") and os.environ.get("TERM_PROGRAM") != "Orca":
        return ["orca-ide"]
    return ["orca"]


def extract_issue_number(task: dict[str, Any]) -> int | None:
    text = "\n".join(
        str(task.get(field) or "") for field in ("spec", "task_title", "display_name")
    )
    for pattern in ISSUE_PATTERNS:
        match = pattern.search(text)
        if match:
            return int(match.group(1))
    return None


def short_task_title(task: dict[str, Any], issue_number: int | None) -> str:
    title = str(task.get("task_title") or task.get("display_name") or task.get("id") or "任务")
    title = " ".join(title.split())
    if issue_number is not None:
        title = re.sub(
            rf"^[A-Za-z]*{issue_number}\s*(?:[|:：-]\s*)?",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip()
    return title[:72] + ("…" if len(title) > 72 else "")


def normalize_orca_timestamp(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace(" ", "T", 1)
    if not re.search(r"(?:Z|[+-]\d\d:\d\d)$", normalized):
        normalized += "Z"
    return normalized


def _run_task_list(
    reader: OrcaReader, run_id: str
) -> tuple[str, list[dict[str, Any]]]:
    result = reader.orchestration(["task-list", "--run", run_id])
    tasks = result.get("tasks", [])
    if not isinstance(tasks, list):
        raise SnapshotError(f"Orca task-list returned an invalid task list for {run_id}")
    return run_id, tasks


def _active_worker(
    reader: OrcaReader, run_id: str, task: dict[str, Any]
) -> tuple[dict[str, Any], str | None]:
    dispatch_id = task.get("dispatch_id")
    if not dispatch_id:
        dispatch_result = reader.orchestration(["dispatch-show", "--task", str(task["id"])])
        dispatch = dispatch_result.get("dispatch") or {}
        dispatch_id = dispatch.get("id")
    if not dispatch_id:
        row = {
            "run_id": run_id,
            "task_id": task.get("id"),
            "dispatch_address": None,
            "issue_number": extract_issue_number(task),
            "task_title": short_task_title(task, extract_issue_number(task)),
            "started_at": None,
            "task_status": task.get("status"),
            "worker_state": "unavailable",
            "worker_stage": None,
            "terminal_status": "unavailable",
            "terminal_connected": None,
            "terminal_orphaned": None,
        }
        return row, f"{task.get('id')}: dispatched task has no current Dispatch"

    try:
        result = reader.orchestration(["worker-show", "--dispatch", str(dispatch_id)])
    except SnapshotError as error:
        issue_number = extract_issue_number(task)
        row = {
            "run_id": run_id,
            "task_id": task.get("id"),
            "dispatch_address": f"dispatch:{dispatch_id}",
            "issue_number": issue_number,
            "task_title": short_task_title(task, issue_number),
            "started_at": None,
            "task_status": task.get("status"),
            "worker_state": "unavailable",
            "worker_stage": None,
            "terminal_status": "unavailable",
            "terminal_connected": None,
            "terminal_orphaned": None,
        }
        return row, f"{task.get('id')}/{dispatch_id}: {error}"

    dispatch = result.get("dispatch") or {}
    worker = result.get("worker") or {}
    terminal = result.get("terminal") or {}
    observation = result.get("observation") or {}
    issue_number = extract_issue_number(task)
    row = {
        "run_id": run_id,
        "task_id": task.get("id"),
        "dispatch_address": f"dispatch:{dispatch_id}",
        "issue_number": issue_number,
        "task_title": short_task_title(task, issue_number),
        "started_at": normalize_orca_timestamp(dispatch.get("dispatched_at")),
        "task_status": task.get("status"),
        "worker_state": worker.get("state") or "unknown",
        "worker_stage": worker.get("stage"),
        "terminal_status": observation.get("status") or "unknown",
        "terminal_connected": terminal.get("connected"),
        "terminal_orphaned": terminal.get("orphaned"),
    }
    return row, None


def count_current_worker_anomalies(
    worker_rows: Sequence[dict[str, Any]],
    warnings: Sequence[str],
    *,
    running_count: int,
    dispatched_count: int,
) -> int:
    anomalous_rows = sum(
        1
        for row in worker_rows
        if str(row.get("terminal_status") or "").lower() != "running"
        or str(row.get("worker_state") or "").lower() in {"failed", "unavailable"}
    )
    non_running_rows = max(dispatched_count - running_count, 0)
    return max(anomalous_rows, non_running_rows, len(warnings))


def collect_snapshot(
    reader: OrcaReader,
    requested_run_ids: Sequence[str] | None = None,
    *,
    now: datetime | None = None,
    max_parallel: int = 8,
) -> dict[str, Any]:
    status = reader.root(["status"])
    runtime = status.get("runtime") or {}
    if runtime.get("state") != "ready" or not runtime.get("reachable"):
        raise SnapshotError("Orca runtime is not ready and reachable")

    run_result = reader.orchestration(["run-list"])
    if run_result.get("nextCursor"):
        raise SnapshotError("Orca run-list is paginated; refusing an incomplete snapshot")
    runs = run_result.get("runs", [])
    if not isinstance(runs, list):
        raise SnapshotError("Orca run-list returned an invalid run list")
    ordinary_runs = [run for run in runs if not run.get("legacy")]
    run_by_id = {str(run["id"]): run for run in ordinary_runs}
    if requested_run_ids:
        unique_run_ids = list(dict.fromkeys(requested_run_ids))
        missing = sorted(set(unique_run_ids) - set(run_by_id))
        if missing:
            raise SnapshotError(f"Orca Run not found: {', '.join(missing)}")
        selected_runs = [run_by_id[run_id] for run_id in unique_run_ids]
    else:
        selected_runs = ordinary_runs

    workers = min(max_parallel, len(selected_runs) or 1)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        task_results = list(
            executor.map(
                lambda run: _run_task_list(reader, str(run["id"])),
                selected_runs,
            )
        )
    active_tasks = [
        (run_id, task)
        for run_id, tasks in task_results
        for task in tasks
        if task.get("status") == "dispatched"
    ]

    worker_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    workers = min(max_parallel, len(active_tasks) or 1)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(
            executor.map(
                lambda item: _active_worker(reader, item[0], item[1]),
                active_tasks,
            )
        )
    for row, warning in results:
        worker_rows.append(row)
        if warning:
            warnings.append(warning)
    worker_rows.sort(key=lambda row: (row.get("started_at") or "", row.get("task_id") or ""))

    observation_counts = Counter(row["terminal_status"] for row in worker_rows)
    running_count = observation_counts.get("running", 0)
    dispatched_count = len(active_tasks)
    active_anomaly_count = count_current_worker_anomalies(
        worker_rows,
        warnings,
        running_count=running_count,
        dispatched_count=dispatched_count,
    )
    observed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return {
        "schema_version": 1,
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
        "source": "orca orchestration read-only point-in-time snapshot",
        "runtime": {
            "id": runtime.get("runtimeId") or status.get("_runtime_id"),
            "version": runtime.get("appVersion"),
        },
        "scope": {
            "run_ids": [str(run["id"]) for run in selected_runs],
            "run_count": len(selected_runs),
        },
        "summary": {
            "running_worker_count": running_count,
            "dispatched_task_count": dispatched_count,
            "active_anomaly_count": active_anomaly_count,
            "terminal_states": dict(sorted(observation_counts.items())),
        },
        "workers": worker_rows,
        "warnings": warnings,
    }


def _plain(value: Any) -> str:
    text = " ".join(str(value or "—").replace("|", "/").split())
    text = text.replace("\\", "\\\\")
    for token in ("`", "*", "_", "[", "]"):
        text = text.replace(token, f"\\{token}")
    return text.replace("<", "&lt;").replace(">", "&gt;")


def render_markdown(snapshot: dict[str, Any]) -> str:
    summary = snapshot["summary"]
    scope = snapshot["scope"]
    states = "、".join(
        f"{state} {count}" for state, count in summary["terminal_states"].items()
    ) or "无"
    lines = [
        "# Worker 观察面",
        "",
        (
            f"> 观察时刻：{snapshot['observed_at']}｜来源：`orca orchestration` 只读瞬时快照"
            f"｜范围：{scope['run_count']} 个 Run"
        ),
        "> 这是一次性观察证据，不是持久任务合同；刷新时重新运行工具。",
        "",
        "## 摘要",
        "",
        f"- 在跑 worker：**{summary['running_worker_count']}**",
        f"- `dispatched` 任务：**{summary['dispatched_task_count']}**",
        f"- 终端观察态：{states}",
        "",
        "## 当前席位",
        "",
    ]
    if not snapshot["workers"]:
        lines.append("当前没有 `dispatched` Worker。")
    for index, worker in enumerate(snapshot["workers"], start=1):
        issue_number = worker.get("issue_number")
        title = _plain(worker.get("task_title"))
        task_label = (
            f"关联 #{issue_number}（{title}）" if issue_number is not None else f"任务：{title}"
        )
        connectivity = (
            "connected"
            if worker.get("terminal_connected") is True
            else "disconnected"
            if worker.get("terminal_connected") is False
            else "connectivity unknown"
        )
        if worker.get("terminal_orphaned"):
            connectivity += " / orphaned"
        state = _plain(worker.get("terminal_status"))
        worker_state = _plain(worker.get("worker_state"))
        stage = _plain(worker.get("worker_stage"))
        lines.append(
            f"{index}. {task_label}｜开始 {worker.get('started_at') or '未知'}｜"
            f"终端 {state} / {connectivity}｜Worker {worker_state} / {stage}｜"
            f"`{_plain(worker.get('dispatch_address'))}`"
        )
    if snapshot["warnings"]:
        lines.extend(["", "## 采集缺口", ""])
        lines.extend(f"- {_plain(warning)}" for warning in snapshot["warnings"])
    lines.extend(
        [
            "",
            "## 口径",
            "",
            "- “在跑”只计 `worker-show.observation.status=running`；`dispatched` 数另列，避免把失联或不可读终端冒充在跑。",
            "- 每席只展示 Task、Dispatch、开始时刻和状态；不读取终端正文，也不把易失终端句柄写入持久文本。",
            "- Orca 返回的无时区 `dispatched_at` 按 UTC 标为 `Z`；快照不推断旧时刻状态。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render a read-only, point-in-time view of active Orca workers."
    )
    parser.add_argument(
        "--run",
        action="append",
        dest="run_ids",
        help="Limit the snapshot to one Orca Run ID; repeatable. Default: all ordinary Runs.",
    )
    parser.add_argument(
        "--format", choices=("markdown", "json"), default="markdown", help="Output format."
    )
    parser.add_argument("--output", type=Path, help="Write to this file instead of stdout.")
    parser.add_argument(
        "--current-json",
        type=Path,
        help="Also write the small, versioned JSON view consumed by ops-console.",
    )
    parser.add_argument(
        "--orca-command",
        help="Orca executable command. Defaults to ORCA_CLI_COMMAND or the platform guide.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    parser.add_argument("--max-parallel", type=int, default=8)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.timeout_seconds <= 0:
        raise SnapshotError("--timeout-seconds must be positive")
    if args.max_parallel <= 0:
        raise SnapshotError("--max-parallel must be positive")
    client = OrcaClient(resolve_orca_command(args.orca_command), args.timeout_seconds)
    snapshot = collect_snapshot(client, args.run_ids, max_parallel=args.max_parallel)
    output = (
        json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n"
        if args.format == "json"
        else render_markdown(snapshot)
    )
    written: list[Path] = []
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        written.append(args.output)
    else:
        sys.stdout.write(output)
    if args.current_json:
        summary = snapshot["summary"]
        write_current(
            args.current_json,
            WorkerView(
                observed_at=parse_view_timestamp(snapshot["observed_at"], "observed_at"),
                running_count=summary["running_worker_count"],
                dispatched_count=summary["dispatched_task_count"],
                active_anomaly_count=summary["active_anomaly_count"],
            ),
        )
        written.append(args.current_json)
    if written:
        print("wrote " + ", ".join(str(path) for path in written))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SnapshotError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
