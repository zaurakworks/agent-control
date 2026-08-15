# Orca Dispatch 一次性截止查询

这是一个被调用时才读取 Orca 的 Python 查询工具。给定一个 Run，它列出当前所有 `dispatched` Task 对应的 Dispatch、开始时间、显式预期时长、截止时间、已逾期时长，以及 `should_wake` 判定。它不等待、不循环、不写 Orca、不发消息，也不执行唤醒。

```text
python tools/dispatch_deadlines/dispatch_deadlines.py --run run_example
python tools/dispatch_deadlines/dispatch_deadlines.py --run run_example --json
```

工具实际执行的只读查询是：

```text
orca orchestration task-list --run <run_id> --status dispatched --json
orca orchestration dispatch-show --task <task_id> --json
```

## 预期时长合同

预期时长采用**派发时显式声明**，而不由工具根据 spec 长度或历史时长暗中推断。创建 Task 时，在 spec 中放入且只放入一行：

```text
Expected-Duration-Minutes: 90
```

这个整数表示从 Dispatch 建立到 `worker_done` 的预期墙钟分钟数，必须包含启动、实现、验证和远端交付。协调者可参考同类已完成任务校准该值，但写入 spec 的显式值才是本次 Dispatch 的唯一判据；任务语义、机器负载和验证门差异很大，自动用字符数或跨类历史外推会制造伪精度。缺失、非正整数或重复声明都报告为 `expected_duration_*`，工具不会猜值，也不会标记唤醒。

判据只有一条：

```text
should_wake =
  当前 Dispatch.status == "dispatched"
  AND spec 恰有一个正整数 Expected-Duration-Minutes
  AND observed_at >= dispatched_at + expected_duration
```

`dispatched_at` 是 Orca 当前返回的开始时间。当前 CLI 的无时区 SQLite 形状按 UTC 解释；带 `Z` 或 offset 的时间先归一到 UTC。未到期的 `overdue_seconds` 为 `0`；缺少合法预期时长时为 `null`。

## 对 D1／D2 的覆盖与缺口

关联 [#287（当前所有可做事项）](https://github.com/Eridanus117/agent-control/issues/287)的 D1 中，如果只是 worker 终端死亡、失联或不再产生 Delivery，而协调者 Session 和它的一次性截止仍能执行，到点查询会看到同一 Dispatch 仍非终态并标记 `should_wake=true`。恢复后的协调者也可主动运行一次查询，找出仍留在 Run 中的逾期 Dispatch。没有在途 Dispatch 时结果明确为零，因此不会复现 D2 的空 Run 常驻 tick；正常 `worker_done` 等正事件仍由 Run Delivery 承担。

它**不能覆盖 D1 的完整事故面**：协调者 Session 整体停止、冻结或一直无法执行回调时，任何 session 内一次性截止都不会响；Orca runtime 不可读时工具也不能回答；Dispatch 没有被记录、被错误写成终态、spec 没有合法预期时长，或系统时钟错误时，同样不能可靠兜底。它也不是离线唤醒。与关联 [#113（巡检口径唯一定位面）](https://github.com/Eridanus117/agent-control/issues/113)及当前权威一致，本目录不建设轮询、Hook、Webhook、常驻调度器或无人值守自动化。

因此，这一方案消除“零在途仍持续烧轮次”的空转，并把存活协调者的超时检查收敛成每个 Dispatch 一次；它没有把 session 内机制包装成跨 Session 可靠性。

## 提议的规则文本（待协调者拼接）

> 派发受监督 Task 时，spec 必须且只能声明一次 `Expected-Duration-Minutes: N`；N 是从 Dispatch 建立到 `worker_done` 的完整预期墙钟分钟数，包含启动、实现、验证和远端交付。`worker-start` 成功后，只为该 Dispatch 安排一次 N 分钟截止唤醒，不建周期 tick；Run 没有在途 Dispatch 时不安排唤醒。到点运行 `python tools/dispatch_deadlines/dispatch_deadlines.py --run <run_id>`，只有同一 Dispatch 仍为 `dispatched` 且 `should_wake=true` 时，协调者才检查并处置；缺失或非法声明按合同缺口报告，不猜值。正常 `worker_done`、问题与升级仍走 Run Delivery。该截止只是 session 内兜底：协调者 Session 或 Orca runtime 停止时不会唤醒；恢复后应主动运行一次查询，但本规则不建设轮询、Hook、Webhook、常驻调度器或离线唤醒。

## 自检

```text
python -m unittest discover -s tools/dispatch_deadlines/tests -v
python tools/dispatch_deadlines/dispatch_deadlines.py --run <run_id>
python tools/dispatch_deadlines/dispatch_deadlines.py --run <run_id> --json
```

单测覆盖：已逾期、未到期、缺失声明、重复／非法声明、零在途和跨 Run 身份不匹配。真实 Run 查询只能证明当次观察到的 Orca 状态；如果现有 Task 是在本规则之前创建的，缺少声明会如实显示为 `unknown`，不会被补成“已验证截止”。
