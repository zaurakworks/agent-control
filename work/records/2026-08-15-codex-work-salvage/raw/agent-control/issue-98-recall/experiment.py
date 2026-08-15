from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Iterable


PACKAGE_FILES = {
    "K1": "project-instructions.md",
    "K2": "orca-supervised-dispatch.md",
    "K3": "github-closing-keywords.md",
    "K4": "claude-plugin-maintenance.md",
    "K5": "entry-sync.md",
    "K6": "newline-normalized-acceptance.md",
    "K7": "projectv2-single-select-options.md",
    "K8": "session-resumption-identity.md",
    "K9": "resource-observability-boundaries.md",
    "K10": "external-agent-capability-lifecycle.md",
    "K11": "github-graphql-mutation-recovery.md",
}

LATIN_RE = re.compile(r"[a-z0-9_./:@#-]+", re.IGNORECASE)
CJK_RE = re.compile(r"[\u3400-\u9fff]+")


def tokenize(text: str) -> list[str]:
    lowered = text.lower()
    tokens = LATIN_RE.findall(lowered)
    for run in CJK_RE.findall(lowered):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


def rank(scores: dict[str, float]) -> list[str]:
    return sorted(scores, key=lambda key: (-scores[key], int(key[1:])))


def grep_rank(query: str, corpus_counts: dict[str, Counter[str]]) -> list[str]:
    query_terms = list(dict.fromkeys(tokenize(query)))
    scores: dict[str, float] = {}
    for doc_id, counts in corpus_counts.items():
        covered = sum(1 for term in query_terms if counts[term] > 0)
        occurrences = sum(counts[term] for term in query_terms)
        scores[doc_id] = covered * 1_000_000.0 + occurrences
    return rank(scores)


class BM25:
    def __init__(self, corpus_tokens: dict[str, list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_counts = {key: Counter(value) for key, value in corpus_tokens.items()}
        self.doc_lens = {key: len(value) for key, value in corpus_tokens.items()}
        self.avgdl = statistics.fmean(self.doc_lens.values())
        self.n = len(corpus_tokens)
        self.df: Counter[str] = Counter()
        for tokens in corpus_tokens.values():
            self.df.update(set(tokens))

    def search(self, query: str) -> list[str]:
        scores: dict[str, float] = {}
        query_counts = Counter(tokenize(query))
        for doc_id, counts in self.doc_counts.items():
            score = 0.0
            dl = self.doc_lens[doc_id]
            for term, qtf in query_counts.items():
                tf = counts[term]
                if tf == 0:
                    continue
                df = self.df[term]
                idf = math.log(1.0 + (self.n - df + 0.5) / (df + 0.5))
                denom = tf + self.k1 * (1.0 - self.b + self.b * dl / self.avgdl)
                score += idf * (tf * (self.k1 + 1.0) / denom) * qtf
            scores[doc_id] = score
        return rank(scores)


def ollama_embed(model: str, inputs: list[str], timeout: float = 600.0) -> list[list[float]]:
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/embed",
        data=json.dumps({"model": model, "input": inputs, "truncate": True}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    embeddings = payload.get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(inputs):
        raise RuntimeError(f"unexpected Ollama response: {payload.keys()}")
    return embeddings


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def vector_rank(query_embedding: list[float], doc_embeddings: dict[str, list[float]]) -> list[str]:
    return rank({doc_id: cosine(query_embedding, embedding) for doc_id, embedding in doc_embeddings.items()})


def rrf_rank(*rankings: list[str], k: int = 60) -> list[str]:
    scores: dict[str, float] = {doc_id: 0.0 for doc_id in PACKAGE_FILES}
    for ranking in rankings:
        for position, doc_id in enumerate(ranking, start=1):
            scores[doc_id] += 1.0 / (k + position)
    return rank(scores)


def metric_rows(details: list[dict[str, object]], method: str) -> dict[str, object]:
    subsets: list[tuple[str, Iterable[dict[str, object]]]] = [
        ("overall", details),
        ("词面重合", (row for row in details if row["type"] == "词面重合")),
        ("改述", (row for row in details if row["type"] == "改述")),
    ]
    result: dict[str, object] = {}
    for name, rows_iter in subsets:
        rows = list(rows_iter)
        hits1 = sum(1 for row in rows if row["rankings"][method][0] == row["gold"])
        hits3 = sum(1 for row in rows if row["gold"] in row["rankings"][method][:3])
        result[name] = {
            "n": len(rows),
            "hit@1": hits1,
            "hit@3": hits3,
            "hit@1_rate": hits1 / len(rows),
            "hit@3_rate": hits3 / len(rows),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--queries", type=Path, default=Path(__file__).with_name("queries.json"))
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("results.json"))
    parser.add_argument("--model", default="qwen3-embedding:8b")
    args = parser.parse_args()

    knowledge_dir = args.repo / "knowledge"
    corpus: dict[str, str] = {
        doc_id: (knowledge_dir / filename).read_text(encoding="utf-8")
        for doc_id, filename in PACKAGE_FILES.items()
    }
    queries = json.loads(args.queries.read_text(encoding="utf-8"))
    if len(queries) < 20:
        raise ValueError("query set must contain at least 20 queries")
    if set(row["gold"] for row in queries) != set(PACKAGE_FILES):
        raise ValueError("query set must cover K1-K11")

    build_times: dict[str, float] = {}

    started = time.perf_counter()
    grep_tokens = {doc_id: tokenize(text) for doc_id, text in corpus.items()}
    corpus_counts = {doc_id: Counter(tokens) for doc_id, tokens in grep_tokens.items()}
    build_times["grep"] = time.perf_counter() - started

    started = time.perf_counter()
    bm25_tokens = {doc_id: tokenize(text) for doc_id, text in corpus.items()}
    bm25 = BM25(bm25_tokens)
    build_times["bm25"] = time.perf_counter() - started

    started = time.perf_counter()
    embedding_list = ollama_embed(args.model, [corpus[doc_id] for doc_id in PACKAGE_FILES])
    doc_embeddings = dict(zip(PACKAGE_FILES, embedding_list))
    build_times["vector"] = time.perf_counter() - started
    build_times["rrf_incremental"] = 0.0

    query_times = {method: [] for method in ("grep", "bm25", "vector", "rrf_fusion")}
    details: list[dict[str, object]] = []
    query_prefix = (
        "Instruct: Given a user question, retrieve the most relevant Chinese technical "
        "knowledge package.\nQuery: "
    )

    for row in queries:
        query = row["query"]

        started = time.perf_counter()
        grep_results = grep_rank(query, corpus_counts)
        query_times["grep"].append(time.perf_counter() - started)

        started = time.perf_counter()
        bm25_results = bm25.search(query)
        query_times["bm25"].append(time.perf_counter() - started)

        started = time.perf_counter()
        query_embedding = ollama_embed(args.model, [query_prefix + query])[0]
        vector_results = vector_rank(query_embedding, doc_embeddings)
        query_times["vector"].append(time.perf_counter() - started)

        started = time.perf_counter()
        rrf_results = rrf_rank(bm25_results, vector_results)
        query_times["rrf_fusion"].append(time.perf_counter() - started)

        details.append(
            {
                **row,
                "rankings": {
                    "grep": grep_results,
                    "bm25": bm25_results,
                    "vector": vector_results,
                    "rrf": rrf_results,
                },
                "gold_ranks": {
                    "grep": grep_results.index(row["gold"]) + 1,
                    "bm25": bm25_results.index(row["gold"]) + 1,
                    "vector": vector_results.index(row["gold"]) + 1,
                    "rrf": rrf_results.index(row["gold"]) + 1,
                },
            }
        )

    methods = ("grep", "bm25", "vector", "rrf")
    metrics = {method: metric_rows(details, method) for method in methods}
    totals = {method: sum(values) for method, values in query_times.items()}
    totals["rrf_end_to_end"] = totals["bm25"] + totals["vector"] + totals["rrf_fusion"]

    output = {
        "environment": {
            "model": args.model,
            "ollama_endpoint": "http://127.0.0.1:11434/api/embed",
            "corpus_docs": len(corpus),
            "corpus_chars": sum(len(text) for text in corpus.values()),
            "query_count": len(queries),
            "query_types": dict(Counter(row["type"] for row in queries)),
        },
        "method_definitions": {
            "grep": "查询拉丁词与中文二元组的去重覆盖数优先、总出现次数次优",
            "bm25": "同一分词上的 BM25(k1=1.5,b=0.75)",
            "vector": f"Ollama {args.model} 全包向量、查询 instruct 前缀、余弦排序",
            "rrf": "BM25 与向量排名的 RRF(k=60)",
        },
        "build_seconds": build_times,
        "query_seconds": {
            "total": totals,
            "median_per_query": {
                method: statistics.median(values) for method, values in query_times.items()
            },
        },
        "metrics": metrics,
        "details": details,
    }
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({key: output[key] for key in ("environment", "build_seconds", "query_seconds", "metrics")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
