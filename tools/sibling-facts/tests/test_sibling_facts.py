from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "sibling_facts.py"
SPEC = importlib.util.spec_from_file_location("sibling_facts", MODULE_PATH)
assert SPEC and SPEC.loader
sibling_facts = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = sibling_facts
SPEC.loader.exec_module(sibling_facts)


class FakeRunner:
    def __init__(self, responses: dict[tuple[str, ...], tuple[int, str]]) -> None:
        self.responses = responses
        self.calls: list[tuple[tuple[str, ...], Path | None]] = []

    def run(
        self, arguments: list[str], *, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        key = tuple(arguments)
        self.calls.append((key, cwd))
        if key not in self.responses:
            raise AssertionError(f"unexpected command: {key}")
        returncode, output = self.responses[key]
        return subprocess.CompletedProcess(arguments, returncode, stdout=output, stderr="")


def orca_payload(result: dict) -> str:
    return json.dumps({"ok": True, "result": result})


def base_responses(agent_repo: Path, work_repo: Path) -> dict[tuple[str, ...], tuple[int, str]]:
    return {
        ("orca", "orchestration", "run-list", "--json"): (
            0,
            orca_payload(
                {
                    "runs": [{"id": "run-1", "objective": "deliver A4"}],
                    "nextCursor": None,
                }
            ),
        ),
        ("orca", "orchestration", "worker-list", "--json"): (
            0,
            orca_payload(
                {
                    "workers": [
                        {
                            "dispatchId": "ctx-self",
                            "taskId": "task-self",
                            "runId": "run-1",
                            "workerState": "ready",
                            "dispatchStatus": "dispatched",
                            "agentTerminalHandle": "term-self",
                            "resource": {"worktreeId": "repo::C:/agent/self"},
                        },
                        {
                            "dispatchId": "ctx-sibling",
                            "taskId": "task-sibling",
                            "runId": "run-1",
                            "workerState": "ready",
                            "dispatchStatus": "dispatched",
                            "agentTerminalHandle": "term-sibling",
                            "resource": {"worktreeId": "repo::C:/agent/sibling"},
                        },
                        {
                            "dispatchId": "ctx-old",
                            "taskId": "task-old",
                            "runId": "run-1",
                            "dispatchStatus": "completed",
                            "agentTerminalHandle": "term-old",
                        },
                    ],
                    "truncated": False,
                }
            ),
        ),
        ("orca", "terminal", "list", "--json"): (
            0,
            orca_payload(
                {
                    "terminals": [
                        {
                            "handle": "term-self",
                            "title": "self",
                            "worktreePath": "C:/agent/self",
                            "branch": "refs/heads/self",
                            "connected": True,
                            "writable": True,
                            "orphaned": False,
                        },
                        {
                            "handle": "term-sibling",
                            "title": "sibling",
                            "worktreePath": "C:/agent/sibling",
                            "branch": "refs/heads/sibling",
                            "connected": True,
                            "writable": True,
                            "orphaned": True,
                        },
                    ],
                    "truncated": False,
                }
            ),
        ),
        ("git", "-C", str(agent_repo), "worktree", "list", "--porcelain"): (
            0,
            "worktree C:/agent/main\nHEAD abc\nbranch refs/heads/main\n\n",
        ),
        ("git", "-C", str(work_repo), "worktree", "list", "--porcelain"): (
            0,
            "worktree C:/work/main\nHEAD def\ndetached\n\n",
        ),
        (
            "gh",
            "pr",
            "list",
            "--repo",
            "owner/agent-system",
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,title,headRefName,author,url,isDraft",
        ): (
            0,
            json.dumps(
                [
                    {
                        "number": 12,
                        "title": "A4",
                        "headRefName": "feature/a4",
                        "author": {"login": "owner"},
                        "url": "https://example/pr/12",
                        "isDraft": True,
                    }
                ]
            ),
        ),
    }


class CollectionTests(unittest.TestCase):
    def test_collects_direct_facts_and_marks_self_and_sibling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent_repo = root / "agent-system"
            work_repo = root / "work-skills"
            agent_repo.mkdir()
            work_repo.mkdir()
            lease = root / "scheduler-lease.json"
            lease.write_text(
                json.dumps({"coordinator": "coord", "session": "session-1"}),
                encoding="utf-8",
            )
            runner = FakeRunner(base_responses(agent_repo, work_repo))

            report = sibling_facts.collect_report(
                runner,
                orca_command=["orca"],
                agent_system_repo=agent_repo,
                work_skills_repo=work_repo,
                lease_path=lease,
                github_repositories=["owner/agent-system"],
                self_terminal="term-self",
                now=datetime(2026, 8, 14, tzinfo=timezone.utc),
            )

        self.assertEqual(report["summary"]["active_dispatch_count"], 2)
        self.assertEqual(report["summary"]["sibling_dispatch_count"], 1)
        self.assertEqual(report["active_dispatches"][0]["observed"]["relation"], "self")
        sibling = report["active_dispatches"][1]
        self.assertEqual(sibling["observed"]["relation"], "sibling")
        self.assertEqual(sibling["write_where"], "C:/agent/sibling")
        self.assertTrue(sibling["observed"]["terminal_orphaned"])
        self.assertEqual(sibling["observed"]["run_objective"], "deliver A4")
        self.assertEqual(report["scheduler_lease"][0]["observed"]["session_id"], "session-1")
        self.assertIn("不提供完整写入范围", report["scheduler_lease"][0]["write_where"])
        self.assertEqual(report["git_worktrees"][1]["observed"]["branch"], "detached")
        pr = report["open_pull_requests"][0]
        self.assertEqual(pr["who"], "author owner / PR #12")
        self.assertEqual(pr["write_where"], "owner/agent-system:feature/a4")

    def test_unavailable_source_is_reported_not_inferred(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent_repo = root / "agent-system"
            work_repo = root / "work-skills"
            agent_repo.mkdir()
            work_repo.mkdir()
            lease = root / "missing.json"
            responses = base_responses(agent_repo, work_repo)
            responses[("orca", "orchestration", "worker-list", "--json")] = (1, "offline")
            runner = FakeRunner(responses)

            report = sibling_facts.collect_report(
                runner,
                orca_command=["orca"],
                agent_system_repo=agent_repo,
                work_skills_repo=work_repo,
                lease_path=lease,
                github_repositories=["owner/agent-system"],
                self_terminal=None,
            )

        self.assertEqual(report["active_dispatches"], [])
        self.assertEqual(report["scheduler_lease"], [])
        statuses = {row["id"]: row["status"] for row in report["sources"]}
        self.assertEqual(statuses["orca_workers"], "unobserved")
        self.assertEqual(statuses["d9_lease"], "unobserved")
        rendered = sibling_facts.render_markdown(report)
        self.assertIn("未观察到非终态 Dispatch", rendered)
        self.assertIn("Orca Workers：未观察到", rendered)
        self.assertIn("D9 scheduler lease：未观察到", rendered)

    def test_only_read_only_subprocess_commands_are_issued(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agent_repo = root / "agent-system"
            work_repo = root / "work-skills"
            agent_repo.mkdir()
            work_repo.mkdir()
            lease = root / "scheduler-lease.json"
            lease.write_text("{}", encoding="utf-8")
            runner = FakeRunner(base_responses(agent_repo, work_repo))
            sibling_facts.collect_report(
                runner,
                orca_command=["orca"],
                agent_system_repo=agent_repo,
                work_skills_repo=work_repo,
                lease_path=lease,
                github_repositories=["owner/agent-system"],
                self_terminal=None,
            )

        commands = [call[0] for call in runner.calls]
        self.assertEqual(len(commands), 6)
        self.assertEqual(commands[0][1:3], ("orchestration", "run-list"))
        self.assertEqual(commands[1][1:3], ("orchestration", "worker-list"))
        self.assertEqual(commands[2][1:3], ("terminal", "list"))
        self.assertTrue(all("--execute" not in command for command in commands))
        self.assertTrue(all("create" not in command for command in commands))
        self.assertTrue(all("send" not in command for command in commands))


class ParsingTests(unittest.TestCase):
    def test_parses_porcelain_records(self) -> None:
        rows = sibling_facts.parse_worktree_porcelain(
            "worktree C:/one\nHEAD aaa\nbranch refs/heads/main\n\n"
            "worktree C:/two\nHEAD bbb\ndetached\nprunable stale\n\n"
        )
        self.assertEqual(rows[0]["branch"], "main")
        self.assertTrue(rows[1]["detached"])
        self.assertEqual(rows[1]["prunable"], "stale")


if __name__ == "__main__":
    unittest.main()
