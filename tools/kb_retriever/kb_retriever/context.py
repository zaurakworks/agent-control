"""把 CLI 的单个查询上下文参数转成结构化查询。"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping

from .models import TriggerContext


KEY_ALIASES = {
    "stage": "stage",
    "阶段": "stage",
    "object": "object",
    "对象": "object",
    "signal": "signals",
    "signals": "signals",
    "信号": "signals",
    "文本": "signals",
}
KEY_PATTERN = "|".join(re.escape(key) for key in KEY_ALIASES)
PAIR_PATTERN = re.compile(
    rf"(?:^|[;；\n]|\s+(?=(?:{KEY_PATTERN})\s*[:=]))"
    rf"\s*(?P<key>{KEY_PATTERN})\s*[:=]\s*"
    rf"(?P<value>.*?)"
    rf"(?=(?:[;；\n]|\s+(?=(?:{KEY_PATTERN})\s*[:=]))|$)",
    re.IGNORECASE,
)


class ContextParseError(ValueError):
    """CLI 查询上下文无法转换为最小结构化查询。"""


def _from_mapping(payload: Mapping[str, object]) -> TriggerContext:
    normalized: dict[str, str] = {}
    for key, value in payload.items():
        canonical = KEY_ALIASES.get(str(key).lower(), KEY_ALIASES.get(str(key)))
        if canonical is None:
            continue
        if isinstance(value, list):
            normalized[canonical] = " ".join(str(item) for item in value)
        elif value is not None:
            normalized[canonical] = str(value)
    return _validate_context(normalized)


def _validate_context(values: Mapping[str, str]) -> TriggerContext:
    missing = [key for key in ("stage", "object", "signals") if not values.get(key, "").strip()]
    if missing:
        raise ContextParseError(
            "查询上下文缺少字段："
            + ", ".join(missing)
            + "；请使用 stage=...; object=...; signals=..."
        )
    return TriggerContext(
        stage=values["stage"].strip(),
        object=values["object"].strip(),
        signals=values["signals"].strip(),
    )


def parse_trigger_context(raw: str) -> TriggerContext:
    """解析 JSON 或 ``key=value`` 形式的单个 CLI 参数。"""

    text = raw.strip()
    if not text:
        raise ContextParseError("查询上下文不能为空")

    if text.startswith("{"):
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as error:
            raise ContextParseError(f"查询上下文 JSON 无效：{error.msg}") from error
        if not isinstance(payload, dict):
            raise ContextParseError("查询上下文 JSON 必须是对象")
        return _from_mapping(payload)

    values: dict[str, str] = {}
    for match in PAIR_PATTERN.finditer(text):
        raw_key = match.group("key")
        canonical = KEY_ALIASES.get(raw_key.lower(), KEY_ALIASES.get(raw_key))
        if canonical is not None:
            values[canonical] = match.group("value").strip()
    return _validate_context(values)
