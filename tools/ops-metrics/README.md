# Agent 系统运营仪表

这个目录提供一次性、可复算的运营日报和两块观测仪表：产能利用率与交互质量。它从 GitHub API 读取 Issue、PR 与评论时间戳，从 Orca orchestration 读取所选 Run 的 Task、Dispatch 与 Worker 状态；负责人纠偏、worker 空转和 composer-pending 竞态使用带来源的版本化 annotations，避免从自然语言自动猜事件。

## 运行

前置条件：Python 3.11+、已认证的 `gh`，以及可访问当前运行面的 `orca`。工具只读取两端并写本地 JSON/Markdown，不启动服务、不轮询、不注册计划任务。
只读命令遇到 EOF、连接重置、超时或 502/503 时最多重试两次；其他错误立即停止，不用缺失数据生成报告。

从仓库根目录运行：

```text
python tools/ops-metrics/ops_metrics.py --repo Eridanus117/agent-control --date 2026-08-12 --timezone America/New_York --run-id run_65a73145f0e2 --annotations tools/ops-metrics/annotations/2026-08-12.json --output-json tools/ops-metrics/reports/2026-08-12.json --output-report tools/ops-metrics/reports/2026-08-12.md --current-report tools/ops-metrics/current.md --current-json tools/ops-metrics/current.json --trigger manual
```

`--run-id` 可重复。必须显式列 Run，防止把无关历史 Run 静默算入；日报会披露最早 Run 起点，若晚于本地日窗起点就明确标记 Orca 覆盖不完整。`--snapshot-at` 可选，用 RFC 3339 时间冻结截止点；省略时使用当前时间。无论是否显式传入，生成报告里的复算命令都会写入实际快照时间，避免以后重跑时静默移动截止点。

`--trigger manual` 与 `--trigger tick` 只记录调用来源，执行相同的一次性流程：人工可直接运行，外部协调 tick 也可调用。工具自身不建定时器、轮询、服务或自动发布。

`--current-report` 与 `--current-json` 均可选；前者同步覆盖给人看的稳定 Markdown，后者写运营台消费的版本化小视图。小视图的异常数严格复用现有口径：composer-pending 受影响 Dispatch 数＋worker 空转事件数＋是否存在 Orca 当前观察缺口，不改变统计定义。日期化 `reports/` 与 `annotations/` 只在活跃日或负责人手动请求时落盘，零活动日不为连续性制造空报告。

验证纯计算与 annotations 结构：

```text
python -m unittest discover -s tools/ops-metrics/tests -v
```

## 口径

- 日窗：指定 IANA 时区的本地自然日，先换算成精确 UTC 半开区间 `[start, end)`，再截断到快照时刻。工具会查询日窗跨越的每个 UTC 日期；GitHub 搜索日期仅缩小候选，最终仍按时间戳过滤。
- 派发数：所选 Run 中 `dispatched_at` 落入日窗的当前可见 Dispatch。Orca 当前接口按 Task 提供当前 Dispatch，历史重试不反推。
- 交付回流：只认 `task.result.provenance=worker_report` 且存在 `outcome` 的 `completedAt`，不用 Task 状态冒充 `worker_done`。
- 同日派发队列回流率：日窗内派发且截至快照已有 `worker_done` 的数量，除以日窗内派发数。跨日完成会进入完成事件日的回流数，但不倒改旧日报。
- 在跑峰值：每个当前可见 Dispatch 形成 `[dispatched_at, 最早完成时刻)` 半开区间；完成时刻依次取 Dispatch、Task 与 `worker_done` 中最早的有效时间，未完成则截到快照。Task 已失败但低层 Dispatch 仍残留时以 Task 完成时刻结束，不把残留记录冒充仍在跑。
- 交付回流时延：Dispatch `dispatched_at` 到 `worker_done completedAt`，按 worker_done 发生日归组；报告 n、中位数、nearest-rank P90 与最大值。
- PR 合并数：`merged_at` 落入日窗的 PR 数；同一批数据继续计算合并周转。
- 审阅周转：PR `created_at` 到首个审阅信号，按首次信号发生日归组。信号仅含正式 review、inline review comment，或匹配 `审阅|review|建议合并|建议修改|建议回退` 的 PR 会话评论；共享账号下不猜 Agent 作者身份。
- 合并周转：PR `created_at` 到 `merged_at`，按合并发生日归组。
- GitHub 评论数：仓库 Issue/PR conversation comments；formal reviews 与 inline review comments只进入审阅信号，不重复塞进评论活动数。
- worker 空转事件：annotations 中有来源的独立共同触发事件数；同一批 5 个 worker 一起空转算 1 个事件，同时保留受影响规模文字。
- composer-pending 竞态与人工点火：annotations 中逐批保存受影响 Dispatch 数、点火次数、记录时刻、已知 Dispatch ID 与稳定来源；只统计记录时刻落入快照的项目。Orca 当前没有结构化的 composer-pending 历史字段，工具不解析 TUI 文本或 GitHub 自然语言来猜事件。`input-missing` 是不同机制，不混入这项竞态计数。
- 负责人纠偏：annotations 中已登记、去重的事件数与分类。同一事实被 Issue 和研发记忆重复登记只计一次；工具验证日期、唯一 ID、分类和非空来源，不自行拆分句子。
- 错误样本回归清单：annotations 的 `regression_checks` 为每类当日错误保存稳定 ID、分类、样本数、复跑类型、逐步复跑程序、通过判据与来源。日报重算项目数、覆盖样本数与复跑类型分布，并逐项渲染；`automated`、`manual`、`hybrid` 只说明复跑方式，不伪装成已经执行或已经通过。

冻结快照只约束带时间戳的事件指标。Orca 当前接口提供的是 Task、Dispatch、Worker 与终端的当前观察，不能回放它们在旧快照时刻的状态；报告把这组辅助状态单独标为“采集时当前可见状态”，不将其混入派发队列回流率或时延统计。

`manual_baseline` 可选，用来把一份有来源的人工口径与自动派发数、回执数和成功率并列，报告只显示差异并解释口径边界，不自动校正数据。

`regression_checks` 的最小结构如下；`sample_ids` 在整份清单中不得重复，`procedure` 必须是非空字符串列表：

```json
{
  "id": "stable-regression-id",
  "category": "reference_integrity",
  "label": "发布前引用未从远端取回核对",
  "sample_ids": ["reference-link-written-from-memory"],
  "check_type": "manual",
  "procedure": ["取回目标对象", "逐项核对编号、标题与稳定链接"],
  "expected": "发布文本中的引用均与取回对象一致",
  "sources": ["https://github.com/owner/repo/issues/1"]
}
```

## 证据边界

首报的 Orca Run 于当日上午中段才建立，不能覆盖该日更早的低层或未登记派发；报告必须保留这项缺口。指标描述吞吐、回流和纠偏观测，不等同于产出价值、交付质量、产品采用或长期能力改善。
