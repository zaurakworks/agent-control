# Windows 默认执行权限：受限调研结论

> 日期：2026-08-09。状态：调研已完成；负责人最终选择维持现状、不执行试点。本文保留方案证据，长期决定见 [`../authority/08-mvp-implementation-direction.md`](../authority/08-mvp-implementation-direction.md)。

## 结论先行

不建议现在同时收紧 Codex 和 Claude，也不建议直接把当前全自动习惯判定为错误。

当前值得验证的不是“人是否应该频繁批准”，而是：**在完全不增加人工批准的前提下，Codex 的工作区边界是否几乎没有使用成本。**

推荐只做一次 Codex 真实任务试点：保持 `approval_policy = "never"`，临时把单次 Session 的执行范围从整台主机改为工作区。Claude 暂时维持 `bypassPermissions`，不与本次试点捆绑。

原因：

- 负责人明确重视低打断和长程自主，当前也没有已知的权限事故；不能凭抽象风险牺牲这项体验；
- Codex 官方把“是否询问”和“命令能访问哪里”分开控制，因此存在“零询问但有工作区边界”的低复杂度组合；
- 本机 Codex 已配置较强的原生 Windows `elevated` 沙箱，只是当前 `danger-full-access` 使它没有形成边界；
- Claude 的原生 Windows 版本没有 Bash 沙箱。它的 `auto` 模式是模型检查，不是操作系统边界，并会增加调用和等待时间；
- 两端能力不对称，不应为了表面统一而选同一种策略。

## 先分开三个概念

| 控制 | 回答的问题 | 是否会打断人 |
|---|---|---|
| 批准策略 | 行动前是否询问负责人 | 可能 |
| 沙箱 | 命令实际能访问哪些文件和网络 | 不一定；可以完全不询问 |
| 模型自动检查 | 由另一个模型判断行动是否越界 | 通常不打断，但有调用、等待和误拦截成本 |

负责人需要的是默认自主执行；这不自动要求命令拥有整机访问权。

## 本机事实

只读取了版本和权限相关键，没有读取凭据值或规则内容。

| 项目 | 当前事实 |
|---|---|
| Codex | `0.147.0`；普通 Windows 与 Orca 两套配置都是 `approval_policy = "never"`、`sandbox_mode = "danger-full-access"`、`[windows] sandbox = "elevated"` |
| Claude Code | `2.1.221`；用户默认是 `bypassPermissions`；没有启用沙箱 |
| Claude 规则 | 有 1 条 allow、1 条 ask、1 条 deny；未读取内容。官方规则说明 ask 与 deny 在 `bypassPermissions` 中仍然有效 |
| 配置覆盖 | 当前项目没有 Codex/Claude 项目级权限配置；没有发现列明路径中的 Claude 本地或托管覆盖文件 |

因此，本机 Codex 是“无询问、无沙箱”；Claude 是“跳过常规询问，但仍受少量显式规则和内建保险限制”。

## 官方能力与限制

### Codex

- OpenAI 明确说明沙箱与批准是两个控制：`never` 可以与任意沙箱模式组合；只有 `--yolo` / `danger-full-access` 同时取消沙箱和批准。[Agent approvals & security](https://learn.chatgpt.com/docs/agent-approvals-security)
- 原生 Windows 的 `elevated` 沙箱使用低权限用户、文件权限边界和防火墙规则；官方建议需要自主运行时保留边界，并可把批准策略设为 `never`。[Windows sandbox](https://learn.chatgpt.com/docs/windows/windows-sandbox)
- 工作区沙箱会保护工作区中的 `.git`、`.agents` 和 `.codex` 等路径，并默认限制命令的整机文件与网络访问。[Sandbox](https://learn.chatgpt.com/docs/sandboxing)
- Codex 的自动审查只检查本来需要批准的行动，会增加额外模型调用；它是第二阶段候选，不是本次最低成本方案。[Agent approvals & security](https://learn.chatgpt.com/docs/agent-approvals-security)

### Claude Code

- `bypassPermissions` 跳过常规批准，包括受保护路径；Anthropic 只建议在容器或虚拟机等隔离环境使用。显式 ask/deny、部分连接器、MCP 交互要求和根目录/主目录删除保险仍会生效。[Permission modes](https://code.claude.com/docs/en/permission-modes)
- Claude 的 Bash 沙箱支持 macOS、Linux 和 WSL2，不支持原生 Windows。[Sandboxing](https://code.claude.com/docs/en/sandboxing)
- `auto` 模式用独立分类模型检查行动，能针对越出请求、陌生基础设施和敌意内容进行拦截；但检查会增加一次往返，某些账户还会计入 token。连续拦截 3 次或累计 20 次后会恢复人工批准，非交互运行则可能中止。[Permission modes](https://code.claude.com/docs/en/permission-modes)
- 官方计划从 2026-08-14 起把 `auto` 作为部分新 Session 的默认模式，但用户已显式设置的默认值不会被静默替换；本机的 `bypassPermissions` 因此不会自动改变。[Permission modes](https://code.claude.com/docs/en/permission-modes)

## 方案比较

| 方案 | 人工打断 | 新增运行成本 | 影响范围 | 当前判断 |
|---|---:|---:|---|---|
| A. 维持两端现状 | 最低 | 最低 | Codex 与 Claude 命令都可影响整台主机 | 合理基准；没有证据要求立即放弃 |
| B. Codex `never + workspace-write`，Claude 不变 | 理论上为零 | 无额外审查模型；可能出现命令被拒绝和绕行 | Codex 收到工作区边界，Claude 不变 | **推荐先试** |
| C. Codex 自动审查、Claude `auto` | 通常较低，误拦截后可能恢复询问 | 额外模型调用、等待和误判处理 | 由模型检查风险；Claude 原生 Windows 仍无系统边界 | 有价值，但不是最低成本第一步 |
| D. 两端默认人工批准 | 高 | 人的持续注意力成本高 | 较容易在关键行动前停止 | 与主要体验冲突，当前不推荐 |

## ROI 判断

现在无法诚实计算“权限事故减少了多少”：没有事故频率、损失记录或对照数据，负责人也说明本机缺少明显的高价值私域资料。把风险数字化会是假精确。

风险也不只来自模型本身是否“聪明”：错误命令目标、仓库或网页中的敌意指令、第三方工具行为都可能扩大影响。但这些风险存在，并不能反向证明它们在这台机器上的预期损失一定很高。

但可以低成本测量边界带来的摩擦：

- 如果工作区沙箱不增加人工批准，真实任务仍能完成，保护收益即使很少也几乎是净增；
- 如果它频繁阻断网络、跨仓或工具链，让 Agent 反复绕行，那么当前全访问模式可能更符合这台专用机器的 ROI；
- 因此试点只验证**使用成本和边界是否真实生效**，不假装一次试点能证明未来事故被避免。

## 推荐的最小试点

### 范围

- 只选一个自然出现、主要在单一仓内完成的真实任务；不制造专门的复杂实验；
- 只启动一个临时 Codex Session，使用 `--sandbox workspace-write --ask-for-approval never`；
- 不修改两份默认配置，不改变 Claude；退出 Session 即恢复现状；
- 先用一个无价值的标记文件做工作区外写入检查，确认写入被拒绝，再执行真实任务；
- 以完成一个任务或经过 60 分钟为上限，先到者停止。

### 只记录五项数据

1. 真实任务是否完成；
2. 是否出现人工批准；
3. 被边界拒绝的行动次数；
4. 为绕开拒绝额外花了多少时间；
5. 是否存在任务必需的工作区外写入或命令行联网。

不建设遥测平台，不记录完整对话，不为了数据重复运行任务。

### 通过条件

- 工作区外写入检查确实被拒绝；
- 人工批准次数为 0；
- 真实任务完成；
- 被拒绝行动不超过 3 次，且调整路径累计不超过 10 分钟；
- 没有任务必需的整机写入能力。

全部满足时，才提议把 Codex 默认改为“无询问 + 工作区边界”；仍需负责人另行批准。

### 立即退出条件

- 到 60 分钟仍未完成；
- 出现无法替代的工作区外写入或命令行联网需要；
- 边界造成方向漂移、重复失败或需要人持续介入；
- 为了让试点通过，必须开始治理 Rules、Hooks、MCP、Plugins 或 WSL。

退出只表示该默认策略在当前工作方式下成本偏高，不表示沙箱机制错误。退出后继续使用现有 yolo 配置。

## 当前不建议做的事

- 不先切换 Claude `auto`：它混入分类模型成本和误拦截，且不能提供原生 Windows 系统边界；
- 不现在迁移 WSL：这会把运行环境迁移、旧配置治理和权限策略混为一个项目；
- 不先设计细密 allow/deny 规则：会增加 Agent 判断、维护和人的理解成本；
- 不同时试两端：出现任务失败时将无法判断是哪一个变化造成的。

## 下一决策点

决策已完成：不执行上述试点。Codex 继续使用 `never + danger-full-access`，Claude Code 继续使用 `bypassPermissions`；两端配置均未修改。
