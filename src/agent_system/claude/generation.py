"""Content-addressed Claude generations: the three hashes and the CAS.

The three hashes have distinct jobs and are deliberately not merged:

* `portable_tree_hash` fingerprints the declaration alone, so it is identical on
  every machine and is what the project lock records.
* `effective_render_hash` folds in the machine binding, the runtime policy and
  the fixed launch gates. It names the CAS directory, so a policy change cannot
  silently reuse a render built under different rules.
* `content_digest` fingerprints the bytes actually on disk, so a generation that
  is edited after it was built is rejected rather than trusted.
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

import yaml

from agent_system.adapter.common import (
    _digest_json,
    generation_source_context,
    materialize_generation,
    render_portable_tree,
    verify_generation,
)
from agent_system.cap.support import _base_args, _binding_args
from agent_system.claude import native
from agent_system.claude.runtime import (
    CLIENT,
    ClaudeError,
    effective_claude_config,
    read_claude_runtime_policy,
    read_global_claude_preference,
)

MANIFEST_VERSION = 1

# Digest of the recorded observations this adapter was written against. It
# enters the generation manifest, so revising the evidence invalidates every
# cached generation instead of letting a stale assumption keep serving renders.
# `test_verified_surface_digest_matches_the_evidence_file` fails if the two
# drift apart.
VERIFIED_SURFACE_DIGEST = (
    "sha256:715a178ab365bdd9b9f0aa92df3523f703340156c4e4d59ce88fd15131e7098f"
)

# Flags CAP always supplies. They are recorded in the hash rather than merely
# passed, so turning one off produces a different generation instead of quietly
# reusing one built with the gate closed.
FIXED_LAUNCH_FLAGS = (
    "--settings",
    "--setting-sources",
    "--mcp-config",
    "--strict-mcp-config",
    "--plugin-dir",
    "--append-system-prompt",
)


def _real_home(args: argparse.Namespace) -> Path:
    return Path(
        getattr(args, "_real_home", getattr(args, "home", Path.home()))
    ).expanduser().absolute()


def claude_state_root(args: argparse.Namespace) -> Path:
    return _real_home(args) / ".agent-system-state"


def claude_render_root(args: argparse.Namespace) -> Path:
    return claude_state_root(args) / "renders" / CLIENT


def _portable_config(rendered: Path) -> dict[str, object]:
    """Read the CAP-side intermediate from the portable render.

    It is an empty table today; reading it anyway keeps the portable render the
    single source for what the adapter composes on top of.
    """

    path = rendered / "claude-config.yaml"
    if not path.is_file():
        return {}
    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ClaudeError("portable Claude configuration is invalid") from error
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ClaudeError("portable Claude configuration must be an object")
    return parsed


def _portable_mcp_servers(rendered: Path) -> dict[str, object]:
    import json

    path = rendered / "mcp.json"
    if not path.is_file():
        return {}
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ClaudeError("portable Claude MCP configuration is invalid") from error
    servers = parsed.get("mcpServers") if isinstance(parsed, dict) else None
    if not isinstance(servers, dict):
        raise ClaudeError("portable Claude MCP configuration has no mcpServers")
    return servers


# Windows refuses paths longer than this unless long-path support is enabled.
# The generation prefix is already long -- a content-addressed directory name is
# 64 characters -- and skills nest another few levels under it, so the limit is
# reachable in practice rather than theoretical.
MAX_PORTABLE_PATH = 260


def _check_generation_path_budget(
    rendered: Path, generation: Path, skill_names: tuple[str, ...]
) -> None:
    """Fail with an actionable message rather than a bare OSError mid-copy.

    The check runs on every platform against the real paths that are about to be
    created, so a machine whose home directory is deep is caught the same way a
    deeply nested skill is. Aborting here also avoids leaving a partial stage
    behind.
    """

    prefix = generation / native.PLUGIN_SKILLS_ROOT
    worst = ""
    for name in skill_names:
        source = rendered / "skills" / name
        if not source.is_dir():
            continue
        for path in source.rglob("*"):
            candidate = str(prefix / name / path.relative_to(source))
            if len(candidate) > len(worst):
                worst = candidate
    if len(worst) > MAX_PORTABLE_PATH:
        raise ClaudeError(
            "Claude generation would exceed the portable path budget "
            f"({len(worst)} > {MAX_PORTABLE_PATH}): {worst}. "
            "Shorten the skill's inner paths, or enable long-path support on "
            "this host."
        )


def materialize_claude_generation(
    args: argparse.Namespace, env: dict[str, str]
) -> tuple[Path, str, str, tuple[str, ...]]:
    """Render, hash and place one Claude generation, reusing an identical one."""

    with tempfile.TemporaryDirectory(
        prefix=f"cap-render-{args.profile}-claude-"
    ) as temporary:
        rendered = Path(temporary)
        portable_hash, skill_names = render_portable_tree(
            command=[
                *_base_args(args),
                "materialize",
                "--client",
                CLIENT,
                "--profile",
                args.profile,
                "--output",
                temporary,
                *_binding_args(args),
            ],
            env=env,
            output=rendered,
            client="Claude",
        )

        policy = read_claude_runtime_policy(args)
        runtime_dir = claude_runtime_dir(args)
        global_preference = read_global_claude_preference(runtime_dir)
        config = effective_claude_config(
            skill_names,
            _portable_mcp_servers(rendered),
            policy,
            global_preference,
            {},
        )
        portable = _portable_config(rendered)
        if portable:
            raise ClaudeError(
                "portable Claude configuration must stay empty; effective "
                "policy belongs to the adapter, not to the reproducible tree"
            )

        native_files = native.project_claude_native(
            config, profile=args.profile, adapter_version=_adapter_version(args)
        )
        projection = native.native_projection_record(
            native_files,
            adapter_version=_adapter_version(args),
            unsupported=tuple(config["unsupported"]),
            verified_surface_digest=VERIFIED_SURFACE_DIGEST,
        )

        launch = {
            "flags": list(FIXED_LAUNCH_FLAGS),
            "setting_sources": "",
            "skills": list(skill_names),
            "runtime_policy": {
                "project": dict(policy),
                "global_preference_digest": _digest_json(dict(global_preference)),
                "effective": {
                    "login_mode": config["login_mode"],
                    "permission_mode": config["permissions"]["default_mode"],
                    "enable_project_mcp": config["mcp"]["enable_project"],
                    "auto_memory": config["memory"]["auto_memory"],
                },
            },
        }

        source_context, source_digest = generation_source_context(
            profile=args.profile,
            client=CLIENT,
            project=Path(args.project),
            binding_dir=Path(args.binding_dir),
            portable_hash=portable_hash,
        )
        effective_hash = _digest_json(
            {
                "version": MANIFEST_VERSION,
                # OMP's payload has no client field because it was the only
                # effective adapter. With a second one, the field keeps two
                # clients from ever colliding on one CAS entry.
                "client": CLIENT,
                "source_context": source_context,
                "source_digest": source_digest,
                "config": config,
                "launch": launch,
                "native_projection": projection,
            }
        )
        generation = claude_render_root(args) / effective_hash.removeprefix("sha256:")
        _check_generation_path_budget(rendered, generation, skill_names)

        expected = {
            "version": MANIFEST_VERSION,
            "client": CLIENT,
            "profile": args.profile,
            "portable_tree_hash": portable_hash,
            "effective_render_hash": effective_hash,
            "source_context": dict(source_context),
            "source_digest": source_digest,
            "runtime_policy": launch["runtime_policy"],
            "native_projection": projection,
            "login_mode": config["login_mode"],
        }

        def verify(target: Path) -> object:
            return verify_generation(target, expected)

        def write_payload(stage: Path) -> None:
            (stage / "claude-config.yaml").write_text(
                yaml.safe_dump(config, allow_unicode=True, sort_keys=True),
                encoding="utf-8",
            )
            for relative, data in sorted(native_files.items()):
                path = stage / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            skills_source = stage / "skills"
            skills_target = stage / native.PLUGIN_SKILLS_ROOT
            skills_target.mkdir(parents=True, exist_ok=True)
            for name in skill_names:
                source = skills_source / name
                if not source.is_dir():
                    raise ClaudeError(
                        f"declared skill {name} is missing from the render"
                    )
                shutil.copytree(source, skills_target / name)
            delivered = sorted(
                path.name for path in skills_target.iterdir() if path.is_dir()
            )
            # The allowlist appears in the intermediate, in the manifest and as
            # real directories. All three must agree or the client would receive
            # a capability face that no record describes.
            if tuple(delivered) != tuple(skill_names):
                raise ClaudeError(
                    "delivered Claude skills do not match the declared allowlist"
                )

        materialize_generation(
            parent=generation.parent,
            generation=generation,
            source_tree=rendered,
            state_root=claude_state_root(args),
            private_root=_real_home(args),
            write_payload=write_payload,
            manifest_base={**expected, "skills": list(skill_names)},
            verify=verify,
        )
        return generation, portable_hash, effective_hash, skill_names


def claude_runtime_id(args: argparse.Namespace) -> str:
    return str(getattr(args, "claude_runtime_id", "default"))


def claude_runtime_dir(args: argparse.Namespace) -> Path:
    """Where credentials and session state live, shared across projects.

    Keyed by runtime id rather than by generation: authentication is user state,
    not a property of any one render.
    """

    return claude_state_root(args) / "runtimes" / CLIENT / claude_runtime_id(args)


def _adapter_version(args: argparse.Namespace) -> int:
    import json

    lock = json.loads(
        (Path(args.project).expanduser() / ".cap" / "lock.json").read_text(
            encoding="utf-8"
        )
    )
    return int(lock["clients"][CLIENT]["adapter_version"])
