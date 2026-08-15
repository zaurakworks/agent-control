from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import ops_metrics


class WindowTests(unittest.TestCase):
    def test_new_york_window_is_converted_to_utc(self) -> None:
        window = ops_metrics.make_window(
            "2026-08-12", "America/New_York", "2026-08-12T16:00:00Z"
        )
        self.assertEqual(window.start.isoformat(), "2026-08-12T04:00:00+00:00")
        self.assertEqual(window.end.isoformat(), "2026-08-13T04:00:00+00:00")
        self.assertTrue(window.contains(datetime(2026, 8, 12, 15, tzinfo=timezone.utc)))
        self.assertFalse(window.contains(datetime(2026, 8, 12, 3, 59, tzinfo=timezone.utc)))
        self.assertFalse(window.contains(datetime(2026, 8, 12, 16, tzinfo=timezone.utc)))

    def test_search_covers_both_utc_dates_crossed_by_local_day(self) -> None:
        window = ops_metrics.make_window(
            "2026-08-12", "America/New_York", "2026-08-12T16:00:00Z"
        )
        responses = [
            {"total_count": 1, "items": [{"number": 1}]},
            {"total_count": 2, "items": [{"number": 1}, {"number": 2}]},
        ]
        with mock.patch.object(ops_metrics, "gh_api", side_effect=responses) as api:
            items = ops_metrics.search_items("owner/repo", "is:pr created:", window)
        self.assertEqual({item["number"] for item in items}, {1, 2})
        queries = [call.kwargs["fields"]["q"] for call in api.call_args_list]
        self.assertEqual(
            queries,
            [
                "repo:owner/repo is:pr created:2026-08-12",
                "repo:owner/repo is:pr created:2026-08-13",
            ],
        )


class StatisticsTests(unittest.TestCase):
    def test_nearest_rank_p90_and_median(self) -> None:
        stats = ops_metrics.summarize_seconds([10, 20, 30, 40, 50])
        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["median_seconds"], 30)
        self.assertEqual(stats["p90_seconds"], 50)
        self.assertEqual(stats["max_seconds"], 50)

    def test_worker_done_requires_worker_report_provenance(self) -> None:
        valid = {
            "result": json.dumps(
                {
                    "provenance": "worker_report",
                    "outcome": "succeeded",
                    "completedAt": "2026-08-12T15:00:00Z",
                }
            )
        }
        self.assertEqual(ops_metrics.worker_done_at(valid), "2026-08-12T15:00:00Z")
        self.assertIsNone(ops_metrics.worker_done_at({"result": '{"outcome":"succeeded"}'}))

    def test_dispatch_cohort_excludes_worker_done_after_snapshot(self) -> None:
        window = ops_metrics.make_window(
            "2026-08-12", "America/New_York", "2026-08-12T16:00:00Z"
        )
        records = [
            {
                "dispatched_at": "2026-08-12 15:00:00",
                "worker_done_at": "2026-08-12T15:30:00Z",
            },
            {
                "dispatched_at": "2026-08-12 15:10:00",
                "worker_done_at": "2026-08-12T16:00:01Z",
            },
        ]
        summary = ops_metrics.summarize_orca_records(records, window)
        self.assertEqual(summary["dispatch_count"], 2)
        self.assertEqual(summary["worker_done_count"], 1)
        self.assertEqual(summary["dispatch_cohort_returned_count"], 1)
        self.assertEqual(summary["dispatch_cohort_return_rate"], 0.5)

    def test_inflight_peak_uses_earliest_durable_completion(self) -> None:
        window = ops_metrics.make_window(
            "2026-08-12", "America/New_York", "2026-08-12T16:00:00Z"
        )
        records = [
            {
                "dispatched_at": "2026-08-12 14:50:00",
                "dispatch_completed_at": "2026-08-12 15:20:00",
                "task_completed_at": "2026-08-12 15:20:01",
                "worker_done_at": "2026-08-12T15:20:02Z",
            },
            {
                "dispatched_at": "2026-08-12 15:00:00",
                "dispatch_completed_at": "2026-08-12 15:30:00",
                "task_completed_at": "2026-08-12 15:30:00",
                "worker_done_at": "2026-08-12T15:30:00Z",
            },
            {
                "dispatched_at": "2026-08-12 15:10:00",
                "dispatch_completed_at": None,
                "task_completed_at": "2026-08-12 15:40:00",
                "worker_done_at": None,
            },
            {
                "dispatched_at": "2026-08-12 15:20:00",
                "dispatch_completed_at": None,
                "task_completed_at": None,
                "worker_done_at": None,
            },
        ]
        summary = ops_metrics.summarize_inflight_peak(records, window)
        self.assertEqual(summary["inflight_peak"], 3)
        self.assertEqual(summary["inflight_peak_at"], "2026-08-12T15:10:00+00:00")


class OrcaCollectionTests(unittest.TestCase):
    def test_task_without_current_dispatch_is_reported_and_skipped(self) -> None:
        window = ops_metrics.make_window(
            "2026-08-12", "America/New_York", "2026-08-12T16:00:00Z"
        )
        responses = [
            {
                "ok": True,
                "result": {
                    "runs": [
                        {
                            "id": "run-1",
                            "objective": "test",
                            "created_at": "2026-08-12 14:00:00",
                        }
                    ]
                },
            },
            {
                "ok": True,
                "result": {"tasks": [{"id": "task-without-dispatch"}]},
            },
            {"ok": True, "result": {"dispatch": None}},
        ]
        with mock.patch.object(ops_metrics, "orca_json", side_effect=responses):
            result = ops_metrics.collect_orca(["run-1"], window)
        self.assertEqual(result["records"], [])
        self.assertEqual(result["dispatch_count"], 0)
        self.assertEqual(
            result["collection_errors"],
            ["task-without-dispatch: no current Dispatch is available"],
        )

    def test_released_worker_keeps_dispatch_and_worker_done_metrics(self) -> None:
        window = ops_metrics.make_window(
            "2026-08-12", "America/New_York", "2026-08-12T16:00:00Z"
        )
        responses = [
            {
                "ok": True,
                "result": {
                    "runs": [
                        {
                            "id": "run-1",
                            "objective": "test",
                            "created_at": "2026-08-12 14:00:00",
                        }
                    ]
                },
            },
            {
                "ok": True,
                "result": {
                    "tasks": [
                        {
                            "id": "task-released-worker",
                            "status": "completed",
                            "result": json.dumps(
                                {
                                    "provenance": "worker_report",
                                    "outcome": "succeeded",
                                    "completedAt": "2026-08-12T15:30:00Z",
                                }
                            ),
                        }
                    ]
                },
            },
            {
                "ok": True,
                "result": {
                    "dispatch": {
                        "id": "dispatch-released-worker",
                        "status": "completed",
                        "dispatched_at": "2026-08-12 15:00:00",
                    }
                },
            },
            ops_metrics.CollectionError(
                "command failed (orca orchestration worker-show): dispatch_not_found"
            ),
        ]
        with mock.patch.object(ops_metrics, "orca_json", side_effect=responses):
            result = ops_metrics.collect_orca(["run-1"], window)
        self.assertEqual(result["dispatch_count"], 1)
        self.assertEqual(result["worker_done_count"], 1)
        self.assertEqual(result["worker_states"], {"unavailable": 1})
        self.assertEqual(result["worker_observations"], {"unavailable": 1})
        self.assertEqual(
            result["collection_errors"],
            [
                "task-released-worker/dispatch-released-worker: worker details unavailable "
                "after release (dispatch_not_found)"
            ],
        )


class AnnotationTests(unittest.TestCase):
    @staticmethod
    def regression_check(check_id: str, *sample_ids: str) -> dict[str, object]:
        return {
            "id": check_id,
            "category": "reference_integrity",
            "label": "可复跑引用检查",
            "sample_ids": list(sample_ids),
            "check_type": "hybrid",
            "procedure": ["取回对象", "逐项核对"],
            "expected": "引用与取回对象一致",
            "sources": ["https://example/check"],
        }

    def test_annotations_count_categories_without_text_inference(self) -> None:
        window = ops_metrics.make_window(
            "2026-08-12", "America/New_York", "2026-08-12T16:00:00Z"
        )
        payload = {
            "schema_version": 1,
            "date": "2026-08-12",
            "correction_events": [
                {"id": "a", "category": "x", "label": "A", "sources": ["https://example/a"]},
                {"id": "b", "category": "x", "label": "B", "sources": ["https://example/b"]},
            ],
            "worker_idle_events": [
                {"id": "c", "category": "idle", "label": "C", "sources": ["https://example/c"]}
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "annotations.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = ops_metrics.load_annotations(path, window)
        self.assertEqual(result["correction_count"], 2)
        self.assertEqual(result["correction_categories"], {"x": 2})
        self.assertEqual(result["worker_idle_event_count"], 1)
        self.assertEqual(result["regression_check_count"], 0)
        self.assertEqual(result["regression_sample_count"], 0)

    def test_regression_checks_count_unique_samples_and_types(self) -> None:
        window = ops_metrics.make_window(
            "2026-08-12", "America/New_York", "2026-08-12T16:00:00Z"
        )
        first = self.regression_check("references", "link", "knowledge-id")
        second = self.regression_check("window", "scan-window")
        second["check_type"] = "automated"
        payload = {
            "schema_version": 1,
            "date": "2026-08-12",
            "correction_events": [],
            "worker_idle_events": [],
            "regression_checks": [first, second],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "annotations.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = ops_metrics.load_annotations(path, window)
        self.assertEqual(result["regression_check_count"], 2)
        self.assertEqual(result["regression_sample_count"], 3)
        self.assertEqual(result["regression_check_types"], {"hybrid": 1, "automated": 1})

    def test_regression_sample_cannot_appear_in_multiple_checks(self) -> None:
        window = ops_metrics.make_window(
            "2026-08-12", "America/New_York", "2026-08-12T16:00:00Z"
        )
        payload = {
            "schema_version": 1,
            "date": "2026-08-12",
            "correction_events": [],
            "worker_idle_events": [],
            "regression_checks": [
                self.regression_check("first", "same-sample"),
                self.regression_check("second", "same-sample"),
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "annotations.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ops_metrics.CollectionError):
                ops_metrics.load_annotations(path, window)

    def test_duplicate_annotation_id_fails(self) -> None:
        window = ops_metrics.make_window(
            "2026-08-12", "America/New_York", "2026-08-12T16:00:00Z"
        )
        event = {
            "id": "same",
            "category": "x",
            "label": "same",
            "sources": ["https://example"],
        }
        payload = {
            "schema_version": 1,
            "date": "2026-08-12",
            "correction_events": [event, event],
            "worker_idle_events": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "annotations.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ops_metrics.CollectionError):
                ops_metrics.load_annotations(path, window)

    def test_dispatch_races_are_source_backed_and_snapshot_bounded(self) -> None:
        window = ops_metrics.make_window(
            "2026-08-12", "America/New_York", "2026-08-12T16:00:00Z"
        )
        payload = {
            "schema_version": 1,
            "date": "2026-08-12",
            "correction_events": [],
            "worker_idle_events": [],
            "dispatch_race_events": [
                {
                    "id": "included",
                    "category": "composer_pending",
                    "label": "two pending composers",
                    "recorded_at": "2026-08-12T15:00:00Z",
                    "affected_count": 2,
                    "ignition_count": 2,
                    "dispatch_ids": ["dispatch-a", "dispatch-b"],
                    "sources": ["https://example/included"],
                },
                {
                    "id": "after-snapshot",
                    "category": "composer_pending",
                    "label": "recorded later",
                    "recorded_at": "2026-08-12T17:00:00Z",
                    "affected_count": 1,
                    "ignition_count": 1,
                    "dispatch_ids": ["dispatch-c"],
                    "sources": ["https://example/later"],
                },
            ],
            "manual_baseline": {
                "label": "manual",
                "dispatch_count": 2,
                "worker_done_count": 1,
                "success_rate": 0.5,
                "sources": ["https://example/baseline"],
            },
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "annotations.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            result = ops_metrics.load_annotations(path, window)
        self.assertEqual(result["dispatch_race_count"], 2)
        self.assertEqual(result["ignition_count"], 2)
        self.assertEqual(result["dispatch_race_categories"], {"composer_pending": 2})
        self.assertEqual(result["manual_baseline"]["success_rate"], 0.5)

    def test_dispatch_id_cannot_appear_in_multiple_race_events(self) -> None:
        window = ops_metrics.make_window(
            "2026-08-12", "America/New_York", "2026-08-12T18:00:00Z"
        )
        event = {
            "category": "composer_pending",
            "label": "pending composer",
            "recorded_at": "2026-08-12T15:00:00Z",
            "affected_count": 1,
            "ignition_count": 1,
            "dispatch_ids": ["same-dispatch"],
            "sources": ["https://example/race"],
        }
        payload = {
            "schema_version": 1,
            "date": "2026-08-12",
            "correction_events": [],
            "worker_idle_events": [],
            "dispatch_race_events": [
                {**event, "id": "first"},
                {**event, "id": "second"},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "annotations.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ops_metrics.CollectionError):
                ops_metrics.load_annotations(path, window)


class CurrentViewTests(unittest.TestCase):
    def test_current_view_preserves_existing_anomaly_formula(self) -> None:
        data = {
            "snapshot_at": "2026-08-13T12:01:00+00:00",
            "annotations": {
                "dispatch_race_count": 3,
                "worker_idle_event_count": 2,
            },
            "orca": {"collection_errors": ["one", "two"]},
        }
        view = ops_metrics.build_current_metrics_view(data)
        self.assertEqual(view.snapshot_at.isoformat(), "2026-08-13T12:01:00+00:00")
        self.assertEqual(view.anomaly_count, 6)


class CliTests(unittest.TestCase):
    def test_tick_and_manual_are_explicit_one_shot_trigger_values(self) -> None:
        required = [
            "--repo",
            "owner/repo",
            "--date",
            "2026-08-12",
            "--run-id",
            "run-1",
            "--annotations",
            "annotations.json",
            "--output-json",
            "report.json",
            "--output-report",
            "report.md",
        ]
        parser = ops_metrics.build_parser()
        self.assertEqual(parser.parse_args(required).trigger, "manual")
        self.assertEqual(parser.parse_args([*required, "--trigger", "tick"]).trigger, "tick")
        current = parser.parse_args([*required, "--current-report", "current.md"])
        self.assertEqual(current.current_report, Path("current.md"))
        structured = parser.parse_args([*required, "--current-json", "current.json"])
        self.assertEqual(structured.current_json, Path("current.json"))


if __name__ == "__main__":
    unittest.main()
