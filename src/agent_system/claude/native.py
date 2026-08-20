"""Projection from the CAP-side Claude configuration into Claude's native files.

This is the only module allowed to name Claude's own configuration keys, and
every name here must have a corresponding entry in the adapter change package's
`evidence/claude-native-surface.json`. Keeping the surface in one file means a
Claude release that renames a key costs one edit plus an adapter version bump.

What is verified today (Claude Code 2.1.236, recorded in that evidence file):

* `.claude-plugin/plugin.json` with `name`, `version`, `description`, `author`
  and `skills`, loaded read-only through `--plugin-dir`. Confirmed by
  experiment: a probe plugin built to this shape produced
  `Loaded 1 skills from plugin cap-probe default directory`.
* An MCP configuration file whose servers live under `mcpServers`, passed with
  `--mcp-config` and narrowed by `--strict-mcp-config`.

What is deliberately *not* projected: any `settings.json` key. `--settings`
accepts a file, but no individual settings key has been verified against a real
client, and this adapter does not guess native keys. Every control CAP needs -
setting sources, MCP strictness, permission mode, prompt injection, skill
delivery - is a verified command-line flag, so the settings file is rendered as
an empty object. It exists so the command-line settings layer belongs to CAP
rather than to whatever else might supply it, and so a future verified key has
a home.
"""

from __future__ import annotations

import json
from collections.abc import Mapping

from agent_system.claude.runtime import ClaudeError

# Relative to the generation root.
NATIVE_ROOT = "native"
SETTINGS_PATH = f"{NATIVE_ROOT}/settings.json"
MCP_PATH = f"{NATIVE_ROOT}/mcp.json"
PLUGIN_ROOT = f"{NATIVE_ROOT}/plugin"
PLUGIN_MANIFEST_PATH = f"{PLUGIN_ROOT}/.claude-plugin/plugin.json"
PLUGIN_SKILLS_ROOT = f"{PLUGIN_ROOT}/skills"

# Top-level keys of the CAP-side configuration that this projection consumes.
# Anything outside this set raises rather than being silently dropped: an
# unmapped field means the projection is behind the configuration schema, and
# rendering anyway would produce a generation whose capability face does not
# match its declaration.
CONSUMED_CONFIG_KEYS = frozenset(
    {
        "version",
        "client",
        "login_mode",
        "skills",
        "mcp",
        "memory",
        "permissions",
        "prompt",
        "unsupported",
    }
)


def _canonical_json_bytes(value: object) -> bytes:
    """Serialize deterministically; these bytes enter the content digest."""

    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")


def plugin_name(profile: str) -> str:
    """Name the session-only plugin that carries this profile's skills.

    Claude echoes the plugin name in its startup log, so a stable, obviously
    CAP-owned name makes the delivery channel identifiable in a real run rather
    than only in our own records.
    """

    return f"cap-{profile}"


def project_claude_native(
    config: Mapping[str, object],
    *,
    profile: str,
    adapter_version: int,
) -> dict[str, bytes]:
    """Return native file bytes keyed by path relative to the generation root.

    Pure: it performs no IO and reads nothing outside `config`. Skill payloads
    are copied by the materializer; this only emits the manifest that makes the
    copied tree loadable.
    """

    unmapped = sorted(set(config) - CONSUMED_CONFIG_KEYS)
    if unmapped:
        raise ClaudeError(
            "Claude native projection does not map configuration fields "
            f"{unmapped}; refusing to drop them silently"
        )

    if config.get("client") != "claude" or config.get("version") != 1:
        raise ClaudeError(
            "Claude native projection requires a version 1 claude configuration"
        )

    mcp = config["mcp"]
    if not isinstance(mcp, Mapping):
        raise ClaudeError("Claude configuration mcp must be a table")
    servers = mcp.get("servers", {})
    if not isinstance(servers, Mapping):
        raise ClaudeError("Claude configuration mcp.servers must be a table")

    if not isinstance(config["skills"], Mapping):
        raise ClaudeError("Claude configuration skills must be a table")

    manifest = {
        "name": plugin_name(profile),
        "version": f"0.0.{adapter_version}",
        "description": (
            "CAP-declared skills for profile "
            f"{profile}; delivered read-only for this session only."
        ),
        "author": {"name": "cap"},
        "skills": "./skills/",
    }

    return {
        # No verified settings key exists yet; see the module docstring.
        SETTINGS_PATH: _canonical_json_bytes({}),
        MCP_PATH: _canonical_json_bytes({"mcpServers": dict(sorted(servers.items()))}),
        PLUGIN_MANIFEST_PATH: _canonical_json_bytes(manifest),
    }


def native_projection_record(
    files: Mapping[str, bytes],
    *,
    adapter_version: int,
    unsupported: tuple[str, ...],
    verified_surface_digest: str,
) -> dict[str, object]:
    """Describe the projection for the generation manifest.

    `verified_surface_digest` pins the evidence this projection was written
    against, so revising the recorded observations invalidates the generation
    instead of letting a stale assumption keep serving cached renders.
    """

    return {
        "adapter_version": adapter_version,
        "files": sorted(files),
        "unsupported": list(unsupported),
        "verified_surface_digest": verified_surface_digest,
    }
