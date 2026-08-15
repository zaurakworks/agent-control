"""检索卡、查询上下文与结果模型。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievalCard:
    """从 ``retrieval-cards.md`` 解析出的单张检索投影卡。"""

    identifier: str
    title: str
    stage: str
    object: str
    operation: str
    aliases: tuple[str, ...]
    one_line_action: str
    source: str
    evidence: str
    invalidates: str

    @property
    def index_text(self) -> str:
        """BM25 的词法索引面；动作结论不反向影响召回。"""

        return " ".join((self.operation, *self.aliases))


@dataclass(frozen=True)
class TriggerContext:
    """调用者主动构造的最小结构化查询上下文。"""

    stage: str
    object: str
    signals: str


@dataclass(frozen=True)
class SearchResult:
    """一张卡的排序结果。"""

    card: RetrievalCard
    score: float
    matched_terms: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalOutcome:
    """安全检索结果；未命中时由 ``reason`` 指示回退原因。"""

    match: SearchResult | None
    reason: str
    candidate_count: int
