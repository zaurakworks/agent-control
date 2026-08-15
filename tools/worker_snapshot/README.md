# Worker 观察面

这是关联 [#226（Worker 观察面一页）](https://github.com/Eridanus117/agent-control/issues/226)的手动、headless 只读工具。它从当前 Orca runtime 读取 Run、Task、Dispatch、Worker 与终端观察态，输出一页 Markdown 或 JSON；不轮询、不启动服务、不写 Orca 状态，也不读取终端正文。

## 运行

前置条件：Python 3.11+，当前版本的 Orca CLI 可访问正在运行的 Orca。工具按 Orca 指南选择 `ORCA_CLI_COMMAND`、开发版 `orca-dev` 或平台默认命令，也可用 `--orca-command` 显式指定。

从仓库根目录生成全部普通 Run 的当前快照：

```text
python tools/worker_snapshot/worker_snapshot.py
```

只看一个或多个 Run，或同时写入给人看的 Markdown 与运营台消费的结构化 current view：

```text
python tools/worker_snapshot/worker_snapshot.py --run run_65a73145f0e2 --output tools/worker_snapshot/current.md --current-json tools/worker_snapshot/current.json
python tools/worker_snapshot/worker_snapshot.py --run run_65a73145f0e2 --format json
```

默认扫描当前 runtime 的全部非 legacy Run；`--run` 可重复，适合负责人只看当前波次。工具并发执行只读查询，任一 Run 的任务清单失败就停止，避免用不完整数据报“当前总数”；单个 `worker-show` 不可读时保留该 `dispatched` 任务、把终端态标成 `unavailable`，且不计入“在跑”。

`--current-json` 可选；提供后会把同一轮结构化数据压缩成版本化小视图。当前活异常仍按既有口径计算：席位终端不在跑、Worker 为 `failed`／`unavailable`、派发数超过在跑数，或存在采集缺口时取三者最大值。Markdown 保持展示产物，运营台不再从其文案反向解析计数。

验证：

```text
python -m unittest discover -s tools/worker_snapshot/tests -v
```

## 手机 30 秒路径

1. 协调者在桌面执行上面的 `--run ... --output ...` 命令，得到紧凑 Markdown。
2. 在已有写入授权的协调 Issue 上执行 `gh issue comment <number> --repo <owner/repo> --body-file <snapshot-path>`；工具本身不替协调者扩大 GitHub 写入权限。
3. 负责人在 GitHub 手机 App 打开该 Issue 的最新评论即可看到总数与逐席状态。正常本地 runtime 与网络下，命令和发布各只需一次调用；若任一步失败，保留错误而不发布旧快照。

这条路径把 GitHub 评论当作负责人可达的临时展示面，不把评论变成执行事实或授权来源。需要刷新时重新生成并发布带新观察时刻的快照；仓内样例只是一次冻结证据。

## 口径与边界

- “在跑 worker”只计 `worker-show.observation.status=running`；另列 `Task.status=dispatched` 数，避免把不可读、失联或残留任务冒充在跑。
- 每席展示合同 Issue／任务一句话、Dispatch 地址、派发开始时刻、Worker 阶段和终端连接态。持久输出使用 `dispatch:` 地址，不写易失终端句柄，不输出 terminal preview。
- Orca 当前无时区的 `dispatched_at` 与仓内既有运营工具一致按 UTC 解释，输出带 `Z`；输出是采集时瞬时状态，不能回放旧时刻。
- 默认范围是当前 runtime 的全部普通 Run；如果历史 Run 很多而负责人只关心一个波次，显式传入该 Run ID，报告会披露范围。
- 这只是手动快照能力，证据最多支持实现完成与一次当前样本；不证明产品采用、长期低成本运行或 Orca 的长期依赖地位。
