from __future__ import annotations

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import subprocess
import threading
import tomllib
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

PROFILE_MODULE = Path(__file__).resolve().parents[1] / "profile.py"
PROFILE_SPEC = importlib.util.spec_from_file_location(
    "agent_control_profile", PROFILE_MODULE
)
assert PROFILE_SPEC is not None and PROFILE_SPEC.loader is not None
profile = importlib.util.module_from_spec(PROFILE_SPEC)
sys.modules[PROFILE_SPEC.name] = profile
PROFILE_SPEC.loader.exec_module(profile)


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "multi-profile"


class ProfileTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.project = self.root / "project"
        shutil.copytree(FIXTURE, self.project)
        self.home = self.root / "home"
        self.home.mkdir()
        self.home_patch = mock.patch.dict(os.environ, {"HOME": str(self.home)})
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)

    def output_directory(self, name: str) -> Path:
        """Create and return one empty render output directory."""

        output = self.root / name
        output.mkdir()
        return output


class MaterializationTests(ProfileTestCase):
    def test_renders_both_profiles_for_all_clients_without_cross_profile_capabilities(
        self,
    ) -> None:
        for profile_name in ("review", "implementation"):
            other = "implementation" if profile_name == "review" else "review"
            for client in profile.CLIENTS:
                with self.subTest(profile=profile_name, client=client):
                    output = self.output_directory(f"{profile_name}-{client}")
                    tree_hash = profile.materialize_profile(
                        self.project, client, profile_name, output
                    )
                    self.assertTrue(tree_hash.startswith("sha256:"))
                    rendered = "\n".join(
                        path.relative_to(output).as_posix()
                        + "\n"
                        + path.read_text(encoding="utf-8")
                        for path in sorted(output.rglob("*"))
                        if path.is_file()
                    )
                    self.assertIn(f"{profile_name}-skill-sentinel", rendered)
                    self.assertIn(f"{profile_name}-mcp-sentinel", rendered)
                    self.assertIn(f"{profile_name}-hook-{client}-sentinel", rendered)
                    self.assertIn(f"{profile_name}-plugin-{client}-sentinel", rendered)
                    self.assertNotIn(f"{other}-skill", rendered)
                    self.assertNotIn(f"{other}-mcp", rendered)
                    self.assertNotIn(f"{other}-hook", rendered)
                    self.assertNotIn(f"{other}-plugin", rendered)

    def test_renders_native_mcp_shapes_and_fixed_environment_values(self) -> None:
        codex = self.output_directory("codex")
        qoder = self.output_directory("qoder")
        omp = self.output_directory("omp")
        profile.materialize_profile(self.project, "codex", "review", codex)
        profile.materialize_profile(self.project, "qoder", "review", qoder)
        profile.materialize_profile(self.project, "omp", "review", omp)

        codex_config = tomllib.loads(
            (codex / "config.toml").read_text(encoding="utf-8")
        )
        codex_server = codex_config["mcp_servers"]["review-mcp"]
        self.assertTrue(codex_server["required"])
        self.assertEqual(codex_server["env"], {"CAPRUN_SENTINEL": "review-mcp"})

        qoder_config = json.loads((qoder / "mcp.json").read_text(encoding="utf-8"))
        self.assertEqual(
            qoder_config["mcpServers"]["review-mcp"]["env"],
            {"CAPRUN_SENTINEL": "review-mcp"},
        )
        omp_config = json.loads((omp / "mcp.json").read_text(encoding="utf-8"))

        self.assertEqual(omp_config["mcpServers"]["review-mcp"]["type"], "stdio")
        self.assertEqual(
            omp_config["mcpServers"]["review-mcp"]["env"],
            {"CAPRUN_SENTINEL": "review-mcp"},
        )
        for prompt_file in (
            codex / "AGENTS.md",
            qoder / "system-prompt.md",
            omp / "system-prompt.md",
        ):
            prompt = prompt_file.read_text(encoding="utf-8")
            self.assertIn("Review session profile", prompt)
            self.assertNotIn("Multi-profile fixture baseline", prompt)

    def test_case_alias_cannot_place_outputs_inside_project(self) -> None:
        alias_text = str(self.project).replace("/private/var/", "/private/VAR/", 1)
        alias_root = Path(alias_text)
        if alias_root == self.project or not alias_root.exists():
            self.skipTest("test requires a case-insensitive /private/var filesystem")
        if not os.path.samefile(alias_root, self.project):
            self.skipTest("test requires a case-insensitive /private/var filesystem")

        output = self.project / "case-output"
        output.mkdir()
        output_alias = alias_root / output.name
        with self.assertRaisesRegex(profile.ProfileError, "outside the project root"):
            profile.materialize_profile(self.project, "codex", "review", output_alias)

        state = self.project / "case-state"
        state.mkdir()
        state_alias = alias_root / state.name
        with self.assertRaisesRegex(profile.ProfileError, "outside the project root"):
            profile.probe_profile(self.project, "codex", "review", state_alias)

        receipt_parent = self.project / "case-receipt"
        receipt_parent.mkdir()
        runner = mock.Mock()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        with self.assertRaisesRegex(profile.ProfileError, "outside the project root"):
            profile.run_client(
                self.project,
                "codex",
                "review",
                receipt_path=alias_root / receipt_parent.name / "receipt.json",
                runner=runner,
            )
        runner.assert_not_called()

    def test_concurrent_profiles_render_to_independent_trees(self) -> None:
        review = self.output_directory("concurrent-review")
        implementation = self.output_directory("concurrent-implementation")
        with ThreadPoolExecutor(max_workers=2) as executor:
            review_future = executor.submit(
                profile.materialize_profile, self.project, "qoder", "review", review
            )
            implementation_future = executor.submit(
                profile.materialize_profile,
                self.project,
                "qoder",
                "implementation",
                implementation,
            )
        self.assertNotEqual(review_future.result(), implementation_future.result())
        self.assertTrue((review / "skills" / "review-skill" / "SKILL.md").is_file())
        self.assertFalse((review / "skills" / "implementation-skill").exists())
        self.assertTrue(
            (implementation / "skills" / "implementation-skill" / "SKILL.md").is_file()
        )
        self.assertFalse((implementation / "skills" / "review-skill").exists())

    def test_render_rejects_symlink_ancestor(self) -> None:
        target = self.root / "ancestor-target"
        output = target / "output"
        output.mkdir(parents=True)
        linked_ancestor = self.root / "linked-ancestor"
        linked_ancestor.symlink_to(target, target_is_directory=True)
        with self.assertRaisesRegex(profile.ProfileError, "non-symlink directory"):
            profile.materialize_profile(
                self.project, "codex", "review", linked_ancestor / "output"
            )

    def test_render_requires_an_existing_empty_non_symlink_directory(self) -> None:
        missing = self.root / "missing"
        with self.assertRaisesRegex(profile.ProfileError, "existing non-symlink"):
            profile.materialize_profile(self.project, "codex", "review", missing)
        occupied = self.output_directory("occupied")
        (occupied / "keep.txt").write_text("occupied", encoding="utf-8")
        with self.assertRaisesRegex(profile.ProfileError, "must be empty"):
            profile.materialize_profile(self.project, "codex", "review", occupied)

    def test_render_rejects_output_inside_project(self) -> None:
        output = self.project / "runtime"
        output.mkdir()
        with self.assertRaisesRegex(profile.ProfileError, "outside the project root"):
            profile.materialize_profile(self.project, "codex", "review", output)
        self.assertEqual(list(output.iterdir()), [])

    def test_render_rejects_global_native_root(self) -> None:
        output = self.home / ".codex"
        output.mkdir()
        with self.assertRaisesRegex(
            profile.ProfileError, "outside global capability roots"
        ):
            profile.materialize_profile(self.project, "codex", "review", output)
        self.assertEqual(list(output.iterdir()), [])

    def test_render_directory_swap_cannot_redirect_materialized_files(self) -> None:
        output = self.output_directory("stable-output")
        moved = self.root / "moved-output"
        redirect = self.root / "redirect-output"
        redirect.mkdir()
        original_mkdir = os.mkdir
        swapped = False

        def swapping_mkdir(
            path: str | bytes,
            mode: int = 0o777,
            *,
            dir_fd: int | None = None,
        ) -> None:
            nonlocal swapped
            if dir_fd is not None and not swapped:
                output.rename(moved)
                output.symlink_to(redirect, target_is_directory=True)
                swapped = True
            original_mkdir(path, mode, dir_fd=dir_fd)

        with mock.patch.object(profile.os, "mkdir", side_effect=swapping_mkdir):
            with self.assertRaisesRegex(
                profile.ProfileError, "stable directory changed"
            ):
                profile.materialize_profile(self.project, "codex", "review", output)
        self.assertEqual(list(redirect.iterdir()), [])


class GateAndLockTests(ProfileTestCase):
    def test_global_capability_pollution_is_rejected(self) -> None:
        global_configs = (
            (".agents/skills/global-skill/SKILL.md", "pollution"),
            (".claude.json", '{"mcpServers": {}}'),
            (".codex/config.toml", 'developer_instructions = "pollution"'),
            (".codex/hooks.json", "{}"),
            (".config/opencode/opencode.json", '{"model": "safe", "mcp": {}}'),
            (".gemini/settings.json", '{"mcpServers": {}}'),
            (".omp/agent/config.yml", "skills:\n  includeSkills: []\n"),
            (".omp/agent/mcp.json", "{}"),
            (".qoder/settings.json", '{"enabledPlugins": {"pollution": true}}'),
        )
        for index, (relative, content) in enumerate(global_configs):
            with self.subTest(relative=relative):
                home = self.root / f"polluted-home-{index}"
                path = home / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                with mock.patch.dict(os.environ, {"HOME": str(home)}):
                    with self.assertRaisesRegex(
                        profile.ProfileError, "global capability pollution"
                    ):
                        profile.verify_project(self.project)

    def test_runtime_only_global_configs_are_allowed(self) -> None:
        configs = {
            ".claude.json": '{"theme": "dark"}',
            ".codex/config.toml": 'model = "gpt-5.6"\nsandbox_mode = "read-only"\n',
            ".config/opencode/opencode.json": '{"model": "openai/gpt-5.6"}',
            ".gemini/settings.json": '{"theme": "dark"}',
            ".omp/agent/config.yml": "model: openai/gpt-5.6\n",
            ".pi/agent/config.yml": "model: openai/gpt-5.6\n",
            ".qoder/settings.json": '{"theme": "dark"}',
        }
        for relative, content in configs.items():
            path = self.home / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        profile.verify_project(self.project)

    def test_project_native_bypasses_are_rejected(self) -> None:
        bypasses = (
            ".mcp.json",
            "mcp.json",
            ".agents/skills/bypass/SKILL.md",
            ".claude/.mcp.json",
            ".claude/mcp.json",
            ".codex/config.toml",
            ".cursor/mcp.json",
            ".gemini/settings.json",
            ".qoder/settings.json",
            ".omp/mcp.json",
            ".vscode/mcp.json",
            ".windsurf/mcp_config.json",
            "opencode.json",
            "nested/AGENTS.md",
            "nested/AGENTS.override.md",
            "nested/CLAUDE.md",
            "nested/QODER.md",
        )
        for index, relative in enumerate(bypasses):
            with self.subTest(relative=relative):
                project = self.root / f"bypass-{index}"
                shutil.copytree(FIXTURE, project)
                path = project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("bypass", encoding="utf-8")
                with self.assertRaisesRegex(
                    profile.ProfileError, "project capability bypass"
                ):
                    profile.verify_project(project)

    def test_project_native_bypasses_are_case_insensitive(self) -> None:
        bypasses = (
            ".CoDeX/config.toml",
            ".QoDeR/settings.json",
            "nested/agents.MD",
            "MCP.JSON",
        )
        for index, relative in enumerate(bypasses):
            with self.subTest(relative=relative):
                project = self.root / f"case-bypass-{index}"
                shutil.copytree(FIXTURE, project)
                path = project / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("bypass", encoding="utf-8")
                with self.assertRaisesRegex(
                    profile.ProfileError, "project capability bypass"
                ):
                    profile.verify_project(project)

    def test_symlinked_provider_directory_is_rejected(self) -> None:
        external = self.root / "external-claude"
        external.mkdir()
        (external / "mcp.json").write_text('{"mcpServers": {}}', encoding="utf-8")
        (self.project / ".claude").symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(profile.ProfileError, "project capability bypass"):
            profile.verify_project(self.project)

    def test_lock_detects_input_and_renderer_drift(self) -> None:
        mutations = (
            ("AGENTS.md", "\nchanged baseline\n"),
            (".cap/profiles/review.toml", "\n# changed profile\n"),
            (".cap/prompts/review.md", "\nchanged prompt\n"),
            (
                ".cap/capabilities/skills/review-skill/SKILL.md",
                "\nchanged capability\n",
            ),
            (".cap/manifest.toml", "\n# changed manifest\n"),
        )
        for index, (relative, addition) in enumerate(mutations):
            with self.subTest(relative=relative):
                project = self.root / f"drift-{index}"
                shutil.copytree(FIXTURE, project)
                with (project / relative).open("a", encoding="utf-8") as stream:
                    stream.write(addition)
                with self.assertRaisesRegex(profile.ProfileError, "lock drift"):
                    profile.verify_project(project)
        with mock.patch.object(profile, "RENDERER_VERSION", "profile-renderer-v2"):
            with self.assertRaisesRegex(profile.ProfileError, "lock drift"):
                profile.verify_project(self.project)

    def test_list_and_explain_reject_stale_lock(self) -> None:
        with (self.project / ".cap" / "prompts" / "review.md").open(
            "a", encoding="utf-8"
        ) as stream:
            stream.write("\ndrift\n")
        for operation in (
            lambda: profile.list_profiles(self.project),
            lambda: profile.explain_profile(self.project, "review"),
        ):
            with self.subTest(operation=operation):
                with self.assertRaisesRegex(profile.ProfileError, "lock drift"):
                    operation()

    def test_lock_file_matches_current_fixture(self) -> None:
        current = profile.verify_project(self.project)
        lock = json.loads(
            (self.project / ".cap" / "lock.json").read_text(encoding="utf-8")
        )
        self.assertEqual(current, lock)

    def test_strict_parsing_rejects_unknown_duplicate_and_non_finite_data(self) -> None:
        manifest = self.project / ".cap" / "manifest.toml"
        manifest.write_text(
            manifest.read_text(encoding="utf-8").replace(
                "version = 1\n", 'version = 1\nunknown = "value"\n', 1
            ),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(profile.ProfileError, "keys mismatch"):
            profile.load_project(self.project)

        shutil.rmtree(self.project)
        shutil.copytree(FIXTURE, self.project)
        mcp = self.project / ".cap" / "capabilities" / "mcp" / "review-mcp.json"
        mcp.write_text(
            '{"version":1,"name":"review-mcp","name":"duplicate",'
            '"command":"python3","args":[],"env":{}}',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(profile.ProfileError, "duplicate JSON key"):
            profile.load_project(self.project)

        mcp.write_text(
            '{"version":1,"name":"review-mcp","command":"python3",'
            '"args":[],"env":{},"number":NaN}',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(profile.ProfileError, "non-finite JSON"):
            profile.load_project(self.project)

    def test_path_escape_and_overlay_root_escape_are_rejected(self) -> None:
        manifest = self.project / ".cap" / "manifest.toml"
        manifest.write_text(
            'version = 1\n\n[profiles]\nreview = "../outside.toml"\n',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(
            profile.ProfileError, "normalized POSIX relative path"
        ):
            profile.load_project(self.project)

        shutil.rmtree(self.project)
        shutil.copytree(FIXTURE, self.project)
        conflict = (
            self.project
            / ".cap"
            / "capabilities"
            / "hooks"
            / "review-hook"
            / "targets"
            / "codex"
            / "config.toml"
        )
        conflict.write_text("opaque conflict", encoding="utf-8")
        with self.assertRaisesRegex(profile.ProfileError, "must contain only hooks/"):
            profile.create_lock(self.project)

    def test_hook_and_plugin_targets_cannot_cross_owned_namespaces(self) -> None:
        escapes = (
            ("hooks", "review-hook", "skills/review-skill/SKILL.md"),
            ("hooks", "review-hook", "plugins/cross-kind.sentinel"),
            ("hooks", "review-hook", "config.toml"),
            ("hooks", "review-hook", "AGENTS.md"),
            ("plugins", "review-plugin", "hooks/cross-kind.sentinel"),
        )
        for index, (kind, name, relative) in enumerate(escapes):
            with self.subTest(kind=kind, relative=relative):
                project = self.root / f"overlay-escape-{index}"
                shutil.copytree(FIXTURE, project)
                payload = (
                    project
                    / ".cap"
                    / "capabilities"
                    / kind
                    / name
                    / "targets"
                    / "codex"
                    / relative
                )
                payload.parent.mkdir(parents=True, exist_ok=True)
                payload.write_text("cross-owned payload", encoding="utf-8")
                with self.assertRaisesRegex(
                    profile.ProfileError,
                    rf"must contain only {kind}/",
                ):
                    profile.load_project(project)

    def test_missing_client_overlay_target_is_rejected(self) -> None:
        target = (
            self.project
            / ".cap"
            / "capabilities"
            / "hooks"
            / "review-hook"
            / "targets"
            / "omp"
        )
        shutil.rmtree(target)
        with self.assertRaisesRegex(profile.ProfileError, "lacks required omp target"):
            profile.create_lock(self.project)


class LaunchTests(ProfileTestCase):
    def setUp(self) -> None:
        super().setUp()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)

    def test_run_builds_each_native_command_and_environment_then_cleans_root(
        self,
    ) -> None:
        expectations = {
            "codex": ("codex", "CODEX_HOME", ()),
            "qoder": (
                "qoder",
                "QODER_CONFIG_DIR",
                (
                    "--config-dir",
                    "--strict-mcp-config",
                    "--mcp-config",
                    "--append-system-prompt",
                ),
            ),
            "omp": (
                "omp",
                "PI_CODING_AGENT_DIR",
                (
                    "--config",
                    "--append-system-prompt",
                    "--skills",
                    "--no-extensions",
                    "--no-rules",
                ),
            ),
        }
        runtime_roots: list[Path] = []
        for client, (
            executable,
            environment_name,
            required_flags,
        ) in expectations.items():
            receipt = self.root / f"{client}-receipt.json"

            def fake_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
                runtime_root = Path(str(kwargs["env"][environment_name]))  # type: ignore[index]
                runtime_roots.append(runtime_root)
                self.assertTrue(runtime_root.is_dir())
                self.assertEqual(command[0], executable)
                for flag in required_flags:
                    self.assertIn(flag, command)
                if client == "omp":
                    safe_omp_environment = {
                        "OMP_PROFILE": "default",
                        "PI_CODING_AGENT_DIR": str(runtime_root),
                        "PI_CONFIG_DIR": str(runtime_root),
                        "PI_CONFIG_FILES": str(runtime_root / "config.yml"),
                        "PI_PROFILE": "default",
                    }
                    for name, value in safe_omp_environment.items():
                        self.assertEqual(kwargs["env"][name], value)  # type: ignore[index]
                    self.assertNotIn("CODEX_HOME", kwargs["env"])  # type: ignore[operator]
                    self.assertNotIn("QODER_CONFIG_DIR", kwargs["env"])  # type: ignore[operator]
                else:
                    for ambient_name in profile.AMBIENT_CONFIG_ENV:
                        if ambient_name != environment_name:
                            self.assertNotIn(ambient_name, kwargs["env"])  # type: ignore[operator]
                if client in {"qoder", "omp"}:
                    prompt_index = command.index("--append-system-prompt") + 1
                    self.assertIn("Review session profile", command[prompt_index])
                    self.assertFalse(command[prompt_index].endswith("system-prompt.md"))
                if client == "omp":
                    skill_index = command.index("--skills") + 1
                    self.assertEqual(command[skill_index], "review-skill")
                self.assertEqual(command[-2:], ["--token", "super-secret"])
                if client == "codex":
                    self.assertTrue((runtime_root / "config.toml").is_file())
                elif client == "qoder":
                    self.assertTrue((runtime_root / "settings.json").is_file())
                else:
                    self.assertTrue((runtime_root / "config.yml").is_file())
                return SimpleNamespace(returncode=0)

            result = profile.run_client(
                self.project,
                client,
                "review",
                ("--token", "super-secret"),
                receipt_path=receipt,
                runner=fake_runner,
            )
            self.assertEqual(result, 0)
            payload = receipt.read_text(encoding="utf-8")
            self.assertNotIn("super-secret", payload)
            self.assertNotIn(str(runtime_roots[-1]), payload)
            self.assertTrue(json.loads(payload)["temporary_root_removed"])
            self.assertEqual(
                json.loads(payload)["inventory"],
                {
                    "hooks": ["review-hook"],
                    "mcps": ["review-mcp"],
                    "plugins": ["review-plugin"],
                    "skills": ["review-skill"],
                },
            )
            self.assertFalse(runtime_roots[-1].exists())

    def test_launch_metadata_cannot_be_swapped_through_runtime_path(self) -> None:
        original_build_launch = profile.build_launch

        def swapping_build_launch(
            client: str,
            runtime_root: Path | str,
            rendered_tree: dict[str, profile.RenderedFile],
            forwarded_args: tuple[str, ...] = (),
        ) -> profile.LaunchSpec:
            root = Path(runtime_root)
            moved = root.with_name(root.name + "-held")
            root.rename(moved)
            root.mkdir()
            (root / "system-prompt.md").write_text("malicious prompt", encoding="utf-8")
            try:
                return original_build_launch(
                    client,
                    runtime_root,
                    rendered_tree,
                    forwarded_args,
                )
            finally:
                shutil.rmtree(root)
                moved.rename(root)

        def fake_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
            prompt_index = command.index("--append-system-prompt") + 1
            self.assertIn("Review session profile", command[prompt_index])
            self.assertNotIn("malicious", command[prompt_index])
            return SimpleNamespace(returncode=0)

        with mock.patch.object(
            profile, "build_launch", side_effect=swapping_build_launch
        ):
            for client in ("qoder", "omp"):
                with self.subTest(client=client):
                    self.assertEqual(
                        profile.run_client(
                            self.project,
                            client,
                            "review",
                            receipt_path=self.root / f"{client}-swap-read-receipt.json",
                            runner=fake_runner,
                        ),
                        0,
                    )

    def test_omp_single_line_prompt_is_forced_to_literal_text(self) -> None:
        prompt_path = self.project / ".cap" / "prompts" / "review.md"
        prompt_path.write_text("collision.txt", encoding="utf-8")
        (self.project / "collision.txt").write_text(
            "malicious unlocked prompt", encoding="utf-8"
        )
        profile.create_lock(self.project)

        def fake_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
            prompt_index = command.index("--append-system-prompt") + 1
            self.assertEqual(command[prompt_index], "collision.txt\n")
            self.assertNotIn("malicious", command[prompt_index])
            return SimpleNamespace(returncode=0)

        self.assertEqual(
            profile.run_client(
                self.project,
                "omp",
                "review",
                receipt_path=self.root / "omp-literal-prompt-receipt.json",
                runner=fake_runner,
            ),
            0,
        )

    def test_missing_or_unknown_profile_never_invokes_client(self) -> None:
        runner = mock.Mock()
        with self.assertRaises(SystemExit) as raised:
            profile.main(
                [
                    "--project",
                    str(self.project),
                    "run",
                    "--client",
                    "codex",
                ]
            )
        self.assertEqual(raised.exception.code, 2)
        with self.assertRaisesRegex(profile.ProfileError, "unknown profile"):
            profile.run_client(self.project, "codex", "missing", runner=runner)
        runner.assert_not_called()

    def test_gate_and_lock_failures_never_invoke_client(self) -> None:
        runner = mock.Mock()
        polluted = self.home / ".agents" / "skills"
        polluted.mkdir(parents=True)
        with self.assertRaisesRegex(
            profile.ProfileError, "global capability pollution"
        ):
            profile.run_client(self.project, "codex", "review", runner=runner)
        runner.assert_not_called()

        shutil.rmtree(self.home / ".agents")
        with (self.project / "AGENTS.md").open("a", encoding="utf-8") as stream:
            stream.write("drift")
        with self.assertRaisesRegex(profile.ProfileError, "lock drift"):
            profile.run_client(self.project, "codex", "review", runner=runner)
        runner.assert_not_called()

    def test_forwarded_capability_overrides_never_invoke_client(self) -> None:
        runner = mock.Mock()
        overrides = (
            ("codex", ("--profile", "unsafe")),
            ("codex", ("-C", "/tmp/unsafe")),
            ("codex", ("-C/tmp/unsafe",)),
            ("codex", ("-p", "unsafe")),
            ("codex", ("-punsafe",)),
            ("codex", ("--cd=/tmp/unsafe",)),
            ("codex", ("-cmodel=unsafe",)),
            ("codex", ("-c=model=unsafe",)),
            ("qoder", ("--mcp-config=/tmp/unsafe.json",)),
            ("qoder", ("-w", "/tmp/unsafe")),
            ("qoder", ("--cwd=/tmp/unsafe",)),
            ("qoder", ("--worktree", "unsafe")),
            ("qoder", ("--worktree=unsafe",)),
            ("qoder", ("-wunsafe",)),
            ("omp", ("--config", "/tmp/unsafe.yml")),
            ("omp", ("--extension=/tmp/unsafe.ts",)),
            ("omp", ("-e/tmp/unsafe.ts",)),
            ("omp", ("--trusted-extension=/tmp/unsafe.ts",)),
            ("omp", ("--trusted-extension", "/tmp/unsafe.ts")),
        )
        for client, arguments in overrides:
            with self.subTest(client=client, arguments=arguments):
                with self.assertRaisesRegex(profile.ProfileError, "may override"):
                    profile.run_client(
                        self.project,
                        client,
                        "review",
                        arguments,
                        runner=runner,
                    )
        runner.assert_not_called()

    def test_nested_project_root_never_invokes_client(self) -> None:
        parent = self.root / "parent-project"
        subprocess.run(["git", "init", "-q", str(parent)], check=True)
        nested = parent / "nested"
        shutil.copytree(FIXTURE, nested)
        runner = mock.Mock()
        with self.assertRaisesRegex(
            profile.ProfileError, "must equal the Git worktree root"
        ):
            profile.run_client(nested, "codex", "review", runner=runner)
        runner.assert_not_called()

    def test_post_verification_render_drift_never_invokes_client(self) -> None:
        runner = mock.Mock()
        original_verify = profile._verify_lock

        def verify_then_mutate(project: profile.Project, desired: object) -> None:
            original_verify(project, desired)  # type: ignore[arg-type]
            skill = (
                project.root
                / ".cap"
                / "capabilities"
                / "skills"
                / "review-skill"
                / "SKILL.md"
            )
            skill.write_text(
                skill.read_text(encoding="utf-8") + "\ndrift\n", encoding="utf-8"
            )

        with mock.patch.object(profile, "_verify_lock", side_effect=verify_then_mutate):
            with self.assertRaisesRegex(
                profile.ProfileError, "drifted after lock verification"
            ):
                profile.run_client(self.project, "codex", "review", runner=runner)
        runner.assert_not_called()

    def test_final_input_and_project_bypass_gates_never_invoke_client(self) -> None:
        mutations = (
            (
                "locked inputs drifted",
                lambda project: (project / "AGENTS.md").write_text(
                    "changed after launch preparation\n",
                    encoding="utf-8",
                ),
            ),
            (
                "project capability bypass",
                lambda project: (
                    (project / ".codex").mkdir(),
                    (project / ".codex" / "AGENTS.md").write_text(
                        "late bypass\n",
                        encoding="utf-8",
                    ),
                ),
            ),
        )
        original_build = profile.build_launch
        for index, (message, mutate) in enumerate(mutations):
            with self.subTest(message=message):
                project = self.root / f"final-gate-{index}"
                shutil.copytree(FIXTURE, project)
                subprocess.run(["git", "init", "-q", str(project)], check=True)
                receipt = self.root / f"final-gate-{index}.json"
                runner = mock.Mock()

                def build_then_mutate(
                    *args: object, **kwargs: object
                ) -> profile.LaunchSpec:
                    spec = original_build(*args, **kwargs)  # type: ignore[arg-type]
                    mutate(project)
                    return spec

                with mock.patch.object(
                    profile,
                    "build_launch",
                    side_effect=build_then_mutate,
                ):
                    with self.assertRaisesRegex(profile.ProfileError, message):
                        profile.run_client(
                            project,
                            "codex",
                            "review",
                            receipt_path=receipt,
                            runner=runner,
                        )
                runner.assert_not_called()
                self.assertFalse(receipt.exists())

    def test_ambient_qoder_working_directory_cannot_override_project_cwd(self) -> None:
        def fake_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
            self.assertEqual(kwargs["cwd"], str(self.project))
            self.assertNotIn("QODER_WORKING_DIR", kwargs["env"])  # type: ignore[operator]
            return SimpleNamespace(returncode=0)

        with mock.patch.dict(
            os.environ,
            {"QODER_WORKING_DIR": "/tmp/unsafe"},
        ):
            self.assertEqual(
                profile.run_client(
                    self.project,
                    "qoder",
                    "review",
                    receipt_path=self.root / "qoder-cwd-receipt.json",
                    runner=fake_runner,
                ),
                0,
            )

    def test_project_dotenv_cannot_override_omp_isolation(self) -> None:
        (self.project / ".env").write_text(
            "OMP_PROFILE=unsafe\nPI_PROFILE=unsafe\nPI_CONFIG_FILES=/tmp/unsafe.yml\n",
            encoding="utf-8",
        )

        def fake_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
            environment = kwargs["env"]
            self.assertEqual(environment["OMP_PROFILE"], "default")  # type: ignore[index]
            self.assertEqual(environment["PI_PROFILE"], "default")  # type: ignore[index]
            self.assertEqual(  # type: ignore[index]
                environment["PI_CONFIG_FILES"],
                str(Path(environment["PI_CONFIG_DIR"]) / "config.yml"),
            )
            self.assertEqual(
                environment["PI_CONFIG_DIR"],  # type: ignore[index]
                environment["PI_CODING_AGENT_DIR"],  # type: ignore[index]
            )
            return SimpleNamespace(returncode=0)

        self.assertEqual(
            profile.run_client(
                self.project,
                "omp",
                "review",
                receipt_path=self.root / "dotenv-receipt.json",
                runner=fake_runner,
            ),
            0,
        )

    def test_symlink_receipt_parent_never_invokes_client(self) -> None:
        target = self.root / "receipts"
        nested_target = target / "nested"
        nested_target.mkdir(parents=True)
        linked_parent = self.root / "receipt-link"
        linked_parent.symlink_to(target, target_is_directory=True)
        runner = mock.Mock()
        with self.assertRaisesRegex(profile.ProfileError, "non-symlink directory"):
            profile.run_client(
                self.project,
                "codex",
                "review",
                receipt_path=linked_parent / "nested" / "receipt.json",
                runner=runner,
            )
        runner.assert_not_called()
        self.assertEqual(list(nested_target.iterdir()), [])

    def test_symlink_receipt_target_never_invokes_client(self) -> None:
        sink = self.root / "existing-receipt-sink.txt"
        sink.write_text("unchanged", encoding="utf-8")
        receipt = self.root / "receipt-link.json"
        receipt.symlink_to(sink)
        runner = mock.Mock()
        with self.assertRaisesRegex(profile.ProfileError, "already exists"):
            profile.run_client(
                self.project,
                "codex",
                "review",
                receipt_path=receipt,
                runner=runner,
            )
        runner.assert_not_called()
        self.assertEqual(sink.read_text(encoding="utf-8"), "unchanged")

    def test_concurrent_launches_cannot_clobber_one_receipt(self) -> None:
        receipt = self.root / "shared-receipt.json"
        started = threading.Event()
        release = threading.Event()
        runner_calls: list[int] = []

        def slow_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
            runner_calls.append(1)
            started.set()
            if not release.wait(5):
                raise AssertionError("test did not release the reserved receipt")
            return SimpleNamespace(returncode=0)

        with ThreadPoolExecutor(max_workers=2) as executor:
            winner = executor.submit(
                profile.run_client,
                self.project,
                "codex",
                "review",
                (),
                receipt_path=receipt,
                runner=slow_runner,
            )
            self.assertTrue(started.wait(5))
            losing_runner = mock.Mock()
            try:
                with self.assertRaisesRegex(profile.ProfileError, "already exists"):
                    profile.run_client(
                        self.project,
                        "codex",
                        "review",
                        receipt_path=receipt,
                        runner=losing_runner,
                    )
            finally:
                release.set()
            self.assertEqual(winner.result(), 0)
        losing_runner.assert_not_called()
        self.assertEqual(runner_calls, [1])
        self.assertEqual(
            json.loads(receipt.read_text(encoding="utf-8"))["profile"], "review"
        )

    def test_reserved_receipt_target_cannot_be_redirected(self) -> None:
        receipt = self.root / "redirected-receipt.json"
        sink = self.root / "receipt-sink.txt"
        sink.write_text("unchanged", encoding="utf-8")

        def replacing_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
            receipt.unlink()
            receipt.symlink_to(sink)
            return SimpleNamespace(returncode=0)

        with self.assertRaisesRegex(profile.ProfileError, "target changed"):
            profile.run_client(
                self.project,
                "codex",
                "review",
                receipt_path=receipt,
                runner=replacing_runner,
            )
        self.assertEqual(sink.read_text(encoding="utf-8"), "unchanged")
        self.assertTrue(receipt.is_symlink())

    def test_reserved_receipt_parent_cannot_be_redirected(self) -> None:
        parent = self.root / "stable-receipt-parent"
        parent.mkdir()
        receipt = parent / "receipt.json"
        moved_parent = self.root / "moved-receipt-parent"
        redirect = self.root / "redirect-target"
        redirect.mkdir()

        def replacing_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
            parent.rename(moved_parent)
            parent.symlink_to(redirect, target_is_directory=True)
            return SimpleNamespace(returncode=0)

        with self.assertRaisesRegex(profile.ProfileError, "parent changed"):
            profile.run_client(
                self.project,
                "codex",
                "review",
                receipt_path=receipt,
                runner=replacing_runner,
            )
        self.assertFalse((redirect / "receipt.json").exists())
        self.assertFalse((moved_parent / "receipt.json").exists())

    def test_reserved_receipt_hard_link_alias_is_rejected(self) -> None:
        receipt = self.root / "hard-link-receipt.json"
        alias = self.root / "receipt-alias.json"

        def linking_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
            os.link(receipt, alias)
            return SimpleNamespace(returncode=0)

        with self.assertRaisesRegex(profile.ProfileError, "hard-link alias"):
            profile.run_client(
                self.project,
                "codex",
                "review",
                receipt_path=receipt,
                runner=linking_runner,
            )
        self.assertFalse(receipt.exists())
        self.assertEqual(alias.read_bytes(), b"")

    def test_runner_exception_removes_reserved_receipt(self) -> None:
        receipt = self.root / "failed-receipt.json"
        runner = mock.Mock(side_effect=RuntimeError("runner failed"))
        with self.assertRaisesRegex(RuntimeError, "runner failed"):
            profile.run_client(
                self.project,
                "codex",
                "review",
                receipt_path=receipt,
                runner=runner,
            )
        self.assertFalse(os.path.lexists(receipt))


class ObserverContractTests(ProfileTestCase):
    def setUp(self) -> None:
        super().setUp()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)

    def state_directory(self, name: str) -> Path:
        """Create one explicit immutable observation directory."""

        state = self.root / name
        state.mkdir()
        return state

    def test_probe_uses_locked_render_tree_and_keeps_unknown_distinct(self) -> None:
        state = self.state_directory("probe-state")
        result = profile.probe_profile(self.project, "omp", "review", state)
        self.assertEqual(result["observed"]["skills"], ["review-skill"])
        self.assertEqual(result["observed"]["mcps"], ["review-mcp"])
        self.assertIsNone(result["observed"]["context"])
        self.assertIsNone(result["observed"]["hooks"])
        self.assertIsNone(result["observed"]["plugins"])
        self.assertEqual(result["staged"]["hooks"], ["review-hook"])
        self.assertEqual(result["staged"]["plugins"], ["review-plugin"])
        self.assertTrue((state / "declared.json").is_file())
        self.assertTrue((state / "probed.json").is_file())
        self.assertFalse((state / "effective.json").exists())

    def test_codex_probe_accepts_a_profile_with_no_mcp_servers(self) -> None:
        profile_path = self.project / ".cap" / "profiles" / "review.toml"
        original = profile_path.read_text(encoding="utf-8")
        updated = original.replace('mcps = ["review-mcp"]', "mcps = []")
        self.assertNotEqual(updated, original)
        profile_path.write_text(updated, encoding="utf-8")
        (self.project / ".cap" / "capabilities" / "mcp" / "review-mcp.json").unlink()
        profile.create_lock(self.project)

        state = self.state_directory("empty-codex-mcp-state")
        result = profile.probe_profile(self.project, "codex", "review", state)
        self.assertEqual(result["observed"]["mcps"], [])

    def test_report_parser_does_not_turn_unknown_into_observed_none(self) -> None:
        self.assertIsNone(
            profile.parse_reported("SKILLS-AVAILABLE: unknown", "SKILLS-AVAILABLE")
        )
        self.assertEqual(
            profile.parse_reported("SKILLS-AVAILABLE: none", "SKILLS-AVAILABLE"), []
        )
        self.assertIsNone(profile.parse_reported("no marker", "SKILLS-AVAILABLE"))
        self.assertEqual(
            profile.parse_reported(
                "SKILLS-AVAILABLE: review-skill", "SKILLS-AVAILABLE"
            ),
            ["review-skill"],
        )
        self.assertEqual(
            profile.parse_reported("SKILLS-AVAILABLE: name1", "SKILLS-AVAILABLE"),
            ["name1"],
        )
        self.assertEqual(
            profile.parse_reported(
                "SKILLS-AVAILABLE: name1, name2", "SKILLS-AVAILABLE"
            ),
            ["name1", "name2"],
        )

    def test_diff_rejects_fifo_state_file_without_blocking(self) -> None:
        state = self.state_directory("fifo-state")
        os.mkfifo(state / "declared.json")
        with self.assertRaisesRegex(profile.ProfileError, "private regular file"):
            profile.diff_profile(self.project, "codex", "review", state)

    def test_run_and_diff_report_unknown_instead_of_silent_success(self) -> None:
        state = self.state_directory("unknown-state")

        def fake_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "SKILLS-AVAILABLE: review-skill\n"
                    "MCP-AVAILABLE: review-mcp\n"
                    "CONTEXT-FILES: unknown\n"
                    "HOOKS-AVAILABLE: unknown\n"
                    "PLUGINS-AVAILABLE: unknown\n"
                ),
                stderr="",
            )

        self.assertEqual(
            profile.run_observed(
                self.project,
                "codex",
                "review",
                state,
                ("exec", "observe"),
                runner=fake_runner,
            ),
            0,
        )
        effective = json.loads((state / "effective.json").read_text(encoding="utf-8"))
        self.assertIsNone(effective["observed"]["context"])
        self.assertIsNone(effective["observed"]["mcps"])
        self.assertEqual(effective["reported_client_limited"]["mcps"], ["review-mcp"])
        self.assertEqual(
            profile.diff_profile(self.project, "codex", "review", state), 2
        )

    def test_observed_none_is_drift_when_declaration_is_nonempty(self) -> None:
        state = self.state_directory("none-state")

        def fake_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
            return SimpleNamespace(
                returncode=0,
                stdout=(
                    "SKILLS-AVAILABLE: none\n"
                    "MCP-AVAILABLE: none\n"
                    "CONTEXT-FILES: none\n"
                    "HOOKS-AVAILABLE: none\n"
                    "PLUGINS-AVAILABLE: none\n"
                ),
                stderr="",
            )

        profile.run_observed(
            self.project,
            "qoder",
            "review",
            state,
            ("-p", "observe"),
            runner=fake_runner,
        )
        effective = json.loads((state / "effective.json").read_text(encoding="utf-8"))
        self.assertEqual(effective["observed"]["skills"], [])
        self.assertIsNone(effective["observed"]["hooks"])
        self.assertEqual(effective["reported_opaque_staging"]["hooks"], [])
        self.assertEqual(
            profile.diff_profile(self.project, "qoder", "review", state), 1
        )

    def test_concurrent_observed_profiles_have_independent_roots_outputs_and_receipts(
        self,
    ) -> None:
        review_state = self.state_directory("review-state")
        implementation_state = self.state_directory("implementation-state")
        runtime_roots: dict[str, Path] = {}

        def observed(profile_name: str, state: Path) -> int:
            def fake_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
                runtime_root = Path(str(kwargs["env"]["QODER_CONFIG_DIR"]))  # type: ignore[index]
                runtime_roots[profile_name] = runtime_root
                skill = f"{profile_name}-skill"
                self.assertTrue(
                    (runtime_root / "skills" / skill / "SKILL.md").is_file()
                )
                other = "implementation" if profile_name == "review" else "review"
                self.assertFalse((runtime_root / "skills" / f"{other}-skill").exists())
                return SimpleNamespace(
                    returncode=0,
                    stdout=(
                        f"SKILLS-AVAILABLE: {skill}\n"
                        f"MCP-AVAILABLE: {profile_name}-mcp\n"
                        "CONTEXT-FILES: unknown\n"
                        "HOOKS-AVAILABLE: unknown\n"
                        "PLUGINS-AVAILABLE: unknown\n"
                    ),
                    stderr="",
                )

            return profile.run_observed(
                self.project,
                "qoder",
                profile_name,
                state,
                ("-p", "observe"),
                runner=fake_runner,
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            review_future = executor.submit(observed, "review", review_state)
            implementation_future = executor.submit(
                observed, "implementation", implementation_state
            )
        self.assertEqual(review_future.result(), 0)
        self.assertEqual(implementation_future.result(), 0)
        self.assertNotEqual(runtime_roots["review"], runtime_roots["implementation"])
        self.assertFalse(runtime_roots["review"].exists())
        self.assertFalse(runtime_roots["implementation"].exists())
        review_receipt = json.loads(
            (review_state / "receipt.json").read_text(encoding="utf-8")
        )
        implementation_receipt = json.loads(
            (implementation_state / "receipt.json").read_text(encoding="utf-8")
        )
        self.assertEqual(review_receipt["profile"], "review")
        self.assertEqual(implementation_receipt["profile"], "implementation")
        self.assertNotEqual(
            review_receipt["output_tree_hash"],
            implementation_receipt["output_tree_hash"],
        )

    def test_observed_state_swap_cannot_redirect_evidence(self) -> None:
        state = self.state_directory("stable-state")
        moved = self.root / "moved-state"
        redirect = self.root / "redirect-state"
        redirect.mkdir()

        def replacing_runner(command: list[str], **kwargs: object) -> SimpleNamespace:
            state.rename(moved)
            state.symlink_to(redirect, target_is_directory=True)
            return SimpleNamespace(
                returncode=0,
                stdout="SKILLS-AVAILABLE: review-skill\n",
                stderr="",
            )

        with self.assertRaisesRegex(profile.ProfileError, "stable directory changed"):
            profile.run_observed(
                self.project,
                "qoder",
                "review",
                state,
                ("-p", "observe"),
                runner=replacing_runner,
            )
        self.assertEqual(list(redirect.iterdir()), [])
        self.assertFalse((moved / "receipt.json").exists())


class SingleEntryTests(unittest.TestCase):
    def test_profile_py_is_the_only_cli_and_observe_schema_is_removed(self) -> None:
        tool_root = Path(__file__).resolve().parents[1]
        self.assertEqual(
            sorted(path.name for path in tool_root.glob("*.py")),
            ["profile.py"],
        )
        self.assertFalse((tool_root.parent / "caprun").exists())
        self.assertFalse((tool_root / "observe").exists())
        self.assertFalse((tool_root / "observe-codex").exists())
        self.assertTrue(
            (
                tool_root / "fixtures" / "multi-profile" / ".cap" / "manifest.toml"
            ).is_file()
        )


if __name__ == "__main__":
    unittest.main()
