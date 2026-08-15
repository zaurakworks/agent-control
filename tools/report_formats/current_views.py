"""Small, versioned JSON views for the operations console."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
WORKER_VIEW_KIND = "agent-control.worker-current"
METRICS_VIEW_KIND = "agent-control.ops-metrics-current"


class ReportFormatError(ValueError):
    """Raised when a published current view is missing or invalid."""


def parse_view_timestamp(value: str, label: str = "timestamp") -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ReportFormatError(f"{label} must be a non-empty timestamp")
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ReportFormatError(f"{label} is not an RFC 3339 timestamp: {value}") from error
    if parsed.tzinfo is None:
        raise ReportFormatError(f"{label} has no timezone: {value}")
    return parsed.astimezone(timezone.utc)


def _timestamp_text(value: datetime, label: str) -> str:
    if value.tzinfo is None:
        raise ReportFormatError(f"{label} has no timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _non_negative_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ReportFormatError(f"{label} must be a non-negative integer")
    return value


@dataclass(frozen=True)
class WorkerView:
    observed_at: datetime
    running_count: int
    dispatched_count: int
    active_anomaly_count: int

    def __post_init__(self) -> None:
        _timestamp_text(self.observed_at, "observed_at")
        _non_negative_integer(self.running_count, "running_count")
        _non_negative_integer(self.dispatched_count, "dispatched_count")
        _non_negative_integer(self.active_anomaly_count, "active_anomaly_count")

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": WORKER_VIEW_KIND,
            "observed_at": _timestamp_text(self.observed_at, "observed_at"),
            "running_count": self.running_count,
            "dispatched_count": self.dispatched_count,
            "active_anomaly_count": self.active_anomaly_count,
        }


@dataclass(frozen=True)
class MetricsView:
    snapshot_at: datetime
    anomaly_count: int

    def __post_init__(self) -> None:
        _timestamp_text(self.snapshot_at, "snapshot_at")
        _non_negative_integer(self.anomaly_count, "anomaly_count")

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "kind": METRICS_VIEW_KIND,
            "snapshot_at": _timestamp_text(self.snapshot_at, "snapshot_at"),
            "anomaly_count": self.anomaly_count,
        }


CurrentView = WorkerView | MetricsView


def write_current(path: Path, view: CurrentView) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(view.to_payload(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _load_payload(path: Path, expected_kind: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ReportFormatError(f"cannot read {path}: {error}") from error
    except json.JSONDecodeError as error:
        raise ReportFormatError(f"{path} is not valid JSON") from error
    if not isinstance(payload, dict):
        raise ReportFormatError(f"{path} must contain a JSON object")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ReportFormatError(
            f"{path} has unsupported schema_version: {payload.get('schema_version')}"
        )
    if payload.get("kind") != expected_kind:
        raise ReportFormatError(f"{path} has unexpected view kind: {payload.get('kind')}")
    return payload


def load_worker_view(path: Path) -> WorkerView:
    payload = _load_payload(path, WORKER_VIEW_KIND)
    return WorkerView(
        observed_at=parse_view_timestamp(payload.get("observed_at"), "observed_at"),
        running_count=_non_negative_integer(payload.get("running_count"), "running_count"),
        dispatched_count=_non_negative_integer(
            payload.get("dispatched_count"), "dispatched_count"
        ),
        active_anomaly_count=_non_negative_integer(
            payload.get("active_anomaly_count"), "active_anomaly_count"
        ),
    )


def load_metrics_view(path: Path) -> MetricsView:
    payload = _load_payload(path, METRICS_VIEW_KIND)
    return MetricsView(
        snapshot_at=parse_view_timestamp(payload.get("snapshot_at"), "snapshot_at"),
        anomaly_count=_non_negative_integer(payload.get("anomaly_count"), "anomaly_count"),
    )
