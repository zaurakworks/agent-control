#!/usr/bin/env python3
"""Rewrite GitHub shorthand references to stable legacy-repository URLs.

The command is deliberately dry-run by default.  It scans Git-tracked Markdown,
protects Markdown code and links, verifies every target through GitHub, and only
writes files when ``--apply`` is supplied.
"""

from __future__ import annotations

import argparse
import bisect
import fnmatch
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping, Sequence


LEGACY_OWNER = "Eridanus117"
CURRENT_REPOSITORY = "agent-control"
KNOWN_REPOSITORIES = ("agent-control", "agent-plugins", "work-skills")
RUNTIME_EXCLUSIONS = (
    "tools/ops-metrics/current.*",
    "tools/ops-metrics/reports/**",
    "tools/worker_snapshot/current.*",
    "tools/worker_snapshot/samples/**",
)
IMMUTABLE_RAW_EXCLUSIONS = (
    "work/records/2026-08-10-federated-session-entry/raw/current-before-migration.md",
)
HISTORICAL_PREFIXES = ("work/history/", "work/records/")

REFERENCE_RE = re.compile(r"#(?P<number>[1-9][0-9]*)(?P<title>（[^）\r\n]*）)?")
FENCE_OPEN_RE = re.compile(r"^(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})")
URL_RE = re.compile(r"https?://[^\s<>]+")
DIRECT_REPOSITORY_RE = re.compile(
    r"(?:(?:Eridanus117|zaurakworks)/)?"
    r"(?P<repository>agent-control|agent-plugins|work-skills)$"
)
EXTERNAL_DIRECT_REPOSITORY_RE = re.compile(
    r"(?P<owner>[A-Za-z0-9_.-]+)/(?P<repository>[A-Za-z0-9_.-]+)$"
)
REPOSITORY_MENTION_RE = re.compile(
    r"(?<![A-Za-z0-9_-])(?:Eridanus117/|zaurakworks/)?"
    r"(?P<repository>agent-control|agent-plugins|work-skills)(?![A-Za-z0-9_-])"
)
CLAUSE_SEPARATORS = "\n。；;！？!?|"


@dataclass(frozen=True)
class ProtectedSpan:
    start: int
    end: int
    reason: str


@dataclass(frozen=True)
class Reference:
    path: str
    start: int
    end: int
    line: int
    column: int
    number: int
    label: str
    repository: str | None
    reason: str | None = None


@dataclass(frozen=True)
class TargetState:
    repository: str
    number: int
    kind: str | None
    url: str | None


@dataclass
class Analysis:
    texts: dict[str, str]
    references: list[Reference]
    target_states: dict[tuple[str, int], TargetState]
    rewrites: list[Reference]
    manual: list[Reference]
    protected: list[Reference]
    excluded: list[Reference]


TargetLookup = Callable[[Mapping[str, set[int]]], Mapping[tuple[str, int], TargetState]]


def _line_offsets(text: str) -> list[int]:
    offsets = [0]
    for match in re.finditer(r"\n", text):
        offsets.append(match.end())
    return offsets


def _location(offsets: Sequence[int], offset: int) -> tuple[int, int]:
    index = bisect.bisect_right(offsets, offset) - 1
    return index + 1, offset - offsets[index] + 1


def _fenced_code_spans(text: str) -> list[ProtectedSpan]:
    spans: list[ProtectedSpan] = []
    offset = 0
    open_start: int | None = None
    open_character = ""
    open_length = 0

    for line in text.splitlines(keepends=True):
        body = line.rstrip("\r\n")
        if open_start is None:
            match = FENCE_OPEN_RE.match(body)
            if match:
                fence = match.group("fence")
                open_start = offset
                open_character = fence[0]
                open_length = len(fence)
        else:
            closing = re.match(
                rf"^ {{0,3}}{re.escape(open_character)}{{{open_length},}}[ \t]*$",
                body,
            )
            if closing:
                spans.append(ProtectedSpan(open_start, offset + len(line), "fenced_code"))
                open_start = None
                open_character = ""
                open_length = 0
        offset += len(line)

    if open_start is not None:
        spans.append(ProtectedSpan(open_start, len(text), "fenced_code"))
    return spans


def _inside(spans: Sequence[ProtectedSpan], offset: int) -> ProtectedSpan | None:
    for span in spans:
        if span.start <= offset < span.end:
            return span
    return None


def _inline_code_spans(text: str, fenced: Sequence[ProtectedSpan]) -> list[ProtectedSpan]:
    spans: list[ProtectedSpan] = []
    cursor = 0
    while cursor < len(text):
        fenced_span = _inside(fenced, cursor)
        if fenced_span:
            cursor = fenced_span.end
            continue
        if text[cursor] != "`":
            cursor += 1
            continue

        run_end = cursor + 1
        while run_end < len(text) and text[run_end] == "`":
            run_end += 1
        delimiter = text[cursor:run_end]
        search = run_end
        close_end: int | None = None
        while search < len(text):
            candidate = text.find(delimiter, search)
            if candidate < 0 or "\n" in text[run_end:candidate]:
                break
            before_same = candidate > 0 and text[candidate - 1] == "`"
            after_index = candidate + len(delimiter)
            after_same = after_index < len(text) and text[after_index] == "`"
            if not before_same and not after_same:
                close_end = after_index
                break
            search = candidate + 1
        if close_end is None:
            line_end = text.find("\n", run_end)
            close_end = len(text) if line_end < 0 else line_end
        spans.append(ProtectedSpan(cursor, close_end, "inline_code"))
        cursor = close_end
    return spans


def _markdown_link_spans(
    text: str, code_spans: Sequence[ProtectedSpan]
) -> list[ProtectedSpan]:
    """Find inline and reference-style links without a Markdown dependency."""

    spans: list[ProtectedSpan] = []
    cursor = 0
    while cursor < len(text):
        code_span = _inside(code_spans, cursor)
        if code_span:
            cursor = code_span.end
            continue
        if text[cursor] != "[":
            cursor += 1
            continue

        depth = 1
        label_end = cursor + 1
        escaped = False
        while label_end < len(text) and depth:
            char = text[label_end]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == "[":
                depth += 1
            elif char == "]":
                depth -= 1
            label_end += 1
        if depth:
            cursor += 1
            continue

        suffix_start = label_end
        while suffix_start < len(text) and text[suffix_start] in " \t":
            suffix_start += 1
        if suffix_start >= len(text) or text[suffix_start] not in "([":
            # The outer brackets may contain an actual inner link.  Advance
            # one character so that nested link start remains discoverable.
            cursor += 1
            continue

        opener = text[suffix_start]
        closer = ")" if opener == "(" else "]"
        depth = 1
        suffix_end = suffix_start + 1
        escaped = False
        while suffix_end < len(text) and depth:
            char = text[suffix_end]
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == opener:
                depth += 1
            elif char == closer:
                depth -= 1
            suffix_end += 1
        if depth:
            cursor += 1
            continue
        spans.append(ProtectedSpan(cursor, suffix_end, "existing_link"))
        cursor = suffix_end
    return spans


def protected_spans(text: str) -> list[ProtectedSpan]:
    fenced = _fenced_code_spans(text)
    inline = _inline_code_spans(text, fenced)
    code = sorted([*fenced, *inline], key=lambda span: (span.start, span.end))
    links = _markdown_link_spans(text, code)
    urls = [ProtectedSpan(match.start(), match.end(), "raw_url") for match in URL_RE.finditer(text)]
    priority = {"fenced_code": 0, "inline_code": 1, "existing_link": 2, "raw_url": 3}
    return sorted(
        [*code, *links, *urls],
        key=lambda span: (span.start, priority[span.reason], -span.end),
    )


def _clause_bounds(text: str, offset: int) -> tuple[int, int]:
    start = offset
    while start > 0 and text[start - 1] not in CLAUSE_SEPARATORS:
        start -= 1
    end = offset
    while end < len(text) and text[end] not in CLAUSE_SEPARATORS:
        end += 1
    return start, end


def infer_repository(text: str, reference_start: int) -> tuple[str | None, str | None]:
    direct_start = max(0, reference_start - 80)
    direct = DIRECT_REPOSITORY_RE.search(text[direct_start:reference_start])
    if direct:
        return direct.group("repository"), None
    external_direct = EXTERNAL_DIRECT_REPOSITORY_RE.search(
        text[direct_start:reference_start]
    )
    if external_direct:
        identity = f"{external_direct.group('owner')}/{external_direct.group('repository')}"
        return None, f"external_repository_{identity}"

    clause_start, clause_end = _clause_bounds(text, reference_start)
    clause = text[clause_start:clause_end]
    local_reference_start = reference_start - clause_start
    current_number_match = REFERENCE_RE.match(text, reference_start)
    assert current_number_match is not None
    current_number = current_number_match.group("number")
    same_number_repositories = {
        repository
        for repository in KNOWN_REPOSITORIES
        if re.search(
            rf"{re.escape(repository)}(?:/(?:issues|pull)/|\s*(?:PR|Issue)?\s*#)"
            rf"{re.escape(current_number)}(?![0-9])",
            clause,
        )
    }
    if len(same_number_repositories) == 1:
        return next(iter(same_number_repositories)), None
    if len(same_number_repositories) > 1:
        return None, "ambiguous_cross_repository"

    mentions = list(REPOSITORY_MENTION_RE.finditer(clause))
    before = {
        match.group("repository")
        for match in mentions
        if match.end() <= local_reference_start
    }
    if len(before) == 1:
        return next(iter(before)), None
    if len(before) > 1:
        return None, "ambiguous_cross_repository"

    after = {
        match.group("repository")
        for match in mentions
        if match.start() > local_reference_start
    }
    if after - {CURRENT_REPOSITORY}:
        return None, "ambiguous_cross_repository"
    return CURRENT_REPOSITORY, None


def is_runtime_excluded(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(fnmatch.fnmatchcase(normalized, pattern) for pattern in RUNTIME_EXCLUSIONS)


def is_immutable_raw_excluded(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(
        fnmatch.fnmatchcase(normalized, pattern) for pattern in IMMUTABLE_RAW_EXCLUSIONS
    )


def is_historical(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return normalized.startswith(HISTORICAL_PREFIXES)


def scan_document(path: str, text: str) -> list[Reference]:
    spans = protected_spans(text)
    offsets = _line_offsets(text)
    references: list[Reference] = []
    for match in REFERENCE_RE.finditer(text):
        line, column = _location(offsets, match.start())
        protected = _inside(spans, match.start())
        repository: str | None = None
        reason: str | None = None
        if protected:
            reason = protected.reason
        elif is_runtime_excluded(path):
            reason = "excluded_runtime_artifact"
        elif is_immutable_raw_excluded(path):
            reason = "excluded_immutable_raw_snapshot"
        else:
            repository, reason = infer_repository(text, match.start())
        references.append(
            Reference(
                path=path,
                start=match.start(),
                end=match.end(),
                line=line,
                column=column,
                number=int(match.group("number")),
                label=match.group(0),
                repository=repository,
                reason=reason,
            )
        )
    return references


def scan_non_markdown_document(path: str, text: str) -> list[Reference]:
    offsets = _line_offsets(text)
    references: list[Reference] = []
    for match in REFERENCE_RE.finditer(text):
        line, column = _location(offsets, match.start())
        references.append(
            Reference(
                path=path,
                start=match.start(),
                end=match.end(),
                line=line,
                column=column,
                number=int(match.group("number")),
                label=match.group(0),
                repository=None,
                reason="excluded_non_markdown",
            )
        )
    return references


def _graphql_target_lookup(
    requested: Mapping[str, set[int]], *, owner: str = LEGACY_OWNER
) -> Mapping[tuple[str, int], TargetState]:
    states: dict[tuple[str, int], TargetState] = {}
    environment = os.environ.copy()
    environment["GH_PAGER"] = ""

    for repository, numbers in sorted(requested.items()):
        if repository not in KNOWN_REPOSITORIES:
            raise RuntimeError(f"unsupported repository: {repository}")
        ordered = sorted(numbers)
        for batch_start in range(0, len(ordered), 40):
            batch = ordered[batch_start : batch_start + 40]
            selections = " ".join(
                f"n_{number}: issueOrPullRequest(number: {number}) "
                "{ __typename ... on Issue { url } ... on PullRequest { url } }"
                for number in batch
            )
            query = (
                "query { repository(owner: "
                f"{json.dumps(owner)}, name: {json.dumps(repository)}) "
                f"{{ {selections} }} }}"
            )
            completed = subprocess.run(
                ["gh", "api", "graphql", "-f", f"query={query}"],
                cwd=None,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
            if not completed.stdout.strip():
                raise RuntimeError(
                    "GitHub verification returned no JSON: "
                    f"{completed.stderr.strip() or f'exit {completed.returncode}'}"
                )
            try:
                payload = json.loads(completed.stdout)
            except json.JSONDecodeError as error:
                raise RuntimeError(
                    f"GitHub verification returned invalid JSON: {completed.stdout[:500]}"
                ) from error

            errors = payload.get("errors", [])
            unexpected = [
                error
                for error in errors
                if "Could not resolve to an issue or pull request" not in error.get("message", "")
            ]
            if unexpected:
                raise RuntimeError(f"GitHub verification failed: {json.dumps(unexpected)}")
            repository_data = payload.get("data", {}).get("repository")
            if repository_data is None:
                raise RuntimeError(f"GitHub repository not found or inaccessible: {owner}/{repository}")

            for number in batch:
                item = repository_data.get(f"n_{number}")
                if item is None:
                    states[(repository, number)] = TargetState(repository, number, None, None)
                else:
                    states[(repository, number)] = TargetState(
                        repository=repository,
                        number=number,
                        kind=item["__typename"],
                        url=item.get("url"),
                    )
    return states


def analyze_documents(
    texts: Mapping[str, str], target_lookup: TargetLookup = _graphql_target_lookup
) -> Analysis:
    references = [
        reference
        for path, text in sorted(texts.items())
        for reference in scan_document(path, text)
    ]
    requested: dict[str, set[int]] = defaultdict(set)
    for reference in references:
        if reference.reason is None and reference.repository:
            requested[reference.repository].add(reference.number)

    target_states = dict(target_lookup(requested))
    rewrites: list[Reference] = []
    manual: list[Reference] = []
    protected: list[Reference] = []
    excluded: list[Reference] = []

    for reference in references:
        if reference.reason in {"fenced_code", "inline_code", "existing_link", "raw_url"}:
            protected.append(reference)
        elif reference.reason in {
            "excluded_runtime_artifact",
            "excluded_immutable_raw_snapshot",
        }:
            excluded.append(reference)
        elif reference.reason:
            manual.append(reference)
        elif reference.repository:
            state = target_states.get((reference.repository, reference.number))
            if state is None:
                raise RuntimeError(
                    f"verification omitted {reference.repository}#{reference.number}"
                )
            if state.kind is None:
                manual.append(
                    Reference(
                        **{
                            **reference.__dict__,
                            "reason": f"nonexistent_in_{reference.repository}",
                        }
                    )
                )
            else:
                rewrites.append(reference)

    return Analysis(
        texts=dict(texts),
        references=references,
        target_states=target_states,
        rewrites=rewrites,
        manual=manual,
        protected=protected,
        excluded=excluded,
    )


def analyze_repository(
    markdown_texts: Mapping[str, str],
    non_markdown_texts: Mapping[str, str],
    target_lookup: TargetLookup = _graphql_target_lookup,
) -> Analysis:
    analysis = analyze_documents(markdown_texts, target_lookup)
    non_markdown_references = [
        reference
        for path, text in sorted(non_markdown_texts.items())
        for reference in scan_non_markdown_document(path, text)
    ]
    analysis.texts.update(non_markdown_texts)
    analysis.references.extend(non_markdown_references)
    analysis.excluded.extend(non_markdown_references)
    return analysis


def replacement(reference: Reference, *, owner: str = LEGACY_OWNER) -> str:
    if not reference.repository:
        raise ValueError("cannot replace a reference without a repository")
    return (
        f"[{reference.label}]"
        f"(https://github.com/{owner}/{reference.repository}/issues/{reference.number})"
    )


def rewritten_texts(analysis: Analysis) -> dict[str, str]:
    by_path: dict[str, list[Reference]] = defaultdict(list)
    for reference in analysis.rewrites:
        by_path[reference.path].append(reference)

    result = dict(analysis.texts)
    for path, references in by_path.items():
        text = result[path]
        for reference in sorted(references, key=lambda item: item.start, reverse=True):
            text = text[: reference.start] + replacement(reference) + text[reference.end :]
        result[path] = text
    return result


def _context(text: str, reference: Reference) -> str:
    line_start = text.rfind("\n", 0, reference.start) + 1
    line_end = text.find("\n", reference.end)
    if line_end < 0:
        line_end = len(text)
    return text[line_start:line_end].strip().replace("\r", "")


def _format_reference(analysis: Analysis, reference: Reference) -> str:
    repository = reference.repository or "?"
    return (
        f"{reference.path}:{reference.line}:{reference.column} {reference.label} "
        f"repo={repository} reason={reference.reason} | "
        f"{_context(analysis.texts[reference.path], reference)}"
    )


def report(analysis: Analysis, *, apply: bool, changed_files: int) -> str:
    boundary = Counter(reference.reason for reference in analysis.protected)
    unique_target_kinds = Counter(
        state.kind for state in analysis.target_states.values() if state.kind is not None
    )
    reference_target_kinds = Counter(
        analysis.target_states[(reference.repository, reference.number)].kind
        for reference in analysis.rewrites
        if reference.repository is not None
    )
    cross_repository = [
        reference
        for reference in analysis.rewrites
        if reference.repository != CURRENT_REPOSITORY
    ]
    ambiguous = [
        reference
        for reference in analysis.manual
        if reference.reason == "ambiguous_cross_repository"
    ]
    nonexistent = [
        reference
        for reference in analysis.manual
        if reference.reason and reference.reason.startswith("nonexistent_in_")
    ]
    historical = [reference for reference in analysis.rewrites if is_historical(reference.path)]
    by_file = Counter(reference.path for reference in analysis.rewrites)
    cross_by_repository = Counter(reference.repository for reference in cross_repository)
    residual = [
        reference
        for reference in [*analysis.protected, *analysis.manual, *analysis.excluded]
        if reference.reason != "existing_link" and reference.reason != "raw_url"
    ]
    residual_by_reason = Counter(reference.reason for reference in residual)
    runtime_excluded = [
        reference
        for reference in analysis.excluded
        if reference.reason == "excluded_runtime_artifact"
    ]
    immutable_raw_excluded = [
        reference
        for reference in analysis.excluded
        if reference.reason == "excluded_immutable_raw_snapshot"
    ]
    non_markdown_excluded = [
        reference
        for reference in analysis.excluded
        if reference.reason == "excluded_non_markdown"
    ]

    lines = [
        f"mode: {'apply' if apply else 'dry-run'}",
        f"scanned_markdown_files: {sum(path.endswith('.md') for path in analysis.texts)}",
        f"audited_non_markdown_files: {sum(not path.endswith('.md') for path in analysis.texts)}",
        f"rewrite_hits: {len(analysis.rewrites)}",
        f"changed_files: {changed_files}",
        "boundary_counts:",
        f"  fenced_code: {boundary['fenced_code']}",
        f"  inline_code: {boundary['inline_code']}",
        f"  existing_link: {boundary['existing_link']}",
        f"  raw_url: {boundary['raw_url']}",
        f"  cross_repository_verified: {len(cross_repository)}",
        f"  cross_repository_ambiguous: {len(ambiguous)}",
        f"  verified_issue_references: {reference_target_kinds['Issue']}",
        f"  verified_pr_references: {reference_target_kinds['PullRequest']}",
        f"  verified_unique_issue_targets: {unique_target_kinds['Issue']}",
        f"  verified_unique_pr_targets: {unique_target_kinds['PullRequest']}",
        f"  nonexistent_targets: {len(nonexistent)}",
        f"  historical_rewrites: {len(historical)}",
        f"  runtime_artifact_exclusions: {len(runtime_excluded)}",
        f"  immutable_raw_snapshot_exclusions: {len(immutable_raw_excluded)}",
        f"  non_markdown_exclusions: {len(non_markdown_excluded)}",
        "cross_repository_by_repo:",
    ]
    if cross_by_repository:
        lines.extend(
            f"  {repository}: {count}"
            for repository, count in sorted(cross_by_repository.items())
        )
    else:
        lines.append("  (none)")
    lines.append("cross_repository_references:")
    if cross_repository:
        lines.extend(
            f"  {_format_reference(analysis, reference)}"
            for reference in sorted(
                cross_repository, key=lambda item: (item.path, item.line, item.column)
            )
        )
    else:
        lines.append("  (none)")
    lines.append("rewrite_hits_by_file:")
    if by_file:
        lines.extend(f"  {path}: {count}" for path, count in sorted(by_file.items()))
    else:
        lines.append("  (none)")

    lines.append(f"manual_review: {len(analysis.manual)}")
    if analysis.manual:
        lines.extend(
            f"  {_format_reference(analysis, reference)}"
            for reference in sorted(
                analysis.manual, key=lambda item: (item.path, item.line, item.column)
            )
        )
    else:
        lines.append("  (none)")

    lines.append(f"projected_unlinked_residual: {len(residual)}")
    lines.append("projected_unlinked_residual_by_reason:")
    if residual_by_reason:
        lines.extend(
            f"  {reason}: {count}"
            for reason, count in sorted(residual_by_reason.items())
        )
    else:
        lines.append("  (none)")
    lines.append("projected_unlinked_residual_details:")
    if residual:
        lines.extend(
            f"  {_format_reference(analysis, reference)}"
            for reference in sorted(residual, key=lambda item: (item.path, item.line, item.column))
        )
    else:
        lines.append("  (none)")
    return "\n".join(lines)


def tracked_files(root: Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files"],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="strict",
        check=True,
    )
    return [line for line in completed.stdout.splitlines() if line]


def tracked_markdown_files(root: Path) -> list[str]:
    return [path for path in tracked_files(root) if path.endswith(".md")]


def read_documents(root: Path, paths: Iterable[str]) -> tuple[dict[str, str], dict[str, bool]]:
    texts: dict[str, str] = {}
    boms: dict[str, bool] = {}
    for path in paths:
        data = (root / path).read_bytes()
        has_bom = data.startswith(b"\xef\xbb\xbf")
        texts[path] = data.decode("utf-8-sig" if has_bom else "utf-8")
        boms[path] = has_bom
    return texts, boms


def write_documents(
    root: Path,
    original: Mapping[str, str],
    updated: Mapping[str, str],
    boms: Mapping[str, bool],
) -> int:
    changed = 0
    for path, new_text in updated.items():
        if new_text == original[path]:
            continue
        encoded = new_text.encode("utf-8")
        if boms[path]:
            encoded = b"\xef\xbb\xbf" + encoded
        (root / path).write_bytes(encoded)
        changed += 1
    return changed


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="report only (the default)")
    mode.add_argument("--apply", action="store_true", help="write verified rewrites")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    root = args.root.resolve()
    paths = tracked_files(root)
    texts, boms = read_documents(root, paths)
    markdown_texts = {path: text for path, text in texts.items() if path.endswith(".md")}
    non_markdown_texts = {
        path: text for path, text in texts.items() if not path.endswith(".md")
    }
    analysis = analyze_repository(markdown_texts, non_markdown_texts)
    changed_files = 0
    if args.apply:
        changed_files = write_documents(root, texts, rewritten_texts(analysis), boms)
    else:
        changed_files = len({reference.path for reference in analysis.rewrites})
    print(report(analysis, apply=args.apply, changed_files=changed_files))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2) from error
