"""知识检索器的解析、排序、回退与边界测试。"""

from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path


TOOL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = TOOL_ROOT.parents[1]
sys.path.insert(0, str(TOOL_ROOT))

from kb_retriever.cli import main as cli_main  # noqa: E402
from kb_retriever.context import parse_trigger_context  # noqa: E402
from kb_retriever.models import RetrievalCard, TriggerContext  # noqa: E402
from kb_retriever.parser import parse_retrieval_cards  # noqa: E402
from kb_retriever.retriever import KnowledgeRetriever  # noqa: E402


CARDS_PATH = REPOSITORY_ROOT / "knowledge" / "retrieval-cards.md"
NATURAL_BYPASS_EVALUATOR = (
    TOOL_ROOT / "examples" / "evaluate_natural_bypass.py"
)

EXPECTED_CARD_IDENTIFIERS = (
    "A",
    "B",
    "C",
    "D",
    "E",
    "F",
    "G",
    "H",
    "I",
    "J",
    "K",
    "L",
    "M",
    "N",
    "O",
    "P",
    "Q",
    "R",
    "S",
    "T",
    "U",
    "V",
    "W",
)

EXPECTED_BUCKET_COUNTS = {
    ("post-dispatch", "orca.supervised-worker-dispatch"): 2,
    ("pre-acceptance", "agent-plugin.installed-copy"): 2,
    ("pre-capacity-decision", "orca.codex-account-snapshot"): 2,
    ("pre-github-publication", "github.issue-reference"): 2,
    ("post-entry-source-change", "agent-system.entry-copy-set"): 2,
    ("pre-session-resume", "coding-agent.session"): 2,
    ("post-remote-write-error", "github.graphql-mutation"): 2,
    ("pre-review-consumption", "multi-session.review-evidence"): 2,
    ("pre-decision-routing", "agent-system.three-party-review"): 2,
    ("pre-capacity-decision", "codex.token-burn"): 2,
    ("pre-worktree-delete", "orca.worktree"): 2,
    ("pre-github-publication", "github.multiline-markdown-body"): 1,
}

EXPECTED_SINGLE_CARD_BUCKETS = {
    ("pre-github-publication", "github.multiline-markdown-body"),
}


class RetrievalCardParserTests(unittest.TestCase):
    def test_card_identifiers_match_corpus_snapshot(self) -> None:
        cards = parse_retrieval_cards(CARDS_PATH)

        self.assertEqual(
            tuple(card.identifier for card in cards),
            EXPECTED_CARD_IDENTIFIERS,
            "检索卡语料已变化；必须在同一批更新卡片标识符快照",
        )
        self.assertEqual(cards[0].stage, "post-dispatch")
        self.assertIn("input_accepted", cards[0].aliases)
        self.assertIn("K2（Orca 受监督派发", cards[0].source)
        self.assertIn("小样回放有效", cards[0].evidence)

        for card in cards:
            with self.subTest(card=card.identifier):
                self.assertIsInstance(card.stage, str)
                self.assertTrue(card.stage)
                self.assertIsInstance(card.object, str)
                self.assertTrue(card.object)
                self.assertIsInstance(card.operation, str)
                self.assertTrue(card.operation)
                self.assertIsInstance(card.aliases, tuple)
                self.assertTrue(card.aliases)
                self.assertTrue(
                    all(
                        isinstance(alias, str) and alias
                        for alias in card.aliases
                    )
                )
                self.assertIsInstance(card.one_line_action, str)
                self.assertTrue(card.one_line_action)
                self.assertIsInstance(card.source, str)
                self.assertTrue(card.source)
                self.assertIsInstance(card.evidence, str)
                self.assertTrue(card.evidence)
                self.assertIsInstance(card.invalidates, str)
                self.assertTrue(card.invalidates)

    def test_stage_object_buckets_match_corpus_snapshot(self) -> None:
        cards = parse_retrieval_cards(CARDS_PATH)
        bucket_counts: dict[tuple[str, str], int] = {}
        for card in cards:
            bucket = (card.stage, card.object)
            bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

        self.assertEqual(
            bucket_counts,
            EXPECTED_BUCKET_COUNTS,
            "检索卡语料已变化；必须在同一批更新 stage/object 分桶快照",
        )
        self.assertEqual(
            {
                bucket
                for bucket, count in bucket_counts.items()
                if count == 1
            },
            EXPECTED_SINGLE_CARD_BUCKETS,
        )
        self.assertTrue(
            all(
                count >= 2
                for bucket, count in bucket_counts.items()
                if bucket not in EXPECTED_SINGLE_CARD_BUCKETS
            )
        )


class ContextParserTests(unittest.TestCase):
    def test_parses_compact_and_json_contexts(self) -> None:
        compact = parse_trigger_context(
            "stage=post-dispatch; object=orca.supervised-worker-dispatch; "
            "signals=worker-start input_accepted"
        )
        payload = parse_trigger_context(
            '{"stage":"post-dispatch","object":"orca.supervised-worker-dispatch",'
            '"signals":["worker-start","input_accepted"]}'
        )

        self.assertEqual(compact.stage, payload.stage)
        self.assertEqual(compact.object, payload.object)
        self.assertEqual(payload.signals, "worker-start input_accepted")


class KnowledgeRetrieverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.retriever = KnowledgeRetriever(parse_retrieval_cards(CARDS_PATH))

    def assert_top_card(self, context: TriggerContext, identifier: str) -> None:
        outcome = self.retriever.search(context)
        self.assertIsNotNone(outcome.match, outcome.reason)
        assert outcome.match is not None
        self.assertEqual(outcome.match.card.identifier, identifier)
        self.assertGreater(outcome.match.score, 0.0)

    def test_replay_dispatch_receipt_top_one(self) -> None:
        self.assert_top_card(
            TriggerContext(
                "post-dispatch",
                "orca.supervised-worker-dispatch",
                "worker-start 返回 input_accepted；查 dispatch-show 后再决定重试",
            ),
            "A",
        )

    def test_replay_three_copy_fingerprint_top_one(self) -> None:
        self.assert_top_card(
            TriggerContext(
                "pre-acceptance",
                "agent-plugin.installed-copy",
                "三端版本化缓存先规范化 CRLF 和 LF，再比较 SHA-256",
            ),
            "B",
        )

    def test_replay_snapshot_freshness_top_one(self) -> None:
        self.assert_top_card(
            TriggerContext(
                "pre-capacity-decision",
                "orca.codex-account-snapshot",
                "账户快照 updatedAt resetsAt windowMinutes usedPercent 扩产",
            ),
            "C",
        )

    def test_hard_filter_excludes_lexically_stronger_wrong_object(self) -> None:
        outcome = self.retriever.search(
            TriggerContext(
                "post-dispatch",
                "orca.supervised-worker-dispatch",
                "worker-start input_accepted 三端 SHA-256 CRLF LF 旧缓存 hash mismatch",
            )
        )

        self.assertIsNotNone(outcome.match)
        assert outcome.match is not None
        self.assertEqual(outcome.candidate_count, 2)
        self.assertEqual(outcome.match.card.identifier, "A")

    def test_equal_score_prefers_shorter_one_line_action(self) -> None:
        common = {
            "title": "并列卡",
            "stage": "same-stage",
            "object": "same.object",
            "operation": "same-operation",
            "aliases": ("same-signal",),
            "source": "K-test",
            "evidence": "测试夹具",
            "invalidates": "测试夹具",
        }
        retriever = KnowledgeRetriever(
            (
                RetrievalCard(
                    identifier="long",
                    one_line_action="这是更长的动作结论",
                    **common,
                ),
                RetrievalCard(
                    identifier="short",
                    one_line_action="短动作",
                    **common,
                ),
            )
        )

        outcome = retriever.search(
            TriggerContext("same-stage", "same.object", "same-signal")
        )

        self.assertIsNotNone(outcome.match)
        assert outcome.match is not None
        self.assertEqual(outcome.match.card.identifier, "short")

    def test_no_hard_filter_candidate_returns_safe_fallback(self) -> None:
        outcome = self.retriever.search(
            TriggerContext("pre-acceptance", "unknown.object", "SHA-256")
        )

        self.assertIsNone(outcome.match)
        self.assertEqual(outcome.reason, "no-hard-filter-candidate")

    def test_known_paraphrase_is_recalled_by_expanded_card(self) -> None:
        paraphrase = "配额读数没变还能否加开工作者"

        unfiltered = self.retriever.rank_unfiltered(paraphrase)
        self.assertTrue(unfiltered)
        self.assertEqual(unfiltered[0].card.identifier, "N")
        structured = self.retriever.search(
            TriggerContext(
                "pre-capacity-decision",
                "orca.codex-account-snapshot",
                paraphrase,
            )
        )
        self.assertIsNotNone(structured.match)
        assert structured.match is not None
        self.assertEqual(structured.reason, "matched")
        self.assertEqual(structured.match.card.identifier, "N")

    def test_cli_prints_action_source_and_evidence(self) -> None:
        with redirect_stdout(io.StringIO()) as output:
            exit_code = cli_main(
                [
                    "stage=post-dispatch; object=orca.supervised-worker-dispatch; "
                    "signals=worker-start input_accepted",
                    "--cards",
                    str(CARDS_PATH),
                ]
            )

        rendered = output.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("命中：卡 A（派发回执）", rendered)
        self.assertIn("动作：", rendered)
        self.assertIn("来源：", rendered)
        self.assertIn("证据：", rendered)

    def test_cli_no_match_prints_knowledge_index_fallback(self) -> None:
        with redirect_stdout(io.StringIO()) as output:
            exit_code = cli_main(
                [
                    "stage=pre-acceptance; object=unknown.object; signals=SHA-256",
                    "--cards",
                    str(CARDS_PATH),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertIn("未命中：no-hard-filter-candidate", output.getvalue())
        self.assertIn("knowledge/README.md", output.getvalue())


class NaturalBypassEvaluatorTests(unittest.TestCase):
    def test_registered_single_card_bucket_does_not_fail_evaluation(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(NATURAL_BYPASS_EVALUATOR)],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        current = json.loads(completed.stdout)["reports"][0]
        self.assertEqual(
            current["singleCardBuckets"],
            [
                {
                    "stage": "pre-github-publication",
                    "object": "github.multiline-markdown-body",
                }
            ],
        )
        self.assertEqual(current["unregisteredSingleCardBuckets"], [])


if __name__ == "__main__":
    unittest.main()
