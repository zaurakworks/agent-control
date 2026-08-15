#!/usr/bin/env python3
"""Build a point-in-time operations report from GitHub and Orca."""

from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
import time as time_module
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence
from zoneinfo import ZoneInfo


TOOLS_ROOT = Path(__file__).resolve().parents[1]
if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from report_formats import (  # noqa: E402
    MetricsView,
    parse_view_timestamp,
    write_current,
)


REVIEW_TEXT = re.compile(r"审阅|review|建议合并|建议修改|建议回退", re.IGNORECASE)


class CollectionError(RuntimeError):
    """Raised when a source cannot be collected without guessing."""


@dataclass(frozen=True)
class Window:
    day: date
    timezone_name: str
    start: datetime
    end: datetime
    snapshot_at: datetime

    def contains(self, value: datetime | None) -> bool:
        return value is not None and self.start <= value < min(self.end, self.snapshot_at)


def parse_timestamp(value: str | None, *, assume_utc: bool = False) -> datetime | None:
    if not value:
        return None
    normalized = value.strip().replace(" ", "T", 1)
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        if not assume_utc:
            raise ValueError(f"timestamp has no timezone: {value}")
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def make_window(day_text: str, timezone_name: str, snapshot_text: str | None) -> Window:
    day = date.fromisoformat(day_text)
    zone = ZoneInfo(timezone_name)
    start = datetime.combine(day, time.min, zone).astimezone(timezone.utc)
    end = datetime.combine(day.fromordinal(day.toordinal() + 1), time.min, zone).astimezone(
        timezone.utc
    )
    snapshot_at = parse_timestamp(snapshot_text) if snapshot_text else datetime.now(timezone.utc)
    assert snapshot_at is not None
    if snapshot_at <= start:
        raise ValueError("snapshot-at must be after the reporting window starts")
    return Window(day, timezone_name, start, end, min(snapshot_at, end))


def run_json(command: Sequence[str]) -> Any:
    completed: subprocess.CompletedProcess[str] | None = None
    for attempt in range(3):
        try:
            completed = subprocess.run(
                list(command), check=True, capture_output=True, text=True, encoding="utf-8"
            )
            break
        except FileNotFoundError as error:
            raise CollectionError(f"required command not found: {command[0]}") from error
        except subprocess.CalledProcessError as error:
            detail = (error.stderr or error.stdout or "no output").strip()
            transient = any(
                token in detail.lower()
                for token in ("eof", "timeout", "timed out", "502", "503", "connection reset")
            )
            if transient and attempt < 2:
                time_module.sleep(0.5 * (attempt + 1))
                continue
            raise CollectionError(f"command failed ({' '.join(command)}): {detail}") from error
    assert completed is not None
    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise CollectionError(f"command did not return JSON: {' '.join(command)}") from error


def gh_api(endpoint: str, *, paginate: bool = False, fields: dict[str, str] | None = None) -> Any:
    command = ["gh", "api"]
    if fields:
        command.extend(["-X", "GET"])
    if paginate:
        command.extend(["--paginate", "--slurp"])
    command.append(endpoint)
    for key, value in (fields or {}).items():
        command.extend(["-f", f"{key}={value}"])
    payload = run_json(command)
    if paginate:
        return [row for page in payload for row in page]
    return payload


def search_items(repo: str, qualifier: str, window: Window) -> list[dict[str, Any]]:
    # A local day can straddle two UTC dates. Search both candidate dates and
    # let the caller apply the exact timestamp window.
    utc_dates = {
        window.start.date(),
        (window.end - timedelta(microseconds=1)).date(),
    }
    items: dict[int, dict[str, Any]] = {}
    for utc_day in sorted(utc_dates):
        response = gh_api(
            "search/issues",
            fields={"q": f"repo:{repo} {qualifier}{utc_day.isoformat()}", "per_page": "100"},
        )
        if response.get("total_count", 0) > 100:
            raise CollectionError(
                f"GitHub search exceeded the supported 100-result UTC-day bound: "
                f"{qualifier}{utc_day.isoformat()}"
            )
        items.update({item["number"]: item for item in response.get("items", [])})
    return list(items.values())


def collect_pr(repo: str, number: int) -> dict[str, Any]:
    pull = gh_api(f"repos/{repo}/pulls/{number}")
    issue_comments = gh_api(f"repos/{repo}/issues/{number}/comments?per_page=100", paginate=True)
    reviews = gh_api(f"repos/{repo}/pulls/{number}/reviews?per_page=100", paginate=True)
    inline_comments = gh_api(f"repos/{repo}/pulls/{number}/comments?per_page=100", paginate=True)

    signals: list[dict[str, str]] = []
    for review in reviews:
        if review.get("submitted_at"):
            signals.append(
                {
                    "at": review["submitted_at"],
                    "kind": "formal_review",
                    "url": review.get("html_url", pull["html_url"]),
                }
            )
    for comment in inline_comments:
        signals.append(
            {
                "at": comment["created_at"],
                "kind": "inline_review_comment",
                "url": comment.get("html_url", pull["html_url"]),
            }
        )
    for comment in issue_comments:
        if REVIEW_TEXT.search(comment.get("body", "")):
            signals.append(
                {
                    "at": comment["created_at"],
                    "kind": "review_conversation_comment",
                    "url": comment.get("html_url", pull["html_url"]),
                }
            )
    signals.sort(key=lambda item: parse_timestamp(item["at"]) or datetime.max.replace(tzinfo=timezone.utc))
    return {
        "number": number,
        "title": pull["title"],
        "url": pull["html_url"],
        "created_at": pull["created_at"],
        "merged_at": pull.get("merged_at"),
        "first_review_signal": signals[0] if signals else None,
    }


def seconds_between(start: str, end: str) -> float:
    start_at = parse_timestamp(start, assume_utc=True)
    end_at = parse_timestamp(end, assume_utc=True)
    assert start_at is not None and end_at is not None
    return (end_at - start_at).total_seconds()


def summarize_seconds(values: Iterable[float]) -> dict[str, float | int | None]:
    ordered = sorted(values)
    if not ordered:
        return {"count": 0, "median_seconds": None, "p90_seconds": None, "max_seconds": None}
    p90_index = max(0, math.ceil(0.9 * len(ordered)) - 1)
    return {
        "count": len(ordered),
        "median_seconds": statistics.median(ordered),
        "p90_seconds": ordered[p90_index],
        "max_seconds": ordered[-1],
    }


def collect_github(repo: str, window: Window) -> dict[str, Any]:
    issue_items = search_items(repo, "is:issue created:", window)
    created_pr_items = search_items(repo, "is:pr created:", window)
    merged_pr_items = search_items(repo, "is:pr merged:", window)
    updated_pr_items = search_items(repo, "is:pr updated:", window)

    issues_created = [item for item in issue_items if window.contains(parse_timestamp(item["created_at"]))]
    prs_created = [item for item in created_pr_items if window.contains(parse_timestamp(item["created_at"]))]

    repo_comments = gh_api(
        f"repos/{repo}/issues/comments?since={window.start.isoformat().replace('+00:00', 'Z')}&per_page=100",
        paginate=True,
    )
    comments_in_window = [
        item for item in repo_comments if window.contains(parse_timestamp(item["created_at"]))
    ]

    pr_numbers = {
        item["number"] for item in created_pr_items + merged_pr_items + updated_pr_items
    }
    ordered_pr_numbers = sorted(pr_numbers)
    with ThreadPoolExecutor(max_workers=min(8, len(ordered_pr_numbers) or 1)) as executor:
        pulls = list(executor.map(lambda number: collect_pr(repo, number), ordered_pr_numbers))
    review_rows: list[dict[str, Any]] = []
    merge_rows: list[dict[str, Any]] = []
    for pull in pulls:
        signal = pull["first_review_signal"]
        if signal and window.contains(parse_timestamp(signal["at"])):
            review_rows.append(
                {
                    **pull,
                    "reviewed_at": signal["at"],
                    "review_kind": signal["kind"],
                    "review_url": signal["url"],
                    "seconds": seconds_between(pull["created_at"], signal["at"]),
                }
            )
        if window.contains(parse_timestamp(pull["merged_at"])):
            merge_rows.append(
                {
                    **pull,
                    "seconds": seconds_between(pull["created_at"], pull["merged_at"]),
                }
            )

    return {
        "issues_created_count": len(issues_created),
        "prs_created_count": len(prs_created),
        "prs_merged_count": len(merge_rows),
        "issue_pr_comments_count": len(comments_in_window),
        "review_turnaround": summarize_seconds(row["seconds"] for row in review_rows),
        "review_rows": review_rows,
        "merge_turnaround": summarize_seconds(row["seconds"] for row in merge_rows),
        "merge_rows": merge_rows,
    }


def orca_json(arguments: Sequence[str]) -> Any:
    return run_json(["orca", "orchestration", *arguments, "--json"])


def unwrap_orca(payload: dict[str, Any], command: str) -> dict[str, Any]:
    if not payload.get("ok"):
        error = payload.get("error", {})
        raise CollectionError(f"Orca {command} failed: {error.get('code')}: {error.get('message')}")
    return payload.get("result", {})


def worker_done_at(task: dict[str, Any]) -> str | None:
    result = task.get("result")
    if not result:
        return None
    try:
        parsed = json.loads(result) if isinstance(result, str) else result
    except json.JSONDecodeError:
        return None
    if parsed.get("provenance") != "worker_report" or not parsed.get("outcome"):
        return None
    return parsed.get("completedAt")


def summarize_orca_records(records: list[dict[str, Any]], window: Window) -> dict[str, Any]:
    dispatched_today = [
        row
        for row in records
        if window.contains(parse_timestamp(row["dispatched_at"], assume_utc=True))
    ]
    returned_today = [
        row
        for row in records
        if window.contains(parse_timestamp(row["worker_done_at"], assume_utc=True))
    ]
    returned_dispatched_today = [
        row
        for row in dispatched_today
        if window.contains(parse_timestamp(row["worker_done_at"], assume_utc=True))
    ]
    latencies = [
        seconds_between(row["dispatched_at"], row["worker_done_at"])
        for row in returned_today
        if row["dispatched_at"] and row["worker_done_at"]
    ]
    return {
        "dispatch_count": len(dispatched_today),
        "worker_done_count": len(returned_today),
        "dispatch_cohort_returned_count": len(returned_dispatched_today),
        "dispatch_cohort_return_rate": (
            len(returned_dispatched_today) / len(dispatched_today) if dispatched_today else None
        ),
        "delivery_return_latency": summarize_seconds(latencies),
        **summarize_inflight_peak(records, window),
    }


def summarize_inflight_peak(records: list[dict[str, Any]], window: Window) -> dict[str, Any]:
    """Calculate peak Dispatch concurrency from durable Task/Dispatch timestamps."""
    boundary = min(window.end, window.snapshot_at)
    events: list[tuple[datetime, int]] = []
    for row in records:
        started_at = parse_timestamp(row.get("dispatched_at"), assume_utc=True)
        if started_at is None:
            continue
        completed_candidates = [
            parse_timestamp(row.get(field), assume_utc=True)
            for field in ("dispatch_completed_at", "task_completed_at", "worker_done_at")
            if row.get(field)
        ]
        completed_at = min(completed_candidates) if completed_candidates else boundary
        active_start = max(started_at, window.start)
        active_end = min(completed_at, boundary)
        if active_start >= active_end:
            continue
        events.append((active_start, 1))
        events.append((active_end, -1))

    # End events precede start events at the same instant: intervals are [start, end).
    events.sort(key=lambda event: (event[0], event[1]))
    running = 0
    peak = 0
    peak_at: datetime | None = None
    for observed_at, delta in events:
        running += delta
        if running > peak:
            peak = running
            peak_at = observed_at
    return {
        "inflight_peak": peak,
        "inflight_peak_at": peak_at.isoformat() if peak_at else None,
    }


def collect_orca_record(
    run_id: str, task: dict[str, Any]
) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    try:
        dispatch = unwrap_orca(
            orca_json(["dispatch-show", "--task", task["id"]]), "dispatch-show"
        ).get("dispatch")
    except CollectionError as error:
        return None, [f"{task['id']}: {error}"]
    if not dispatch:
        return None, [f"{task['id']}: no current Dispatch is available"]
    try:
        worker_result = unwrap_orca(
            orca_json(["worker-show", "--dispatch", dispatch["id"]]), "worker-show"
        )
    except CollectionError as error:
        detail = (
            "worker details unavailable after release (dispatch_not_found)"
            if "dispatch_not_found" in str(error)
            else str(error)
        )
        errors.append(f"{task['id']}/{dispatch['id']}: {detail}")
        worker_result = {}
    return (
        {
            "run_id": run_id,
            "task_id": task["id"],
            "task_title": task.get("task_title") or task.get("display_name"),
            "task_status": task.get("status"),
            "task_completed_at": task.get("completed_at"),
            "dispatch_id": dispatch["id"],
            "dispatch_status": dispatch.get("status"),
            "dispatched_at": dispatch.get("dispatched_at"),
            "dispatch_completed_at": dispatch.get("completed_at"),
            "worker_done_at": worker_done_at(task),
            "worker_state": worker_result.get("worker", {}).get("state", "unavailable"),
            "worker_stage": worker_result.get("worker", {}).get("stage"),
            "observation_status": worker_result.get("observation", {}).get(
                "status", "unavailable"
            ),
        },
        errors,
    )


def collect_orca(run_ids: list[str], window: Window) -> dict[str, Any]:
    runs = unwrap_orca(orca_json(["run-list"]), "run-list").get("runs", [])
    run_by_id = {run["id"]: run for run in runs}
    unknown = sorted(set(run_ids) - set(run_by_id))
    if unknown:
        raise CollectionError(f"Orca run IDs not found: {', '.join(unknown)}")

    task_rows: list[tuple[str, dict[str, Any]]] = []
    for run_id in run_ids:
        tasks = unwrap_orca(orca_json(["task-list", "--run", run_id]), "task-list").get(
            "tasks", []
        )
        task_rows.extend((run_id, task) for task in tasks)

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=min(8, len(task_rows) or 1)) as executor:
        results = executor.map(lambda row: collect_orca_record(*row), task_rows)
        for record, record_errors in results:
            if record:
                records.append(record)
            errors.extend(record_errors)

    run_coverage = [
        {
            "id": run_id,
            "objective": run_by_id[run_id].get("objective"),
            "created_at": run_by_id[run_id].get("created_at"),
        }
        for run_id in run_ids
    ]
    return {
        "run_coverage": run_coverage,
        "records": records,
        **summarize_orca_records(records, window),
        "task_states": dict(Counter(row["task_status"] for row in records)),
        "dispatch_states": dict(Counter(row["dispatch_status"] for row in records)),
        "worker_states": dict(Counter(row["worker_state"] for row in records)),
        "worker_observations": dict(Counter(row["observation_status"] for row in records)),
        "collection_errors": errors,
    }


def load_annotations(path: Path, window: Window) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        raise CollectionError("annotations schema_version must be 1")
    if data.get("date") != window.day.isoformat():
        raise CollectionError("annotations date does not match report date")
    for collection in ("correction_events", "worker_idle_events"):
        ids: set[str] = set()
        for event in data.get(collection, []):
            if not event.get("id") or event["id"] in ids:
                raise CollectionError(f"{collection} has a missing or duplicate id")
            if not event.get("category") or not event.get("label") or not event.get("sources"):
                raise CollectionError(
                    f"{collection}/{event['id']} lacks category, label, or sources"
                )
            ids.add(event["id"])
    corrections = data.get("correction_events", [])
    idle = data.get("worker_idle_events", [])
    dispatch_races = data.get("dispatch_race_events", [])
    race_ids: set[str] = set()
    race_dispatch_ids: set[str] = set()
    race_categories: Counter[str] = Counter()
    included_races: list[dict[str, Any]] = []
    for event in dispatch_races:
        event_id = event.get("id")
        affected_count = event.get("affected_count")
        ignition_count = event.get("ignition_count")
        dispatch_ids = event.get("dispatch_ids", [])
        if not event_id or event_id in race_ids:
            raise CollectionError("dispatch_race_events has a missing or duplicate id")
        if (
            not event.get("category")
            or not event.get("label")
            or not event.get("recorded_at")
            or not event.get("sources")
        ):
            raise CollectionError(
                f"dispatch_race_events/{event_id} lacks category, label, recorded_at, or sources"
            )
        if (
            isinstance(affected_count, bool)
            or not isinstance(affected_count, int)
            or affected_count < 1
            or isinstance(ignition_count, bool)
            or not isinstance(ignition_count, int)
            or ignition_count < 0
        ):
            raise CollectionError(
                f"dispatch_race_events/{event_id} counts must be non-negative integers "
                "with affected_count >= 1"
            )
        if (
            not isinstance(dispatch_ids, list)
            or any(not isinstance(dispatch_id, str) or not dispatch_id for dispatch_id in dispatch_ids)
            or len(set(dispatch_ids)) != len(dispatch_ids)
            or len(dispatch_ids) > affected_count
        ):
            raise CollectionError(
                f"dispatch_race_events/{event_id} dispatch_ids must be unique strings and "
                "cannot exceed affected_count"
            )
        duplicated_dispatches = race_dispatch_ids.intersection(dispatch_ids)
        if duplicated_dispatches:
            raise CollectionError(
                "dispatch_race_events dispatch ids appear in multiple events: "
                f"{', '.join(sorted(duplicated_dispatches))}"
            )
        recorded_at = parse_timestamp(event["recorded_at"])
        assert recorded_at is not None
        if not window.start <= recorded_at < window.end:
            raise CollectionError(
                f"dispatch_race_events/{event_id} recorded_at is outside the report date"
            )
        race_ids.add(event_id)
        race_dispatch_ids.update(dispatch_ids)
        if window.contains(recorded_at):
            included_races.append(event)
            race_categories[event["category"]] += affected_count

    regression_checks = data.get("regression_checks", [])
    regression_ids: set[str] = set()
    regression_sample_ids: set[str] = set()
    allowed_check_types = {"automated", "manual", "hybrid"}
    for check in regression_checks:
        check_id = check.get("id")
        if not check_id or check_id in regression_ids:
            raise CollectionError("regression_checks has a missing or duplicate id")
        if (
            not check.get("category")
            or not check.get("label")
            or check.get("check_type") not in allowed_check_types
            or not check.get("expected")
            or not check.get("sources")
        ):
            raise CollectionError(
                f"regression_checks/{check_id} lacks category, label, check_type, expected, or sources"
            )
        sample_ids = check.get("sample_ids")
        if (
            not isinstance(sample_ids, list)
            or not sample_ids
            or any(not isinstance(sample_id, str) or not sample_id.strip() for sample_id in sample_ids)
            or len(set(sample_ids)) != len(sample_ids)
        ):
            raise CollectionError(
                f"regression_checks/{check_id} sample_ids must be a non-empty unique string list"
            )
        duplicated_samples = regression_sample_ids.intersection(sample_ids)
        if duplicated_samples:
            raise CollectionError(
                f"regression_checks sample ids appear in multiple checks: "
                f"{', '.join(sorted(duplicated_samples))}"
            )
        procedure = check.get("procedure")
        if (
            not isinstance(procedure, list)
            or not procedure
            or any(not isinstance(step, str) or not step.strip() for step in procedure)
        ):
            raise CollectionError(
                f"regression_checks/{check_id} procedure must be a non-empty string list"
            )
        regression_ids.add(check_id)
        regression_sample_ids.update(sample_ids)
    manual_baseline = data.get("manual_baseline")
    if manual_baseline is not None:
        baseline_dispatches = manual_baseline.get("dispatch_count")
        baseline_done = manual_baseline.get("worker_done_count")
        baseline_rate = manual_baseline.get("success_rate")
        if (
            not manual_baseline.get("label")
            or not manual_baseline.get("sources")
            or isinstance(baseline_dispatches, bool)
            or not isinstance(baseline_dispatches, int)
            or baseline_dispatches < 0
            or isinstance(baseline_done, bool)
            or not isinstance(baseline_done, int)
            or baseline_done < 0
            or isinstance(baseline_rate, bool)
            or not isinstance(baseline_rate, (int, float))
            or not 0 <= baseline_rate <= 1
        ):
            raise CollectionError(
                "manual_baseline requires label, sources, non-negative counts, and success_rate 0..1"
            )

    return {
        "correction_events": corrections,
        "correction_count": len(corrections),
        "correction_categories": dict(Counter(event["category"] for event in corrections)),
        "worker_idle_events": idle,
        "worker_idle_event_count": len(idle),
        "dispatch_race_events": included_races,
        "dispatch_race_count": sum(event["affected_count"] for event in included_races),
        "ignition_count": sum(event["ignition_count"] for event in included_races),
        "dispatch_race_categories": dict(race_categories),
        "regression_checks": regression_checks,
        "regression_check_count": len(regression_checks),
        "regression_sample_count": len(regression_sample_ids),
        "regression_check_types": dict(
            Counter(check["check_type"] for check in regression_checks)
        ),
        "manual_baseline": manual_baseline,
        "notes": data.get("notes", []),
    }


def duration(value: float | int | None) -> str:
    if value is None:
        return "—"
    seconds = int(round(value))
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


def stats_text(stats: dict[str, Any]) -> str:
    if not stats["count"]:
        return "无可计算样本"
    return (
        f"n={stats['count']}；中位 {duration(stats['median_seconds'])}；"
        f"P90 {duration(stats['p90_seconds'])}；最大 {duration(stats['max_seconds'])}"
    )


def json_compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\r", " ").replace("\n", "<br>")


def render_report(data: dict[str, Any], reproduction: str) -> str:
    github = data["github"]
    orca = data["orca"]
    annotations = data["annotations"]
    coverage = ", ".join(item["id"] for item in orca["run_coverage"])
    rate = orca["dispatch_cohort_return_rate"]
    rate_text = "—" if rate is None else f"{rate:.1%}"
    peak_at = orca["inflight_peak_at"] or "—"
    lines = [
        f"# Agent 系统运营日报｜{data['date']}",
        "",
        f"> 时区：`{data['timezone']}`；快照：`{data['snapshot_at']}`；触发：`{data['trigger']}`；本报告是当日截至快照时刻的部分日快照。",
        "",
        "## 结论先行",
        "",
        f"- Orca 覆盖的 Run 共派发 **{orca['dispatch_count']}** 个当前可见 Dispatch；"
        f"收到 **{orca['worker_done_count']}** 个 `worker_done`。派发同日队列截至快照回流率为 **{rate_text}**，"
        f"交付回流时延为 {stats_text(orca['delivery_return_latency'])}。",
        f"- Dispatch 在跑峰值 **{orca['inflight_peak']}**（首次达到于 `{peak_at}`）；"
        f"已登记 composer-pending 竞态 **{annotations['dispatch_race_count']}** 次，"
        f"人工点火 **{annotations['ignition_count']}** 次。",
        f"- GitHub 当日活动：Issue **{github['issues_created_count']}**、PR **{github['prs_created_count']}**、"
        f"合并 PR **{github['prs_merged_count']}**、Issue/PR 会话评论 **{github['issue_pr_comments_count']}**；"
        f"审阅周转 {stats_text(github['review_turnaround'])}；"
        f"合并周转 {stats_text(github['merge_turnaround'])}。",
        f"- 已登记、去重后的负责人纠偏 **{annotations['correction_count']}** 次；"
        f"worker 空转事件 **{annotations['worker_idle_event_count']}** 次。两者只计人工登记证据，不从措辞猜测新事件。",
        f"- 当日错误样本已形成 **{annotations['regression_check_count']}** 个结构化回归项，"
        f"覆盖 **{annotations['regression_sample_count']}** 个样本；"
        f"复跑类型 {json_compact(annotations['regression_check_types'])}。",
        "",
        "## 产能利用率仪表",
        "",
        "| 指标 | 值 | 可复算定义 |",
        "| --- | ---: | --- |",
        f"| 派发数 | {orca['dispatch_count']} | 所选 Run 中 `dispatched_at` 落入日窗的当前可见 Dispatch 记录 |",
        f"| worker_done 回流数 | {orca['worker_done_count']} | `task.result.provenance=worker_report` 且 `completedAt` 落入日窗 |",
        f"| 同日派发队列回流率 | {rate_text} | 日窗内派发且截至快照已有 worker_done ÷ 日窗内派发 |",
        f"| Dispatch 在跑峰值 | {orca['inflight_peak']} | Task／Dispatch 的派发到完成半开区间重叠峰值；首次达到 `{peak_at}` |",
        f"| composer-pending 竞态 | {annotations['dispatch_race_count']} | annotations 中已登记的受影响 Dispatch 数；分类 {json_compact(annotations['dispatch_race_categories'])} |",
        f"| 人工点火 | {annotations['ignition_count']} | 上述竞态中沿原 Dispatch 补交 Enter 的操作次数 |",
        f"| 交付回流时延 | {stats_text(orca['delivery_return_latency'])} | 派发时间 → worker_done `completedAt`；按完成事件日归组 |",
        f"| 审阅周转 | {stats_text(github['review_turnaround'])} | PR 创建 → 首个正式 review、inline review comment，或含审阅语义的 PR 会话评论；按首次审阅事件日归组 |",
        f"| PR 合并数 | {github['prs_merged_count']} | `merged_at` 落入日窗的 PR |",
        f"| 合并周转 | {stats_text(github['merge_turnaround'])} | PR 创建 → `merged_at`；按合并事件日归组 |",
        f"| worker 空转事件 | {annotations['worker_idle_event_count']} | annotations 中有来源的事件数；批量空转按一次共同触发事件计 |",
        "",
        f"所选 Run：`{coverage}`。采集时当前可见状态（不作历史回放）：任务 {json_compact(orca['task_states'])}；"
        f"Dispatch {json_compact(orca['dispatch_states'])}；Worker {json_compact(orca['worker_states'])}；"
        f"终端观察 {json_compact(orca['worker_observations'])}。",
        "",
        "### 空转事件明细",
        "",
    ]
    for event in annotations["worker_idle_events"]:
        sources = "、".join(f"[来源]({source})" for source in event["sources"])
        lines.append(f"- `{event['id']}`｜{event['label']}｜{sources}")

    lines.extend(["", "### 派发竞态与点火明细", ""])
    for event in annotations["dispatch_race_events"]:
        sources = "、".join(f"[来源]({source})" for source in event["sources"])
        known_dispatches = "、".join(f"`{item}`" for item in event.get("dispatch_ids", []))
        if not known_dispatches:
            known_dispatches = "来源仅保存批次计数，未逐项冻结 ID"
        lines.append(
            f"- `{event['id']}`｜{event['label']}｜受影响 {event['affected_count']}；"
            f"点火 {event['ignition_count']}；{known_dispatches}｜{sources}"
        )

    baseline = annotations["manual_baseline"]
    if baseline:
        dispatch_delta = orca["dispatch_count"] - baseline["dispatch_count"]
        done_delta = orca["worker_done_count"] - baseline["worker_done_count"]
        rate_delta = None if rate is None else (rate - baseline["success_rate"]) * 100
        rate_delta_text = "—" if rate_delta is None else f"{rate_delta:+.1f} 个百分点"
        exact_match = dispatch_delta == 0 and done_delta == 0 and (
            rate_delta is not None and abs(rate_delta) < 0.05
        )
        explanation = (
            "按报告展示精度三项差异为零：自动口径与人工口径使用同一日窗、显式 Run 和当前可见 Dispatch。"
            if exact_match
            else "差异未被自动抹平；优先核对日窗、显式 Run 覆盖、历史重试与当前可见 Dispatch 边界。"
        )
        sources = "、".join(f"[来源]({source})" for source in baseline["sources"])
        lines.extend(
            [
                "",
                "### 人工口径交叉核对",
                "",
                f"- {baseline['label']}：派发 {baseline['dispatch_count']}、回执 {baseline['worker_done_count']}、成功率 {baseline['success_rate']:.1%}；{sources}。",
                f"- 自动口径：派发 {orca['dispatch_count']}、回执 {orca['worker_done_count']}、成功率 {rate_text}。差异：派发 {dispatch_delta:+d}、回执 {done_delta:+d}、成功率 {rate_delta_text}。",
                f"- 解释：{explanation}",
            ]
        )

    lines.extend(
        [
            "",
            "## 交互质量仪表",
            "",
            f"纠偏总数：**{annotations['correction_count']}**。分类：`{json_compact(annotations['correction_categories'])}`。",
            "",
            "| 事件 | 分类 | 已登记事实 | 来源 |",
            "| --- | --- | --- | --- |",
        ]
    )
    for event in annotations["correction_events"]:
        sources = "<br>".join(f"[证据]({source})" for source in event["sources"])
        lines.append(
            f"| `{event['id']}` | `{event['category']}` | {event['label']} | {sources} |"
        )
    lines.extend(["", "登记说明："])
    lines.extend(f"- {note}" for note in annotations["notes"])

    lines.extend(
        [
            "",
            "### 当日错误样本回归清单",
            "",
            "| 回归项 | 分类 | 样本数 | 复跑类型 | 复跑步骤 | 通过判据 | 来源 |",
            "| --- | --- | ---: | --- | --- | --- | --- |",
        ]
    )
    for check in annotations["regression_checks"]:
        procedure = "<br>".join(
            f"{index}. {markdown_cell(step)}"
            for index, step in enumerate(check["procedure"], start=1)
        )
        sources = "<br>".join(f"[证据]({source})" for source in check["sources"])
        lines.append(
            f"| `{check['id']}` {markdown_cell(check['label'])} | `{check['category']}` | "
            f"{len(check['sample_ids'])} | `{check['check_type']}` | {procedure} | "
            f"{markdown_cell(check['expected'])} | {sources} |"
        )

    lines.extend(
        [
            "",
            "## GitHub 活动与周转样本",
            "",
            f"- Issue 创建：{github['issues_created_count']}；PR 创建：{github['prs_created_count']}；Issue/PR 会话评论：{github['issue_pr_comments_count']}。",
            f"- 首次审阅事件样本：{github['review_turnaround']['count']}；合并事件样本：{github['merge_turnaround']['count']}。",
            "",
            "## 口径边界",
            "",
            "- GitHub 计数使用精确 UTC 边界换算后的本地日窗，并截断到快照时刻；工具查询日窗跨越的每个 UTC 日期，搜索日期只用于缩小候选，最终按时间戳再过滤。",
            "- 审阅信号不把任意 PR 评论都算作审阅：仅正式 review、inline review comment，或正文匹配 `审阅|review|建议合并|建议修改|建议回退` 的会话评论。共享 GitHub 账号下无法可靠区分 Agent 身份，因此不猜作者角色。",
            "- Orca 只覆盖显式列出的 Run，且 `dispatch-show` 暴露的是每个 Task 当前可见 Dispatch；更早 Run、低层未登记工作和历史重试不反推。",
            "- 在跑峰值用派发时刻到 Dispatch／Task／worker_done 最早完成时刻的半开区间计算；低层残留 Dispatch 若 Task 已失败，以 Task 完成时刻结束，不把残留记录冒充仍在跑。",
            "- Task／Dispatch／Worker／终端状态是采集时的当前观察，不支持按旧 `--snapshot-at` 回放；冻结快照只约束带时间戳的派发、worker_done 与 GitHub 事件口径。",
        ]
    )
    earliest = min(
        (parse_timestamp(item["created_at"]) for item in orca["run_coverage"] if item.get("created_at")),
        default=None,
    )
    if earliest and earliest > parse_timestamp(data["window_start"]):
        lines.append(
            f"- 所选 Orca Run 最早始于 `{earliest.isoformat()}`，晚于日窗起点；此前活动不在 Orca 仪表覆盖内。"
        )
    if orca["collection_errors"]:
        lines.append(f"- Orca 当前观察缺口：`{json_compact(orca['collection_errors'])}`。")
    lines.extend(
        [
            "- 纠偏、空转与 composer-pending 竞态来自版本化 annotations；工具验证结构、日期、计数、唯一 ID 与非空来源字段，不从自然语言自动发明或拆分事件。`input-missing` 是不同机制，不混入本表竞态计数。",
            "- 本仪表描述观测到的吞吐与周转，不等同于价值、质量、产品采用或长期能力结论。",
            "",
            "## 复算",
            "",
            "```text",
            reproduction,
            "```",
            "",
            "工具会同时重写 JSON 快照与本 Markdown；它是手动触发的一次性进程，不含服务、轮询或计划任务。",
            "",
        ]
    )
    return "\n".join(lines)


def build_current_metrics_view(data: dict[str, Any]) -> MetricsView:
    annotations = data["annotations"]
    orca = data["orca"]
    anomaly_count = (
        annotations["dispatch_race_count"]
        + annotations["worker_idle_event_count"]
        + (1 if orca["collection_errors"] else 0)
    )
    return MetricsView(
        snapshot_at=parse_view_timestamp(data["snapshot_at"], "snapshot_at"),
        anomaly_count=anomaly_count,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="GitHub owner/repository")
    parser.add_argument("--date", required=True, help="Local reporting date (YYYY-MM-DD)")
    parser.add_argument("--timezone", default="America/New_York", help="IANA timezone")
    parser.add_argument("--run-id", action="append", required=True, help="Orca Run ID; repeatable")
    parser.add_argument("--annotations", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-report", type=Path, required=True)
    parser.add_argument(
        "--current-report",
        type=Path,
        help="Also overwrite this stable Markdown view with the same generated report",
    )
    parser.add_argument(
        "--current-json",
        type=Path,
        help="Also write the small, versioned JSON view consumed by ops-console",
    )
    parser.add_argument("--snapshot-at", help="Optional RFC 3339 cutoff for a reproducible snapshot")
    parser.add_argument(
        "--trigger",
        choices=("manual", "tick"),
        default="manual",
        help="Record whether a human or an external tick invoked this one-shot run",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    for executable in ("gh", "orca"):
        if shutil.which(executable) is None:
            raise CollectionError(f"required command not found: {executable}")
    window = make_window(args.date, args.timezone, args.snapshot_at)
    data = {
        "schema_version": 1,
        "date": window.day.isoformat(),
        "timezone": window.timezone_name,
        "window_start": window.start.isoformat(),
        "window_end": window.end.isoformat(),
        "snapshot_at": window.snapshot_at.isoformat(),
        "trigger": args.trigger,
        "github": collect_github(args.repo, window),
        "orca": collect_orca(args.run_id, window),
        "annotations": load_annotations(args.annotations, window),
    }
    reproduction = " ".join(
        [
            "python tools/ops-metrics/ops_metrics.py",
            f"--repo {args.repo}",
            f"--date {args.date}",
            f"--timezone {args.timezone}",
            *(f"--run-id {run_id}" for run_id in args.run_id),
            f"--annotations {args.annotations.as_posix()}",
            f"--output-json {args.output_json.as_posix()}",
            f"--output-report {args.output_report.as_posix()}",
            f"--snapshot-at {window.snapshot_at.isoformat()}",
            f"--trigger {args.trigger}",
        ]
    )
    report = render_report(data, reproduction)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_report.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    args.output_report.write_text(report, encoding="utf-8")
    written = [args.output_json, args.output_report]
    if args.current_report:
        args.current_report.parent.mkdir(parents=True, exist_ok=True)
        args.current_report.write_text(report, encoding="utf-8")
        written.append(args.current_report)
    if args.current_json:
        write_current(args.current_json, build_current_metrics_view(data))
        written.append(args.current_json)
    print("wrote " + ", ".join(str(path) for path in written))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (CollectionError, ValueError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        raise SystemExit(2)
