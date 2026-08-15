from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from report_formats import (  # noqa: E402
    MetricsView,
    ReportFormatError,
    WorkerView,
    load_metrics_view,
    load_worker_view,
    write_current,
)


class CurrentViewTests(unittest.TestCase):
    def test_worker_view_round_trip(self) -> None:
        view = WorkerView(
            observed_at=datetime(2026, 8, 13, 12, tzinfo=timezone.utc),
            running_count=2,
            dispatched_count=3,
            active_anomaly_count=1,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "worker.json"
            write_current(path, view)
            loaded = load_worker_view(path)
        self.assertEqual(loaded, view)

    def test_metrics_view_round_trip(self) -> None:
        view = MetricsView(
            snapshot_at=datetime(2026, 8, 13, 12, 1, tzinfo=timezone.utc),
            anomaly_count=4,
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.json"
            write_current(path, view)
            loaded = load_metrics_view(path)
        self.assertEqual(loaded, view)

    def test_wrong_view_kind_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "view.json"
            write_current(
                path,
                MetricsView(
                    snapshot_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
                    anomaly_count=0,
                ),
            )
            with self.assertRaisesRegex(ReportFormatError, "unexpected view kind"):
                load_worker_view(path)

    def test_unknown_schema_version_is_rejected(self) -> None:
        payload = {
            "schema_version": 2,
            "kind": "agent-control.worker-current",
            "observed_at": "2026-08-13T12:00:00Z",
            "running_count": 0,
            "dispatched_count": 0,
            "active_anomaly_count": 0,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "view.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ReportFormatError, "unsupported schema_version"):
                load_worker_view(path)

    def test_negative_count_is_rejected(self) -> None:
        with self.assertRaisesRegex(ReportFormatError, "non-negative integer"):
            WorkerView(
                observed_at=datetime(2026, 8, 13, tzinfo=timezone.utc),
                running_count=-1,
                dispatched_count=0,
                active_anomaly_count=0,
            )


if __name__ == "__main__":
    unittest.main()
