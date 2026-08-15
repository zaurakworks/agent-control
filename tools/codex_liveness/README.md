# Codex 派发验活

这个只读 Python 工具用 Codex JSONL 事件回答一个精确 Orca Dispatch 当前是“未提交”“已提交”还是“已开始”。它不读取 Orca 合同、不发送 Enter、不重派、不修改 Codex 配置，也不把 Provider 事件升级成 Issue 已交付或 Worker 已完成。

## 会话验活

扫描 `$CODEX_HOME/sessions`（未设置时为 `~/.codex/sessions`）：

```text
python tools/codex_liveness/codex_liveness.py sessions --task-id task_abc --dispatch-id ctx_def --json
```

也可用一个或多个 `--session <rollout.jsonl>` 限定已知会话。工具只在用户消息事件同时含有精确 `taskId` 和 `dispatchId` 时建立绑定；工具调用、工具输出、Session 元数据和任意其他文本即使含有相同 ID 也不算提交证据。输出不包含 prompt、模型回答或工具内容。

状态证据如下：

| 状态 | 会话 JSONL 证据 |
| --- | --- |
| 未提交 | 没有找到同时绑定精确 `taskId + dispatchId` 的用户消息 |
| 已提交 | 找到精确用户消息，但没有与它关联的 turn 启动事件 |
| 已开始 | 精确用户消息的 `turn_id` 已有 `task_started`；旧版无消息 `turn_id` 时只使用当时活动 turn |

当前解析两种已在本机历史中出现的消息形状：Codex 0.144.5 的 `event_msg/user_message`，以及 0.147.0 的 `event_msg/item_completed` + `UserMessage`。活动文件末尾出现尚未写完的 JSON 行时会在 `warnings` 中报告，但不会抹掉此前完整记录提供的证据。

## 非交互事件验活

[OpenAI 官方非交互模式文档](https://learn.chatgpt.com/docs/non-interactive-mode#make-output-machine-readable)中的 JSONL stdout 使用 `thread.started`、`turn.started` 等点号事件名；它与持久 rollout 中的 `event_msg/task_started` 不是同一序列化形状。只有当一个文件已经由调用者排他绑定到给定 Dispatch 时，才能这样读取：

```text
python tools/codex_liveness/codex_liveness.py events --task-id task_abc --dispatch-id ctx_def --input dispatch-events.jsonl --json
```

`thread.started` 对应“已提交”，`turn.started` 对应“已开始”。`events` 子命令不会从 JSONL 自行证明外部文件与 Dispatch 的归属；共享文件、混合多个运行的 stdout 或来源不明文件不得使用该适配器。

## Codex 0.147 flag 形状

本机 `codex-cli 0.147.0` 的 `-a/--ask-for-approval` 是全局 flag，必须放在 `exec` 前；`--ephemeral`、`--ignore-user-config`、`--ignore-rules` 和 `--json` 放在 `exec` 后。生成只读、无人值守、stdin prompt 的 argv（只打印，不执行）：

```text
python tools/codex_liveness/codex_liveness.py exec-argv
```

默认结果等价于：

```text
codex -a never -s read-only exec --ephemeral --ignore-user-config --ignore-rules --json -
```

生成器不使用滚动文档中的兼容 flag `--full-auto`，也不生成本机 0.147.0 会拒绝的 `codex exec -a never ...` 形状。它只提供受限 batch lane 的可复核 argv，不启动 Codex、不改变现有 Orca 派发路径。

## 协调者使用边界

Codex 派发后优先读取这个结构化结果，不再先刮终端内容或把固定 30 秒当作 Provider 已开始的推断。只有“已开始”可以证明这个精确 Dispatch 的 Codex turn 已创建；“未提交”或“已提交”是当前快照，不是失败、重派、释放或补 Enter 的充分条件。若当前 Codex 版本或 JSONL schema 命中失效条件，先退出自动判定并做最少复核；Claude、其他 Provider 和没有 JSONL 的交互面仍按各自证据路径处理。

验证：

```text
python -m unittest discover -s tools/codex_liveness/tests -v
```
