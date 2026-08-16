"""profile — 把一个声明的 agent 状态物化成可运行的 home，跑完再比对实际生效态。

用法:
    python profile.py materialize <profile-dir>
    python profile.py probe       <profile-dir>              # 秒级，无模型调用
    python profile.py run         <profile-dir> --task <t.md>  # 分钟级，要 token
    python profile.py diff        <profile-dir>

设计要点:
  declared  = manifest.toml，进 git，可 diff 可 tag
  effective = 每次运行捕获，跟 declared 比对，抓漂移
只有 declared 是锁不住的；只有 effective 是没法回滚的。要两半。

两个量具，量的不是同一个东西，都要：
  probe = 配置面。CLI 只读子命令 + 文件系统。日常用这个。
  run   = 生效面。唯一能测到"运行时实际看得见什么"的仪器，贵，用于定期校准。
已实测的偏差方向：Claude 侧 probe 多报（看不到 --strict-mcp-config 的效果），
Codex 侧 probe 少报（内置 codex_apps 不进配置表）。差值本身是信号，不是噪声。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path


# tools/profile/profile.py -> tools/profile -> tools -> 仓库根
REPO = Path(__file__).resolve().parents[2]


def expand(s: str, home: Path | None = None) -> str:
    """展开 manifest 里的路径令牌。

    manifest 进 git，所以不能写死某台机器的绝对路径。
      <repo>      仓库根
      <skills>    skill 树（= <repo>/.claude/skills）
      <userhome>  真实用户目录。只在两处用到：播种凭据，以及声明那些
                  明确管不了、住在真实 home 里的东西。
      <home>      本次物化出来的 home —— 只有运行时才知道，所以要传进来。
    """
    s = (s.replace("<repo>", str(REPO))
          .replace("<skills>", str(REPO / ".claude" / "skills"))
          .replace("<userhome>", str(Path.home())))
    return s if home is None else s.replace("<home>", str(home))


def load_manifest(profile_dir: Path) -> dict:
    path = profile_dir / "manifest.toml"
    if not path.exists():
        sys.exit(f"没有 manifest: {path}")
    with path.open("rb") as fh:
        return tomllib.load(fh)


def gc_old_homes(homes_root: Path, keep: int = 3) -> None:
    """尽力清理旧的物化 home，保留最近 keep 个。

    删不掉就跳过 —— Windows 的句柄残留是常态，不该让 GC 失败挡住新的物化。
    这是"尽力"不是"保证"，所以不抛异常。
    """
    if not homes_root.exists():
        return
    dirs = sorted((d for d in homes_root.iterdir() if d.is_dir()), reverse=True)
    for old in dirs[keep:]:
        try:
            shutil.rmtree(old)
        except OSError:
            pass  # 有句柄占着，下次再说


def homes_root(profile_dir: Path, manifest: dict) -> Path:
    """物化 home 的根目录 —— 默认在仓库之外。

    两个理由，都不是洁癖：
      1. CLAUDE.md / AGENTS.md 按 cwd 及其祖先发现。home 放在仓库里，
         仓库根就是它的祖先，本仓那 12 KB 入口会进每一次运行的上下文。
      2. home 里有播种进去的凭据。放在仓库外，"不小心提交"这件事在物理上不可能，
         而不是靠一条 .gitignore 撑着。
    """
    root = manifest.get("homes", {}).get("root")
    if root:
        return Path(expand(root))
    base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".cache")
    return base / "agent-control-profiles" / profile_dir.name


def workdir_of(profile_dir: Path, manifest: dict, home: Path) -> Path:
    """agent 的工作目录。默认既不在仓库里，也不在物化 home 里。

    三个约束叠出来只剩这一个位置：
      1. 不能在仓库里 —— CLAUDE.md / AGENTS.md 按 cwd 及其祖先发现，
         仓库根一旦成为祖先，本仓那 12 KB 入口会进每一次运行的上下文。
      2. 不能是物化 home 本身 —— home 就是 CODEX_HOME，Codex 的 workspace-write
         沙箱拒绝 agent 往自己的配置目录写（实测 out.md 写入被拒，整轮无交付）。
      3. 得在 cwd 内 —— 同一个沙箱只放行 cwd 内的读写，任务文件也得拷进来。
    """
    spec = manifest.get("run", {}).get("workdir", "<work>")
    if spec != "<work>":
        return Path(expand(spec, home))
    return homes_root(profile_dir, manifest).parent / f"{profile_dir.name}-work"


def provider_of(manifest: dict) -> str:
    return manifest.get("model", {}).get("provider", "claude")


def write_codex_config(home: Path, manifest: dict) -> dict:
    """生成最小 config.toml。

    刻意不复制真实的 14 KB config.toml —— 那里面有内联 Authorization 头、
    MCP 定义和历史沉积。声明态就该是声明出来的，不是继承来的。
    """
    m = manifest.get("model", {})
    s = manifest.get("settings", {})
    cfg = {
        "model": m.get("id", "gpt-5.6-sol"),
        "sandbox_mode": s.get("sandboxMode", "workspace-write"),
        "network_access": s.get("networkAccess", True),
        "windows_sandbox": s.get("windowsSandbox", "unelevated"),
    }
    (home / "config.toml").write_text(
        f'model = "{cfg["model"]}"\n'
        f'sandbox_mode = "{cfg["sandbox_mode"]}"\n\n'
        f"[sandbox_workspace_write]\n"
        f'network_access = {"true" if cfg["network_access"] else "false"}\n\n'
        f"[windows]\n"
        f'sandbox = "{cfg["windows_sandbox"]}"\n',
        encoding="utf-8",
    )
    return cfg


def materialize(profile_dir: Path, manifest: dict) -> Path:
    """按 manifest 建一个干净的配置 home。每次全新重建，不做增量。

    claude → CLAUDE_CONFIG_DIR   codex → CODEX_HOME
    两者都是整个家目录重定向，所以白名单是物理的：不在名单里的 skill 根本不存在。
    """
    # 每次物化建一个带时间戳的新 home，不复用也不删旧的。
    #
    # 原因不是洁癖：Windows 上 CLI 建的 projects/ sessions/ 在进程退出后
    # 仍被短暂持有，rmtree 会以 WinError 145 失败（重试 4 次也没用）。
    # 时间戳目录让这个问题根本不出现，副作用是每次物化都成为独立可追溯的产物。
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    root = homes_root(profile_dir, manifest)
    home = root / stamp
    (home / "skills").mkdir(parents=True)
    gc_old_homes(root, keep=3)

    # 1. 白名单 skill —— 不在名单里的物理上不存在，比 skillOverrides 黑名单更强
    skills_cfg = manifest.get("skills", {})
    src_root = Path(expand(skills_cfg.get("source", "")))
    copied: list[str] = []
    for name in skills_cfg.get("allow", []):
        src = src_root / name
        if not src.is_dir():
            sys.exit(f"白名单里的 skill 不存在: {src}")
        shutil.copytree(src, home / "skills" / name)
        copied.append(name)

    # 2. 播种凭据 —— 显式列出，可审计
    seed = manifest.get("seed", {})
    seeded: list[str] = []
    if seed:
        seed_root = Path(expand(seed.get("from", "")))
        for rel in seed.get("files", []):
            src = seed_root / rel
            if not src.exists():
                sys.exit(f"要播种的文件不存在: {src}")
            shutil.copy2(src, home / rel)
            seeded.append(rel)

    # 3. provider 各自的配置文件
    s = manifest.get("settings", {})
    if provider_of(manifest) == "codex":
        settings = write_codex_config(home, manifest)
    else:
        settings = {
            "skillListingBudgetFraction": s.get("skillListingBudgetFraction", 0.02),
            "permissions": {"defaultMode": s.get("permissionsDefaultMode", "default")},
            "enabledPlugins": {p: True for p in manifest.get("plugins", {}).get("enabled", [])},
            # 内置 skill 在二进制里，白名单管不到；只能黑名单逐个关
            "skillOverrides": {k: "off" for k in manifest.get("skills", {}).get("deny", [])},
        }
        (home / "settings.json").write_text(
            json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    declared = {
        "profile": manifest["profile"],
        "provider": provider_of(manifest),
        "model": manifest.get("model", {}),
        "skills_allow": copied,
        "skills_deny": manifest.get("skills", {}).get("deny", []),
        # MCP 与上下文文件：这两个维度物化时无法强制，只能声明+事后比对。
        # 写出来是为了让"没管住"变成可见的漂移，而不是不可见的盲区。
        "mcp_allow": manifest.get("mcp", {}).get("allow", []),
        "context_allow": [expand(x, home) for x in manifest.get("context", {}).get("allow", [])],
        "plugins_enabled": manifest.get("plugins", {}).get("enabled", []),
        "seeded_files": seeded,
        "settings": settings,
        # 这个 profile 明确管不了的维度。假装管得了才是危险的。
        # 声明为管不了的东西也要展开：其中的路径同样不能写死这台机器
        "uncontrollable": {
            k: ([expand(x, home) for x in v] if k == "context" and isinstance(v, list) else v)
            for k, v in manifest.get("uncontrollable", {}).items()
        },
        "home": str(home),
        "materialized_at": datetime.now(timezone.utc).isoformat(),
    }
    (profile_dir / "declared.json").write_text(
        json.dumps(declared, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return home


def build_prompt_file(profile_dir: Path, manifest: dict) -> Path:
    """只拼锚点，走 --append-system-prompt-file，不过命令行。

    刻意**不**把阶段规则放进系统提示词：那会在 profile 里留一份副本，
    而副本会漂移 —— 上一版就是这样，profile/stage.md 比仓库里的
    references/observe.md 旧了一个版本，两份冲突的指令同时在上下文里。
    阶段规则的唯一来源是 skill，由锚点第 5 条按名触发加载。
    """
    p = manifest.get("prompt", {})
    parts = []
    for key in ("anchor",):
        rel = p.get(key)
        if not rel:
            continue
        # <skills> 指向 skill 树，让锚点也只有一份来源。
        # 之前 profiles/_shared/anchor.md 和 skill 里的 anchor.md 是两份逐字副本。
        f = (Path(expand(rel)) if "<" in rel else profile_dir / rel).resolve()
        if not f.exists():
            sys.exit(f"prompt 文件不存在: {f}")
        parts.append(f.read_text(encoding="utf-8"))
    out = profile_dir / "system-prompt.md"
    out.write_text("\n\n---\n\n".join(parts), encoding="utf-8")
    return out


def sh(cmd: list[str], env: dict, timeout: int = 90) -> str:
    """跑一个只读的 CLI 子命令。失败不抛——探针缺一项是 unknown，不是崩溃。"""
    try:
        p = subprocess.run(
            cmd, env=env, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
        )
        return (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.SubprocessError) as e:
        return f"__PROBE_FAILED__ {e}"


def probe_static(profile_dir: Path, manifest: dict, home: Path) -> dict:
    """不调模型，只问 CLI 和文件系统。秒级。

    这是日常该用的量具。跑 agent 问"你看得见什么"要几分钟和一堆 token，
    而且自报的标识符还不稳定（同一批连接器两次运行一次报 id 一次报显示名）。

    但静态探针和运行时**量的不是同一个东西**，两个方向都会错：
      - Claude: `mcp list` 不接受 --strict-mcp-config，会**多报**（配置面 ≠ 生效面）
      - Codex:  `mcp list` 看不见内置的 codex_apps，会**少报**
    所以 probe 不能取代 run，只能降低 run 的频率。差值本身是要看的信号。
    """
    provider = provider_of(manifest)
    env = dict(os.environ)
    env["CODEX_HOME" if provider == "codex" else "CLAUDE_CONFIG_DIR"] = str(home)

    # --- skill：磁盘可数，内置的数不到 ---
    skills_disk = sorted(
        p.name for p in (home / "skills").iterdir()
        if p.is_dir() and not p.name.startswith(".")
    ) if (home / "skills").exists() else []

    # --- MCP / plugin：CLI 子命令 ---
    if provider == "codex":
        mcp_raw, plug_raw = sh(["codex", "mcp", "list"], env), sh(["codex", "plugin", "list"], env)
    else:
        mcp_raw, plug_raw = sh(["claude", "mcp", "list"], env), sh(["claude", "plugin", "list"], env)

    def names(raw: str, empty_markers: tuple[str, ...]) -> list[str] | None:
        if raw.startswith("__PROBE_FAILED__"):
            return None
        if any(m in raw for m in empty_markers):
            return []
        out = []
        for line in raw.splitlines():
            s = line.strip()
            # 形如 "claude.ai Google Drive: https://… - ✔ Connected"
            if ":" in s and ("http" in s or " - " in s) and not s.startswith(("WARNING", "Checking")):
                out.append(s.split(":", 1)[0].strip())
        return sorted(set(out))

    mcp = names(mcp_raw, ("No MCP servers configured",))
    plugins = names(plug_raw, ("No plugins installed", "No marketplace plugins found"))

    # --- 上下文文件：按发现规则枚举候选，逐个测存在性 ---
    # 没有 CLI 能问（claude doctor 不含记忆路径），但规则是确定的，文件系统能答。
    memory = "AGENTS.md" if provider == "codex" else "CLAUDE.md"
    cands = [home / memory, Path.home() / (".codex" if provider == "codex" else ".claude") / memory]
    d = workdir_of(profile_dir, manifest, home)
    for _ in range(6):  # cwd 及其祖先
        cands.append(d / memory)
        if d.parent == d:
            break
        d = d.parent
    ctx = sorted({str(c) for c in cands if c.is_file()})

    probed = {
        "probed_at": datetime.now(timezone.utc).isoformat(),
        "home": str(home),
        "method": "静态：CLI 只读子命令 + 文件系统。无模型调用。",
        "skills_disk": skills_disk,
        "skills_builtin": "unknown —— 内置于 CLI 二进制，没有列举接口，只能靠 run 自报",
        "mcp_configured": mcp,
        "plugins": plugins,
        "context_candidates_present": ctx,
        "caveat": "配置面，非生效面。--strict-mcp-config 之类的运行期开关不体现在这里。",
    }
    (profile_dir / "probed.json").write_text(
        json.dumps(probed, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return probed


def probe(profile_dir: Path, manifest: dict) -> int:
    # 复用最近一次物化的 home，不重新物化。
    # 每次 probe 都新建一个 home，会让 declared 和 effective 指向不同的时间戳目录，
    # 上一次 run 的记录就整个报成漂移 —— probe 是只读量具，不该改变被测对象。
    homes = homes_root(profile_dir, manifest)
    existing = sorted((d for d in homes.iterdir() if d.is_dir()), reverse=True) if homes.exists() else []
    home = existing[0] if existing else materialize(profile_dir, manifest)
    p = probe_static(profile_dir, manifest, home)
    # probe 和 diff 必须认同一份声明，否则两个量具会给出矛盾的判断。
    u = manifest.get("uncontrollable", {})
    allow = set(manifest.get("skills", {}).get("allow", [])) | set(u.get("skills", []))
    mcp_allow = set(manifest.get("mcp", {}).get("allow", [])) | set(u.get("mcp", []))
    ctx_allow = {
        norm_path(expand(x, home))
        for x in list(manifest.get("context", {}).get("allow", [])) + list(u.get("context", []))
    }

    # 上一次 run 的自报，用来给静态候选定性。
    # 探针只能证明"文件在那儿"，证明不了"运行时加载了它" —— 两者差得很远：
    # ~/.codex/AGENTS.md 存在，但 CODEX_HOME 重定向后运行时根本不看它；
    # ~/.claude/CLAUDE.md 存在，且 CLAUDE_CONFIG_DIR 重定向后**仍然**加载。
    # 这个不对称只有 run 能测出来，probe 只能引用它。
    ef = profile_dir / "effective.json"
    confirmed = None
    if ef.exists():
        loaded = json.loads(ef.read_text(encoding="utf-8")).get("context_files")
        if loaded is not None:
            confirmed = {norm_path(x) for x in loaded}

    print(f"profile : {manifest['profile']['name']}@{manifest['profile']['version']}  ({p['method']})")
    rc = 0
    for label, observed, declared, by_path in (
        ("skill(磁盘)", p["skills_disk"], allow, False),
        ("MCP(配置面)", p["mcp_configured"], mcp_allow, False),
        ("上下文文件(候选)", p["context_candidates_present"], ctx_allow, True),
    ):
        if observed is None:
            print(f"  {label}: unknown（探针失败）")
            rc = max(rc, 2)
            continue
        key = norm_path if by_path else (lambda x: x)
        extra = sorted(x for x in observed if key(x) not in {key(y) for y in declared})
        # MCP 是运行期开关能拦的：配置面有，不代表生效面有。
        # probe 看不到 --strict-mcp-config 的效果，所以这里只能标注，不能判漂移。
        if label.startswith("MCP") and extra and manifest.get("mcp", {}).get("strict"):
            print(f"  {label}: {observed}  ⚠ 配置面有 {len(extra)} 个，"
                  f"但 strict=true 会在运行期全部拦掉（已由 run 确认为 []）")
            continue
        # 先分类再定表头。表头写 ❌ 而结论是通过，会让人信错一边。
        lines, worst = [], 0
        for x in extra:
            if not by_path:
                lines.append((x, "")); worst = max(worst, 1)
            elif confirmed is None:
                lines.append((x, "  ← 未确认（还没有 run 的自报可比）")); worst = max(worst, 2)
            elif norm_path(x) in confirmed:
                lines.append((x, "  ← 上次 run 确认已加载")); worst = max(worst, 1)
            else:
                lines.append((x, "  ← 候选存在，但上次 run 未加载它，不计漂移"))
        mark = {0: "✅", 1: f"❌ 越界 {len(extra)}", 2: f"? 未确认 {len(extra)}"}[worst]
        print(f"  {label}: {observed or '(空)'}  {mark}")
        for x, tag in lines:
            print(f"      + {x}{tag}")
        rc = max(rc, worst)
    print(f"  plugin: {p['plugins'] if p['plugins'] is not None else 'unknown'}")
    print(f"  内置 skill: {p['skills_builtin']}")
    print(f"\n注意: {p['caveat']}")
    return rc


def run(profile_dir: Path, manifest: dict, task: Path) -> int:
    home = materialize(profile_dir, manifest)
    sysprompt = build_prompt_file(profile_dir, manifest)

    env = dict(os.environ)
    provider = provider_of(manifest)
    model = manifest.get("model", {}).get("id", "sonnet")

    # 工作目录默认是物化 home，不是 profile 目录。
    # profile 目录住在仓库里，而 CLAUDE.md / AGENTS.md 是按 cwd 及其祖先发现的 ——
    # 用 profile 目录当 cwd，本仓那 12 KB 入口会进每一次运行的上下文，
    # 量具自己污染被测对象。需要在某个项目里干活的 profile 显式声明 workdir。
    workdir = workdir_of(profile_dir, manifest, home)
    workdir.mkdir(parents=True, exist_ok=True)

    # 任务文件拷进 workdir 再指过去，不指仓库里的原件。
    # Codex 的 workspace-write 沙箱只放行 cwd 内的读写：任务留在仓库里，
    # 三次读取尝试全部挂起无输出，agent 只能如实报 unknown，整轮观测作废。
    task_in_wd = workdir / "task.md"
    shutil.copy2(task, task_in_wd)
    pointer = f"Read {task_in_wd.as_posix()} and follow it exactly."

    if provider == "codex":
        # Codex 没有 --append-system-prompt，靠 CODEX_HOME/AGENTS.md 承载锚点
        env["CODEX_HOME"] = str(home)
        shutil.copy2(sysprompt, home / "AGENTS.md")
        cmd = [
            "codex", "exec", "-m", model,
            "-s", manifest.get("settings", {}).get("sandboxMode", "workspace-write"),
            "-c", "sandbox_workspace_write.network_access=true",
            "--skip-git-repo-check", pointer,
        ]
    else:
        env["CLAUDE_CONFIG_DIR"] = str(home)
        cmd = [
            "claude", "-p", pointer,
            "--append-system-prompt-file", str(sysprompt),
            "--model", model,
        ]
        # MCP 是能被机制拦的：--strict-mcp-config + 不给 --mcp-config = 一个都不加载。
        # 上一轮账号级连接器（claude.ai Google Drive）漏进来，是因为没关，不是关不掉。
        # 能拦的就拦，不要写进提示词。
        if manifest.get("mcp", {}).get("strict"):
            cmd.append("--strict-mcp-config")

    # 交付物先删。跑挂了留着旧的，解析器会拿上一轮的答案当本轮结果——
    # 那是最坏的一种失败：看起来通过了。
    artifact = workdir / "out.md"
    artifact.unlink(missing_ok=True)

    started = datetime.now(timezone.utc)
    proc = subprocess.run(
        cmd, env=env, cwd=str(workdir), capture_output=True, text=True, encoding="utf-8"
    )
    ended = datetime.now(timezone.utc)

    if artifact.exists():
        shutil.copy2(artifact, profile_dir / "out.md")  # homes/ 会被 GC，交付物要留下

    log = profile_dir / "last-run.log"
    log.write_text((proc.stdout or "") + "\n--- stderr ---\n" + (proc.stderr or ""), encoding="utf-8")

    # 三处都要看：
    #   stdout —— Claude 的最终消息
    #   stderr —— codex exec 把进度和文件写入回显送这里
    #   out.md —— 阶段合同要求交付物是文件，标记行写在交付物里而不是最终消息里，
    #             这是符合合同的行为；只解析 stdout 会把它整个漏掉（表现为 unknown）
    text = (proc.stdout or "") + "\n" + (proc.stderr or "")
    if artifact.exists():
        text += "\n" + artifact.read_text(encoding="utf-8", errors="replace")
    capture_effective(profile_dir, home, text, started, ended, proc.returncode, cmd)
    print(f"退出码 {proc.returncode}  耗时 {(ended - started).total_seconds():.0f}s  日志 {log}")
    return proc.returncode


def parse_reported(text: str, marker: str) -> list[str] | None:
    """从产出里抓 `SKILLS-AVAILABLE: a, b, c` 这类行。抓不到返回 None（= unknown）。

    None 和 [] 必须区分：None 是"没观测到"，[] 是"观测到确实为空"。
    把 None 当成 [] 正是上一版报假阴性的原因。
    """
    # 从后往前找。提示词模板里也有这个标记，而它总是出现在答案之前——
    # 取第一个匹配会读到模板（"逗号分隔的全部可用 skill 名"），不是答案。
    for line in reversed(text.splitlines()):
        s = line.strip().lstrip("+-").strip().strip("`").strip()
        if not s.upper().startswith(marker + ":"):
            continue
        body = s.split(":", 1)[1].strip().strip("`").strip()
        # 模板占位符的守卫：真答案不会长这样
        if any(t in body for t in ("逗号分隔", "name1", "<", "…", "...")):
            continue
        # agent 自己声明观测失败 —— 和"确实为空"必须分开
        if body.lower() in {"unknown", "未知"}:
            return None
        if body.lower() in {"none", "无", ""}:
            return []
        return [x.strip().strip("`") for x in body.split(",") if x.strip()]
    return None


_STAMP = re.compile(r"/homes/\d{8}t\d{6}z/")


def norm_path(p: str) -> str:
    """路径比对用的归一化。Windows 大小写不敏感，且反斜杠正斜杠混用。

    还要把物化 home 的时间戳折掉：homes/ 下每次物化一个新目录，
    declared 里记的是本次的，effective 里记的是那次运行的，两者本就不同。
    不折掉的话，任何一次重新物化都会让上一次运行的记录整个报成漂移 ——
    那是量具的坐标系问题，不是被测对象变了。
    """
    s = p.strip().strip("`").replace("\\", "/").rstrip("/").lower()
    return _STAMP.sub("/homes/<stamp>/", s)


# 三个受检维度。每个都是 (声明键, 运行时观测键, 中文名, 是否按路径比对)
DIMENSIONS = [
    ("skills_allow", "skills_available", "skill", False),
    ("mcp_allow", "mcp_available", "MCP", False),
    ("context_allow", "context_files", "上下文文件", True),
]


def capture_effective(profile_dir, home, stdout, started, ended, rc, cmd) -> None:
    """实际生效态。

    运行时可用清单只能由 agent 自报——磁盘证明不了它。
    磁盘只作辅助：它能证明"我放了什么进去"，证明不了"运行时看得见什么"。

    MCP 与上下文文件两个维度**只有自报这一个仪器**，没有任何磁盘旁证。
    证据等级因此低于 skill：skill 至少能跟 home/skills/ 交叉验证。
    """
    on_disk = sorted(p.name for p in (home / "skills").iterdir()) if (home / "skills").exists() else []

    effective = {
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "duration_s": round((ended - started).total_seconds()),
        "exit_code": rc,
        "command": cmd,
        "skills_on_disk": on_disk,                              # 辅助，非判据
        "skills_available": parse_reported(stdout, "SKILLS-AVAILABLE"),  # None = unknown
        "skills_loaded": parse_reported(stdout, "SKILLS-LOADED"),
        "mcp_available": parse_reported(stdout, "MCP-AVAILABLE"),
        "context_files": parse_reported(stdout, "CONTEXT-FILES"),
        "evidence": "agent 自报；MCP 与上下文文件无磁盘旁证",
    }
    (profile_dir / "effective.json").write_text(
        json.dumps(effective, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def diff(profile_dir: Path) -> int:
    d = profile_dir / "declared.json"
    e = profile_dir / "effective.json"
    if not d.exists() or not e.exists():
        sys.exit("先跑一次 run，才有 declared / effective 可比")
    declared = json.loads(d.read_text(encoding="utf-8"))
    effective = json.loads(e.read_text(encoding="utf-8"))

    problems: list[str] = []
    unknowns: list[str] = []
    blind = False  # 有任何一个维度观测不到，整体结论就不能是"无漂移"

    print(f"profile   : {declared['profile']['name']}@{declared['profile']['version']}")
    print(f"provider  : {declared.get('provider')}   模型: {declared['model'].get('id')}")

    for allow_key, obs_key, label, by_path in DIMENSIONS:
        allow = declared.get(allow_key, [])
        unctl = declared.get("uncontrollable", {}).get(allow_key.replace("_allow", ""), [])
        observed = effective.get(obs_key)

        key = norm_path if by_path else (lambda x: x.strip())
        ok = {key(x) for x in list(allow) + list(unctl)}

        print(f"\n[{label}]")
        print(f"  声明允许  : {sorted(allow) or '(空)'}")
        print(f"  声明不可控: {sorted(unctl) or '(未声明)'}")
        print(f"  运行时观测: {observed if observed is not None else 'unknown'}")

        if observed is None:
            blind = True
            unknowns.append(f"{label}: unknown —— 产出里没有对应标记行。**不能据此判定无漂移**")
            continue
        extra = sorted(x for x in observed if key(x) not in ok)
        if extra:
            problems.append(f"{label} 越界 ({len(extra)}): {extra}")
        expected_unctl = sorted(x for x in observed if key(x) in {key(u) for u in unctl})
        if expected_unctl:
            unknowns.append(f"{label} 已声明为不可控、按预期出现: {expected_unctl}")

    print(f"\nskill 实际加载: {effective.get('skills_loaded') if effective.get('skills_loaded') is not None else 'unknown'}")
    print(f"skill 落盘(辅助): {effective['skills_on_disk']}")
    print(f"耗时: {effective['duration_s']}s   证据: {effective.get('evidence', 'agent 自报')}")

    if effective["exit_code"] != 0:
        problems.append(f"退出码非零: {effective['exit_code']}")

    if unknowns:
        print("\n未知:")
        for u in unknowns:
            print(f"  ? {u}")
    if problems:
        print("\n漂移:")
        for p in problems:
            print(f"  - {p}")
        return 1
    if blind:
        print("\n结论: 无法判定（有维度观测不足）")
        return 2
    print("\n三个维度均无漂移 ✅")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["materialize", "probe", "run", "diff"])
    ap.add_argument("profile_dir", type=Path)
    ap.add_argument("--task", type=Path)
    args = ap.parse_args()

    pd = args.profile_dir.resolve()
    if args.cmd == "diff":
        return diff(pd)

    manifest = load_manifest(pd)
    if args.cmd == "probe":
        return probe(pd, manifest)
    if args.cmd == "materialize":
        home = materialize(pd, manifest)
        print(f"已物化: {home}")
        return 0

    if not args.task:
        sys.exit("run 需要 --task")
    return run(pd, manifest, args.task)


if __name__ == "__main__":
    raise SystemExit(main())
