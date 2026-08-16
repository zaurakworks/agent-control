#!/usr/bin/env python3
"""静态验证联邦式 Session 入口、在线续接与跨 Session 负责人交互合同。"""

from __future__ import annotations

import argparse
import os
import json
import re
import subprocess
import sys
from pathlib import Path

from entry_sync import (
    EntrySyncError,
    compare_contents,
    find_markdown_section,
    generate_target,
    iter_targets,
    load_config,
)


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
MIGRATION_SOURCE_COMMIT = "fcfba814de4ac0e31480fe0d7ac5e715478d5b2c"  # 仅用于原始索引文本比对，不再用于 git show
PROHIBITED_SCRIPT_SUFFIXES = {
    ".ps1",
    ".psm1",
    ".psd1",
    ".bat",
    ".cmd",
    ".sh",
    ".bash",
    ".zsh",
}
RECEIPT_SCHEMA = "agent-control.federated-entry-validation-receipt"
RECEIPT_VERSION = 1
CONTINUATION_SECTION_MAX_CHARACTERS = 1200
CONTINUATION_FORBIDDEN_WORKFLOW_DETAILS = (
    "最多形成",
    "最多同时存在",
    "把观察分为四类",
    "形成可执行子 Issue",
    "准入条件必须同时成立",
    "第六节第 5 步",
    "终止状态",
)
GLOBAL_WAVE_SECTION_MAX_CHARACTERS = 700
CONTINUATION_BACKREFERENCE = "./entrypoints/agent-system.md#在线续接与负责人事项"
GLOBAL_WAVE_BACKREFERENCE = "./entrypoints/agent-system.md#持有-issue-时扩大并行波次"
LANGUAGE_BACKREFERENCE = "./entrypoints/agent-system.md#持久实现语言"

passes: list[str] = []
failures: list[str] = []
check_results: list[dict[str, bool | str]] = []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="静态验证联邦式 Session 入口、在线续接与跨 Session 负责人交互合同。"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="只输出机器可读的版本化 JSON 回执。",
    )
    return parser.parse_args()


def add_check_result(condition: bool, description: str) -> None:
    check_results.append({"ok": condition, "description": description})
    (passes if condition else failures).append(description)


def get_repository_text(relative_path: str) -> str:
    path = REPOSITORY_ROOT / relative_path
    exists = path.is_file()
    add_check_result(exists, f"{relative_path} 存在")
    if not exists:
        return ""
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeError as error:
        add_check_result(False, f"{relative_path} 可读取为 UTF-8；错误：{error}")
    except OSError as error:
        add_check_result(False, f"{relative_path} 可读取；错误：{error}")
    return ""


def git_failure_detail(process: subprocess.CompletedProcess[bytes]) -> str:
    detail = process.stderr.decode("utf-8", errors="replace").strip()
    return detail or f"退出码 {process.returncode}"


def run_git(arguments: list[str]) -> subprocess.CompletedProcess[bytes]:
    command = ["git", "-C", str(REPOSITORY_ROOT), *arguments]
    try:
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as error:
        return subprocess.CompletedProcess(
            command,
            returncode=127,
            stdout=b"",
            stderr=str(error).encode("utf-8", errors="replace"),
        )


def test_contains_all(text: str, patterns: list[str], description: str) -> None:
    missing = [pattern for pattern in patterns if pattern not in text]
    if missing:
        add_check_result(False, f"{description}；缺少：{'、'.join(missing)}")
    else:
        add_check_result(True, description)


def extract_markdown_section(text: str, heading: str) -> str:
    try:
        return find_markdown_section(text, heading, 2).text.strip()
    except EntrySyncError:
        return ""


def extract_markdown_subsection(text: str, heading: str) -> str:
    try:
        return find_markdown_section(text, heading, 3).text.strip()
    except EntrySyncError:
        return ""


def test_local_markdown_links(relative_paths: list[str]) -> None:
    link_pattern = re.compile(r"\[[^\]]+\]\((?P<target>[^)]+)\)")
    for relative_path in relative_paths:
        path = REPOSITORY_ROOT / relative_path
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeError as error:
            add_check_result(False, f"{relative_path} 的本地链接可读取为 UTF-8；错误：{error}")
            continue
        except OSError as error:
            add_check_result(False, f"{relative_path} 的本地链接可读取；错误：{error}")
            continue
        for match in link_pattern.finditer(text):
            target = match.group("target").strip("<>")
            if re.match(r"^(https?://|mailto:|#)", target):
                continue
            path_part = target.split("#", 1)[0]
            if not path_part.strip():
                continue
            resolved = (path.parent / path_part).resolve()
            add_check_result(
                resolved.exists(),
                f"{relative_path} 的本地链接存在：{target}",
            )


readme = get_repository_text("README.md")
system_entry = get_repository_text("entrypoints/agent-system.md")
agents_entry = get_repository_text("AGENTS.md")
claude_entry = get_repository_text("CLAUDE.md")
current = get_repository_text("work/current.md")
collaboration_authority = get_repository_text("authority/04-collaboration.md")
thinking_authority = get_repository_text("authority/03-thinking-methods.md")
ledger_authority = get_repository_text("authority/10-operating-ledger.md")
authority_map = get_repository_text("authority/00-map.md")
record = get_repository_text(
    "work/records/2026-08-10-federated-session-entry/record.md"
)
raw_current = get_repository_text(
    "work/records/2026-08-10-federated-session-entry/raw/"
    "current-before-migration.md"
)
raw_index = get_repository_text(
    "work/records/2026-08-10-federated-session-entry/raw/index.md"
)

try:
    entry_sync_config = load_config()
except EntrySyncError as error:
    entry_sync_config = None
    add_check_result(False, f"入口同步声明式配置可加载；错误：{error}")
else:
    add_check_result(True, "入口同步声明式配置可加载")
    for entry_target in iter_targets(entry_sync_config, "repository"):
        target_id = entry_target["id"]
        try:
            generated_target = generate_target(
                REPOSITORY_ROOT,
                entry_sync_config,
                entry_target,
                REPOSITORY_ROOT / "build" / "entry-sync",
            )
            current_target = generated_target.current_path.read_bytes().decode("utf-8")
            target_comparison = compare_contents(
                generated_target.content,
                current_target,
                expected_name=f"generated/{target_id}",
                actual_name=str(generated_target.current_path),
            )
        except (EntrySyncError, OSError, UnicodeError) as error:
            add_check_result(
                False,
                f"{target_id} 的声明式投影与单一真源一致；错误：{error}",
            )
        else:
            add_check_result(
                target_comparison.matches,
                (
                    f"{target_id} 的声明式投影与单一真源一致"
                    if target_comparison.matches
                    else (
                        f"{target_id} 的声明式投影与单一真源一致；"
                        f"差异：\n{target_comparison.diff}"
                    )
                ),
            )

    # installed 目标已从声明式配置中移除：用户级入口不再是版本化正文的投影。
    # 守护它们的不变量改由下面的反向断言承担。
    add_check_result(
        not list(iter_targets(entry_sync_config, "installed")),
        "声明式配置不再把用户级入口当作版本化正文的投影",
    )


# 用户级入口的反向断言，两个 Provider 都要守。
#
# 原先这里断言用户级入口是版本化正文的指针 —— 那等于让本仓正文对这台机器上
# 每一个会话生效，包括与本仓无关的项目。入口下沉到仓库级之后，要守的不变量
# 正好相反：用户级只放与任务无关的锚点，本仓正文不得进全局面。
#
# Claude 的 @import 会把正文内联展开，Codex 的指针只是一句"去读它" —— 常驻的
# token 量差很多，但作用域问题同类，所以两边用同一条断言。
#
# 按平台限定而非按文件存在性跳过：存在性判断会把本机上真实的漂移掩盖成"不适用"。
INSTALLED_ENTRIES = [
    ("Claude", Path.home() / ".claude" / "CLAUDE.md"),
    ("Codex", Path.home() / ".codex" / "AGENTS.md"),
]
if os.name == "nt":
    for provider_name, installed_path in INSTALLED_ENTRIES:
        if not installed_path.is_file():
            add_check_result(False, f"用户级 {provider_name} 入口存在：{installed_path}")
            continue
        installed_text = installed_path.read_text(encoding="utf-8", errors="replace")
        leaks = [
            marker
            for marker in ("entrypoints/agent-system.md", "entrypoints\agent-system.md")
            if marker in installed_text
        ]
        add_check_result(
            not leaks,
            f"用户级 {provider_name} 入口不把版本化正文拉进全局面"
            if not leaks
            else f"用户级 {provider_name} 入口不把版本化正文拉进全局面；发现引用："
            + "、".join(leaks),
        )
else:
    add_check_result(
        True,
        "用户级入口检查在非 Windows 环境不适用（本机专属，需在 Windows 上运行）",
    )

routing_patterns = [
    "没有明确 Issue",
    "父 Issue",
    "叶子 Issue",
    "github-collaboration:issue-workflow",
    "未满足",
    "就绪",
]

test_contains_all(
    readme,
    routing_patterns,
    "README 覆盖无 Issue／父 Issue／叶子 Issue 三种模式",
)
test_contains_all(
    system_entry,
    routing_patterns,
    "版本化系统入口覆盖三种模式并使用固定 Skill 接口",
)
test_contains_all(
    agents_entry,
    ["github-collaboration:issue-workflow", "Issue 合同", "写入所有权"],
    "Codex 仓库入口与联邦式路由一致",
)
readme_continuation_section = extract_markdown_section(
    readme, "在线续接与负责人事项"
)
system_continuation_section = extract_markdown_section(
    system_entry, "在线续接与负责人事项"
)
agents_continuation_section = extract_markdown_section(
    agents_entry, "在线续接与负责人事项"
)
for entry_name, continuation_section in [
    ("仓库 README", readme_continuation_section),
    ("版本化系统入口", system_continuation_section),
    ("Codex／Claude 仓库入口", agents_continuation_section),
]:
    add_check_result(
        len(continuation_section) <= CONTINUATION_SECTION_MAX_CHARACTERS,
        (
            f"{entry_name}：在线续接章节保持短（实际 {len(continuation_section)} 字符，"
            f"上限 {CONTINUATION_SECTION_MAX_CHARACTERS} 字符）"
        ),
    )
    copied_workflow_details = [
        detail
        for detail in CONTINUATION_FORBIDDEN_WORKFLOW_DETAILS
        if detail in continuation_section
    ]
    add_check_result(
        not copied_workflow_details,
        (
            f"{entry_name}：在线续接章节不复制 Skill 内部限流／生命周期细节"
            if not copied_workflow_details
            else (
                f"{entry_name}：在线续接章节不复制 Skill 内部限流／生命周期细节；"
                f"发现：{'、'.join(copied_workflow_details)}"
            )
        ),
    )

test_contains_all(
    system_continuation_section,
    [
        "明确、开放且已授权父 Issue 未满足成功条件",
        "具体缺口时，加载 `github-collaboration:issue-workflow`",
        "不自动启动，也不扫描队列找活",
        "新建一个 Session 与恢复一个已有但当前空闲的 Session 是等价入口",
        "不得沿用旧聊天记忆",
        "Project 只作观察面",
        "不是默认审批入口",
        "缺少 L3 离线唤醒",
    ],
    "版本化系统入口保留在线续接的触发、恢复、决定与离线边界",
)
for entry_name, continuation_section in [
    ("README", readme_continuation_section),
    ("AGENTS", agents_continuation_section),
]:
    test_contains_all(
        continuation_section,
        [CONTINUATION_BACKREFERENCE],
        f"{entry_name} 的在线续接章节回指唯一版本化正文",
    )
add_check_result(
    bool(system_continuation_section)
    and readme_continuation_section == agents_continuation_section
    and system_continuation_section != readme_continuation_section,
    "README 与 AGENTS 只保留在线续接最短回指，版本化入口独占正文",
)
readme_global_wave_section = extract_markdown_subsection(
    readme, "持有 Issue 时扩大并行波次"
)
system_global_wave_section = extract_markdown_subsection(
    system_entry, "持有 Issue 时扩大并行波次"
)
agents_global_wave_section = extract_markdown_subsection(
    agents_entry, "持有 Issue 时扩大并行波次"
)
for entry_name, global_wave_section in [
    ("仓库 README", readme_global_wave_section),
    ("版本化系统入口", system_global_wave_section),
    ("Codex／Claude 仓库入口", agents_global_wave_section),
]:
    add_check_result(
        len(global_wave_section) <= GLOBAL_WAVE_SECTION_MAX_CHARACTERS,
        (
            f"{entry_name}：扩大并行波次章节保持短（实际 {len(global_wave_section)} 字符，"
            f"上限 {GLOBAL_WAVE_SECTION_MAX_CHARACTERS} 字符）"
        ),
    )
add_check_result(
    bool(system_global_wave_section),
    "版本化系统入口包含扩大并行波次正文",
)
test_contains_all(
    system_global_wave_section,
    [
        "只有负责人要求扩大当前并发面",
        "经营总账权威与远端观察面",
        "写入所有权仍限于原 Issue 子树",
        "普通进度询问和当前 Issue 内选择下一切片不触发全局枚举",
        "同一阶段没有新证据时不重复扫描",
        "不自动建 Issue、派发或修改 Project",
    ],
    "版本化系统入口保留扩大并行波次的触发、所有权与禁用边界",
)
global_wave_contradictions = [
    phrase
    for phrase in ["即使只问当前 PR 进度", "可以顺便扫描全局", "直接派发"]
    if phrase in system_global_wave_section
]
add_check_result(
    not global_wave_contradictions,
    "版本化系统入口的扩大并行波次正文不含反向放宽"
    if not global_wave_contradictions
    else "版本化系统入口的扩大并行波次正文不含反向放宽；发现："
    + "、".join(global_wave_contradictions),
)
for entry_name, global_wave_section in [
    ("README", readme_global_wave_section),
    ("AGENTS", agents_global_wave_section),
]:
    test_contains_all(
        global_wave_section,
        [GLOBAL_WAVE_BACKREFERENCE],
        f"{entry_name} 的扩大并行波次章节回指唯一版本化正文",
    )
add_check_result(
    readme_global_wave_section == agents_global_wave_section
    and system_global_wave_section != readme_global_wave_section,
    "README 与 AGENTS 只保留扩大并行波次最短回指，版本化入口独占正文",
)
claude_entry_lines = [line.strip() for line in claude_entry.strip().splitlines() if line.strip()]
add_check_result(
    claude_entry_lines == ["@AGENTS.md", "@entrypoints/agent-system.md"],
    "Claude 真实仓库入口继续导入同一 AGENTS.md"
    if claude_entry_lines == ["@AGENTS.md", "@entrypoints/agent-system.md"]
    else "Claude 真实仓库入口继续导入同一 AGENTS.md；实际："
    + "、".join(claude_entry_lines or ["(空)"]),
)

effective_entries = [
    ("普通／Orca Codex", f"{system_entry}\n{agents_entry}\n{readme}"),
    ("Claude", f"{system_entry}\n{agents_entry}\n{readme}"),
]
scenario_contracts = [
    (
        "明确叶子 Issue",
        ["有明确 Issue", "叶子 Issue", "github-collaboration:issue-workflow", "端到端交付"],
    ),
    (
        "父 Issue 局部协调",
        ["父 Issue", "github-collaboration:issue-workflow", "协调自己的子树"],
    ),
    (
        "无 Issue 选择下一项工作",
        ["没有明确 Issue", "经营总账", "adaptive-problem-solving", "有界 Issue"],
    ),
]
for entry_name, entry_text in effective_entries:
    for scenario_name, patterns in scenario_contracts:
        test_contains_all(
            entry_text,
            patterns,
            f"{entry_name} 静态走读：{scenario_name}",
        )

test_contains_all(
    system_entry,
    [
        "Issue 是持久任务合同，不是最高权威",
        "当前权威",
        "负责人更新的明确指令",
        "有效协作派发",
    ],
    "入口不会把 Issue 升格到权威和负责人新指令之上",
)
test_contains_all(
    system_entry,
    ["只冻结依赖被推翻假设", "有独立合同和所有权的安全工作继续"],
    "纠偏采用局部冻结而不是整体停工",
)

language_rule_patterns = [
    "持久维护的程序、CLI、自动化和验证脚本",
    "Go",
    "Python",
    "TypeScript",
    "Rust",
    "PowerShell",
    "Batch",
    "Shell",
    "不得以当前是否",
    "安装",
    "排除理由",
]
global_language_scope_patterns = [
    "这台电脑",
    "Codex",
    "Claude Code",
    "所有仓库、Provider、Session 和 worktree",
    "仓库入口",
    "触发条件",
    "不授权",
    "批量重写",
]
test_contains_all(system_entry, language_rule_patterns, "版本化入口包含全局脚本语言规则")
for scope_name, scope_text in [
    ("版本化系统入口", system_entry),
    ("仓库 README", readme),
    ("可读研发记录", record),
]:
    test_contains_all(
        scope_text,
        global_language_scope_patterns,
        f"{scope_name} 明确语言规则的机器级全局作用域与非批量重写边界",
    )
system_language_section = extract_markdown_section(system_entry, "持久实现语言")
agents_language_section = extract_markdown_section(agents_entry, "持久实现语言")
test_contains_all(
    system_language_section,
    language_rule_patterns + global_language_scope_patterns,
    "机器级作用域与语言边界位于同一版本化入口章节",
)
add_check_result(
    bool(system_language_section)
    and LANGUAGE_BACKREFERENCE in agents_language_section
    and system_language_section != agents_language_section,
    "AGENTS 的持久实现语言章节只回指唯一版本化正文",
)
test_contains_all(
    authority_map,
    ["[`entrypoints/agent-system.md`](../entrypoints/agent-system.md)", "唯一版本化正文", "本总图不复制"],
    "权威总图回指机器级持久实现语言与常驻规则的唯一版本化正文",
)
add_check_result(
    system_entry.find("## 持久实现语言")
    < system_entry.find("当任务涉及 Agent 系统"),
    "机器级语言规则位于 Agent 系统任务条件之前",
)
test_contains_all(
    readme,
    ["机器级持久实现语言", "Go", "Python", "TypeScript", "Rust", "一次性命令"],
    "仓库入口可发现脚本语言规则",
)

required_current_headings = [
    "## 主线入口",
    "## 各来源 observedAt 水位",
    "## unresolved-conflict",
]
test_contains_all(current, required_current_headings, "current 只保留指针壳的三部分")
test_contains_all(
    current,
    [
        "本文件是恢复指针，不是状态权威",
        "github.com/zaurakworks/agent-control/issues/22",  # 迁仓后：老 #44 → 新 #22
        "observedAt",
    ],
    "current 声明指针壳定位、主线入口与来源水位",
)
forbidden_current_patterns = [
    "## 当前主线",
    "## 活动并行事项",
    "## 活动协调与共享写入所有权",
    "## 最新授权与边界变化",
    "## 下一检查点",
    "## 当前任务可读取的权威与记录",
    "term_",
]
present_forbidden = [
    pattern for pattern in forbidden_current_patterns if pattern in current
]
add_check_result(
    not present_forbidden,
    "current 不再承载状态、授权与执行者标识"
    if not present_forbidden
    else f"current 仍含已降级内容：{'、'.join(present_forbidden)}",
)

current_line_count = len(current.splitlines())
add_check_result(
    current_line_count <= 30,
    f"current 保持指针壳（实际 {current_line_count} 行，上限 30 行）",
)
current_byte_count = len(current.encode("utf-8"))
add_check_result(
    current_byte_count <= 1200,
    f"current 保持紧凑（实际 {current_byte_count} 字节，上限 1200 字节）",
)

historical_headings = [
    "## 并行资源实验的原始问题",
    "## 2026-08-10 负责人纠偏",
    "## 当前证据与下一检查点",
]
leaked_headings = [heading for heading in historical_headings if heading in current]
if leaked_headings:
    add_check_result(
        False,
        f"current 不再承载长篇历史章节；残留：{'、'.join(leaked_headings)}",
    )
else:
    add_check_result(True, "current 不再承载长篇历史章节")

test_contains_all(
    record,
    [
        "原始主线",
        "资源观测与并发实验",
        "负责人纠正及被替代判断",
        "方案演变",
        "迁移完整性映射",
        "授权与不做事项的来由",
        "持久脚本语言的全局纠正",
        "合并前发现的作用域缩窄",
        "所有仓库、Provider、Session 和 worktree",
    ],
    "可读研发记录覆盖迁移前因果历史和最新语言纠正",
)
test_contains_all(
    raw_index,
    [
        "S01｜迁移前",
        MIGRATION_SOURCE_COMMIT,
        "run_8f829c43983e",
        "task_7453a1e6b730",
        "ctx_4bfaa4a38dbe",
        "msg_6f7a25bce52d",
        "task_2b4478780c1a",
        "ctx_5266427014cb",
    ],
    "原始索引保留 Git、GitHub 与 Orca 来源链",
)

# 迁移基线校验已删除：该检查依赖原仓提交 fcfba814（clean-slate 迁仓后按设计不存在），
# 且其一次性目的（校验迁移前后 current 逐字一致）在原仓已完成。按入口「制度自清洁」
# 第 6 条，已证实错误的路径连同专属兼容说明一起删，不加例外或 fallback。

test_contains_all(
    collaboration_authority,
    [
        "联邦式 Session 入口的后续确认",
        "github-collaboration:issue-workflow",
        "不保留永久协调者身份",
    ],
    "协作权威记录联邦式模型及能力边界",
)
test_contains_all(
    authority_map,
    [
        "[`04-collaboration.md`](./04-collaboration.md)",
        "多 Agent／多 Session 协作产品模型",
    ],
    "权威总图把联邦式协作边界路由到协作权威",
)
test_contains_all(
    thinking_authority,
    ["最小实验与最小完整交付的后续澄清", "负责人注意力", "不能为了最小 diff"],
    "思考方法权威区分最小实验与最小完整交付",
)
test_contains_all(
    ledger_authority,
    ["“就绪”子集为空", "未满足／部分满足诉求", "adaptive-problem-solving", "不扩大当前授权"],
    "经营总账权威保留空队列返回诉求的窄路由",
)

git_files = run_git(
    [
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
    ],
)
git_files_description = "可以枚举仓库持久与待提交文件"
add_check_result(
    git_files.returncode == 0,
    git_files_description
    if git_files.returncode == 0
    else f"{git_files_description}；Git 错误：{git_failure_detail(git_files)}",
)
if git_files.returncode == 0:
    try:
        repository_files = [
            item
            for item in git_files.stdout.decode("utf-8").split("\0")
            if item
        ]
    except UnicodeError as error:
        add_check_result(False, f"Git 文件列表可读取为 UTF-8；错误：{error}")
    else:
        prohibited_scripts = sorted(
            item
            for item in repository_files
            if Path(item).suffix.lower() in PROHIBITED_SCRIPT_SUFFIXES
        )
        add_check_result(
            not prohibited_scripts,
            "仓库未沉淀 PowerShell、Batch 或 Shell 脚本"
            if not prohibited_scripts
            else f"仓库存在禁用脚本：{'、'.join(prohibited_scripts)}",
        )

test_local_markdown_links(
    [
        "README.md",
        "AGENTS.md",
        "work/current.md",
        "work/records/2026-08-10-federated-session-entry/record.md",
        "work/records/2026-08-10-federated-session-entry/raw/index.md",
        "authority/00-map.md",
        "authority/02-long-horizon-work.md",
        "authority/03-thinking-methods.md",
        "authority/04-collaboration.md",
        "authority/08-mvp-implementation-direction.md",
        "authority/10-operating-ledger.md",
    ]
)

args = parse_args()

if args.json:
    print(
        json.dumps(
            {
                "schema": RECEIPT_SCHEMA,
                "version": RECEIPT_VERSION,
                "ok": not failures,
                "counts": {
                    "passed": len(passes),
                    "failed": len(failures),
                    "total": len(check_results),
                },
                "checks": check_results,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
else:
    print(f"通过：{len(passes)}")
    for passed_check in passes:
        print(f"  [PASS] {passed_check}")

    if failures:
        print(f"失败：{len(failures)}")
        for failed_check in failures:
            print(f"  [FAIL] {failed_check}")
    else:
        print("联邦式 Session 入口静态合同验证通过。")

if failures:
    sys.exit(1)
