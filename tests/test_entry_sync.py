"""Unit tests for declarative Agent entrypoint synchronization."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from scripts.entry_sync import __main__ as entry_cli
from scripts.entry_sync.core import (
    EntrySyncError,
    apply_sections,
    compare_contents,
    find_markdown_section,
    generate_target,
    load_config,
    normalize_newlines,
    replace_files_atomically,
)


class MarkdownSelectionTests(unittest.TestCase):
    SOURCE = (
        "# Source\n\n"
        "## Shared\n\nsource body\n\n"
        "### Nested\n\nnested source\n\n"
        "## Final\n\nfinal source\n"
    )

    def test_section_selection_stops_at_same_or_higher_level(self) -> None:
        section = find_markdown_section(self.SOURCE, "Shared", 2)

        self.assertIn("### Nested", section.text)
        self.assertNotIn("## Final", section.text)

    def test_mirror_can_rename_heading_and_preserve_unselected_content(self) -> None:
        target = (
            "# Target\n\n"
            "## Local name\n\nstale\n\n"
            "## Local only\n\nkeep me\n"
        )
        declarations = [
            {
                "mode": "mirror",
                "source": {"heading": "Shared", "level": 2},
                "target": {"heading": "Local name", "level": 2},
            }
        ]

        rendered = apply_sections(self.SOURCE, target, declarations)

        self.assertIn("## Local name\n\nsource body", rendered)
        self.assertIn("### Nested\n\nnested source", rendered)
        self.assertIn("## Local only\n\nkeep me", rendered)
        self.assertNotIn("stale", rendered)

    def test_target_specific_projection_is_validated_but_not_rewritten(self) -> None:
        target = "# Target\n\n## Local route\n\nlocal body\n"
        declarations = [
            {
                "mode": "target_specific",
                "source": {"heading": "Shared", "level": 2},
                "target": {"heading": "Local route", "level": 2},
                "reason": "The target has repository-only routing.",
            }
        ]

        self.assertEqual(apply_sections(self.SOURCE, target, declarations), target)

    def test_missing_declared_section_fails_instead_of_silently_dropping_it(self) -> None:
        with self.assertRaisesRegex(EntrySyncError, "找不到 Markdown 章节"):
            apply_sections(
                self.SOURCE,
                "# Target\n",
                [
                    {
                        "mode": "mirror",
                        "source": {"heading": "Shared", "level": 2},
                        "target": {"heading": "Missing", "level": 2},
                    }
                ],
            )


class FencedCodeBlockTests(unittest.TestCase):
    def test_backtick_fence_headings_do_not_end_a_section(self) -> None:
        text = (
            "# Doc\n\n"
            "## Shared\n\nintro\n\n"
            "```markdown\n## Example\n# Fake top\n```\n\n"
            "tail after fence\n\n"
            "## Next\n\nnext body\n"
        )

        section = find_markdown_section(text, "Shared", 2)

        self.assertIn("## Example", section.text)
        self.assertIn("# Fake top", section.text)
        self.assertIn("tail after fence", section.text)
        self.assertNotIn("## Next", section.text)

    def test_tilde_fence_headings_do_not_end_a_section(self) -> None:
        text = (
            "## Shared\n\n~~~text\n## Example\n~~~\n\n"
            "after fence\n\n## Next\n\nnext body\n"
        )

        section = find_markdown_section(text, "Shared", 2)

        self.assertIn("## Example", section.text)
        self.assertIn("after fence", section.text)
        self.assertNotIn("## Next", section.text)

    def test_unclosed_fence_hides_headings_until_end_of_document(self) -> None:
        text = "## Shared\n\n```\n## Example\n\nno closing fence\n"

        section = find_markdown_section(text, "Shared", 2)

        self.assertIn("no closing fence", section.text)
        with self.assertRaisesRegex(EntrySyncError, "找不到 Markdown 章节"):
            find_markdown_section(text, "Example", 2)

    def test_fenced_duplicate_heading_does_not_make_section_ambiguous(self) -> None:
        text = "## Shared\n\n```\n## Shared\n```\n\nreal body\n"

        section = find_markdown_section(text, "Shared", 2)

        self.assertIn("real body", section.text)

    def test_mirror_preserves_fenced_example_content(self) -> None:
        source = (
            "# S\n\n"
            "## Shared\n\n```md\n## Example\n```\n\ntail\n\n"
            "## Final\n\nfinal\n"
        )
        target = "# T\n\n## Local\n\nstale\n"
        declarations = [
            {
                "mode": "mirror",
                "source": {"heading": "Shared", "level": 2},
                "target": {"heading": "Local", "level": 2},
            }
        ]

        rendered = apply_sections(source, target, declarations)

        self.assertIn("## Example", rendered)
        self.assertIn("tail", rendered)
        self.assertNotIn("stale", rendered)
        self.assertNotIn("## Final", rendered)

    def test_literal_trailing_hash_stays_in_the_title(self) -> None:
        text = "## C#\n\ncsharp body\n\n## Closed ##\n\nclosed body\n"

        self.assertIn("csharp body", find_markdown_section(text, "C#", 2).text)
        self.assertIn("closed body", find_markdown_section(text, "Closed", 2).text)


class AtomicWriteTests(unittest.TestCase):
    def test_batch_write_replaces_existing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first = root / "first.md"
            first.write_bytes(b"old first")
            second = root / "nested" / "second.md"

            replace_files_atomically([(first, b"new first"), (second, b"new second")])

            self.assertEqual(first.read_bytes(), b"new first")
            self.assertEqual(second.read_bytes(), b"new second")
            self.assertEqual(list(root.rglob("*.tmp")), [])

    def test_staging_failure_leaves_destinations_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            good = root / "good.md"
            good.write_bytes(b"old")
            blocker = root / "blocker"
            blocker.write_bytes(b"")
            bad = blocker / "sub" / "bad.md"

            for writes in (
                [(bad, b"new"), (good, b"new")],
                [(good, b"new"), (bad, b"new")],
            ):
                with self.assertRaisesRegex(EntrySyncError, "原子写入失败"):
                    replace_files_atomically(writes)
                self.assertEqual(good.read_bytes(), b"old")
                self.assertEqual(list(root.rglob("*.tmp")), [])


class GenerateArgumentTests(unittest.TestCase):
    def test_generate_rejects_write_repository_with_installed_scope(self) -> None:
        arguments = Namespace(
            config=None,
            output_dir=Path("build/entry-sync"),
            scope="installed",
            write_repository=True,
        )

        with self.assertRaisesRegex(EntrySyncError, "--scope installed"):
            entry_cli.run_generate(arguments)


class NormalizationAndComparisonTests(unittest.TestCase):
    def test_normalize_newlines_handles_crlf_and_lone_cr(self) -> None:
        self.assertEqual(normalize_newlines("a\r\nb\rc\n"), "a\nb\nc\n")

    def test_comparison_accepts_only_newline_differences(self) -> None:
        result = compare_contents("a\nb\n", "a\r\nb\r\n")

        self.assertTrue(result.matches)
        self.assertEqual(result.diff, "")

    def test_comparison_reports_a_ci_usable_unified_diff(self) -> None:
        result = compare_contents("a\nexpected\n", "a\nactual\n")

        self.assertFalse(result.matches)
        self.assertIn("-actual", result.diff)
        self.assertIn("+expected", result.diff)


class TargetGenerationTests(unittest.TestCase):
    def test_copy_target_does_not_read_or_write_installed_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "entrypoints").mkdir()
            (root / "entrypoints/source.md").write_bytes(b"source\r\n")
            config = {"source": "entrypoints/source.md"}
            target = {
                "id": "installed-test",
                "scope": "installed",
                "strategy": "copy",
                "destination": {"base": "home", "path": ".example/entry.md"},
                "output": "installed/example/entry.md",
            }
            output_root = root / "build"

            with mock.patch.object(Path, "home", return_value=root / "fake-home"):
                result = generate_target(root, config, target, output_root)

            self.assertEqual(result.content, "source\n")
            self.assertEqual(
                result.output_path,
                (output_root / "installed/example/entry.md").resolve(),
            )
            self.assertFalse(result.current_path.exists())

    def test_default_config_declares_expected_projection_counts(self) -> None:
        config = load_config()
        targets = {target["id"]: target for target in config["targets"]}

        self.assertEqual(config["source"], "entrypoints/agent-system.md")
        self.assertEqual(len(targets["repository-readme"]["sections"]), 3)
        # AGENTS 只剩两节实质内容（仓库任务路由、知识按名问路）。原先另有 5 节是
        # 指向版本化正文的回指，而 CLAUDE.md 已经 @import 了那份正文全文 ——
        # 纯冗余，且在教模型"去大文档里找"。
        self.assertEqual(len(targets["repository-agents"]["sections"]), 2)
        # 默认配置只剩 repository 作用域：用户级入口下沉之后，~/.claude/CLAUDE.md 与
        # ~/.codex/AGENTS.md 不再是版本化正文的投影，改由 test_federated_entry 的
        # 反向断言守护（它们必须**不**引用那份正文）。
        # installed 作用域的生成能力本身保留，本文件其他用例仍用合成配置覆盖它。
        self.assertEqual(
            {target["scope"] for target in targets.values()},
            {"repository"},
        )

    def test_repository_target_cannot_escape_repository_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "source.md").write_text("source\n", encoding="utf-8")
            target = {
                "id": "escape",
                "scope": "repository",
                "strategy": "copy",
                "destination": {"base": "repository", "path": "../outside.md"},
                "output": "escape.md",
            }

            with self.assertRaisesRegex(EntrySyncError, "越出声明根目录"):
                generate_target(
                    root,
                    {"source": "source.md"},
                    target,
                    root / "build",
                )

    def test_check_returns_nonzero_for_a_normalized_content_difference(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "source.md").write_text("expected\n", encoding="utf-8")
            (root / "target.md").write_text("actual\r\n", encoding="utf-8")
            config_path = root / "targets.json"
            config_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "source": "source.md",
                        "targets": [
                            {
                                "id": "repository-test",
                                "scope": "repository",
                                "strategy": "copy",
                                "destination": {
                                    "base": "repository",
                                    "path": "target.md",
                                },
                                "output": "target.md",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            arguments = Namespace(config=config_path, scope="repository", context_lines=3)

            with mock.patch.object(entry_cli, "repository_root", return_value=root):
                with redirect_stdout(io.StringIO()) as output:
                    exit_code = entry_cli.run_check(arguments)

            self.assertEqual(exit_code, 1)
            self.assertIn("[DIFF] repository-test", output.getvalue())

    def test_config_rejects_duplicate_target_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_path = Path(temporary_directory) / "targets.json"
            config_path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "source": "source.md",
                        "targets": [
                            {
                                "id": "same",
                                "scope": "repository",
                                "strategy": "copy",
                                "destination": {
                                    "base": "repository",
                                    "path": "a.md",
                                },
                                "output": "a.md",
                            },
                            {
                                "id": "same",
                                "scope": "installed",
                                "strategy": "copy",
                                "destination": {
                                    "base": "environment",
                                    "variable": "APPDATA",
                                    "path": "b.md",
                                },
                                "output": "b.md",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(EntrySyncError, "target id 重复"):
                load_config(config_path)


if __name__ == "__main__":
    unittest.main()
