from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODULE_PATH = Path(__file__).resolve().parents[1] / "dispatch_deadlines.py"
SPEC = importlib.util.spec_from_file_location("dispatch_deadlines", MODULE_PATH)
assert SPEC and SPEC.loader
dispatch_deadlines = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = dispatch_deadlines
SPEC.loader.exec_module(dispatch_deadlines)


class FakeReader:
    def __init__(self, tasks: list[dict[str, Any]], dispatches: dict[str, dict[str, Any]]):
        self.tasks = tasks
        self.dispatches = dispatches

    def task_list(self, run_id: str) -> dict[str, Any]:
        return {"runId": run_id, "tasks": self.tasks}

    def dispatch_show(self, task_id: str) -> dict[str, Any]:
        return {"dispatch": self.dispatches[task_id]}


def task(task_id: str, spec: str, title: str = "test") -> dict[str, Any]:
    return {
        "id": task_id,
        "status": "dispatched",
        "spec": spec,
        "display_name": title,
    }


def dispatch(task_id: str, started_at: str) -> dict[str, Any]:
    return {
        "id": "ctx_" + task_id.removeprefix("task_"),
        "task_id": task_id,
        "run_id": "run_test",
        "status": "dispatched",
        "dispatched_at": started_at,
    }


class DurationParsingTests(unittest.TestCase):
    def test_accepts_one_positive_explicit_value(self) -> None:
        self.assertEqual(
            dispatch_deadlines.expected_duration_minutes(
                "Title\nExpected-Duration-Minutes: 90\nDetails"
            ),
            (90, None),
        )

    def test_missing_value_is_unknown(self) -> None:
        self.assertEqual(
            dispatch_deadlines.expected_duration_minutes("no declaration"),
            (None, "expected_duration_missing"),
        )

    def test_duplicate_or_nonpositive_value_is_invalid(self) -> None:
        self.assertEqual(
            dispatch_deadlines.expected_duration_minutes(
                "Expected-Duration-Minutes: 30\nExpected-Duration-Minutes: 45"
            ),
            (None, "expected_duration_ambiguous"),
        )
        self.assertEqual(
            dispatch_deadlines.expected_duration_minutes(
                "Expected-Duration-Minutes: 0"
            ),
            (None, "expected_duration_invalid"),
        )


class ClassificationTests(unittest.TestCase):
    def test_exact_deadline_wakes_with_zero_overdue_seconds(self) -> None:
        item = task("task_boundary", "Expected-Duration-Minutes: 60")
        report = dispatch_deadlines.collect_deadlines(
            FakeReader(
                [item],
                {"task_boundary": dispatch("task_boundary", "2026-08-14T11:00:00Z")},
            ),
            "run_test",
            now=datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc),
        )
        row = report["dispatches"][0]
        self.assertTrue(row["should_wake"])
        self.assertEqual(row["overdue_seconds"], 0)

    def test_only_overdue_declared_dispatch_wakes(self) -> None:
        tasks = [
            task("task_overdue", "Expected-Duration-Minutes: 60", "overdue"),
            task("task_early", "Expected-Duration-Minutes: 90", "early"),
            task("task_missing", "ordinary spec", "missing"),
        ]
        dispatches = {
            "task_overdue": dispatch("task_overdue", "2026-08-14 10:00:00"),
            "task_early": dispatch("task_early", "2026-08-14T11:00:00Z"),
            "task_missing": dispatch("task_missing", "2026-08-14T09:00:00+00:00"),
        }
        report = dispatch_deadlines.collect_deadlines(
            FakeReader(tasks, dispatches),
            "run_test",
            now=datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc),
        )

        rows = {row["task_id"]: row for row in report["dispatches"]}
        self.assertTrue(rows["task_overdue"]["should_wake"])
        self.assertEqual(rows["task_overdue"]["overdue_seconds"], 3600)
        self.assertFalse(rows["task_early"]["should_wake"])
        self.assertEqual(rows["task_early"]["overdue_seconds"], 0)
        self.assertFalse(rows["task_missing"]["should_wake"])
        self.assertIsNone(rows["task_missing"]["overdue_seconds"])
        self.assertEqual(report["summary"]["should_wake_count"], 1)
        self.assertEqual(
            report["summary"]["missing_or_invalid_expectation_count"], 1
        )

    def test_no_in_flight_dispatch_means_no_wake(self) -> None:
        report = dispatch_deadlines.collect_deadlines(
            FakeReader([], {}),
            "run_test",
            now=datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(report["summary"]["in_flight_dispatch_count"], 0)
        self.assertEqual(report["summary"]["should_wake_count"], 0)
        self.assertIn("no wake is needed", dispatch_deadlines.render_text(report))

    def test_refuses_cross_run_dispatch(self) -> None:
        item = task("task_wrong", "Expected-Duration-Minutes: 30")
        wrong = dispatch("task_wrong", "2026-08-14T11:00:00Z")
        wrong["run_id"] = "run_other"
        with self.assertRaises(dispatch_deadlines.DeadlineError):
            dispatch_deadlines.collect_deadlines(
                FakeReader([item], {"task_wrong": wrong}),
                "run_test",
                now=datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc),
            )


if __name__ == "__main__":
    unittest.main()
