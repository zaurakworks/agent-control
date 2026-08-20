"""Client-agnostic primitives shared by every CAP client adapter.

These moved out of `agent_system.omp.runtime` unchanged. They encode CAP-wide
invariants -- canonical digests, content-addressed tree hashing, and the path
safety rules for the managed state root -- so a second adapter must reuse them
rather than restate them. Anything that depends on one client's native schema
stays in that client's module.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
import os
import shutil
import stat
import sys
from pathlib import Path


class AdapterError(ValueError):
    """Report a fail-closed adapter error."""


def _digest_bytes(payload: bytes) -> str:
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"

def _digest_json(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _digest_bytes(payload)

def _assert_managed_path(
    root: Path, candidate: Path, label: str, *, allow_missing: bool = False
) -> Path:
    root = root.expanduser().absolute()
    candidate = candidate.expanduser().absolute()
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise AdapterError(f"{label} is outside the CAP state root") from error
    if not relative.parts:
        raise AdapterError(f"{label} must not be the CAP state root")
    current = root
    for part in relative.parts:
        current = current / part
        if not current.exists() and not current.is_symlink():
            if allow_missing:
                continue
            raise AdapterError(f"{label} does not exist")
        info = current.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise AdapterError(f"{label} contains a symlink")
    return candidate

def _validate_private_runtime(
    root: Path, label: str, *, private_root: Path
) -> None:
    info = root.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise AdapterError(
            f"{label} must be a directory"
        )
    if hasattr(os, "geteuid"):
        if info.st_uid != os.geteuid():
            raise AdapterError(
                f"{label} must be a current-user directory"
            )
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise AdapterError(
                f"{label} must not grant group or other access"
            )
        return

    # Windows has no geteuid, and POSIX mode bits are a no-op there, so the
    # two checks above cannot run. Substitute the constraints that are
    # enforceable: the directory must stay inside the CAP-managed root, and
    # no component may be a symlink or junction pointing elsewhere.
    # This is a weaker guarantee than the POSIX branch -- it does not read
    # ACLs, so a managed root that grants other principals write access
    # still passes. Tracked in zaurakworks/agent-system#83.
    managed = private_root.expanduser().absolute()
    candidate = root.expanduser().absolute()
    try:
        relative = candidate.relative_to(managed)
    except ValueError as error:
        raise AdapterError(
            f"{label} must stay inside the CAP-managed root"
        ) from error
    current = managed
    for part in relative.parts:
        current = current / part
        entry = current.lstat()
        reparse = getattr(entry, "st_file_attributes", 0) & (
            stat.FILE_ATTRIBUTE_REPARSE_POINT
        )
        if stat.S_ISLNK(entry.st_mode) or reparse:
            raise AdapterError(
                f"{label} contains a symlink or junction"
            )

def _reject_unsafe_tree(root: Path, label: str) -> None:
    for path in [root, *root.rglob("*")]:
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise AdapterError(f"{label} contains a symlink")
        if stat.S_ISREG(info.st_mode) and info.st_nlink != 1:
            raise AdapterError(f"{label} contains a hard-linked file")
        if not stat.S_ISDIR(info.st_mode) and not stat.S_ISREG(info.st_mode):
            raise AdapterError(f"{label} contains a special file")

def _safe_remove_tree(
    root: Path,
    candidate: Path,
    label: str,
    *,
    protected: tuple[Path, ...] = (),
) -> bool:
    if not candidate.exists() and not candidate.is_symlink():
        return False
    _assert_managed_path(root, candidate, label)
    resolved = candidate.expanduser().absolute()
    for guarded in protected:
        guarded = guarded.expanduser().absolute()
        if guarded == resolved or guarded.is_relative_to(resolved):
            # `_assert_managed_path` only rejects escaping the CAP state root;
            # it cannot tell that a legitimate in-root target is an ancestor of
            # live state. Without this check a cleanup entry that names a parent
            # directory silently takes the global render CAS with it.
            raise AdapterError(
                f"{label} would remove preserved state: {guarded}"
            )
    _reject_unsafe_tree(candidate, label)
    shutil.rmtree(candidate)
    return True

def _tree_digest(root: Path, *, exclude: set[str] | None = None) -> str:
    excluded = exclude or set()
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        info = path.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise AdapterError("profile generation contains a symlink")
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        if stat.S_ISDIR(info.st_mode):
            digest.update(b"d\0")
        elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
            digest.update(b"f\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
        else:
            raise AdapterError(
                "profile generation contains an unsafe file"
            )
    return f"sha256:{digest.hexdigest()}"

def _deep_overlay(
    base: Mapping[str, object], override: Mapping[str, object]
) -> dict[str, object]:
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _deep_overlay(existing, value)
        else:
            merged[key] = value
    return merged

def _replace_generation_placeholder(
    value: object, generation: Path
) -> object:
    if isinstance(value, str):
        return value.replace(
            "<PROFILE_GENERATION>", str(generation)
        )
    if isinstance(value, list):
        return [
            _replace_generation_placeholder(item, generation)
            for item in value
        ]
    if isinstance(value, dict):
        return {
            key: _replace_generation_placeholder(item, generation)
            for key, item in value.items()
        }
    return value
