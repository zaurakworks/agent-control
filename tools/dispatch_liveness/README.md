# Orca Dispatch 自动验活与单次点火

这个一次性 Python 工具在 `worker-start` 返回后，对一个精确 `task / dispatch / terminal` 做关联 [#211（tui-idle 竞态对照）](https://github.com/Eridanus117/agent-control/issues/211)E1 的有界验活：5 秒首读；尚未提交时再等 5 秒复读；分类为 `submitted`、`composer-pending` 或 `input-missing`。`submitted` 优先使用 `worker-read` 的真实 user-message transcript；终端正文里只出现 Task／Dispatch 标记并不足以证明 composer。只有第二读与点火前即时第三读都确认同一可编辑 composer，Dispatch 仍为 `dispatched` 且终端仍 connected+writable，才沿同一终端发送一次 Enter；随后等 10 秒只复读一次。

## 协调者集成

从 `worker-start` 回执取得三个精确 ID 后立即运行：

```text
python tools/dispatch_liveness/dispatch_liveness.py --task-id task_abc --dispatch-id ctx_def --terminal term_ghi --source https://github.com/Eridanus117/agent-control/issues/241
```

输出是不含终端正文的 JSON：最终三态、是否点火、点火前即时复核、点火后态、完整有界时间线与对象身份核验。确认过 composer 的结果还包含两个自足候选：`ops_metrics_annotation.event` 可直接放入 `tools/ops-metrics/annotations/<date>.json` 的 `dispatch_race_events`；`issue_31_sample_candidate.sample` 包含 Run／Task／Dispatch／terminal、Orca App 与捆绑 CLI 版本、runtime、worker-start 路径与 worktree selector/path、后态、heartbeat/worker_done、释放与遗留资源后态、自动 Enter 和人工动作成本。提供稳定 `--source` 后两者的 `ready_*` 均为 true；没有来源时明确列出缺字段。`input-missing` 与 `submitted` 不生成 composer 竞态候选。

工具不会重派、不会创建 Task／Dispatch／Worker、不会修改 Orca 配置，也不会轮询。`input-missing` 永不点火；确认 `composer-pending` 后也只允许一个 Enter 和一次复读。

## 单次点火硬约束

点火前先在操作系统解析出的唯一用户状态目录原子创建 `<dispatch-id>.json` 标记（Windows 为 Known Folder API 返回的 LocalAppData 下 `orca-dispatch-liveness/ignitions`）。标记在发送 Enter 前落盘；多个进程竞争、进程崩溃或命令结果不明时，后续运行也不会对同一 Dispatch 再发 Enter。产品 CLI 没有 `--state-dir`、状态目录环境变量、`--force` 或清理标记入口；单次调用不能切换领取域。需要调查异常时保留标记与 JSON 结果，交回协调者处理。

单测和受控演示只通过 Python 内部的显式 `FileIgnitionStore.for_test(...)` 夹具注入临时目录，不属于产品入口。普通协调集成不要在重试前清理用户状态标记。

## 判据与边界

- `submitted`：精确 Task／Dispatch 已成为 transcript 中的 user message、Dispatch 已完成、目标终端标题处于明确工作态，或标记之后出现 TUI 提交后活动；即使尚无思考或输出，只要 user message 已进入 transcript 就属于本态；
- `composer-pending`：精确 Provider transcript 可取得且其中尚无该 user message，同时精确 Task／Dispatch 位于当前 viewport 末端并带有受支持 Provider 的可编辑输入 footer；第二读后必须在点火前即时重读仍得到同一状态；
- `input-missing`：没有提交证据，也没有足以证明可编辑 composer 的终端证据。标记出现但形状歧义、第一次看到后第二次消失、transcript 不可取得或 Provider footer 未适配时都保守归入本态，不发送 Enter；
- `input_accepted`、终端 `running` 或 `tui-idle` 本身都不升级为 `submitted`；
- 结果只证明本次目标终端观察面，不证明 Worker 完成、失败、可释放或 Issue 已交付。

当前适配优先读取 Orca 的精确 Provider transcript，并只把 Codex／Claude 已知输入 footer、`esc to interrupt`、工作标题与活动符号作为有界终端证据。Orca 或 Provider 改变 transcript／渲染形状时，若 user message 或可编辑 composer 无法语义区分，应停止自动点火并更新适配器与测试；不要放宽到“有标记”或“终端还活着”。

## 验证与受控演示

```text
python -m unittest discover -s tools/dispatch_liveness/tests -v
python tools/dispatch_liveness/demo.py
```

受控演示冻结四次读为 `composer-pending / composer-pending / composer-pending / submitted`（第三次是点火前即时复核），不等待真实时间、不接触 Orca，但会经过与生产入口相同的身份核验、原子点火标记、唯一 Enter、样本消费和点火后复读路径。输出的 `demo_enter_calls` 必须为 `1`。
