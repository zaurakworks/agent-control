"""解析 ``knowledge/retrieval-cards.md`` 的结构化卡片表格。"""

from __future__ import annotations

import re
from pathlib import Path

from .models import RetrievalCard


CARD_HEADING = re.compile(r"^##\s+卡\s+([^：:]+)[：:]\s*(.+?)\s*$")
INLINE_CODE = re.compile(r"`([^`]+)`")
REQUIRED_FIELDS = (
    "stage",
    "object",
    "operation",
    "signals.aliases",
    "one-line-action",
    "source",
    "evidence",
    "invalidates",
)


class CardParseError(ValueError):
    """卡片正文不满足当前最小 schema。"""


def _strip_single_code_span(value: str) -> str:
    match = re.fullmatch(r"`([^`]*)`", value.strip())
    return match.group(1) if match else value.strip()


def _parse_table_row(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|")):
        return None

    inner = stripped[1:-1]
    key, separator, value = inner.partition("|")
    if not separator:
        return None

    key = _strip_single_code_span(key.strip())
    value = value.strip()
    if key in {"字段", "---", ""} or set(key) <= {"-", ":"}:
        return None
    return key, value


def _parse_aliases(raw: str) -> tuple[str, ...]:
    aliases = tuple(alias.strip() for alias in INLINE_CODE.findall(raw) if alias.strip())
    if aliases:
        return aliases

    fallback = tuple(
        part.strip()
        for part in re.split(r"[、,，;；]", raw)
        if part.strip()
    )
    if not fallback:
        raise CardParseError("signals.aliases 不能为空")
    return fallback


def _build_card(identifier: str, title: str, fields: dict[str, str]) -> RetrievalCard:
    missing = [field for field in REQUIRED_FIELDS if not fields.get(field, "").strip()]
    if missing:
        raise CardParseError(
            f"卡 {identifier}（{title}）缺少字段：{', '.join(missing)}"
        )

    return RetrievalCard(
        identifier=identifier.strip(),
        title=title.strip(),
        stage=_strip_single_code_span(fields["stage"]),
        object=_strip_single_code_span(fields["object"]),
        operation=_strip_single_code_span(fields["operation"]),
        aliases=_parse_aliases(fields["signals.aliases"]),
        one_line_action=fields["one-line-action"].strip(),
        source=fields["source"].strip(),
        evidence=fields["evidence"].strip(),
        invalidates=fields["invalidates"].strip(),
    )


def parse_retrieval_cards_text(text: str) -> tuple[RetrievalCard, ...]:
    """从 Markdown 正文解析全部 ``## 卡 X：标题`` 表格。"""

    cards: list[RetrievalCard] = []
    current: tuple[str, str] | None = None
    fields: dict[str, str] = {}

    def finish_current() -> None:
        nonlocal current, fields
        if current is not None:
            cards.append(_build_card(current[0], current[1], fields))
        current = None
        fields = {}

    for line in text.splitlines():
        if line.startswith("## "):
            finish_current()
            heading = CARD_HEADING.match(line)
            if heading:
                current = (heading.group(1).strip(), heading.group(2).strip())
            continue

        if current is None:
            continue

        row = _parse_table_row(line)
        if row is None:
            continue
        key, value = row
        if key in fields:
            raise CardParseError(f"卡 {current[0]} 的字段 {key} 重复")
        fields[key] = value

    finish_current()

    if not cards:
        raise CardParseError("没有找到任何结构化检索卡")
    identifiers = [card.identifier for card in cards]
    if len(identifiers) != len(set(identifiers)):
        raise CardParseError("卡片标识重复")
    return tuple(cards)


def parse_retrieval_cards(path: str | Path) -> tuple[RetrievalCard, ...]:
    """以 UTF-8 读取并解析卡片文件。"""

    card_path = Path(path)
    return parse_retrieval_cards_text(card_path.read_text(encoding="utf-8"))
