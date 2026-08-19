from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from agent_system.omp import runtime
from agent_system.profile import cli as profile_cli


def _args(project: Path, home: Path) -> argparse.Namespace:
    return argparse.Namespace(project=str(project), agent_home_root=str(home))


def test_policy_preserves_unknown_fields_without_projecting_them(tmp_path: Path) -> None:
    (tmp_path / ".cap" / "runtime").mkdir(parents=True)
    (tmp_path / ".cap" / "runtime" / "omp.toml").write_text(
        'version = 1\nclient = "omp"\n\n[policy]\n'
        'memory_backend = "off"\n'
        'enable_project_mcp = false\n'
        'future_field = "untouched"\n',
        encoding="utf-8",
    )
    policy = runtime._read_omp_runtime_policy(_args(tmp_path, tmp_path / "home"))
    rendered = runtime._effective_config_template(
        {}, [], policy, {"memory": {"backend": "off"}, "future_global": 1}
    )
    assert policy["future_field"] == "untouched"
    assert "future_field" not in rendered
    assert rendered["memory"]["backend"] == "off"
    assert rendered["mcp"]["enableProjectConfig"] is False

def test_project_policy_overrides_unsafe_global_preference(
    tmp_path: Path,
) -> None:
    rendered = runtime._effective_config_template(
        {}, [],
        {"memory_backend": "off", "enable_project_mcp": False},
        {"memory": {"backend": "sqlite"}},
    )
    assert rendered["memory"]["backend"] == "off"

def test_external_import_requires_approved_profile_and_digest() -> None:
    project = type(
        "Project",
        (),
        {
            "external_imports": (
                {
                    "name": "review-skill",
                    "source": "user-home",
                    "digest": "sha256:asset",
                    "approved": True,
                    "profiles": ("assembly-helper",),
                },
            )
        },
    )()
    profile = type("Profile", (), {"name": "assembly-helper"})()
    inventory = {
        "capability_entries": [
            {
                "digest": "sha256:asset",
                "capabilities": {"skills": ["review-skill"]},
            }
        ],
        "instruction_entries": [],
    }
    assert profile_cli._validate_external_imports(
        project, profile, inventory
    ) == ("review-skill",)

    general = type("Profile", (), {"name": "general"})()
    assert profile_cli._validate_external_imports(
        project, general, inventory
    ) == ()

@pytest.mark.parametrize(
    ("approved", "digest", "message"),
    (
        (False, "sha256:asset", "not approved"),
        (True, "sha256:other", "does not match"),
    ),
)
def test_external_import_rejects_unapproved_or_mismatched_assets(
    approved: bool, digest: str, message: str
) -> None:
    project = type(
        "Project",
        (),
        {
            "external_imports": (
                {
                    "name": "review-skill",
                    "source": "user-home",
                    "digest": digest,
                    "approved": approved,
                    "profiles": ("assembly-helper",),
                },
            )
        },
    )()
    profile = type("Profile", (), {"name": "assembly-helper"})()
    inventory = {
        "capability_entries": [
            {
                "digest": "sha256:asset",
                "capabilities": {"skills": ["review-skill"]},
            }
        ],
        "instruction_entries": [],
    }
    with pytest.raises(profile_cli.ProfileError, match=message):
        profile_cli._validate_external_imports(project, profile, inventory)

def test_generation_rejects_runtime_policy_metadata_drift(tmp_path: Path) -> None:
    generation = tmp_path / "generation"
    generation.mkdir()
    (generation / "config.yml").write_text("memory: {}\n", encoding="utf-8")
    policy = {"effective": {"memory_backend": "off"}}
    manifest = {
        "version": 2,
        "profile": "general",
        "portable_tree_hash": "sha256:portable",
        "effective_render_hash": "sha256:render",
        "source_context": {"profile": "general"},
        "source_digest": "sha256:source",
        "runtime_policy": {"effective": {"memory_backend": "sqlite"}},
        "content_digest": runtime._tree_digest(
            generation, exclude={".cap-generation.json"}
        ),
    }
    (generation / ".cap-generation.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    with pytest.raises(runtime._MigrationError, match="metadata drifted"):
        runtime._verify_profile_generation(
            generation,
            "general",
            "sha256:portable",
            "sha256:render",
            {"profile": "general"},
            "sha256:source",
            policy,
        )
