#!/usr/bin/env python3
"""用于查看和使用显式 Agent 能力 profile 的 CLI。"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

def _discover_project_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for candidate in (current, *current.parents):
        if (candidate / ".cap" / "manifest.toml").is_file():
            return candidate
    return current


DEFAULT_PROJECT = (
    Path(os.environ["CAP_PROJECT"]).expanduser()
    if "CAP_PROJECT" in os.environ
    else _discover_project_root(Path.cwd())
)


def _default_profile_tool() -> Path:
    configured = os.environ.get("AGENT_CONTROL_PROFILE_TOOL")
    if configured:
        return Path(configured)
    bundled = Path(__file__).resolve().parent / "profile" / "profile.py"
    if bundled.is_file():
        return bundled
    return Path("profile.py")


DEFAULT_PROFILE_TOOL = _default_profile_tool()
DEFAULT_PROFILE = "assembly-helper"
CLIENTS = ("codex", "qoder", "omp")
DEFAULT_CLI = "omp"
AMBIENT_CONFIG_ENV = {
    "CODEX_HOME",
    "OMP_PROFILE",
    "PI_CODING_AGENT_DIR",
    "PI_CONFIG_DIR",
    "PI_CONFIG_FILES",
    "PI_PROFILE",
    "QODER_CONFIG_DIR",
    "QODER_WORKING_DIR",
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cap",
        description="查看和使用显式 Agent profile；默认使用隔离且持久的 agent home，避免继承真实 HOME 的隐式能力。",
        epilog=(
            "常用示例：\n"
            "  cap agents\n"
            "  cap show assembly-helper\n"
            "  cap clients\n"
            "  cap interactive\n"
            "  cap use assembly-helper\n"
            "  cap use assembly-helper -- --version\n"
            "  cap run assembly-helper -- -p \"帮我装配一个 review-agent\"\n"
            "  cap render assembly-helper --output /tmp/rendered-cap\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--project",
        default=str(DEFAULT_PROJECT),
        metavar="目录",
        help="profile 项目根目录；默认从当前目录向上寻找 .cap/manifest.toml",
    )
    parser.add_argument(
        "--home",
        default=argparse.SUPPRESS,
        metavar="目录",
        help="用于校验和渲染的 clean HOME；默认是 <project>.clean-home",
    )
    parser.add_argument(
        "--agent-home-root",
        default=argparse.SUPPRESS,
        metavar="目录",
        help="持久 agent home 根目录；默认是 <project>.agent-homes",
    )
    parser.add_argument(
        "--employee-root",
        dest="agent_home_root",
        default=argparse.SUPPRESS,
        metavar="目录",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--profile-tool",
        default=str(DEFAULT_PROFILE_TOOL),
        metavar="文件",
        help="agent-control 的 tools/profile/profile.py 路径",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        metavar="命令",
        title="命令",
        description="查看 profile，或选择 profile 与 CLI 来使用。",
    )

    agents = subparsers.add_parser(
        "agents",
        help="查看可用 agent",
        description="查看当前项目声明的全部 agent。",
    )
    agents.set_defaults(profile_tool_command="agents")

    profiles = subparsers.add_parser(
        "profiles",
        aliases=("list",),
        help="查看可用 profile（底层格式名）",
        description="查看当前项目声明的全部 profile。",
    )
    profiles.set_defaults(profile_tool_command="list")

    clients = subparsers.add_parser(
        "clients",
        help="查看客户端 CLI 解析路径",
        description="查看 codex、qoder、omp 在当前 PATH 中解析到哪个可执行文件及其版本输出。",
    )
    clients.set_defaults(profile_tool_command="clients")

    interactive = subparsers.add_parser(
        "interactive",
        aliases=("i",),
        help="交互式选择 profile、CLI 和动作",
        description="通过提示选择 profile、目标 CLI，以及交互启动、批处理运行或渲染。",
    )
    interactive.set_defaults(profile_tool_command="interactive")

    show = subparsers.add_parser(
        "show",
        aliases=("explain",),
        help="查看一个 profile 的能力闭包",
        description="查看 profile 的 prompt、skills、MCP、hooks、plugins 与各 CLI 渲染 hash。",
    )
    show.add_argument("profile", nargs="?", default=DEFAULT_PROFILE, help="profile 名；默认 assembly-helper")
    show.set_defaults(profile_tool_command="explain")

    use = subparsers.add_parser(
        "use",
        aliases=("launch",),
        help="使用 profile 启动一个 CLI",
        description="选择 profile 和目标 CLI，在当前工作目录中用持久 agent home 启动交互式客户端。",
    )
    use.add_argument("profile", nargs="?", default=DEFAULT_PROFILE, help="profile 名；默认 assembly-helper")
    use.add_argument("--cli", default=DEFAULT_CLI, choices=CLIENTS, help="要启动的客户端 CLI；默认 omp")
    use.add_argument(
        "--receipt",
        default=None,
        metavar="文件",
        help="启动收据路径；默认 <project>.runs/<profile>-<cli>-<时间戳>.receipt.json",
    )
    use.add_argument(
        "--workdir",
        default=None,
        metavar="目录",
        help="客户端工作目录；默认当前目录",
    )
    use.add_argument(
        "--fresh",
        action="store_true",
        help="使用一次性临时 runtime；默认 OMP 使用持久 agent home",
    )
    use.set_defaults(profile_tool_command="launch")

    run = subparsers.add_parser(
        "run",
        help="使用 profile 执行一次批处理命令",
        description="选择 profile 和目标 CLI，在当前工作目录中执行一次 batch 命令并记录 state；必须在 -- 后提供客户端命令参数。",
    )
    run.add_argument("profile", nargs="?", default=DEFAULT_PROFILE, help="profile 名；默认 assembly-helper")
    run.add_argument("--cli", default=DEFAULT_CLI, choices=CLIENTS, help="要运行的客户端 CLI；默认 omp")
    run.add_argument(
        "--state",
        default=None,
        metavar="目录",
        help="观察 state 目录；默认 <project>.runs/<profile>-<cli>-<时间戳>.state",
    )
    run.add_argument(
        "--workdir",
        default=None,
        metavar="目录",
        help="客户端工作目录；默认当前目录",
    )
    run.add_argument(
        "--fresh",
        action="store_true",
        help="使用一次性临时 runtime；默认 OMP 使用持久 agent home",
    )
    run.set_defaults(profile_tool_command="run")

    render = subparsers.add_parser(
        "render",
        aliases=("materialize",),
        help="渲染 profile，不启动 CLI",
        description="把 profile 渲染到指定空目录，用于检查目标 CLI 会看到的配置。",
    )
    render.add_argument("profile", nargs="?", default=DEFAULT_PROFILE, help="profile 名；默认 assembly-helper")
    render.add_argument("--cli", default=DEFAULT_CLI, choices=CLIENTS, help="要渲染的客户端 CLI；默认 omp")
    render.add_argument("--output", required=True, metavar="目录", help="已存在且为空的输出目录")
    render.set_defaults(profile_tool_command="materialize")

    lock = subparsers.add_parser(
        "lock",
        help="刷新 .cap/lock.json",
        description="重新计算 profile 声明、能力文件和三端渲染 hash，并写入 lock。",
    )
    lock.set_defaults(profile_tool_command="lock")

    verify = subparsers.add_parser(
        "verify",
        help="校验 lock 和能力闭包",
        description="校验当前声明、能力闭包和 lock 是否一致。",
    )
    verify.set_defaults(profile_tool_command="verify")

    return parser


def _base_args(args: argparse.Namespace) -> list[str]:
    return [
        sys.executable,
        str(Path(args.profile_tool).expanduser()),
        "--project",
        str(Path(args.project).expanduser()),
    ]


def _run_path(args: argparse.Namespace, suffix: str) -> str:
    root = Path(args.project).expanduser()
    run_dir = root.with_name(f"{root.name}.runs")
    run_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return str(run_dir / f"{args.profile}-{args.cli}-{stamp}-{os.getpid()}-{time.time_ns()}.{suffix}")


def _workdir(args: argparse.Namespace) -> Path:
    return (Path(args.workdir).expanduser() if args.workdir else Path.cwd()).resolve(strict=True)

def _apply_project_defaults(args: argparse.Namespace) -> None:
    project = Path(args.project).expanduser()
    if not hasattr(args, "home"):
        args.home = str(project.with_name(f"{project.name}.clean-home"))
    if not hasattr(args, "agent_home_root"):
        args.agent_home_root = str(project.with_name(f"{project.name}.agent-homes"))



def _agent_home_dir(args: argparse.Namespace) -> Path:
    return Path(args.agent_home_root).expanduser() / args.profile / args.cli


def _passthrough(values: list[str]) -> list[str]:
    return values


def _profile_args(args: argparse.Namespace) -> list[str]:
    base = _base_args(args)
    command = args.profile_tool_command
    if command in {"list", "lock", "verify"}:
        return [*base, command]
    if command == "explain":
        return [*base, "explain", "--profile", args.profile]
    if command == "materialize":
        return [
            *base,
            "materialize",
            "--client",
            args.cli,
            "--profile",
            args.profile,
            "--output",
            args.output,
        ]
    if command == "launch":
        receipt = Path(args.receipt).expanduser() if args.receipt else Path(
            _run_path(args, "receipt.json")
        )
        receipt.parent.mkdir(parents=True, exist_ok=True)
        return [
            *base,
            "launch",
            "--client",
            args.cli,
            "--profile",
            args.profile,
            "--receipt",
            str(receipt),
            "--workdir",
            str(_workdir(args)),
            "--",
            *_passthrough(args.client_args),
        ]
    if command == "run":
        state = args.state or _run_path(args, "state")
        Path(state).mkdir(parents=True, exist_ok=True)
        return [
            *base,
            "run",
            "--client",
            args.cli,
            "--profile",
            args.profile,
            "--state",
            state,
            "--workdir",
            str(_workdir(args)),
            "--",
            *_passthrough(args.client_args),
        ]
    raise AssertionError(f"unsupported command: {command}")


def _migrate_default_agent_home_root(args: argparse.Namespace) -> None:
    project = Path(args.project).expanduser()
    target = Path(args.agent_home_root).expanduser()
    default_target = project.with_name(f"{project.name}.agent-homes")
    if target != default_target:
        return
    legacy = project.with_name(f"{project.name}.employees")
    if legacy.exists() and not target.exists():
        shutil.move(str(legacy), str(target))


def _client_inventory() -> dict[str, object]:
    clients: dict[str, object] = {}
    for name in CLIENTS:
        resolved = shutil.which(name)
        version: dict[str, object] = {"exit_code": None, "output": None}
        if resolved:
            try:
                completed = subprocess.run(
                    [resolved, "--version"],
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=5,
                )
                version = {
                    "exit_code": completed.returncode,
                    "output": (completed.stdout + completed.stderr).strip(),
                }
            except (OSError, subprocess.TimeoutExpired) as error:
                version = {"exit_code": None, "output": str(error)}
        clients[name] = {"path": resolved, "version": version}
    return {"clients": clients}


def _available_profiles(args: argparse.Namespace, env: dict[str, str]) -> list[str]:
    completed = subprocess.run(
        [
            sys.executable,
            str(Path(args.profile_tool).expanduser()),
            "--project",
            str(Path(args.project).expanduser()),
            "list",
        ],
        capture_output=True,
        check=False,
        env=env,
        text=True,
    )
    if completed.returncode != 0:
        print(completed.stderr.strip() or completed.stdout.strip(), file=sys.stderr)
        return []
    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        print(f"无法解析 profile 列表：{error}", file=sys.stderr)
        return []
    profiles = data.get("profiles", [])
    return [item for item in profiles if isinstance(item, str)]


def _choose(label: str, choices: list[str], default: str) -> str:
    print(f"\n选择 {label}：")
    for index, choice in enumerate(choices, start=1):
        marker = " [默认]" if choice == default else ""
        print(f"  {index}. {choice}{marker}")
    while True:
        raw = input(f"{label} [{default}]: ").strip()
        if not raw:
            return default
        if raw.isdigit():
            offset = int(raw) - 1
            if 0 <= offset < len(choices):
                return choices[offset]
        if raw in choices:
            return raw
        print(f"无效选择：{raw}")


def _interactive(args: argparse.Namespace, env: dict[str, str]) -> int:
    profiles = _available_profiles(args, env)
    if not profiles:
        print("没有可用 profile。", file=sys.stderr)
        return 2
    profile_default = DEFAULT_PROFILE if DEFAULT_PROFILE in profiles else profiles[0]
    profile = _choose("profile", profiles, profile_default)
    cli = _choose("CLI", list(CLIENTS), DEFAULT_CLI)
    action = _choose("动作", ["use", "run", "render"], "use")

    args.profile = profile
    args.cli = cli
    args.receipt = None
    args.state = None
    args.workdir = None
    args.output = None
    args.fresh = False
    if action == "render":
        output = input("渲染输出目录（必须是已存在空目录）: ").strip()
        if not output:
            print("render 需要输出目录。", file=sys.stderr)
            return 2
        args.output = output
        args.profile_tool_command = "materialize"
    else:
        extra = input("客户端参数（可空；例如 --version；run 必填）: ").strip()
        args.client_args = shlex.split(extra) if extra else []
        if action == "run" and not args.client_args:
            print("run 需要客户端 batch 参数。", file=sys.stderr)
            return 2
        args.profile_tool_command = "launch" if action == "use" else "run"

    return _run_selected(args, env)


def _render_for_agent_home(args: argparse.Namespace, env: dict[str, str], agent_home: Path) -> str:
    agent_home.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"cap-render-{args.profile}-{args.cli}-") as temporary:
        completed = subprocess.run(
            [
                *_base_args(args),
                "materialize",
                "--client",
                args.cli,
                "--profile",
                args.profile,
                "--output",
                temporary,
            ],
            capture_output=True,
            check=False,
            env=env,
            text=True,
        )
        if completed.returncode != 0:
            print(completed.stderr.strip() or completed.stdout.strip(), file=sys.stderr)
            raise SystemExit(completed.returncode)
        try:
            tree_hash = json.loads(completed.stdout).get("tree_hash", "unknown")
        except json.JSONDecodeError:
            tree_hash = "unknown"
        rendered = Path(temporary)
        rendered_snapshot = agent_home / ".cap-rendered"
        if rendered_snapshot.exists():
            shutil.rmtree(rendered_snapshot)
        rendered_snapshot.mkdir(parents=True, exist_ok=True)
        for file_name in ("config.yml", "mcp.json", "system-prompt.md"):
            source = rendered / file_name
            if source.is_file():
                shutil.copy2(source, rendered_snapshot / file_name)
                if file_name == "config.yml" and (agent_home / file_name).exists():
                    continue
                shutil.copy2(source, agent_home / file_name)
        skills_source = rendered / "skills"
        skills_snapshot = rendered_snapshot / "skills"
        if skills_snapshot.exists():
            shutil.rmtree(skills_snapshot)
        if skills_source.is_dir():
            shutil.copytree(skills_source, skills_snapshot)
        skills_target = agent_home / "skills"
        if skills_target.exists():
            shutil.rmtree(skills_target)
        if skills_source.is_dir():
            shutil.copytree(skills_source, skills_target)
        return str(tree_hash)


def _omp_command(agent_home: Path, forwarded: list[str]) -> list[str]:
    executable = shutil.which("omp") or "omp"
    prompt = (agent_home / "system-prompt.md").read_text(encoding="utf-8").strip() + "\n"
    skills_root = agent_home / "skills"
    skill_names = sorted(item.name for item in skills_root.iterdir() if item.is_dir()) if skills_root.is_dir() else []
    skill_args = ["--skills", ",".join(skill_names)] if skill_names else ["--no-skills"]
    return [
        executable,
        "--config",
        str(agent_home / "config.yml"),
        "--append-system-prompt",
        prompt,
        *skill_args,
        "--no-extensions",
        "--no-rules",
        *forwarded,
    ]


def _agent_home_env(base_env: dict[str, str], agent_home: Path) -> dict[str, str]:
    env = base_env.copy()
    for name in AMBIENT_CONFIG_ENV:
        env.pop(name, None)
    home = agent_home / "home"
    home.mkdir(parents=True, exist_ok=True)
    env.update(
        {
            "HOME": str(home),
            "OMP_PROFILE": "default",
            "PI_CODING_AGENT_DIR": str(agent_home),
            "PI_CONFIG_DIR": str(agent_home),
            "PI_CONFIG_FILES": str(agent_home / "config.yml"),
            "PI_PROFILE": "default",
        }
    )
    return env


def _write_receipt(args: argparse.Namespace, receipt: Path, return_code: int, tree_hash: str, agent_home: Path) -> None:
    payload = {
        "version": 1,
        "client": args.cli,
        "profile": args.profile,
        "exit_code": return_code,
        "persistent_agent_home": True,
        "agent_home": str(agent_home),
        "workdir": str(_workdir(args)),
        "output_tree_hash": tree_hash,
        "forwarded_argument_count": len(args.client_args),
    }
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_omp_agent_home(args: argparse.Namespace, env: dict[str, str]) -> int:
    agent_home = _agent_home_dir(args)
    tree_hash = _render_for_agent_home(args, env, agent_home)
    receipt = Path(args.receipt).expanduser() if getattr(args, "receipt", None) else Path(_run_path(args, "receipt.json"))
    completed = subprocess.run(
        _omp_command(agent_home, _passthrough(args.client_args)),
        cwd=str(_workdir(args)),
        env=_agent_home_env(env, agent_home),
        check=False,
    )
    _write_receipt(args, receipt, completed.returncode, tree_hash, agent_home)
    return completed.returncode if completed.returncode >= 0 else 128 + abs(completed.returncode)


def _run_selected(args: argparse.Namespace, env: dict[str, str]) -> int:
    if args.profile_tool_command in {"launch", "run"} and args.cli == "omp" and not args.fresh:
        return _run_omp_agent_home(args, env)
    completed = subprocess.run(_profile_args(args), env=env, check=False)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    passthrough: list[str] = []
    if "--" in raw_args:
        separator = raw_args.index("--")
        passthrough = raw_args[separator + 1 :]
        raw_args = raw_args[:separator]
    parser = _build_parser()
    if not raw_args:
        parser.print_help()
        return 0
    args = parser.parse_args(raw_args)
    if hasattr(args, "profile_tool_command") and args.profile_tool_command in {"launch", "run"}:
        args.client_args = passthrough
    _apply_project_defaults(args)
    _migrate_default_agent_home_root(args)
    clean_home = Path(args.home).expanduser()
    clean_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(clean_home)
    if getattr(args, "profile_tool_command", None) == "clients":
        print(json.dumps(_client_inventory(), ensure_ascii=False, indent=2))
        return 0
    if getattr(args, "profile_tool_command", None) == "agents":
        print(json.dumps({"agents": _available_profiles(args, env)}, ensure_ascii=False, indent=2))
        return 0
    if getattr(args, "profile_tool_command", None) == "interactive":
        return _interactive(args, env)
    if getattr(args, "profile_tool_command", None) == "run" and not args.client_args:
        print(
            "cap run 需要在 -- 后提供客户端 batch 参数；否则目标 CLI 可能进入交互/恢复等待，看起来像卡住。\n"
            "示例：cap run assembly-helper -- -p \"帮我装配一个 review-agent\"\n"
            "如果要交互式启动，请用：cap use assembly-helper",
            file=sys.stderr,
        )
        return 2
    return _run_selected(args, env)


if __name__ == "__main__":
    raise SystemExit(main())
