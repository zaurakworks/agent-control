#!/usr/bin/env python3
"""Lock, render, launch, and observe explicit project capability profiles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
import tomllib
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator, Mapping, Sequence
from urllib.parse import urlsplit


RENDERER_VERSION = "profile-renderer-v1"
LOCK_VERSION = 1
MANIFEST_VERSION = 1
CLIENTS = ("codex", "qoder", "omp")
CLIENT_EXECUTABLES = {"codex": "codex", "qoder": "qoder", "omp": "omp"}
CLIENT_ADAPTER_VERSION = 7
IDENTIFIER = re.compile(r"^[a-z][a-z0-9-]*$")
CAPABILITY_KINDS = ("skills", "mcp", "hooks", "plugins")
PROJECT_BYPASS_DIRS = frozenset(
    {
        ".agents",
        ".claude",
        ".codeium",
        ".codex",
        ".cursor",
        ".gemini",
        ".omp",
        ".qoder",
        ".vscode",
        ".windsurf",
    }
)
PROJECT_BYPASS_FILES = frozenset(
    {
        "AGENTS.md",
        "AGENTS.override.md",
        "CLAUDE.md",
        "CLAUDE.local.md",
        "QODER.md",
        "QODER.local.md",
    }
)
PROJECT_BYPASS_PATHS = frozenset(
    {
        ".mcp.json",
        "mcp.json",
        ".claude/.mcp.json",
        ".claude/mcp.json",
        ".cursor/mcp.json",
        ".gemini/settings.json",
        ".vscode/mcp.json",
        ".windsurf/mcp_config.json",
        "opencode.json",
    }
)
GLOBAL_CAPABILITY_PATHS = (
    ".agents/hooks",
    ".agents/plugins",
    ".agents/skills",
    ".claude/mcp.json",
    ".codeium/windsurf/mcp_config.json",
    ".codex/AGENTS.md",
    ".codex/AGENTS.override.md",
    ".codex/hooks",
    ".codex/hooks.json",
    ".codex/plugins",
    ".codex/skills",
    ".cursor/mcp.json",
    ".mcp.json",
    ".omp/AGENTS.md",
    ".omp/hooks",
    ".omp/mcp.json",
    ".omp/plugins",
    ".omp/skills",
    ".omp/agent/AGENTS.md",
    ".omp/agent/extensions",
    ".omp/agent/hooks",
    ".omp/agent/mcp.json",
    ".omp/agent/.mcp.json",
    ".omp/agent/plugins",
    ".omp/agent/skills",
    ".pi/agent/AGENTS.md",
    ".pi/agent/extensions",
    ".pi/agent/hooks",
    ".pi/agent/mcp.json",
    ".pi/agent/skills",
    ".qoder/AGENTS.md",
    ".qoder/QODER.md",
    ".qoder/hooks",
    ".qoder/mcp.json",
    ".qoder/plugins",
    ".qoder/skills",
)
GLOBAL_FLOOR_PATHS = frozenset({".codex/AGENTS.md", ".qoder/AGENTS.md"})
HOST_FLOOR_TEXT = """# Agent 宿主底座

- 业务指令与能力必须由当前 Git 项目显式声明；模板只用于生成项目内副本，不是运行时来源。
- 全局不得启用业务 Skills、MCP、hooks、plugins、rules、agents、marketplaces 或 provider 覆盖。
- 项目需要本机增量时，必须在项目 manifest 中显式允许；不得因目录位置自动继承。
- 项目缺少 `AGENTS.md` 或 `.cap/manifest.toml` 时，先警告再按用户要求继续；不得从用户目录补齐业务能力。
- 认证、运行态与 UI 偏好可以留在用户目录，但不得向模型注入业务上下文。
- 用户当轮明确指令与平台安全约束优先。
"""
CODEX_CAPABILITY_FEATURES = frozenset(
    {
        "apps",
        "browser_use",
        "browser_use_external",
        "browser_use_full_cdp_access",
        "computer_use",
        "goals",
        "hooks",
        "image_generation",
        "in_app_browser",
        "memories",
        "multi_agent",
        "multi_agent_v2",
        "plugin_sharing",
        "plugins",
        "recommended_plugins",
        "remote_plugin",
        "skill_mcp_dependency_install",
        "skill_search",
        "tool_suggest",
        "workspace_dependencies",
    }
)
CODEX_RUNTIME_ONLY_FEATURES = frozenset({"prevent_idle_sleep"})
CODEX_RUNTIME_ONLY_KEYS = frozenset(
    {
        "approval_policy",
        "analytics",
        "approvals_reviewer",
        "cli_auth_credentials_store",
        "feedback",
        "desktop",
        "features",
        "history",
        "model",
        "model_reasoning_effort",
        "model_reasoning_summary",
        "notice",
        "sandbox_mode",
        "tool_output_token_limit",
        "projects",
        "tui",
    }
)
CODEX_CAPABILITY_KEYS = frozenset(
    {
        "agents",
        "apps",
        "developer_instructions",
        "hooks",
        "marketplaces",
        "mcp_servers",
        "model_instructions_file",
        "model_provider",
        "model_providers",
        "personality",
        "plugins",
        "skills",
    }
)
ORCA_MANAGED_EXTENSION_NAMES = frozenset(
    {"orca-agent-status.ts", "orca-prefill.ts", "orca-titlebar-spinner.ts"}
)
CODEX_EXPLICITLY_DISABLABLE_ROOTS = frozenset({"agents", "apps", "marketplaces"})
GLOBAL_NATIVE_ROOTS = (
    ".agents",
    ".claude",
    ".codeium",
    ".codex",
    ".config/opencode",
    ".cursor",
    ".gemini",
    ".omp",
    ".pi",
    ".qoder",
)
AMBIENT_CONFIG_ENV = frozenset(
    {
        "CODEX_ACCESS_TOKEN",
        "CODEX_API_KEY",
        "CODEX_HOME",
        "OMP_AUTH_BROKER_TOKEN",
        "OMP_AUTH_BROKER_URL",
        "OMP_PROFILE",
        "OPENAI_API_KEY",
        "PI_CODING_AGENT_DIR",
        "PI_CONFIG_DIR",
        "PI_CONFIG_FILES",
        "PI_PROFILE",
        "QODER_CONFIG_DIR",
        "QODER_WORKING_DIR",
    }
)
OMP_AMBIENT_AUTH_ENV = frozenset(
    {
        "AIAND_API_KEY",
        "AIMLAPI_API_KEY",
        "AI_GATEWAY_API_KEY",
        "ALIBABA_CODING_PLAN_API_KEY",
        "ALIBABA_TOKEN_PLAN_API_KEY",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_BASE_URL",
        "ANTHROPIC_CUSTOM_HEADERS",
        "ANTHROPIC_FOUNDRY_API_KEY",
        "ANTHROPIC_OAUTH_TOKEN",
        "AWS_CONFIG_FILE",
        "ANTHROPIC_SEARCH_API_KEY",
        "ANTHROPIC_SEARCH_BASE_URL",
        "AWS_ACCESS_KEY_ID",
        "AWS_BEARER_TOKEN_BEDROCK",
        "AWS_CONTAINER_AUTHORIZATION_TOKEN",
        "AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE",
        "AWS_CONTAINER_CREDENTIALS_FULL_URI",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
        "AWS_EC2_METADATA_DISABLED",
        "AWS_EC2_METADATA_SERVICE_ENDPOINT",
        "AWS_PROFILE",
        "AWS_EC2_METADATA_SERVICE_ENDPOINT_MODE",
        "AWS_ROLE_ARN",
        "AWS_ROLE_SESSION_NAME",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "AWS_SHARED_CREDENTIALS_FILE",
        "AWS_WEB_IDENTITY_TOKEN_FILE",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_BASE_URL",
        "AZURE_OPENAI_DEPLOYMENT_NAME_MAP",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_RESOURCE_NAME",
        "BAILIAN_TOKEN_PLAN_API_KEY",
        "BASETEN_API_KEY",
        "BRAVE_API_KEY",
        "CEREBRAS_API_KEY",
        "CLAUDE_CODE_USE_FOUNDRY",
        "CLAUDE_CODE_CLIENT_CERT",
        "CLAUDE_CODE_CLIENT_KEY",
        "CLOUDFLARE_AI_GATEWAY_API_KEY",
        "COPILOT_GITHUB_TOKEN",
        "CLOUDSDK_CONFIG",
        "COREWEAVE_API_KEY",
        "CURSOR_ACCESS_TOKEN",
        "CURSOR_API_KEY",
        "DEEPSEEK_API_KEY",
        "DEVIN_API_KEY",
        "EXA_API_KEY",
        "FIRECRAWL_API_KEY",
        "FIREPASS_API_KEY",
        "FIREWORKS_API_KEY",
        "FUGU_BASE_URL",
        "FOUNDRY_BASE_URL",
        "FUGU_API_KEY",
        "GEMINI_API_KEY",
        "GITLAB_TOKEN",
        "GCLOUD_PROJECT",
        "GMI_API_KEY",
        "GOOGLE_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS",
        "GOOGLE_CLOUD_ACCESS_TOKEN",
        "GOOGLE_CLOUD_API_KEY",
        "GOOGLE_CLOUD_LOCATION",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_PROJECT_ID",
        "GOOGLE_VERTEX_LOCATION",
        "GCP_PROJECT",
        "GROQ_API_KEY",
        "HF_TOKEN",
        "HUGGINGFACE_HUB_TOKEN",
        "JINA_API_KEY",
        "KAGI_API_KEY",
        "KILO_API_KEY",
        "KIMI_API_KEY",
        "KIMI_CODE_BASE_URL",
        "KIMI_CODE_OAUTH_HOST",
        "KIMI_OAUTH_HOST",
        "KIMI_SEARCH_API_KEY",
        "LITELLM_API_KEY",
        "LITELLM_BASE_URL",
        "LLAMA_CPP_API_KEY",
        "LLAMA_CPP_BASE_URL",
        "LM_STUDIO_API_KEY",
        "LM_STUDIO_BASE_URL",
        "META_API_KEY",
        "MINIMAX_API_KEY",
        "MINIMAX_CODE_API_KEY",
        "MINIMAX_CODE_CN_API_KEY",
        "MISTRAL_API_KEY",
        "MODEL_API_KEY",
        "MOONSHOT_API_KEY",
        "MOONSHOT_BASE_URL",
        "MOONSHOT_SEARCH_API_KEY",
        "NANO_GPT_API_KEY",
        "NOVITA_API_KEY",
        "NVIDIA_API_KEY",
        "NODE_EXTRA_CA_CERTS",
        "OLLAMA_API_KEY",
        "OLLAMA_CLOUD_API_KEY",
        "OPENCODE_API_KEY",
        "OPENAI_API_KEY",
        "OLLAMA_BASE_URL",
        "OLLAMA_HOST",
        "OPENAI_BASE_URL",
        "OPENAI_CODEX_OAUTH_TOKEN",
        "OPENROUTER_API_KEY",
        "PARALLEL_API_KEY",
        "PERPLEXITY_API_KEY",
        "PERPLEXITY_COOKIES",
        "QIANFAN_API_KEY",
        "QWEN_OAUTH_TOKEN",
        "QWEN_PORTAL_API_KEY",
        "SAKANA_API_KEY",
        "SILICONFLOW_API_KEY",
        "SILICONFLOW_CN_API_KEY",
        "SYNTHETIC_API_KEY",
        "TAVILY_API_KEY",
        "TINYFISH_API_KEY",
        "TOGETHER_API_KEY",
        "UMANS_AI_CODING_PLAN_API_KEY",
        "SAKANA_BASE_URL",
        "VENICE_API_KEY",
        "VERCEL_AI_GATEWAY_API_KEY",
        "VLLM_API_KEY",
        "WAFER_SERVERLESS_API_KEY",
        "WANDB_API_KEY",
        "XAI_API_KEY",
        "UMANS_WEBSEARCH_PROVIDER",
        "XAI_OAUTH_TOKEN",
        "XIAOMI_API_KEY",
        "XIAOMI_TOKEN_PLAN_AMS_API_KEY",
        "XIAOMI_TOKEN_PLAN_CN_API_KEY",
        "XIAOMI_TOKEN_PLAN_SGP_API_KEY",
        "ZAI_API_KEY",
        "ZENMUX_API_KEY",
        "VERTEX_LOCATION",
        "ZHIPU_API_KEY",
    }
)
OMP_AMBIENT_CREDENTIAL_SUFFIXES = (
    "_API_KEY",
    "_ACCESS_TOKEN",
    "_OAUTH_TOKEN",
    "_BEARER_TOKEN",
    "_HUB_TOKEN",
    "_SECRET_ACCESS_KEY",
    "_SESSION_TOKEN",
)


def _is_ambient_credential_name(name: str) -> bool:
    """Return whether an inherited variable can directly carry provider credentials."""

    return name.endswith(OMP_AMBIENT_CREDENTIAL_SUFFIXES)


FORBIDDEN_CLIENT_ARGUMENTS = {
    "codex": frozenset(
        {"-c", "-C", "-p", "--add-dir", "--cd", "--config", "--profile"}
    ),
    "qoder": frozenset(
        {
            "-w",
            "--add-dir",
            "--allowed-mcp-server-names",
            "--append-system-prompt",
            "--config-dir",
            "--mcp-config",
            "--plugin-dir",
            "--settings",
            "--strict-mcp-config",
            "--system-prompt",
            "--cwd",
            "--worktree",
        }
    ),
    "omp": frozenset(
        {
            "--add-dir",
            "-e",
            "--append-system-prompt",
            "--config",
            "--extension",
            "--cwd",
            "--from-claude",
            "--from-codex",
            "--hook",
            "--no-skills",
            "--plugin-dir",
            "--trusted-extension",
            "--profile",
            "--skills",
            "--system-prompt",
        }
    ),
}


class ProfileError(Exception):
    """Report a deterministic validation or launch-preparation failure."""


@dataclass(frozen=True)
class McpDefinition:
    """Hold one validated, client-neutral stdio MCP definition."""

    name: str
    command: str
    args: tuple[str, ...]
    env: Mapping[str, str]
    source: Path


@dataclass(frozen=True)
class Profile:
    """Hold one explicit, flat capability closure."""

    name: str
    source: Path
    prompt: Path
    skills: tuple[str, ...]
    mcps: tuple[str, ...]
    hooks: tuple[str, ...]
    plugins: tuple[str, ...]


@dataclass(frozen=True)
class Project:
    """Hold a fully validated profile project manifest and its closures."""

    root: Path
    manifest: Path
    profiles: Mapping[str, Profile]
    mcps: Mapping[str, McpDefinition]


@dataclass(frozen=True)
class RenderedFile:
    """Hold normalized output bytes and permission bits for one rendered file."""

    content: bytes
    mode: int = 0o644


@dataclass(frozen=True)
class LaunchSpec:
    """Describe a client command and its isolated-root environment override."""

    command: tuple[str, ...]
    environment: Mapping[str, str]


@dataclass(frozen=True)
class AuthBinding:
    """Hold explicit auth environment values and strings that must be redacted."""

    environment: Mapping[str, str]
    private_values: tuple[str, ...]


@dataclass(frozen=True)
class ReceiptReservation:
    """Hold a no-clobber receipt inode and its stable parent directory."""

    path: Path
    parent_descriptor: int
    descriptor: int
    parent_device: int
    parent_inode: int
    device: int
    inode: int


@dataclass(frozen=True)
class StableDirectory:
    """Hold a directory and every no-follow descriptor from the filesystem root to it."""

    path: Path
    parts: tuple[str, ...]
    descriptors: tuple[int, ...]

    @property
    def descriptor(self) -> int:
        """Return the descriptor for the final directory."""

        return self.descriptors[-1]


def load_project(project_root: Path | str) -> Project:
    """Load a project manifest, profiles, and capabilities with strict schemas."""

    root = Path(project_root).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ProfileError(f"project root is not a directory: {root}")
    root_instructions = _resolve_file(root, "AGENTS.md", "root instructions")
    _read_nonempty_text(root_instructions, "root instructions")
    manifest_path = _resolve_file(root, ".cap/manifest.toml", "manifest")
    manifest = _read_toml(manifest_path)
    _expect_keys(manifest, {"version", "profiles"}, "manifest")
    if type(manifest["version"]) is not int or manifest["version"] != MANIFEST_VERSION:
        raise ProfileError(f"manifest.version must be {MANIFEST_VERSION}")
    raw_profiles = manifest["profiles"]
    if not isinstance(raw_profiles, dict) or not raw_profiles:
        raise ProfileError("manifest.profiles must be a non-empty table")

    profiles: dict[str, Profile] = {}
    for name, raw_path in sorted(raw_profiles.items()):
        _validate_identifier(name, "profile name")
        if not isinstance(raw_path, str):
            raise ProfileError(f"manifest.profiles.{name} must be a path string")
        source = _resolve_file(root, raw_path, f"profile {name}")
        _require_under_cap(root, source, f"profile {name}")
        profile_data = _read_toml(source)
        _expect_keys(
            profile_data,
            {"version", "prompt", "skills", "mcps", "hooks", "plugins"},
            f"profile {name}",
        )
        if type(profile_data["version"]) is not int or profile_data["version"] != 1:
            raise ProfileError(f"profile {name}.version must be 1")
        raw_prompt = profile_data["prompt"]
        if not isinstance(raw_prompt, str):
            raise ProfileError(f"profile {name}.prompt must be a path string")
        prompt = _resolve_file(root, raw_prompt, f"profile {name} prompt")
        _require_under_cap(root, prompt, f"profile {name} prompt")
        profiles[name] = Profile(
            name=name,
            source=source,
            prompt=prompt,
            skills=_identifier_list(profile_data["skills"], f"profile {name}.skills"),
            mcps=_identifier_list(profile_data["mcps"], f"profile {name}.mcps"),
            hooks=_identifier_list(profile_data["hooks"], f"profile {name}.hooks"),
            plugins=_identifier_list(
                profile_data["plugins"], f"profile {name}.plugins"
            ),
        )

    expected = {
        "skills": {item for profile in profiles.values() for item in profile.skills},
        "mcp": {item for profile in profiles.values() for item in profile.mcps},
        "hooks": {item for profile in profiles.values() for item in profile.hooks},
        "plugins": {item for profile in profiles.values() for item in profile.plugins},
    }
    mcps = _validate_capability_store(root, expected)
    return Project(root=root, manifest=manifest_path, profiles=profiles, mcps=mcps)


def create_lock(project_root: Path | str) -> dict[str, Any]:
    """Create the deterministic content and renderer lock for every profile/client pair."""

    project = load_project(project_root)
    _check_project_pollution(project.root)
    payload = _desired_lock(project)
    lock_path = project.root / ".cap" / "lock.json"
    if lock_path.is_symlink():
        raise ProfileError("lock file must not be a symlink")
    _atomic_write(lock_path, _canonical_json(payload), mode=0o644)
    return payload


def verify_project(project_root: Path | str) -> dict[str, Any]:
    """Enforce global/project gates and verify the checked-in lock without rendering."""

    project = load_project(project_root)
    _check_global_pollution()
    _check_project_pollution(project.root)
    desired = _desired_lock(project)
    _verify_lock(project, desired)
    return desired


def materialize_profile(
    project_root: Path | str,
    client: str,
    profile_name: str,
    output_root: Path | str,
) -> str:
    """Verify and render one profile into an explicit, existing empty directory."""

    project = load_project(project_root)
    _check_global_pollution()
    _check_project_pollution(project.root)
    desired = _desired_lock(project)
    _verify_lock(project, desired)
    profile = _select_profile(project, profile_name)
    _validate_client(client)
    output = Path(output_root).expanduser().absolute()
    with _stable_directory(output, "render output") as output_directory:
        _require_external_directory(project, output_directory, "render output")
        if os.listdir(output_directory.descriptor):
            raise ProfileError("render output directory must be empty")
        tree = _render_tree(project, client, profile)
        tree_hash = _tree_hash(tree)
        expected_hash = desired["profiles"][profile_name]["clients"][client][
            "tree_hash"
        ]
        if tree_hash != expected_hash:
            raise ProfileError("rendered output drifted after lock verification")
        _materialize_tree(output_directory, tree)
        return tree_hash


def _rendered_text(
    tree: Mapping[str, RenderedFile],
    relative: str,
    context: str,
    *,
    require_nonempty: bool = True,
) -> str:
    """Decode one UTF-8 file directly from the immutable rendered tree."""

    try:
        value = tree[relative].content.decode("utf-8").strip()
    except (KeyError, UnicodeError) as error:
        raise ProfileError(
            f"{context} must be rendered UTF-8 text: {relative}"
        ) from error
    if require_nonempty and not value:
        raise ProfileError(f"{context} must be non-empty")
    return value


def _rendered_skill_names(tree: Mapping[str, RenderedFile]) -> tuple[str, ...]:
    """Return validated top-level skill names directly from the rendered tree."""

    names = {
        parts[1]
        for relative in tree
        if len(parts := PurePosixPath(relative).parts) >= 3 and parts[0] == "skills"
    }
    for name in names:
        _validate_identifier(name, "rendered skill name")
    return tuple(sorted(names))


def _validate_private_directory(directory: StableDirectory, context: str) -> None:
    """Require one held credential directory to be private, writable, and user-owned."""

    info = os.fstat(directory.descriptor)
    if info.st_uid != os.geteuid():
        raise ProfileError(f"{context} must be owned by the current user")
    mode = stat.S_IMODE(info.st_mode)
    if mode & 0o077:
        raise ProfileError(f"{context} must not grant group or other access")
    if mode & 0o700 != 0o700:
        raise ProfileError(f"{context} must grant its owner read, write, and search")


def _read_private_file(
    directory: StableDirectory,
    name: str,
    context: str,
    *,
    max_bytes: int,
    require_owner_write: bool = False,
) -> bytes:
    """Read one bounded private file, retrying concurrent in-place refreshes."""

    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    for attempt in range(3):
        try:
            descriptor = os.open(name, flags, dir_fd=directory.descriptor)
        except OSError as error:
            raise ProfileError(
                f"{context} is not a readable regular file: {error}"
            ) from error
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.geteuid()
                or before.st_nlink != 1
            ):
                raise ProfileError(
                    f"{context} must be a current-user regular file with one hard link"
                )
            mode = stat.S_IMODE(before.st_mode)
            if mode & 0o077:
                raise ProfileError(f"{context} must not grant group or other access")
            if mode & 0o400 != 0o400 or (require_owner_write and mode & 0o200 != 0o200):
                requirement = "read and write" if require_owner_write else "read"
                raise ProfileError(f"{context} must grant its owner {requirement}")
            content = bytearray()
            while len(content) <= max_bytes:
                chunk = os.read(descriptor, min(65536, max_bytes + 1 - len(content)))
                if not chunk:
                    break
                content.extend(chunk)
            if len(content) > max_bytes:
                raise ProfileError(f"{context} exceeds {max_bytes} bytes")
            after = os.fstat(descriptor)
            live = os.stat(name, dir_fd=directory.descriptor, follow_symlinks=False)
            stable_identity = _same_file_identity(
                after, before.st_dev, before.st_ino
            ) and _same_file_identity(live, before.st_dev, before.st_ino)
            stable_generation = (
                after.st_size,
                after.st_mtime_ns,
                after.st_ctime_ns,
            ) == (
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            ) and (
                live.st_size,
                live.st_mtime_ns,
                live.st_ctime_ns,
            ) == (
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            )
            if stable_identity and stable_generation:
                return bytes(content)
        finally:
            os.close(descriptor)
        if attempt == 2:
            break
    raise ProfileError(f"{context} did not remain stable while it was read")


def _read_stable_private_value(
    directory: StableDirectory,
    name: str,
    context: str,
    *,
    max_bytes: int,
    parse: Callable[[bytes], Any],
    require_owner_write: bool = False,
) -> Any:
    """Read and parse one private value, retrying stable-but-incomplete refresh snapshots."""

    last_error: ProfileError | None = None
    for attempt in range(3):
        payload = _read_private_file(
            directory,
            name,
            context,
            max_bytes=max_bytes,
            require_owner_write=require_owner_write,
        )
        try:
            return parse(payload)
        except ProfileError as error:
            last_error = error
            if attempt < 2:
                time.sleep(0.01 * (attempt + 1))
    assert last_error is not None
    raise last_error


def _validate_private_tree(root: Path, context: str) -> None:
    """Reject unsafe, deep, or oversized entries in one mutable auth tree."""

    entry_count = 0
    total_bytes = 0
    pending = [(root, 0)]
    while pending:
        directory, depth = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                entry_count += 1
                if entry_count > 256:
                    raise ProfileError(f"{context} exceeds 256 directory entries")
                info = entry.stat(follow_symlinks=False)
                label = f"{context}/{entry.name}"
                if info.st_uid != os.geteuid():
                    raise ProfileError(f"{label} must be owned by the current user")
                if stat.S_ISDIR(info.st_mode):
                    if stat.S_IMODE(info.st_mode) & 0o077:
                        raise ProfileError(
                            f"{label} must not grant group or other access"
                        )
                    if stat.S_IMODE(info.st_mode) & 0o700 != 0o700:
                        raise ProfileError(
                            f"{label} must grant its owner read, write, and search"
                        )
                    if depth >= 16:
                        raise ProfileError(f"{context} exceeds 16 directory levels")
                    pending.append((Path(entry.path), depth + 1))
                    continue
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ProfileError(
                        f"{label} must be a regular file with one hard link"
                    )
                if stat.S_IMODE(info.st_mode) & 0o022:
                    raise ProfileError(f"{label} must not grant group or other write")
                total_bytes += info.st_size
                if total_bytes > 16 * 1024 * 1024:
                    raise ProfileError(f"{context} exceeds 16 MiB")


def _create_auth_symlink(
    runtime: StableDirectory, name: str, target: Path, context: str
) -> None:
    """Expose one validated persistent credential object inside the temporary root."""

    try:
        os.symlink(str(target), name, dir_fd=runtime.descriptor)
    except OSError as error:
        raise ProfileError(f"could not stage {context}: {error}") from error


def _validate_broker_url(value: Any) -> str:
    """Return one HTTPS or loopback-HTTP auth-broker URL."""

    if not isinstance(value, str) or not value:
        raise ProfileError("OMP auth broker url must be a non-empty string")
    if any(not character.isprintable() or character.isspace() for character in value):
        raise ProfileError(
            "OMP auth broker url must contain only printable non-space characters"
        )
    parsed = urlsplit(value)
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
    ):
        raise ProfileError("OMP auth broker url must contain only scheme and authority")
    loopback = parsed.hostname in {"127.0.0.1", "::1", "localhost"}
    if parsed.scheme != "https" and not (parsed.scheme == "http" and loopback):
        raise ProfileError("OMP auth broker url must use HTTPS or loopback HTTP")
    if parsed.hostname is None:
        raise ProfileError("OMP auth broker url must include a host")
    try:
        parsed.port
    except ValueError as error:
        raise ProfileError("OMP auth broker url has an invalid port") from error
    return value.rstrip("/")


def _parse_codex_auth(payload: bytes) -> dict[str, Any]:
    """Parse one complete Codex auth snapshot."""

    try:
        parsed = _loads_strict_json(
            payload.decode("utf-8"), "<auth-root>/codex/auth.json"
        )
    except UnicodeError as error:
        raise ProfileError("Codex auth.json must be UTF-8 JSON") from error
    if not isinstance(parsed, dict) or not parsed:
        raise ProfileError("Codex auth.json must be a non-empty JSON object")
    return parsed


def _parse_omp_broker_metadata(payload: bytes) -> dict[str, Any]:
    """Parse and validate one complete OMP broker metadata snapshot."""

    try:
        broker = _loads_strict_json(
            payload.decode("utf-8"), "<auth-root>/omp/broker.json"
        )
    except UnicodeError as error:
        raise ProfileError("OMP broker metadata must be UTF-8 JSON") from error
    if not isinstance(broker, dict):
        raise ProfileError("OMP broker metadata must be a JSON object")
    _expect_keys(broker, {"version", "url"}, "OMP broker metadata")
    if type(broker["version"]) is not int or broker["version"] != 1:
        raise ProfileError("OMP broker metadata.version must be 1")
    return {"version": 1, "url": _validate_broker_url(broker["url"])}


def _parse_omp_broker_token(payload: bytes) -> str:
    """Parse one complete OMP broker bearer-token snapshot."""

    try:
        token = payload.decode("ascii")
    except UnicodeError as error:
        raise ProfileError("OMP broker token must be ASCII") from error
    if not token or any(not 0x21 <= ord(character) <= 0x7E for character in token):
        raise ProfileError(
            "OMP broker token must contain only printable non-space ASCII"
        )
    return token


@contextmanager
def _staged_auth(
    project: Project,
    client: str,
    auth_root: Path | str,
    runtime: StableDirectory,
) -> Iterator[AuthBinding]:
    """Stage only the selected client's explicit persistent credential source."""

    root_path = Path(auth_root).expanduser().absolute()
    with _stable_directory(root_path, "auth root") as root:
        _require_external_directory(project, root, "auth root")
        _validate_private_directory(root, "auth root")
        client_path = root.path / client
        with _stable_directory(client_path, f"{client} auth directory") as client_root:
            _validate_private_directory(client_root, f"{client} auth directory")
            if client == "codex":
                _read_stable_private_value(
                    client_root,
                    "auth.json",
                    "Codex auth.json",
                    max_bytes=1024 * 1024,
                    parse=_parse_codex_auth,
                    require_owner_write=True,
                )
                _create_auth_symlink(
                    runtime, "auth.json", client_root.path / "auth.json", "Codex auth"
                )
                yield AuthBinding({}, (str(root.path), str(client_root.path)))
            elif client == "qoder":
                auth_path = client_root.path / ".auth"
                with _stable_directory(auth_path, "Qoder .auth") as qoder_auth:
                    _validate_private_directory(qoder_auth, "Qoder .auth")
                    _validate_private_tree(qoder_auth.path, "Qoder .auth")
                    _create_auth_symlink(
                        runtime, ".auth", qoder_auth.path, "Qoder auth directory"
                    )
                    yield AuthBinding({}, (str(root.path), str(qoder_auth.path)))
                    _validate_stable_directory(qoder_auth)
                    _validate_private_tree(qoder_auth.path, "Qoder .auth")
            else:
                broker = _read_stable_private_value(
                    client_root,
                    "broker.json",
                    "OMP broker metadata",
                    max_bytes=16 * 1024,
                    parse=_parse_omp_broker_metadata,
                )
                token_text = _read_stable_private_value(
                    client_root,
                    "token",
                    "OMP broker token",
                    max_bytes=8192,
                    parse=_parse_omp_broker_token,
                )
                yield AuthBinding(
                    {
                        "OMP_AUTH_BROKER_URL": broker["url"],
                        "OMP_AUTH_BROKER_TOKEN": token_text,
                    },
                    (str(root.path), str(client_root.path), token_text),
                )
            _validate_stable_directory(client_root)
        _validate_stable_directory(root)


def build_launch(
    client: str,
    runtime_root: Path | str,
    rendered_tree: Mapping[str, RenderedFile],
    forwarded_args: Sequence[str] = (),
) -> LaunchSpec:
    """Build one fixed launch from a stable root name and its immutable rendered tree."""

    _validate_client(client)
    root = Path(runtime_root).absolute()
    args = tuple(forwarded_args)
    _validate_forwarded_args(client, args)
    executable = CLIENT_EXECUTABLES[client]
    if client == "codex":
        return LaunchSpec((executable, *args), {"CODEX_HOME": str(root)})
    prompt = _rendered_text(
        rendered_tree, "system-prompt.md", "rendered profile prompt"
    )
    if client == "qoder":
        command = (
            executable,
            "--config-dir",
            str(root),
            "--strict-mcp-config",
            "--mcp-config",
            str(root / "mcp.json"),
            "--append-system-prompt",
            prompt,
            *args,
        )
        return LaunchSpec(command, {"QODER_CONFIG_DIR": str(root)})
    skill_names = _rendered_skill_names(rendered_tree)
    skill_arguments = (
        ("--skills", ",".join(skill_names)) if skill_names else ("--no-skills",)
    )
    command = (
        executable,
        "--config",
        str(root / "config.yml"),
        "--append-system-prompt",
        prompt + "\n",
        *skill_arguments,
        "--no-extensions",
        "--no-rules",
        *args,
    )
    return LaunchSpec(
        command,
        {
            "OMP_PROFILE": "default",
            "PI_CODING_AGENT_DIR": str(root),
            "PI_CONFIG_DIR": str(root),
            "PI_CONFIG_FILES": str(root / "config.yml"),
            "PI_PROFILE": "default",
        },
    )


def _prepare_execution(
    project_root: Path | str,
    client: str,
    profile_name: str,
    forwarded_args: Sequence[str],
) -> tuple[Project, Profile, dict[str, Any], tuple[str, ...]]:
    """Validate every launch precondition before a client process can be created."""

    project = load_project(project_root)
    _require_git_root(project.root)
    _check_global_pollution()
    _check_project_pollution(project.root)
    desired = _desired_lock(project)
    _verify_lock(project, desired)
    profile = _select_profile(project, profile_name)
    _validate_client(client)
    args = tuple(forwarded_args)
    _validate_forwarded_args(client, args)
    return project, profile, desired, args

def _prepare_workdir(value: Path | str | None, default: Path) -> Path:
    """Resolve the client working directory without using mutable profile state."""

    if value is None:
        return default
    path = Path(value).expanduser().resolve(strict=True)
    if path.is_symlink() or not path.is_dir():
        raise ProfileError(f"workdir must be a non-symlink directory: {path}")
    return path


def _execute_runtime(
    project: Project,
    client: str,
    profile: Profile,
    desired: Mapping[str, Any],
    forwarded_args: Sequence[str],
    *,
    auth_root: Path | str,
    runner: Callable[..., Any],
    capture_output: bool,
    workdir: Path | str | None = None,
) -> tuple[int, str, str]:
    """Render, bind explicit auth, and invoke one client through the strict path."""

    output_hash = desired["profiles"][profile.name]["clients"][client]["tree_hash"]
    with tempfile.TemporaryDirectory(
        prefix=f"profile-{client}-{profile.name}-"
    ) as temporary:
        runtime_root = Path(temporary)
        tree = _render_tree(project, client, profile)
        if _tree_hash(tree) != output_hash:
            raise ProfileError("rendered output drifted after lock verification")
        with _stable_directory(runtime_root, "runtime root") as runtime_directory:
            _materialize_tree(runtime_directory, tree)
            with _staged_auth(
                project, client, auth_root, runtime_directory
            ) as auth_binding:
                spec = build_launch(
                    client, runtime_directory.path, tree, forwarded_args
                )
                target_workdir = _prepare_workdir(workdir, project.root)
                if client == "omp":
                    spec = LaunchSpec(
                        (
                            spec.command[0],
                            "--cwd",
                            str(target_workdir),
                            *spec.command[1:],
                        ),
                        spec.environment,
                    )
                environment = os.environ.copy()
                for name in AMBIENT_CONFIG_ENV:
                    environment.pop(name, None)
                if client == "omp":
                    for name in set(OMP_AMBIENT_AUTH_ENV) | {
                        candidate
                        for candidate in environment
                        if _is_ambient_credential_name(candidate)
                    }:
                        environment[name] = ""
                    environment["AWS_EC2_METADATA_DISABLED"] = "true"
                    environment["HOME"] = str(runtime_directory.path)
                    environment["PI_AUTH_NO_BORROW"] = "1"
                environment.update(spec.environment)
                environment.update(auth_binding.environment)
                run_options: dict[str, Any] = {
                    "cwd": str(
                        runtime_directory.path if client == "omp" else target_workdir
                    ),
                    "env": environment,
                    "check": False,
                }
                if capture_output:
                    run_options.update(
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                    )
                _check_project_pollution(project.root)
                _check_global_pollution()
                if _input_records(project) != desired["inputs"]:
                    raise ProfileError("locked inputs drifted after lock verification")
                _validate_stable_directory(runtime_directory)
                completed = runner(list(spec.command), **run_options)
                _check_global_pollution()
                return_code = getattr(completed, "returncode", None)
                if type(return_code) is not int:
                    raise ProfileError(
                        "client runner did not return an integer return code"
                    )
                stdout = getattr(completed, "stdout", "") or ""
                stderr = getattr(completed, "stderr", "") or ""
                private_spellings = {
                    str(runtime_root),
                    runtime_root.as_posix(),
                    str(runtime_directory.path),
                    runtime_directory.path.as_posix(),
                    str(Path(auth_root).expanduser().absolute()),
                    Path(auth_root).expanduser().absolute().as_posix(),
                    *auth_binding.private_values,
                }
                for spelling in sorted(
                    (value for value in private_spellings if value),
                    key=len,
                    reverse=True,
                ):
                    stdout = stdout.replace(spelling, "<private>")
                    stderr = stderr.replace(spelling, "<private>")
    return return_code, stdout, stderr


def _receipt_payload(
    client: str,
    profile: Profile,
    desired: Mapping[str, Any],
    forwarded_args: Sequence[str],
    return_code: int,
) -> dict[str, Any]:
    """Build a receipt that records identity and hashes without arguments or secrets."""

    return {
        "version": 1,
        "client": client,
        "profile": profile.name,
        "executable": CLIENT_EXECUTABLES[client],
        "exit_code": return_code,
        "forwarded_argument_count": len(forwarded_args),
        "inventory": _profile_inventory(profile),
        "lock_hash": f"sha256:{_sha256(_canonical_json(desired))}",
        "output_tree_hash": desired["profiles"][profile.name]["clients"][client][
            "tree_hash"
        ],
        "adapter_version": CLIENT_ADAPTER_VERSION,
        "temporary_root_removed": True,
    }


def run_client(
    project_root: Path | str,
    client: str,
    profile_name: str,
    forwarded_args: Sequence[str] = (),
    *,
    auth_root: Path | str,
    receipt_path: Path | str | None = None,
    workdir: Path | str | None = None,
    runner: Callable[..., Any] | None = None,
) -> int:
    """Launch one authenticated client in a verified temporary root and clean it up."""

    project, profile, desired, args = _prepare_execution(
        project_root, client, profile_name, forwarded_args
    )
    receipt_target = (
        _prepare_receipt_path(receipt_path) if receipt_path is not None else None
    )
    reservation: ReceiptReservation | None = None
    if receipt_target is not None:
        reservation = _reserve_receipt(project, receipt_target)
    committed = False
    try:
        return_code, _, _ = _execute_runtime(
            project,
            client,
            profile,
            desired,
            args,
            auth_root=auth_root,
            runner=runner or subprocess.run,
            capture_output=False,
            workdir=workdir,
        )
        receipt_bytes = _canonical_json(
            _receipt_payload(client, profile, desired, args, return_code)
        )
        if reservation is None:
            sys.stdout.buffer.write(receipt_bytes)
        else:
            _commit_receipt(reservation, receipt_bytes)
            committed = True
        return return_code if return_code >= 0 else 128 + abs(return_code)
    finally:
        if reservation is not None:
            _release_receipt(reservation, remove=not committed)


def list_profiles(project_root: Path | str) -> tuple[str, ...]:
    """Return locked explicit profile names in deterministic order without choosing a default."""

    project = load_project(project_root)
    _check_global_pollution()
    _check_project_pollution(project.root)
    _verify_lock(project, _desired_lock(project))
    return tuple(sorted(project.profiles))


def explain_profile(project_root: Path | str, profile_name: str) -> dict[str, Any]:
    """Return one locked profile's flat closure and normalized output hashes for all clients."""

    project = load_project(project_root)
    _check_global_pollution()
    _check_project_pollution(project.root)
    desired = _desired_lock(project)
    _verify_lock(project, desired)
    profile = _select_profile(project, profile_name)
    return {
        "profile": profile.name,
        "prompt": profile.prompt.relative_to(project.root).as_posix(),
        "inventory": _profile_inventory(profile),
        "clients": desired["profiles"][profile.name]["clients"],
    }


OBSERVATION_DIMENSIONS = ("skills", "mcps", "context", "hooks", "plugins")
REPORT_MARKERS = {
    "skills": "SKILLS-AVAILABLE",
    "mcps": "MCP-AVAILABLE",
    "context": "CONTEXT-FILES",
    "hooks": "HOOKS-AVAILABLE",
    "plugins": "PLUGINS-AVAILABLE",
}


def parse_reported(text: str, marker: str) -> list[str] | None:
    """Parse one self-report marker, preserving unknown separately from observed none."""

    for line in reversed(text.splitlines()):
        candidate = line.strip().lstrip("+-").strip().strip("`").strip()
        if not candidate.upper().startswith(marker + ":"):
            continue
        body = candidate.split(":", 1)[1].strip().strip("`").strip()
        if body.lower() in {"unknown", "未知"}:
            return None
        if body.lower() in {"none", "无", ""}:
            return []
        return [item.strip().strip("`") for item in body.split(",") if item.strip()]
    return None


def _directory_open_flags() -> int:
    """Return fail-closed flags for opening one directory component."""

    flags = os.O_RDONLY
    for name in ("O_CLOEXEC", "O_DIRECTORY", "O_NOFOLLOW"):
        flags |= getattr(os, name, 0)
    return flags


def _same_file_identity(info: os.stat_result, device: int, inode: int) -> bool:
    """Return whether one stat result names the expected filesystem object."""

    return info.st_dev == device and info.st_ino == inode


def _validate_stable_directory(directory: StableDirectory) -> None:
    """Verify that every held directory still occupies its original parent entry."""

    try:
        root_info = os.fstat(directory.descriptors[0])
        if not stat.S_ISDIR(root_info.st_mode):
            raise ProfileError("stable directory filesystem root is not a directory")
        for index, name in enumerate(directory.parts):
            parent_descriptor = directory.descriptors[index]
            descriptor = directory.descriptors[index + 1]
            live = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
            held = os.fstat(descriptor)
            if (
                not stat.S_ISDIR(live.st_mode)
                or not stat.S_ISDIR(held.st_mode)
                or not _same_file_identity(live, held.st_dev, held.st_ino)
            ):
                raise ProfileError(f"stable directory changed: {directory.path}")
    except (OSError, NotImplementedError) as error:
        raise ProfileError(
            f"stable directory is no longer accessible: {error}"
        ) from error


def _normalize_root_alias(path: Path, context: str) -> Path:
    """Normalize only a root-owned first-component symlink such as macOS /var."""

    absolute = path.expanduser().absolute()
    if absolute.anchor != os.sep:
        raise ProfileError(f"{context} requires POSIX component-safe directory handles")
    if len(absolute.parts) < 2:
        return absolute
    first = Path(os.sep) / absolute.parts[1]
    try:
        info = os.lstat(first)
        if not stat.S_ISLNK(info.st_mode):
            return absolute
        if getattr(info, "st_uid", -1) != 0:
            raise ProfileError(f"{context} contains a non-root-owned symlink ancestor")
        target = first.resolve(strict=True)
    except ProfileError:
        raise
    except OSError as error:
        raise ProfileError(f"{context} root alias is not stable: {error}") from error
    return target.joinpath(*absolute.parts[2:])


def _open_stable_directory(path: Path, context: str) -> StableDirectory:
    """Open a lexical path one no-follow component at a time."""

    absolute = _normalize_root_alias(path, context)
    descriptors: list[int] = []
    parts = tuple(absolute.parts[1:])
    try:
        descriptors.append(os.open(os.sep, _directory_open_flags()))
        for part in parts:
            descriptors.append(
                os.open(part, _directory_open_flags(), dir_fd=descriptors[-1])
            )
        directory = StableDirectory(absolute, parts, tuple(descriptors))
        _validate_stable_directory(directory)
        return directory
    except (OSError, NotImplementedError) as error:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise ProfileError(
            f"{context} must be an existing non-symlink directory: {error}"
        ) from error
    except BaseException:
        for descriptor in reversed(descriptors):
            os.close(descriptor)
        raise


def _close_stable_directory(directory: StableDirectory) -> None:
    """Close every descriptor held for one stable directory chain."""

    for descriptor in reversed(directory.descriptors):
        try:
            os.close(descriptor)
        except OSError:
            pass


@contextmanager
def _stable_directory(path: Path, context: str) -> Iterator[StableDirectory]:
    """Yield one component-safe directory handle and verify its path before closing."""

    directory = _open_stable_directory(path, context)
    try:
        yield directory
    except BaseException:
        raise
    else:
        _validate_stable_directory(directory)
    finally:
        _close_stable_directory(directory)


def _stable_directory_is_within(directory: StableDirectory, root: Path) -> bool:
    """Return whether a held directory is the same as or below one physical root."""

    root_directory = _open_stable_directory(root, "restricted root")
    try:
        root_info = os.fstat(root_directory.descriptor)
        return any(
            _same_file_identity(
                os.fstat(descriptor), root_info.st_dev, root_info.st_ino
            )
            for descriptor in directory.descriptors
        )
    finally:
        _close_stable_directory(root_directory)


def _stable_directory_is_same(directory: StableDirectory, other: Path) -> bool:
    """Return whether a held directory is the same physical directory as one path."""

    other_directory = _open_stable_directory(other, "restricted root")
    try:
        other_info = os.fstat(other_directory.descriptor)
        current_info = os.fstat(directory.descriptor)
        return _same_file_identity(current_info, other_info.st_dev, other_info.st_ino)
    finally:
        _close_stable_directory(other_directory)


def _require_external_directory(
    project: Project, directory: StableDirectory, context: str
) -> None:
    """Reject a held output directory inside the project or native capability roots."""

    if _stable_directory_is_within(directory, project.root):
        raise ProfileError(f"{context} must be outside the project root")
    home = Path.home().absolute()
    if _stable_directory_is_same(directory, home):
        raise ProfileError(f"{context} must be outside global capability roots")
    for relative in GLOBAL_NATIVE_ROOTS:
        native_root = home / relative
        if native_root.exists() and _stable_directory_is_within(directory, native_root):
            raise ProfileError(f"{context} must be outside global capability roots")


def _state_root(
    project: Project, value: Path | str, *, require_empty: bool
) -> StableDirectory:
    """Open an explicit observation directory without remembering a prior selection."""

    candidate = Path(value).expanduser().absolute()
    directory = _open_stable_directory(candidate, "state directory")
    try:
        _require_external_directory(project, directory, "state directory")
        if require_empty and os.listdir(directory.descriptor):
            raise ProfileError("state directory must be empty")
        _validate_stable_directory(directory)
        return directory
    except BaseException:
        _close_stable_directory(directory)
        raise


def _declared_snapshot(
    project: Project,
    client: str,
    profile: Profile,
    desired: Mapping[str, Any],
) -> dict[str, Any]:
    """Describe the selected declaration and its normalized client render."""

    context = [str(project.root / "AGENTS.md")]
    if client == "codex":
        context.append("<runtime>/AGENTS.md")
    return {
        "version": 1,
        "client": client,
        "profile": profile.name,
        "renderer_version": RENDERER_VERSION,
        "adapter_version": CLIENT_ADAPTER_VERSION,
        "lock_hash": f"sha256:{_sha256(_canonical_json(desired))}",
        "output_tree_hash": desired["profiles"][profile.name]["clients"][client][
            "tree_hash"
        ],
        "inventory": _profile_inventory(profile),
        "context": context,
        "capability_semantics": desired["capability_semantics"],
    }


def _configured_mcp_names(tree: Mapping[str, RenderedFile], client: str) -> list[str]:
    """Read native MCP server names directly from the immutable rendered tree."""

    if client == "codex":
        try:
            data = tomllib.loads(
                _rendered_text(
                    tree,
                    "config.toml",
                    "rendered Codex configuration",
                    require_nonempty=False,
                )
            )
        except tomllib.TOMLDecodeError as error:
            raise ProfileError(
                f"rendered Codex configuration is invalid: {error}"
            ) from error
        servers = data.get("mcp_servers", {})
    else:
        relative = "mcp.json"
        data = _loads_strict_json(
            _rendered_text(tree, relative, "rendered MCP configuration"),
            f"<rendered-tree>/{relative}",
        )
        servers = data.get("mcpServers", {}) if isinstance(data, dict) else None
    if not isinstance(servers, dict):
        raise ProfileError("rendered MCP configuration has an invalid server table")
    return sorted(servers)


def probe_profile(
    project_root: Path | str,
    client: str,
    profile_name: str,
    state_root: Path | str,
) -> dict[str, Any]:
    """Observe the rendered configuration plane without invoking an agent or model."""

    project = load_project(project_root)
    _check_global_pollution()
    _check_project_pollution(project.root)
    desired = _desired_lock(project)
    _verify_lock(project, desired)
    profile = _select_profile(project, profile_name)
    _validate_client(client)
    state = _state_root(project, state_root, require_empty=True)
    try:
        expected_hash = desired["profiles"][profile.name]["clients"][client][
            "tree_hash"
        ]
        with tempfile.TemporaryDirectory(
            prefix=f"profile-probe-{client}-{profile.name}-"
        ) as temporary:
            runtime_root = Path(temporary)
            tree = _render_tree(project, client, profile)
            if _tree_hash(tree) != expected_hash:
                raise ProfileError("rendered output drifted after lock verification")
            with _stable_directory(
                runtime_root, "probe runtime root"
            ) as runtime_directory:
                _materialize_tree(runtime_directory, tree)
                skills = list(_rendered_skill_names(tree))
                mcps = _configured_mcp_names(tree, client)
        declared = _declared_snapshot(project, client, profile, desired)
        probed = {
            "version": 1,
            "client": client,
            "profile": profile.name,
            "plane": "configured",
            "probed_at": datetime.now(timezone.utc).isoformat(),
            "observed": {
                "skills": skills,
                "mcps": mcps,
                "context": None,
                "hooks": None,
                "plugins": None,
            },
            "candidates": {"context": declared["context"]},
            "staged": {
                "hooks": list(profile.hooks),
                "plugins": list(profile.plugins),
            },
            "caveats": [
                "context candidates are not proof that the client loaded them",
                "hooks and plugins are opaque-staging until native loading is verified",
                "configured state is not effective runtime state",
            ],
        }
        _materialize_tree(
            state,
            {
                "declared.json": RenderedFile(_canonical_json(declared)),
                "probed.json": RenderedFile(_canonical_json(probed)),
            },
        )
        return probed
    finally:
        _close_stable_directory(state)


def run_observed(
    project_root: Path | str,
    client: str,
    profile_name: str,
    state_root: Path | str,
    forwarded_args: Sequence[str] = (),
    *,
    auth_root: Path | str,
    receipt_path: Path | str | None = None,
    workdir: Path | str | None = None,
    runner: Callable[..., Any] | None = None,
) -> int:
    """Run one batch client, capture self-reported effective state, and clean its root."""

    project, profile, desired, args = _prepare_execution(
        project_root, client, profile_name, forwarded_args
    )
    state = _state_root(project, state_root, require_empty=True)
    reservation: ReceiptReservation | None = None
    committed = False
    try:
        receipt_target = _prepare_receipt_path(
            receipt_path or state.path / "receipt.json"
        )
        reservation = _reserve_receipt(
            project,
            receipt_target,
            parent_directory=state if receipt_target.parent == state.path else None,
        )
        declared = _declared_snapshot(project, client, profile, desired)
        _materialize_tree(
            state,
            {"declared.json": RenderedFile(_canonical_json(declared))},
        )
        started = datetime.now(timezone.utc)
        return_code, stdout, stderr = _execute_runtime(
            project,
            client,
            profile,
            desired,
            args,
            auth_root=auth_root,
            runner=runner or subprocess.run,
            capture_output=True,
            workdir=workdir,
        )
        ended = datetime.now(timezone.utc)
        text = stdout + "\n" + stderr
        reported = {
            dimension: parse_reported(text, REPORT_MARKERS[dimension])
            for dimension in OBSERVATION_DIMENSIONS
        }
        client_limited = {
            "codex": {"mcps", "context"},
            "qoder": set(),
            "omp": {"mcps"},
        }[client]
        forced_unknown = {"hooks", "plugins"} | client_limited
        effective = {
            "version": 1,
            "client": client,
            "profile": profile.name,
            "plane": "effective",
            "started_at": started.isoformat(),
            "ended_at": ended.isoformat(),
            "duration_s": round((ended - started).total_seconds()),
            "exit_code": return_code,
            "forwarded_argument_count": len(args),
            "observed": {
                dimension: None if dimension in forced_unknown else reported[dimension]
                for dimension in OBSERVATION_DIMENSIONS
            },
            "reported_opaque_staging": {
                dimension: reported[dimension] for dimension in ("hooks", "plugins")
            },
            "reported_client_limited": {
                dimension: reported[dimension] for dimension in sorted(client_limited)
            },
            "evidence": (
                "client output self-report; missing or explicit unknown markers remain unknown; "
                "hook/plugin reports remain opaque-staging; client-limited dimensions are retained "
                "only as unreliable reports rather than effective observations"
            ),
        }
        _materialize_tree(
            state,
            {"effective.json": RenderedFile(_canonical_json(effective))},
        )
        _commit_receipt(
            reservation,
            _canonical_json(
                _receipt_payload(client, profile, desired, args, return_code)
            ),
        )
        committed = True
        if stdout:
            print(stdout, end="" if stdout.endswith("\n") else "\n")
        if stderr:
            print(stderr, end="" if stderr.endswith("\n") else "\n", file=sys.stderr)
        return return_code if return_code >= 0 else 128 + abs(return_code)
    finally:
        if reservation is not None:
            _release_receipt(reservation, remove=not committed)
        _close_stable_directory(state)


def _observation_key(dimension: str, value: str) -> str:
    if dimension != "context":
        return value.strip()
    normalized = value.strip().strip("`").replace("\\", "/").rstrip("/")
    return os.path.normcase(normalized)


def diff_profile(
    project_root: Path | str,
    client: str,
    profile_name: str,
    state_root: Path | str,
) -> int:
    """Compare one immutable declaration with the separately captured effective state."""

    project = load_project(project_root)
    _check_global_pollution()
    _check_project_pollution(project.root)
    desired = _desired_lock(project)
    _verify_lock(project, desired)
    profile = _select_profile(project, profile_name)
    _validate_client(client)
    state = _state_root(project, state_root, require_empty=False)
    try:
        try:
            declared = _strict_json_from_directory(state, "declared.json")
            effective = _strict_json_from_directory(state, "effective.json")
        except ProfileError as error:
            if "state file missing:" in str(error):
                raise ProfileError(
                    "diff requires declared.json and effective.json from one observed run"
                ) from error
            raise
        current = _declared_snapshot(project, client, profile, desired)
        if declared != current:
            raise ProfileError(
                "declared observation no longer matches the selected locked profile"
            )
        if (
            not isinstance(effective, dict)
            or effective.get("client") != client
            or effective.get("profile") != profile.name
        ):
            raise ProfileError(
                "effective observation belongs to a different client or profile"
            )
        observed_by_dimension = effective.get("observed")
        if not isinstance(observed_by_dimension, dict):
            raise ProfileError("effective observation has no observed dimension table")
        expected = {
            "skills": list(profile.skills),
            "mcps": list(profile.mcps),
            "context": list(current["context"]),
            "hooks": list(profile.hooks),
            "plugins": list(profile.plugins),
        }
        problems: list[str] = []
        unknowns: list[str] = []
        print(f"profile: {profile.name}  client: {client}")
        for dimension in OBSERVATION_DIMENSIONS:
            observed = observed_by_dimension.get(dimension)
            effective_text = observed if observed is not None else "unknown"
            print(
                f"[{dimension}] declared={expected[dimension] or '(none)'} "
                f"effective={effective_text}"
            )
            if observed is None:
                unknowns.append(
                    f"{dimension}: unknown; absence of evidence is not observed none"
                )
                continue
            if not isinstance(observed, list) or any(
                not isinstance(item, str) for item in observed
            ):
                raise ProfileError(
                    f"effective observation {dimension} must be an array or null"
                )
            expected_keys = {
                _observation_key(dimension, item): item for item in expected[dimension]
            }
            observed_keys = {
                _observation_key(dimension, item): item for item in observed
            }
            missing = sorted(
                expected_keys[key]
                for key in expected_keys.keys() - observed_keys.keys()
            )
            extra = sorted(
                observed_keys[key]
                for key in observed_keys.keys() - expected_keys.keys()
            )
            if missing:
                problems.append(f"{dimension} missing: {missing}")
            if extra:
                problems.append(f"{dimension} outside declaration: {extra}")
        if effective.get("exit_code") != 0:
            problems.append(f"client exit code was {effective.get('exit_code')}")
        if unknowns:
            print("unknown:")
            for item in unknowns:
                print(f"  ? {item}")
        if problems:
            print("drift:")
            for item in problems:
                print(f"  - {item}")
            return 1
        if unknowns:
            print("result: unknown; one or more effective dimensions were not observed")
            return 2
        print("result: no observed drift")
        return 0
    finally:
        _close_stable_directory(state)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the sole profile command-line interface and return its process exit code."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        project = Path(args.project)
        if args.command == "lock":
            payload = create_lock(project)
            _print_json(
                {
                    "status": "locked",
                    "lock_hash": f"sha256:{_sha256(_canonical_json(payload))}",
                }
            )
            return 0
        if args.command == "verify":
            payload = verify_project(project)
            _print_json(
                {
                    "status": "ok",
                    "lock_hash": f"sha256:{_sha256(_canonical_json(payload))}",
                }
            )
            return 0
        if args.command == "list":
            _print_json({"profiles": list(list_profiles(project))})
            return 0
        if args.command == "explain":
            _print_json(explain_profile(project, args.profile))
            return 0
        if args.command == "materialize":
            tree_hash = materialize_profile(
                project, args.client, args.profile, args.output
            )
            _print_json(
                {
                    "status": "materialized",
                    "client": args.client,
                    "profile": args.profile,
                    "tree_hash": tree_hash,
                }
            )
            return 0
        if args.command == "probe":
            _print_json(probe_profile(project, args.client, args.profile, args.state))
            return 0
        if args.command == "diff":
            return diff_profile(project, args.client, args.profile, args.state)
        forwarded = list(args.client_args)
        if forwarded and forwarded[0] == "--":
            forwarded.pop(0)
        if args.command == "launch":
            return run_client(
                project,
                args.client,
                args.profile,
                forwarded,
                auth_root=args.auth_root,
                receipt_path=args.receipt,
                workdir=args.workdir,
            )
        return run_observed(
            project,
            args.client,
            args.profile,
            args.state,
            forwarded,
            auth_root=args.auth_root,
            receipt_path=args.receipt,
            workdir=args.workdir,
        )
    except (ProfileError, OSError) as error:
        print(f"profile: error: {error}", file=sys.stderr)
        return 2


def _add_selection(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--client", required=True, choices=CLIENTS)
    parser.add_argument("--profile", required=True)


def _add_auth(parser: argparse.ArgumentParser) -> None:
    """Require one explicit persistent auth vault for runtime commands."""

    parser.add_argument(
        "--auth-root",
        required=True,
        help="private directory containing codex/, qoder/, and omp/ credentials",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="profile")
    parser.add_argument(
        "--project", default=".", help="project root containing .cap/manifest.toml"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("lock", "verify", "list"):
        subparsers.add_parser(name)
    explain = subparsers.add_parser("explain")
    explain.add_argument("--profile", required=True)
    materialize = subparsers.add_parser("materialize")
    _add_selection(materialize)
    materialize.add_argument("--output", required=True)
    probe = subparsers.add_parser("probe")
    _add_selection(probe)
    probe.add_argument("--state", required=True)
    diff = subparsers.add_parser("diff")
    _add_selection(diff)
    diff.add_argument("--state", required=True)
    launch = subparsers.add_parser("launch")
    _add_selection(launch)
    _add_auth(launch)
    launch.add_argument("--receipt")
    launch.add_argument("--workdir")
    launch.add_argument("client_args", nargs=argparse.REMAINDER)
    run = subparsers.add_parser("run")
    _add_selection(run)
    _add_auth(run)
    run.add_argument("--state", required=True)
    run.add_argument("--receipt")
    run.add_argument("--workdir")
    run.add_argument("client_args", nargs=argparse.REMAINDER)
    return parser


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as error:
        raise ProfileError(f"invalid TOML {path}: {error}") from error
    if not isinstance(data, dict):
        raise ProfileError(f"TOML root must be a table: {path}")
    return data


def _loads_strict_json(text: str, context: str) -> Any:
    """Parse strict JSON text with duplicate-key and non-finite-number rejection."""

    def pairs_hook(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ProfileError(f"duplicate JSON key {key!r} in {context}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise ProfileError(f"non-finite JSON number {value!r} in {context}")

    try:
        return json.loads(
            text,
            object_pairs_hook=pairs_hook,
            parse_constant=reject_constant,
        )
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ProfileError(f"invalid JSON {context}: {error}") from error


def _strict_json(path: Path) -> Any:
    """Read and parse one strict JSON file by path."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ProfileError(f"invalid JSON {path}: {error}") from error
    return _loads_strict_json(text, str(path))


def _strict_json_from_directory(directory: StableDirectory, name: str) -> Any:
    """Read one strict JSON file relative to a held directory without following links."""

    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0)
    for flag_name in ("O_CLOEXEC", "O_NOFOLLOW"):
        flags |= getattr(os, flag_name, 0)
    try:
        _validate_stable_directory(directory)
        try:
            descriptor = os.open(name, flags, dir_fd=directory.descriptor)
        except FileNotFoundError as error:
            raise ProfileError(f"state file missing: {name}") from error
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise ProfileError(f"state file must be a private regular file: {name}")
            with os.fdopen(descriptor, "r", encoding="utf-8") as stream:
                descriptor = -1
                text = stream.read()
        finally:
            if descriptor >= 0:
                os.close(descriptor)
        live = os.stat(name, dir_fd=directory.descriptor, follow_symlinks=False)
        if (
            not stat.S_ISREG(live.st_mode)
            or live.st_nlink != 1
            or not _same_file_identity(live, info.st_dev, info.st_ino)
        ):
            raise ProfileError(f"state file changed while reading: {name}")
        _validate_stable_directory(directory)
    except ProfileError:
        raise
    except (OSError, NotImplementedError, UnicodeError) as error:
        raise ProfileError(f"invalid JSON {directory.path / name}: {error}") from error
    return _loads_strict_json(text, str(directory.path / name))


def _expect_keys(data: Mapping[str, Any], expected: set[str], context: str) -> None:
    actual = set(data)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise ProfileError(f"{context} keys mismatch: missing={missing}, extra={extra}")


def _validate_identifier(value: Any, context: str) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ProfileError(f"{context} must match {IDENTIFIER.pattern}: {value!r}")
    return value


def _identifier_list(value: Any, context: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ProfileError(f"{context} must be an array")
    result = tuple(_validate_identifier(item, context) for item in value)
    if len(result) != len(set(result)):
        raise ProfileError(f"{context} contains duplicates")
    return result


def _safe_relative(value: str, context: str) -> PurePosixPath:
    if not value or "\\" in value:
        raise ProfileError(
            f"{context} must be a normalized POSIX relative path: {value!r}"
        )
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ProfileError(
            f"{context} must be a normalized POSIX relative path: {value!r}"
        )
    return path


def _resolve_file(root: Path, value: str, context: str) -> Path:
    relative = _safe_relative(value, context)
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ProfileError(f"{context} must not traverse a symlink: {value}")
    try:
        resolved = current.resolve(strict=True)
    except OSError as error:
        raise ProfileError(f"{context} does not exist: {value}") from error
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise ProfileError(f"{context} must resolve to a regular project file: {value}")
    return resolved


def _require_under_cap(root: Path, path: Path, context: str) -> None:
    cap_root = root / ".cap"
    if not path.is_relative_to(cap_root):
        raise ProfileError(f"{context} must be stored under .cap")


def _validate_capability_store(
    root: Path, expected: Mapping[str, set[str]]
) -> dict[str, McpDefinition]:
    base = root / ".cap" / "capabilities"
    _require_directory(base, "capability store")
    children = {item.name for item in base.iterdir()}
    if children != set(CAPABILITY_KINDS):
        raise ProfileError(
            f"capability store kinds mismatch: missing={sorted(set(CAPABILITY_KINDS) - children)}, "
            f"extra={sorted(children - set(CAPABILITY_KINDS))}"
        )
    mcps: dict[str, McpDefinition] = {}
    for kind in CAPABILITY_KINDS:
        kind_root = base / kind
        _require_directory(kind_root, f"capability kind {kind}")
        if kind == "mcp":
            actual = set()
            for item in sorted(kind_root.iterdir(), key=lambda path: path.name):
                if item.is_symlink() or not item.is_file() or item.suffix != ".json":
                    raise ProfileError(
                        f"mcp store contains invalid entry: {item.relative_to(root)}"
                    )
                name = item.stem
                _validate_identifier(name, "mcp capability name")
                actual.add(name)
                mcps[name] = _load_mcp(item, name)
        else:
            actual = set()
            for item in sorted(kind_root.iterdir(), key=lambda path: path.name):
                if item.is_symlink() or not item.is_dir():
                    raise ProfileError(
                        f"{kind} store contains invalid entry: {item.relative_to(root)}"
                    )
                _validate_identifier(item.name, f"{kind} capability name")
                actual.add(item.name)
                _validate_capability_tree(root, kind, item)
        if actual != expected[kind]:
            raise ProfileError(
                f"{kind} inventory mismatch: missing={sorted(expected[kind] - actual)}, "
                f"unreferenced={sorted(actual - expected[kind])}"
            )
    return mcps


def _require_directory(path: Path, context: str) -> None:
    if path.is_symlink() or not path.exists() or not path.is_dir():
        raise ProfileError(f"{context} must be a non-symlink directory: {path}")


def _validate_capability_tree(root: Path, kind: str, capability: Path) -> None:
    entries = sorted(
        capability.rglob("*"), key=lambda path: path.relative_to(root).as_posix()
    )
    for item in entries:
        if item.is_symlink() or not (item.is_file() or item.is_dir()):
            raise ProfileError(
                f"capability tree contains unsupported entry: {item.relative_to(root)}"
            )
    if kind == "skills":
        if not (capability / "SKILL.md").is_file():
            raise ProfileError(
                f"skill capability lacks SKILL.md: {capability.relative_to(root)}"
            )
        if not any(item.is_file() for item in entries):
            raise ProfileError(
                f"skill capability is empty: {capability.relative_to(root)}"
            )
        return
    direct = {item.name for item in capability.iterdir()}
    if direct != {"targets"}:
        raise ProfileError(
            f"{kind} capability must contain only targets/: {capability.relative_to(root)}"
        )
    targets = capability / "targets"
    _require_directory(targets, f"{kind} targets")
    target_names = {item.name for item in targets.iterdir()}
    if not target_names or not target_names.issubset(set(CLIENTS)):
        raise ProfileError(
            f"{kind} targets must be a non-empty subset of {list(CLIENTS)}"
        )
    for target in targets.iterdir():
        _require_directory(target, f"{kind} target {target.name}")
        direct = {item.name for item in target.iterdir()}
        if direct != {kind}:
            raise ProfileError(
                f"{kind} target {target.name} must contain only {kind}/: "
                f"{target.relative_to(root)}"
            )
        namespace = target / kind
        _require_directory(namespace, f"{kind} target {target.name} namespace")
        if not any(item.is_file() for item in namespace.rglob("*")):
            raise ProfileError(f"{kind} target is empty: {target.relative_to(root)}")


def _load_mcp(path: Path, expected_name: str) -> McpDefinition:
    data = _strict_json(path)
    if not isinstance(data, dict):
        raise ProfileError(f"MCP definition must be an object: {path}")
    _expect_keys(
        data, {"version", "name", "command", "args", "env"}, f"MCP {expected_name}"
    )
    if type(data["version"]) is not int or data["version"] != 1:
        raise ProfileError(f"MCP {expected_name}.version must be 1")
    if data["name"] != expected_name:
        raise ProfileError(f"MCP {expected_name}.name must equal its file name")
    if (
        not isinstance(data["command"], str)
        or not data["command"]
        or "\x00" in data["command"]
    ):
        raise ProfileError(
            f"MCP {expected_name}.command must be a non-empty NUL-free string"
        )
    args = data["args"]
    if not isinstance(args, list) or any(
        not isinstance(item, str) or "\x00" in item for item in args
    ):
        raise ProfileError(
            f"MCP {expected_name}.args must be an array of NUL-free strings"
        )
    env = data["env"]
    if not isinstance(env, dict) or any(
        not isinstance(key, str)
        or not key
        or "\x00" in key
        or not isinstance(value, str)
        or "\x00" in value
        for key, value in env.items()
    ):
        raise ProfileError(f"MCP {expected_name}.env must be a string-to-string object")
    return McpDefinition(
        expected_name, data["command"], tuple(args), dict(sorted(env.items())), path
    )


def _path_key(value: str) -> str:
    """Normalize one relative path spelling for conservative cross-platform comparisons."""

    return os.path.normcase(value.replace("\\", "/")).casefold()


def _check_project_pollution(root: Path) -> None:
    violations: list[str] = []
    bypass_dirs = {_path_key(value) for value in PROJECT_BYPASS_DIRS}
    bypass_files = {_path_key(value) for value in PROJECT_BYPASS_FILES}
    bypass_paths = {_path_key(value) for value in PROJECT_BYPASS_PATHS}
    for item in sorted(
        root.rglob("*"), key=lambda path: path.relative_to(root).as_posix()
    ):
        relative = item.relative_to(root)
        relative_text = relative.as_posix()
        if relative.parts[0] in {".cap", ".git"}:
            continue
        if any(_path_key(part) in bypass_dirs for part in relative.parts):
            violations.append(relative_text)
            continue
        if _path_key(relative_text) in bypass_paths:
            violations.append(relative_text)
            continue
        if _path_key(item.name) in bypass_files and relative_text != "AGENTS.md":
            violations.append(relative_text)
    if violations:
        raise ProfileError(
            f"project capability bypass detected: {', '.join(violations)}"
        )


def _codex_capability_root_is_disabled(value: Any) -> bool:
    """Return whether a capability root or all of its named entries are disabled."""

    if not isinstance(value, Mapping) or not value:
        return False
    if value.get("enabled") is False:
        return True
    return all(
        isinstance(entry, Mapping) and entry.get("enabled") is False
        for entry in value.values()
    )


def _codex_config_has_active_capability(config: Mapping[str, Any]) -> bool:
    """Return whether a Codex config actively enables model-visible capability input."""

    for key in CODEX_CAPABILITY_KEYS - {"hooks", "plugins", "skills"}:
        value = config.get(key)
        if not value:
            continue
        if (
            key in CODEX_EXPLICITLY_DISABLABLE_ROOTS
            and _codex_capability_root_is_disabled(value)
        ):
            continue
        return True
    projects = config.get("projects")
    if projects and (
        not isinstance(projects, Mapping)
        or any(
            not isinstance(value, Mapping)
            or set(value) - {"trust_level"}
            or not isinstance(value.get("trust_level"), str)
            for value in projects.values()
        )
    ):
        return True
    if any(
        value
        for key, value in config.items()
        if key not in CODEX_RUNTIME_ONLY_KEYS and key not in CODEX_CAPABILITY_KEYS
    ):
        return True
    hooks = config.get("hooks")
    if hooks and (
        not isinstance(hooks, Mapping) or any(key != "state" for key in hooks)
    ):
        return True
    features = config.get("features")
    if features and not isinstance(features, Mapping):
        return True
    if isinstance(features, Mapping):
        for key, value in features.items():
            if key in CODEX_CAPABILITY_FEATURES:
                if value is True:
                    return True
                if value is not False:
                    return True
            elif key not in CODEX_RUNTIME_ONLY_FEATURES and value not in (False, None):
                return True
    plugins = config.get("plugins")
    if plugins and (
        not isinstance(plugins, Mapping)
        or any(
            not isinstance(value, Mapping) or value.get("enabled") is not False
            for value in plugins.values()
        )
    ):
        return True
    skills = config.get("skills")
    if isinstance(skills, Mapping):
        if any(key != "config" for key in skills):
            return True
        entries = skills.get("config", ())
        if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
            return True
        if any(
            not isinstance(entry, Mapping) or entry.get("enabled") is not False
            for entry in entries
        ):
            return True
    elif skills:
        return True
    return False


def _qoder_hooks_are_ignored_host_integrations(value: Any, home: Path) -> bool:
    """Return whether Qoder Hooks contain only the ignored Yunke/R2C integrations."""

    if not isinstance(value, Mapping):
        return False
    yunke_command = f"{home}/.yunke/aah_hooks/hook_entry --agent-type=qoder"
    r2c_command = f"bash {home}/.r2c/scripts/qoder-cli-hook.sh"
    for registrations in value.values():
        if not isinstance(registrations, Sequence) or isinstance(
            registrations, (str, bytes)
        ):
            return False
        for registration in registrations:
            if not isinstance(registration, Mapping) or set(registration) - {
                "hooks",
                "matcher",
            }:
                return False
            actions = registration.get("hooks")
            if not isinstance(actions, Sequence) or isinstance(actions, (str, bytes)):
                return False
            for action in actions:
                if not isinstance(action, Mapping) or action.get("type") != "command":
                    return False
                command = action.get("command")
                if command == yunke_command:
                    if action.get("_yunke_managed") is not True or set(action) - {
                        "_yunke_managed",
                        "command",
                        "timeout",
                        "type",
                    }:
                        return False
                elif command == r2c_command:
                    if set(action) - {"command", "timeout", "type"}:
                        return False
                else:
                    return False
    return True


def _qoder_config_has_active_capability(config: Mapping[str, Any], home: Path) -> bool:
    """Return whether a Qoder config actively enables project business capability."""

    enabled_plugins = config.get("enabledPlugins")
    if isinstance(enabled_plugins, Mapping) and any(
        value is not False for value in enabled_plugins.values()
    ):
        return True
    hooks = config.get("hooks")
    if hooks and not _qoder_hooks_are_ignored_host_integrations(hooks, home):
        return True
    return any(config.get(key) for key in ("mcpServers", "plugins", "skills"))


def _matches_host_floor(path: Path) -> bool:
    """Return whether one global instruction entry is exactly the inert host floor."""

    try:
        return path.is_file() and path.read_text(encoding="utf-8") == HOST_FLOOR_TEXT
    except (OSError, UnicodeError):
        return False


def _path_has_symlink_component(path: Path) -> bool:
    """Return whether an absolute path traverses a symlink at any component."""

    current = Path(path.anchor)
    try:
        for part in path.parts[1:]:
            current /= part
            if current.is_symlink():
                return True
    except OSError:
        return True
    return False


def _tree_has_symlink(root: Path) -> bool:
    """Return whether a materialized capability tree contains any symlink."""

    try:
        return root.is_symlink() or any(item.is_symlink() for item in root.rglob("*"))
    except OSError:
        return True


def _codex_system_skills_are_disabled(
    path: Path, config: Mapping[str, Any], home: Path
) -> bool:
    """Return whether every materialized Codex system Skill is explicitly disabled."""

    features = config.get("features")
    if not isinstance(features, Mapping) or features.get("skill_search") is not False:
        return False
    skills = config.get("skills")
    if not isinstance(skills, Mapping):
        return False
    entries = skills.get("config")
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
        return False
    if _tree_has_symlink(path):
        return False
    disabled: set[Path] = set()
    for entry in entries:
        if not isinstance(entry, Mapping) or entry.get("enabled") is not False:
            continue
        raw_path = entry.get("path")
        if not isinstance(raw_path, str) or not raw_path:
            continue
        entry_path = Path(raw_path).expanduser()
        if not entry_path.is_absolute():
            entry_path = home / ".codex" / entry_path
        entry_path = Path(os.path.abspath(entry_path))
        if _path_has_symlink_component(entry_path):
            continue
        disabled.add(entry_path)
    materialized = {Path(os.path.abspath(skill)) for skill in path.rglob("SKILL.md")}
    return materialized.issubset(disabled)


def _qoder_plugin_cache_is_disabled(path: Path, config: Mapping[str, Any]) -> bool:
    """Return whether every materialized Qoder plugin is explicitly disabled."""

    enabled = config.get("enabledPlugins")
    if (
        not isinstance(enabled, Mapping)
        or not enabled
        or any(value is not False for value in enabled.values())
        or _tree_has_symlink(path)
    ):
        return False
    try:
        root_entries = list(path.iterdir())
    except OSError:
        return False
    if any(
        item.name not in {"cache", "data"} or not item.is_dir() for item in root_entries
    ):
        return False
    data = path / "data"
    if data.exists():
        try:
            data_entries = list(data.iterdir())
            if any(
                item.name != "security-scan" or not item.is_dir() or any(item.iterdir())
                for item in data_entries
            ):
                return False
        except OSError:
            return False
    cache = path / "cache"
    if not cache.is_dir():
        return False
    for marketplace in cache.iterdir():
        if not marketplace.is_dir():
            return False
        children = list(marketplace.iterdir())
        if marketplace.name.startswith("qoder-enterprise-"):
            if any(
                item.name != "update.lock" or not item.is_file() for item in children
            ):
                return False
            continue
        for plugin in children:
            if not plugin.is_dir():
                return False
            if enabled.get(f"{plugin.name}@{marketplace.name}") is not False:
                return False
    return True


def _orca_managed_extensions_are_inert(path: Path) -> bool:
    """Return whether a client extension root contains only Orca runtime adapters."""

    if _tree_has_symlink(path):
        return False
    try:
        entries = list(path.iterdir())
        if not entries or any(
            not item.is_file() or item.name not in ORCA_MANAGED_EXTENSION_NAMES
            for item in entries
        ):
            return False
        for item in entries:
            with item.open(encoding="utf-8") as stream:
                if stream.readline(128).rstrip() != "// @orca-managed-pi-extension":
                    return False
        return True
    except (OSError, UnicodeError):
        return False


def _global_path_is_passive(
    relative: str,
    path: Path,
    home: Path,
    codex_config: Mapping[str, Any],
    qoder_config: Mapping[str, Any],
) -> bool:
    """Return whether an existing global path is an inert floor, empty root, or cache."""

    if path.is_dir() and not any(path.iterdir()):
        return True
    if relative in GLOBAL_FLOOR_PATHS:
        return _matches_host_floor(path)
    if relative in {".omp/agent/extensions", ".pi/agent/extensions"}:
        return _orca_managed_extensions_are_inert(path)
    codex_features = codex_config.get("features")
    if relative == ".codex/hooks":
        return (
            isinstance(codex_features, Mapping) and codex_features.get("hooks") is False
        )
    if relative == ".codex/plugins":
        return (
            isinstance(codex_features, Mapping)
            and codex_features.get("plugins") is False
            and not _codex_config_has_active_capability(
                {**codex_config, "skills": {}, "hooks": {}}
            )
        )
    if relative == ".codex/skills":
        return _codex_system_skills_are_disabled(path, codex_config, home)
    if relative == ".qoder/plugins":
        return _qoder_plugin_cache_is_disabled(path, qoder_config)
    return False


def _check_global_pollution() -> None:
    home = Path.home()
    codex_config_path = home / ".codex" / "config.toml"
    codex_config = _read_toml(codex_config_path) if codex_config_path.is_file() else {}
    qoder_config_path = home / ".qoder" / "settings.json"
    qoder_config = (
        _strict_json(qoder_config_path) if qoder_config_path.is_file() else {}
    )
    violations = {
        relative
        for relative in set(GLOBAL_CAPABILITY_PATHS)
        if os.path.lexists(home / relative)
        and not _global_path_is_passive(
            relative, home / relative, home, codex_config, qoder_config
        )
    }
    if codex_config and _codex_config_has_active_capability(codex_config):
        violations.add(".codex/config.toml")
    json_configs = {
        ".claude.json": {"enabledPlugins", "hooks", "mcpServers", "plugins", "skills"},
        ".gemini/settings.json": {
            "extensions",
            "hooks",
            "mcpServers",
            "plugins",
            "skills",
        },
    }
    for relative, keys in json_configs.items():
        path = home / relative
        if path.is_file() and _contains_mapping_key(_strict_json(path), keys):
            violations.add(relative)
    if qoder_config and _qoder_config_has_active_capability(qoder_config, home):
        violations.add(".qoder/settings.json")
    text_configs = {
        ".config/opencode/opencode.json": {"instructions", "mcp", "plugin"},
        ".omp/agent/config.yml": {
            "extensions",
            "hooks",
            "mcp",
            "mcpServers",
            "plugins",
            "rules",
            "skills",
        },
        ".pi/agent/config.yml": {
            "extensions",
            "hooks",
            "mcp",
            "mcpServers",
            "plugins",
            "rules",
            "skills",
        },
    }
    for relative, keys in text_configs.items():
        path = home / relative
        if path.is_file() and _text_has_top_level_key(path, keys):
            violations.add(relative)
    if violations:
        raise ProfileError(
            f"global capability pollution detected: {', '.join(sorted(violations))}"
        )


def _desired_lock(project: Project) -> dict[str, Any]:
    profiles: dict[str, Any] = {}
    for name, profile in sorted(project.profiles.items()):
        clients = {
            client: {"tree_hash": _tree_hash(_render_tree(project, client, profile))}
            for client in CLIENTS
        }
        profiles[name] = {"inventory": _profile_inventory(profile), "clients": clients}
    return {
        "version": LOCK_VERSION,
        "renderer_version": RENDERER_VERSION,
        "clients": {
            client: {
                "adapter_version": CLIENT_ADAPTER_VERSION,
                "executable": CLIENT_EXECUTABLES[client],
            }
            for client in CLIENTS
        },
        "capability_semantics": {
            "skills": "native-staging",
            "mcp": "native-config",
            "hooks": "opaque-staging",
            "plugins": "opaque-staging",
        },
        "inputs": _input_records(project),
        "profiles": profiles,
    }


def _profile_inventory(profile: Profile) -> dict[str, list[str]]:
    return {
        "skills": list(profile.skills),
        "mcps": list(profile.mcps),
        "hooks": list(profile.hooks),
        "plugins": list(profile.plugins),
    }


def _input_records(project: Project) -> dict[str, Any]:
    paths: set[Path] = {project.manifest, project.root / "AGENTS.md"}
    for profile in project.profiles.values():
        paths.update({profile.source, profile.prompt})
    capability_root = project.root / ".cap" / "capabilities"
    paths.add(capability_root)
    paths.update(capability_root.rglob("*"))
    records: dict[str, Any] = {}
    for path in sorted(
        paths, key=lambda item: item.relative_to(project.root).as_posix()
    ):
        relative = path.relative_to(project.root).as_posix()
        if path.is_symlink():
            raise ProfileError(f"lock input must not be a symlink: {relative}")
        if path.is_dir():
            records[relative] = {"type": "directory"}
        elif path.is_file():
            records[relative] = {
                "type": "file",
                "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}",
                "sha256": _sha256(path.read_bytes()),
            }
        else:
            raise ProfileError(
                f"lock input is not a regular file or directory: {relative}"
            )
    return records


def _verify_lock(project: Project, desired: Mapping[str, Any]) -> None:
    lock_path = project.root / ".cap" / "lock.json"
    if lock_path.is_symlink() or not lock_path.is_file():
        raise ProfileError("missing regular .cap/lock.json; run profile lock")
    actual = _strict_json(lock_path)
    if actual != desired:
        raise ProfileError(
            "capability lock drift detected; run profile lock after reviewing changes"
        )


def _render_tree(
    project: Project, client: str, profile: Profile
) -> dict[str, RenderedFile]:
    _validate_client(client)
    tree: dict[str, RenderedFile] = {}
    folded_paths: dict[str, str] = {}

    def put(path: str, rendered: RenderedFile, source: str) -> None:
        relative = _safe_relative(path, f"render path from {source}").as_posix()
        folded = relative.casefold()
        if relative in tree or folded in folded_paths:
            prior = folded_paths.get(folded, relative)
            raise ProfileError(
                f"render path conflict: {relative} from {source} conflicts with {prior}"
            )
        tree[relative] = rendered
        folded_paths[folded] = relative

    prompt = _profile_prompt(profile)
    mcp_definitions = [project.mcps[name] for name in profile.mcps]
    if client == "codex":
        put(
            "config.toml",
            RenderedFile(_codex_config(mcp_definitions)),
            "codex renderer",
        )
        put("AGENTS.md", RenderedFile(prompt), "codex renderer")
    elif client == "qoder":
        put("settings.json", RenderedFile(b"{}\n"), "qoder renderer")
        put("mcp.json", RenderedFile(_qoder_mcp(mcp_definitions)), "qoder renderer")
        put("system-prompt.md", RenderedFile(prompt), "qoder renderer")
    else:
        put("config.yml", RenderedFile(b"{}\n"), "omp renderer")
        put("mcp.json", RenderedFile(_omp_mcp(mcp_definitions)), "omp renderer")
        put("system-prompt.md", RenderedFile(prompt), "omp renderer")

    skills_root = project.root / ".cap" / "capabilities" / "skills"
    for skill in profile.skills:
        source_root = skills_root / skill
        for source in sorted(
            source_root.rglob("*"),
            key=lambda path: path.relative_to(source_root).as_posix(),
        ):
            if source.is_file():
                relative = source.relative_to(source_root).as_posix()
                put(
                    f"skills/{skill}/{relative}",
                    RenderedFile(
                        source.read_bytes(), stat.S_IMODE(source.stat().st_mode)
                    ),
                    f"skill {skill}",
                )

    capability_root = project.root / ".cap" / "capabilities"
    for kind, names in (("hooks", profile.hooks), ("plugins", profile.plugins)):
        for name in names:
            target = capability_root / kind / name / "targets" / client
            if not target.is_dir() or target.is_symlink():
                raise ProfileError(f"{kind[:-1]} {name} lacks required {client} target")
            for source in sorted(
                target.rglob("*"), key=lambda path: path.relative_to(target).as_posix()
            ):
                if source.is_file():
                    relative = source.relative_to(target).as_posix()
                    put(
                        relative,
                        RenderedFile(
                            source.read_bytes(), stat.S_IMODE(source.stat().st_mode)
                        ),
                        f"{kind[:-1]} {name}",
                    )
    return dict(sorted(tree.items()))


def _read_nonempty_text(path: Path, context: str) -> str:
    """Read one required non-empty UTF-8 project source file."""

    try:
        value = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        raise ProfileError(f"{context} must be readable UTF-8 text: {error}") from error
    if not value:
        raise ProfileError(f"{context} must be non-empty")
    return value


def _profile_prompt(profile: Profile) -> bytes:
    text = _read_nonempty_text(profile.prompt, f"profile {profile.name} prompt")
    return f"{text}\n".encode("utf-8")


def _codex_config(definitions: Sequence[McpDefinition]) -> bytes:
    lines = ['cli_auth_credentials_store = "file"']
    for definition in definitions:
        if lines:
            lines.append("")
        lines.extend(
            [
                f"[mcp_servers.{definition.name}]",
                f"command = {_toml_string(definition.command)}",
                f"args = {_toml_array(definition.args)}",
                "required = true",
            ]
        )
        if definition.env:
            lines.append("")
            lines.append(f"[mcp_servers.{definition.name}.env]")
            for key, value in sorted(definition.env.items()):
                lines.append(f"{_toml_key(key)} = {_toml_string(value)}")
    return (("\n".join(lines) + "\n") if lines else "").encode("utf-8")


def _qoder_mcp(definitions: Sequence[McpDefinition]) -> bytes:
    servers = {
        definition.name: {
            "command": definition.command,
            "args": list(definition.args),
            "env": dict(definition.env),
        }
        for definition in definitions
    }
    return _canonical_json({"mcpServers": servers})


def _omp_mcp(definitions: Sequence[McpDefinition]) -> bytes:
    servers = {
        definition.name: {
            "type": "stdio",
            "command": definition.command,
            "args": list(definition.args),
            "env": dict(definition.env),
        }
        for definition in definitions
    }
    return _canonical_json({"mcpServers": servers})


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _toml_array(values: Sequence[str]) -> str:
    return "[" + ", ".join(_toml_string(value) for value in values) + "]"


def _toml_key(value: str) -> str:
    return value if re.fullmatch(r"[A-Za-z0-9_-]+", value) else _toml_string(value)


def _tree_hash(tree: Mapping[str, RenderedFile]) -> str:
    records = {
        path: {
            "mode": f"{rendered.mode:04o}",
            "sha256": _sha256(rendered.content),
        }
        for path, rendered in sorted(tree.items())
    }
    return f"sha256:{_sha256(_canonical_json(records))}"


def _write_all(descriptor: int, content: bytes) -> None:
    """Write every byte to one already-open file descriptor."""

    remaining = memoryview(content)
    while remaining:
        written = os.write(descriptor, remaining)
        if written <= 0:
            raise OSError("file write made no progress")
        remaining = remaining[written:]


def _materialize_tree(
    directory: StableDirectory, tree: Mapping[str, RenderedFile]
) -> None:
    """Materialize files relative to held no-follow directory descriptors."""

    directories: dict[tuple[str, ...], int] = {(): directory.descriptor}
    created_descriptors: list[int] = []
    directory_records: list[tuple[int, str, int, int, int]] = []
    file_records: list[tuple[int, str, int, int]] = []
    try:
        _validate_stable_directory(directory)
        for relative, rendered in sorted(tree.items()):
            relative_path = PurePosixPath(relative)
            if (
                relative_path.is_absolute()
                or not relative_path.parts
                or any(part in {"", ".", ".."} for part in relative_path.parts)
            ):
                raise ProfileError(
                    f"render path must be normalized and relative: {relative}"
                )
            parent_key: tuple[str, ...] = ()
            parent_descriptor = directory.descriptor
            for part in relative_path.parts[:-1]:
                child_key = (*parent_key, part)
                child_descriptor = directories.get(child_key)
                if child_descriptor is None:
                    try:
                        os.mkdir(part, 0o700, dir_fd=parent_descriptor)
                    except FileExistsError as error:
                        raise ProfileError(
                            f"materialize directory appeared concurrently: {'/'.join(child_key)}"
                        ) from error
                    child_descriptor = os.open(
                        part,
                        _directory_open_flags(),
                        dir_fd=parent_descriptor,
                    )
                    child_info = os.fstat(child_descriptor)
                    live_info = os.stat(
                        part, dir_fd=parent_descriptor, follow_symlinks=False
                    )
                    if not stat.S_ISDIR(child_info.st_mode) or not _same_file_identity(
                        live_info, child_info.st_dev, child_info.st_ino
                    ):
                        os.close(child_descriptor)
                        raise ProfileError(
                            f"materialize directory changed: {'/'.join(child_key)}"
                        )
                    directories[child_key] = child_descriptor
                    created_descriptors.append(child_descriptor)
                    directory_records.append(
                        (
                            parent_descriptor,
                            part,
                            child_descriptor,
                            child_info.st_dev,
                            child_info.st_ino,
                        )
                    )
                parent_key = child_key
                parent_descriptor = child_descriptor
            file_name = relative_path.parts[-1]
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            for name in ("O_CLOEXEC", "O_NOFOLLOW"):
                flags |= getattr(os, name, 0)
            descriptor = os.open(
                file_name,
                flags,
                rendered.mode,
                dir_fd=parent_descriptor,
            )
            try:
                os.fchmod(descriptor, rendered.mode)
                _write_all(descriptor, rendered.content)
                os.fsync(descriptor)
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ProfileError(f"materialized file is not private: {relative}")
                file_records.append(
                    (parent_descriptor, file_name, info.st_dev, info.st_ino)
                )
            finally:
                os.close(descriptor)
        for parent_descriptor, name, descriptor, device, inode in directory_records:
            live = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
            held = os.fstat(descriptor)
            if not _same_file_identity(live, device, inode) or not _same_file_identity(
                held, device, inode
            ):
                raise ProfileError(f"materialized directory changed: {name}")
        for parent_descriptor, name, device, inode in file_records:
            live = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
            if (
                not stat.S_ISREG(live.st_mode)
                or live.st_nlink != 1
                or not _same_file_identity(live, device, inode)
            ):
                raise ProfileError(f"materialized file changed: {name}")
        for descriptor in created_descriptors:
            os.fsync(descriptor)
        os.fsync(directory.descriptor)
        _validate_stable_directory(directory)
    except ProfileError:
        raise
    except (OSError, NotImplementedError) as error:
        raise ProfileError(f"could not materialize tree: {error}") from error
    finally:
        for descriptor in reversed(created_descriptors):
            try:
                os.close(descriptor)
            except OSError:
                pass


def _select_profile(project: Project, profile_name: str) -> Profile:
    if not profile_name:
        raise ProfileError("profile is required; there is no default profile")
    try:
        return project.profiles[profile_name]
    except KeyError as error:
        raise ProfileError(f"unknown profile: {profile_name}") from error


def _validate_client(client: str) -> None:
    if client not in CLIENTS:
        raise ProfileError(f"unknown client: {client}")


def _validate_forwarded_args(client: str, args: Sequence[str]) -> None:
    forbidden = FORBIDDEN_CLIENT_ARGUMENTS[client]
    for argument in args:
        if not isinstance(argument, str) or "\x00" in argument:
            raise ProfileError("forwarded arguments must be NUL-free strings")
        key = argument.split("=", 1)[0]
        compact_prefixes = {
            "codex": ("-c", "-C", "-p"),
            "qoder": ("-w",),
            "omp": ("-e",),
        }[client]
        compact_override = any(
            argument.startswith(prefix) for prefix in compact_prefixes
        )
        if key in forbidden or compact_override:
            raise ProfileError(
                f"forwarded argument may override the {client} capability root: {argument}"
            )


def _require_git_root(root: Path) -> None:
    completed = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        raise ProfileError("run requires the profile project to be a Git worktree root")
    try:
        discovered = Path(completed.stdout.strip()).resolve(strict=True)
    except OSError as error:
        raise ProfileError("Git reported an invalid worktree root") from error
    if discovered != root:
        raise ProfileError(
            f"profile project must equal the Git worktree root; discovered {discovered}"
        )


def _contains_mapping_key(value: Any, keys: set[str]) -> bool:
    """Return whether a nested mapping contains any capability-bearing key."""

    if isinstance(value, Mapping):
        return any(
            key in keys or _contains_mapping_key(item, keys)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(_contains_mapping_key(item, keys) for item in value)
    return False


def _text_has_top_level_key(path: Path, keys: set[str]) -> bool:
    """Detect capability-bearing top-level keys in YAML or JSONC configuration."""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as error:
        raise ProfileError(
            f"global config must be readable UTF-8 text: {path}: {error}"
        ) from error
    stripped = text.lstrip()
    if stripped.startswith("{"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            alternatives = "|".join(re.escape(key) for key in sorted(keys))
            return (
                re.search(
                    rf"(?m)^[ \t]*(?:\"(?:{alternatives})\"|'(?:{alternatives})'|(?:{alternatives}))\s*:",
                    text,
                )
                is not None
            )
        return isinstance(data, dict) and any(key in data for key in keys)
    alternatives = "|".join(re.escape(key) for key in sorted(keys))
    return (
        re.search(
            rf"(?m)^(?:\"(?:{alternatives})\"|'(?:{alternatives})'|(?:{alternatives}))\s*:",
            text,
        )
        is not None
    )


def _prepare_receipt_path(value: Path | str) -> Path:
    """Normalize one lexical receipt target without resolving mutable ancestors."""

    path = Path(value).expanduser().absolute()
    if not path.name:
        raise ProfileError("receipt target must name a file")
    parent = _normalize_root_alias(path.parent, "receipt parent")
    return parent / path.name


def _reserve_receipt(
    project: Project,
    path: Path,
    *,
    parent_directory: StableDirectory | None = None,
) -> ReceiptReservation:
    """Exclusively create an external receipt through a stable parent descriptor."""

    if parent_directory is not None:
        if path.parent != parent_directory.path:
            raise ProfileError("receipt parent handle does not match the target path")
        _validate_stable_directory(parent_directory)
        _require_external_directory(project, parent_directory, "receipt")
        parent_descriptor = os.dup(parent_directory.descriptor)
        os.set_inheritable(parent_descriptor, False)
        parent_info = os.fstat(parent_descriptor)
    else:
        with _stable_directory(path.parent, "receipt parent") as stable_parent:
            _require_external_directory(project, stable_parent, "receipt")
            parent_descriptor = os.dup(stable_parent.descriptor)
            os.set_inheritable(parent_descriptor, False)
            parent_info = os.fstat(parent_descriptor)
    descriptor: int | None = None
    try:
        live_parent = os.stat(path.parent, follow_symlinks=False)
        if not stat.S_ISDIR(live_parent.st_mode) or not _same_file_identity(
            live_parent, parent_info.st_dev, parent_info.st_ino
        ):
            raise ProfileError("receipt parent changed before reservation")

        target_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        for name in ("O_CLOEXEC", "O_NOFOLLOW"):
            target_flags |= getattr(os, name, 0)
        try:
            descriptor = os.open(
                path.name,
                target_flags,
                0o600,
                dir_fd=parent_descriptor,
            )
        except FileExistsError as error:
            raise ProfileError(f"receipt target already exists: {path}") from error
        except (OSError, NotImplementedError) as error:
            raise ProfileError(f"could not reserve receipt target: {error}") from error
        os.fchmod(descriptor, 0o600)
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ProfileError("reserved receipt must be a private regular file")
        return ReceiptReservation(
            path=path,
            parent_descriptor=parent_descriptor,
            descriptor=descriptor,
            parent_device=parent_info.st_dev,
            parent_inode=parent_info.st_ino,
            device=info.st_dev,
            inode=info.st_ino,
        )
    except BaseException:
        try:
            if descriptor is not None:
                _unlink_reserved_receipt(
                    parent_descriptor,
                    descriptor,
                    path.name,
                )
        finally:
            try:
                if descriptor is not None:
                    os.close(descriptor)
            finally:
                os.close(parent_descriptor)
        raise


def _validate_receipt_reservation(reservation: ReceiptReservation) -> None:
    try:
        if any(
            candidate.is_symlink()
            for candidate in (reservation.path.parent, *reservation.path.parent.parents)
        ):
            raise ProfileError("receipt parent changed to a symlink")
        parent_info = os.stat(reservation.path.parent, follow_symlinks=False)
        target_info = os.stat(
            reservation.path.name,
            dir_fd=reservation.parent_descriptor,
            follow_symlinks=False,
        )
        descriptor_info = os.fstat(reservation.descriptor)
    except (OSError, NotImplementedError) as error:
        raise ProfileError(
            f"receipt reservation is no longer stable: {error}"
        ) from error
    if not stat.S_ISDIR(parent_info.st_mode) or not _same_file_identity(
        parent_info,
        reservation.parent_device,
        reservation.parent_inode,
    ):
        raise ProfileError("receipt parent changed after reservation")
    if (
        target_info.st_nlink != 1
        or descriptor_info.st_nlink != 1
        or not stat.S_ISREG(target_info.st_mode)
        or not stat.S_ISREG(descriptor_info.st_mode)
        or not _same_file_identity(
            target_info,
            reservation.device,
            reservation.inode,
        )
        or not _same_file_identity(
            descriptor_info,
            reservation.device,
            reservation.inode,
        )
    ):
        raise ProfileError("receipt target changed or gained a hard-link alias")


def _commit_receipt(reservation: ReceiptReservation, content: bytes) -> None:
    """Commit bytes to the reserved inode without resolving the receipt path again."""

    _validate_receipt_reservation(reservation)
    try:
        os.lseek(reservation.descriptor, 0, os.SEEK_SET)
        os.ftruncate(reservation.descriptor, 0)
        _write_all(reservation.descriptor, content)
        os.fsync(reservation.descriptor)
    except OSError as error:
        raise ProfileError(f"could not commit receipt: {error}") from error
    _validate_receipt_reservation(reservation)


def _unlink_reserved_receipt(
    parent_descriptor: int,
    descriptor: int,
    name: str,
) -> None:
    try:
        target_info = os.stat(
            name,
            dir_fd=parent_descriptor,
            follow_symlinks=False,
        )
        descriptor_info = os.fstat(descriptor)
        if (target_info.st_dev, target_info.st_ino) == (
            descriptor_info.st_dev,
            descriptor_info.st_ino,
        ):
            os.unlink(name, dir_fd=parent_descriptor)
    except (FileNotFoundError, NotImplementedError):
        return


def _release_receipt(reservation: ReceiptReservation, *, remove: bool) -> None:
    try:
        if remove:
            _unlink_reserved_receipt(
                reservation.parent_descriptor,
                reservation.descriptor,
                reservation.path.name,
            )
    finally:
        try:
            os.close(reservation.descriptor)
        finally:
            os.close(reservation.parent_descriptor)


def _atomic_write(path: Path, content: bytes, *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(mode)
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _canonical_json(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _print_json(value: Any) -> None:
    sys.stdout.buffer.write(_canonical_json(value))


if __name__ == "__main__":
    raise SystemExit(main())
