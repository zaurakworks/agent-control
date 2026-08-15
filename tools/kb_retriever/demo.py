"""回放三个已登记的真实决策点。"""

from __future__ import annotations

from kb_retriever.cli import locate_default_cards
from kb_retriever.models import TriggerContext
from kb_retriever.parser import parse_retrieval_cards
from kb_retriever.retriever import KnowledgeRetriever


CASES = (
    (
        "派发回执",
        "A",
        TriggerContext(
            stage="post-dispatch",
            object="orca.supervised-worker-dispatch",
            signals=(
                "Orca Worker 走 worker-start 返回 input_accepted；需要用 "
                "dispatch-show 确认任务是否真正提交，mutation error 后再判断重试。"
            ),
        ),
    ),
    (
        "三端指纹",
        "B",
        TriggerContext(
            stage="pre-acceptance",
            object="agent-plugin.installed-copy",
            signals=(
                "验收 Plugin 三端目标版本与版本化缓存，先处理 CRLF/LF "
                "换行噪声，再比较 SHA-256，避免旧缓存和 hash mismatch 误判。"
            ),
        ),
    ),
    (
        "快照新鲜度",
        "C",
        TriggerContext(
            stage="pre-capacity-decision",
            object="orca.codex-account-snapshot",
            signals=(
                "Orca account 账户快照 usedPercent 是否可用于扩产：核对 "
                "updatedAt、resetsAt 与 windowMinutes 后再解释消耗差值。"
            ),
        ),
    ),
)


def main() -> int:
    cards_path = locate_default_cards()
    retriever = KnowledgeRetriever(parse_retrieval_cards(cards_path))
    failures = 0

    print(f"卡片来源：{cards_path}")
    print("证据边界：小样回放有效；不代表主动问路的自然采用率或产品采用。")
    for label, expected_id, context in CASES:
        outcome = retriever.search(context)
        if outcome.match is None:
            failures += 1
            print(f"[{label}] 未命中（{outcome.reason}）")
            continue
        result = outcome.match
        state = "命中" if result.card.identifier == expected_id else "误排"
        if state != "命中":
            failures += 1
        print(
            f"[{label}] {state} 卡 {result.card.identifier}（{result.card.title}）"
            f"，BM25={result.score:.3f}"
        )
        print(f"  动作：{result.card.one_line_action}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
