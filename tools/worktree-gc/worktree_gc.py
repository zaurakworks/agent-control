#!/usr/bin/env python3
"""Safely remove inactive Orca-managed Git worktrees."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, Sequence


class WorktreeGcError(RuntimeError):
    """Raised when a complete, safe cleanup decision cannot be made."""


class OrcaCommandError(WorktreeGcError):
    """Raised for a typed Orca command failure."""

    def __init__(self, arguments: Sequence[str], code: str, message: str) -> None:
        self.arguments = list(arguments)
        self.code = code
        self.message = message
        super().__init__(f"Orca {' '.join(arguments)} failed: {code}: {message}")


class OrcaReader(Protocol):
    def root(self, arguments: Sequence[str]) -> dict[str, Any]: ...

    def orchestration(self, arguments: Sequence[str]) -> dict[str, Any]: ...


class GitReader(Protocol):
    def list_worktrees(self) -> list["GitWorktree"]: ...

    def fetch(self, remote: str) -> None: ...

    def is_clean(self, path: Path) -> bool: ...

    def is_ancestor(self, commit: str, target: str) -> bool: ...

    def upstream_ref(self, branch_ref: str) -> str | None: ...

    def ref_exists(self, ref: str) -> bool: ...

    def remove_worktree(self, path: Path) -> None: ...

    def delete_branch(self, branch: str, *, force: bool) -> None: ...


@dataclass(frozen=True)
class GitWorktree:
    path: Path
    head: str
    branch_ref: str | None
    bare: bool = False

    @property
    def branch(self) -> str | None:
        prefix = "refs/heads/"
        if self.branch_ref and self.branch_ref.startswith(prefix):
            return self.branch_ref[len(prefix) :]
        return None


@dataclass
class ActivitySnapshot:
    complete: bool
    terminal_paths: set[str] = field(default_factory=set)
    dispatch_paths: set[str] = field(default_factory=set)
    run_count: int = 0
    dispatched_task_count: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class WorktreeDecision:
    path: str
    branch: str | None
    head: str
    clean: bool | None
    merged_into_main: bool | None
    upstream_ref: str | None
    remote_branch_deleted: bool | None
    active_terminal: bool
    active_dispatch: bool
    protected_self: bool
    eligible: bool
    reasons: list[str]
    action: str
    branch_action: str | None = None
    error: str | None = None


def normalize_path(path: Path | str) -> str:
    return os.path.normcase(os.path.abspath(os.fspath(path))).replace("\\", "/")


def is_within(path: Path, root: Path) -> bool:
    try:
        Path(normalize_path(path)).relative_to(Path(normalize_path(root)))
    except ValueError:
        return False
    return True


def resolve_orca_command(override: str | None) -> list[str]:
    configured = override or os.environ.get("ORCA_CLI_COMMAND")
    if configured:
        command = shlex.split(configured)
        if not command:
            raise WorktreeGcError("configured Orca command is empty")
        return command
    if os.environ.get("ORCA_DEV_REPO_ROOT"):
        return ["orca-dev"]
    if sys.platform.startswith("linux") and os.environ.get("TERM_PROGRAM") != "Orca":
        return ["orca-ide"]
    return ["orca"]


class OrcaClient:
    """Read-only wrapper around the version-matched Orca CLI."""

    def __init__(self, command: Sequence[str], timeout_seconds: float) -> None:
        if not command:
            raise WorktreeGcError("Orca command cannot be empty")
        self.command = list(command)
        self.timeout_seconds = timeout_seconds

    def _json(self, arguments: Sequence[str]) -> dict[str, Any]:
        command = [*self.command, *arguments, "--json"]
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise WorktreeGcError(f"Orca read failed: {' '.join(arguments)}: {error}") from error
        output = (completed.stdout or completed.stderr).strip()
        try:
            payload = json.loads(output)
        except json.JSONDecodeError as error:
            detail = output[:240] or "no output"
            raise WorktreeGcError(
                f"Orca returned invalid JSON for {' '.join(arguments)}: {detail}"
            ) from error
        if completed.returncode or not payload.get("ok"):
            failure = payload.get("error") or {}
            raise OrcaCommandError(
                arguments,
                str(failure.get("code", completed.returncode)),
                str(failure.get("message", "unknown error")),
            )
        result = payload.get("result")
        if not isinstance(result, dict):
            raise WorktreeGcError(f"Orca {' '.join(arguments)} returned no result")
        return result

    def root(self, arguments: Sequence[str]) -> dict[str, Any]:
        return self._json(arguments)

    def orchestration(self, arguments: Sequence[str]) -> dict[str, Any]:
        return self._json(["orchestration", *arguments])


class GitClient:
    """Argument-array Git wrapper; destructive calls never use worktree force."""

    def __init__(self, repo: Path, timeout_seconds: float) -> None:
        self.repo = repo
        self.timeout_seconds = timeout_seconds

    def _run(
        self,
        arguments: Sequence[str],
        *,
        cwd: Path | None = None,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        command = ["git", *arguments]
        try:
            completed = subprocess.run(
                command,
                cwd=cwd or self.repo,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise WorktreeGcError(f"Git command failed: {' '.join(command)}: {error}") from error
        if check and completed.returncode:
            detail = (completed.stderr or completed.stdout).strip()
            raise WorktreeGcError(
                f"Git command failed ({completed.returncode}): {' '.join(command)}: {detail}"
            )
        return completed

    def repository_root(self) -> Path:
        output = self._run(["rev-parse", "--show-toplevel"]).stdout.strip()
        return Path(output).resolve()

    def fetch(self, remote: str) -> None:
        self._run(["fetch", "--prune", remote])

    def list_worktrees(self) -> list[GitWorktree]:
        output = self._run(["worktree", "list", "--porcelain"]).stdout
        records: list[GitWorktree] = []
        current: dict[str, str | bool] = {}
        for line in [*output.splitlines(), ""]:
            if not line:
                if current.get("worktree"):
                    records.append(
                        GitWorktree(
                            path=Path(str(current["worktree"])).resolve(),
                            head=str(current.get("HEAD") or ""),
                            branch_ref=(
                                str(current["branch"]) if current.get("branch") else None
                            ),
                            bare=bool(current.get("bare")),
                        )
                    )
                current = {}
                continue
            key, _, value = line.partition(" ")
            current[key] = value if value else True
        return records

    def is_clean(self, path: Path) -> bool:
        output = self._run(
            ["status", "--porcelain=v1", "--untracked-files=all"], cwd=path
        ).stdout
        return not output.strip()

    def is_ancestor(self, commit: str, target: str) -> bool:
        completed = self._run(
            ["merge-base", "--is-ancestor", commit, target], check=False
        )
        if completed.returncode == 0:
            return True
        if completed.returncode == 1:
            return False
        detail = (completed.stderr or completed.stdout).strip()
        raise WorktreeGcError(f"cannot compare {commit} with {target}: {detail}")

    def upstream_ref(self, branch_ref: str) -> str | None:
        output = self._run(
            ["for-each-ref", "--format=%(upstream)", branch_ref]
        ).stdout.strip()
        return output or None

    def ref_exists(self, ref: str) -> bool:
        completed = self._run(["show-ref", "--verify", "--quiet", ref], check=False)
        if completed.returncode in (0, 1):
            return completed.returncode == 0
        raise WorktreeGcError(f"cannot inspect Git ref {ref}")

    def remove_worktree(self, path: Path) -> None:
        self._run(["worktree", "remove", str(path)])

    def delete_branch(self, branch: str, *, force: bool) -> None:
        self._run(["branch", "-D" if force else "-d", branch])


def _task_list(reader: OrcaReader, run_id: str) -> tuple[str, list[dict[str, Any]]]:
    result = reader.orchestration(["task-list", "--run", run_id, "--brief"])
    tasks = result.get("tasks")
    if not isinstance(tasks, list):
        raise WorktreeGcError(f"Orca returned an invalid task list for {run_id}")
    return run_id, tasks


def _dispatch_path(reader: OrcaReader, task: dict[str, Any]) -> tuple[str | None, str | None]:
    task_id = str(task.get("id"))
    try:
        result = reader.orchestration(["dispatch-show", "--task", str(task.get("id"))])
    except OrcaCommandError as error:
        if error.code == "dispatch_not_found":
            return None, f"{task_id}: stale dispatched Task has no current Dispatch"
        raise
    dispatch = result.get("dispatch") or {}
    dispatch_id = dispatch.get("id")
    if not dispatch_id:
        raise WorktreeGcError(f"dispatched task {task.get('id')} has no Dispatch")
    if dispatch.get("status") != "dispatched":
        return None, f"{task_id}/{dispatch_id}: current Dispatch is {dispatch.get('status')}"
    try:
        result = reader.orchestration(["worker-show", "--dispatch", str(dispatch_id)])
    except OrcaCommandError as error:
        if error.code != "dispatch_not_found":
            raise
        process_incarnation = dispatch.get("process_incarnation")
        if isinstance(process_incarnation, str) and "::" in process_incarnation:
            path_part = process_incarnation.split("@@", 1)[0].split("::", 1)[1]
            if path_part:
                return (
                    normalize_path(path_part),
                    f"{task_id}/{dispatch_id}: Worker record missing; protected Dispatch process path",
                )
        raise WorktreeGcError(
            f"active Dispatch {dispatch_id} has no readable Worker or process worktree path"
        ) from error
    terminal_path = (result.get("terminal") or {}).get("worktreePath")
    if terminal_path:
        return normalize_path(str(terminal_path)), None
    worktree_id = (result.get("worker") or {}).get("worktree_id")
    if isinstance(worktree_id, str) and "::" in worktree_id:
        return normalize_path(worktree_id.split("::", 1)[1]), None
    raise WorktreeGcError(f"active Dispatch {dispatch_id} has no worktree path")


def collect_activity(reader: OrcaReader, *, max_parallel: int = 8) -> ActivitySnapshot:
    status = reader.root(["status"])
    runtime = status.get("runtime") or {}
    if runtime.get("state") != "ready" or not runtime.get("reachable"):
        raise WorktreeGcError("Orca runtime is not ready and reachable")

    terminal_result = reader.root(["terminal", "list"])
    terminals = terminal_result.get("terminals")
    if not isinstance(terminals, list):
        raise WorktreeGcError("Orca terminal list is invalid")
    terminal_paths = {
        normalize_path(str(terminal["worktreePath"]))
        for terminal in terminals
        if isinstance(terminal, dict) and terminal.get("worktreePath")
    }

    run_result = reader.orchestration(["run-list"])
    if run_result.get("nextCursor"):
        raise WorktreeGcError("Orca run list is paginated; refusing an incomplete scan")
    runs = run_result.get("runs")
    if not isinstance(runs, list):
        raise WorktreeGcError("Orca run list is invalid")
    run_ids = [str(run["id"]) for run in runs if not run.get("legacy")]

    worker_count = min(max_parallel, len(run_ids) or 1)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        task_results = list(executor.map(lambda run_id: _task_list(reader, run_id), run_ids))
    active_tasks = [
        task
        for _, tasks in task_results
        for task in tasks
        if task.get("status") == "dispatched"
    ]
    worker_count = min(max_parallel, len(active_tasks) or 1)
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        dispatch_results = list(executor.map(lambda task: _dispatch_path(reader, task), active_tasks))
    dispatch_paths = {path for path, _ in dispatch_results if path}
    warnings = [warning for _, warning in dispatch_results if warning]
    return ActivitySnapshot(
        complete=True,
        terminal_paths=terminal_paths,
        dispatch_paths=dispatch_paths,
        run_count=len(run_ids),
        dispatched_task_count=len(active_tasks),
        warnings=warnings,
    )


def safe_activity(reader: OrcaReader, *, max_parallel: int) -> ActivitySnapshot:
    try:
        return collect_activity(reader, max_parallel=max_parallel)
    except WorktreeGcError as error:
        return ActivitySnapshot(complete=False, warnings=[str(error)])


def evaluate_worktree(
    git: GitReader,
    worktree: GitWorktree,
    activity: ActivitySnapshot,
    *,
    self_path: Path,
    main_ref: str,
    remote: str,
) -> WorktreeDecision:
    normalized = normalize_path(worktree.path)
    reasons: list[str] = []
    clean: bool | None = None
    merged: bool | None = None
    upstream: str | None = None
    remote_deleted: bool | None = None

    protected_self = normalized == normalize_path(self_path)
    active_terminal = normalized in activity.terminal_paths
    active_dispatch = normalized in activity.dispatch_paths
    if protected_self:
        reasons.append("current_worktree")
    if active_terminal:
        reasons.append("active_terminal")
    if active_dispatch:
        reasons.append("active_dispatch")
    if not activity.complete:
        reasons.append("activity_scan_incomplete")

    try:
        clean = git.is_clean(worktree.path)
    except WorktreeGcError:
        reasons.append("git_status_unknown")
    else:
        if not clean:
            reasons.append("working_tree_dirty")

    try:
        merged = git.is_ancestor(worktree.head, main_ref)
    except WorktreeGcError:
        reasons.append("main_ancestry_unknown")

    if worktree.branch_ref:
        try:
            upstream = git.upstream_ref(worktree.branch_ref)
            expected_prefix = f"refs/remotes/{remote}/"
            if upstream and upstream.startswith(expected_prefix):
                remote_deleted = not git.ref_exists(upstream)
        except WorktreeGcError:
            reasons.append("upstream_state_unknown")

    lifecycle_safe = merged is True or remote_deleted is True
    if not lifecycle_safe:
        if merged is False and remote_deleted is False:
            reasons.append("branch_unmerged_remote_exists")
        else:
            reasons.append("lifecycle_not_proven")

    eligible = not reasons and clean is True and lifecycle_safe
    return WorktreeDecision(
        path=normalized,
        branch=worktree.branch,
        head=worktree.head,
        clean=clean,
        merged_into_main=merged,
        upstream_ref=upstream,
        remote_branch_deleted=remote_deleted,
        active_terminal=active_terminal,
        active_dispatch=active_dispatch,
        protected_self=protected_self,
        eligible=eligible,
        reasons=reasons,
        action="would_remove" if eligible else "retained",
    )


def scoped_worktrees(git: GitReader, workspace_root: Path) -> list[GitWorktree]:
    root_key = normalize_path(workspace_root)
    return sorted(
        (
            worktree
            for worktree in git.list_worktrees()
            if is_within(worktree.path, workspace_root)
            and normalize_path(worktree.path) != root_key
            and not worktree.bare
        ),
        key=lambda worktree: normalize_path(worktree.path),
    )


def _activity_dict(activity: ActivitySnapshot) -> dict[str, Any]:
    return {
        "complete": activity.complete,
        "run_count": activity.run_count,
        "dispatched_task_count": activity.dispatched_task_count,
        "terminal_worktree_count": len(activity.terminal_paths),
        "dispatch_worktree_count": len(activity.dispatch_paths),
        "warnings": activity.warnings,
    }


def run_cleanup(
    git: GitReader,
    reader: OrcaReader,
    *,
    workspace_root: Path,
    self_path: Path,
    main_ref: str,
    remote: str,
    execute: bool,
    max_parallel: int,
    now: datetime | None = None,
) -> tuple[dict[str, Any], int]:
    git.fetch(remote)
    before = scoped_worktrees(git, workspace_root)
    activity = safe_activity(reader, max_parallel=max_parallel)
    decisions = [
        evaluate_worktree(
            git,
            worktree,
            activity,
            self_path=self_path,
            main_ref=main_ref,
            remote=remote,
        )
        for worktree in before
    ]
    initial_eligible_count = sum(1 for decision in decisions if decision.eligible)
    worktree_by_path = {normalize_path(worktree.path): worktree for worktree in before}
    action_failures = 0

    if execute and activity.complete:
        for index, decision in enumerate(decisions):
            if not decision.eligible:
                continue
            worktree = worktree_by_path[decision.path]
            latest_activity = safe_activity(reader, max_parallel=max_parallel)
            latest = evaluate_worktree(
                git,
                worktree,
                latest_activity,
                self_path=self_path,
                main_ref=main_ref,
                remote=remote,
            )
            if not latest.eligible:
                latest.action = "retained_after_recheck"
                decisions[index] = latest
                continue
            try:
                git.remove_worktree(worktree.path)
            except WorktreeGcError as error:
                latest.action = "retained_remove_failed"
                latest.error = str(error)
                action_failures += 1
                decisions[index] = latest
                continue
            latest.action = "removed"
            latest.eligible = False
            if worktree.branch:
                force = latest.merged_into_main is not True and latest.remote_branch_deleted is True
                try:
                    git.delete_branch(worktree.branch, force=force)
                except WorktreeGcError as error:
                    latest.branch_action = "retained_delete_failed"
                    latest.error = str(error)
                    action_failures += 1
                else:
                    latest.branch_action = "deleted_force" if force else "deleted"
            decisions[index] = latest

    after = scoped_worktrees(git, workspace_root) if execute else before
    before_paths = {normalize_path(worktree.path) for worktree in before}
    appeared = [
        worktree for worktree in after if normalize_path(worktree.path) not in before_paths
    ]
    removed = sum(1 for decision in decisions if decision.action == "removed")
    pending_eligible = sum(1 for decision in decisions if decision.action == "would_remove")
    report = {
        "schema_version": 1,
        "observed_at": (now or datetime.now(timezone.utc)).isoformat().replace("+00:00", "Z"),
        "mode": "execute" if execute else "dry-run",
        "workspace_root": normalize_path(workspace_root),
        "self_worktree": normalize_path(self_path),
        "main_ref": main_ref,
        "remote": remote,
        "activity": _activity_dict(activity),
        "summary": {
            "before_count": len(before),
            "after_count": len(after),
            "eligible_count": initial_eligible_count,
            "removed_count": removed,
            "retained_count": len(decisions) - removed - pending_eligible,
            "action_failure_count": action_failures,
            "appeared_during_run_count": len(appeared),
        },
        "worktrees": [asdict(decision) for decision in decisions],
        "appeared_during_run": [
            {
                "path": normalize_path(worktree.path),
                "branch": worktree.branch,
                "head": worktree.head,
                "action": "retained_not_in_initial_plan",
            }
            for worktree in appeared
        ],
    }
    if not activity.complete:
        return report, 2
    if action_failures:
        return report, 1
    return report, 0


REASON_LABELS = {
    "current_worktree": "当前执行树",
    "active_terminal": "存在活动终端",
    "active_dispatch": "存在活动 Dispatch",
    "activity_scan_incomplete": "活动面扫描不完整",
    "git_status_unknown": "Git 状态未知",
    "working_tree_dirty": "工作区有未提交改动",
    "main_ancestry_unknown": "main 祖先关系未知",
    "upstream_state_unknown": "upstream 状态未知",
    "branch_unmerged_remote_exists": "分支未合入 main 且远端仍存在",
    "lifecycle_not_proven": "未证明已合入 main 或远端 upstream 已删除",
}


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    activity = report["activity"]
    mode = "执行" if report["mode"] == "execute" else "dry-run"
    lines = [
        f"# worktree 清理{mode}报告",
        "",
        f"> 观察时刻：{report['observed_at']}｜根：`{report['workspace_root']}`",
        (
            f"> Orca 活动面：{'完整' if activity['complete'] else '不完整'}｜"
            f"普通 Run {activity['run_count']}｜活动 Dispatch {activity['dispatched_task_count']}｜"
            f"活动终端路径 {activity['terminal_worktree_count']}"
        ),
        "",
        "## 汇总",
        "",
        f"- 清理前：{summary['before_count']} 根",
        f"- 通过项：{summary['eligible_count']} 根",
        f"- 已移除：{summary['removed_count']} 根",
        f"- 清理后：{summary['after_count']} 根",
        f"- 执行期间新增并保留：{summary['appeared_during_run_count']} 根",
        f"- 动作失败：{summary['action_failure_count']} 项",
        "",
        "## 明细",
        "",
    ]
    for row in report["worktrees"]:
        label = Path(row["path"]).name
        branch = row["branch"] or "detached"
        if row["action"] == "would_remove":
            result = "通过（待执行）"
        elif row["action"] == "removed":
            result = "已移除"
            if row.get("branch_action") == "retained_delete_failed":
                result += "；本地分支保留"
        else:
            reasons = "、".join(REASON_LABELS.get(reason, reason) for reason in row["reasons"])
            result = f"保留：{reasons or row['action']}"
        lines.append(f"- `{label}`｜`{branch}`｜{result}")
        if row.get("error"):
            lines.append(f"  - 错误：{row['error']}")
    if report["appeared_during_run"]:
        lines.extend(["", "## 执行期间新增", ""])
        for row in report["appeared_during_run"]:
            lines.append(
                f"- `{Path(row['path']).name}`｜`{row['branch'] or 'detached'}`｜"
                "不在初始计划，自动保留"
            )
    if activity["warnings"]:
        lines.extend(
            ["", "## 采集说明" if activity["complete"] else "## 采集缺口", ""]
        )
        lines.extend(f"- {warning}" for warning in activity["warnings"])
    lines.extend(
        [
            "",
            "## 判据",
            "",
            "仅当工作区干净、提交已合入 main 或已刷新且可证明原 upstream 消失、并且没有活动终端或 Dispatch 时通过；当前执行树始终保留。执行模式会在每个删除动作前重跑全部活动门。",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path.home() / "orca" / "workspaces" / "agent-control",
        help="Only registered Git worktrees below this resolved path are candidates.",
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="Any checkout of the repo.")
    parser.add_argument("--main-ref", default="origin/main")
    parser.add_argument("--remote", default="origin")
    parser.add_argument("--execute", action="store_true", help="Apply eligible removals.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--orca-command")
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--max-parallel", type=int, default=8)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.timeout_seconds <= 0:
        raise WorktreeGcError("--timeout-seconds must be positive")
    if args.max_parallel <= 0:
        raise WorktreeGcError("--max-parallel must be positive")
    workspace_root = args.workspace_root.resolve()
    if not workspace_root.is_dir():
        raise WorktreeGcError(f"workspace root is not a directory: {workspace_root}")
    git = GitClient(args.repo.resolve(), args.timeout_seconds)
    self_path = git.repository_root()
    reader = OrcaClient(resolve_orca_command(args.orca_command), args.timeout_seconds)
    report, result = run_cleanup(
        git,
        reader,
        workspace_root=workspace_root,
        self_path=self_path,
        main_ref=args.main_ref,
        remote=args.remote,
        execute=args.execute,
        max_parallel=args.max_parallel,
    )
    output = (
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
        if args.format == "json"
        else render_markdown(report)
    )
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        sys.stdout.write(output)
    return result


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except WorktreeGcError as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
