"""Tests for deterministic, explicitly invoked knowledge routing."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


TOOL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = TOOL_ROOT.parents[1]
sys.path.insert(0, str(TOOL_ROOT))

from action_trigger import (  # noqa: E402
    KnowledgeActionTrigger,
    TriggerError,
    hook_response,
    load_routes,
    main,
)


class KnowledgeActionTriggerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.trigger = KnowledgeActionTrigger(load_routes())

    def test_powershell_github_multiline_blind_spot_routes_to_k17(self) -> None:
        matches = self.trigger.match_text(
            "UserPromptSubmit",
            "Windows PowerShell 中用 gh CLI 给 GitHub Issue 发布多行 Markdown 评论正文",
        )

        self.assertEqual(
            [match.route.identifier for match in matches],
            ["github-multiline-markdown"],
        )
        self.assertEqual(
            matches[0].route.source,
            "knowledge/windows-powershell-multiline-transfer.md",
        )

    def test_windows_path_and_file_lock_blind_spot_routes_to_k24(self) -> None:
        matches = self.trigger.match_text(
            "UserPromptSubmit",
            "Windows 11 深目录出现长路径错误，覆盖文件时又提示被另一个进程使用",
        )

        self.assertEqual([match.route.identifier for match in matches], ["windows-path-or-file-lock"])
        self.assertEqual(matches[0].route.source, "knowledge/windows-agent-ops.md")

    def test_partial_signal_groups_do_not_match(self) -> None:
        self.assertEqual(
            self.trigger.match_text(
                "UserPromptSubmit", "Use PowerShell to print a local Markdown file"
            ),
            (),
        )
        self.assertEqual(
            self.trigger.match_text(
                "UserPromptSubmit", "A Linux process reports a sharing violation"
            ),
            (),
        )

    def test_hook_response_uses_current_claude_shape(self) -> None:
        response = hook_response(
            {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Windows PowerShell 用 gh api 发布多行 Markdown issue body",
            },
            self.trigger,
        )

        output = response["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "UserPromptSubmit")
        self.assertIn("windows-powershell-multiline-transfer.md", output["additionalContext"])
        self.assertNotIn("decision", response)

    def test_retained_hook_adapter_remains_cli_compatible(self) -> None:
        payload = json.dumps(
            {
                "hook_event_name": "UserPromptSubmit",
                "prompt": "Windows PowerShell 用 gh CLI 发布多行 Markdown 评论",
            },
            ensure_ascii=False,
        )
        completed = subprocess.run(
            [sys.executable, str(TOOL_ROOT / "action_trigger.py"), "--hook"],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        response = json.loads(completed.stdout)
        output = response["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "UserPromptSubmit")
        self.assertIn(
            "windows-powershell-multiline-transfer.md",
            output["additionalContext"],
        )

    def test_readme_marks_hook_adapter_unadopted(self) -> None:
        readme = (TOOL_ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("本系统不安装", readme)
        self.assertIn("注入式投递已被负责人否决", readme)
        self.assertIn("251-D1", readme)
        self.assertNotIn("Activating this adapter", readme)

    def test_pre_tool_use_reads_tool_name_and_input(self) -> None:
        response = hook_response(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {
                    "command": "gh issue comment --body-file body.md",
                    "description": "Windows PowerShell 多行 Markdown",
                },
            },
            self.trigger,
        )

        self.assertEqual(
            response["hookSpecificOutput"]["hookEventName"], "PreToolUse"
        )

    def test_direct_action_emits_source_and_boundary(self) -> None:
        output = self.trigger.context(
            (self.trigger.match_action("windows-path-or-file-lock"),)
        )

        self.assertIn("knowledge\\windows-agent-ops.md", output)
        self.assertIn("按名问路查询结果", output)
        self.assertIn("不改变任务合同", output)


class CatalogValidationTests(unittest.TestCase):
    def test_source_cannot_escape_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            catalog = root / "routes.json"
            catalog.write_text(
                json.dumps(
                    {
                        "schema": "agent-control.knowledge-action-routes",
                        "version": 1,
                        "routes": [
                            {
                                "id": "escape",
                                "events": ["UserPromptSubmit"],
                                "allOf": [["signal"]],
                                "source": "../outside.md",
                                "checkpoint": "before",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(TriggerError, "escapes the repository"):
                load_routes(catalog, root)

    def test_hook_mode_is_fail_open_for_malformed_json(self) -> None:
        stdin = mock.Mock()
        stdin.buffer = io.BytesIO(b"not json")
        with mock.patch("sys.stdin", stdin), redirect_stdout(io.StringIO()) as output:
            exit_code = main(["--hook"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue()), {})

    def test_hook_mode_is_fail_open_for_catalog_error(self) -> None:
        stdin = mock.Mock()
        stdin.buffer = io.BytesIO(b"{}")
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_catalog = Path(temporary_directory) / "missing.json"
            with mock.patch("sys.stdin", stdin), redirect_stdout(io.StringIO()) as output:
                exit_code = main(["--hook", "--routes", str(missing_catalog)])

        self.assertEqual(exit_code, 0)
        self.assertEqual(json.loads(output.getvalue()), {})


if __name__ == "__main__":
    unittest.main()
