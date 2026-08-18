#!/usr/bin/env python3
"""Report active sibling facts from read-only local and GitHub observations."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, Sequence


TERMINAL_DISPATCH_STATUSES = {"completed", "failed", "stopped", "abandoned"}
DEFAULT_GITHUB_REPOSITORIES = (
    "zaurakworks/agent-system",
    "zaurakworks/work-skills",
    "zaurakworks/agent-plugins",
)


class Runner(Protocol):
    def run(self, arguments: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]: ...


@dataclass
class SubprocessRunner:
    timeout_seconds: float

    def run(
        self, arguments: Sequence[str], *, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(arguments),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=self.timeout_seconds,
        )


def resolve_orca_command(override: str | None) -> list[str]:
    configured = override or os.environ.get("ORCA_CLI_COMMAND")
    if configured:
        command = shlex.split(configured)
        if not command:
            raise ValueError("configured Orca command is empty")
        return command
    if os.environ.get("ORCA_DEV_REPO_ROOT"):
        return ["orca-dev"]
    if sys.platform.startswith("linux") and os.environ.get("TERM_PROGRAM") != "Orca":
        return ["orca-ide"]
    return ["orca"]


def display_command(arguments: Sequence[str]) -> str:
    """Render the exact argv as a copyable Windows command line."""

    return subprocess.list2cmdline(list(arguments))


def source(
    source_id: str,
    label: str,
    verify_command: str,
    *,
    status: str = "observed",
    error: str | None = None,
    item_count: int = 0,
) -> dict[str, Any]:
    return {
        "id": source_id,
        "label": label,
        "status": status,
        "item_count": item_count,
        "verify_command": verify_command,
        "error": error,
    }


def unavailable(source_row: dict[str, Any], error: str) -> dict[str, Any]:
    source_row["status"] = "unobserved"
    source_row["error"] = error
    source_row["item_count"] = 0
    return source_row


def run_json(
    runner: Runner,
    arguments: Sequence[str],
    *,
    cwd: Path | None = None,
    unwrap_orca: bool = False,
) -> Any:
    try:
        completed = runner.run(arguments, cwd=cwd)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as error:
        raise RuntimeError(str(error)) from error
    output = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode:
        raise RuntimeError(output[:400] or f"exit {completed.returncode}")
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"invalid JSON: {output[:300] or 'no output'}") from error
    if unwrap_orca:
        if not isinstance(payload, dict) or not payload.get("ok"):
            detail = payload.get("error") if isinstance(payload, dict) else payload
            raise RuntimeError(f"Orca returned an error: {detail}")
        result = payload.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("Orca returned no result object")
        return result
    return payload


def parse_worktree_porcelain(text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for raw_line in [*text.splitlines(), ""]:
        line = raw_line.strip()
        if not line:
            if current:
                rows.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current["path"] = value
        elif key == "HEAD":
            current["head"] = value
        elif key == "branch":
            current["branch"] = value.removeprefix("refs/heads/")
        elif key == "detached":
            current["detached"] = True
        elif key == "prunable":
            current["prunable"] = value or True
    return rows


def worktree_path(worker: dict[str, Any]) -> str | None:
    resource = worker.get("resource")
    if not isinstance(resource, dict):
        return None
    direct = resource.get("worktreePath")
    if isinstance(direct, str) and direct:
        return direct
    identity = resource.get("worktreeId")
    if isinstance(identity, str) and "::" in identity:
        return identity.split("::", 1)[1]
    return None


def fact(
    kind: str,
    who: str,
    write_where: str,
    verify_command: str,
    **observed: Any,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "who": who,
        "write_where": write_where,
        "verify_command": verify_command,
        "observed": observed,
    }


def collect_report(
    runner: Runner,
    *,
    orca_command: Sequence[str],
    agent_system_repo: Path,
    work_skills_repo: Path,
    lease_path: Path,
    github_repositories: Sequence[str],
    self_terminal: str | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    observed_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    report: dict[str, Any] = {
        "schema_version": 1,
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
        "caller_terminal": self_terminal or "未观察到",
        "sources": [],
        "active_dispatches": [],
        "live_terminals": [],
        "scheduler_lease": [],
        "git_worktrees": [],
        "open_pull_requests": [],
    }

    run_args = [*orca_command, "orchestration", "run-list", "--json"]
    worker_args = [*orca_command, "orchestration", "worker-list", "--json"]
    terminal_args = [*orca_command, "terminal", "list", "--json"]
    run_source = source("orca_runs", "Orca Runs", display_command(run_args))
    worker_source = source("orca_workers", "Orca Workers", display_command(worker_args))
    terminal_source = source("orca_terminals", "Orca terminals", display_command(terminal_args))

    runs: list[dict[str, Any]] = []
    workers: list[dict[str, Any]] = []
    terminals: list[dict[str, Any]] = []
    try:
        result = run_json(runner, run_args, unwrap_orca=True)
        value = result.get("runs")
        if not isinstance(value, list):
            raise RuntimeError("result.runs is not a list")
        runs = [row for row in value if isinstance(row, dict)]
        run_source["item_count"] = len(runs)
        if result.get("nextCursor"):
            run_source["status"] = "partial"
            run_source["error"] = "run-list returned a continuation cursor"
    except RuntimeError as error:
        unavailable(run_source, str(error))
    try:
        result = run_json(runner, worker_args, unwrap_orca=True)
        value = result.get("workers")
        if not isinstance(value, list):
            raise RuntimeError("result.workers is not a list")
        workers = [row for row in value if isinstance(row, dict)]
        worker_source["item_count"] = len(workers)
        if result.get("truncated"):
            worker_source["status"] = "partial"
            worker_source["error"] = "worker-list reported truncated=true"
    except RuntimeError as error:
        unavailable(worker_source, str(error))
    try:
        result = run_json(runner, terminal_args, unwrap_orca=True)
        value = result.get("terminals")
        if not isinstance(value, list):
            raise RuntimeError("result.terminals is not a list")
        terminals = [row for row in value if isinstance(row, dict)]
        terminal_source["item_count"] = len(terminals)
        if result.get("truncated"):
            terminal_source["status"] = "partial"
            terminal_source["error"] = "terminal list reported truncated=true"
    except RuntimeError as error:
        unavailable(terminal_source, str(error))
    report["sources"].extend([run_source, worker_source, terminal_source])

    run_by_id = {str(row.get("id")): row for row in runs if row.get("id")}
    terminal_by_handle = {
        str(row.get("handle")): row for row in terminals if row.get("handle")
    }
    for worker in workers:
        dispatch_status = str(worker.get("dispatchStatus") or "")
        if dispatch_status.lower() in TERMINAL_DISPATCH_STATUSES:
            continue
        task_id = str(worker.get("taskId") or "未观察到")
        dispatch_id = str(worker.get("dispatchId") or "未观察到")
        terminal_handle = str(worker.get("agentTerminalHandle") or "未观察到")
        run_id = str(worker.get("runId") or "未观察到")
        path = worktree_path(worker) or "未观察到"
        terminal = terminal_by_handle.get(terminal_handle, {})
        run = run_by_id.get(run_id, {})
        relation = (
            "self"
            if self_terminal and terminal_handle == self_terminal
            else "sibling"
            if self_terminal
            else "unknown"
        )
        report["active_dispatches"].append(
            fact(
                "active_dispatch",
                f"Task {task_id} / Dispatch {dispatch_id} / terminal {terminal_handle}",
                path,
                worker_source["verify_command"],
                relation=relation,
                task_id=task_id,
                dispatch_id=dispatch_id,
                dispatch_status=dispatch_status or "未观察到",
                worker_state=worker.get("workerState") or "未观察到",
                terminal_handle=terminal_handle,
                terminal_orphaned=terminal.get("orphaned", "未观察到"),
                branch=terminal.get("branch") or "未观察到",
                run_id=run_id,
                run_objective=run.get("objective") or "未观察到",
                run_verify_command=run_source["verify_command"],
            )
        )

    for terminal in terminals:
        handle = str(terminal.get("handle") or "未观察到")
        path = terminal.get("worktreePath") or "未观察到"
        relation = (
            "self"
            if self_terminal and handle == self_terminal
            else "sibling"
            if self_terminal
            else "unknown"
        )
        report["live_terminals"].append(
            fact(
                "live_terminal",
                f"terminal {handle} / {terminal.get('title') or '标题未观察到'}",
                str(path),
                terminal_source["verify_command"],
                relation=relation,
                handle=handle,
                title=terminal.get("title") or "未观察到",
                branch=terminal.get("branch") or "未观察到",
                connected=terminal.get("connected", "未观察到"),
                writable=terminal.get("writable", "未观察到"),
                orphaned=terminal.get("orphaned", "未观察到"),
            )
        )

    lease_verify = f"Get-Content -Raw -LiteralPath '{str(lease_path).replace(chr(39), chr(39) * 2)}'"
    lease_source = source("d9_lease", "D9 scheduler lease", lease_verify)
    try:
        payload = json.loads(lease_path.read_text(encoding="utf-8-sig"))
        if not isinstance(payload, dict):
            raise RuntimeError("lease root is not an object")
        lease_source["item_count"] = 1
        coordinator = payload.get("coordinator") or "未观察到"
        session_id = payload.get("session") or "未观察到"
        report["scheduler_lease"].append(
            fact(
                "scheduler_lease",
                f"coordinator {coordinator} / session {session_id}",
                "未观察到（D9 租约只提供调度权持有者与 session，不提供完整写入范围）",
                lease_verify,
                coordinator=coordinator,
                session_id=session_id,
                coordinator_terminal_handle=payload.get("coordinator_terminal_handle")
                or "未观察到",
            )
        )
    except (OSError, json.JSONDecodeError, RuntimeError) as error:
        unavailable(lease_source, str(error))
    report["sources"].append(lease_source)

    for source_id, label, repo_path in (
        ("git_agent_system", "agent-system worktrees", agent_system_repo),
        ("git_work_skills", "work-skills worktrees", work_skills_repo),
    ):
        git_args = ["git", "-C", str(repo_path), "worktree", "list", "--porcelain"]
        git_source = source(source_id, label, display_command(git_args))
        try:
            completed = runner.run(git_args)
            output = (completed.stdout or completed.stderr or "").strip()
            if completed.returncode:
                raise RuntimeError(output[:400] or f"exit {completed.returncode}")
            rows = parse_worktree_porcelain(output)
            git_source["item_count"] = len(rows)
            for row in rows:
                branch = row.get("branch") or "detached"
                report["git_worktrees"].append(
                    fact(
                        "git_worktree",
                        f"branch {branch}（Session 所有者未观察到）",
                        row.get("path") or "未观察到",
                        git_source["verify_command"],
                        repository=label.removesuffix(" worktrees"),
                        branch=branch,
                        head=row.get("head") or "未观察到",
                        detached=bool(row.get("detached")),
                        prunable=row.get("prunable", False),
                        caveat="登记的 worktree 不证明当前有 Session 在跑",
                    )
                )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError, RuntimeError) as error:
            unavailable(git_source, str(error))
        report["sources"].append(git_source)

    for repository in github_repositories:
        gh_args = [
            "gh",
            "pr",
            "list",
            "--repo",
            repository,
            "--state",
            "open",
            "--limit",
            "100",
            "--json",
            "number,title,headRefName,author,url,isDraft",
        ]
        gh_source = source(
            f"github_prs_{repository.replace('/', '_')}",
            f"{repository} open PRs",
            display_command(gh_args),
        )
        try:
            payload = run_json(runner, gh_args)
            if not isinstance(payload, list):
                raise RuntimeError("gh pr list root is not a list")
            rows = [row for row in payload if isinstance(row, dict)]
            gh_source["item_count"] = len(rows)
            for row in rows:
                author = row.get("author")
                login = author.get("login") if isinstance(author, dict) else None
                head = row.get("headRefName") or "未观察到"
                number = row.get("number") or "未观察到"
                report["open_pull_requests"].append(
                    fact(
                        "open_pull_request",
                        f"author {login or '未观察到'} / PR #{number}",
                        f"{repository}:{head}",
                        gh_source["verify_command"],
                        repository=repository,
                        number=number,
                        title=row.get("title") or "未观察到",
                        head_ref_name=head,
                        author=login or "未观察到",
                        url=row.get("url") or "未观察到",
                        is_draft=row.get("isDraft", "未观察到"),
                        caveat="开放 PR 证明远端分支存在，不单独证明作者 Session 仍在跑",
                    )
                )
        except RuntimeError as error:
            unavailable(gh_source, str(error))
        report["sources"].append(gh_source)

    report["summary"] = {
        "active_dispatch_count": len(report["active_dispatches"]),
        "sibling_dispatch_count": sum(
            row["observed"].get("relation") == "sibling"
            for row in report["active_dispatches"]
        ),
        "live_terminal_count": len(report["live_terminals"]),
        "orphaned_terminal_count": sum(
            row["observed"].get("orphaned") is True for row in report["live_terminals"]
        ),
        "git_worktree_count": len(report["git_worktrees"]),
        "open_pull_request_count": len(report["open_pull_requests"]),
        "unobserved_source_count": sum(
            row["status"] == "unobserved" for row in report["sources"]
        ),
        "partial_source_count": sum(row["status"] == "partial" for row in report["sources"]),
    }
    return report


def safe_text(value: Any) -> str:
    return " ".join(str(value).replace("`", "'").split())


def render_item(row: dict[str, Any], index: int) -> list[str]:
    return [
        f"{index}. 谁：{safe_text(row['who'])}",
        f"   写哪儿：{safe_text(row['write_where'])}",
        f"   怎么核实：`{safe_text(row['verify_command'])}`",
    ]


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# 本机兄弟 Session 事实",
        "",
        f"> 观察时刻：{report['observed_at']}｜当前终端：{safe_text(report['caller_terminal'])}",
        "> 这是只读瞬时观察，不是写入授权或所有权合同；需要行动前请运行每项给出的命令复核。",
        "",
        "## 非终态 Dispatch",
        "",
    ]
    if report["active_dispatches"]:
        for index, row in enumerate(report["active_dispatches"], start=1):
            relation = row["observed"].get("relation")
            suffix = "（当前调用者）" if relation == "self" else "（兄弟）" if relation == "sibling" else "（关系未观察到）"
            row = {**row, "who": row["who"] + suffix}
            lines.extend(render_item(row, index))
    else:
        lines.append("未观察到非终态 Dispatch。")

    lines.extend(["", "## 活终端", ""])
    if report["live_terminals"]:
        for index, row in enumerate(report["live_terminals"], start=1):
            orphaned = row["observed"].get("orphaned")
            suffix = "｜orphaned=true" if orphaned is True else "｜orphaned=false" if orphaned is False else "｜orphaned 未观察到"
            row = {**row, "who": row["who"] + suffix}
            lines.extend(render_item(row, index))
    else:
        lines.append("未观察到活终端。")

    lines.extend(["", "## D9 调度租约", ""])
    if report["scheduler_lease"]:
        lines.extend(render_item(report["scheduler_lease"][0], 1))
    else:
        lines.append("未观察到 D9 租约持有者。")

    lines.extend(["", "## Git worktree", "", "> 登记的 worktree 不证明当前有 Session 在跑。", ""])
    if report["git_worktrees"]:
        for index, row in enumerate(report["git_worktrees"], start=1):
            lines.extend(render_item(row, index))
    else:
        lines.append("未观察到 agent-control / work-skills worktree。")

    lines.extend(["", "## 三仓开放 PR", "", "> 开放 PR 证明远端分支存在，不单独证明作者 Session 仍在跑。", ""])
    if report["open_pull_requests"]:
        for index, row in enumerate(report["open_pull_requests"], start=1):
            lines.extend(render_item(row, index))
    else:
        lines.append("未观察到三仓开放 PR。")

    unavailable_sources = [
        row for row in report["sources"] if row["status"] in {"unobserved", "partial"}
    ]
    lines.extend(["", "## 采集状态", ""])
    if unavailable_sources:
        for row in unavailable_sources:
            label = "未观察到" if row["status"] == "unobserved" else "只观察到部分"
            lines.append(f"- {safe_text(row['label'])}：{label}；{safe_text(row['error'])}")
            lines.append(f"  - 核实：`{safe_text(row['verify_command'])}`")
    else:
        lines.append("全部配置的数据源均成功读取，且未报告截断。")

    lines.extend(
        [
            "",
            "## 摘要",
            "",
            f"- 非终态 Dispatch：{summary['active_dispatch_count']}（已识别兄弟 {summary['sibling_dispatch_count']}）",
            f"- 活终端：{summary['live_terminal_count']}（orphaned {summary['orphaned_terminal_count']}）",
            f"- Git worktree：{summary['git_worktree_count']}",
            f"- 三仓开放 PR：{summary['open_pull_request_count']}",
            f"- 未观察到的数据源：{summary['unobserved_source_count']}；部分数据源：{summary['partial_source_count']}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_parser() -> argparse.ArgumentParser:
    repository_root = Path(__file__).resolve().parents[2]
    local_app_data = os.environ.get("LOCALAPPDATA")
    default_lease = (
        Path(local_app_data) / "agent-system" / "scheduler-lease.json"
        if local_app_data
        else Path.home() / "AppData" / "Local" / "agent-system" / "scheduler-lease.json"
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit structured JSON instead of Markdown.")
    parser.add_argument("--orca-command", help="Orca executable; defaults to the current Orca guide resolution.")
    parser.add_argument("--agent-system-repo", type=Path, default=repository_root)
    parser.add_argument("--work-skills-repo", type=Path, default=Path.home() / "workspace" / "work-skills")
    parser.add_argument("--lease-path", type=Path, default=default_lease)
    parser.add_argument(
        "--github-repo",
        action="append",
        dest="github_repositories",
        help="GitHub repository to inspect for open PRs; repeatable. Defaults to the three Agent-system repos.",
    )
    parser.add_argument(
        "--self-terminal",
        default=os.environ.get("ORCA_TERMINAL_HANDLE"),
        help="Mark this terminal as the caller; defaults to ORCA_TERMINAL_HANDLE.",
    )
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.timeout_seconds <= 0:
        print("error: --timeout-seconds must be positive", file=sys.stderr)
        return 2
    try:
        orca_command = resolve_orca_command(args.orca_command)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    report = collect_report(
        SubprocessRunner(args.timeout_seconds),
        orca_command=orca_command,
        agent_system_repo=args.agent_system_repo.resolve(),
        work_skills_repo=args.work_skills_repo.resolve(),
        lease_path=args.lease_path.resolve(),
        github_repositories=args.github_repositories or DEFAULT_GITHUB_REPOSITORIES,
        self_terminal=args.self_terminal,
    )
    if args.json:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    else:
        sys.stdout.write(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
