#!/usr/bin/env python3
"""Classify one Orca Dispatch and ignite a confirmed pending composer at most once."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Protocol, Sequence


TASK_ID = re.compile(r"^task_[A-Za-z0-9]+$")
DISPATCH_ID = re.compile(r"^ctx_[A-Za-z0-9]+$")
TERMINAL_ID = re.compile(r"^term_[A-Za-z0-9-]+$")
ACTIVE_TITLE = re.compile(
    r"\b(?:thinking|working|executing|generating|processing)\b|思考|处理中",
    re.IGNORECASE,
)
POST_SUBMISSION_ACTIVITY = re.compile(
    r"esc to interrupt|ctrl\s*\+\s*c to interrupt|"
    r"(?:^|\n)\s*[•✻✽⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]",
    re.IGNORECASE,
)
COMPOSER_FOOTER = re.compile(
    r"\bContext\s+\d+%\s+left\b|"
    r"\bCtx\s*/\s*In\s*/\s*Out\b|"
    r"\?\s*for\s+shortcuts|"
    r"bypass\s+permissions|"
    r"shift\s*\+\s*tab\s+to\s+cycle",
    re.IGNORECASE,
)
FINAL_DISPATCH_STATUSES = {"completed"}
IGNITABLE_DISPATCH_STATUSES = {"dispatched"}
SCHEMA_VERSION = 2
ISSUE_31_SAMPLE_SCHEMA_VERSION = 1


class LivenessError(RuntimeError):
    """Raised when the exact target cannot be observed or mutated safely."""


class OrcaAccess(Protocol):
    def dispatch_show(self, task_id: str) -> dict[str, Any]: ...

    def worker_read(self, dispatch_id: str) -> dict[str, Any]: ...

    def worker_show(self, dispatch_id: str) -> dict[str, Any]: ...

    def status(self) -> dict[str, Any]: ...

    def terminal_read(self, terminal: str) -> dict[str, Any]: ...

    def terminal_show(self, terminal: str) -> dict[str, Any]: ...

    def send_enter(self, terminal: str) -> dict[str, Any]: ...


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def validate_identity(task_id: str, dispatch_id: str, terminal: str) -> None:
    if not TASK_ID.fullmatch(task_id):
        raise LivenessError(f"invalid task id: {task_id!r}")
    if not DISPATCH_ID.fullmatch(dispatch_id):
        raise LivenessError(f"invalid dispatch id: {dispatch_id!r}")
    if not TERMINAL_ID.fullmatch(terminal):
        raise LivenessError(f"invalid terminal handle: {terminal!r}")


def resolve_orca_command(override: str | None) -> list[str]:
    configured = override or os.environ.get("ORCA_CLI_COMMAND")
    if configured:
        command = shlex.split(configured)
        if not command:
            raise LivenessError("configured Orca command is empty")
        return command
    if os.environ.get("ORCA_DEV_REPO_ROOT"):
        return ["orca-dev"]
    if sys.platform.startswith("linux") and os.environ.get("TERM_PROGRAM") != "Orca":
        return ["orca-ide"]
    return ["orca"]


class OrcaClient:
    """Narrow wrapper over the version-matched Orca CLI."""

    def __init__(self, command: Sequence[str], timeout_seconds: float = 30.0) -> None:
        if not command:
            raise LivenessError("Orca command cannot be empty")
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
            raise LivenessError(f"Orca CLI not found: {self.command[0]}") from error
        except subprocess.TimeoutExpired as error:
            raise LivenessError(
                f"Orca command timed out after {self.timeout_seconds:g}s: "
                f"{' '.join(arguments)}"
            ) from error

        output = (completed.stdout or completed.stderr).strip()
        try:
            payload = json.loads(output)
        except json.JSONDecodeError as error:
            detail = output[:240] or "no output"
            raise LivenessError(
                f"Orca did not return JSON for {' '.join(arguments)}: {detail}"
            ) from error
        if completed.returncode or not payload.get("ok"):
            failure = payload.get("error", {})
            code = failure.get("code", f"exit_{completed.returncode}")
            message = failure.get("message", "unknown Orca error")
            raise LivenessError(
                f"Orca {' '.join(arguments)} failed: {code}: {message}"
            )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise LivenessError(f"Orca {' '.join(arguments)} returned no result object")
        result["_runtime_id"] = payload.get("_meta", {}).get("runtimeId")
        return result

    def dispatch_show(self, task_id: str) -> dict[str, Any]:
        return self._json(["orchestration", "dispatch-show", "--task", task_id])

    def worker_read(self, dispatch_id: str) -> dict[str, Any]:
        return self._json(
            ["orchestration", "worker-read", "--dispatch", dispatch_id, "--limit", "200"]
        )

    def worker_show(self, dispatch_id: str) -> dict[str, Any]:
        return self._json(["orchestration", "worker-show", "--dispatch", dispatch_id])

    def status(self) -> dict[str, Any]:
        return self._json(["status"])

    def terminal_read(self, terminal: str) -> dict[str, Any]:
        return self._json(["terminal", "read", "--terminal", terminal, "--limit", "1000"])

    def terminal_show(self, terminal: str) -> dict[str, Any]:
        return self._json(["terminal", "show", "--terminal", terminal])

    def send_enter(self, terminal: str) -> dict[str, Any]:
        return self._json(
            ["terminal", "send", "--terminal", terminal, "--text", "", "--enter"]
        )


def _dispatch_payload(result: dict[str, Any]) -> dict[str, Any]:
    dispatch = result.get("dispatch")
    if not isinstance(dispatch, dict):
        raise LivenessError("dispatch-show returned no Dispatch")
    return dispatch


def _terminal_payload(result: dict[str, Any]) -> dict[str, Any]:
    terminal = result.get("terminal")
    if not isinstance(terminal, dict):
        raise LivenessError("terminal command returned no terminal")
    return terminal


def assert_exact_target(
    client: OrcaAccess,
    task_id: str,
    dispatch_id: str,
    terminal: str,
    *,
    require_writable: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    dispatch = _dispatch_payload(client.dispatch_show(task_id))
    if dispatch.get("id") != dispatch_id:
        raise LivenessError(
            f"task {task_id} current Dispatch is {dispatch.get('id')!r}, not {dispatch_id!r}"
        )
    if dispatch.get("task_id") != task_id:
        raise LivenessError("dispatch-show returned a mismatched task identity")
    if dispatch.get("assignee_handle") != terminal:
        raise LivenessError(
            f"Dispatch {dispatch_id} is assigned to {dispatch.get('assignee_handle')!r}, "
            f"not {terminal!r}"
        )

    terminal_payload = _terminal_payload(client.terminal_show(terminal))
    if terminal_payload.get("handle") != terminal:
        raise LivenessError("terminal-show returned a mismatched terminal identity")
    if require_writable:
        if not terminal_payload.get("connected") or not terminal_payload.get("writable"):
            raise LivenessError(
                f"terminal {terminal} is not both connected and writable; refusing Enter"
            )
    return dispatch, terminal_payload


def _contains_exact_ids(value: Any, task_id: str, dispatch_id: str) -> bool:
    if isinstance(value, str):
        return task_id in value and dispatch_id in value
    if isinstance(value, list):
        return any(_contains_exact_ids(item, task_id, dispatch_id) for item in value)
    if isinstance(value, dict):
        return any(_contains_exact_ids(item, task_id, dispatch_id) for item in value.values())
    return False


def transcript_submission_evidence(
    client: OrcaAccess, task_id: str, dispatch_id: str
) -> tuple[str, bool]:
    """Return exact user-message evidence without treating terminal text as a transcript."""

    reader = getattr(client, "worker_read", None)
    if reader is None:
        return "unavailable", False
    try:
        result = reader(dispatch_id)
    except LivenessError:
        return "unavailable", False
    source = result.get("source")
    if source != "transcript":
        return str(source or "unavailable"), False
    transcript = result.get("transcript")
    messages = transcript.get("messages") if isinstance(transcript, dict) else None
    if not isinstance(messages, list):
        return "transcript-invalid", False
    submitted = any(
        isinstance(message, dict)
        and message.get("role") == "user"
        and _contains_exact_ids(message, task_id, dispatch_id)
        for message in messages
    )
    return "transcript", submitted


def terminal_composer_evidence(
    lines: Sequence[str], task_id: str, dispatch_id: str
) -> bool:
    """Require markers in the live input footer; marker presence alone is ambiguous."""

    marker_lines = [
        index
        for index, line in enumerate(lines)
        if task_id in line or dispatch_id in line
    ]
    if not marker_lines:
        return False
    first_marker = min(marker_lines)
    last_marker = max(marker_lines)
    marker_window = "\n".join(lines[first_marker : min(len(lines), last_marker + 4)])
    both_ids_are_local = task_id in marker_window and dispatch_id in marker_window
    near_viewport_end = len(lines) - last_marker <= 4
    return both_ids_are_local and near_viewport_end and bool(
        COMPOSER_FOOTER.search(marker_window)
    )


@dataclass
class Observation:
    event: str
    scheduled_after_seconds: float
    observed_at: str
    state: str
    dispatch_status: str | None
    terminal_status: str | None
    terminal_connected: bool
    terminal_writable: bool
    terminal_title_active: bool
    task_marker_present: bool
    dispatch_marker_present: bool
    transcript_source: str
    transcript_user_message_present: bool
    composer_evidence: bool
    post_submission_activity: bool
    runtime_id: str | None


def observe(
    client: OrcaAccess,
    task_id: str,
    dispatch_id: str,
    terminal: str,
    *,
    event: str,
    scheduled_after_seconds: float,
) -> Observation:
    dispatch_result = client.dispatch_show(task_id)
    dispatch = _dispatch_payload(dispatch_result)
    if dispatch.get("id") != dispatch_id or dispatch.get("assignee_handle") != terminal:
        raise LivenessError("Dispatch identity changed during the observation window")

    read_result = client.terminal_read(terminal)
    read_terminal = _terminal_payload(read_result)
    show_result = client.terminal_show(terminal)
    shown_terminal = _terminal_payload(show_result)
    if read_terminal.get("handle") != terminal or shown_terminal.get("handle") != terminal:
        raise LivenessError("terminal identity changed during the observation window")

    tail = read_terminal.get("tail", [])
    if not isinstance(tail, list) or not all(isinstance(line, str) for line in tail):
        raise LivenessError("terminal-read returned an invalid tail")
    text = "\n".join(tail)
    task_position = text.rfind(task_id)
    dispatch_position = text.rfind(dispatch_id)
    marker_position = max(task_position, dispatch_position)
    after_markers = text[marker_position:] if marker_position >= 0 else text
    title_active = bool(ACTIVE_TITLE.search(str(shown_terminal.get("title") or "")))
    activity = marker_position >= 0 and bool(POST_SUBMISSION_ACTIVITY.search(after_markers))
    dispatch_status = dispatch.get("status")
    transcript_source, transcript_user_message = transcript_submission_evidence(
        client, task_id, dispatch_id
    )
    composer_evidence = terminal_composer_evidence(tail, task_id, dispatch_id)

    if (
        dispatch_status in FINAL_DISPATCH_STATUSES
        or transcript_user_message
        or title_active
        or activity
    ):
        state = "submitted"
    elif (
        dispatch_status in IGNITABLE_DISPATCH_STATUSES
        and transcript_source == "transcript"
        and composer_evidence
        and shown_terminal.get("connected")
        and shown_terminal.get("writable")
    ):
        state = "composer-pending"
    else:
        state = "input-missing"

    return Observation(
        event=event,
        scheduled_after_seconds=scheduled_after_seconds,
        observed_at=utc_now(),
        state=state,
        dispatch_status=dispatch_status if isinstance(dispatch_status, str) else None,
        terminal_status=(
            read_terminal.get("status")
            if isinstance(read_terminal.get("status"), str)
            else None
        ),
        terminal_connected=bool(shown_terminal.get("connected")),
        terminal_writable=bool(shown_terminal.get("writable")),
        terminal_title_active=title_active,
        task_marker_present=task_position >= 0,
        dispatch_marker_present=dispatch_position >= 0,
        transcript_source=transcript_source,
        transcript_user_message_present=transcript_user_message,
        composer_evidence=composer_evidence,
        post_submission_activity=activity,
        runtime_id=(
            dispatch_result.get("_runtime_id")
            or read_result.get("_runtime_id")
            or show_result.get("_runtime_id")
        ),
    )


def _windows_local_app_data() -> Path:
    class Guid(ctypes.Structure):
        _fields_ = [
            ("data1", ctypes.c_uint32),
            ("data2", ctypes.c_uint16),
            ("data3", ctypes.c_uint16),
            ("data4", ctypes.c_ubyte * 8),
        ]

    identifier = uuid.UUID("f1b32785-6fba-4fcf-9d55-7b8e7f157091")
    raw = identifier.bytes_le
    guid = Guid(
        int.from_bytes(raw[0:4], "little"),
        int.from_bytes(raw[4:6], "little"),
        int.from_bytes(raw[6:8], "little"),
        (ctypes.c_ubyte * 8).from_buffer_copy(raw[8:16]),
    )
    path_pointer = ctypes.c_wchar_p()
    result = ctypes.windll.shell32.SHGetKnownFolderPath(  # type: ignore[attr-defined]
        ctypes.byref(guid), 0, None, ctypes.byref(path_pointer)
    )
    if result != 0 or not path_pointer.value:
        raise LivenessError(
            f"Windows LocalAppData known-folder lookup failed with HRESULT {result}"
        )
    try:
        return Path(path_pointer.value)
    finally:
        ctypes.windll.ole32.CoTaskMemFree(path_pointer)  # type: ignore[attr-defined]


def production_state_dir() -> Path:
    """Return the one per-user product claim domain without invocation overrides."""

    if sys.platform == "win32":
        base = _windows_local_app_data()
    else:
        try:
            import pwd

            base = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".local" / "state"
        except (ImportError, KeyError, OSError) as error:
            raise LivenessError("cannot resolve the operating-system user state directory") from error
    return base / "orca-dispatch-liveness" / "ignitions"


@dataclass(frozen=True)
class FileIgnitionStore:
    state_dir: Path

    @classmethod
    def production(cls) -> "FileIgnitionStore":
        return cls(production_state_dir())

    @classmethod
    def for_test(cls, state_dir: Path) -> "FileIgnitionStore":
        """Explicit non-product injection point for isolated fixtures and demos."""

        return cls(state_dir)

    def claim(
        self, task_id: str, dispatch_id: str, terminal: str
    ) -> tuple[Path, bool, dict[str, Any]]:
        return claim_ignition(self.state_dir, task_id, dispatch_id, terminal)

    @staticmethod
    def mark_sent(marker: Path, record: dict[str, Any]) -> None:
        mark_ignition_sent(marker, record)


def claim_ignition(
    state_dir: Path, task_id: str, dispatch_id: str, terminal: str
) -> tuple[Path, bool, dict[str, Any]]:
    state_dir.mkdir(parents=True, exist_ok=True)
    marker = state_dir / f"{dispatch_id}.json"
    record = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "dispatch_id": dispatch_id,
        "terminal": terminal,
        "claimed_at": utc_now(),
        "status": "claimed-before-send",
    }
    try:
        with marker.open("x", encoding="utf-8") as stream:
            json.dump(record, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        return marker, True, record
    except FileExistsError:
        try:
            existing = json.loads(marker.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise LivenessError(
                f"ignition marker exists but is unreadable; refusing another Enter: {marker}"
            ) from error
        expected = {
            "task_id": task_id,
            "dispatch_id": dispatch_id,
            "terminal": terminal,
        }
        if any(existing.get(key) != value for key, value in expected.items()):
            raise LivenessError(
                f"ignition marker identity mismatch; refusing another Enter: {marker}"
            )
        return marker, False, existing


def mark_ignition_sent(marker: Path, record: dict[str, Any]) -> None:
    updated = dict(record)
    updated["status"] = "sent"
    updated["sent_at"] = utc_now()
    temporary = marker.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(updated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, marker)


def annotation_candidate(
    *,
    dispatch_id: str,
    recorded_at: str,
    ignition_count: int,
    sources: Sequence[str],
) -> dict[str, Any]:
    event = {
        "id": f"auto-{dispatch_id}-composer-pending",
        "category": "composer_pending",
        "label": "自动验活确认任务文本停在 composer；沿原终端至多补交一次 Enter",
        "recorded_at": recorded_at,
        "affected_count": 1,
        "ignition_count": ignition_count,
        "dispatch_ids": [dispatch_id],
        "sources": list(sources),
    }
    return {
        "ready_for_ops_metrics": bool(sources),
        "missing_required_fields": [] if sources else ["sources"],
        "event": event,
    }


def _nested_value(payload: dict[str, Any], dotted_path: str) -> Any:
    value: Any = payload
    for component in dotted_path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(component)
    return value


ISSUE_31_REQUIRED_FIELDS = (
    "sample.id",
    "sample.recorded_at",
    "sample.sources",
    "sample.identities.run_id",
    "sample.identities.task_id",
    "sample.identities.dispatch_id",
    "sample.identities.terminal",
    "sample.orca.app_version",
    "sample.orca.cli_version",
    "sample.orca.runtime_id",
    "sample.placement.dispatch_path",
    "sample.placement.worktree_selector",
    "sample.placement.worktree_path",
    "sample.outcome.observed_state",
    "sample.outcome.post_state",
    "sample.lifecycle.worker_done",
    "sample.lifecycle.release_result",
    "sample.lifecycle.residual_resources",
    "sample.recovery.automated_enter_count",
    "sample.recovery.human_action_count",
    "sample.recovery.elapsed_seconds",
)


def validate_issue_31_sample_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    """Consume the candidate schema used for direct Issue #31 sample registration."""

    missing: list[str] = []
    if candidate.get("schema_version") != ISSUE_31_SAMPLE_SCHEMA_VERSION:
        missing.append("schema_version")
    for path in ISSUE_31_REQUIRED_FIELDS:
        value = _nested_value(candidate, path)
        if value is None or value == "" or value == []:
            missing.append(path)
    return {
        "ready_for_issue_31": not missing,
        "missing_required_fields": missing,
        "sample": candidate.get("sample"),
    }


def issue_31_sample_candidate(
    client: OrcaAccess,
    *,
    task_id: str,
    dispatch_id: str,
    terminal: str,
    result: dict[str, Any],
    sources: Sequence[str],
) -> dict[str, Any]:
    worker_result = client.worker_show(dispatch_id)
    status_result = client.status()
    dispatch = worker_result.get("dispatch", {})
    worker = worker_result.get("worker", {})
    shown_terminal = worker_result.get("terminal", {})
    terminal_resource = worker_result.get("terminalResource", {})
    runtime = status_result.get("runtime", {})
    app_version = runtime.get("appVersion")
    start_options = worker.get("startOptions", {})
    if not isinstance(start_options, dict):
        start_options = {}
    residual_resources = worker.get("residualResources")
    if not isinstance(residual_resources, list):
        residual_resources = []
    elapsed_seconds = (
        max(
            float(entry.get("scheduled_after_seconds", 0))
            for entry in result.get("timeline", [])
            if isinstance(entry, dict)
        )
        if result.get("timeline")
        else 0.0
    )
    sample = {
        "id": f"auto-{dispatch_id}-{result['state']}",
        "recorded_at": result["finished_at"],
        "sources": list(sources),
        "identities": {
            "run_id": dispatch.get("run_id"),
            "task_id": task_id,
            "dispatch_id": dispatch_id,
            "terminal": terminal,
        },
        "orca": {
            "app_version": app_version,
            "cli_version": app_version,
            "cli_version_basis": "bundled CLI version reported by runtime appVersion",
            "runtime_id": runtime.get("runtimeId") or worker.get("runtime_epoch"),
        },
        "placement": {
            "dispatch_path": "worker-start" if worker else "unknown",
            "worktree_selector": start_options.get("worktree"),
            "worktree_path": shown_terminal.get("worktreePath"),
            "worktree_id": worker.get("worktree_id") or shown_terminal.get("worktreeId"),
            "branch": shown_terminal.get("branch"),
        },
        "outcome": {
            "observed_state": result.get("state"),
            "pre_ignition_state": result.get("pre_ignition_state"),
            "post_state": result.get("post_ignition_state") or result.get("state"),
            "dispatch_status": dispatch.get("status"),
            "worker_state": worker.get("state"),
            "terminal_status": worker_result.get("observation", {}).get("status"),
        },
        "lifecycle": {
            "heartbeat": (
                "observed" if dispatch.get("last_heartbeat_at") else "not-observed"
            ),
            "worker_done": (
                "observed" if dispatch.get("completed_at") else "not-observed"
            ),
            "release_result": terminal_resource.get("releaseState") or "not-requested",
            "residual_resources": residual_resources or ["none-reported"],
        },
        "recovery": {
            "automated_enter_count": result.get("ignition_count", 0),
            "human_action_count": 0,
            "elapsed_seconds": elapsed_seconds,
        },
        "side_effects": {
            "terminal_send_enter": result.get("ignition_count", 0),
            "redispatch": False,
            "worker_created": False,
            "resource_mutation": "none beyond the bounded Enter",
        },
    }
    return validate_issue_31_sample_candidate(
        {"schema_version": ISSUE_31_SAMPLE_SCHEMA_VERSION, "sample": sample}
    )


def monitor_dispatch(
    client: OrcaAccess,
    *,
    task_id: str,
    dispatch_id: str,
    terminal: str,
    ignition_store: FileIgnitionStore | None = None,
    sources: Sequence[str] = (),
    first_delay_seconds: float = 5.0,
    second_delay_seconds: float = 5.0,
    post_ignition_delay_seconds: float = 10.0,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    validate_identity(task_id, dispatch_id, terminal)
    if min(first_delay_seconds, second_delay_seconds, post_ignition_delay_seconds) < 0:
        raise LivenessError("delays cannot be negative")
    store = ignition_store or FileIgnitionStore.production()
    dispatch, _ = assert_exact_target(client, task_id, dispatch_id, terminal)
    started_at = utc_now()
    timeline: list[dict[str, Any]] = [
        {
            "event": "preflight",
            "observed_at": started_at,
            "dispatch_status": dispatch.get("status"),
            "identity_matched": True,
        }
    ]

    sleep(first_delay_seconds)
    first = observe(
        client,
        task_id,
        dispatch_id,
        terminal,
        event="read-5s",
        scheduled_after_seconds=first_delay_seconds,
    )
    timeline.append(asdict(first))
    second: Observation | None = None
    if first.state != "submitted":
        sleep(second_delay_seconds)
        second = observe(
            client,
            task_id,
            dispatch_id,
            terminal,
            event="read-10s",
            scheduled_after_seconds=first_delay_seconds + second_delay_seconds,
        )
        timeline.append(asdict(second))

    initial_state = (second or first).state
    observed_state = initial_state
    ignition_count = 0
    ignition: dict[str, Any] = {
        "eligible": initial_state == "composer-pending",
        "attempted": False,
        "sent": False,
        "marker": None,
        "reason": None,
    }
    pre_ignition_state: str | None = None
    post_ignition_state: str | None = None

    if initial_state == "composer-pending":
        pre_ignition = observe(
            client,
            task_id,
            dispatch_id,
            terminal,
            event="pre-ignition-read",
            scheduled_after_seconds=(
                first_delay_seconds + (second_delay_seconds if second else 0)
            ),
        )
        timeline.append(asdict(pre_ignition))
        pre_ignition_state = pre_ignition.state
        observed_state = pre_ignition.state
        gate_dispatch, gate_terminal = assert_exact_target(
            client, task_id, dispatch_id, terminal
        )
        timeline.append(
            {
                "event": "ignition-gate",
                "observed_at": utc_now(),
                "dispatch_status": gate_dispatch.get("status"),
                "terminal_connected": bool(gate_terminal.get("connected")),
                "terminal_writable": bool(gate_terminal.get("writable")),
                "identity_matched": True,
            }
        )
        still_ignitable = (
            pre_ignition.state == "composer-pending"
            and pre_ignition.dispatch_status in IGNITABLE_DISPATCH_STATUSES
            and pre_ignition.terminal_connected
            and pre_ignition.terminal_writable
            and pre_ignition.composer_evidence
            and gate_dispatch.get("status") in IGNITABLE_DISPATCH_STATUSES
            and gate_terminal.get("connected")
            and gate_terminal.get("writable")
        )
        if not still_ignitable:
            ignition["reason"] = "pre-ignition-state-changed"
        else:
            marker, claimed, record = store.claim(task_id, dispatch_id, terminal)
            ignition["marker"] = str(marker)
            if claimed:
                ignition["attempted"] = True
                client.send_enter(terminal)
                ignition_count = 1
                ignition["sent"] = True
                ignition["reason"] = "confirmed-by-pre-ignition-reread"
                store.mark_sent(marker, record)
                timeline.append(
                    {
                        "event": "single-enter",
                        "observed_at": utc_now(),
                        "terminal": terminal,
                        "ignition_count": 1,
                    }
                )
                sleep(post_ignition_delay_seconds)
                post = observe(
                    client,
                    task_id,
                    dispatch_id,
                    terminal,
                    event="post-ignition-read",
                    scheduled_after_seconds=(
                        first_delay_seconds
                        + (second_delay_seconds if second else 0)
                        + post_ignition_delay_seconds
                    ),
                )
                timeline.append(asdict(post))
                post_ignition_state = post.state
            else:
                ignition["reason"] = "already-claimed-for-this-dispatch"

    result: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "dispatch_id": dispatch_id,
        "terminal": terminal,
        "started_at": started_at,
        "finished_at": utc_now(),
        "state": observed_state,
        "initial_state": initial_state,
        "pre_ignition_state": pre_ignition_state,
        "post_ignition_state": post_ignition_state,
        "ignition_count": ignition_count,
        "ignition": ignition,
        "timeline": timeline,
        "boundaries": {
            "maximum_reads": 4,
            "maximum_enter_sends_per_dispatch": 1,
            "re_dispatch_permitted": False,
            "looping_permitted": False,
            "input_missing_recovery_permitted": False,
        },
    }
    if observed_state == "composer-pending":
        result["ops_metrics_annotation"] = annotation_candidate(
            dispatch_id=dispatch_id,
            recorded_at=(second or first).observed_at,
            ignition_count=ignition_count,
            sources=sources,
        )
        result["issue_31_sample_candidate"] = issue_31_sample_candidate(
            client,
            task_id=task_id,
            dispatch_id=dispatch_id,
            terminal=terminal,
            result=result,
            sources=sources,
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--dispatch-id", required=True)
    parser.add_argument("--terminal", required=True)
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--orca-command")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    parser.add_argument("--first-delay-seconds", type=float, default=5.0)
    parser.add_argument("--second-delay-seconds", type=float, default=5.0)
    parser.add_argument("--post-ignition-delay-seconds", type=float, default=10.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    client = OrcaClient(
        resolve_orca_command(args.orca_command), timeout_seconds=args.timeout_seconds
    )
    try:
        result = monitor_dispatch(
            client,
            task_id=args.task_id,
            dispatch_id=args.dispatch_id,
            terminal=args.terminal,
            sources=args.source,
            first_delay_seconds=args.first_delay_seconds,
            second_delay_seconds=args.second_delay_seconds,
            post_ignition_delay_seconds=args.post_ignition_delay_seconds,
        )
    except LivenessError as error:
        print(
            json.dumps(
                {"schema_version": SCHEMA_VERSION, "error": str(error)},
                ensure_ascii=False,
                indent=2,
            )
        )
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
