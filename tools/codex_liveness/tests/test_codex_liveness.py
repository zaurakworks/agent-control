from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import codex_liveness


TASK = "task_abc123"
DISPATCH = "ctx_def456"
TURN = "turn-1"


def write_jsonl(path: Path, rows: list[dict[str, object]], *, malformed_tail: bool = False) -> None:
    text = "\n".join(json.dumps(row) for row in rows) + "\n"
    if malformed_tail:
        text += '{"type":"partial"'
    path.write_text(text, encoding="utf-8")


class RolloutTests(unittest.TestCase):
    def test_current_item_completed_shape_binds_exact_turn(self) -> None:
        rows = [
            {
                "timestamp": "2026-08-12T12:00:00Z",
                "type": "session_meta",
                "payload": {"session_id": "session-1", "cli_version": "0.147.0"},
            },
            {
                "timestamp": "2026-08-12T12:00:01Z",
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": TURN},
            },
            {
                "timestamp": "2026-08-12T12:00:02Z",
                "type": "event_msg",
                "payload": {
                    "type": "item_completed",
                    "turn_id": TURN,
                    "item": {
                        "type": "UserMessage",
                        "content": [{"type": "input_text", "text": f"{TASK} {DISPATCH}"}],
                    },
                },
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            write_jsonl(path, rows)
            result = codex_liveness.inspect_rollout(path, TASK, DISPATCH)
        self.assertEqual(result.status, "已开始")
        self.assertEqual(result.turn_id, TURN)
        self.assertEqual(result.codex_version, "0.147.0")

    def test_legacy_user_message_shape_uses_active_turn(self) -> None:
        rows = [
            {
                "timestamp": "2026-07-18T12:00:00Z",
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": TURN},
            },
            {
                "timestamp": "2026-07-18T12:00:01Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": f"{TASK}\n{DISPATCH}",
                },
            },
            {
                "timestamp": "2026-07-18T12:00:01Z",
                "type": "event_msg",
                "payload": {"type": "user_message", "message": f"{TASK}\n{DISPATCH}"},
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            write_jsonl(path, rows)
            result = codex_liveness.inspect_rollout(path, TASK, DISPATCH)
        self.assertEqual(result.status, "已开始")
        self.assertEqual(result.schema, "event_msg/user_message")

    def test_stronger_message_schema_wins_over_later_duplicate(self) -> None:
        rows = [
            {
                "timestamp": "2026-08-12T12:00:00Z",
                "type": "event_msg",
                "payload": {"type": "task_started", "turn_id": TURN},
            },
            {
                "timestamp": "2026-08-12T12:00:01Z",
                "type": "event_msg",
                "payload": {
                    "type": "item_completed",
                    "turn_id": TURN,
                    "item": {
                        "type": "UserMessage",
                        "content": [{"type": "input_text", "text": f"{TASK} {DISPATCH}"}],
                    },
                },
            },
            {
                "timestamp": "2026-08-12T12:00:02Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": f"{TASK} {DISPATCH}",
                },
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            write_jsonl(path, rows)
            result = codex_liveness.inspect_rollout(path, TASK, DISPATCH)
        self.assertEqual(result.schema, "event_msg/item_completed.UserMessage")

    def test_exact_user_message_without_start_is_submitted(self) -> None:
        rows = [
            {
                "timestamp": "2026-08-12T12:00:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": f"{TASK} {DISPATCH}",
                },
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            write_jsonl(path, rows)
            result = codex_liveness.inspect_rollout(path, TASK, DISPATCH)
        self.assertEqual(result.status, "已提交")

    def test_tool_output_with_ids_does_not_count_as_submission(self) -> None:
        rows = [
            {
                "timestamp": "2026-08-12T12:00:00Z",
                "type": "response_item",
                "payload": {
                    "type": "custom_tool_call_output",
                    "output": f"{TASK} {DISPATCH}",
                },
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            write_jsonl(path, rows)
            result = codex_liveness.inspect_rollout(path, TASK, DISPATCH)
        self.assertEqual(result.status, "未提交")

    def test_malformed_tail_is_reported_without_losing_evidence(self) -> None:
        rows = [
            {
                "timestamp": "2026-08-12T12:00:00Z",
                "type": "response_item",
                "payload": {
                    "type": "message",
                    "role": "user",
                    "content": f"{TASK} {DISPATCH}",
                },
            }
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rollout.jsonl"
            write_jsonl(path, rows, malformed_tail=True)
            result = codex_liveness.inspect_rollout(path, TASK, DISPATCH)
        self.assertEqual(result.status, "已提交")
        self.assertEqual(len(result.warnings), 1)


class ExecEventTests(unittest.TestCase):
    def inspect(self, rows: list[dict[str, object]]) -> codex_liveness.Observation:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            write_jsonl(path, rows)
            return codex_liveness.inspect_bound_events(path, TASK, DISPATCH)

    def test_thread_started_means_submitted(self) -> None:
        result = self.inspect([{"type": "thread.started", "thread_id": "thread-1"}])
        self.assertEqual(result.status, "已提交")
        self.assertEqual(result.thread_id, "thread-1")

    def test_turn_started_means_started(self) -> None:
        result = self.inspect(
            [
                {"type": "thread.started", "thread_id": "thread-1"},
                {"type": "turn.started"},
            ]
        )
        self.assertEqual(result.status, "已开始")

    def test_empty_capture_means_not_submitted(self) -> None:
        self.assertEqual(self.inspect([]).status, "未提交")


class CommandShapeTests(unittest.TestCase):
    def test_approval_and_sandbox_precede_exec_only_flags(self) -> None:
        argv = codex_liveness.build_exec_argv()
        self.assertEqual(
            argv,
            [
                "codex",
                "-a",
                "never",
                "-s",
                "read-only",
                "exec",
                "--ephemeral",
                "--ignore-user-config",
                "--ignore-rules",
                "--json",
                "-",
            ],
        )
        self.assertLess(argv.index("-a"), argv.index("exec"))
        self.assertGreater(argv.index("--json"), argv.index("exec"))
        self.assertNotIn("--full-auto", argv)

    def test_rejects_ambiguous_identifier_prefixes(self) -> None:
        with self.assertRaises(ValueError):
            codex_liveness.validate_ids("task_bad-id", DISPATCH)


if __name__ == "__main__":
    unittest.main()
