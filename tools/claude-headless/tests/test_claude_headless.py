from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import claude_headless


SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {"classification": {"type": "string"}},
    "required": ["classification"],
}


class BoundsTests(unittest.TestCase):
    def test_rejects_limits_above_hard_ceilings(self) -> None:
        invalid = (
            claude_headless.Bounds(claude_headless.DEFAULT_MODEL, max_turns=4),
            claude_headless.Bounds(
                claude_headless.DEFAULT_MODEL, max_budget_usd=Decimal("1.01")
            ),
            claude_headless.Bounds(claude_headless.DEFAULT_MODEL, timeout_seconds=301),
        )
        for bounds in invalid:
            with self.subTest(bounds=bounds), self.assertRaises(claude_headless.HeadlessError):
                bounds.validate()

    def test_rejects_model_alias_or_version_omitted_name(self) -> None:
        for model in ("haiku", "claude-haiku-4-5"):
            with self.subTest(model=model), self.assertRaises(
                claude_headless.HeadlessError
            ):
                claude_headless.Bounds(model).validate()

    def test_rejects_non_finite_or_non_positive_budget(self) -> None:
        for budget in (
            Decimal("NaN"),
            Decimal("Infinity"),
            Decimal("-Infinity"),
            Decimal("-0.01"),
            Decimal("0"),
        ):
            with self.subTest(budget=budget), self.assertRaises(
                claude_headless.HeadlessError
            ):
                claude_headless.Bounds(
                    claude_headless.DEFAULT_MODEL, max_budget_usd=budget
                ).validate()

    def test_command_enforces_permission_tool_session_and_schema_boundaries(self) -> None:
        bounds = claude_headless.Bounds(
            claude_headless.DEFAULT_MODEL,
            max_turns=1,
            max_budget_usd=Decimal("0.10"),
            timeout_seconds=30,
        )
        command = claude_headless.build_command("claude", bounds, SCHEMA)
        self.assertIn("--safe-mode", command)
        self.assertIn("--no-session-persistence", command)
        self.assertEqual(command[command.index("--permission-mode") + 1], "dontAsk")
        self.assertEqual(command[command.index("--tools") + 1], "")
        self.assertEqual(command[command.index("--effort") + 1], "low")
        self.assertEqual(command[command.index("--max-turns") + 1], "1")
        self.assertEqual(command[command.index("--max-budget-usd") + 1], "0.1")
        encoded_schema = command[command.index("--json-schema") + 1]
        self.assertEqual(json.loads(encoded_schema), SCHEMA)


class InputTests(unittest.TestCase):
    def test_rejects_non_object_schema_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prompt = root / "prompt.txt"
            schema = root / "schema.json"
            prompt.write_text("classify this", encoding="utf-8")
            schema.write_text('{"type":"array"}', encoding="utf-8")
            with self.assertRaises(claude_headless.HeadlessError):
                claude_headless.load_inputs(prompt, schema)


class InvocationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bounds = claude_headless.Bounds(
            claude_headless.DEFAULT_MODEL,
            max_turns=1,
            max_budget_usd=Decimal("0.10"),
            timeout_seconds=30,
        )

    def invoke(self, root: Path) -> claude_headless.InvocationOutcome:
        return claude_headless.invoke(
            prompt_raw=b"classify this",
            prompt="classify this",
            schema_raw=json.dumps(SCHEMA).encode("utf-8"),
            schema=SCHEMA,
            bounds=self.bounds,
            result_path=root / "result.json",
            receipt_path=root / "receipt.json",
        )

    @mock.patch.object(claude_headless, "probe_claude_version", return_value="2.1.229")
    @mock.patch.object(claude_headless.subprocess, "Popen")
    def test_success_writes_only_structured_result_and_sanitized_receipt(
        self, popen: mock.Mock, _version: mock.Mock
    ) -> None:
        process = popen.return_value
        process.returncode = 0
        process.communicate.return_value = (
            json.dumps(
                {
                    "is_error": False,
                    "session_id": "must-not-be-persisted",
                    "result": "duplicate provider text",
                    "duration_ms": 1200,
                    "num_turns": 1,
                    "total_cost_usd": 0.01,
                    "modelUsage": {
                        claude_headless.DEFAULT_MODEL: {"costUSD": 0.01}
                    },
                    "structured_output": {"classification": "review"},
                }
            ),
            "",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outcome = self.invoke(root)
            result = json.loads((root / "result.json").read_text(encoding="utf-8"))
            receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(outcome.exit_code, 0)
        self.assertEqual(result, {"classification": "review"})
        self.assertEqual(receipt["status"], "succeeded")
        self.assertNotIn("session_id", receipt["provider"])
        self.assertNotIn("result", receipt["provider"])
        process.communicate.assert_called_once_with(input="classify this", timeout=30)

    @mock.patch.object(claude_headless, "terminate_process_tree")
    @mock.patch.object(claude_headless, "probe_claude_version", return_value="2.1.229")
    @mock.patch.object(claude_headless.subprocess, "Popen")
    def test_timeout_terminates_process_tree_and_writes_receipt(
        self,
        popen: mock.Mock,
        _version: mock.Mock,
        terminate: mock.Mock,
    ) -> None:
        process = popen.return_value
        process.returncode = -9
        process.communicate.side_effect = [
            subprocess.TimeoutExpired("claude", 30),
            ("", "sensitive-timeout-stderr"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outcome = self.invoke(root)
            receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
            self.assertFalse((root / "result.json").exists())
        self.assertEqual(outcome.exit_code, 4)
        self.assertEqual(receipt["status"], "timed_out")
        self.assertNotIn("stderrSummary", receipt)
        self.assertNotIn("sensitive-timeout-stderr", json.dumps(receipt))
        terminate.assert_called_once_with(process)

    @mock.patch.object(claude_headless, "probe_claude_version", return_value="2.1.229")
    @mock.patch.object(claude_headless.subprocess, "Popen")
    def test_nonzero_provider_exit_writes_failure_receipt(
        self, popen: mock.Mock, _version: mock.Mock
    ) -> None:
        process = popen.return_value
        process.returncode = 1
        process.communicate.return_value = (
            json.dumps(
                {
                    "is_error": True,
                    "subtype": "error_max_budget_usd",
                    "result": "Maximum budget reached",
                    "total_cost_usd": 0.25,
                }
            ),
            "sensitive-provider-stderr",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outcome = self.invoke(root)
            receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(outcome.exit_code, 5)
        self.assertEqual(receipt["status"], "provider_failed")
        self.assertNotIn("stderrSummary", receipt)
        self.assertNotIn("sensitive-provider-stderr", json.dumps(receipt))
        self.assertEqual(receipt["providerErrorCategory"], "budget")
        self.assertEqual(receipt["provider"]["total_cost_usd"], 0.25)
        self.assertNotIn("result", receipt["provider"])

    def test_rejects_non_finite_or_negative_provider_cost(self) -> None:
        for total_cost in ("NaN", "Infinity", "-Infinity", "-0.01"):
            envelope = {
                "modelUsage": {
                    claude_headless.DEFAULT_MODEL: {"costUSD": total_cost}
                },
                "total_cost_usd": total_cost,
            }
            with self.subTest(total_cost=total_cost):
                error = claude_headless.provider_boundary_error(
                    envelope, self.bounds
                )
                self.assertEqual(
                    error,
                    "provider total_cost_usd must be finite and non-negative",
                )

    @mock.patch.object(claude_headless, "probe_claude_version", return_value="2.1.229")
    @mock.patch.object(claude_headless.subprocess, "Popen")
    def test_missing_structured_output_is_rejected(
        self, popen: mock.Mock, _version: mock.Mock
    ) -> None:
        process = popen.return_value
        process.returncode = 0
        process.communicate.return_value = (json.dumps({"is_error": False}), "")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outcome = self.invoke(root)
            receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(outcome.exit_code, 6)
        self.assertEqual(receipt["status"], "invalid_provider_output")

    @mock.patch.object(claude_headless, "probe_claude_version", return_value="2.1.229")
    @mock.patch.object(claude_headless.subprocess, "Popen")
    def test_unexpected_model_usage_is_rejected(
        self, popen: mock.Mock, _version: mock.Mock
    ) -> None:
        process = popen.return_value
        process.returncode = 0
        process.communicate.return_value = (
            json.dumps(
                {
                    "is_error": False,
                    "total_cost_usd": 0.02,
                    "modelUsage": {
                        claude_headless.DEFAULT_MODEL: {"costUSD": 0.01},
                        "claude-sonnet-5": {"costUSD": 0.01},
                    },
                    "structured_output": {"classification": "review"},
                }
            ),
            "",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outcome = self.invoke(root)
            receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(outcome.exit_code, 6)
        self.assertIn("provider used models", receipt["error"])


if __name__ == "__main__":
    unittest.main()
