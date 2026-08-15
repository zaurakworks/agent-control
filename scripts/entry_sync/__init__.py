"""Generate and verify Agent-system entrypoint projections."""

from .core import (
    Comparison,
    EntrySyncError,
    TargetResult,
    compare_contents,
    find_markdown_section,
    generate_target,
    iter_targets,
    load_config,
    normalize_newlines,
    repository_root,
)

__all__ = [
    "Comparison",
    "EntrySyncError",
    "TargetResult",
    "compare_contents",
    "find_markdown_section",
    "generate_target",
    "iter_targets",
    "load_config",
    "normalize_newlines",
    "repository_root",
]
