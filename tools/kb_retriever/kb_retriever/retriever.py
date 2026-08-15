"""stage/object 硬筛之后的 BM25 检索。"""

from __future__ import annotations

from collections.abc import Iterable

from .models import RetrievalCard, RetrievalOutcome, SearchResult, TriggerContext
from .scoring import rank_cards


class KnowledgeRetriever:
    """对结构化检索卡执行硬筛和词法排序。"""

    def __init__(self, cards: Iterable[RetrievalCard]) -> None:
        self.cards = tuple(cards)
        if not self.cards:
            raise ValueError("检索索引至少需要一张卡")

    def search(self, context: TriggerContext) -> RetrievalOutcome:
        """返回一张最短动作卡；无法安全命中时给出回退原因。"""

        candidates = tuple(
            card
            for card in self.cards
            if card.stage == context.stage and card.object == context.object
        )
        if not candidates:
            return RetrievalOutcome(
                match=None,
                reason="no-hard-filter-candidate",
                candidate_count=0,
            )

        ranked = rank_cards(context.signals, candidates)
        if not ranked:
            return RetrievalOutcome(
                match=None,
                reason="no-ranked-candidate",
                candidate_count=len(candidates),
            )

        top = ranked[0]
        if top.score <= 0.0 and len(candidates) > 1:
            return RetrievalOutcome(
                match=None,
                reason="no-lexical-overlap",
                candidate_count=len(candidates),
            )

        reason = "matched" if top.score > 0.0 else "matched-by-structure"
        return RetrievalOutcome(
            match=top,
            reason=reason,
            candidate_count=len(candidates),
        )

    def rank_unfiltered(self, signals: str) -> tuple[SearchResult, ...]:
        """只供测试/诊断裸词法边界；产品路径不得跳过硬筛。"""

        return tuple(result for result in rank_cards(signals, self.cards) if result.score > 0.0)
