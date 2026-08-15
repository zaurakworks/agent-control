"""Core entrypoint projection and comparison logic."""

from __future__ import annotations

import difflib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


# A literal trailing "#" (as in "C#") is part of the title; only a
# whitespace-separated closing hash sequence is stripped.
HEADING_PATTERN = re.compile(
    r"^(?P<marks>#{1,6})[ \t]+(?P<title>.*?)(?:[ \t]+#+)?[ \t]*$",
    re.MULTILINE,
)
_FENCE_OPEN_PATTERN = re.compile(r"^ {0,3}(?P<fence>`{3,}|~{3,})[ \t]*(?P<info>.*)$")
SUPPORTED_CONFIG_VERSION = 1


class EntrySyncError(ValueError):
    """Raised when the declarative entrypoint contract cannot be rendered."""


@dataclass(frozen=True)
class MarkdownSection:
    """A Markdown ATX section including its heading and trailing separator."""

    heading: str
    level: int
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class Comparison:
    """A newline-normalized comparison result."""

    matches: bool
    expected: str
    actual: str
    diff: str


@dataclass(frozen=True)
class TargetResult:
    """Rendered target plus its resolved filesystem locations."""

    target_id: str
    scope: str
    source_path: Path
    current_path: Path
    output_path: Path
    content: str


def repository_root() -> Path:
    """Return the repository root for the installed module."""

    return Path(__file__).resolve().parents[2]


def normalize_newlines(text: str) -> str:
    """Convert CRLF and lone CR line endings to LF without other changes."""

    return text.replace("\r\n", "\n").replace("\r", "\n")


def read_utf8(path: Path) -> str:
    """Read a file without Python's implicit universal-newline conversion."""

    try:
        return path.read_bytes().decode("utf-8")
    except FileNotFoundError as error:
        raise EntrySyncError(f"目标不存在：{path}") from error
    except UnicodeDecodeError as error:
        raise EntrySyncError(f"目标不是 UTF-8：{path}: {error}") from error
    except OSError as error:
        raise EntrySyncError(f"无法读取目标：{path}: {error}") from error


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load and minimally validate the declarative target configuration."""

    config_path = path or Path(__file__).with_name("targets.json")
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EntrySyncError(f"无法读取入口同步配置 {config_path}: {error}") from error

    if config.get("version") != SUPPORTED_CONFIG_VERSION:
        raise EntrySyncError(
            "不支持的入口同步配置版本："
            f"{config.get('version')!r}（支持 {SUPPORTED_CONFIG_VERSION}）"
        )
    if not isinstance(config.get("source"), str):
        raise EntrySyncError("入口同步配置缺少字符串 source")
    targets = config.get("targets")
    if not isinstance(targets, list) or not targets:
        raise EntrySyncError("入口同步配置必须包含非空 targets 列表")

    seen: set[str] = set()
    for target in targets:
        if not isinstance(target, dict):
            raise EntrySyncError("每个 target 必须是对象")
        target_id = target.get("id")
        if not isinstance(target_id, str) or not target_id:
            raise EntrySyncError("每个 target 必须有非空字符串 id")
        if target_id in seen:
            raise EntrySyncError(f"target id 重复：{target_id}")
        seen.add(target_id)
        if target.get("scope") not in {"repository", "installed"}:
            raise EntrySyncError(f"{target_id}: scope 必须是 repository 或 installed")
        strategy = target.get("strategy")
        if strategy not in {"copy", "overlay", "pointer"}:
            raise EntrySyncError(
                f"{target_id}: strategy 必须是 copy、overlay 或 pointer"
            )
        if strategy == "pointer":
            pointer = target.get("pointer")
            pointer_format = target.get("pointer_format", "at_import")
            if target.get("scope") != "installed":
                raise EntrySyncError(
                    f"{target_id}: pointer strategy 只允许 installed target"
                )
            if (
                not isinstance(pointer, str)
                or not pointer
                or "\n" in pointer
                or "\r" in pointer
            ):
                raise EntrySyncError(
                    f"{target_id}: pointer strategy 必须声明单行非空 pointer"
                )
            if pointer_format not in {"at_import", "text"}:
                raise EntrySyncError(
                    f"{target_id}: pointer_format 必须是 at_import 或 text"
                )
        if not isinstance(target.get("output"), str):
            raise EntrySyncError(f"{target_id}: 缺少字符串 output")
        if not isinstance(target.get("destination"), dict):
            raise EntrySyncError(f"{target_id}: 缺少 destination 对象")
    return config


def iter_targets(
    config: Mapping[str, Any], scope: str = "all"
) -> Iterable[Mapping[str, Any]]:
    """Yield targets in declaration order for the requested scope."""

    if scope not in {"all", "repository", "installed"}:
        raise EntrySyncError(f"未知 scope：{scope}")
    for target in config["targets"]:
        if scope == "all" or target["scope"] == scope:
            yield target


def _selector(value: Any, context: str) -> tuple[str, int]:
    if not isinstance(value, dict):
        raise EntrySyncError(f"{context}: selector 必须是对象")
    heading = value.get("heading")
    level = value.get("level")
    if not isinstance(heading, str) or not heading:
        raise EntrySyncError(f"{context}: selector.heading 必须是非空字符串")
    if not isinstance(level, int) or not 1 <= level <= 6:
        raise EntrySyncError(f"{context}: selector.level 必须是 1..6")
    return heading, level


def _fenced_ranges(normalized: str) -> list[tuple[int, int]]:
    """Locate fenced code blocks so heading scans can skip their contents."""

    ranges: list[tuple[int, int]] = []
    fence_char = ""
    fence_length = 0
    fence_start = 0
    offset = 0
    for line in normalized.splitlines(keepends=True):
        content = line.rstrip("\n")
        if not fence_char:
            match = _FENCE_OPEN_PATTERN.match(content)
            # A backtick fence cannot carry backticks in its info string.
            if match and not (
                match.group("fence")[0] == "`" and "`" in match.group("info")
            ):
                fence_char = match.group("fence")[0]
                fence_length = len(match.group("fence"))
                fence_start = offset
        else:
            closing = re.fullmatch(
                rf" {{0,3}}{fence_char}{{{fence_length},}}[ \t]*", content
            )
            if closing:
                ranges.append((fence_start, offset + len(line)))
                fence_char = ""
        offset += len(line)
    if fence_char:
        ranges.append((fence_start, len(normalized)))
    return ranges


def scan_headings(normalized: str) -> list[re.Match[str]]:
    """Find ATX headings, ignoring any line inside a fenced code block."""

    fenced = _fenced_ranges(normalized)
    return [
        match
        for match in HEADING_PATTERN.finditer(normalized)
        if not any(start <= match.start() < end for start, end in fenced)
    ]


def find_markdown_section(text: str, heading: str, level: int) -> MarkdownSection:
    """Find one uniquely named ATX section and include its nested content."""

    normalized = normalize_newlines(text)
    headings = scan_headings(normalized)
    matches = [
        (index, match)
        for index, match in enumerate(headings)
        if len(match.group("marks")) == level and match.group("title") == heading
    ]
    if not matches:
        raise EntrySyncError(f"找不到 Markdown 章节：{'#' * level} {heading}")
    if len(matches) > 1:
        raise EntrySyncError(f"Markdown 章节不唯一：{'#' * level} {heading}")

    index, match = matches[0]
    end = len(normalized)
    for following in headings[index + 1 :]:
        if len(following.group("marks")) <= level:
            end = following.start()
            break
    return MarkdownSection(heading, level, match.start(), end, normalized[match.start() : end])


def _render_source_section(
    source_text: str,
    source_selector: Mapping[str, Any],
    target_selector: Mapping[str, Any],
) -> str:
    source_heading, source_level = _selector(source_selector, "source")
    target_heading, target_level = _selector(target_selector, "target")
    source_section = find_markdown_section(source_text, source_heading, source_level)
    lines = source_section.text.splitlines(keepends=True)
    if not lines:
        raise EntrySyncError(f"源章节为空：{'#' * source_level} {source_heading}")
    line_ending = "\n" if lines[0].endswith("\n") else ""
    lines[0] = f"{'#' * target_level} {target_heading}{line_ending}"
    return "".join(lines)


def apply_sections(
    source_text: str,
    target_text: str,
    declarations: Iterable[Mapping[str, Any]],
) -> str:
    """Apply mirrored sections while validating declared target-specific projections."""

    rendered = normalize_newlines(target_text)
    normalized_source = normalize_newlines(source_text)
    for index, declaration in enumerate(declarations):
        mode = declaration.get("mode")
        context = f"sections[{index}]"
        source_selector = declaration.get("source")
        target_selector = declaration.get("target")
        source_heading, source_level = _selector(source_selector, f"{context}.source")
        target_heading, target_level = _selector(target_selector, f"{context}.target")
        # Both sides are validated even for an intentional target-specific projection.
        find_markdown_section(normalized_source, source_heading, source_level)
        target_section = find_markdown_section(rendered, target_heading, target_level)

        if mode == "target_specific":
            if not declaration.get("reason"):
                raise EntrySyncError(f"{context}: target_specific 必须声明 reason")
            continue
        if mode != "mirror":
            raise EntrySyncError(f"{context}: mode 必须是 mirror 或 target_specific")

        replacement = _render_source_section(
            normalized_source, source_selector, target_selector
        )
        # The source owns section content; the target keeps only its structural
        # separator so mirroring a source middle section into a target EOF does
        # not invent an extra blank line.
        target_trailing_newlines = target_section.text[
            len(target_section.text.rstrip("\n")) :
        ]
        replacement = replacement.rstrip("\n") + target_trailing_newlines
        rendered = rendered[: target_section.start] + replacement + rendered[target_section.end :]
    return rendered


def _contained_path(base_path: Path, relative: str, context: str) -> Path:
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise EntrySyncError(f"{context} 必须是相对路径：{relative}")
    resolved_base = base_path.resolve()
    resolved = (resolved_base / relative_path).resolve()
    if not resolved.is_relative_to(resolved_base):
        raise EntrySyncError(f"{context} 越出声明根目录：{relative}")
    return resolved


def _resolve_destination(root: Path, destination: Mapping[str, Any]) -> Path:
    base = destination.get("base")
    relative = destination.get("path")
    if not isinstance(relative, str) or not relative:
        raise EntrySyncError("destination.path 必须是非空字符串")
    if base == "repository":
        return _contained_path(root, relative, "repository destination.path")
    if base == "home":
        return _contained_path(Path.home(), relative, "home destination.path")
    if base == "environment":
        variable = destination.get("variable")
        if not isinstance(variable, str) or not variable:
            raise EntrySyncError("environment destination 缺少 variable")
        value = os.environ.get(variable)
        if not value:
            raise EntrySyncError(f"环境变量未设置：{variable}")
        return _contained_path(Path(value), relative, f"{variable} destination.path")
    raise EntrySyncError(f"未知 destination.base：{base!r}")


def generate_target(
    root: Path,
    config: Mapping[str, Any],
    target: Mapping[str, Any],
    output_root: Path,
) -> TargetResult:
    """Render one target from the authoritative source and its declaration."""

    source_path = _contained_path(root, config["source"], "source")
    source_text = normalize_newlines(read_utf8(source_path))
    destination_base = target["destination"].get("base")
    if target["scope"] == "repository" and destination_base != "repository":
        raise EntrySyncError(
            f"{target['id']}: repository target 必须使用 repository destination"
        )
    if target["scope"] == "installed" and destination_base == "repository":
        raise EntrySyncError(
            f"{target['id']}: installed target 不能使用 repository destination"
        )
    current_path = _resolve_destination(root, target["destination"])
    strategy = target["strategy"]
    if strategy == "copy":
        content = source_text
    elif strategy == "pointer":
        pointer = target["pointer"]
        if target.get("pointer_format", "at_import") == "at_import":
            content = f"@{pointer}\n"
        else:
            content = (
                "本文件只作指针；开始任何工作前，先读取 "
                f"`{pointer}` 作为全局规则正文。\n"
            )
    else:
        current_text = read_utf8(current_path)
        sections = target.get("sections")
        if not isinstance(sections, list) or not sections:
            raise EntrySyncError(f"{target['id']}: overlay target 缺少 sections")
        content = apply_sections(source_text, current_text, sections)

    return TargetResult(
        target_id=target["id"],
        scope=target["scope"],
        source_path=source_path,
        current_path=current_path,
        output_path=_contained_path(output_root, target["output"], "target.output"),
        content=normalize_newlines(content),
    )


def compare_contents(
    expected: str,
    actual: str,
    expected_name: str = "generated",
    actual_name: str = "current",
    context_lines: int = 3,
) -> Comparison:
    """Compare content after newline normalization and prepare a unified diff."""

    normalized_expected = normalize_newlines(expected)
    normalized_actual = normalize_newlines(actual)
    matches = normalized_expected == normalized_actual
    diff = ""
    if not matches:
        diff = "".join(
            difflib.unified_diff(
                normalized_actual.splitlines(keepends=True),
                normalized_expected.splitlines(keepends=True),
                fromfile=actual_name,
                tofile=expected_name,
                n=context_lines,
            )
        )
    return Comparison(matches, normalized_expected, normalized_actual, diff)


def repository_write_bytes(content: str, current_bytes: bytes | None) -> bytes:
    """Encode generated text using an existing repository file's newline convention."""

    normalized = normalize_newlines(content)
    uses_only_crlf = False
    if current_bytes:
        uses_only_crlf = (
            b"\r\n" in current_bytes
            and b"\n" not in current_bytes.replace(b"\r\n", b"")
        )
    if uses_only_crlf:
        normalized = normalized.replace("\n", "\r\n")
    return normalized.encode("utf-8")


def replace_files_atomically(writes: Sequence[tuple[Path, bytes]]) -> None:
    """Stage every payload beside its destination, then swap all in via os.replace.

    A staging failure leaves every destination untouched; os.replace keeps each
    destination either fully old or fully new, never truncated.
    """

    staged: list[tuple[Path, Path]] = []
    try:
        try:
            for path, data in writes:
                path.parent.mkdir(parents=True, exist_ok=True)
                descriptor, temp_name = tempfile.mkstemp(
                    dir=path.parent, prefix=f"{path.name}.", suffix=".entry-sync.tmp"
                )
                with os.fdopen(descriptor, "wb") as handle:
                    handle.write(data)
                staged.append((Path(temp_name), path))
            for temp_path, path in staged:
                os.replace(temp_path, path)
        except OSError as error:
            raise EntrySyncError(f"原子写入失败：{error}") from error
    finally:
        for temp_path, _ in staged:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
