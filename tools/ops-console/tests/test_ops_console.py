from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).resolve().parents[1] / "ops_console.py"
SPEC = importlib.util.spec_from_file_location("ops_console", MODULE_PATH)
assert SPEC and SPEC.loader
ops_console = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ops_console
SPEC.loader.exec_module(ops_console)

from report_formats import write_current  # noqa: E402


class ParsingTests(unittest.TestCase):
    def test_loads_two_structured_current_views(self) -> None:
        worker = ops_console.WorkerView(
            observed_at=datetime(2026, 8, 13, 12, tzinfo=timezone.utc),
            running_count=2,
            dispatched_count=2,
            active_anomaly_count=0,
        )
        metrics = ops_console.MetricsView(
            snapshot_at=datetime(2026, 8, 13, 12, 1, tzinfo=timezone.utc),
            anomaly_count=1,
        )
        with tempfile.TemporaryDirectory() as directory:
            worker_path = Path(directory) / "worker.json"
            metrics_path = Path(directory) / "metrics.json"
            write_current(worker_path, worker)
            write_current(metrics_path, metrics)
            loaded_worker, loaded_metrics = ops_console.load_current_views(
                worker_path, metrics_path
            )
        self.assertEqual(loaded_worker, worker)
        self.assertEqual(loaded_metrics, metrics)

    def test_counts_only_project_waiting_statuses(self) -> None:
        payload = {
            "items": [
                {"status": "待决定"},
                {"status": "验收中"},
                {"status": "进行中"},
                {"title": "no status"},
            ]
        }
        self.assertEqual(ops_console.count_pending_items(payload), 2)


class RenderingTests(unittest.TestCase):
    def snapshot(
        self,
        *,
        pending_count: int = 1,
        anomaly_count: int = 1,
        active_anomaly_count: int = 0,
    ) -> object:
        return ops_console.ConsoleSnapshot(
            observed_at=datetime(2026, 8, 13, 12, 0, tzinfo=timezone.utc),
            metrics_at=datetime(2026, 8, 13, 12, 1, tzinfo=timezone.utc),
            running_count=2,
            pending_count=pending_count,
            anomaly_count=anomaly_count,
            active_anomaly_count=active_anomaly_count,
        )

    def test_fresh_card_has_required_counts_links_and_limits(self) -> None:
        body = ops_console.render_card(
            self.snapshot(),
            repo="owner/repo",
            sha="a" * 40,
            now=datetime(2026, 8, 13, 12, 10, tzinfo=timezone.utc),
            fresh_minutes=15,
        )
        self.assertIn("状态：🟡 有事项等您决定", body)
        self.assertIn("（超时即视为已失效）", body)
        self.assertNotIn("状态：🔴", body)
        self.assertIn(
            "正在工作的 Worker：2 个｜等您决定：1 项｜"
            "今天异常记录：1 项（当前仍有 0 项）",
            body,
        )
        self.assertIn(
            "有 1 项等您决定；请到 Project 或对应合同 Issue 查看并回复。",
            body,
        )
        self.assertIn(
            "今天记录 1 项运行异常，其中 0 项仍在发生；详情见下方明细。",
            body,
        )
        self.assertNotIn("待决定数", body)
        self.assertNotIn("异常数", body)
        self.assertIn("blob/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/", body)
        self.assertLessEqual(sum(1 for line in body.splitlines() if line.strip()), 10)
        self.assertLessEqual(sum(1 for line in body.splitlines() if line.startswith("- ")), 3)

    def test_historical_anomalies_without_active_anomaly_are_not_red(self) -> None:
        body = ops_console.render_card(
            self.snapshot(pending_count=0, anomaly_count=3),
            repo="owner/repo",
            sha="d" * 40,
            now=datetime(2026, 8, 13, 12, 10, tzinfo=timezone.utc),
            fresh_minutes=15,
        )
        self.assertIn("状态：🟢 正常", body)
        self.assertIn("今天异常记录：3 项（当前仍有 0 项）", body)
        self.assertNotIn("状态：🔴", body)

    def test_current_worker_anomaly_is_red(self) -> None:
        body = ops_console.render_card(
            self.snapshot(
                pending_count=0, anomaly_count=1, active_anomaly_count=1
            ),
            repo="owner/repo",
            sha="e" * 40,
            now=datetime(2026, 8, 13, 12, 10, tzinfo=timezone.utc),
            fresh_minutes=15,
        )
        self.assertIn("状态：🔴 当前有异常", body)
        self.assertIn("今天异常记录：1 项（当前仍有 1 项）", body)
        self.assertIn("今天记录 1 项运行异常，其中 1 项仍在发生", body)

    def test_stale_card_never_presents_counts_as_current(self) -> None:
        body = ops_console.render_card(
            self.snapshot(),
            repo="owner/repo",
            sha="b" * 40,
            now=datetime(2026, 8, 13, 12, 16, tzinfo=timezone.utc),
            fresh_minutes=15,
        )
        self.assertIn("状态：🔴", body)
        self.assertIn("已失效：数据过期，需刷新", body)
        self.assertIn("数据过期，需刷新", body)
        self.assertIn(
            "过期样本：工作的 Worker 2 个｜曾等您决定 1 项｜"
            "当天异常记录 1 项",
            body,
        )
        self.assertIn("请先刷新，再据此行动", body)
        self.assertNotIn("正在工作的 Worker：2", body)

    def test_failure_card_invalidates_every_count(self) -> None:
        body = ops_console.render_unavailable(repo="owner/repo", sha="c" * 40)
        self.assertIn("状态：🔴", body)
        self.assertIn("已失效：卡片生成失败", body)
        self.assertIn("数据截至：未观察到", body)
        self.assertIn("正在工作的 Worker：未观察到", body)
        self.assertIn("等您决定：未观察到", body)
        self.assertIn("今天异常记录：未观察到", body)
        self.assertNotIn("待决定数", body)
        self.assertNotIn("异常数", body)
        self.assertLessEqual(sum(1 for line in body.splitlines() if line.strip()), 10)


class MainFlowTests(unittest.TestCase):
    def test_invalid_source_commit_publishes_unavailable_card_and_fails(self) -> None:
        with (
            mock.patch.object(
                ops_console,
                "resolve_source_commit",
                side_effect=ops_console.ConsoleError("cannot resolve source commit"),
            ),
            mock.patch.object(ops_console, "publish_issue_body") as publish,
        ):
            result = ops_console.main(
                [
                    "--repo",
                    "owner/repo",
                    "--issue",
                    "237",
                    "--source-commit",
                    "missing-commit",
                ]
            )

        self.assertEqual(result, 2)
        publish.assert_called_once()
        repo, issue, body = publish.call_args.args
        self.assertEqual((repo, issue), ("owner/repo", 237))
        self.assertIn("已失效：卡片生成失败", body)
        self.assertIn("数据截至：未观察到", body)
        self.assertIn("精确提交：不可用", body)
        self.assertNotIn("/blob/", body)


if __name__ == "__main__":
    unittest.main()
