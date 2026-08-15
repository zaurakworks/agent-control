#!/usr/bin/env python3
"""Report one-shot deadline state for in-flight Orca Dispatches in one Run."""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Any, Protocol, Sequence


RUN_ID = re.compile(r"^run_[A-Za-z0-9]+$")
TASK_ID = re.compile(r"^task_[A-Za-z0-9]+$")
EXPECTED_DURATION = re.compile(
    r"^\s*Expected-Duration-Minutes\s*:\s*([^\s#]+)\s*(?:#.*)?$",
    re.IGNORECASE | re.MULTILINE,
)
IN_FLIGHT_DISPATCH_STATUSES = {"dispatched"}
SCHEMA_VERSION = 1


class DeadlineError(RuntimeError):
    """Raised when the Run cannot be queried without guessing."""


class OrcaReader(Protocol):
    def task_list(self, run_id: str) -> dict[str, Any]: ...

    def dispatch_show(self, task_id: str) -> dict[str, Any]: ...


def resolve_orca_command(override: str | None) -> list[str]:
    configured = override or os.environ.get("ORCA_CLI_COMMAND")
    if configured:
        command = shlex.split(configured)
        if not command:
            raise DeadlineError("configured Orca command is empty")
        return command
    if os.environ.get("ORCA_DEV_REPO_ROOT"):
        return ["orca-dev"]
    if sys.platform.startswith("linux") and os.environ.get("TERM_PROGRAM") != "Orca":
        return ["orca-ide"]
    return ["orca"]


class OrcaClient:
    """Minimal read-only wrapper around the version-matched Orca CLI."""

    def __init__(self, command: Sequence[str], timeout_seconds: float = 30.0) -> None:
        if not command:
            raise DeadlineError("Orca command cannot be empty")
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
            raise DeadlineError(f"Orca CLI not found: {self.command[0]}") from error
        except subprocess.TimeoutExpired as error:
            raise DeadlineError(
                f"Orca read timed out after {self.timeout_seconds:g}s: "
                f"{' '.join(arguments)}"
            ) from error

        output = (completed.stdout or completed.stderr).strip()
        try:
            payload = json.loads(output)
        except json.JSONDecodeError as error:
            detail = output[:240] or "no output"
            raise DeadlineError(
                f"Orca did not return JSON for {' '.join(arguments)}: {detail}"
            ) from error
        if completed.returncode or not payload.get("ok"):
            failure = payload.get("error", {})
            code = failure.get("code", f"exit_{completed.returncode}")
            message = failure.get("message", "unknown Orca error")
            raise DeadlineError(
                f"Orca {' '.join(arguments)} failed: {code}: {message}"
            )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise DeadlineError(f"Orca {' '.join(arguments)} returned no result object")
        return result

    def task_list(self, run_id: str) -> dict[str, Any]:
        return self._json(
            [
                "orchestration",
                "task-list",
                "--run",
                run_id,
                "--status",
                "dispatched",
            ]
        )

    def dispatch_show(self, task_id: str) -> dict[str, Any]:
        return self._json(
            ["orchestration", "dispatch-show", "--task", task_id]
        )


def parse_utc_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise DeadlineError("Dispatch has no start timestamp")
    normalized = value.strip().replace(" ", "T", 1)
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise DeadlineError(f"invalid Dispatch start timestamp: {value!r}") from error
    # Orca's current SQLite-shaped timestamps omit a suffix but are UTC.
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def expected_duration_minutes(spec: Any) -> tuple[int | None, str | None]:
    text = spec if isinstance(spec, str) else ""
    matches = EXPECTED_DURATION.findall(text)
    if not matches:
        return None, "expected_duration_missing"
    if len(matches) != 1:
        return None, "expected_duration_ambiguous"
    try:
        minutes = int(matches[0])
    except ValueError:
        return None, "expected_duration_invalid"
    if minutes <= 0:
        return None, "expected_duration_invalid"
    return minutes, None


def _title(task: dict[str, Any]) -> str:
    value = task.get("display_name") or task.get("task_title") or task.get("id")
    return " ".join(str(value or "unknown task").split())


def classify_dispatch(
    run_id: str,
    task: dict[str, Any],
    dispatch: dict[str, Any],
    observed_at: datetime,
) -> dict[str, Any]:
    task_id = str(task.get("id") or "")
    dispatch_id = str(dispatch.get("id") or "")
    if not TASK_ID.fullmatch(task_id):
        raise DeadlineError(f"task-list returned an invalid task id: {task_id!r}")
    if dispatch.get("task_id") != task_id:
        raise DeadlineError(f"dispatch-show returned a mismatched task for {task_id}")
    if dispatch.get("run_id") != run_id:
        raise DeadlineError(f"dispatch-show returned a mismatched Run for {task_id}")

    started_at = parse_utc_timestamp(dispatch.get("dispatched_at"))
    duration_minutes, duration_error = expected_duration_minutes(task.get("spec"))
    dispatch_status = str(dispatch.get("status") or "unknown")
    deadline_at: datetime | None = None
    overdue_seconds: int | None = None
    should_wake = False
    reason = duration_error

    if dispatch_status not in IN_FLIGHT_DISPATCH_STATUSES:
        reason = "dispatch_not_in_flight"
    elif duration_minutes is not None:
        deadline_at = started_at + timedelta(minutes=duration_minutes)
        overdue_seconds = max(0, int((observed_at - deadline_at).total_seconds()))
        should_wake = observed_at >= deadline_at
        reason = "deadline_reached" if should_wake else "before_deadline"

    return {
        "run_id": run_id,
        "task_id": task_id,
        "dispatch_id": dispatch_id,
        "title": _title(task),
        "dispatch_status": dispatch_status,
        "started_at": iso_utc(started_at),
        "expected_duration_minutes": duration_minutes,
        "deadline_at": iso_utc(deadline_at) if deadline_at else None,
        "overdue_seconds": overdue_seconds,
        "should_wake": should_wake,
        "reason": reason,
    }


def collect_deadlines(
    reader: OrcaReader,
    run_id: str,
    *,
    now: datetime | None = None,
    max_parallel: int = 8,
) -> dict[str, Any]:
    if not RUN_ID.fullmatch(run_id):
        raise DeadlineError(f"invalid Run id: {run_id!r}")
    if max_parallel < 1:
        raise DeadlineError("max_parallel must be positive")

    result = reader.task_list(run_id)
    returned_run_id = result.get("runId")
    if returned_run_id != run_id:
        raise DeadlineError(
            f"task-list returned Run {returned_run_id!r}, expected {run_id!r}"
        )
    tasks = result.get("tasks")
    if not isinstance(tasks, list):
        raise DeadlineError("task-list returned no task list")
    for task in tasks:
        if not isinstance(task, dict):
            raise DeadlineError("task-list returned a non-object task")
        if task.get("status") != "dispatched":
            raise DeadlineError("filtered task-list returned a non-dispatched task")

    observed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)

    def fetch(task: dict[str, Any]) -> dict[str, Any]:
        task_id = str(task.get("id") or "")
        dispatch_result = reader.dispatch_show(task_id)
        dispatch = dispatch_result.get("dispatch")
        if not isinstance(dispatch, dict):
            raise DeadlineError(f"dispatch-show returned no Dispatch for {task_id}")
        return classify_dispatch(run_id, task, dispatch, observed_at)

    worker_count = min(max_parallel, len(tasks) or 1)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        dispatches = list(executor.map(fetch, tasks))
    dispatches.sort(key=lambda row: (row["started_at"], row["task_id"]))

    return {
        "schema_version": SCHEMA_VERSION,
        "observed_at": iso_utc(observed_at),
        "run_id": run_id,
        "criterion": (
            "should_wake iff the current Dispatch status is dispatched, its task spec "
            "has exactly one positive Expected-Duration-Minutes value, and observed_at "
            "is at or after dispatched_at plus that duration"
        ),
        "summary": {
            "in_flight_dispatch_count": len(dispatches),
            "should_wake_count": sum(row["should_wake"] for row in dispatches),
            "missing_or_invalid_expectation_count": sum(
                str(row["reason"]).startswith("expected_duration_")
                for row in dispatches
            ),
        },
        "dispatches": dispatches,
        "commands": [
            f"orca orchestration task-list --run {run_id} --status dispatched --json",
            "orca orchestration dispatch-show --task <task_id> --json",
        ],
    }


def format_duration(seconds: int | None) -> str:
    if seconds is None:
        return "unknown"
    minutes, remainder = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if remainder or not parts:
        parts.append(f"{remainder}s")
    return "".join(parts)


def render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        f"Run: {report['run_id']}",
        f"Observed: {report['observed_at']}",
        (
            "Summary: "
            f"in_flight={summary['in_flight_dispatch_count']} "
            f"should_wake={summary['should_wake_count']} "
            f"missing_or_invalid={summary['missing_or_invalid_expectation_count']}"
        ),
    ]
    if not report["dispatches"]:
        lines.append("No in-flight Dispatches; no wake is needed.")
        return "\n".join(lines)

    for row in report["dispatches"]:
        expected = row["expected_duration_minutes"]
        expected_text = f"{expected}m" if expected is not None else "unknown"
        lines.extend(
            [
                "",
                f"{'WAKE' if row['should_wake'] else 'WAIT'} {row['task_id']} / {row['dispatch_id']}",
                f"  title: {row['title']}",
                f"  started_at: {row['started_at']}",
                f"  expected: {expected_text}",
                f"  deadline_at: {row['deadline_at'] or 'unknown'}",
                f"  overdue: {format_duration(row['overdue_seconds'])}",
                f"  reason: {row['reason']}",
            ]
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="exact Orca Run id")
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument(
        "--orca-command",
        help="override the Orca CLI command (normally auto-resolved)",
    )
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--max-parallel", type=int, default=8)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        client = OrcaClient(
            resolve_orca_command(args.orca_command),
            timeout_seconds=args.timeout_seconds,
        )
        report = collect_deadlines(
            client,
            args.run,
            max_parallel=args.max_parallel,
        )
    except DeadlineError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
