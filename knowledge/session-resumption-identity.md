# K8：编码 Agent 会话恢复必须绑定精确身份

> 状态：正式当前公共知识。
> 最近核验：2026-08-12。
> 适用对象：Codex CLI、Claude Code 与 Orca 编排下的会话恢复和任务接手。
> 环境：Windows 11；原核验使用 Orca 1.4.177、Codex CLI 0.147.0、Claude Code 2.1.227；2026-08-12 以 Claude Code 2.1.228 一手文档复核 checkpoint／resume 边界。
> 版本边界：任一 Provider 的 resume 语义、转录保留规则或 Orca 的活派接管能力变化时，相关结论需重新核验。

## 回答的问题与价值门

在多终端、多 Session 并发环境中，怎样恢复指定编码 Agent 会话？“恢复同一会话”“让新 Session 接手 Worker 任务”与“让新协调 Session 继任既有 Run”是否是同一件事？

精确恢复、Worker 任务接手与协调者 Run 继任在长程任务中会重复发生；本机已有一次在并发现场用“最近会话”选择器恢复错对象、并需要负责人介入的真实事故。本结论能直接避免错接任务和错中断进程，也解释 Worker 与协调者两类接手为什么必须分开，通过价值门。

## 可直接复用的结论

### 1. 并发现场只用精确会话身份

Codex 的 `resume --last` 会选取当前工作目录中最近会话；Claude Code 的 `--continue` 也是当前目录最近会话。这两个选择器描述的是时间与目录，不是目标执行者的身份；同目录存在多个会话时，只能用 Session ID 或已核对的 Session name 精确恢复。

本机的反例是：在并发现场执行 `codex resume --last` 恢复了根 Session，而非目标 Worker。故障虽在文件修改前被发现，后续按不完整进程身份处置时又影响了正确根 Session。

### 2. 会话恢复、Worker 任务接手与协调者 Run 继任是三种能力

- **恢复同一会话**：依赖 Provider 的 Session ID 和本机转录，继续该会话的对话历史。
- **新 Session 接手 Worker 任务**：依赖外部持久合同重建目标、授权、证据和写入所有权，不依赖旧对话仍在。
- **新协调 Session 继任既有 Run**：依赖 GitHub 合同恢复目标与授权，再按 Orca 当前动态指南恢复 Run 的协调者绑定、Delivery 消费权和既有 Worker 生命周期；它保留原 Task／Dispatch，不等于把 Worker 活派换绑到另一终端。完整边界与 0–8 步协议见 [K12（协调者压缩存续与继任协议）](./coordinator-succession-protocol.md)。

Orca 1.4.177 的可见 CLI 没有把一个正在运行的 Worker 活派重新绑定给第二终端的动词；对已活派任务二次活派会被状态机拒绝。因此 Worker 接手路径是建立新活派，再从 GitHub Issue 合同恢复；不把协调者 Run 绑定能力外推为“移动 Worker 活派”。

### 3. 恢复对话历史不等于恢复完整启动状态

Claude Code 恢复后会带回对话、工具记录与部分 Provider 状态，但某些启动参数需重新传入，标准 settings 会在启动时重读，`plan`／`bypassPermissions` 权限模式不恢复；依赖 `--mcp-config`、`--settings`、`--plugin-dir`、`--add-dir` 等启动面时仍须重传。Codex 的 `/compact` 会用摘要替换早期可见轮次，本批没有找到官方对摘要无损保留所有决定与因果的保证。

所以，继续会话前仍应重新核对当前任务合同、环境与启动参数；跨 Session／Provider 必须持久保畘的目标、授权、决定和因果，不能只存在聊天转录中。

### 4. Claude checkpoint／resume 只补强 Provider 局部恢复，不替代 K8／K12

Claude Code 2.1.228 的一手文档复核显示，checkpoint 是单 Session 内对 Claude 文件编辑工具改动的局部撤销：它不覆盖 Bash 造成的文件系统变更，通常不覆盖 subagent、外部并发编辑或链接文件，也不是 Git。resume 恢复的是精确 Provider 会话及其部分状态，不恢复上节列出的权限与启动面。

因此，checkpoint 能帮助撤销一部分 Claude 编辑，resume 能帮助回到选定对话，但二者都不能证明 GitHub 合同仍有效、worktree 与外部系统状态正确、Orca Task／Dispatch／Delivery 仍属于同一执行事实，或并发修改已经安全回退。K8 的精确 Session ID／显式 name 规则继续是 Provider 身份前件；[K12（协调者压缩存续与继任协议）](./coordinator-succession-protocol.md)的 GitHub 合同／Orca 执行事实／Provider 会话三层恢复继续不可互换。

## 第一方来源与证据映射

1. [关联 #43（Agent 系统全局架构与投资组合）的长程工作、Session 恢复与对齐调研回执](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253461458)：记录当日 Codex／Claude Code 官方文档与本机 CLI help 复核，以及错误恢复真实样本；支持结论 1、3 和“会话恢复／Worker 任务接手”的区分。
2. [关联 #44（实施已批准 D1–D6）的 S5 探测回执](https://github.com/Eridanus117/agent-control/issues/44#issuecomment-5254413472)：记录 Orca 无 rebind 动词、重复活派被状态机拒绝，并将当前接手终态定为“新活派＋从 Issue 合同恢复”；支持结论 2。
3. [关联 #95（协调者压缩存续与继任协议）调研交付](https://github.com/Eridanus117/agent-control/issues/95#issuecomment-5258844877)：读取 Orca 1.4.177 的 Run 绑定与 Worker 生命周期现行合同，区分 Provider 恢复、Worker 活派边界与协调者 Run 继任；支持结论 2 的三分增补。该来源没有真实继任样本。
4. [关联 #203（Claude Code 本体能力面调研）研究交付](https://github.com/Eridanus117/agent-control/issues/203#issuecomment-5270830002)与[负责人决定回执](https://github.com/Eridanus117/agent-control/issues/203#issuecomment-5271454219)：于 2026-08-12 复核 Claude 官方 checkpointing／sessions 文档和本机 2.1.228 环境，保存覆盖范围、恢复与不恢复状态、失效条件和未运行项，并批准 C4 增量修订；支持结论 3、4，不支持 checkpoint 已覆盖外部并发或完整恢复链。

## 两道准入门逐项判定

| 准入项 | 判定 | 依据 |
| --- | --- | --- |
| 价值门 | 通过 | 长程、并发与换 Session 任务会重复使用，且已有错对象事故。 |
| 1. 明确回答的问题 | 通过 | 问题限定为精确会话恢复、任务接手与启动状态边界。 |
| 2. 可直接使用的结论和必要解释 | 通过 | 给出精确 ID 规则、三种能力的分界和恢复前核对要求。 |
| 3. 第一方来源或可重复验证过程 | 通过 | 调研回执保存官方来源核对范围与本机实例，S5 保存可重复的 Orca 状态机探测。 |
| 4. 对象、版本、环境和核验时间 | 通过 | 页首列明三个工具的版本、Windows 环境与日期。 |
| 5. 例外、仍未知内容和不能推出的结论 | 通过 | 下节明确排除跨主机、转录完整性与未核验版本的泛化。 |
| 6. 明确的失效条件 | 通过 | 下节列出 Provider、Orca 与转录保留语义变化。 |
| 7. 下次最少复核步骤 | 通过 | 只需核对三个 help／官方说明，真实任务可以作自然样本。 |
| 8. 人容易理解、Agent 足以复用的表达 | 通过 | 中文自足正文先分两种能力，再给执行规则与边界。 |
| checkpoint／resume 增量候选的价值门／可信门 | 均通过 | 更新既有知识且会在 Claude 恢复中反复使用；一手官方文档复核给出可执行边界、2.1.228／Windows／日期、例外、失效条件与最少复核步骤，结论只到“局部补强”。 |

## 例外、未知和不能推出的结论

- 本包没有核验 Codex 转录的默认保留期、compact 后的实测保真度、Claude 转录的跨主机迁移，也不能推出任一 Provider 会保留全部授权与环境。
- “精确 ID 恢复”只解决选对转录，不证明任务合同、权限、工作树或外部系统状态仍然正确。
- Claude checkpoint 只跟踪其文件编辑工具覆盖的局部改动；不能推出 Bash、subagent、外部并发、链接文件或 Git 状态已回退。resume 也不能推出权限模式、启动参数、Orca 执行事实或 GitHub 合同已经恢复。
- Orca 结论限于 1.4.177 的可见 CLI 与 S5 实测；没有核验 UI、未公开接口或后续版本。
- 协调者 Run 继任只有只读推演、无真实继任样本，证据最多支持当前交付验收；普通 Run 的竞争接管与围栏语义仍未知。
- 对话历史可读不等于外部合同完整；本包没有测得两者在超长自然任务中的恢复时间或遗漏率。

## 失效条件

1. Codex 或 Claude Code 改变最近会话选择器、精确 ID／name 恢复、转录或启动状态语义；
2. Orca 增加经验证的活派 rebind 能力，或不再拒绝对已活派任务二次活派；
3. 该任务转到另一主机、云端运行面或未核验 Provider；
4. 实测显示用精确 ID 仍恢复错对象，或恢复后的必要状态与本包边界不一致。
5. Claude Code 改变 checkpoint 对 Bash／subagent／外部编辑／链接文件的覆盖，或改变 resume 对权限模式、settings 与启动参数的恢复语义。

## 下次最少复核步骤

1. 运行 `codex resume --help`、`claude --help` 和版本匹配的 Orca orchestration 指南，确认最近会话选择器、精确 ID／name、Worker 活派边界与协调者 Run 继任语义表面未变；Claude 版本变化时只复核官方 checkpointing／sessions 的覆盖与恢复状态小节。
2. 只打开上节相关远端回执，核对当日官方页面的具体小节和 S5 的探测步骤；没有变化时直接复用。
3. 下一次自然恢复任务时，在执行前记录目标 Session ID 并在恢复后核对转录中的任务标识、权限模式和任务所依赖的启动参数；任一不一致即让受影响结论退出当前知识。只在真实恢复需要中记录 checkpoint 覆盖，不为复核主动制造并发编辑或破坏性 rewind。

## 不适用范围

- Provider 转录的长期备份、隐私、加密与保留策略；
- 跨主机或云端 Session 迁移；
- 任务合同本身的编写规则；
- Provider 与 Orca 之外的编排器。
