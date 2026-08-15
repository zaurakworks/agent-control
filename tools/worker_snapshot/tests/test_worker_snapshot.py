from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import worker_snapshot


class FakeReader:
    def __init__(self, responses: dict[tuple[str, ...], dict]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, ...]] = []

    def root(self, arguments: list[str]) -> dict:
        key = ("root", *arguments)
        self.calls.append(key)
        response = self.responses[key]
        if isinstance(response, Exception):
            raise response
        return response

    def orchestration(self, arguments: list[str]) -> dict:
        key = ("orchestration", *arguments)
        self.calls.append(key)
        response = self.responses[key]
        if isinstance(response, Exception):
            raise response
        return response


def base_responses() -> dict[tuple[str, ...], dict]:
    return {
        ("root", "status"): {
            "runtime": {
                "state": "ready",
                "reachable": True,
                "runtimeId": "runtime-1",
                "appVersion": "1.2.3",
            }
        },
        ("orchestration", "run-list"): {
            "runs": [
                {"id": "run-1", "legacy": 0},
                {"id": "legacy", "legacy": 1},
            ],
            "nextCursor": None,
        },
        ("orchestration", "task-list", "--run", "run-1"): {
            "tasks": [
                {
                    "id": "task-1",
                    "task_title": "W226 观察面一页",
                    "spec": "合同=agent-control#226；交付快照",
                    "status": "dispatched",
                    "dispatch_id": "dispatch-1",
                },
                {"id": "task-done", "status": "completed"},
            ]
        },
        ("orchestration", "worker-show", "--dispatch", "dispatch-1"): {
            "dispatch": {"id": "dispatch-1", "dispatched_at": "2026-08-13 06:17:44"},
            "worker": {"state": "ready", "stage": "input_accepted"},
            "terminal": {
                "handle": "term_secret-should-not-leak",
                "connected": True,
                "orphaned": False,
            },
            "observation": {"status": "running"},
        },
    }


class ExtractionTests(unittest.TestCase):
    def test_contract_reference_wins_over_later_references(self) -> None:
        task = {"spec": "合同=agent-control#226；参考关联 #7（父级）"}
        self.assertEqual(worker_snapshot.extract_issue_number(task), 226)

    def test_title_removes_wave_prefix(self) -> None:
        task = {"task_title": "W226 观察面一页"}
        self.assertEqual(worker_snapshot.short_task_title(task, 226), "观察面一页")


class CollectionTests(unittest.TestCase):
    def test_collects_only_dispatched_workers_and_excludes_legacy_run(self) -> None:
        reader = FakeReader(base_responses())
        snapshot = worker_snapshot.collect_snapshot(
            reader,
            now=datetime(2026, 8, 13, 6, 20, tzinfo=timezone.utc),
            max_parallel=1,
        )
        self.assertEqual(snapshot["scope"]["run_ids"], ["run-1"])
        self.assertEqual(snapshot["summary"]["running_worker_count"], 1)
        self.assertEqual(snapshot["summary"]["dispatched_task_count"], 1)
        self.assertEqual(snapshot["summary"]["active_anomaly_count"], 0)
        self.assertEqual(snapshot["workers"][0]["dispatch_address"], "dispatch:dispatch-1")
        self.assertNotIn("handle", snapshot["workers"][0])
        self.assertNotIn("term_secret", str(snapshot))

    def test_worker_read_failure_is_visible_and_not_counted_as_running(self) -> None:
        responses = base_responses()
        responses[("orchestration", "worker-show", "--dispatch", "dispatch-1")] = (
            worker_snapshot.SnapshotError("dispatch_not_found")
        )
        snapshot = worker_snapshot.collect_snapshot(FakeReader(responses), max_parallel=1)
        self.assertEqual(snapshot["summary"]["running_worker_count"], 0)
        self.assertEqual(snapshot["summary"]["dispatched_task_count"], 1)
        self.assertEqual(snapshot["summary"]["active_anomaly_count"], 1)
        self.assertEqual(snapshot["summary"]["terminal_states"], {"unavailable": 1})
        self.assertIn("dispatch_not_found", snapshot["warnings"][0])

    def test_failed_worker_is_anomalous_even_while_terminal_runs(self) -> None:
        responses = base_responses()
        worker = responses[("orchestration", "worker-show", "--dispatch", "dispatch-1")]
        worker["worker"] = {"state": "failed", "stage": "cleanup"}
        snapshot = worker_snapshot.collect_snapshot(FakeReader(responses), max_parallel=1)
        self.assertEqual(snapshot["summary"]["running_worker_count"], 1)
        self.assertEqual(snapshot["summary"]["active_anomaly_count"], 1)

    def test_unknown_explicit_run_fails(self) -> None:
        with self.assertRaisesRegex(worker_snapshot.SnapshotError, "missing-run"):
            worker_snapshot.collect_snapshot(
                FakeReader(base_responses()), ["missing-run"], max_parallel=1
            )

    def test_duplicate_explicit_run_is_not_double_counted(self) -> None:
        snapshot = worker_snapshot.collect_snapshot(
            FakeReader(base_responses()), ["run-1", "run-1"], max_parallel=1
        )
        self.assertEqual(snapshot["scope"]["run_ids"], ["run-1"])
        self.assertEqual(snapshot["summary"]["running_worker_count"], 1)

    def test_paginated_run_list_fails_instead_of_under_counting(self) -> None:
        responses = base_responses()
        responses[("orchestration", "run-list")]["nextCursor"] = "more"
        with self.assertRaisesRegex(worker_snapshot.SnapshotError, "incomplete snapshot"):
            worker_snapshot.collect_snapshot(FakeReader(responses), max_parallel=1)


class RenderingTests(unittest.TestCase):
    def test_markdown_is_mobile_compact_and_uses_safe_issue_reference(self) -> None:
        snapshot = worker_snapshot.collect_snapshot(
            FakeReader(base_responses()),
            now=datetime(2026, 8, 13, 6, 20, tzinfo=timezone.utc),
            max_parallel=1,
        )
        rendered = worker_snapshot.render_markdown(snapshot)
        self.assertIn("在跑 worker：**1**", rendered)
        self.assertIn("关联 #226（观察面一页）", rendered)
        self.assertIn("dispatch:dispatch-1", rendered)
        self.assertNotIn("term_secret", rendered)
        self.assertEqual(rendered.count("关联 #226（观察面一页）"), 1)

    def test_untrusted_task_title_cannot_create_a_markdown_link(self) -> None:
        responses = base_responses()
        task = responses[("orchestration", "task-list", "--run", "run-1")]["tasks"][0]
        task["task_title"] = "W226 [点我](https://example.invalid)"
        rendered = worker_snapshot.render_markdown(
            worker_snapshot.collect_snapshot(FakeReader(responses), max_parallel=1)
        )
        self.assertIn(r"\[点我\](https://example.invalid)", rendered)
        self.assertNotIn("[点我](https://example.invalid)", rendered)


class CliTests(unittest.TestCase):
    def test_current_json_is_an_optional_parallel_output(self) -> None:
        arguments = worker_snapshot.build_parser().parse_args(
            ["--output", "current.md", "--current-json", "current.json"]
        )
        self.assertEqual(arguments.output, Path("current.md"))
        self.assertEqual(arguments.current_json, Path("current.json"))


if __name__ == "__main__":
    unittest.main()
