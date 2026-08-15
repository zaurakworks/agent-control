"""Read and compare timezone-qualified timestamp scalars without host conversion."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Sequence


RFC3339 = re.compile(
    r"\A\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})\Z"
)


class ScalarError(ValueError):
    """Raised when a timestamp cannot be handled without guessing its semantics."""


@dataclass(frozen=True)
class TimestampScalar:
    """An exact serialized value together with its source."""

    value: str
    source: str
    keys: tuple[str, ...]

    def __post_init__(self) -> None:
        validate_rfc3339(self.value)
        if not self.source.strip():
            raise ScalarError("source must not be empty")
        if not self.keys:
            raise ScalarError("at least one JSON object key is required")


def validate_rfc3339(value: object) -> str:
    """Return an unchanged RFC 3339 scalar, rejecting converted host objects."""

    if not isinstance(value, str):
        raise TypeError("timestamp must remain a serialized string; host time objects are forbidden")
    if not RFC3339.fullmatch(value):
        raise ScalarError(f"timestamp is not timezone-qualified RFC 3339: {value!r}")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        datetime.fromisoformat(normalized)
    except ValueError as error:
        raise ScalarError(f"timestamp is not valid RFC 3339: {value!r}") from error
    return value


def extract_timestamp(
    payload: str | bytes | bytearray,
    *,
    keys: Sequence[str],
    source: str,
) -> TimestampScalar:
    """Extract a timestamp directly from serialized JSON and retain its exact value."""

    if not isinstance(payload, (str, bytes, bytearray)):
        raise TypeError("payload must be serialized JSON; parsed host objects are forbidden")
    if not source.strip():
        raise ScalarError("source must not be empty")
    if not keys:
        raise ScalarError("at least one JSON object key is required")

    try:
        current: object = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ScalarError("input is not valid UTF-8 JSON") from error

    for key in keys:
        if not isinstance(current, dict) or key not in current:
            path = ".".join(keys)
            raise ScalarError(f"JSON object key path not found: {path}")
        current = current[key]

    return TimestampScalar(
        value=validate_rfc3339(current),
        source=source,
        keys=tuple(keys),
    )


def matches_snapshot(current: TimestampScalar, expected: object) -> bool:
    """Compare exact scalars; do not normalize two representations of one instant."""

    if not isinstance(current, TimestampScalar):
        raise TypeError("current timestamp must come from extract_timestamp")
    return validate_rfc3339(current.value) == validate_rfc3339(expected)


def read_payload(path: str) -> bytes:
    if path == "-":
        return sys.stdin.buffer.read()
    return Path(path).read_bytes()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read or compare an RFC 3339 JSON scalar without host time conversion."
    )
    parser.add_argument("command", choices=("extract", "compare"))
    parser.add_argument("--input", default="-", help="JSON file, or - for standard input")
    parser.add_argument(
        "--key",
        action="append",
        required=True,
        help="JSON object key; repeat for a nested path",
    )
    parser.add_argument("--source", required=True, help="Human-readable source of the scalar")
    parser.add_argument("--expected", help="Exact expected scalar for compare")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        current = extract_timestamp(
            read_payload(args.input),
            keys=args.key,
            source=args.source,
        )
        if args.command == "extract":
            if args.expected is not None:
                raise ScalarError("--expected is only valid with compare")
            print(current.value)
            return 0
        if args.expected is None:
            raise ScalarError("compare requires --expected")
        if not matches_snapshot(current, args.expected):
            print(
                f"timestamp mismatch for {current.source}: "
                f"expected {args.expected!r}, received {current.value!r}",
                file=sys.stderr,
            )
            return 1
        print(current.value)
        return 0
    except (OSError, ScalarError, TypeError) as error:
        print(f"time-scalar: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
