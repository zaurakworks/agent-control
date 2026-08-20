from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


from agent_system.cap import cli as cap


class NonTTY(io.StringIO):
    def isatty(self) -> bool:
        return False


class CapEntryTest(unittest.TestCase):
    def test_tui_selects_default_profile(self) -> None:
        class FakeCurses:
            KEY_UP = 259
            KEY_DOWN = 258
            KEY_LEFT = 260
            KEY_ENTER = 343
            error = RuntimeError

        class FakeScreen:
            def __init__(self) -> None:
                self.keys = [10]
                self.output: list[str] = []

            def erase(self) -> None:
                pass

            def getmaxyx(self) -> tuple[int, int]:
                return (40, 120)

            def addstr(self, _row: int, _column: int, text: str) -> None:
                self.output.append(text)

            def refresh(self) -> None:
                pass

            def getch(self) -> int:
                return self.keys.pop(0)

        screen = FakeScreen()
        profile = cap._tui_profile(
            screen,
            FakeCurses,
            ["agent-assembler", "general"],
        )

        self.assertEqual(profile, "general")
        self.assertTrue(
            any("general [默认]  通用工程" in line for line in screen.output)
        )

    def test_profile_defaults_to_general_and_accepts_chinese_name(self) -> None:
        parser = cap._build_parser()
        self.assertEqual(parser.parse_args(["run"]).profile, "general")
        self.assertEqual(cap.RUNNABLE_PROFILES, ("general", "agent-assembler"))
        self.assertNotIn("assembly-helper", cap.PROFILE_LABELS)

        stdout = io.StringIO()
        with (
            patch("builtins.input", return_value="通用工程"),
            contextlib.redirect_stdout(stdout),
        ):
            selected = cap._choose(
                "profile",
                ["general", "agent-assembler"],
                "general",
                cap.PROFILE_LABELS,
            )

        self.assertEqual(selected, "general")
        self.assertIn("general（通用工程） [默认]", stdout.getvalue())

    def test_skill_validation_includes_manifest_imports(self) -> None:
        project = Path(__file__).resolve().parents[2]
        report = cap._skill_metadata_report(project)

        self.assertEqual(report["standard_conformance"], "ok")
        grilling = next(
            skill for skill in report["skills"] if skill["id"] == "grilling"
        )
        self.assertEqual(
            grilling["path"],
            "plugins/grilling/skills/grilling/SKILL.md",
        )

    def test_help_remains_explicit_and_old_aliases_fail(self) -> None:
        with contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as help_exit:
                cap.main(["--help"])
        self.assertEqual(help_exit.exception.code, 0)

        for alias in ("i", "interactive"):
            stderr = io.StringIO()
            with self.subTest(alias=alias), contextlib.redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as alias_exit:
                    cap.main([alias])
            self.assertNotEqual(alias_exit.exception.code, 0)
            self.assertIn("请使用裸 cap", stderr.getvalue())

    def test_incomplete_non_tty_calls_fail_without_interaction(self) -> None:
        for argv, expected in (([], "裸 cap"), (["show"], "cap show")):
            stderr = io.StringIO()
            with (
                self.subTest(argv=argv),
                patch.object(cap.sys, "stdin", NonTTY()),
                patch.object(cap.sys, "stdout", NonTTY()),
                patch.object(cap, "_tui_use") as tui_use,
                patch.object(cap, "_show") as show,
                contextlib.redirect_stderr(stderr),
            ):
                result = cap.main(argv)
            self.assertEqual(result, 2)
            self.assertIn(expected, stderr.getvalue())
            tui_use.assert_not_called()
            show.assert_not_called()

    def test_explicit_run_and_render_remain_non_interactive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "home").mkdir()
            common = [
                "--project",
                str(root),
                "--home",
                str(root / "home"),
                "--agent-state-root",
                str(root / "agent-homes"),
                "--profile-tool",
                str(root / "profile.py"),
            ]
            cases = (
                ([*common, "run", "general", "--cli", "omp", "--", "-p", "check"], "run"),
                ([*common, "render", "general", "--cli", "omp", "--output", str(root / "rendered")], "materialize"),
            )
            for argv, command in cases:
                with (
                    self.subTest(command=command),
                    patch.object(cap.sys, "stdin", NonTTY()),
                    patch.object(cap.sys, "stdout", NonTTY()),
                    patch.object(cap, "_run_selected", return_value=23) as run_selected,
                ):
                    result = cap.main(argv)
                self.assertEqual(result, 23)
                selected = run_selected.call_args.args[0]
                self.assertEqual(selected.profile_tool_command, command)
                self.assertEqual(Path(selected._real_home), (root / "home").resolve())

    def test_layered_commands_forward_all_binding_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            common = [
                "--machine-context-manifest",
                str(root / "base.json"),
                "--machine-context-pin",
                str(root / "pin.json"),
                "--assembly-binding-dir",
                str(root / "bindings"),
            ]
            verify = cap._build_parser().parse_args([*common, "verify"])
            render = cap._build_parser().parse_args(
                [
                    *common,
                    "render",
                    "general",
                    "--output",
                    str(root / "output"),
                ]
            )

        for args in (verify, render):
            command = cap._profile_args(args)
            self.assertIn(str(root / "base.json"), command)
            self.assertIn(str(root / "pin.json"), command)
            self.assertIn(str(root / "bindings"), command)


class CapShowTest(unittest.TestCase):
    def test_explicit_profile_outputs_public_closure_without_prompt(self) -> None:
        args = cap._build_parser().parse_args(["show", "general"])
        explanation = {"profile": "general", "inventory": {"skills": []}, "clients": {}}
        stdout = io.StringIO()
        with (
            patch.object(cap, "_profile_json", return_value=explanation),
            patch.object(cap, "_choose") as choose,
            patch.object(cap, "_render_preview") as render_preview,
            contextlib.redirect_stdout(stdout),
        ):
            result = cap._show(args, {})

        self.assertEqual(result, 0)
        self.assertEqual(json_from(stdout), explanation)
        choose.assert_not_called()
        render_preview.assert_not_called()

    def test_interactive_show_outputs_public_closure_then_allows_no_expansion(self) -> None:
        args = cap._build_parser().parse_args(["show"])
        explanation = {"profile": "general", "inventory": {"skills": []}, "clients": {}}
        stdout = io.StringIO()
        with (
            patch.object(cap, "_available_profiles", return_value=["agent-assembler", "general"]),
            patch.object(cap, "_choose", side_effect=["general", "不展开"]) as choose,
            patch.object(cap, "_profile_json", return_value=explanation),
            patch.object(cap, "_render_preview") as render_preview,
            contextlib.redirect_stdout(stdout),
        ):
            result = cap._show(args, {})

        self.assertEqual(result, 0)
        self.assertEqual([call.args[0] for call in choose.call_args_list], ["profile", "CLI 装配"])
        self.assertEqual(json_from(stdout), explanation)
        render_preview.assert_not_called()

    def test_explicit_cli_combines_public_closure_and_preview(self) -> None:
        args = cap._build_parser().parse_args(["show", "general", "--cli", "omp"])
        explanation = {"profile": "general", "inventory": {"skills": []}, "clients": {}}
        preview = {"client": "omp", "files": ["config.yml"], "tree_hash": "sha256:test"}
        stdout = io.StringIO()
        with (
            patch.object(cap, "_profile_json", return_value=explanation),
            patch.object(cap, "_render_preview", return_value=preview),
            patch.object(cap, "_choose") as choose,
            contextlib.redirect_stdout(stdout),
        ):
            result = cap._show(args, {})

        self.assertEqual(result, 0)
        self.assertEqual(json_from(stdout)["preview"], preview)
        choose.assert_not_called()


class CapPreviewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.args = cap._build_parser().parse_args(["show", "general", "--cli", "omp"])
        self.real_temporary_directory = tempfile.TemporaryDirectory

    def test_preview_lists_sorted_relative_files_and_cleans_success(self) -> None:
        created: list[str] = []

        def tracked_directory(*args: object, **kwargs: object) -> tempfile.TemporaryDirectory[str]:
            directory = self.real_temporary_directory(*args, **kwargs)
            created.append(directory.name)
            return directory

        def render(preview_args: object, _env: object, _stage: object) -> dict[str, object]:
            output = Path(preview_args.output)
            (output / "skills" / "sample").mkdir(parents=True)
            (output / "skills" / "sample" / "SKILL.md").write_text("skill\n", encoding="utf-8")
            (output / "config.yml").write_text("config\n", encoding="utf-8")
            return {"tree_hash": "sha256:test"}

        with self.real_temporary_directory() as generation_temp:
            generation = Path(generation_temp) / "generation"
            generation.mkdir()
            (generation / ".cap-generation.json").write_text(
                json.dumps(
                    {
                        "source_context": {
                            "profile": "general",
                            "layer_digest": "sha256:layer",
                        },
                        "source_digest": "sha256:source",
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch.object(cap.tempfile, "TemporaryDirectory", side_effect=tracked_directory),
                patch.object(cap, "_profile_json", side_effect=render),
                patch.object(
                    cap,
                    "_materialize_profile_generation",
                    return_value=(
                        generation,
                        "sha256:test",
                        "sha256:effective",
                        ["sample"],
                    ),
                ),
                patch.object(
                    cap,
                    "_agent_home_dir",
                    return_value=Path("/state/global/omp/default"),
                ),
            ):
                preview = cap._render_preview(self.args, {})

            self.assertEqual(
                preview,
                {
                    "client": "omp",
                    "files": ["config.yml", "skills/sample/SKILL.md"],
                    "tree_hash": "sha256:test",
                    "runtime_id": "default",
                    "global_runtime_root": "/state/global/omp/default",
                    "global_generation": str(generation),
                    "portable_tree_hash": "sha256:test",
                    "effective_render_hash": "sha256:effective",
                    "project_source_context": {
                        "profile": "general",
                        "layer_digest": "sha256:layer",
                    },
                    "project_source_digest": "sha256:source",
                    "skills": ["sample"],
                    "fixed_flags": ["--no-extensions", "--no-rules"],
                },
            )
        self.assertTrue(created)
        self.assertTrue(all(not os.path.exists(path) for path in created))

    def test_preview_cleans_render_failure(self) -> None:
        created: list[str] = []

        def tracked_directory(*args: object, **kwargs: object) -> tempfile.TemporaryDirectory[str]:
            directory = self.real_temporary_directory(*args, **kwargs)
            created.append(directory.name)
            return directory

        with (
            patch.object(cap.tempfile, "TemporaryDirectory", side_effect=tracked_directory),
            patch.object(cap, "_profile_json", return_value=None),
        ):
            preview = cap._render_preview(self.args, {})

        self.assertIsNone(preview)
        self.assertTrue(created)
        self.assertTrue(all(not os.path.exists(path) for path in created))


class PrivateRuntimeValidationTest(unittest.TestCase):
    """Cover both branches of _validate_private_runtime on either host."""

    def _run_non_posix(self, root: Path, private_root: Path) -> None:
        """Exercise the branch taken when os.geteuid is unavailable."""

        from agent_system.omp import runtime

        with _HiddenAttr(runtime.os, "geteuid"):
            runtime._validate_private_runtime(
                root, "test runtime", private_root=private_root
            )

    def test_windows_branch_rejects_directory_outside_managed_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            managed = root / "managed"
            outside = root / "outside"
            managed.mkdir()
            outside.mkdir()
            with self.assertRaisesRegex(Exception, "CAP-managed root"):
                self._run_non_posix(outside, managed)

    def test_windows_branch_accepts_directory_inside_managed_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            managed = root / "managed"
            inside = managed / "renders" / "omp"
            inside.mkdir(parents=True)
            self._run_non_posix(inside, managed)

    def test_private_root_is_required(self) -> None:
        from agent_system.omp import runtime

        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(TypeError):
                runtime._validate_private_runtime(Path(temporary), "test runtime")


class _HiddenAttr:
    """Temporarily remove one attribute so hasattr() reports it missing."""

    def __init__(self, target: object, name: str) -> None:
        self._target = target
        self._name = name
        self._missing = object()
        self._original = getattr(target, name, self._missing)

    def __enter__(self) -> None:
        if self._original is not self._missing:
            delattr(self._target, self._name)

    def __exit__(self, *exc: object) -> None:
        if self._original is not self._missing:
            setattr(self._target, self._name, self._original)


class SharedRuntimeTest(unittest.TestCase):
    def test_profiles_share_runtime_and_clear_broker_environment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shared = root / "agent-homes" / "shared" / "omp"
            real_home = root / "home"
            real_home.mkdir()
            ambient = {
                "HOME": "/ambient",
                "PI_CONFIG_DIR": "/ambient-config",
                "OPENAI_API_KEY": "ambient-provider-key",
                "AWS_PROFILE": "ambient-cloud-profile",
                "OMP_AUTH_BROKER_URL": "https://ambient.invalid",
                "OMP_AUTH_BROKER_TOKEN": "ambient-broker-token",
            }
            environments = [
                cap._agent_home_env(
                    ambient,
                    shared,
                    root / "renders" / profile,
                    real_home,
                )
                for profile in cap.RUNNABLE_PROFILES
            ]

        self.assertEqual(
            {environment["PI_CODING_AGENT_DIR"] for environment in environments},
            {str(shared)},
        )
        self.assertEqual(
            {environment["PI_CONFIG_DIR"] for environment in environments},
            {str(shared)},
        )
        self.assertEqual(
            {environment["HOME"] for environment in environments},
            {str(real_home)},
        )
        for environment in environments:
            self.assertNotIn("OMP_AUTH_BROKER_URL", environment)
            self.assertNotIn("OMP_AUTH_BROKER_TOKEN", environment)
            self.assertEqual(environment["OPENAI_API_KEY"], "")
            self.assertEqual(environment["AWS_PROFILE"], "")
            self.assertEqual(environment["PI_AUTH_NO_BORROW"], "1")
            self.assertEqual(environment["AWS_EC2_METADATA_DISABLED"], "true")

    def test_runtime_id_resolves_only_inside_approved_user_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            home.mkdir()
            args = cap.argparse.Namespace(
                home=str(home),
                omp_runtime_id="default",
                omp_runtime_root=None,
            )
            expected = (
                home
                / ".agent-system-state"
                / "runtimes"
                / "omp"
                / "default"
            )
            self.assertEqual(cap._agent_home_dir(args), expected)
            args.omp_runtime_id = "work-account"
            self.assertEqual(
                cap._agent_home_dir(args),
                expected.parent / "work-account",
            )
            args.omp_runtime_root = str(home / ".omp")
            with self.assertRaisesRegex(
                cap._MigrationError, "approved HOME/id path"
            ):
                cap._agent_home_dir(args)
            args.omp_runtime_id = "../escape"
            args.omp_runtime_root = None
            with self.assertRaisesRegex(
                cap._MigrationError, "lowercase kebab-case"
            ):
                cap._agent_home_dir(args)

    def test_fresh_and_other_clients_keep_explicit_auth_root(self) -> None:
        root = Path("/private/test")
        common = [
            "--auth-root",
            str(root / "auth"),
            "--profile-tool",
            str(root / "profile.py"),
        ]
        for client in ("codex", "qoder", "omp"):
            args = cap._build_parser().parse_args(
                [
                    *common,
                    "use",
                    "general",
                    "--cli",
                    client,
                    "--fresh",
                ]
            )
            args.client_args = []
            command = cap._profile_args(args)
            self.assertIn("--auth-root", command)
            self.assertIn(str(root / "auth"), command)

    def test_receipt_reports_shared_runtime_without_auth_material(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            binding_dir = root / "bindings"
            binding_dir.mkdir()
            (binding_dir / "general.binding.json").write_text(
                json.dumps(
                    {
                        "base_digest": "sha256:base",
                        "layer_digest": "sha256:layer",
                        "effective_digest": "sha256:effective",
                    }
                ),
                encoding="utf-8",
            )
            workdir = root / "workdir"
            workdir.mkdir()
            receipt = root / "receipt.json"
            generation = root / "renders" / "general" / "hash"
            generation.mkdir(parents=True)
            (generation / ".cap-generation.json").write_text(
                json.dumps(
                    {
                        "source_context": {
                            "profile": "general",
                            "layer_digest": "sha256:layer",
                        },
                        "source_digest": "sha256:source",
                    }
                ),
                encoding="utf-8",
            )
            args = cap.argparse.Namespace(
                binding_dir=str(binding_dir),
                profile="general",
                cli="omp",
                project=str(root / "project"),
                omp_runtime_id="default",
                workdir=str(workdir),
                client_args=["-p", "check"],
            )
            shared = root / ".cap-user-state" / "runtimes" / "omp" / "default"

            cap._write_receipt(
                args,
                receipt,
                0,
                "sha256:portable",
                "sha256:effective-render",
                shared,
                generation,
            )
            payload = json.loads(receipt.read_text(encoding="utf-8"))
            serialized = json.dumps(payload)

        self.assertEqual(payload["version"], 4)
        self.assertEqual(payload["profile"], "general")
        self.assertEqual(payload["runtime_id"], "default")
        self.assertEqual(payload["global_runtime_root"], str(shared))
        self.assertEqual(payload["global_generation"], str(generation))
        self.assertEqual(payload["project_source_digest"], "sha256:source")
        self.assertEqual(payload["portable_tree_hash"], "sha256:portable")
        self.assertNotIn("broker", serialized.lower())
        self.assertNotIn("token", serialized.lower())
        self.assertNotIn("auth-root", serialized.lower())

    def test_command_uses_current_overlay_and_shared_session_space(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            commands: list[list[str]] = []
            for profile, skills in (
                ("general", ["openspec-apply-change"]),
                ("agent-assembler", ["agent-assembler"]),
            ):
                generation = root / profile
                generation.mkdir()
                (generation / "system-prompt.md").write_text(
                    f"{profile} prompt\n", encoding="utf-8"
                )
                (generation / "config.yml").write_text("{}\n", encoding="utf-8")
                (generation / "extension").mkdir()
                commands.append(
                    cap._omp_command(
                        generation,
                        skills,
                        ["--resume", "shared-session"],
                    )
                )

        for command, profile in zip(
            commands, ("general", "agent-assembler"), strict=True
        ):
            self.assertEqual(
                command[command.index("--append-system-prompt") + 1],
                f"{profile} prompt\n",
            )
            self.assertIn("--extension", command)
            self.assertIn("--no-extensions", command)
            self.assertIn("--no-rules", command)
            self.assertNotIn("--session-dir", command)
            self.assertEqual(command[-2:], ["--resume", "shared-session"])
        self.assertNotEqual(
            commands[0][commands[0].index("--skills") + 1],
            commands[1][commands[1].index("--skills") + 1],
        )


class ProfileGenerationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.bindings = self.root / "bindings"
        self.bindings.mkdir()
        for profile in ("general", "agent-assembler"):
            (self.bindings / f"{profile}.binding.json").write_text(
                json.dumps(
                    {
                        "layer_digest": f"sha256:layer-{profile}",
                        "effective_digest": f"sha256:effective-{profile}",
                    }
                ),
                encoding="utf-8",
            )
        for project_name in ("project", "project-copy"):
            cap_dir = self.root / project_name / ".cap"
            cap_dir.mkdir(parents=True)
            runtime_dir = cap_dir / "runtime"
            runtime_dir.mkdir()
            (runtime_dir / "omp.toml").write_text(
                'version = 1\nclient = "omp"\n\n[policy]\n'
                'memory_backend = "off"\nenable_project_mcp = false\n',
                encoding="utf-8",
            )
            (cap_dir / "lock.json").write_text(
                json.dumps(
                    {
                        "clients": {
                            "omp": {"adapter_version": 8}
                        }
                    }
                ),
                encoding="utf-8",
            )

    def args(self, profile: str, project_name: str = "project") -> object:
        return cap.argparse.Namespace(
            profile=profile,
            agent_home_root=str(self.root / "agent-homes"),
            home=str(self.home),
            omp_runtime_id="default",
            omp_runtime_root=None,
            profile_tool=str(self.root / "profile.py"),
            project=str(self.root / project_name),
            base_manifest=str(self.root / "base.json"),
            base_pin=str(self.root / "pin.json"),
            binding_dir=str(self.bindings),
        )

    def render(self, command: list[str], **_: object) -> object:
        output = Path(command[command.index("--output") + 1])
        profile = command[command.index("--profile") + 1]
        skills = (
            ["openspec-apply-change"]
            if profile == "general"
            else ["agent-assembler", "openspec-apply-change"]
        )
        (output / "skills").mkdir()
        for skill in skills:
            skill_root = output / "skills" / skill
            skill_root.mkdir()
            (skill_root / "SKILL.md").write_text(
                f"---\nname: {skill}\ndescription: test\n---\n",
                encoding="utf-8",
            )
        (output / "config.yml").write_text("{}\n", encoding="utf-8")
        (output / "mcp.json").write_text(
            '{"mcpServers":{}}\n', encoding="utf-8"
        )
        (output / "system-prompt.md").write_text(
            f"{profile} prompt\n", encoding="utf-8"
        )
        return cap.subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps({"tree_hash": f"sha256:{profile}"}),
            stderr="",
        )

    def test_effective_config_and_immutable_reuse(self) -> None:
        args = self.args("general")
        with patch.object(cap.subprocess, "run", side_effect=self.render):
            first = cap._materialize_profile_generation(args, {})
            first_mtime = first[0].stat().st_mtime_ns
            second = cap._materialize_profile_generation(args, {})

        self.assertEqual(first, second)
        self.assertEqual(first[0].stat().st_mtime_ns, first_mtime)
        config = yaml_from(first[0] / "config.yml")
        self.assertEqual(config["memory"]["backend"], "off")
        self.assertFalse(config["mcp"]["enableProjectConfig"])
        self.assertEqual(
            config["skills"]["customDirectories"],
            [str(first[0] / "skills")],
        )
        self.assertEqual(
            config["skills"]["includeSkills"],
            ["openspec-apply-change"],
        )
        for key in (
            "enableCodexUser",
            "enableClaudeUser",
            "enableClaudeProject",
            "enablePiUser",
            "enablePiProject",
            "enableAgentsUser",
            "enableAgentsProject",
        ):
            self.assertFalse(config["skills"][key])
        self.assertTrue((first[0] / "extension" / ".mcp.json").is_file())

    def test_tampering_is_rejected(self) -> None:
        args = self.args("general")
        with patch.object(cap.subprocess, "run", side_effect=self.render):
            generation, *_ = cap._materialize_profile_generation(args, {})
            (generation / "system-prompt.md").write_text(
                "tampered\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                cap._MigrationError, "content drifted"
            ):
                cap._materialize_profile_generation(args, {})

    def test_extra_generation_file_is_rejected(self) -> None:
        args = self.args("general")
        with patch.object(cap.subprocess, "run", side_effect=self.render):
            generation, *_ = cap._materialize_profile_generation(args, {})
            (generation / "unexpected.txt").write_text(
                "unexpected\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                cap._MigrationError, "content drifted"
            ):
                cap._materialize_profile_generation(args, {})

    def test_source_context_and_digest_mismatch_are_rejected(self) -> None:
        args = self.args("general")
        with patch.object(cap.subprocess, "run", side_effect=self.render):
            generation, *_ = cap._materialize_profile_generation(args, {})
            manifest_path = generation / ".cap-generation.json"
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            manifest["source_context"]["layer_digest"] = "sha256:wrong"
            manifest["source_digest"] = "sha256:wrong"
            manifest_path.write_text(
                json.dumps(manifest), encoding="utf-8"
            )
            with self.assertRaisesRegex(
                cap._MigrationError, "metadata drifted"
            ):
                cap._materialize_profile_generation(args, {})


    def test_profiles_and_concurrent_materialization_do_not_collide(self) -> None:
        def materialize(profile: str) -> tuple[Path, str, str, list[str]]:
            return cap._materialize_profile_generation(
                self.args(profile), {}
            )

        with patch.object(cap.subprocess, "run", side_effect=self.render):
            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(
                    executor.map(
                        materialize,
                        [
                            "general",
                            "agent-assembler",
                            "general",
                            "agent-assembler",
                        ],
                    )
                )

        general_paths = {result[0] for result in results[::2]}
        helper_paths = {result[0] for result in results[1::2]}
        self.assertEqual(len(general_paths), 1)
        self.assertEqual(len(helper_paths), 1)
        self.assertTrue(general_paths.isdisjoint(helper_paths))
        for result in results:
            manifest = json.loads(
                (result[0] / ".cap-generation.json").read_text(
                    encoding="utf-8"
                )
            )
            cap._verify_profile_generation(
                result[0],
                manifest["profile"],
                result[1],
                result[2],
                manifest["source_context"],
                manifest["source_digest"],
                manifest["runtime_policy"],
            )

    def test_global_cas_rebuilds_and_reuses_across_worktrees(self) -> None:
        with patch.object(cap.subprocess, "run", side_effect=self.render):
            first = cap._materialize_profile_generation(
                self.args("general", "project"), {}
            )
            cap.shutil.rmtree(first[0])
            rebuilt = cap._materialize_profile_generation(
                self.args("general", "project"), {}
            )
            reused = cap._materialize_profile_generation(
                self.args("general", "project-copy"), {}
            )
        self.assertEqual(first[0], rebuilt[0])
        self.assertEqual(rebuilt[0], reused[0])

    def test_cache_never_authorizes_unknown_profile(self) -> None:
        def reject_unknown(command: list[str], **_: object) -> object:
            return cap.subprocess.CompletedProcess(
                command,
                2,
                stdout="",
                stderr="unknown profile",
            )
        fake_cache = (
            self.home
            / ".cap-user-state"
            / "renders"
            / "omp"
            / "preexisting-undeclared-profile"
        )
        fake_cache.mkdir(parents=True)
        (fake_cache / ".cap-generation.json").write_text(
            json.dumps(
                {
                    "version": 2,
                    "profile": "not-declared",
                    "source_digest": "sha256:untrusted",
                }
            ),
            encoding="utf-8",
        )

        with (
            patch.object(
                cap.subprocess, "run", side_effect=reject_unknown
            ),
            contextlib.redirect_stderr(io.StringIO()),
            self.assertRaises(SystemExit),
        ):
            cap._materialize_profile_generation(
                self.args("not-declared"), {}
            )


class OmpRuntimeMigrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.agent_root = self.root / "project.agent-homes"
        self.args = cap.argparse.Namespace(
            home=str(self.home),
            omp_runtime_id="default",
            omp_runtime_root=None,
            agent_home_root=str(self.agent_root),
            auth_root=str(self.root / "project.auth"),
        )

    def make_runtime(
        self,
        runtime: Path,
        *,
        identity: str | None = None,
        config: dict[str, object] | None = None,
        sessions: dict[str, str] | None = None,
        global_marker: bool = False,
    ) -> Path:
        runtime.mkdir(parents=True, mode=0o700)
        runtime.chmod(0o700)
        database = runtime / "agent.db"
        connection = cap.sqlite3.connect(database)
        connection.executescript(
            """
            CREATE TABLE auth_credentials (
                provider TEXT,
                credential_type TEXT,
                identity_key TEXT,
                disabled_cause TEXT
            );
            CREATE TABLE auth_schema_version (version INTEGER);
            INSERT INTO auth_schema_version VALUES (1);
            CREATE TABLE schema_version (version INTEGER);
            INSERT INTO schema_version VALUES (1);
            CREATE TABLE settings (key TEXT, value TEXT);
            """
        )
        if identity is not None:
            connection.execute(
                "INSERT INTO auth_credentials VALUES (?, ?, ?, NULL)",
                ("openai-codex", "oauth", identity),
            )
        connection.commit()
        connection.close()
        database.chmod(0o600)
        (runtime / "config.yml").write_text(
            cap.yaml.safe_dump(config or {}, sort_keys=True),
            encoding="utf-8",
        )
        (runtime / "config.yml").chmod(0o600)
        cap._write_shared_mcp_policy(runtime)
        for relative, content in (sessions or {}).items():
            path = runtime / "sessions" / relative
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            path.write_text(content, encoding="utf-8")
            path.chmod(0o600)
        if global_marker:
            (runtime / ".cap-shared-runtime.json").write_text(
                json.dumps(
                    {
                        "version": 2,
                        "runtime_id": "default",
                        "migration_complete": True,
                        "session_files": len(sessions or {}),
                    }
                ),
                encoding="utf-8",
            )
        return runtime

    def test_dry_run_selects_project_source(self) -> None:
        source = self.make_runtime(
            cap._project_shared_omp_home(self.args),
            identity="account",
            config={"theme": {"dark": "titanium"}},
            sessions={"project/source.jsonl": "source\n"},
        )

        public, summaries, canonical, config, sessions = cap._migration_plan(
            self.args
        )

        self.assertEqual(canonical, "project-shared")
        self.assertEqual(public["runtime_id"], "default")
        self.assertTrue(public["source"]["exists"])
        self.assertFalse(public["target"]["exists"])
        self.assertEqual(public["session_files"], 1)
        self.assertEqual(config["memory"]["backend"], "off")
        self.assertEqual(
            summaries["project-shared"].root, source
        )
        self.assertNotIn("account", json.dumps(public))
        self.assertEqual(set(sessions), {"project/source.jsonl"})
    def test_dry_run_is_read_only_and_secret_safe(self) -> None:
        source = self.make_runtime(
            cap._project_shared_omp_home(self.args),
            identity="account",
            config={"memory": {"backend": "sqlite"}, "theme": {"dark": "titanium"}},
            sessions={"project/source.jsonl": "source\n"},
        )
        before = {
            path.relative_to(source).as_posix(): path.read_bytes()
            for path in source.rglob("*")
            if path.is_file()
        }

        public, _, _, config, _ = cap._migration_plan(self.args)

        after = {
            path.relative_to(source).as_posix(): path.read_bytes()
            for path in source.rglob("*")
            if path.is_file()
        }
        self.assertEqual(after, before)
        self.assertEqual(config["memory"], {"backend": "off"})
        self.assertNotIn("account", json.dumps(public))
        self.assertFalse(cap._agent_home_dir(self.args).exists())
        self.assertFalse(cap._migration_backup_root(self.args).exists())

    def test_apply_quarantines_legacy_state_until_cleanup(self) -> None:
        source = self.make_runtime(
            cap._project_shared_omp_home(self.args),
            identity="account",
            sessions={"project/source.jsonl": "source\n"},
        )
        public, summaries, canonical, config, sessions = cap._migration_plan(
            self.args
        )

        result = cap._apply_omp_runtime_migration(
            self.args, public, summaries, canonical, config, sessions
        )

        backup = cap._migration_backup_root(self.args) / "project-shared"
        self.assertEqual(result["status"], "migrated-global")
        self.assertTrue(source.is_dir())
        self.assertTrue(backup.is_dir())
        self.assertEqual(
            (backup / "sessions" / "project/source.jsonl").read_text(
                encoding="utf-8"
            ),
            "source\n",
        )
        self.assertTrue((backup / "agent.db").is_file())
    def test_rollback_restores_legacy_runtime_and_removes_new_target(self) -> None:
        source = self.make_runtime(
            cap._project_shared_omp_home(self.args),
            identity="account",
            config={"theme": {"dark": "before"}},
            sessions={"project/source.jsonl": "source\n"},
        )
        public, summaries, canonical, config, sessions = cap._migration_plan(
            self.args
        )
        cap._apply_omp_runtime_migration(
            self.args, public, summaries, canonical, config, sessions
        )
        (cap._agent_home_dir(self.args) / "config.yml").write_text(
            "theme:\n  dark: changed\n", encoding="utf-8"
        )

        result = cap._rollback_omp_runtime(self.args)

        self.assertEqual(result["status"], "rolled-back")
        self.assertEqual(
            (source / "config.yml").read_text(encoding="utf-8"),
            "memory:\n  backend: 'off'\ntheme:\n  dark: before\n",
        )
        self.assertFalse(cap._agent_home_dir(self.args).exists())
        self.assertFalse(cap._migration_backup_root(self.args).exists())

    def test_apply_installs_global_runtime_and_is_idempotent(self) -> None:
        self.make_runtime(
            cap._project_shared_omp_home(self.args),
            identity="account",
            sessions={"project/source.jsonl": "source\n"},
        )
        public, summaries, canonical, config, sessions = cap._migration_plan(
            self.args
        )

        result = cap._apply_omp_runtime_migration(
            self.args, public, summaries, canonical, config, sessions
        )
        second = cap._migration_plan(self.args)[0]

        global_runtime = cap._agent_home_dir(self.args)
        self.assertEqual(result["status"], "migrated-global")
        self.assertEqual(second["status"], "ready")
        self.assertTrue((global_runtime / "agent.db").is_file())
        self.assertTrue(
            (
                global_runtime
                / "sessions"
                / "project/source.jsonl"
            ).is_file()
        )
        marker = json.loads(
            (global_runtime / ".cap-shared-runtime.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(marker["version"], 2)
        self.assertEqual(marker["runtime_id"], "default")
        self.assertTrue(cap._migration_backup_root(self.args).is_dir())

    def test_existing_equivalent_global_target_merges_sessions(self) -> None:
        self.make_runtime(
            cap._project_shared_omp_home(self.args),
            identity="account",
            sessions={"source/source.jsonl": "source\n"},
        )
        self.make_runtime(
            cap._agent_home_dir(self.args),
            identity="account",
            sessions={"target/target.jsonl": "target\n"},
            global_marker=True,
        )
        public, summaries, canonical, config, sessions = cap._migration_plan(
            self.args
        )
        self.assertEqual(canonical, "global")
        self.assertEqual(set(sessions), {
            "source/source.jsonl",
            "target/target.jsonl",
        })
        cap._apply_omp_runtime_migration(
            self.args, public, summaries, canonical, config, sessions
        )
        target = cap._agent_home_dir(self.args) / "sessions"
        self.assertTrue((target / "source/source.jsonl").is_file())
        self.assertTrue((target / "target/target.jsonl").is_file())

    def test_conflicts_and_active_writer_fail_before_install(self) -> None:
        source = self.make_runtime(
            cap._project_shared_omp_home(self.args),
            identity="source-account",
            config={"theme": {"dark": "one"}},
            sessions={"same.jsonl": "one\n"},
        )
        self.make_runtime(
            cap._agent_home_dir(self.args),
            identity="target-account",
            config={"theme": {"dark": "two"}},
            sessions={"same.jsonl": "two\n"},
            global_marker=True,
        )
        with self.assertRaises(cap._MigrationError):
            cap._migration_plan(self.args)

        cap.shutil.rmtree(cap._agent_home_dir(self.args))
        connection = cap.sqlite3.connect(source / "agent.db", timeout=0.05)
        connection.execute("BEGIN IMMEDIATE")
        try:
            with self.assertRaisesRegex(
                cap._MigrationError, "busy or unreadable"
            ):
                cap._migration_plan(self.args)
        finally:
            connection.rollback()
            connection.close()

    def test_failed_install_removes_stage_and_backup(self) -> None:
        self.make_runtime(cap._project_shared_omp_home(self.args))
        public, summaries, canonical, config, sessions = cap._migration_plan(
            self.args
        )
        with (
            patch.object(cap.os, "rename", side_effect=OSError("failed")),
            self.assertRaises(OSError),
        ):
            cap._apply_omp_runtime_migration(
                self.args, public, summaries, canonical, config, sessions
            )
        self.assertFalse(cap._agent_home_dir(self.args).exists())
        self.assertFalse(cap._migration_backup_root(self.args).exists())
        self.assertTrue(cap._project_shared_omp_home(self.args).exists())

    def test_cleanup_removes_only_project_migration_state(self) -> None:
        self.make_runtime(
            cap._project_shared_omp_home(self.args),
            identity="account",
        )
        project_renders = cap._project_render_root(self.args)
        project_renders.mkdir(parents=True)
        (project_renders / "old").write_text("old", encoding="utf-8")
        public, summaries, canonical, config, sessions = cap._migration_plan(
            self.args
        )
        cap._apply_omp_runtime_migration(
            self.args, public, summaries, canonical, config, sessions
        )

        result = cap._cleanup_legacy_omp_runtime(self.args)

        self.assertEqual(result["status"], "cleaned-project-state")
        self.assertFalse(cap._project_shared_omp_home(self.args).exists())
        self.assertFalse(cap._project_render_root(self.args).exists())
        self.assertFalse(cap._migration_backup_root(self.args).exists())
        self.assertTrue(cap._agent_home_dir(self.args).is_dir())
        outside = self.root / "outside"
        outside.mkdir()
        with self.assertRaisesRegex(
            cap._MigrationError, "outside the CAP state root"
        ):
            cap._safe_remove_tree(self.agent_root, outside, "outside")


def yaml_from(path: Path) -> dict[str, object]:
    payload = cap.yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def json_from(buffer: io.StringIO) -> dict[str, object]:
    import json

    payload = json.loads(buffer.getvalue())
    assert isinstance(payload, dict)
    return payload


if __name__ == "__main__":
    unittest.main()
