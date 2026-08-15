from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "worktree_gc.py"
SPEC = importlib.util.spec_from_file_location("worktree_gc", MODULE_PATH)
assert SPEC and SPEC.loader
worktree_gc = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = worktree_gc
SPEC.loader.exec_module(worktree_gc)


class FakeOrca:
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


def orca_responses() -> dict[tuple[str, ...], dict]:
    return {
        ("root", "status"): {"runtime": {"state": "ready", "reachable": True}},
        ("root", "terminal", "list"): {
            "terminals": [{"worktreePath": "C:/root/terminal-active"}]
        },
        ("orchestration", "run-list"): {
            "runs": [{"id": "run-1", "legacy": 0}, {"id": "legacy", "legacy": 1}],
            "nextCursor": None,
        },
        ("orchestration", "task-list", "--run", "run-1", "--brief"): {
            "tasks": [
                {"id": "task-1", "status": "dispatched", "dispatch_id": "ctx-1"},
                {"id": "task-2", "status": "completed", "dispatch_id": "ctx-2"},
            ]
        },
        ("orchestration", "dispatch-show", "--task", "task-1"): {
            "dispatch": {"id": "ctx-1", "status": "dispatched"}
        },
        ("orchestration", "worker-show", "--dispatch", "ctx-1"): {
            "terminal": {"worktreePath": "C:/root/dispatch-active"}
        },
    }


class FakeGit:
    def __init__(self, worktrees: list[object]) -> None:
        self.worktrees = list(worktrees)
        self.clean: dict[str, bool] = {}
        self.merged: dict[str, bool] = {}
        self.upstreams: dict[str, str | None] = {}
        self.existing_refs: set[str] = set()
        self.fetches: list[str] = []
        self.removed: list[str] = []
        self.deleted: list[tuple[str, bool]] = []

    def list_worktrees(self) -> list[object]:
        return list(self.worktrees)

    def fetch(self, remote: str) -> None:
        self.fetches.append(remote)

    def is_clean(self, path: Path) -> bool:
        return self.clean[worktree_gc.normalize_path(path)]

    def is_ancestor(self, commit: str, target: str) -> bool:
        return self.merged[commit]

    def upstream_ref(self, branch_ref: str) -> str | None:
        return self.upstreams.get(branch_ref)

    def ref_exists(self, ref: str) -> bool:
        return ref in self.existing_refs

    def remove_worktree(self, path: Path) -> None:
        key = worktree_gc.normalize_path(path)
        self.removed.append(key)
        self.worktrees = [
            item for item in self.worktrees if worktree_gc.normalize_path(item.path) != key
        ]

    def delete_branch(self, branch: str, *, force: bool) -> None:
        self.deleted.append((branch, force))


class ActivityTests(unittest.TestCase):
    def test_collects_terminal_and_dispatch_paths_and_skips_legacy_run(self) -> None:
        reader = FakeOrca(orca_responses())
        snapshot = worktree_gc.collect_activity(reader, max_parallel=1)

        self.assertTrue(snapshot.complete)
        self.assertEqual(snapshot.run_count, 1)
        self.assertEqual(snapshot.dispatched_task_count, 1)
        self.assertIn(
            worktree_gc.normalize_path("C:/root/terminal-active"), snapshot.terminal_paths
        )
        self.assertIn(
            worktree_gc.normalize_path("C:/root/dispatch-active"), snapshot.dispatch_paths
        )
        self.assertNotIn(
            ("orchestration", "task-list", "--run", "legacy", "--brief"), reader.calls
        )

    def test_missing_active_dispatch_path_makes_safe_snapshot_incomplete(self) -> None:
        responses = orca_responses()
        responses[("orchestration", "worker-show", "--dispatch", "ctx-1")] = {
            "worker": {"worktree_id": None},
            "terminal": {},
        }
        snapshot = worktree_gc.safe_activity(FakeOrca(responses), max_parallel=1)
        self.assertFalse(snapshot.complete)
        self.assertIn("has no worktree path", snapshot.warnings[0])

    def test_stale_dispatched_task_is_warning_not_an_active_dispatch(self) -> None:
        responses = orca_responses()
        responses[("orchestration", "dispatch-show", "--task", "task-1")] = (
            worktree_gc.OrcaCommandError(
                ["orchestration", "dispatch-show", "--task", "task-1"],
                "dispatch_not_found",
                "not found",
            )
        )
        snapshot = worktree_gc.collect_activity(FakeOrca(responses), max_parallel=1)
        self.assertTrue(snapshot.complete)
        self.assertEqual(snapshot.dispatch_paths, set())
        self.assertIn("stale dispatched Task", snapshot.warnings[0])

    def test_missing_worker_uses_dispatch_process_path(self) -> None:
        responses = orca_responses()
        responses[("orchestration", "dispatch-show", "--task", "task-1")] = {
            "dispatch": {
                "id": "ctx-1",
                "status": "dispatched",
                "process_incarnation": "repo::C:/root/process-active@@pty:incarnation",
            }
        }
        responses[("orchestration", "worker-show", "--dispatch", "ctx-1")] = (
            worktree_gc.OrcaCommandError(
                ["orchestration", "worker-show", "--dispatch", "ctx-1"],
                "dispatch_not_found",
                "not found",
            )
        )
        snapshot = worktree_gc.collect_activity(FakeOrca(responses), max_parallel=1)
        self.assertTrue(snapshot.complete)
        self.assertIn(
            worktree_gc.normalize_path("C:/root/process-active"), snapshot.dispatch_paths
        )
        self.assertIn("protected Dispatch process path", snapshot.warnings[0])


class DecisionTests(unittest.TestCase):
    def make_worktree(self, name: str, head: str = "head") -> object:
        return worktree_gc.GitWorktree(
            path=Path(f"C:/root/{name}"),
            head=head,
            branch_ref=f"refs/heads/feature/{name}",
        )

    def configured_git(self, worktree: object) -> FakeGit:
        git = FakeGit([worktree])
        git.clean[worktree_gc.normalize_path(worktree.path)] = True
        git.merged[worktree.head] = True
        return git

    def test_clean_merged_inactive_worktree_is_eligible(self) -> None:
        worktree = self.make_worktree("old")
        decision = worktree_gc.evaluate_worktree(
            self.configured_git(worktree),
            worktree,
            worktree_gc.ActivitySnapshot(complete=True),
            self_path=Path("C:/root/self"),
            main_ref="origin/main",
            remote="origin",
        )
        self.assertTrue(decision.eligible)
        self.assertEqual(decision.action, "would_remove")

    def test_current_dirty_terminal_or_dispatch_worktrees_are_retained(self) -> None:
        for reason in ("current", "dirty", "terminal", "dispatch"):
            with self.subTest(reason=reason):
                worktree = self.make_worktree(reason)
                git = self.configured_git(worktree)
                activity = worktree_gc.ActivitySnapshot(complete=True)
                self_path = Path("C:/root/self")
                if reason == "current":
                    self_path = worktree.path
                elif reason == "dirty":
                    git.clean[worktree_gc.normalize_path(worktree.path)] = False
                elif reason == "terminal":
                    activity.terminal_paths.add(worktree_gc.normalize_path(worktree.path))
                else:
                    activity.dispatch_paths.add(worktree_gc.normalize_path(worktree.path))
                decision = worktree_gc.evaluate_worktree(
                    git,
                    worktree,
                    activity,
                    self_path=self_path,
                    main_ref="origin/main",
                    remote="origin",
                )
                self.assertFalse(decision.eligible)

    def test_remote_deleted_requires_a_proven_origin_upstream(self) -> None:
        worktree = self.make_worktree("gone")
        git = self.configured_git(worktree)
        git.merged[worktree.head] = False
        activity = worktree_gc.ActivitySnapshot(complete=True)

        unknown = worktree_gc.evaluate_worktree(
            git,
            worktree,
            activity,
            self_path=Path("C:/root/self"),
            main_ref="origin/main",
            remote="origin",
        )
        self.assertFalse(unknown.eligible)
        self.assertIn("lifecycle_not_proven", unknown.reasons)

        git.upstreams[worktree.branch_ref] = "refs/remotes/origin/feature/gone"
        proven = worktree_gc.evaluate_worktree(
            git,
            worktree,
            activity,
            self_path=Path("C:/root/self"),
            main_ref="origin/main",
            remote="origin",
        )
        self.assertTrue(proven.eligible)
        self.assertTrue(proven.remote_branch_deleted)

    def test_incomplete_activity_scan_retains_everything(self) -> None:
        worktree = self.make_worktree("old")
        decision = worktree_gc.evaluate_worktree(
            self.configured_git(worktree),
            worktree,
            worktree_gc.ActivitySnapshot(complete=False, warnings=["probe failed"]),
            self_path=Path("C:/root/self"),
            main_ref="origin/main",
            remote="origin",
        )
        self.assertFalse(decision.eligible)
        self.assertIn("activity_scan_incomplete", decision.reasons)


class ExecutionTests(unittest.TestCase):
    def test_execute_rechecks_activity_then_removes_and_deletes_branch(self) -> None:
        worktree = worktree_gc.GitWorktree(
            path=Path("C:/root/old"),
            head="head",
            branch_ref="refs/heads/feature/old",
        )
        git = FakeGit([worktree])
        git.clean[worktree_gc.normalize_path(worktree.path)] = True
        git.merged["head"] = True
        reader = FakeOrca(
            {
                ("root", "status"): {"runtime": {"state": "ready", "reachable": True}},
                ("root", "terminal", "list"): {"terminals": []},
                ("orchestration", "run-list"): {"runs": [], "nextCursor": None},
            }
        )

        report, result = worktree_gc.run_cleanup(
            git,
            reader,
            workspace_root=Path("C:/root"),
            self_path=Path("C:/root/self"),
            main_ref="origin/main",
            remote="origin",
            execute=True,
            max_parallel=1,
        )

        self.assertEqual(result, 0)
        self.assertEqual(git.fetches, ["origin"])
        self.assertEqual(git.removed, [worktree_gc.normalize_path(worktree.path)])
        self.assertEqual(git.deleted, [("feature/old", False)])
        self.assertEqual(report["summary"]["before_count"], 1)
        self.assertEqual(report["summary"]["after_count"], 0)
        self.assertEqual(report["summary"]["removed_count"], 1)
        self.assertEqual(report["summary"]["appeared_during_run_count"], 0)
        self.assertGreaterEqual(reader.calls.count(("root", "terminal", "list")), 2)

    def test_dry_run_never_removes(self) -> None:
        worktree = worktree_gc.GitWorktree(
            path=Path("C:/root/old"),
            head="head",
            branch_ref="refs/heads/feature/old",
        )
        git = FakeGit([worktree])
        git.clean[worktree_gc.normalize_path(worktree.path)] = True
        git.merged["head"] = True
        reader = FakeOrca(
            {
                ("root", "status"): {"runtime": {"state": "ready", "reachable": True}},
                ("root", "terminal", "list"): {"terminals": []},
                ("orchestration", "run-list"): {"runs": [], "nextCursor": None},
            }
        )
        report, result = worktree_gc.run_cleanup(
            git,
            reader,
            workspace_root=Path("C:/root"),
            self_path=Path("C:/root/self"),
            main_ref="origin/main",
            remote="origin",
            execute=False,
            max_parallel=1,
        )
        self.assertEqual(result, 0)
        self.assertEqual(git.removed, [])
        self.assertEqual(report["summary"]["eligible_count"], 1)


class PorcelainParsingTests(unittest.TestCase):
    def test_parses_branch_and_detached_records(self) -> None:
        client = worktree_gc.GitClient(Path.cwd(), 1)
        output = """worktree C:/root/main
HEAD aaaa
branch refs/heads/main

worktree C:/root/detached
HEAD bbbb
detached

"""

        class Result:
            stdout = output

        client._run = lambda *args, **kwargs: Result()  # type: ignore[method-assign]
        records = client.list_worktrees()
        self.assertEqual(records[0].branch, "main")
        self.assertIsNone(records[1].branch)


if __name__ == "__main__":
    unittest.main()
