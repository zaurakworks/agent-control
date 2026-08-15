"""Command-line interface for entrypoint generation and verification."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import (
    EntrySyncError,
    compare_contents,
    generate_target,
    iter_targets,
    load_config,
    read_utf8,
    replace_files_atomically,
    repository_root,
    repository_write_bytes,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="从 entrypoints/agent-system.md 生成并校验各运行入口。"
    )
    parser.add_argument("--config", type=Path, help="覆盖默认 targets.json。")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="生成全部声明目标到 build 目录。")
    generate.add_argument(
        "--output-dir",
        type=Path,
        default=Path("build/entry-sync"),
        help="生成目录（默认 build/entry-sync）。",
    )
    generate.add_argument(
        "--scope",
        choices=("all", "repository", "installed"),
        default="all",
    )
    generate.add_argument(
        "--write-repository",
        action="store_true",
        help="同时更新仓内目标；从不写用户目录或 APPDATA。",
    )

    check = subparsers.add_parser("check", help="规范化换行后比对当前目标。")
    check.add_argument(
        "--scope",
        choices=("all", "repository", "installed"),
        default="all",
    )
    check.add_argument("--context-lines", type=int, default=3)
    return parser


def _resolved_output(root: Path, value: Path) -> Path:
    return value if value.is_absolute() else root / value


def run_generate(args: argparse.Namespace) -> int:
    if args.write_repository and args.scope == "installed":
        raise EntrySyncError(
            "--write-repository 不能与 --scope installed 组合："
            "installed 目标从不写回，请使用 --scope all 或 --scope repository"
        )
    root = repository_root()
    config = load_config(args.config)
    output_root = _resolved_output(root, args.output_dir)
    source_display = config["source"]
    results = [
        generate_target(root, config, target, output_root)
        for target in iter_targets(config, args.scope)
    ]

    replace_files_atomically(
        [(result.output_path, result.content.encode("utf-8")) for result in results]
    )
    for result in results:
        print(
            f"{source_display} -> {result.current_path} "
            f"[build: {result.output_path}]"
        )

    if args.write_repository:
        repository_writes: list[tuple[Path, bytes]] = []
        for result in results:
            if result.scope != "repository":
                continue
            try:
                current_bytes = (
                    result.current_path.read_bytes()
                    if result.current_path.exists()
                    else None
                )
            except OSError as error:
                raise EntrySyncError(
                    f"无法读取当前目标以保留换行约定：{result.current_path}: {error}"
                ) from error
            repository_writes.append(
                (
                    result.current_path,
                    repository_write_bytes(result.content, current_bytes),
                )
            )
        replace_files_atomically(repository_writes)
        for path, _ in repository_writes:
            print(f"[WRITE repository] {path}")
    return 0


def run_check(args: argparse.Namespace) -> int:
    root = repository_root()
    config = load_config(args.config)
    scratch_output = root / "build/entry-sync"
    failures = 0
    for target in iter_targets(config, args.scope):
        target_id = target["id"]
        try:
            result = generate_target(root, config, target, scratch_output)
            actual = read_utf8(result.current_path)
            comparison = compare_contents(
                result.content,
                actual,
                expected_name=f"generated/{target_id}",
                actual_name=str(result.current_path),
                context_lines=args.context_lines,
            )
        except EntrySyncError as error:
            failures += 1
            print(f"[ERROR] {target_id}: {error}")
            continue

        if comparison.matches:
            print(f"[OK] {target_id}: {result.current_path}")
        else:
            failures += 1
            print(f"[DIFF] {target_id}: {result.current_path}")
            print(comparison.diff, end="" if comparison.diff.endswith("\n") else "\n")
    return 1 if failures else 0


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "generate":
            return run_generate(args)
        return run_check(args)
    except EntrySyncError as error:
        print(f"entry-sync: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
