# Worker 观察面

> 观察时刻：2026-08-14T20:46:02.693758Z｜来源：`orca orchestration` 只读瞬时快照｜范围：1 个 Run
> 这是一次性观察证据，不是持久任务合同；刷新时重新运行工具。

## 摘要

- 在跑 worker：**1**
- `dispatched` 任务：**1**
- 终端观察态：running 1

## 当前席位

1. 关联 #287（R3｜治理正文一次性修订（A3/A5/A6规则/A7-A10））｜开始 2026-08-14T20:31:45Z｜终端 running / connected｜Worker ready / input\_accepted｜`dispatch:ctx\_9af805e7e142`

## 口径

- “在跑”只计 `worker-show.observation.status=running`；`dispatched` 数另列，避免把失联或不可读终端冒充在跑。
- 每席只展示 Task、Dispatch、开始时刻和状态；不读取终端正文，也不把易失终端句柄写入持久文本。
- Orca 返回的无时区 `dispatched_at` 按 UTC 标为 `Z`；快照不推断旧时刻状态。
