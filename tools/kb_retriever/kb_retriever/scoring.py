"""不依赖第三方库的轻量 BM25 实现。"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence

from .models import RetrievalCard, SearchResult


TOKEN_PATTERN = re.compile(
    r"[A-Za-z0-9]+(?:[._*-][A-Za-z0-9*]+)*|[\u3400-\u9fff]+"
)
CAMEL_PART = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+")


def _unique_in_order(tokens: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(token for token in tokens if token))


def tokenize(text: str) -> tuple[str, ...]:
    """为技术标识与中文生成稳定的词法 token，不做语义扩展。"""

    normalized = unicodedata.normalize("NFKC", text)
    tokens: list[str] = []
    for match in TOKEN_PATTERN.finditer(normalized):
        token = match.group(0)
        if "\u3400" <= token[0] <= "\u9fff":
            tokens.append(token)
            if len(token) == 1:
                continue
            tokens.extend(token[index : index + 2] for index in range(len(token) - 1))
            continue

        lowered = token.lower()
        tokens.append(lowered)
        for part in re.split(r"[._*-]+", token):
            if not part:
                continue
            tokens.append(part.lower())
            tokens.extend(piece.lower() for piece in CAMEL_PART.findall(part))
    return tuple(tokens)


def rank_cards(
    query: str,
    cards: Sequence[RetrievalCard],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> tuple[SearchResult, ...]:
    """在给定候选集合内按 Okapi BM25 降序排序。"""

    if not cards:
        return ()

    query_terms = _unique_in_order(tokenize(query))
    documents = [tokenize(card.index_text) for card in cards]
    frequencies = [Counter(document) for document in documents]
    lengths = [len(document) for document in documents]
    average_length = sum(lengths) / len(lengths) if lengths else 1.0

    document_frequency = {
        term: sum(1 for frequency in frequencies if term in frequency)
        for term in query_terms
    }
    document_count = len(cards)
    idf = {
        term: math.log(
            1.0
            + (document_count - frequency + 0.5) / (frequency + 0.5)
        )
        for term, frequency in document_frequency.items()
    }

    results: list[SearchResult] = []
    for card, frequency, length in zip(cards, frequencies, lengths, strict=True):
        score = 0.0
        matched: list[str] = []
        normalization = k1 * (1.0 - b + b * length / (average_length or 1.0))
        for term in query_terms:
            term_frequency = frequency.get(term, 0)
            if not term_frequency:
                continue
            matched.append(term)
            score += idf[term] * (
                term_frequency * (k1 + 1.0)
                / (term_frequency + normalization)
            )
        results.append(
            SearchResult(card=card, score=score, matched_terms=tuple(matched))
        )

    results.sort(
        key=lambda result: (
            -result.score,
            len(result.card.one_line_action),
            result.card.identifier,
        )
    )
    return tuple(results)
