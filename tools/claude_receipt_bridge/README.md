# Claude 正向回执与协调者唤醒桥

本工具是关联 [#208（L1 Hook 正向回执）](https://github.com/Eridanus117/agent-control/issues/208)与关联 [#225（事件驱动唤醒端到端接通）](https://github.com/Eridanus117/agent-control/issues/225)的版本化实现。它把 Claude Code 的三个正事件压缩为四字段回执，经固定 loopback 端点交给同机协调者；协调者可选择仅观察 JSONL，或把完成类回执聚合成当前 Orca Run 的一条 `status` 唤醒消息。它不安装 Hook、不写 GitHub 生命周期状态、不改变 Orca Task 生命周期，也不把“没有回执”解释为失败。

## 固定协议

二进制只有三个固定模式：

- `hook`：Claude Code command Hook 的入口，从 stdin 读取官方 Hook JSON；
- `listen`：只监听 `http://127.0.0.1:43127/v1/claude-receipts`，把通过校验的回执逐条写为 stdout JSONL。
- `wake`：监听同一固定端点，只消费 `Stop`／`TaskCompleted`，在 250 ms 窗内聚合、按 `taskId + dispatchId + event` 做 2 分钟 TTL 去重，再向显式指定的当前 Orca Run 写一条 `status` 消息。

`hook` 只接受 `UserPromptSubmit`、`Stop`、`TaskCompleted`。每次发送的 JSON 正文严格只有四个字段：

```json
{"taskId":"task_123","dispatchId":"dispatch_456","event":"Stop","time":"2026-08-12T23:45:01.000000123Z"}
```

`taskId`、`dispatchId` 和共享 token 只从 Claude 父进程环境读取，不能由 Hook stdin 覆盖：

- `AGENT_CONTROL_TASK_ID`
- `AGENT_CONTROL_DISPATCH_ID`
- `AGENT_CONTROL_RECEIPT_TOKEN`（32–512 字节，不含换行）

`wake` 还要求协调者进程显式提供 `AGENT_CONTROL_WAKE_RUN_ID`。它必须是 `run_...` 形式的精确 Run ID；工具不会从最近 Run、Issue、终端标题或 Hook 输入猜测目标。Orca CLI 按当前动态指南解析：优先使用 `ORCA_CLI_COMMAND`，开发环境使用 `orca-dev`，其余 Orca 托管终端使用 `orca`。

Hook 输入中的 `session_id` 只作当前事件确实绑定 Claude Session 的准入检查；transcript、cwd、提示、回复、Provider 内部 task ID 和工具数据都不进入回执。事件时间由桥本地生成并规范化为 UTC RFC3339Nano。

三个事件只保留 Claude 官方语义，不能升级为 Orca／GitHub 生命周期事实：

- `UserPromptSubmit`：提示已经进入 Claude 的 Hook 阶段、模型处理之前；不是 Provider turn 已开始；
- `Stop`：主 Agent 已完成一次响应；其他 Stop Hook 仍可能要求继续，不表示 Session 或 worker 已结束；
- `TaskCompleted`：Claude 内部 Task 正在被标记完成；不表示同名 Orca task、Issue 或交付已经完成。

## 协调者唤醒回路

协调者在当前 Orca Run 的终端以前台方式启动 `wake`；它不是 OS 服务、开机启动项或调度器：

```text
AGENT_CONTROL_RECEIPT_TOKEN=<本次随机 token>
AGENT_CONTROL_WAKE_RUN_ID=run_<当前精确 Run ID>
claude-receipt-bridge.exe wake
```

受监督 Claude worker 的可信父进程仍只注入 `AGENT_CONTROL_TASK_ID`、`AGENT_CONTROL_DISPATCH_ID` 与同一个随机 token。已安装的 `hook` 二进制和当前源码构建的 `wake` 二进制使用同一四字段协议，因此可以在不修改用户级 Hook 配置的情况下做受监督验证。

每个聚合批次只调用一次：

```text
orca orchestration send --to run:<精确 Run ID> --type status ... --payload <结构化聚合>
```

消息 payload 的 schema 是 `agent-control.claude-receipt-wake` v1，包含精确 Run、回执数、Dispatch 数、首末事件时间、观察时间和原始四字段回执。协调者的阻塞等待必须把 `status` 纳入类型过滤，例如：

```text
orca orchestration check --wait --types status,worker_done,escalation,question --timeout-ms 900000 --json
```

收到唤醒后仍须读取精确 Dispatch／交付来源；`status` 只表示“完成类 Provider 正事件值得检查”，不能把 `Stop`、`TaskCompleted` 或该消息升级为 `worker_done`、Issue 交付、验收或合并授权。`UserPromptSubmit` 继续可由 `listen` 观察，但不会触发协调者唤醒。

## 安全与失败边界

- 发送端不接受 URL、路径或命令参数，只能直连字面量 `127.0.0.1:43127`；显式禁用代理和重定向，500 ms 后超时。
- 接收端只绑定 loopback，要求定时安全比较的 token、`application/json`、四字段 schema、允许事件、受限 ID 和 4 KiB 正文。
- `hook` 是观测面：无论输入、绑定、认证或端点是否失败，都以 0 退出且不写 stdout，避免改变 Claude 的正常停止／完成语义；诊断只进 stderr/debug 面。
- `listen` 不去重；`wake` 只对完成类事件做短窗口聚合和易失 TTL 去重，并只写当前 Run 的 `status` 消息。它不选任务、不派发、不确认 Delivery、不创建或完成 Task，也不触碰 GitHub／Project。
- Hook 缺席、端点错误或回执超时都不是负事实证据，外部精确 Dispatch 检查仍保留。

## 失败模式与退化

| 失败 | 当前行为 | 退化路径 |
| --- | --- | --- |
| `wake` 未运行或端口未绑定 | `hook` 最多等待 500 ms，写 stderr 后仍以 0 退出 | 既有 cron／人工恢复继续按精确 Dispatch 核对；不能从“无回执”推出 worker 未开始或未完成 |
| token、Run ID 或回执 schema 不合法 | 接收端拒绝启动或返回认证／输入错误，不形成唤醒 | 修正当前受监督样本的绑定；cron 兜底保持不变 |
| Orca runtime／CLI／Run 写入不可用 | 当前聚合批次写 stderr，不写 TTL 成功标记；后续同键回执仍可重试 | cron／人工检查接管，不把本地内存冒充已交接事实 |
| 重复 `Stop`／`TaskCompleted` | 同键事件在 2 分钟内只形成一次唤醒；不同事件或 TTL 到期后可再次进入 | 协调者仍以精确 Dispatch 和持久交付为准 |
| 进程退出、主机休眠或重启 | 易失去重表与未发送聚合丢失，不声称离线保证 | 系统自然回到既有 cron／GitHub 合同恢复；本工具不新增 OS 层常驻能力 |

这条失败链刻意保留“桥不在跑时自然退化为 cron 兜底”：事件路径降低正常完成延迟，周期路径只负责漏事件、超时和其他负事实。

## 构建与验证

```text
cd tools/claude_receipt_bridge
go test ./...
go test -race ./...
go vet ./...
go build -trimpath -o claude-receipt-bridge.exe .
```

安装与用户级配置仍须负责人过目，见 [INSTALLATION_PROPOSAL.md](./INSTALLATION_PROPOSAL.md)。

参考：Claude Code [Hooks reference](https://code.claude.com/docs/en/hooks) 的 command exec form、Hook 通用输入、`UserPromptSubmit`、`Stop`、`TaskCompleted` 与安全章节；2026-08-12 本次实现时本机版本为 2.1.229。
