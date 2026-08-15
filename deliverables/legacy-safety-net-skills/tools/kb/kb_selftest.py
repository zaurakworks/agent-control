#!/usr/bin/env python3
"""kb.py 的可重复自验(旁车轨+嵌入轨双轨)。

在临时目录里搭「中央库 + 假 worktree」,验证:
  旁车轨(*.kb.md 软链):
    1. sync 首跑建链、二跑幂等跳过;
    2. 冲突(实体文件占位/链接指向别处)只报告不覆盖;
    3. 软链之下在代码旁编辑=直接写中央库真本(collect 不需要存在);
    4. snapshot 产生提交、无变化不重复提交、并发覆盖可从历史恢复;
    5. collect 子命令确实不存在。
  嵌入轨([KB] 注释路牌):
    6. filter-clean 剥标记行、filter-smudge 显式 no-op 透传;
    7. filter-install 装配 .git/config + .git/info/attributes 并 check-attr 校验、幂等;
    8. 装配后 git 对 [KB] 注释失明:暂存 blob 已剥、工作区保留、commit 后 status 干净;
    9. harvest 收割进中央库 notes.json(锚点=方法签名),按文件整体替换;
   10. sync 显式注入:锚点上方按缩进注回、可重跑幂等、找不到锚点报错不乱插。

宿主不支持 symlink(如未开开发者模式的 Windows)时,软链相关项如实标
SKIP,其余项(含全部嵌入轨项)仍然验证。macOS/Linux 上应全部 PASS。
用法:python3 tools/kb/kb_selftest.py
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KB = HERE / "kb.py"
# 标记符拆写,避免本文件自身被 [KB] 兜底 grep 拦下(本仓可能被整包拷走)
MARKER = "[KB" "]"

results: list[tuple[str, str]] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    status = "PASS" if ok else "FAIL"
    results.append((name, status))
    print(f"{status} {name}" + (f" | {detail}" if detail and not ok else ""))


def skip(name: str, reason: str) -> None:
    results.append((name, "SKIP"))
    print(f"SKIP {name} | {reason}")


def sh(args: list[str], cwd: Path, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True,
                          input=stdin, text=stdin is None)


def git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return sh(["git", *args], cwd)


def kb(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return sh([sys.executable, str(KB), *args], cwd)


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="kb-selftest-"))
    print(f"selftest 工作目录:{tmp}")

    # 宿主 symlink 能力探测
    symlink_ok = True
    try:
        probe_src = tmp / "probe-src.txt"
        probe_src.write_text("probe", encoding="utf-8")
        os.symlink(probe_src, tmp / "probe-link.txt")
    except OSError:
        symlink_ok = False
        print("提示:宿主不支持创建 symlink,软链项将标 SKIP(Mac 上应全 PASS)")

    # 搭中央库
    central = tmp / "central"
    (central / "cards" / "demo-repo").mkdir(parents=True)
    card = central / "cards" / "demo-repo" / "free-rule.kb.md"
    card.write_text("# 坑卡:免邮判断在主模板\n- 触发条件:改免邮逻辑\n", encoding="utf-8")
    manifest = {
        "version": 1,
        "links": [
            {"repo": "demo-repo", "path": "src/calc/free-rule.kb.md",
             "card": "cards/demo-repo/free-rule.kb.md"},
            {"repo": "demo-repo", "path": "src/other/occupied.kb.md",
             "card": "cards/demo-repo/free-rule.kb.md"},
            {"repo": "another-repo", "path": "src/x/y.kb.md",
             "card": "cards/demo-repo/free-rule.kb.md"},
        ],
    }
    (central / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    git(["init", "-q"], central)
    git(["config", "user.email", "kb-selftest@example.com"], central)
    git(["config", "user.name", "kb-selftest"], central)

    # 搭假 worktree:一个占位实体文件制造冲突
    worktree = tmp / "demo-repo"
    (worktree / "src" / "calc").mkdir(parents=True)
    (worktree / "src" / "other").mkdir(parents=True)
    occupied = worktree / "src" / "other" / "occupied.kb.md"
    occupied.write_text("本地实体文件,不该被覆盖\n", encoding="utf-8")
    git(["init", "-q"], worktree)

    link_target = worktree / "src" / "calc" / "free-rule.kb.md"

    # 1+2. sync 首跑:建链一条,冲突一条(exit 1),另一仓条目不处理
    p1 = kb(["sync", "--central", str(central), "--repo", "demo-repo"], worktree)
    if symlink_ok:
        record("sync 首跑建链", link_target.is_symlink() and "[建链]" in p1.stdout)
        record("sync 首跑读穿软链取到真本内容",
               link_target.read_text(encoding="utf-8").startswith("# 坑卡:免邮判断在主模板"))
    else:
        skip("sync 首跑建链", "宿主无 symlink 权限")
        skip("sync 首跑读穿软链取到真本内容", "宿主无 symlink 权限")
    record("冲突路径只报告不覆盖", "[冲突]" in p1.stdout
           and occupied.read_text(encoding="utf-8") == "本地实体文件,不该被覆盖\n"
           and p1.returncode == 1, p1.stdout)
    record("其他仓条目不被处理", "another-repo" not in p1.stdout)

    # 1b. sync 二跑幂等
    p2 = kb(["sync", "--central", str(central), "--repo", "demo-repo"], worktree)
    if symlink_ok:
        record("sync 二跑幂等跳过", "已在场 1" in p2.stdout and "[建链]" not in p2.stdout, p2.stdout)
    else:
        skip("sync 二跑幂等跳过", "宿主无 symlink 权限")

    # 3. 软链下编辑=直接写中央库(collect 不需要存在)
    if symlink_ok:
        with open(link_target, "a", encoding="utf-8") as fh:
            fh.write("- 失效条件:免邮迁营销中心后作废\n")
        record("代码旁编辑直接落中央库真本",
               "失效条件" in card.read_text(encoding="utf-8"))
    else:
        card.write_text(card.read_text(encoding="utf-8")
                        + "- 失效条件:免邮迁营销中心后作废\n", encoding="utf-8")
        skip("代码旁编辑直接落中央库真本", "宿主无 symlink 权限,改为直接写真本以继续快照项")

    # 4. snapshot:产生提交/无变化不重复/历史可恢复
    s1 = kb(["snapshot", "--central", str(central)], tmp)
    record("snapshot 产生提交", s1.returncode == 0 and "快照完成" in s1.stdout, s1.stdout + s1.stderr)
    s2 = kb(["snapshot", "--central", str(central)], tmp)
    record("snapshot 无变化不重复提交", s2.returncode == 0 and "无变化" in s2.stdout, s2.stdout)

    good = card.read_text(encoding="utf-8")
    card.write_text("被并发覆盖坏掉的内容\n", encoding="utf-8")
    s3 = kb(["snapshot", "--central", str(central), "-m", "模拟并发覆盖"], tmp)
    rel = "cards/demo-repo/free-rule.kb.md"
    git(["checkout", "HEAD~1", "--", rel], central)
    record("并发覆盖可从历史恢复",
           s3.returncode == 0 and card.read_text(encoding="utf-8") == good)

    # 5. collect 子命令不存在
    c = kb(["collect"], tmp)
    record("collect 子命令不存在", c.returncode != 0)

    # ---------------- 嵌入轨([KB] 注释路牌) ----------------

    # 6. filter-clean / filter-smudge(纯 stdin→stdout,不需要 git)
    sample = f"a();\n// {MARKER} 路牌一\n  # {MARKER} 路牌二\nb();\n".encode("utf-8")
    fc = sh([sys.executable, str(KB), "filter-clean"], tmp, stdin=sample)
    record("filter-clean 剥掉所有含标记的行", fc.stdout == b"a();\nb();\n")
    fs = sh([sys.executable, str(KB), "filter-smudge"], tmp, stdin=sample)
    record("filter-smudge 显式 no-op 原样透传", fs.stdout == sample)

    # 搭嵌入轨热点仓
    hot = tmp / "hotdemo"
    (hot / "src").mkdir(parents=True)
    calc = hot / "src" / "Calc.java"
    signpost = f"// {MARKER} 坑:免邮只看主模板 → 见同目录 free-rule.kb.md"
    anchor = "public int calc(int w) {"
    calc.write_text(
        "public class Calc {\n"
        f"    {signpost}\n"
        f"    {anchor}\n"
        "        return w * 2;\n"
        "    }\n"
        "}\n", encoding="utf-8")
    git(["init", "-q"], hot)
    git(["config", "user.email", "kb-selftest@example.com"], hot)
    git(["config", "user.name", "kb-selftest"], hot)

    # 7. filter-install:装配+校验+幂等
    fi1 = kb(["filter-install", "src/Calc.java"], hot)
    clean_cfg = git(["config", "--get", "filter.kb.clean"], hot).stdout.strip()
    required_cfg = git(["config", "--get", "filter.kb.required"], hot).stdout.strip()
    attrs = hot / ".git" / "info" / "attributes"
    attr_lines = attrs.read_text(encoding="utf-8").splitlines() if attrs.is_file() else []
    record("filter-install 装配 config+attributes 并通过校验",
           fi1.returncode == 0 and "filter-clean" in clean_cfg and required_cfg == "true"
           and attr_lines.count("/src/Calc.java filter=kb") == 1,
           fi1.stdout + fi1.stderr)
    fi2 = kb(["filter-install", "src/Calc.java"], hot)
    attr_lines2 = attrs.read_text(encoding="utf-8").splitlines()
    record("filter-install 幂等不重复登记",
           fi2.returncode == 0 and attr_lines2.count("/src/Calc.java filter=kb") == 1)

    # 8. git 对 [KB] 失明:暂存 blob 已剥、工作区保留、commit 后 status 干净
    ga = git(["add", "src/Calc.java"], hot)
    staged = git(["show", ":src/Calc.java"], hot).stdout
    git(["commit", "-qm", "init"], hot)
    status = git(["status", "--porcelain"], hot).stdout.strip()
    record("clean 过滤器:暂存内容已剥标记(git 失明)",
           ga.returncode == 0 and MARKER not in staged and anchor in staged,
           staged)
    record("工作区保留标记且 commit 后 status 干净",
           MARKER in calc.read_text(encoding="utf-8") and status == "",
           status)

    # 9. harvest:收割进 notes.json(锚点=方法签名);按文件整体替换
    hv1 = kb(["harvest", "--central", str(central), "--repo", "hotdemo"], hot)
    notes = json.loads((central / "notes.json").read_text(encoding="utf-8"))["notes"]
    mine = [n for n in notes if n["repo"] == "hotdemo"]
    record("harvest 收割标记块且锚点=方法签名",
           hv1.returncode == 0 and len(mine) == 1
           and mine[0]["path"] == "src/Calc.java"
           and mine[0]["anchor"] == anchor
           and mine[0]["lines"] == [signpost],
           hv1.stdout + json.dumps(mine, ensure_ascii=False))
    calc.write_text(calc.read_text(encoding="utf-8").replace(f"    {signpost}\n", ""),
                    encoding="utf-8")
    kb(["harvest", "--central", str(central), "--repo", "hotdemo"], hot)
    notes2 = json.loads((central / "notes.json").read_text(encoding="utf-8"))["notes"]
    record("harvest 按文件整体替换(注释删除后旧条目清掉)",
           [n for n in notes2 if n["repo"] == "hotdemo"] == [])
    # 恢复路牌并重新收割,供注入项使用
    calc.write_text(calc.read_text(encoding="utf-8").replace(
        f"    {anchor}", f"    {signpost}\n    {anchor}"), encoding="utf-8")
    kb(["harvest", "--central", str(central), "--repo", "hotdemo"], hot)

    # 10. sync 显式注入:模拟干净 master 检出的新 worktree(无路牌)
    hot2 = tmp / "hotdemo2"
    (hot2 / "src").mkdir(parents=True)
    clean_text = ("public class Calc {\n"
                  f"    {anchor}\n"
                  "        return w * 2;\n"
                  "    }\n"
                  "}\n")
    (hot2 / "src" / "Calc.java").write_text(clean_text, encoding="utf-8")
    git(["init", "-q"], hot2)
    inj1 = kb(["sync", "--central", str(central), "--repo", "hotdemo"], hot2)
    injected_text = (hot2 / "src" / "Calc.java").read_text(encoding="utf-8")
    record("sync 显式注入:锚点上方按缩进注回",
           inj1.returncode == 0 and f"    {signpost}\n    {anchor}" in injected_text,
           inj1.stdout + injected_text)
    inj2 = kb(["sync", "--central", str(central), "--repo", "hotdemo"], hot2)
    record("sync 注入可重跑(已在场跳过)",
           inj2.returncode == 0 and "已在场 1" in inj2.stdout
           and injected_text == (hot2 / "src" / "Calc.java").read_text(encoding="utf-8"),
           inj2.stdout)
    (hot2 / "src" / "Calc.java").write_text(
        injected_text.replace(anchor, "public int calculate(int w) {"), encoding="utf-8")
    inj3 = kb(["sync", "--central", str(central), "--repo", "hotdemo"], hot2)
    record("找不到锚点报错不乱插(exit 1)",
           inj3.returncode == 1 and "找不到锚点" in inj3.stdout,
           inj3.stdout)

    print()
    fails = [n for n, s in results if s == "FAIL"]
    skips = [n for n, s in results if s == "SKIP"]
    print(f"汇总:{len(results)} 项,FAIL {len(fails)},SKIP {len(skips)}")
    if skips:
        print("SKIP 项(在 macOS 上重跑应全 PASS):", "; ".join(skips))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
