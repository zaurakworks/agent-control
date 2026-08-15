#!/usr/bin/env python3
"""Run a controlled composer-pending -> single Enter -> submitted demonstration."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import dispatch_liveness


TASK = "task_controlleddemo"
DISPATCH = "ctx_controlleddemo"
TERMINAL = "term_controlled-demo"


class DemoClient:
    def __init__(self) -> None:
        self.reads = ["pending", "pending", "pending", "submitted"]
        self.current = "pending"
        self.enter_count = 0

    def dispatch_show(self, task_id: str) -> dict[str, object]:
        return {
            "dispatch": {
                "id": DISPATCH,
                "task_id": TASK,
                "assignee_handle": TERMINAL,
                "status": "dispatched",
            },
            "_runtime_id": "controlled-runtime",
        }

    def terminal_read(self, terminal: str) -> dict[str, object]:
        self.current = self.reads.pop(0)
        tail = [f"> {TASK} {DISPATCH}", "Ctx / In / Out 0 / 0 / 0"]
        if self.current == "submitted":
            tail.append("• Controlled post-submit activity (1s • esc to interrupt)")
        return {
            "terminal": {"handle": TERMINAL, "status": "running", "tail": tail},
            "_runtime_id": "controlled-runtime",
        }

    def worker_read(self, dispatch_id: str) -> dict[str, object]:
        messages = []
        if self.current == "submitted":
            messages = [
                {
                    "role": "user",
                    "blocks": [{"type": "text", "text": f"{TASK} {DISPATCH}"}],
                }
            ]
        return {"source": "transcript", "transcript": {"messages": messages}}

    def worker_show(self, dispatch_id: str) -> dict[str, object]:
        return {
            "dispatch": {
                "id": DISPATCH,
                "task_id": TASK,
                "assignee_handle": TERMINAL,
                "status": "dispatched",
                "run_id": "run_controlleddemo",
                "last_heartbeat_at": None,
                "completed_at": None,
            },
            "worker": {
                "state": "ready",
                "runtime_epoch": "controlled-runtime",
                "worktree_id": "controlled-repo::C:/controlled",
                "startOptions": {"worktree": "path:C:/controlled"},
                "residualResources": [
                    {"kind": "terminal", "id": TERMINAL, "action": "created"}
                ],
            },
            "terminal": {
                "handle": TERMINAL,
                "worktreePath": "C:/controlled",
                "worktreeId": "controlled-repo::C:/controlled",
                "branch": "refs/heads/controlled",
            },
            "observation": {"status": "running"},
            "terminalResource": {"releaseState": "not_requested"},
        }

    @staticmethod
    def status() -> dict[str, object]:
        return {
            "runtime": {
                "appVersion": "1.4.181-controlled",
                "runtimeId": "controlled-runtime",
            }
        }

    def terminal_show(self, terminal: str) -> dict[str, object]:
        return {
            "terminal": {
                "handle": TERMINAL,
                "connected": True,
                "writable": True,
                "title": "Controlled terminal",
            },
            "_runtime_id": "controlled-runtime",
        }

    def send_enter(self, terminal: str) -> dict[str, object]:
        self.enter_count += 1
        return {"accepted": True}


def main() -> int:
    client = DemoClient()
    with tempfile.TemporaryDirectory() as directory:
        result = dispatch_liveness.monitor_dispatch(
            client,
            task_id=TASK,
            dispatch_id=DISPATCH,
            terminal=TERMINAL,
            ignition_store=dispatch_liveness.FileIgnitionStore.for_test(
                Path(directory)
            ),
            sources=["https://github.com/Eridanus117/agent-control/issues/241"],
            sleep=lambda _: None,
        )
        result["controlled_demo"] = True
        result["demo_enter_calls"] = client.enter_count
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
