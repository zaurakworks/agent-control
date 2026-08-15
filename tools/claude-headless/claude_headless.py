"""Run one schema-bound Claude headless advisory call with hard local limits."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Sequence


DEFAULT_MAX_TURNS = 1
DEFAULT_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_MAX_BUDGET_USD = Decimal("0.10")
DEFAULT_TIMEOUT_SECONDS = 60.0
MAX_ALLOWED_TURNS = 3
MAX_ALLOWED_BUDGET_USD = Decimal("1.00")
MAX_ALLOWED_TIMEOUT_SECONDS = 300.0
MAX_PROMPT_BYTES = 65_536
MAX_SCHEMA_BYTES = 32_768
PERMISSION_MODE = "dontAsk"
EFFORT_LEVEL = "low"
SYSTEM_PROMPT = (
    "You are a bounded advisory classifier. Use only the user-supplied facts. "
    "Do not claim that actions were executed, do not infer authority, and return "
    "exactly one JSON value matching the supplied schema."
)
FULL_MODEL_ID_PATTERN = re.compile(
    r"claude-[a-z0-9]+(?:-[a-z0-9]+)*-(?P<version>\d{8})"
)


class HeadlessError(ValueError):
    """Raised when an invocation cannot safely satisfy the bounded contract."""


@dataclass(frozen=True)
class Bounds:
    model: str
    max_turns: int = DEFAULT_MAX_TURNS
    max_budget_usd: Decimal = DEFAULT_MAX_BUDGET_USD
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    def validate(self) -> None:
        if not self.model.strip():
            raise HeadlessError("model must not be empty")
        model_match = FULL_MODEL_ID_PATTERN.fullmatch(self.model)
        if model_match is None:
            raise HeadlessError("model must be a full Claude model ID, not an alias")
        try:
            datetime.strptime(model_match.group("version"), "%Y%m%d")
        except ValueError as error:
            raise HeadlessError(
                "model must be a full Claude model ID with a valid version date"
            ) from error
        if not 1 <= self.max_turns <= MAX_ALLOWED_TURNS:
            raise HeadlessError(
                f"max turns must be between 1 and {MAX_ALLOWED_TURNS}"
            )
        if (
            not self.max_budget_usd.is_finite()
            or not Decimal("0") < self.max_budget_usd <= MAX_ALLOWED_BUDGET_USD
        ):
            raise HeadlessError(
                "budget must be finite, greater than 0, and at most "
                f"{MAX_ALLOWED_BUDGET_USD} USD"
            )
        if not 0 < self.timeout_seconds <= MAX_ALLOWED_TIMEOUT_SECONDS:
            raise HeadlessError(
                "timeout must be greater than 0 and at most "
                f"{MAX_ALLOWED_TIMEOUT_SECONDS:g} seconds"
            )


@dataclass(frozen=True)
class InvocationOutcome:
    exit_code: int
    status: str
    receipt: dict[str, Any]
    structured_output: dict[str, Any] | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_bounded_utf8(path: Path, *, limit: int, label: str) -> tuple[bytes, str]:
    try:
        raw = path.read_bytes()
    except OSError as error:
        raise HeadlessError(f"could not read {label} file {path}: {error}") from error
    if len(raw) > limit:
        raise HeadlessError(f"{label} exceeds the {limit}-byte limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise HeadlessError(f"{label} must be UTF-8") from error
    return raw, text


def load_inputs(prompt_path: Path, schema_path: Path) -> tuple[bytes, str, bytes, dict[str, Any]]:
    prompt_raw, prompt = read_bounded_utf8(
        prompt_path, limit=MAX_PROMPT_BYTES, label="prompt"
    )
    if not prompt.strip():
        raise HeadlessError("prompt must not be empty")

    schema_raw, schema_text = read_bounded_utf8(
        schema_path, limit=MAX_SCHEMA_BYTES, label="schema"
    )
    try:
        schema = json.loads(schema_text)
    except json.JSONDecodeError as error:
        raise HeadlessError(f"schema is not valid JSON: {error}") from error
    if not isinstance(schema, dict) or schema.get("type") != "object":
        raise HeadlessError("schema root must be a JSON object with type=object")
    return prompt_raw, prompt, schema_raw, schema


def compact_decimal(value: Decimal) -> str:
    rendered = format(value, "f")
    return rendered.rstrip("0").rstrip(".") if "." in rendered else rendered


def build_command(
    claude_command: str,
    bounds: Bounds,
    schema: dict[str, Any],
) -> list[str]:
    bounds.validate()
    return [
        claude_command,
        "--safe-mode",
        "--no-session-persistence",
        "--permission-mode",
        PERMISSION_MODE,
        "--tools",
        "",
        "--model",
        bounds.model,
        "--effort",
        EFFORT_LEVEL,
        "--max-turns",
        str(bounds.max_turns),
        "--max-budget-usd",
        compact_decimal(bounds.max_budget_usd),
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(schema, ensure_ascii=False, separators=(",", ":")),
        "--system-prompt",
        SYSTEM_PROMPT,
        "--print",
    ]


def process_creation_kwargs() -> dict[str, Any]:
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


def terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """Best-effort termination of the isolated process group after timeout."""

    if process.poll() is not None:
        return
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            pass
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass


def probe_claude_version(claude_command: str) -> str | None:
    try:
        completed = subprocess.run(
            [claude_command, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    version = completed.stdout.strip()
    return version or None


def provider_metadata(envelope: dict[str, Any]) -> dict[str, Any]:
    allowed = (
        "subtype",
        "is_error",
        "duration_ms",
        "duration_api_ms",
        "num_turns",
        "total_cost_usd",
        "usage",
        "modelUsage",
        "permission_denials",
    )
    return {key: envelope[key] for key in allowed if key in envelope}


def parse_provider_envelope(stdout: str) -> dict[str, Any] | None:
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    return envelope if isinstance(envelope, dict) else None


def provider_error_category(envelope: dict[str, Any]) -> str:
    result = envelope.get("result")
    if not isinstance(result, str):
        return "unspecified"
    normalized = result.lower()
    categories = (
        ("max_turns", ("max turns", "maximum turns")),
        ("budget", ("budget", "cost limit")),
        ("authentication", ("authentication", "not logged in", "unauthorized")),
        ("rate_limit", ("rate limit", "too many requests")),
        ("model", ("model",)),
        ("schema", ("schema", "structured output")),
    )
    for category, markers in categories:
        if any(marker in normalized for marker in markers):
            return category
    return "unspecified"


def provider_boundary_error(envelope: dict[str, Any], bounds: Bounds) -> str | None:
    model_usage = envelope.get("modelUsage")
    if not isinstance(model_usage, dict) or not model_usage:
        return "provider did not report modelUsage"
    actual_models = set(model_usage)
    if actual_models != {bounds.model}:
        return (
            f"provider used models {sorted(actual_models)!r}; "
            f"expected only {bounds.model!r}"
        )

    total_cost = envelope.get("total_cost_usd")
    try:
        actual_cost = Decimal(str(total_cost))
    except (InvalidOperation, TypeError):
        return "provider did not report a numeric total_cost_usd"
    if not actual_cost.is_finite() or actual_cost < Decimal("0"):
        return "provider total_cost_usd must be finite and non-negative"
    if actual_cost > bounds.max_budget_usd:
        return (
            f"provider reported cost {actual_cost} above "
            f"the {bounds.max_budget_usd} USD limit"
        )
    return None


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporary, path)


def make_receipt_base(
    *,
    started_at: str,
    bounds: Bounds,
    claude_version: str | None,
    prompt_raw: bytes,
    schema_raw: bytes,
) -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "startedAt": started_at,
        "claudeVersion": claude_version,
        "bounds": {
            "model": bounds.model,
            "maxTurns": bounds.max_turns,
            "maxBudgetUsd": compact_decimal(bounds.max_budget_usd),
            "timeoutSeconds": bounds.timeout_seconds,
            "permissionMode": PERMISSION_MODE,
            "effort": EFFORT_LEVEL,
            "tools": [],
            "safeMode": True,
            "sessionPersistence": False,
        },
        "input": {
            "promptBytes": len(prompt_raw),
            "promptSha256": sha256_bytes(prompt_raw),
            "schemaBytes": len(schema_raw),
            "schemaSha256": sha256_bytes(schema_raw),
        },
    }


def invoke(
    *,
    prompt_raw: bytes,
    prompt: str,
    schema_raw: bytes,
    schema: dict[str, Any],
    bounds: Bounds,
    result_path: Path,
    receipt_path: Path,
    claude_command: str = "claude",
) -> InvocationOutcome:
    bounds.validate()
    if result_path.resolve() == receipt_path.resolve():
        raise HeadlessError("result and receipt paths must be different")

    started_at = utc_now()
    started_clock = time.monotonic()
    version = probe_claude_version(claude_command)
    receipt = make_receipt_base(
        started_at=started_at,
        bounds=bounds,
        claude_version=version,
        prompt_raw=prompt_raw,
        schema_raw=schema_raw,
    )
    command = build_command(claude_command, bounds, schema)

    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            **process_creation_kwargs(),
        )
    except OSError as error:
        receipt.update(
            {
                "status": "command_not_found",
                "finishedAt": utc_now(),
                "elapsedSeconds": round(time.monotonic() - started_clock, 3),
                "error": str(error),
            }
        )
        write_json_atomic(receipt_path, receipt)
        return InvocationOutcome(3, "command_not_found", receipt, None)

    try:
        stdout, _stderr = process.communicate(
            input=prompt, timeout=bounds.timeout_seconds
        )
    except subprocess.TimeoutExpired:
        terminate_process_tree(process)
        stdout, _stderr = process.communicate()
        receipt.update(
            {
                "status": "timed_out",
                "finishedAt": utc_now(),
                "elapsedSeconds": round(time.monotonic() - started_clock, 3),
                "processExitCode": process.returncode,
            }
        )
        write_json_atomic(receipt_path, receipt)
        return InvocationOutcome(4, "timed_out", receipt, None)

    elapsed = round(time.monotonic() - started_clock, 3)
    if process.returncode != 0:
        receipt.update(
            {
                "status": "provider_failed",
                "finishedAt": utc_now(),
                "elapsedSeconds": elapsed,
                "processExitCode": process.returncode,
            }
        )
        failure_envelope = parse_provider_envelope(stdout)
        if failure_envelope is not None:
            receipt["provider"] = provider_metadata(failure_envelope)
            receipt["providerErrorCategory"] = provider_error_category(failure_envelope)
        write_json_atomic(receipt_path, receipt)
        return InvocationOutcome(5, "provider_failed", receipt, None)

    envelope = parse_provider_envelope(stdout)
    if envelope is None:
        try:
            json.loads(stdout)
        except json.JSONDecodeError as error:
            detail = str(error)
        else:
            detail = "provider JSON envelope was not an object"
        receipt.update(
            {
                "status": "invalid_provider_output",
                "finishedAt": utc_now(),
                "elapsedSeconds": elapsed,
                "processExitCode": process.returncode,
                "error": f"provider stdout was not a JSON object: {detail}",
            }
        )
        write_json_atomic(receipt_path, receipt)
        return InvocationOutcome(6, "invalid_provider_output", receipt, None)

    structured_output = envelope.get("structured_output")
    error_message = None
    if envelope.get("is_error") is True:
        error_message = "provider returned is_error=true"
    elif not isinstance(structured_output, dict):
        error_message = "provider did not return an object in structured_output"
    else:
        error_message = provider_boundary_error(envelope, bounds)

    if error_message is not None:
        receipt.update(
            {
                "status": "invalid_provider_output",
                "finishedAt": utc_now(),
                "elapsedSeconds": elapsed,
                "processExitCode": process.returncode,
                "error": error_message,
            }
        )
        receipt["provider"] = provider_metadata(envelope)
        write_json_atomic(receipt_path, receipt)
        return InvocationOutcome(6, "invalid_provider_output", receipt, None)

    assert isinstance(envelope, dict)
    assert isinstance(structured_output, dict)
    receipt.update(
        {
            "status": "succeeded",
            "finishedAt": utc_now(),
            "elapsedSeconds": elapsed,
            "processExitCode": process.returncode,
            "provider": provider_metadata(envelope),
        }
    )
    write_json_atomic(result_path, structured_output)
    write_json_atomic(receipt_path, receipt)
    return InvocationOutcome(0, "succeeded", receipt, structured_output)


def decimal_argument(value: str) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise argparse.ArgumentTypeError("must be a decimal number") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--schema-file", type=Path, required=True)
    parser.add_argument("--result-file", type=Path, required=True)
    parser.add_argument("--receipt-file", type=Path, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-turns", type=int, default=DEFAULT_MAX_TURNS)
    parser.add_argument(
        "--max-budget-usd", type=decimal_argument, default=DEFAULT_MAX_BUDGET_USD
    )
    parser.add_argument(
        "--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS
    )
    parser.add_argument(
        "--claude-command",
        default="claude",
        help="Claude executable name or path (default: claude)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        bounds = Bounds(
            model=args.model,
            max_turns=args.max_turns,
            max_budget_usd=args.max_budget_usd,
            timeout_seconds=args.timeout_seconds,
        )
        bounds.validate()
        prompt_raw, prompt, schema_raw, schema = load_inputs(
            args.prompt_file, args.schema_file
        )
        outcome = invoke(
            prompt_raw=prompt_raw,
            prompt=prompt,
            schema_raw=schema_raw,
            schema=schema,
            bounds=bounds,
            result_path=args.result_file,
            receipt_path=args.receipt_file,
            claude_command=args.claude_command,
        )
    except HeadlessError as error:
        print(f"claude-headless: {error}", file=sys.stderr)
        return 2

    if outcome.exit_code == 0:
        print(f"wrote {args.result_file} and {args.receipt_file}")
    else:
        print(
            f"claude-headless: {outcome.status}; receipt: {args.receipt_file}",
            file=sys.stderr,
        )
    return outcome.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
