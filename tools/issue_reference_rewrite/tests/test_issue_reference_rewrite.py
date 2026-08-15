from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).parents[1] / "issue_reference_rewrite.py"
SPEC = importlib.util.spec_from_file_location("issue_reference_rewrite", MODULE_PATH)
assert SPEC and SPEC.loader
rewrite = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rewrite
SPEC.loader.exec_module(rewrite)


def lookup(existing, pulls=()):
    existing_set = set(existing)
    pull_set = set(pulls)

    def fake(requested):
        result = {}
        for repository, numbers in requested.items():
            for number in numbers:
                key = (repository, number)
                if key not in existing_set:
                    result[key] = rewrite.TargetState(repository, number, None, None)
                elif key in pull_set:
                    result[key] = rewrite.TargetState(
                        repository, number, "PullRequest", f"https://example.test/{number}"
                    )
                else:
                    result[key] = rewrite.TargetState(
                        repository, number, "Issue", f"https://example.test/{number}"
                    )
        return result

    return fake


class RewriteTests(unittest.TestCase):
    def test_fenced_and_inline_code_are_protected(self):
        text = "outside #1\n\n```json\n{\"issue\": \"#2\"}\n```\ninline `#3` end\n"
        analysis = rewrite.analyze_documents(
            {"doc.md": text}, lookup({("agent-control", 1)})
        )
        updated = rewrite.rewritten_texts(analysis)["doc.md"]
        self.assertIn("[#1](https://github.com/Eridanus117/agent-control/issues/1)", updated)
        self.assertIn('"#2"', updated)
        self.assertIn("`#3`", updated)
        self.assertEqual(
            {item.reason for item in analysis.protected}, {"fenced_code", "inline_code"}
        )

    def test_existing_link_is_not_nested_or_rewritten(self):
        text = "关联 [#4（已有）](https://github.com/Eridanus117/agent-control/issues/4)\n"
        analysis = rewrite.analyze_documents({"doc.md": text}, lookup(set()))
        self.assertEqual(rewrite.rewritten_texts(analysis)["doc.md"], text)
        self.assertEqual([item.reason for item in analysis.protected], ["existing_link"])

    def test_generated_link_inside_plain_brackets_is_idempotent(self):
        original = "[关联 agent-plugins#59]\n"
        first = rewrite.analyze_documents(
            {"doc.md": original}, lookup({("agent-plugins", 59)})
        )
        updated = rewrite.rewritten_texts(first)["doc.md"]
        second = rewrite.analyze_documents({"doc.md": updated}, lookup(set()))
        self.assertEqual(second.rewrites, [])
        self.assertEqual(rewrite.rewritten_texts(second)["doc.md"], updated)

    def test_cross_repository_context_and_ambiguity(self):
        text = (
            "Eridanus117/agent-plugins#34、#35 均已交付。\n"
            "agent-plugins 与 work-skills 对照时查看 #7。\n"
        )
        analysis = rewrite.analyze_documents(
            {"doc.md": text},
            lookup({("agent-plugins", 34), ("agent-plugins", 35)}),
        )
        updated = rewrite.rewritten_texts(analysis)["doc.md"]
        self.assertIn("agent-plugins[#34](https://github.com/Eridanus117/agent-plugins/issues/34)", updated)
        self.assertIn("[#35](https://github.com/Eridanus117/agent-plugins/issues/35)", updated)
        self.assertIn("查看 #7", updated)
        self.assertEqual(analysis.manual[0].reason, "ambiguous_cross_repository")

    def test_later_foreign_repository_does_not_reclassify_earlier_reference(self):
        text = "本仓 PR #33 与 agent-plugins#19 分别处理。\n"
        analysis = rewrite.analyze_documents(
            {"doc.md": text}, lookup({("agent-plugins", 19)})
        )
        updated = rewrite.rewritten_texts(analysis)["doc.md"]
        self.assertIn("PR #33", updated)
        self.assertIn("agent-plugins[#19]", updated)
        self.assertEqual(analysis.manual[0].reason, "ambiguous_cross_repository")

    def test_same_number_full_url_uniquely_resolves_repository(self):
        text = (
            "#32 的回执见 "
            "https://github.com/Eridanus117/agent-plugins/issues/32。\n"
        )
        analysis = rewrite.analyze_documents(
            {"doc.md": text}, lookup({("agent-plugins", 32)})
        )
        updated = rewrite.rewritten_texts(analysis)["doc.md"]
        self.assertTrue(updated.startswith("[#32](https://github.com/Eridanus117/agent-plugins/issues/32)"))

    def test_external_repository_is_never_assumed_to_be_current(self):
        text = "上游 stablyai/orca#13821 保持原样。\n"
        analysis = rewrite.analyze_documents({"doc.md": text}, lookup(set()))
        self.assertEqual(rewrite.rewritten_texts(analysis)["doc.md"], text)
        self.assertEqual(analysis.manual[0].reason, "external_repository_stablyai/orca")

    def test_pull_request_uses_issues_url(self):
        analysis = rewrite.analyze_documents(
            {"doc.md": "PR #295\n"},
            lookup({("agent-control", 295)}, pulls={("agent-control", 295)}),
        )
        updated = rewrite.rewritten_texts(analysis)["doc.md"]
        self.assertEqual(
            updated,
            "PR [#295](https://github.com/Eridanus117/agent-control/issues/295)\n",
        )
        self.assertEqual(analysis.target_states[("agent-control", 295)].kind, "PullRequest")

    def test_nonexistent_number_requires_manual_review(self):
        text = "笔误 #999999\n"
        analysis = rewrite.analyze_documents({"doc.md": text}, lookup(set()))
        self.assertEqual(rewrite.rewritten_texts(analysis)["doc.md"], text)
        self.assertEqual(analysis.manual[0].reason, "nonexistent_in_agent-control")

    def test_history_is_included_but_runtime_artifacts_are_excluded(self):
        texts = {
            "work/history/old.md": "历史 #8\n",
            "work/records/run/record.md": "记录 #9\n",
            "tools/ops-metrics/reports/day.md": "快照 #10\n",
            "tools/worker_snapshot/current.md": "当前 #11\n",
            "tools/worker_snapshot/samples/example.md": "样本 #12\n",
            "work/records/2026-08-10-federated-session-entry/raw/current-before-migration.md": "原始 #13\n",
        }
        analysis = rewrite.analyze_documents(
            texts,
            lookup({("agent-control", 8), ("agent-control", 9)}),
        )
        updated = rewrite.rewritten_texts(analysis)
        self.assertIn("issues/8", updated["work/history/old.md"])
        self.assertIn("issues/9", updated["work/records/run/record.md"])
        self.assertEqual(updated["tools/ops-metrics/reports/day.md"], "快照 #10\n")
        self.assertEqual(updated["tools/worker_snapshot/current.md"], "当前 #11\n")
        self.assertEqual(updated["tools/worker_snapshot/samples/example.md"], "样本 #12\n")
        self.assertEqual(
            updated[
                "work/records/2026-08-10-federated-session-entry/raw/current-before-migration.md"
            ],
            "原始 #13\n",
        )
        self.assertEqual(len(analysis.excluded), 4)

    def test_default_mode_is_dry_run(self):
        args = rewrite.parse_args([])
        self.assertFalse(args.apply)

    def test_non_markdown_references_are_audited_but_not_rewritten(self):
        analysis = rewrite.analyze_repository(
            {"doc.md": "正文 #14\n"},
            {"example.py": 'value = "#15"\n'},
            lookup({("agent-control", 14)}),
        )
        updated = rewrite.rewritten_texts(analysis)
        self.assertIn("issues/14", updated["doc.md"])
        self.assertEqual(updated["example.py"], 'value = "#15"\n')
        self.assertEqual(
            [item.reason for item in analysis.excluded], ["excluded_non_markdown"]
        )

    def test_crlf_is_preserved_by_rewrite(self):
        text = "first #12\r\nsecond\r\n"
        analysis = rewrite.analyze_documents(
            {"doc.md": text}, lookup({("agent-control", 12)})
        )
        updated = rewrite.rewritten_texts(analysis)["doc.md"]
        self.assertEqual(updated.count("\r\n"), 2)


if __name__ == "__main__":
    unittest.main()
