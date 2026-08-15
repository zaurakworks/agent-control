# Agent 系统运营日报｜2026-08-14

> 时区：`America/New_York`；快照：`2026-08-14T20:46:02.890537+00:00`；触发：`manual`；本报告是当日截至快照时刻的部分日快照。

## 结论先行

- Orca 覆盖的 Run 共派发 **19** 个当前可见 Dispatch；收到 **16** 个 `worker_done`。派发同日队列截至快照回流率为 **84.2%**，交付回流时延为 n=16；中位 8m 12s；P90 22m 58s；最大 40m 45s。
- Dispatch 在跑峰值 **3**（首次达到于 `2026-08-14T19:27:54+00:00`）；已登记 composer-pending 竞态 **0** 次，人工点火 **0** 次。
- GitHub 当日活动：Issue **7**、PR **9**、合并 PR **9**、Issue/PR 会话评论 **32**；审阅周转 无可计算样本；合并周转 n=9；中位 3m 55s；P90 15m 39s；最大 15m 39s。
- 已登记、去重后的负责人纠偏 **0** 次；worker 空转事件 **0** 次。两者只计人工登记证据，不从措辞猜测新事件。
- 当日错误样本已形成 **0** 个结构化回归项，覆盖 **0** 个样本；复跑类型 {}。

## 产能利用率仪表

| 指标 | 值 | 可复算定义 |
| --- | ---: | --- |
| 派发数 | 19 | 所选 Run 中 `dispatched_at` 落入日窗的当前可见 Dispatch 记录 |
| worker_done 回流数 | 16 | `task.result.provenance=worker_report` 且 `completedAt` 落入日窗 |
| 同日派发队列回流率 | 84.2% | 日窗内派发且截至快照已有 worker_done ÷ 日窗内派发 |
| Dispatch 在跑峰值 | 3 | Task／Dispatch 的派发到完成半开区间重叠峰值；首次达到 `2026-08-14T19:27:54+00:00` |
| composer-pending 竞态 | 0 | annotations 中已登记的受影响 Dispatch 数；分类 {} |
| 人工点火 | 0 | 上述竞态中沿原 Dispatch 补交 Enter 的操作次数 |
| 交付回流时延 | n=16；中位 8m 12s；P90 22m 58s；最大 40m 45s | 派发时间 → worker_done `completedAt`；按完成事件日归组 |
| 审阅周转 | 无可计算样本 | PR 创建 → 首个正式 review、inline review comment，或含审阅语义的 PR 会话评论；按首次审阅事件日归组 |
| PR 合并数 | 9 | `merged_at` 落入日窗的 PR |
| 合并周转 | n=9；中位 3m 55s；P90 15m 39s；最大 15m 39s | PR 创建 → `merged_at`；按合并事件日归组 |
| worker 空转事件 | 0 | annotations 中有来源的事件数；批量空转按一次共同触发事件计 |

所选 Run：`run_65a73145f0e2`。采集时当前可见状态（不作历史回放）：任务 {"blocked": 1, "completed": 220, "dispatched": 1, "failed": 2}；Dispatch {"completed": 220, "dispatched": 1, "failed": 3}；Worker {"failed": 2, "ready": 1, "stopped": 1, "succeeded": 220}；终端观察 {"exited": 42, "missing": 178, "running": 4}。

### 空转事件明细


### 派发竞态与点火明细


## 交互质量仪表

纠偏总数：**0**。分类：`{}`。

| 事件 | 分类 | 已登记事实 | 来源 |
| --- | --- | --- | --- |

登记说明：
- 本次刷新未观察到有稳定来源的人工 annotations；不从自然语言猜测或沿用昨日事件。

### 当日错误样本回归清单

| 回归项 | 分类 | 样本数 | 复跑类型 | 复跑步骤 | 通过判据 | 来源 |
| --- | --- | ---: | --- | --- | --- | --- |

## GitHub 活动与周转样本

- Issue 创建：7；PR 创建：9；Issue/PR 会话评论：32。
- 首次审阅事件样本：0；合并事件样本：9。

## 口径边界

- GitHub 计数使用精确 UTC 边界换算后的本地日窗，并截断到快照时刻；工具查询日窗跨越的每个 UTC 日期，搜索日期只用于缩小候选，最终按时间戳再过滤。
- 审阅信号不把任意 PR 评论都算作审阅：仅正式 review、inline review comment，或正文匹配 `审阅|review|建议合并|建议修改|建议回退` 的会话评论。共享 GitHub 账号下无法可靠区分 Agent 身份，因此不猜作者角色。
- Orca 只覆盖显式列出的 Run，且 `dispatch-show` 暴露的是每个 Task 当前可见 Dispatch；更早 Run、低层未登记工作和历史重试不反推。
- 在跑峰值用派发时刻到 Dispatch／Task／worker_done 最早完成时刻的半开区间计算；低层残留 Dispatch 若 Task 已失败，以 Task 完成时刻结束，不把残留记录冒充仍在跑。
- Task／Dispatch／Worker／终端状态是采集时的当前观察，不支持按旧 `--snapshot-at` 回放；冻结快照只约束带时间戳的派发、worker_done 与 GitHub 事件口径。
- 纠偏、空转与 composer-pending 竞态来自版本化 annotations；工具验证结构、日期、计数、唯一 ID 与非空来源字段，不从自然语言自动发明或拆分事件。`input-missing` 是不同机制，不混入本表竞态计数。
- 本仪表描述观测到的吞吐与周转，不等同于价值、质量、产品采用或长期能力结论。

## 复算

```text
python tools/ops-metrics/ops_metrics.py --repo Eridanus117/agent-control --date 2026-08-14 --timezone America/New_York --run-id run_65a73145f0e2 --annotations tools/ops-metrics/annotations/2026-08-14.json --output-json tools/ops-metrics/reports/2026-08-14.json --output-report tools/ops-metrics/reports/2026-08-14.md --snapshot-at 2026-08-14T20:46:02.890537+00:00 --trigger manual
```

工具会同时重写 JSON 快照与本 Markdown；它是手动触发的一次性进程，不含服务、轮询或计划任务。
