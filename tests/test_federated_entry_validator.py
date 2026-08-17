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
            "AGENTS 不再单列扩大工作范围章节，版本化入口独占正文",
            "版本化系统入口保留显式激活、恢复与离线边界",
            "版本化系统入口保留扩大范围的触发、所有权与禁用边界",
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
        proposal_gate = "公开父 Issue 的缺口时，只记录 proposal"
        activation_gate = "只有负责人明确激活后"
        scan_gate = "不自动启动，也不扫描队列找活"
        mutations = [
            (
                proposal_gate,
                "私有父 Issue 的缺口也可以直接执行",
            ),
            (
                activation_gate,
                "无需负责人明确激活",
            ),
            (
                scan_gate,
                "自动启动并扫描队列找活",
            ),
            (
                "新建 Session 与恢复空闲 Session 都必须重读项目入口和远端当前合同",
                "恢复空闲 Session 可以沿用旧合同",
            ),
            (
                (
                    "重读项目入口和远端当前合同；"
                    "不得沿用旧聊天记忆、草稿、角色、身份、授权或所有权。"
                ),
                (
                    "重读项目入口和远端当前合同；"
                    "可以沿用旧聊天记忆、草稿、角色、身份、授权或所有权。"
                ),
            ),
        ]
        gate_description = "版本化系统入口保留显式激活、恢复与离线边界"

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
            "只有负责人明确要求扩大并发面、选择下一项工作或启动另一项任务时，"
            "才枚举公开候选。"
        )
        ownership_gate = (
            "迁移索引默认排除；当前 Session 的写入所有权仍限于原合同。"
        )
        guard_gate = (
            "没有明确激活语句时，不创建 Issue、不派发、不修改 Project、不启动新模型执行。"
        )
        mutations = [
            (
                trigger_gate,
                "普通进度询问也枚举所有公开候选。",
            ),
            (
                trigger_gate,
                "只有发现空闲运行后端时，才枚举私有旧 Project。",
            ),
            (
                ownership_gate,
                "迁移索引一并纳入；当前 Session 的写入所有权扩展到全部候选。",
            ),
            (
                guard_gate,
                "没有明确激活语句时，也可以创建 Issue、派发和启动新模型执行。",
            ),
            (
                guard_gate,
                "没有明确激活语句时，不创建 Issue，但可以派发并修改 Project。",
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
            "版本化系统入口保留扩大范围的触发、所有权与禁用边界",
            "版本化系统入口的扩大工作范围正文不含反向放宽",
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
