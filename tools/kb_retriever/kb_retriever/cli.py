"""知识检索 CLI。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from .context import ContextParseError, parse_trigger_context
from .parser import CardParseError, parse_retrieval_cards
from .retriever import KnowledgeRetriever


def locate_default_cards() -> Path:
    """从当前目录和包目录向上查找正式检索卡。"""

    roots: list[Path] = []
    for anchor in (Path.cwd().resolve(), Path(__file__).resolve().parent):
        roots.extend((anchor, *anchor.parents))
    for root in dict.fromkeys(roots):
        candidate = root / "knowledge" / "retrieval-cards.md"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("未找到 knowledge/retrieval-cards.md")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m kb_retriever",
        description="按 stage/object 硬筛后，以 BM25 返回一张知识检索卡。",
    )
    parser.add_argument(
        "context",
        help='查询上下文："stage=...; object=...; signals=..." 或 JSON 对象',
    )
    parser.add_argument("--cards", type=Path, help="检索卡 Markdown 路径")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    return parser


def _result_payload(outcome: object) -> dict[str, object]:
    match = outcome.match
    if match is None:
        return {
            "matched": False,
            "reason": outcome.reason,
            "candidateCount": outcome.candidate_count,
            "fallback": "转回 knowledge/README.md 人工选择当前 K 包。",
        }
    card = match.card
    return {
        "matched": True,
        "reason": outcome.reason,
        "candidateCount": outcome.candidate_count,
        "card": {"id": card.identifier, "title": card.title},
        "score": round(match.score, 6),
        "matchedTerms": list(match.matched_terms),
        "oneLineAction": card.one_line_action,
        "source": card.source,
        "evidence": card.evidence,
    }


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        context = parse_trigger_context(arguments.context)
        cards_path = arguments.cards or locate_default_cards()
        retriever = KnowledgeRetriever(parse_retrieval_cards(cards_path))
    except (ContextParseError, CardParseError, OSError, ValueError) as error:
        print(f"检索失败：{error}", file=sys.stderr)
        return 2

    outcome = retriever.search(context)
    payload = _result_payload(outcome)
    if arguments.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if not payload["matched"]:
        print(f"未命中：{payload['reason']}。{payload['fallback']}")
        return 0

    card = payload["card"]
    print(f"命中：卡 {card['id']}（{card['title']}）")
    print(f"得分：{payload['score']:.6f}")
    print(f"动作：{payload['oneLineAction']}")
    print(f"来源：{payload['source']}")
    print(f"证据：{payload['evidence']}")
    return 0
