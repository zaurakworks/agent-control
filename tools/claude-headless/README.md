# Claude headless 有界调用

这个一次性 Python 入口把结构化事实交给 `claude -p` 做窄语义判断。它不是巡检器、循环、调度器或战略协调者；机械检查应先由确定性程序完成，只有确实需要语义判断的事件才调用本入口。

## 固定边界

每次调用都由包装器显式传入以下约束：

- `--safe-mode`，不加载用户／项目自定义 Hook、MCP、Skill、Plugin 或 `CLAUDE.md`；
- `--permission-mode dontAsk` 与空工具集，模型不能读写文件、运行命令或访问共享写入面；
- `--no-session-persistence`，不恢复或保存会话；
- `--json-schema` 与 `--output-format json`，只接受对象型结构化输出；
- 默认本机已核验的带版本日期完整模型 ID `claude-haiku-4-5-20251001`、`low` effort、1 agentic turn、`$0.10` 客户端预算上限和 60 秒进程超时；模型别名及省略版本日期的名称会在本地被拒绝；
- 包装器硬上限为 3 turns、`$1.00` 和 300 秒，提示最多 64 KiB、schema 最多 32 KiB；
- 超时后终止隔离的进程组／Windows 进程树；不重试，避免一次事件产生多次模型调用。
- 成功前反查 `modelUsage` 与 `total_cost_usd`；实际模型集合不等于请求的完整 ID、成本字段缺失、非有限、为负或报告成本越界时拒绝结果；请求预算也必须为有限正数。

模型输出只是 advisory。它不获得 Orca Run 协调能力、GitHub 写入权、产品决定权或跨所有权派发权；外层确定性调用方必须按自己的固定规则消费或升级结果。

## 调用

从仓库根目录运行：

```text
python tools/claude-headless/claude_headless.py --prompt-file tools/claude-headless/samples/2026-08-12-readonly-review.prompt.txt --schema-file tools/claude-headless/samples/readonly-review.schema.json --result-file build/claude-headless/result.json --receipt-file build/claude-headless/receipt.json --model claude-haiku-4-5-20251001 --max-turns 1 --max-budget-usd 0.10 --timeout-seconds 60
```

提示通过标准输入送给 Claude 子进程，不进入命令行。schema 会进入命令行，但包装器限制其大小并要求根类型为对象。

成功时 `result-file` 只保存 `structured_output`；`receipt-file` 保存边界、输入哈希、耗时、客户端成本和 token 用量。回执有意排除 prompt、provider 原始文本（包括失败／超时时的 `stderr`）、Session ID 和 UUID；失败回执只保存本地状态、进程退出码及可从结构化 envelope 稳定归类的错误类别。调用方应以本次唯一回执的 `status=succeeded` 为成功依据，不能把旧结果文件当成当前成功。

退出码：`0` 成功，`2` 本地输入／边界错误，`3` 找不到命令，`4` 超时，`5` Provider 失败，`6` Provider 输出不是合格的结构化对象。失败不自动重试；若同一事件要重试，应由外层先做幂等判断并使用新的结果／回执路径。

## 验证与样本

单元测试覆盖硬上限、命令边界、输入校验、超时终止、Provider 失败、结构化输出和回执去敏：

```text
python -m unittest discover -s tools/claude-headless/tests -v
```

[`samples/2026-08-12-readonly-review.prompt.txt`](./samples/2026-08-12-readonly-review.prompt.txt) 是一次真实只读巡视输入；同目录的 result 与 receipt 是实际 `claude -p` 返回和成本回执。首次调用返回非零且没有可归类错误，包装器没有自动重试；人工复核后的 `plan + haiku` 调用显示同时使用 Haiku 与 Sonnet、成本 `$0.0336003`，因此留下 `plan-attempt` 证据并收窄为 `dontAsk + 完整 Haiku ID`；下一次样本只使用 Haiku、成本 `$0.02747`，但 thinking token 和 50.05 秒耗时仍偏高，因而最终固定 `low` effort 并加入成功后模型／成本反查。

Claude Code 2.1.229 的 JSON-schema 样本即使命令固定 `--max-turns 1`，回执 `num_turns` 仍可能为 `2`；这里把 CLI 参数解释为 agentic turn 上限，不把它写成“只发一次 Provider API 请求”。真正的硬停止面是客户端预算和外层进程超时。最终 `low` effort 样本只使用请求的 Haiku 完整模型，28.056 秒完成，客户端估算成本 `$0.016046`，低于 `$0.10` 上限；这只证明当前版本、当前主机上的一次有界调用成功，不证明长期成本、稳定性、产品采用或常驻运行价值。

## 明确不做

- 不提供启用工具、`bypassPermissions`、Session resume 或持久化的开关；
- 不安装 Agent SDK，不修改用户级 Claude 配置或交互 Session 默认权限；
- 不把 LLM 放入心跳、TTL、去重、轮询或其他机械路径；
- 不替调用方保存 prompt 或原始 Provider envelope；需要审计输入时由调用方在自己的授权边界内保存去敏材料。
