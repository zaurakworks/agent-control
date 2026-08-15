from __future__ import annotations

import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import time_scalar


class ExtractTimestampTests(unittest.TestCase):
    def test_preserves_raw_rfc3339_scalar(self) -> None:
        raw = "2026-08-12T13:16:41Z"
        result = time_scalar.extract_timestamp(
            json.dumps({"updated_at": raw}),
            keys=["updated_at"],
            source="GitHub Issue 28 updated_at",
        )
        self.assertEqual(result.value, raw)
        self.assertEqual(result.source, "GitHub Issue 28 updated_at")

    def test_reads_nested_orca_scalar_without_assigning_a_timezone(self) -> None:
        raw = "2026-08-12T17:09:22Z"
        result = time_scalar.extract_timestamp(
            json.dumps({"result": {"dispatch": {"last_heartbeat_at": raw}}}),
            keys=["result", "dispatch", "last_heartbeat_at"],
            source="Orca dispatch ctx_example",
        )
        self.assertEqual(result.value, raw)

    def test_rejects_timezone_free_value(self) -> None:
        with self.assertRaises(time_scalar.ScalarError):
            time_scalar.extract_timestamp(
                '{"created_at":"2026-08-12 17:07:12"}',
                keys=["created_at"],
                source="Orca dispatch ctx_example",
            )

    def test_rejects_already_parsed_payload(self) -> None:
        with self.assertRaises(TypeError):
            time_scalar.extract_timestamp(  # type: ignore[arg-type]
                {"updated_at": datetime(2026, 8, 12, tzinfo=timezone.utc)},
                keys=["updated_at"],
                source="converted host object",
            )


class SnapshotComparisonTests(unittest.TestCase):
    def test_exact_original_scalar_matches(self) -> None:
        current = time_scalar.TimestampScalar(
            "2026-08-12T13:16:41Z", "GitHub Issue 28 updated_at", ("updated_at",)
        )
        self.assertTrue(time_scalar.matches_snapshot(current, "2026-08-12T13:16:41Z"))

    def test_implicit_round_trip_format_does_not_match(self) -> None:
        current = time_scalar.TimestampScalar(
            "2026-08-12T13:16:41Z", "GitHub Issue 28 updated_at", ("updated_at",)
        )
        self.assertFalse(
            time_scalar.matches_snapshot(current, "2026-08-12T13:16:41.0000000Z")
        )

    def test_rejects_datetime_in_comparison_path(self) -> None:
        current = time_scalar.TimestampScalar(
            "2026-08-12T13:16:41Z", "GitHub Issue 28 updated_at", ("updated_at",)
        )
        with self.assertRaises(TypeError):
            time_scalar.matches_snapshot(current, datetime(2026, 8, 12, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
