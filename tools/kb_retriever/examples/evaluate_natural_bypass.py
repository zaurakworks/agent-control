"""评估固定自然场景回放中的精确命中、次名差与改述漏检。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any


TOOL_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = TOOL_ROOT.parents[1]
if str(TOOL_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOL_ROOT))

from kb_retriever.models import RetrievalCard, TriggerContext  # noqa: E402
from kb_retriever.parser import (  # noqa: E402
    parse_retrieval_cards,
    parse_retrieval_cards_text,
)
from kb_retriever.retriever import KnowledgeRetriever  # noqa: E402
from kb_retriever.scoring import rank_cards  # noqa: E402


DEFAULT_CARDS_PATH = REPOSITORY_ROOT / "knowledge" / "retrieval-cards.md"
DEFAULT_SAMPLES_PATH = Path(__file__).with_name("natural_bypass_samples.json")
REGISTERED_SINGLE_CARD_BUCKETS = frozenset(
    {
        ("pre-github-publication", "github.multiline-markdown-body"),
    }
)


@dataclass(frozen=True)
class Sample:
    identifier: str
    checkpoint: str
    provenance: str
    stage: str
    object: str
    signals: str
    phrasing: str
    expected_card: str | None
    card_generation: str


def _load_samples(path: Path) -> tuple[Sample, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    samples: list[Sample] = []
    for row in payload["samples"]:
        samples.append(
            Sample(
                identifier=row["id"],
                checkpoint=row["checkpoint"],
                provenance=row["provenance"],
                stage=row["stage"],
                object=row["object"],
                signals=row["signals"],
                phrasing=row["phrasing"],
                expected_card=row["expectedCard"],
                card_generation=row["cardGeneration"],
            )
        )

    identifiers = [sample.identifier for sample in samples]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("样本 id 重复")
    return tuple(samples)


def _cards_from_git(ref: str) -> tuple[RetrievalCard, ...]:
    completed = subprocess.run(
        ["git", "show", f"{ref}:knowledge/retrieval-cards.md"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return parse_retrieval_cards_text(completed.stdout)


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _margin_distribution(margins: list[float]) -> dict[str, Any]:
    if not margins:
        return {
            "measurable": 0,
            "minimum": None,
            "p25": None,
            "median": None,
            "p75": None,
            "maximum": None,
            "bins": {},
        }

    bins = Counter()
    for margin in margins:
        if margin <= 0.0:
            bins["<=0"] += 1
        elif margin <= 1.0:
            bins["(0,1]"] += 1
        elif margin <= 3.0:
            bins["(1,3]"] += 1
        elif margin <= 5.0:
            bins["(3,5]"] += 1
        else:
            bins[">5"] += 1

    return {
        "measurable": len(margins),
        "minimum": round(min(margins), 6),
        "p25": round(_percentile(margins, 0.25) or 0.0, 6),
        "median": round(median(margins), 6),
        "p75": round(_percentile(margins, 0.75) or 0.0, 6),
        "maximum": round(max(margins), 6),
        "bins": dict(bins),
    }


def _render_buckets(buckets: set[tuple[str, str]]) -> list[dict[str, str]]:
    return [
        {"stage": stage, "object": object_name}
        for stage, object_name in sorted(buckets)
    ]


def evaluate(
    label: str,
    cards: tuple[RetrievalCard, ...],
    samples: tuple[Sample, ...],
) -> dict[str, Any]:
    retriever = KnowledgeRetriever(cards)
    known_cards = {card.identifier for card in cards}
    bucket_counts = Counter((card.stage, card.object) for card in cards)
    single_card_buckets = {
        bucket for bucket, count in bucket_counts.items() if count == 1
    }
    unregistered_single_card_buckets = (
        single_card_buckets - REGISTERED_SINGLE_CARD_BUCKETS
    )
    covered = [sample for sample in samples if sample.expected_card is not None]
    fallbacks = [sample for sample in samples if sample.expected_card is None]
    paraphrases = [sample for sample in covered if sample.phrasing == "paraphrase"]
    legacy = [sample for sample in covered if sample.card_generation == "A-K"]

    top_one_correct = 0
    legacy_correct = 0
    fallback_correct = 0
    paraphrase_misses = 0
    margins: list[float] = []
    rows: list[dict[str, Any]] = []

    for sample in samples:
        context = TriggerContext(sample.stage, sample.object, sample.signals)
        outcome = retriever.search(context)
        actual = outcome.match.card.identifier if outcome.match else None
        correct = actual == sample.expected_card
        if sample.expected_card is None:
            fallback_correct += int(correct)
        else:
            top_one_correct += int(correct)
            if sample.card_generation == "A-K":
                legacy_correct += int(correct)

        candidates = tuple(
            card
            for card in cards
            if card.stage == sample.stage and card.object == sample.object
        )
        ranked = rank_cards(sample.signals, candidates)
        positive_top_three = [
            result.card.identifier for result in ranked if result.score > 0.0
        ][:3]
        if sample in paraphrases and sample.expected_card not in positive_top_three:
            paraphrase_misses += 1

        margin = None
        if sample.expected_card is not None and len(ranked) >= 2 and ranked[0].score > 0.0:
            margin = ranked[0].score - ranked[1].score
            margins.append(margin)

        rows.append(
            {
                "id": sample.identifier,
                "expected": sample.expected_card,
                "expectedAvailable": (
                    sample.expected_card is None or sample.expected_card in known_cards
                ),
                "actual": actual,
                "correct": correct,
                "reason": outcome.reason,
                "candidateCount": outcome.candidate_count,
                "topScore": round(outcome.match.score, 6) if outcome.match else None,
                "runnerUpMargin": round(margin, 6) if margin is not None else None,
                "positiveTop3": positive_top_three,
            }
        )

    exact_gold_available = sum(
        1 for sample in covered if sample.expected_card in known_cards
    )
    return {
        "label": label,
        "cardCount": len(cards),
        "bucketCount": len(bucket_counts),
        "bucketSizes": sorted(bucket_counts.values()),
        "minimumBucketSize": min(bucket_counts.values()),
        "singleCardBuckets": _render_buckets(single_card_buckets),
        "unregisteredSingleCardBuckets": _render_buckets(
            unregistered_single_card_buckets
        ),
        "exactGoldAvailable": {
            "numerator": exact_gold_available,
            "denominator": len(covered),
        },
        "coveredTop1": {
            "numerator": top_one_correct,
            "denominator": len(covered),
        },
        "legacyTop1": {
            "numerator": legacy_correct,
            "denominator": len(legacy),
        },
        "safeFallback": {
            "numerator": fallback_correct,
            "denominator": len(fallbacks),
        },
        "paraphraseTop3Miss": {
            "numerator": paraphrase_misses,
            "denominator": len(paraphrases),
        },
        "runnerUpMargin": _margin_distribution(margins),
        "samples": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cards", type=Path, default=DEFAULT_CARDS_PATH)
    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES_PATH)
    parser.add_argument(
        "--baseline-ref",
        help="可选 Git ref；读取其中的 retrieval-cards.md 作为前态",
    )
    args = parser.parse_args(argv)

    samples = _load_samples(args.samples)
    current_cards = parse_retrieval_cards(args.cards)
    reports = []
    if args.baseline_ref:
        reports.append(
            evaluate(
                f"baseline:{args.baseline_ref}",
                _cards_from_git(args.baseline_ref),
                samples,
            )
        )
    current = evaluate("current", current_cards, samples)
    reports.append(current)
    print(json.dumps({"reports": reports}, ensure_ascii=False, indent=2))

    covered = current["coveredTop1"]
    fallback = current["safeFallback"]
    paraphrase = current["paraphraseTop3Miss"]
    current_is_valid = (
        not current["unregisteredSingleCardBuckets"]
        and covered["numerator"] == covered["denominator"]
        and fallback["numerator"] == fallback["denominator"]
        and paraphrase["numerator"] == 0
    )
    return 0 if current_is_valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
