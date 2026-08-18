#!/usr/bin/env python3
"""Reject private state-lab assets and credential-shaped values from public product files."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

SKIP_PARTS = {".git", ".venv", "node_modules", "__pycache__"}
NEGATIVE_FIXTURE_ROOT = Path("tests/fixtures/public-surface")
GRADUATED_FILES = {
    Path("authority/11-execution-state.md"),
    Path("work/records/2026-08-19-agent-system-consolidation/state-lab-selection.json"),
}
SECRET_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "github-token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "provider-key": re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    "assigned-secret": re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*[\"'][A-Za-z0-9_./+=-]{12,}[\"']"
    ),
}
PRIVATE_RESEARCH_PATTERN = re.compile(
    r"agent-state-lab/(?:experiments|handoffs|\.omp)|EXPERIMENT-[0-9]+(?:-AUDIT)?\.json|concepts/CONCEPTS\.md"
)
PRIVATE_PATH_PATTERN = re.compile(r"(?:/Users/[^/\s]+|/home/[^/\s]+|[A-Za-z]:\\Users\\[^\\\s]+)")


@dataclass(frozen=True)
class Finding:
    path: str
    rule: str


def iter_public_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        relative = path.relative_to(root)
        if relative == NEGATIVE_FIXTURE_ROOT or NEGATIVE_FIXTURE_ROOT in relative.parents:
            continue
        yield path


def scan(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in iter_public_files(root):
        relative = path.relative_to(root)
        if path.stat().st_size > 1_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for rule, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                findings.append(Finding(relative.as_posix(), rule))
        if PRIVATE_RESEARCH_PATTERN.search(text):
            findings.append(Finding(relative.as_posix(), "private-state-lab-asset"))
        if relative in GRADUATED_FILES and PRIVATE_PATH_PATTERN.search(text):
            findings.append(Finding(relative.as_posix(), "private-path-in-graduated-asset"))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve(strict=True)
    findings = scan(root)
    payload = {
        "status": "ok" if not findings else "rejected",
        "findings": [asdict(item) for item in findings],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    elif findings:
        for finding in findings:
            print(f"{finding.path}: {finding.rule}")
    else:
        print("public surface check passed")
    return 0 if not findings else 2


if __name__ == "__main__":
    raise SystemExit(main())
