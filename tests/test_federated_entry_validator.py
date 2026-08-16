"""回归测试：联邦式续接入口验证器的人类输出与 JSON 回执。"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPOSITORY_ROOT / "scripts" / "test_federated_entry.py"
EXPECTED_SCHEMA = "agent-control.federated-entry-validation-receipt"
ENTRY_PATHS = (
    Path("README.md"),
    Path("entrypoints/agent-system.md"),
    Path("AGENTS.md"),
)
ENTRY_SYNC_DIRECTORY = REPOSITORY_ROOT / "scripts" / "entry_sync"


def copy_validator_bundle(fixture_root: Path) -> Path:
    fixture_validator = fixture_root / "scripts" / VALIDATOR.name
    fixture_validator.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(VALIDATOR, fixture_validator)
    shutil.copytree(
        ENTRY_SYNC_DIRECTORY,
        fixture_root / "scripts" / "entry_sync",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    return fixture_validator


def run_validator(
    *arguments: str,
    cwd: Path = REPOSITORY_ROOT,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", str(VALIDATOR), *arguments],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def run_validator_with_system_entry_mutation(
    before: str,
    after: str,
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory() as temporary_directory:
        fixture_root = Path(temporary_directory)
        fixture_validator = copy_validator_bundle(fixture_root)
        for relative_path in ENTRY_PATHS:
            source = REPOSITORY_ROOT / relative_path
            target = fixture_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            entry_text = source.read_text(encoding="utf-8")
            if relative_path == Path("entrypoints/agent-system.md"):
                if before not in entry_text:
                    raise ValueError(f"变异源句不存在：{relative_path}: {before}")
                entry_text = entry_text.replace(before, after)
            target.write_text(entry_text, encoding="utf-8")
        (fixture_root / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", str(fixture_validator), "--json"],
            cwd=fixture_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )


class FederatedEntryValidatorTests(unittest.TestCase):
    def test_default_output_remains_the_human_projection(self) -> None:
        human = run_validator()
        machine = run_validator("--json")

        self.assertEqual(human.returncode, 0, human.stderr)
        self.assertEqual(machine.returncode, 0, machine.stderr)
        receipt = json.loads(machine.stdout)

        expected_lines = [f"通过：{receipt['counts']['passed']}"]
        expected_lines.extend(
            f"  [PASS] {check['description']}"
            for check in receipt["checks"]
            if check["ok"]
        )
        expected_lines.append("联邦式 Session 入口静态合同验证通过。")
        self.assertEqual(human.stdout.splitlines(), expected_lines)

    def test_json_success_receipt_is_consistent(self) -> None:
        completed = run_validator("--json")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        receipt = json.loads(completed.stdout)
        self.assertEqual(receipt["schema"], EXPECTED_SCHEMA)
        self.assertEqual(receipt["version"], 1)
        self.assertTrue(receipt["ok"])
        self.assertEqual(receipt["counts"]["failed"], 0)
        self.assertEqual(receipt["counts"]["total"], len(receipt["checks"]))
        self.assertEqual(
            receipt["counts"]["passed"] + receipt["counts"]["failed"],
            receipt["counts"]["total"],
        )
        self.assertTrue(
            all(
                set(check) == {"ok", "description"}
                for check in receipt["checks"]
            )
        )
        self.assertEqual(completed.stderr, "")

    def test_receipt_exposes_complete_continuation_contract(self) -> None:
        completed = run_validator("--json")

        self.assertEqual(completed.returncode, 0, completed.stderr)
        receipt = json.loads(completed.stdout)
        descriptions = {check["description"] for check in receipt["checks"]}
        expected_descriptions = {
            "入口同步声明式配置可加载",
            "repository-source 的声明式投影与单一真源一致",
            "repository-readme 的声明式投影与单一真源一致",
            "repository-agents 的声明式投影与单一真源一致",
            "AGENTS 不再单列在线续接章节，版本化入口独占正文",
            "AGENTS 不再单列扩大并行波次章节，版本化入口独占正文",
            "版本化系统入口保留在线续接的触发、恢复、决定与离线边界",
            "版本化系统入口保留扩大并行波次的触发、所有权与禁用边界",
            "Claude 真实仓库入口继续导入同一 AGENTS.md",
        }
        self.assertTrue(
            expected_descriptions.issubset(descriptions),
            expected_descriptions - descriptions,
        )
        self.assertTrue(
            any("在线续接章节保持短" in description for description in descriptions)
        )
        self.assertIn(
            "版本化系统入口：在线续接章节不复制 Skill 内部限流／生命周期细节",
            descriptions,
        )
        # 下界按 S3（生成器整合）与 S2（current 降级为指针壳）合并后的实测检查数回填。
        self.assertGreaterEqual(receipt["counts"]["total"], 80)

    def test_continuation_target_drift_fails_source_projection(self) -> None:
        trigger_gate = (
            "自然发现直接对应明确、开放且已授权父 Issue 未满足成功条件的"
            "具体缺口时，加载 `github-collaboration:issue-workflow`"
        )
        mutations = [
            (
                trigger_gate,
                (
                    "自然发现一个直接对应明确、开放且已授权父 Issue 未满足成功条件的"
                    "具体缺口时，不加载 `github-collaboration:issue-workflow`。"
                ),
            ),
            (
                trigger_gate,
                (
                    "即使缺口并不对应明确、开放且已授权父 Issue 未满足成功条件，"
                    "也可以加载 `github-collaboration:issue-workflow`。"
                ),
            ),
            (
                trigger_gate,
                (
                    "自然发现一个直接对应明确、开放且已授权父 Issue 未满足成功条件的"
                    "具体缺口时，可以选择加载 `github-collaboration:issue-workflow`。"
                ),
            ),
            (
                "新建一个 Session 与恢复一个已有但当前空闲的 Session 是等价入口：",
                "新建一个 Session 与恢复一个已有但当前空闲的 Session 不是等价入口：",
            ),
            (
                (
                    "重读入口、远端 Issue／Project 与必要的 `work/current.md`；"
                    "不得沿用旧聊天记忆、草稿、角色、身份、授权或所有权。"
                ),
                (
                    "重读入口、远端 Issue／Project 与必要的 `work/current.md`；"
                    "可以沿用旧聊天记忆、草稿、角色、身份、授权或所有权。"
                ),
            ),
        ]
        gate_description = "版本化系统入口保留在线续接的触发、恢复、决定与离线边界"

        for before, after in mutations:
            with self.subTest(after=after):
                completed = run_validator_with_system_entry_mutation(before, after)
                receipt = json.loads(completed.stdout)
                target_checks = [
                    check
                    for check in receipt["checks"]
                    if check["description"].startswith(gate_description)
                ]

                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(len(target_checks), 1, target_checks)
                self.assertFalse(target_checks[0]["ok"])

    def test_global_wave_target_drift_fails_source_projection(self) -> None:
        trigger_gate = (
            "持有明确 Issue 时，只有负责人要求扩大当前并发面、增加并行投入或选择下一波次"
            "（包括询问“还有可并发推进事项吗”），才读取经营总账权威与远端观察面，"
            "把候选枚举源扩大到整个经营总账的未满足／部分满足诉求，并返回 "
            "`adaptive-problem-solving` 形成或选择有界 Issue。"
        )
        ownership_gate = (
            "看得更宽不等于写得更宽：当前 Session 的写入所有权仍限于原 Issue 子树；"
            "表外候选只能提出、形成获准合同或交给其他所有者。"
        )
        guard_gate = (
            "普通进度询问和当前 Issue 内选择下一切片不触发全局枚举；"
            "同一阶段没有新证据时不重复扫描。"
            "全局枚举本身不自动建 Issue、派发或修改 Project；"
        )
        mutations = [
            (
                trigger_gate,
                (
                    "持有明确 Issue 时，即使负责人只问当前 PR 进度，也读取经营总账权威与"
                    "远端观察面，把候选枚举源扩大到整个经营总账的未满足／部分满足诉求。"
                ),
            ),
            (
                trigger_gate,
                (
                    "持有明确 Issue 时，只有负责人要求扩大当前并发面、增加并行投入或选择"
                    "下一波次，才读取短活动协调快照，把候选枚举源限制为当前 Run 邻域。"
                ),
            ),
            (
                ownership_gate,
                (
                    "看得更宽就可以写得更宽：当前 Session 的写入所有权扩展到表外候选；"
                    "表外候选可以直接领取、派发或改写。"
                ),
            ),
            (
                guard_gate,
                (
                    "普通进度询问和当前 Issue 内选择下一切片也触发全局枚举；"
                    "同一阶段没有新证据时不重复扫描。"
                    "全局枚举本身不自动建 Issue、派发或修改 Project。"
                ),
            ),
            (
                guard_gate,
                (
                    "普通进度询问和当前 Issue 内选择下一切片不触发全局枚举；"
                    "同一阶段没有新证据时重复扫描。"
                    "全局枚举本身自动建 Issue、派发并修改 Project。"
                ),
            ),
            (
                guard_gate,
                (
                    guard_gate
                    + "\n\n即使只问当前 PR 进度，也可以顺便扫描全局并直接派发。"
                ),
            ),
        ]
        gate_prefixes = (
            "版本化系统入口保留扩大并行波次的触发、所有权与禁用边界",
            "版本化系统入口的扩大并行波次正文不含反向放宽",
        )

        for before, after in mutations:
            with self.subTest(after=after):
                completed = run_validator_with_system_entry_mutation(before, after)
                receipt = json.loads(completed.stdout)
                target_checks = [
                    check
                    for check in receipt["checks"]
                    if any(
                        check["description"].startswith(prefix)
                        for prefix in gate_prefixes
                    )
                    and not check["ok"]
                ]

                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(len(target_checks), 1, target_checks)
                self.assertFalse(target_checks[0]["ok"])

    def test_size_and_workflow_detail_guards_reject_mirrored_drift(self) -> None:
        terminal_boundary = (
            "直接进入原终端只用于实时纠偏、过程观察或工具故障逃生，不是默认审批入口。"
            "没有在线 Session 时如实缺少 L3 离线唤醒。"
        )
        mutations = [
            (
                terminal_boundary + "\n- 同一父级最多同时存在 2 个自动派发子项。",
                "版本化系统入口：在线续接章节不复制 Skill 内部限流／生命周期细节",
            ),
            (
                terminal_boundary + ("\n- 额外生命周期说明。" * 100),
                "版本化系统入口：在线续接章节保持短",
            ),
        ]
        for mutated_boundary, target_prefix in mutations:
            with self.subTest(target_prefix=target_prefix):
                completed = run_validator_with_system_entry_mutation(
                    terminal_boundary,
                    mutated_boundary,
                )
                receipt = json.loads(completed.stdout)
                target_checks = [
                    check
                    for check in receipt["checks"]
                    if check["description"].startswith(target_prefix)
                ]

                self.assertNotEqual(completed.returncode, 0)
                self.assertEqual(len(target_checks), 1, target_checks)
                self.assertFalse(target_checks[0]["ok"])

    def test_json_failure_receipt_is_parseable_and_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            fixture_root = Path(temporary_directory)
            fixture_validator = copy_validator_bundle(fixture_root)
            (fixture_root / "README.md").write_bytes(b"\xff\xfeinvalid UTF-8")
            completed = subprocess.run(
                [sys.executable, "-B", str(fixture_validator), "--json"],
                cwd=fixture_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=False,
            )

        receipt = json.loads(completed.stdout)
        self.assertNotEqual(completed.returncode, 0)
        self.assertFalse(receipt["ok"])
        self.assertGreater(receipt["counts"]["failed"], 0)
        self.assertEqual(receipt["counts"]["total"], len(receipt["checks"]))
        self.assertIn(
            {"ok": False, "description": "entrypoints/agent-system.md 存在"},
            receipt["checks"],
        )
        self.assertTrue(
            any(
                not check["ok"] and "UTF-8" in check["description"]
                for check in receipt["checks"]
            )
        )
        self.assertTrue(
            any(
                not check["ok"] and "Git 错误" in check["description"]
                for check in receipt["checks"]
            )
        )
        self.assertEqual(completed.stderr, "")


if __name__ == "__main__":
    unittest.main()
