# 运营台卡片生成器

这是关联 [#236（运营台承载实施）](https://github.com/Eridanus117/agent-control/issues/236)的单次 Python 进程。它读取既有 `worker_snapshot` 与 `ops-metrics` 的版本化 JSON current view、从 Project 3 读取待负责人动作数量，并用 `gh api` 原地覆盖运营台 Issue 正文；对应 Markdown 只作负责人明细展示。工具不启动服务、轮询或定时器，也不向 GitHub 之外发布。

## 刷新流程

先让两个既有工具按原口径生成文件层。运营日报只在活跃日或负责人手动请求时生成日期化报告；`--current-report` 同步覆盖稳定入口：

```text
python tools/worker_snapshot/worker_snapshot.py --run <run-id> --output tools/worker_snapshot/current.md --current-json tools/worker_snapshot/current.json
python tools/ops-metrics/ops_metrics.py --repo Eridanus117/agent-control --date <YYYY-MM-DD> --timezone America/New_York --run-id <run-id> --annotations tools/ops-metrics/annotations/<YYYY-MM-DD>.json --output-json tools/ops-metrics/reports/<YYYY-MM-DD>.json --output-report tools/ops-metrics/reports/<YYYY-MM-DD>.md --current-report tools/ops-metrics/current.md --current-json tools/ops-metrics/current.json --trigger manual
```

提交并推送两组 `current.md`／`current.json` 之后，用包含四个文件的精确提交刷新运营台：

```text
python tools/ops-console/ops_console.py --repo Eridanus117/agent-control --issue 237 --project-owner Eridanus117 --project-number 3 --source-commit <40位提交SHA> --trigger manual
```

协调者 tick 可把最后一个参数改为 `--trigger tick`。

只在事件边界调用：波次开始或收口、任务完成或失败、出现负责人决定或显著状态翻转，以及负责人手动索取时刷新。静默期不按 tick 数或墙钟补刷；`manual` 与 `tick` 都只是调用来源标记，每次只执行一次。生成器不会提交文件、创建评论、注册计划任务或维持后台进程；`--dry-run` 只输出待发布正文，不改 GitHub。

## 失效纪律

- 默认新鲜窗是 15 分钟，以两份输入较早的观察时刻为准；每张新鲜卡片也明确写明“超时即视为已失效”，因此即使静默期没有下一次刷新，过了 `新鲜至` 的旧值也不再具有当前语义。调用时已经超过窗口，则状态直接标成“已失效”，计数改称“样本”。
- 任一输入缺字段、Project 不可读或解析失败时，仍把正文更新为“已失效”，所有来源与计数显示“未观察到”，并返回非零退出码；旧卡片不会继续冒充当前。
- 状态灯只表示此刻：当前快照存在 failed、失联或不可读席时为红灯；有待负责人动作且无当前活异常时为黄灯；其余新鲜可用状态为绿灯。
- “异常数”合计当前活异常与既有运营日报解析计入的当日历史样本，便于追溯；只有当前活异常影响新鲜卡片的灯色，已恢复历史样本不会单独点红灯。
- `--source-commit` 必须同时包含与工作区完全一致的两组 Markdown／JSON current 文件，否则发布“不可用”。卡片链接仍指向这个精确提交下的 Markdown 明细。
- 卡片最多 10 个非空行、最多 3 条要事。评论只留给需要负责人动作、异常或失效越阈值等高注意力事件，例行刷新不新增评论。
- Project、文件与运营台都只是观察面；意图、授权、决定和验收仍以合同 Issue／PR 为准，吞吐不等于价值。

验证：

```text
python -m unittest discover -s tools/ops-console/tests -v
```
