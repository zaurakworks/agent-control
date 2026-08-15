from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops-metrics"))

import dispatch_liveness
import ops_metrics


TASK = "task_abc123"
DISPATCH = "ctx_def456"
TERMINAL = "term_12345678-abcd"


class FakeClient:
    def __init__(
        self,
        observations: list[dict[str, object]],
        dispatch_statuses: list[str] | None = None,
        transcript_source: str = "transcript",
    ) -> None:
        self.observations = list(observations)
        self.dispatch_statuses = list(dispatch_statuses or [])
        self.transcript_source = transcript_source
        self.current: dict[str, object] | None = None
        self.enter_count = 0
        self.dispatch = {
            "id": DISPATCH,
            "task_id": TASK,
            "assignee_handle": TERMINAL,
            "status": "dispatched",
        }

    def dispatch_show(self, task_id: str) -> dict[str, object]:
        self.assert_task(task_id)
        if self.dispatch_statuses:
            self.dispatch["status"] = self.dispatch_statuses.pop(0)
        return {"dispatch": dict(self.dispatch), "_runtime_id": "runtime-demo"}

    def worker_read(self, dispatch_id: str) -> dict[str, object]:
        if dispatch_id != DISPATCH:
            raise AssertionError(dispatch_id)
        messages: list[dict[str, object]] = []
        if (self.current or {}).get("transcript_submitted"):
            messages.append(
                {
                    "role": "user",
                    "blocks": [{"type": "text", "text": f"{TASK} {DISPATCH}"}],
                }
            )
        return {
            "source": self.transcript_source,
            "transcript": {"messages": messages},
            "_runtime_id": "runtime-demo",
        }

    def worker_show(self, dispatch_id: str) -> dict[str, object]:
        if dispatch_id != DISPATCH:
            raise AssertionError(dispatch_id)
        return {
            "dispatch": {
                **self.dispatch,
                "run_id": "run_demo",
                "last_heartbeat_at": "2026-08-13T14:00:00Z",
                "completed_at": None,
            },
            "worker": {
                "state": "ready",
                "runtime_epoch": "runtime-demo",
                "worktree_id": "repo-demo::C:/demo",
                "startOptions": {"worktree": "path:C:/demo"},
                "residualResources": [
                    {"kind": "terminal", "id": TERMINAL, "action": "created"}
                ],
            },
            "terminal": {
                "handle": TERMINAL,
                "worktreePath": "C:/demo",
                "worktreeId": "repo-demo::C:/demo",
                "branch": "refs/heads/demo",
            },
            "observation": {"status": "running"},
            "terminalResource": {"releaseState": "not_requested"},
        }

    @staticmethod
    def status() -> dict[str, object]:
        return {
            "runtime": {"appVersion": "1.4.181", "runtimeId": "runtime-demo"}
        }

    def terminal_read(self, terminal: str) -> dict[str, object]:
        self.assert_terminal(terminal)
        if not self.observations:
            raise AssertionError("unexpected extra observation")
        self.current = self.observations.pop(0)
        return {
            "terminal": {
                "handle": TERMINAL,
                "status": "running",
                "tail": self.current.get("tail", []),
            },
            "_runtime_id": "runtime-demo",
        }

    def terminal_show(self, terminal: str) -> dict[str, object]:
        self.assert_terminal(terminal)
        current = self.current or {}
        return {
            "terminal": {
                "handle": TERMINAL,
                "connected": True,
                "writable": True,
                "title": current.get("title", "Claude"),
            },
            "_runtime_id": "runtime-demo",
        }

    def send_enter(self, terminal: str) -> dict[str, object]:
        self.assert_terminal(terminal)
        self.enter_count += 1
        return {"accepted": True}

    @staticmethod
    def assert_task(task_id: str) -> None:
        if task_id != TASK:
            raise AssertionError(task_id)

    @staticmethod
    def assert_terminal(terminal: str) -> None:
        if terminal != TERMINAL:
            raise AssertionError(terminal)


def pending() -> dict[str, object]:
    return {
        "tail": [f"> injected contract {TASK} {DISPATCH}", "Ctx / In / Out 0 / 0 / 0"]
    }


def submitted() -> dict[str, object]:
    return {
        "tail": [
            f"injected contract {TASK} {DISPATCH}",
            "• Running a tool (2s • esc to interrupt)",
        ],
        "transcript_submitted": True,
    }


def submitted_without_activity() -> dict[str, object]:
    return {
        "tail": [f"› submitted user message {TASK} {DISPATCH}"],
        "transcript_submitted": True,
    }


def ambiguous_markers() -> dict[str, object]:
    return {"tail": [f"› ambiguous terminal text {TASK} {DISPATCH}"]}


def missing() -> dict[str, object]:
    return {"tail": ["empty composer", "no task markers"]}


class ClassificationTests(unittest.TestCase):
    def run_monitor(
        self, client: FakeClient, state_dir: Path
    ) -> tuple[dict[str, object], list[float]]:
        sleeps: list[float] = []
        result = dispatch_liveness.monitor_dispatch(
            client,
            task_id=TASK,
            dispatch_id=DISPATCH,
            terminal=TERMINAL,
            ignition_store=dispatch_liveness.FileIgnitionStore.for_test(state_dir),
            sources=["https://github.com/Eridanus117/agent-control/issues/241"],
            first_delay_seconds=5,
            second_delay_seconds=5,
            post_ignition_delay_seconds=10,
            sleep=sleeps.append,
        )
        return result, sleeps

    def test_submitted_stops_after_first_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient([submitted()])
            result, sleeps = self.run_monitor(client, Path(directory))
        self.assertEqual(result["state"], "submitted")
        self.assertEqual(result["ignition_count"], 0)
        self.assertEqual(client.enter_count, 0)
        self.assertEqual(sleeps, [5])

    def test_user_message_in_transcript_without_activity_is_submitted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient([submitted_without_activity()])
            result, sleeps = self.run_monitor(client, Path(directory))
        self.assertEqual(result["state"], "submitted")
        self.assertEqual(result["ignition_count"], 0)
        self.assertEqual(client.enter_count, 0)
        self.assertEqual(sleeps, [5])

    def test_ambiguous_terminal_markers_without_composer_evidence_never_enter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient([ambiguous_markers(), ambiguous_markers()])
            result, sleeps = self.run_monitor(client, Path(directory))
        self.assertEqual(result["state"], "input-missing")
        self.assertEqual(client.enter_count, 0)
        self.assertEqual(sleeps, [5, 5])

    def test_composer_looking_terminal_without_transcript_is_not_ignited(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient(
                [pending(), pending()], transcript_source="terminal"
            )
            result, sleeps = self.run_monitor(client, Path(directory))
        self.assertEqual(result["state"], "input-missing")
        self.assertEqual(client.enter_count, 0)
        self.assertEqual(sleeps, [5, 5])

    def test_input_missing_uses_two_reads_and_never_enters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient([missing(), missing()])
            result, sleeps = self.run_monitor(client, Path(directory))
        self.assertEqual(result["state"], "input-missing")
        self.assertEqual(result["ignition_count"], 0)
        self.assertEqual(client.enter_count, 0)
        self.assertEqual(sleeps, [5, 5])

    def test_confirmed_composer_gets_one_enter_and_post_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient([pending(), pending(), pending(), submitted()])
            result, sleeps = self.run_monitor(client, Path(directory))
            marker = Path(result["ignition"]["marker"])
            marker_payload = json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual(result["state"], "composer-pending")
        self.assertEqual(result["post_ignition_state"], "submitted")
        self.assertEqual(result["ignition_count"], 1)
        self.assertEqual(client.enter_count, 1)
        self.assertEqual(sleeps, [5, 5, 10])
        self.assertEqual(marker_payload["status"], "sent")

    def test_existing_claim_prevents_second_enter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state_dir = Path(directory)
            first_client = FakeClient([pending(), pending(), pending(), submitted()])
            self.run_monitor(first_client, state_dir)
            second_client = FakeClient([pending(), pending(), pending()])
            result, sleeps = self.run_monitor(second_client, state_dir)
        self.assertEqual(first_client.enter_count, 1)
        self.assertEqual(second_client.enter_count, 0)
        self.assertEqual(result["ignition"]["reason"], "already-claimed-for-this-dispatch")
        self.assertEqual(result["ignition_count"], 0)
        self.assertEqual(sleeps, [5, 5])

    def test_dispatch_completion_after_second_read_stops_before_enter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient(
                [pending(), pending(), pending()],
                dispatch_statuses=[
                    "dispatched",
                    "dispatched",
                    "dispatched",
                    "completed",
                ],
            )
            result, sleeps = self.run_monitor(client, Path(directory))
        self.assertEqual(result["initial_state"], "composer-pending")
        self.assertEqual(result["pre_ignition_state"], "submitted")
        self.assertEqual(result["state"], "submitted")
        self.assertEqual(result["ignition"]["reason"], "pre-ignition-state-changed")
        self.assertEqual(client.enter_count, 0)
        self.assertEqual(sleeps, [5, 5])

    def test_prompt_disappearing_without_activity_is_not_ignited(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient([pending(), missing()])
            result, _ = self.run_monitor(client, Path(directory))
        self.assertEqual(result["state"], "input-missing")
        self.assertEqual(client.enter_count, 0)

    def test_sample_and_annotation_are_consumed_by_their_real_parsers(self) -> None:
        source = "https://github.com/Eridanus117/agent-control/issues/241"
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient([pending(), pending(), pending(), submitted()])
            result, _ = self.run_monitor(client, Path(directory))
            annotation = result["ops_metrics_annotation"]
            sample = result["issue_31_sample_candidate"]
            self.assertTrue(sample["ready_for_issue_31"])
            self.assertEqual(sample["missing_required_fields"], [])
            consumed_sample = dispatch_liveness.validate_issue_31_sample_candidate(
                {"schema_version": 1, "sample": sample["sample"]}
            )
            self.assertTrue(consumed_sample["ready_for_issue_31"])

            event = dict(annotation["event"])
            event["sources"] = [source]
            observed = datetime.fromisoformat(event["recorded_at"].replace("Z", "+00:00"))
            window = ops_metrics.make_window(
                observed.date().isoformat(),
                "UTC",
                (observed + timedelta(seconds=1)).isoformat(),
            )
            annotations_path = Path(directory) / "annotations.json"
            annotations_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "date": observed.date().isoformat(),
                        "correction_events": [],
                        "worker_idle_events": [],
                        "dispatch_race_events": [event],
                    }
                ),
                encoding="utf-8",
            )
            consumed_annotation = ops_metrics.load_annotations(annotations_path, window)
        self.assertEqual(consumed_annotation["dispatch_race_count"], 1)
        self.assertEqual(consumed_annotation["ignition_count"], 1)


class SafetyTests(unittest.TestCase):
    def test_identity_mismatch_stops_before_read_or_enter(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            client = FakeClient([])
            client.dispatch["assignee_handle"] = "term_someone_else"
            with self.assertRaises(dispatch_liveness.LivenessError):
                dispatch_liveness.monitor_dispatch(
                    client,
                    task_id=TASK,
                    dispatch_id=DISPATCH,
                    terminal=TERMINAL,
                    ignition_store=dispatch_liveness.FileIgnitionStore.for_test(
                        Path(directory)
                    ),
                    sleep=lambda _: None,
                )
        self.assertEqual(client.enter_count, 0)

    def test_invalid_identity_is_rejected(self) -> None:
        with self.assertRaises(dispatch_liveness.LivenessError):
            dispatch_liveness.validate_identity("bad", DISPATCH, TERMINAL)

    def test_product_cli_has_no_state_directory_override(self) -> None:
        required = ["--task-id", TASK, "--dispatch-id", DISPATCH, "--terminal", TERMINAL]
        with self.assertRaises(SystemExit):
            dispatch_liveness.build_parser().parse_args(
                [*required, "--state-dir", "C:/another-claim-domain"]
            )
        with mock.patch.dict(
            os.environ,
            {"ORCA_DISPATCH_LIVENESS_STATE_DIR": "C:/ignored"},
            clear=False,
        ):
            self.assertNotEqual(
                dispatch_liveness.production_state_dir(), Path("C:/ignored")
            )

    def test_atomic_claim_allows_one_winner_across_processes(self) -> None:
        module_dir = Path(dispatch_liveness.__file__).resolve().parent
        script = (
            "import sys; from pathlib import Path; "
            f"sys.path.insert(0, {str(module_dir)!r}); "
            "import dispatch_liveness as d; "
            "print(d.claim_ignition(Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4])[1])"
        )
        with tempfile.TemporaryDirectory() as directory:
            arguments = [directory, TASK, DISPATCH, TERMINAL]
            processes = [
                subprocess.Popen(
                    [sys.executable, "-c", script, *arguments],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for _ in range(2)
            ]
            outputs = [process.communicate(timeout=10) for process in processes]
        self.assertTrue(all(process.returncode == 0 for process in processes), outputs)
        self.assertEqual(sorted(stdout.strip() for stdout, _ in outputs), ["False", "True"])


if __name__ == "__main__":
    unittest.main()
