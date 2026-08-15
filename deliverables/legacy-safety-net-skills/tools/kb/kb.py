#!/usr/bin/env python3
"""kb — 知识资产物化器(Mac 软链版,双轨完整版)。

中央库 = 一个本地 git 仓,存两类真本:
  cards/…  + manifest.json   *.kb.md 卡片(旁车轨,主力)
  notes.json                 代码内 [KB] 注释路牌(嵌入轨,只给最热文件)

worktree 里的 *.kb.md 只是指向真本的 symlink;git 侧用 .git/info/exclude
单条 `**/*.kb.md` 排除。嵌入轨的 [KB] 注释由 clean 过滤器在入暂存时机械
剥离(git 对注释失明),由 `kb sync` 按方法签名锚点显式注回;smudge 不承担
注入(静默注入难调试),只装一个显式 no-op。pre-commit/pre-push 保险丝兜底
(见安装说明与 hooks/ 样例)。

子命令:
  sync            读中央库,幂等补建 *.kb.md 软链 + 显式注入 [KB] 注释
                  (锚点=方法签名邻近;找不到锚点报错不乱插;可重跑)。
  snapshot        中央库自动 git commit 一次;并发覆盖可从历史恢复。
  filter-install  给用户显式指定的热点文件装配并校验 clean/smudge 过滤器
                  (写 .git/config + .git/info/attributes,均本地、worktree
                  共享;不全仓开)。
  harvest         收割热点文件里的 [KB] 注释进中央库 notes.json(备份,
                  经 snapshot 版本化)。
  filter-clean    (供 git 调用)stdin→stdout,剥掉所有含 [KB] 标记的行。
  filter-smudge   (供 git 调用)显式 no-op,原样透传。

没有 collect:软链之下,在代码旁编辑就是直接写中央库真本,无需回收。
边界:kb 不做分支版本化——所有分支/worktree 链接同一真本;随分支不同
而不同的行为,应钉进该分支的测试/断言,不进 kb。
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MANIFEST_NAME = "manifest.json"
NOTES_NAME = "notes.json"
FILTER_NAME = "kb"
# 标记符拆写,避免本文件自身被 [KB] 兜底 grep 拦下(本仓可能被整包拷走)
MARKER = "[KB" "]"


def path_arg(value: str) -> Path:
    return Path(value).expanduser()


def default_central() -> Path:
    env = os.environ.get("KB_CENTRAL")
    return Path(env).expanduser() if env else Path.home() / "kb-central"


def run_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def detect_worktree_root() -> Path:
    p = run_git(["rev-parse", "--show-toplevel"], Path.cwd())
    if p.returncode != 0:
        sys.exit("错误:当前目录不在 git worktree 内(本命令需要在目标仓里运行)")
    return Path(p.stdout.strip())


def detect_common_dir(worktree: Path) -> Path:
    """共享 git 目录:linked worktree 下 config 与 info/ 都在这里,天然全 worktree 共享。"""
    p = run_git(["rev-parse", "--git-common-dir"], worktree)
    if p.returncode != 0:
        sys.exit("错误:读不到 git 公共目录")
    raw = Path(p.stdout.strip())
    return raw if raw.is_absolute() else (worktree / raw).resolve()


def detect_repo_name(worktree: Path) -> str:
    p = run_git(["remote", "get-url", "origin"], worktree)
    if p.returncode == 0 and p.stdout.strip():
        name = p.stdout.strip().rstrip("/").rsplit("/", 1)[-1]
        return name[:-4] if name.endswith(".git") else name
    return worktree.name


def load_manifest(central: Path) -> dict:
    manifest = central / MANIFEST_NAME
    if not manifest.is_file():
        sys.exit(f"错误:中央库清单不存在:{manifest}")
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"错误:{manifest} 不是合法 JSON:{exc}")
    if not isinstance(data.get("links"), list):
        sys.exit(f"错误:{manifest} 缺少 links 数组")
    return data


def load_notes(central: Path) -> dict:
    notes = central / NOTES_NAME
    if not notes.is_file():
        return {"version": 1, "notes": []}
    try:
        data = json.loads(notes.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"错误:{notes} 不是合法 JSON:{exc}")
    if not isinstance(data.get("notes"), list):
        sys.exit(f"错误:{notes} 缺少 notes 数组")
    return data


def save_notes(central: Path, data: dict) -> None:
    (central / NOTES_NAME).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def strip_kb_bytes(data: bytes) -> bytes:
    marker = MARKER.encode("utf-8")
    return b"".join(
        line for line in data.splitlines(keepends=True) if marker not in line)


# ---------------------------------------------------------------- sync

def sync_links(central: Path, worktree: Path, repo: str) -> tuple[int, int, int]:
    data = load_manifest(central)
    created = skipped = warned = 0
    for entry in data["links"]:
        if entry.get("repo") != repo:
            continue
        rel_path, card_rel = entry.get("path"), entry.get("card")
        if not rel_path or not card_rel:
            print(f"[警告] 清单条目缺 path/card 字段,跳过:{entry}")
            warned += 1
            continue
        card = (central / card_rel).resolve()
        target = worktree / rel_path
        if not card.is_file():
            print(f"[警告] 中央库真本缺失,跳过:{card}")
            warned += 1
            continue
        if target.is_symlink():
            current = Path(os.readlink(target))
            if not current.is_absolute():
                current = target.parent / current
            if current.resolve() == card:
                skipped += 1
                continue
            print(f"[冲突] 已有链接指向别处,不动:{target} -> {current}")
            warned += 1
            continue
        if target.exists():
            print(f"[冲突] 路径上已有实体文件,不覆盖(真本应在中央库):{target}")
            warned += 1
            continue
        if not target.parent.is_dir():
            print(f"[警告] 代码目录不存在(代码搬家了?清单待更新):{target.parent}")
            warned += 1
            continue
        try:
            os.symlink(card, target)
        except OSError as exc:
            print(f"[错误] 创建 symlink 失败:{target}({exc})")
            print("       本工具面向 macOS 等原生支持软链的系统;Windows 需开发者模式/管理员权限。")
            warned += 1
            continue
        print(f"[建链] {target} -> {card}")
        created += 1
    return created, skipped, warned


def inject_notes(central: Path, worktree: Path, repo: str) -> tuple[int, int, int]:
    """按方法签名锚点把 [KB] 注释注回热点文件。显式、幂等、找不到锚点报错不乱插。"""
    data = load_notes(central)
    injected = present = errors = 0
    for note in data["notes"]:
        if note.get("repo") != repo:
            continue
        rel_path, anchor = note.get("path"), note.get("anchor")
        note_lines = note.get("lines") or []
        target = worktree / (rel_path or "")
        if not rel_path or not note_lines:
            print(f"[错误] notes 条目缺 path/lines,不注入:{note}")
            errors += 1
            continue
        if not target.is_file():
            print(f"[错误] 注入目标文件不存在(代码搬家了?):{target}")
            errors += 1
            continue
        if not anchor:
            print(f"[错误] 条目没有锚点(收割时块后没有代码行),无法注入:{rel_path}")
            errors += 1
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"[错误] 非 UTF-8 文件,不注入:{target}")
            errors += 1
            continue
        lines = text.splitlines(keepends=True)
        matches = [i for i, l in enumerate(lines) if l.strip() == anchor]
        if not matches:
            print(f"[错误] 找不到锚点(方法签名改了?先 kb harvest 或手工搬卡):{rel_path} :: {anchor}")
            errors += 1
            continue
        if len(matches) > 1:
            print(f"[错误] 锚点不唯一({len(matches)} 处),不注入:{rel_path} :: {anchor}")
            errors += 1
            continue
        idx = matches[0]
        n = len(note_lines)
        above = [l.strip() for l in lines[idx - n:idx]] if idx >= n else []
        if above == note_lines:
            present += 1
            continue
        anchor_line = lines[idx]
        indent = anchor_line[: len(anchor_line) - len(anchor_line.lstrip())]
        eol = "\r\n" if anchor_line.rstrip("\r\n") != anchor_line.rstrip("\n") else "\n"
        lines[idx:idx] = [indent + c + eol for c in note_lines]
        target.write_text("".join(lines), encoding="utf-8")
        print(f"[注入] {rel_path} :: {anchor}({n} 行)")
        injected += 1
    return injected, present, errors


def cmd_sync(args: argparse.Namespace) -> int:
    central = args.central.resolve()
    worktree = detect_worktree_root()
    repo = args.repo or detect_repo_name(worktree)
    created, skipped, warned = sync_links(central, worktree, repo)
    injected, present, errors = inject_notes(central, worktree, repo)
    print(f"sync 完成(repo={repo}):软链 新建 {created}/已在场 {skipped}/警告 {warned};"
          f"[KB] 注入 {injected}/已在场 {present}/锚点等错误 {errors}")
    return 1 if (warned or errors) else 0


# ---------------------------------------------------------------- snapshot

def cmd_snapshot(args: argparse.Namespace) -> int:
    central = args.central.resolve()
    if run_git(["rev-parse", "--git-dir"], central).returncode != 0:
        sys.exit(f"错误:中央库不是 git 仓:{central}(先 git -C \"{central}\" init)")
    run_git(["add", "-A"], central)
    if not run_git(["status", "--porcelain"], central).stdout.strip():
        print("无变化,不产生新快照")
        return 0
    message = args.message or f"kb snapshot {datetime.now().isoformat(timespec='seconds')}"
    p = run_git(["commit", "-m", message], central)
    if p.returncode != 0:
        sys.exit(f"错误:commit 失败:\n{p.stderr}")
    head = run_git(["rev-parse", "--short", "HEAD"], central).stdout.strip()
    print(f"快照完成:{head} {message}")
    print("恢复某张卡:git -C <中央库> log --oneline -- <卡路径>;git -C <中央库> checkout <提交> -- <卡路径>")
    return 0


# ---------------------------------------------------------------- filter

def cmd_filter_clean(_args: argparse.Namespace) -> int:
    sys.stdout.buffer.write(strip_kb_bytes(sys.stdin.buffer.read()))
    return 0


def cmd_filter_smudge(_args: argparse.Namespace) -> int:
    # 显式 no-op:smudge 不承担注入(静默注入难调试);注入走 kb sync。
    sys.stdout.buffer.write(sys.stdin.buffer.read())
    return 0


def rel_to_worktree(raw: str, worktree: Path) -> Path:
    p = Path(raw).expanduser()
    abs_p = p.resolve() if p.is_absolute() else (Path.cwd() / p).resolve()
    try:
        return abs_p.relative_to(worktree)
    except ValueError:
        sys.exit(f"错误:{raw} 不在当前仓内({worktree})")


def cmd_filter_install(args: argparse.Namespace) -> int:
    worktree = detect_worktree_root()
    common = detect_common_dir(worktree)
    kb_path = Path(__file__).resolve()
    py = Path(sys.executable)
    clean_cmd = f'"{py.as_posix()}" "{kb_path.as_posix()}" filter-clean'
    smudge_cmd = f'"{py.as_posix()}" "{kb_path.as_posix()}" filter-smudge'

    # 1) 装配 .git/config(--local 写入公共 config,全 worktree 共享)
    for key, val in ((f"filter.{FILTER_NAME}.clean", clean_cmd),
                     (f"filter.{FILTER_NAME}.smudge", smudge_cmd),
                     (f"filter.{FILTER_NAME}.required", "true")):
        p = run_git(["config", "--local", key, val], worktree)
        if p.returncode != 0:
            sys.exit(f"错误:写 git config 失败:{key}\n{p.stderr}")

    # 2) 装配 .git/info/attributes:只对用户显式指定的热点文件生效,不全仓开
    attrs = common / "info" / "attributes"
    attrs.parent.mkdir(parents=True, exist_ok=True)
    existing = attrs.read_text(encoding="utf-8").splitlines() if attrs.is_file() else []
    rels: list[Path] = []
    added = skipped = 0
    for raw in args.paths:
        rel = rel_to_worktree(raw, worktree)
        if " " in str(rel):
            sys.exit(f"错误:attributes 模式不支持含空格路径:{rel}")
        rels.append(rel)
        line = f"/{rel.as_posix()} filter={FILTER_NAME}"
        if line in existing:
            skipped += 1
            continue
        existing.append(line)
        added += 1
    if added:
        attrs.write_text("\n".join(existing) + "\n", encoding="utf-8")

    # 3) 校验:属性真的生效 + clean 真的剥标记
    ok = True
    for rel in rels:
        p = run_git(["check-attr", "filter", "--", rel.as_posix()], worktree)
        if f"filter: {FILTER_NAME}" not in p.stdout:
            print(f"[校验失败] check-attr 未命中 filter={FILTER_NAME}:{rel.as_posix()}\n{p.stdout}")
            ok = False
    sample = f"code();\n// {MARKER} 样例路牌\nmore();\n".encode("utf-8")
    if strip_kb_bytes(sample) != b"code();\nmore();\n":
        print("[校验失败] clean 剥离逻辑异常")
        ok = False

    print(f"filter-install 完成:config 写入 filter.{FILTER_NAME}.clean/smudge/required,"
          f"attributes 新增 {added}/已有 {skipped}(共享于所有 worktree)")
    print(f"  clean = {clean_cmd}")
    print("  提示:过滤器只对装配后的新暂存生效;已在暂存/历史里的内容用 pre-commit/pre-push 保险丝兜底。")
    return 0 if ok else 1


# ---------------------------------------------------------------- harvest

def find_hotspots(worktree: Path, common: Path) -> list[str]:
    attrs = common / "info" / "attributes"
    if not attrs.is_file():
        return []
    pats = []
    for line in attrs.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 2 and f"filter={FILTER_NAME}" in parts[1:]:
            pats.append(parts[0].lstrip("/"))
    return pats


def extract_blocks(text: str) -> list[tuple[str | None, list[str]]]:
    """返回 [(锚点, 标记行列表)]:锚点=紧随 [KB] 块之后的第一个非空代码行(通常是方法签名)。"""
    lines = text.splitlines()
    blocks = []
    i = 0
    while i < len(lines):
        if MARKER not in lines[i]:
            i += 1
            continue
        j = i
        while j < len(lines) and MARKER in lines[j]:
            j += 1
        k = j
        while k < len(lines) and not lines[k].strip():
            k += 1
        anchor = lines[k].strip() if k < len(lines) else None
        blocks.append((anchor, [l.strip() for l in lines[i:j]]))
        i = j
    return blocks


def cmd_harvest(args: argparse.Namespace) -> int:
    central = args.central.resolve()
    if not central.is_dir():
        sys.exit(f"错误:中央库不存在:{central}")
    worktree = detect_worktree_root()
    common = detect_common_dir(worktree)
    repo = args.repo or detect_repo_name(worktree)
    if args.paths:
        rels = [rel_to_worktree(raw, worktree) for raw in args.paths]
    else:
        # attributes 里登记的热点是仓根相对路径,直接使用
        rels = [Path(pat) for pat in find_hotspots(worktree, common)]
    if not rels:
        sys.exit("错误:没有热点文件可收割——先 kb filter-install <文件>,或显式传路径")

    data = load_notes(central)
    harvested = warned = 0
    scanned_rels: list[str] = []
    new_notes = []
    for rel in rels:
        target = worktree / rel
        rel_posix = rel.as_posix()
        scanned_rels.append(rel_posix)
        if not target.is_file():
            print(f"[警告] 热点文件不存在,跳过:{target}")
            warned += 1
            continue
        try:
            text = target.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"[警告] 非 UTF-8 文件,跳过:{target}")
            warned += 1
            continue
        blocks = extract_blocks(text)
        anchors_seen: set[str] = set()
        for anchor, block_lines in blocks:
            if anchor is None:
                print(f"[警告] 文件尾的 {MARKER} 块没有后续代码行可锚定,收割但 sync 无法注回:{rel_posix}")
                warned += 1
            elif anchor in anchors_seen:
                print(f"[警告] 同文件出现重复锚点,注入时会报不唯一:{rel_posix} :: {anchor}")
                warned += 1
            if anchor is not None:
                anchors_seen.add(anchor)
            new_notes.append({"repo": repo, "path": rel_posix,
                              "anchor": anchor, "lines": block_lines})
            harvested += 1

    # 按文件整体替换:被扫描文件的旧条目清掉(删除也是变更;中央库经 snapshot 版本化,可恢复)
    kept = [n for n in data["notes"]
            if not (n.get("repo") == repo and n.get("path") in scanned_rels)]
    data["notes"] = kept + new_notes
    save_notes(central, data)
    print(f"harvest 完成(repo={repo}):扫描 {len(scanned_rels)} 文件,收割 {harvested} 块,警告 {warned}")
    print("  提示:跑一次 kb snapshot 把本次收割固化进中央库历史。")
    return 1 if warned else 0


# ---------------------------------------------------------------- main

def add_central_repo_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--central", type=path_arg, default=default_central(),
                   help="中央库路径(缺省 $KB_CENTRAL,再缺省 ~/kb-central)")
    p.add_argument("--repo", help="仓名(缺省取 origin URL 末段或仓目录名)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="kb",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_sync = sub.add_parser("sync", help="幂等补建 kb 软链 + 显式注入 [KB] 注释(锚点=方法签名)")
    add_central_repo_args(p_sync)
    p_sync.set_defaults(func=cmd_sync)

    p_snap = sub.add_parser("snapshot", help="中央库自动 commit 一次快照")
    p_snap.add_argument("--central", type=path_arg, default=default_central(),
                        help="中央库路径(缺省 $KB_CENTRAL,再缺省 ~/kb-central)")
    p_snap.add_argument("-m", "--message", help="快照说明(缺省带时间戳)")
    p_snap.set_defaults(func=cmd_snapshot)

    p_fi = sub.add_parser("filter-install",
                          help="给显式指定的热点文件装配并校验 clean/smudge 过滤器")
    p_fi.add_argument("paths", nargs="+", help="热点文件路径(只对这些文件生效,不全仓开)")
    p_fi.set_defaults(func=cmd_filter_install)

    p_hv = sub.add_parser("harvest", help="收割热点文件里的 [KB] 注释进中央库 notes.json")
    p_hv.add_argument("paths", nargs="*",
                      help="要收割的文件(缺省=info/attributes 里登记的全部热点文件)")
    add_central_repo_args(p_hv)
    p_hv.set_defaults(func=cmd_harvest)

    p_fc = sub.add_parser("filter-clean", help="(git 调用)剥掉 stdin 里含 [KB] 的行")
    p_fc.set_defaults(func=cmd_filter_clean)

    p_fs = sub.add_parser("filter-smudge", help="(git 调用)显式 no-op 透传")
    p_fs.set_defaults(func=cmd_filter_smudge)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
