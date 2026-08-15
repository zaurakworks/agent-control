# K12：协调者压缩存续与继任协议

> 状态：正式当前公共知识。
> 最近核验：2026-08-13。
> 修订版：9（补入 Orca 1.4.180→1.4.181 自动更新清场事件、`input-missing` 第二机制与 1.4.181 自然高层验活样本；此前实现精确 Dispatch 的 Codex JSONL 三态验活并替代终端刮屏／固定 30 秒猜测，增补 fresh Codex 四样本的 `codex_apps` 有界相关性、Claude checkpoint／resume 局部恢复边界、D9 首次真实易主让位、resume cron 查重、D9 租约交割、C9 停门、C10 可发现性与 C11 巡检唯一定位面）。
> 适用对象：本机 Windows 上，由 Orca Run 承载的多 Session 受监督协作；继任者需要从远端恢复协调职责，而不是恢复一段聊天。
> 环境：Windows 11；0–8 步原核验使用 Orca 1.4.177 packaged；resume、重派、首次计划性交接、W5 与 fresh Codex 自然样本使用 Orca 1.4.180 packaged；自动更新清场、低层／高层派发对照与最新自然验活使用 Orca 1.4.181 packaged；Provider 增量边界来自 Codex CLI 0.147.0 与 Claude Code 2.1.228–2.1.229。
> 版本边界：Orca 的 Run 绑定、Delivery、Worker 生命周期或协调者围栏语义变化时，受影响结论必须先退出直接复用。
> **证据标记（分层）：已有一次无待处理 Delivery、无在途 Worker 的真实计划性交接，覆盖稳定 Run 绑定、`consumer_generation` 唯一前进与 D9 易主让位；完整 0–8 步在途收养仍无真实样本。同 Session resume 复活 cron 有一例；另有一次 1.4.180→1.4.181 自动更新清场事件，覆盖 Worker PTY 清除、终端句柄重注册、Run generation 3→4 重绑与沿原 Task 重派。dispatch-race 基线、fresh Codex `codex_apps` cohort 与 JSONL 三态适配器仍按正文分层；1.4.181 新增低层 `input-missing 5/5` 对照和两个自然 Codex“已开始”样本。证据最多支持当前环境的样本有效／当前交付验收，不支持稳定率、跨 Provider 通用性或产品采用。** 除第 5 条已批窄例外、结论 6 的自然恢复分支及上述自然样本外，本包的未覆盖分支仍来自只读推演；没有迁移在途 Worker 或处理待确认 Delivery。

## 回答的问题与价值门

协调 Session 经反复压缩或意外终止后，新 Session 怎样恢复同一棵任务子树的目标、授权、Orca 执行事实与在途 Worker，同时避免双协调、重复派发和误消费负责人动作？哪些状态可以从远端恢复，哪些只能重建或如实标为遗失？

该问题会在长程、多 Session 协作和计划性交接中反复出现；一次误判即可造成竞争 Run、重复派发、遗漏 Delivery 或误处置 dirty worktree。本包还增量补足 [K8（编码 Agent 会话恢复必须绑定精确身份）](./session-resumption-identity.md) 未覆盖的“协调者 Run 继任”，并复用 [K2（Orca 受监督派发的路径选择、mutation 回执与收口核验）](./orca-supervised-dispatch.md) 的回执、派发和资源边界，因此通过价值门。

## 2026-08-13 的 1.4.181 版本边界复核

Orca 自动更新命中本包的升级失效条件，因此先按最少步骤复核而不是静默沿用 1.4.180：当前 `orca status --json` 返回 app `1.4.181`、runtime `ready`；从同一二进制读取的完整 orchestration 指南仍保留 Run／Task／Dispatch／Delivery、`consumer_generation`、高层 Worker 复用／释放与显式确认前 Delivery 重放语义。关联 [#207（Mode B P0 前检）](https://github.com/Eridanus117/agent-control/issues/207)保存了更新当时的自然恢复链，关联 [#211（tui-idle 竞态对照）](https://github.com/Eridanus117/agent-control/issues/211)和关联 [#216（Mode C 混合试点第一阶段）](https://github.com/Eridanus117/agent-control/issues/216)分别补了低层失败面与高层自然验活面。

**复核结论**：三层恢复、Worker 活派与协调者 Run 继任分离、Delivery 后确认和高层 Worker 生命周期继续可复用；更新事件新增“应用重启清场”分支，派发验活新增 `input-missing`，但没有证据把普通 Run 的失联围栏、完整在途收养或离线唤醒从未知升级为已具备。

## 可直接复用的结论

### 1. 继任恢复分三层，任一层都不能替代另外两层

| 层 | 恢复什么 | 唯一用途 | 不能推出什么 |
| --- | --- | --- | --- |
| GitHub 合同层 | 当前目标、范围、成功条件、原生关系、有效决定与授权 | 重建“为什么做、允许做什么、怎样验收” | 当前有哪些在途 Worker、未签收 Delivery 或本地草稿 |
| Orca 执行事实层 | Run、Task、Dispatch、Delivery、Worker、终端与 worktree 的当前身份和状态 | 重建“谁在做什么、消息是否处理、资源归谁” | 用户目标、产品决定或 GitHub 合同 |
| Provider 会话层 | 精确 Session ID／name 对应的对话与转录 | 确需继续原对话时选择正确会话 | 当前合同、权限、工作树、Orca 状态或完整启动参数 |

继任者必须先从 GitHub 与 Orca 恢复合同和执行事实；Provider 会话恢复只是可选的第三层。恢复原对话不等于获得协调权，新建 Session 也不等于必须重派 Worker。

Claude Code 的 checkpoint／resume 只补强表中的 Provider 会话层：checkpoint 仅撤销同一 Session 中 Claude 文件编辑工具覆盖的局部改动，不覆盖 Bash、通常不覆盖 subagent、外部并发编辑或链接文件，也不是 Git；resume 恢复对话与部分 Provider 状态，但不恢复 `plan`／`bypassPermissions`，依赖的 MCP、settings、plugin 与额外目录启动参数仍须重传。它们不能替代 GitHub 合同层或 Orca 执行事实层，完整 Provider 身份边界见 [K8（编码 Agent 会话恢复必须绑定精确身份）](./session-resumption-identity.md)。

### 2. Worker 活派接手与协调者 Run 继任是两种不同的运行语义

K8 的“活派不能换绑到另一终端”约束仍适用于 Worker：不能把协调者 Run 的绑定能力外推为 Worker Dispatch 的换绑能力。协调者继任处理的是既有 Run 的协调者绑定和 Delivery 消费权；成功继任应保留原 Run、Task、Dispatch、Worker 进程与 worktree 身份。

具体动作、参数和恢复分支只从即将执行它们的同一个 Orca 二进制动态读取；本包保存稳定语义、输入、验证面与停止条件，不保存命令清单。计划性交接只有在旧协调者明确交出同一稳定 Run ID、活动 Issue／Task／Dispatch 来源链、写入所有权与 `consumer_generation` 基线后，才进入动态合同覆盖的写阶段；失联恢复只有在当前 Run 类型具备可核验围栏时才能写入。普通 Run 缺少可核验围栏时继续只读。

### 3. 易失状态必须逐项映射为“远端恢复、重建或遗失”

| 状态 | 主要风险 | 可恢复对应物 | 继任处理 |
| --- | --- | --- | --- |
| 目标、范围、成功条件、明确不做 | 压缩摘要改写或遗漏 | 当前 Issue 正文、原生关系、有效评论 | 从远端重读，不从旧聊天或 Run 任务文本反推 |
| 负责人原话、勘误、时限 | 摘要只保留首版口径 | 指令记录与后续修正 | 按可信主体、评论顺序和有效期恢复现行口径 |
| 决定与授权边界 | 只剩“已授权”而丢掉例外 | 决定请求、可信回复与决定回执 | 分开重建已授权、未授权、是否已消费与下一责任人 |
| Session 内存态巡检 | 把重启／resume 误当成必然清空，盲目再建后形成同 Session 双 cron | 当前指令、租约与本 Session 的 `CronList` | fresh Session 按租约接管；同 Session resume 先查重，再决定复用、去重或重建；不得称为持久调度或离线唤醒 |
| Orca 应用更新与 Worker PTY | 把 Provider 会话幸存误当成终端、句柄和在途尝试也幸存 | 更新前后的 runtime、Run generation、Task／Dispatch、终端清单与动态指南 | 先重读 1.4.181 指南并按稳定身份对账；句柄重注册后不沿用旧 handle，已死亡尝试只在原合同允许时沿原 Task 显式重派 |
| 协调者绑定 | 旧终端失效或双协调 | 稳定 Run ID、活动来源链、写入所有权、`consumer_generation` 与动态指南 | 区分计划性交接与失联恢复；普通 Run 无可核验围栏时只读 |
| 在途 Task／Dispatch | 人工清单过时、重复派发，或把 `input_accepted`／终端存活误当成已经工作 | Run 的 Task、Dispatch、Worker 记录与精确终端工作态 | 用稳定 ID 全量对账；重派后验活，只沿原身份补交一次，不凭标题、摘要或存活数重派 |
| 未签收 Delivery | 先确认后处理导致漏项 | Run 的 FIFO Delivery | 完整处理一批后才确认；心跳只证明存活 |
| Worker、终端、worktree 与未提交文件 | 视觉状态或空白被误当成已持久化 | Worker／终端记录、Git 状态、已发布提交或 PR | 精确核对身份；dirty worktree 保留，未提交文件没有远端副本 |
| Worker 生命周期处置意图 | “准备释放”等意图只留在记忆 | 当前生命周期回执 | 以真实回执为准；超时、心跳与 TUI 空闲均不触发处置 |
| Provider 转录与启动参数 | 最近会话选择器接错对象 | 精确 Session 身份与本机转录 | 精确恢复后仍重读合同、环境与启动参数 |
| 临时草稿与未外显推理 | 新 Session 无法取得 | 只有已进入 Issue、PR、提交或当前知识的外化内容 | 找不到远端产物即标为遗失，不补写成前任计划 |
| 动态账户与容量快照 | 旧读数快速过期 | 继任时的当前观测面 | 重新读取，不沿用旧百分比或把容量当成交付结果 |

“协调 Session 会被长期保留”是使用意图，不是内存态持久性保证。只有已经外化的合同、执行事实和精确身份可以恢复；内存态要么按当前有效指令重建，要么如实列为遗失。

### 4. 压缩后的最小存续锚点是六个坐标，不是一篇万能摘要

| 锚点 | 保住什么 | 不承担什么 |
| --- | --- | --- |
| 活动 Issue | 当前持久合同、范围、成功条件与来源链 | 实时执行态和未发布草稿 |
| Run ID | 找回同一 Run 的 Task、Dispatch 与 Delivery；Run 目标文字只作创建时的历史标签 | 用户授权、产品目标，也不单独充当继任停门 |
| 指令记录 | 负责人原话、修正、节律和期限 | 当前循环是否仍在运行 |
| 授权／决定记录 | 决定权、边界、已消费动作与翻转条件 | Orca 当前状态 |
| 最近波次回执 | 最近阶段的交付、事故、证据等级与下一检查点 | 实时任务队列 |
| 动态 Orca 指南 | 当前命令、对象模型与生命周期合同 | GitHub 合同、用户目标和产品决定 |

恢复指针只负责定位活动 Issue、Run、观察水位与未解决冲突；它不镜像实时 Task 清单。研发记忆保存因果与失败样本，但不产生当前授权。

### 5. 租约只防跨 Session 易主；resume 后还要 cron 查重与重派验活

Session 内巡检 cron 是 session 作用域：fresh 协调者看不到、也停不掉旧 session 的调度器。[关联 #172（协调者操作模式收敛）D8/D9/D11 决定回执](https://github.com/Eridanus117/agent-control/issues/172#issuecomment-5266705644)批准的租约协议以一个仓外持久文件交割单调度权；同一个 Provider Session 被 resume 时则先检查原 cron 是否一起复活：

- **租约文件**：`%LOCALAPPDATA%\agent-control\scheduler-lease.json`，字段至少含 `coordinator`（协调者标识，`session` 为其具体组成）／`session`／`cron_id`／`takeover_at`／`last_tick`；
- **fresh 接管方**：新协调者接管时先改写租约（写入自己的 session 标识），再建立自己的巡检 cron，且 cron 提示词第 0 步必须是租约检查；
- **让位方**：每个 tick 先读租约；`session` 字段与自己不符＝调度权已易主，立即删除自己的 cron、停止一切共享面写入，只输出让位回执；
- **同 Session resume**：核对租约仍指向本 Session 后，先用 `CronList` 查重，再决定是否重建。零项才新建；恰有一项且符合当前指令就复用；多项时只保留一项，删除身份与所有权均明确的本 Session 重复项，无法判定时停止写共享面。租约中的 `session` 相同，不能替这一步发现双 cron；
- **重派验活**：恢复既有 worktree 并沿原 Task／Dispatch 重派后，Codex 先运行 [`tools/codex_liveness`](../tools/codex_liveness/README.md)，用精确 `taskId + dispatchId` 读取 rollout 三态；只有“已开始”证明 Provider 已创建关联 turn。“未提交”／“已提交”只是当前快照，不从 `input_accepted`、固定 30 秒、终端存活、心跳或 live 数量猜测开始，也不单独触发补交、重派、失败或释放。Provider 精确观察还要区分文本留在 composer 的 `composer-pending` 与文本根本未呈现的 `input-missing`：一次 Enter 只适用于前者，后者保持失败证据并停止，不创建第二个 Task、Dispatch 或 Worker。JSONL 不可读、schema 失效或其他 Provider 才退回其精确观察面；
- **Provider 事件适配器（已实现）**：`codex exec --json` 的 `thread.started`／`turn.started` 与持久 rollout 的 `event_msg/task_started` 形状不同；工具分别解析，batch stdout 只有在调用者已把捕获文件排他绑定到精确 Dispatch 时才使用。它不创建 batch 派发、不改变现有 worker 路径，且 `turn.started` 不替代 Orca 生命周期或其他 Provider 的开始证据；
- **兜底**：负责人直接关闭旧协调者终端仍然有效，且是最强保证。

证据分层：D9 租约协议由上述决定回执批准；当前样本先覆盖「租约建立＋当前持有者逐 tick 检查通过」，随后取得四组 2026-08-12、Orca 1.4.180 的增量自然证据：

1. [关联 #172（协调者操作模式收敛）重启后调度事实](https://github.com/Eridanus117/agent-control/issues/172#issuecomment-5268487239)记录 resume 复活重启前 cron，新建 cron 后形成同 Session 双调度器，`CronList` 查重删除旧项；
2. [关联 #172（协调者操作模式收敛）重派验活事实](https://github.com/Eridanus117/agent-control/issues/172#issuecomment-5268591611)记录 5 个复用既有 worktree 的 Codex Dispatch 均显示 `input_accepted` 却在提示符空转约 40 分钟，沿原 Task 身份点火后全部进入工作态；
3. [关联 #172（协调者操作模式收敛）首次真实计划性交接回执](https://github.com/Eridanus117/agent-control/issues/172#issuecomment-5269558988)记录租约于 16:22Z 易主后，前任在 16:26Z 的下一 tick 读到新持有者、自删 cron `d2439b1c`、输出让位回执并停止共享面写入；此后租约 `last_tick` 未被前任再写。同一接管回执还记录第三个 dispatch-race 自然事件：Task `task_b506c16f73bd`／Dispatch `ctx_54bba59b302b` 返回 `input_accepted` 后仍停在输入框，沿原身份补交一次后进入工作态；
4. 本机同一 Run `run_65a73145f0e2` 的 W5 审阅 Task `task_5cceed05ece9`／Dispatch `ctx_2ac6cc659fff` 记录第四个 dispatch-race 自然事件：16:51Z 返回 `input_accepted`，首次精确验活仍无法确认工作，沿原终端 `term_714285f1-02f6-489e-bf2a-ee7dfe8be0df` 补交一次；补交约 20 秒后仍显示 `Out: 0`／`Total: 0`，再过约 30 秒复核才进入工作态，最终正常交付[关联 #145（生命周期可重入收口）席 A 审阅](https://github.com/Eridanus117/agent-control/issues/145#issuecomment-5269878475)与[关联 #147（行动前双门）席 A 审阅](https://github.com/Eridanus117/agent-control/issues/147#issuecomment-5269879598)。
5. [关联 #184（协调者运营与管理能力）波次回执](https://github.com/Eridanus117/agent-control/issues/184#issuecomment-5271396248)另行冻结同一 1.4.180 Run 中 V1／V6／V7／S1 四个 fresh Codex 自然样本：4/4 在竞态发生时伴随 `MCP startup interrupted` 或 `starting: codex_apps` 签名，四例均沿原身份一次点火恢复且零重派；[关联 #31（Orca 生命周期断裂）补充样本](https://github.com/Eridanus117/agent-control/issues/31#issuecomment-5270706519)保存其中两例的输入框与零输入输出细节。该 cohort 只支持相关性线索，不支持 MCP 因果或固定发生率。
6. [关联 #204（Codex CLI 本体能力面调研）研究交付](https://github.com/Eridanus117/agent-control/issues/204#issuecomment-5270952054)记录 Codex CLI 0.147.0 的一次非交互只读探针实际发出 `thread.started`、`turn.started`、`turn.completed`；[负责人决定回执](https://github.com/Eridanus117/agent-control/issues/204#issuecomment-5271454711)批准把该验活面作为知识候选。本样本只证明事件可用与语义更强，不证明 Orca 映射、自然竞态收益或适配器已实施。
7. [关联 #209（L2 turn.started 验活面）](https://github.com/Eridanus117/agent-control/issues/209)实现精确 Dispatch 三态工具，并在本机 Codex 0.144.5／0.147.0 两个真实历史 rollout 上验证“已开始”；它证明适配器当前可用，不证明自然竞态收益、跨 Provider 通用性或产品采用。

第 2–5 项与 [K2（Orca 受监督派发）](./orca-supervised-dispatch.md) 已验证的“输入停在输入框、补 Enter 后启动”共同支持同一纪律。修订版 6 的“四例”是当时按自然事件／证据批混合口径冻结的历史基线，其中 5/5 重派是一批证据；本次不把四个 fresh Codex 样本硬并入该混合总数，而把它们保留为单独的 `n=4` cohort，避免把 Worker 数与批次数相加成伪精确累计。**既有基线与新增 cohort 都不能推出固定发生率、固定等待时长、点火后的固定生效时延、MCP 因果或通用触发原因；JSONL 适配器的两个历史样本也不能证明自然竞态收益。首次易主让位只验证单次同机正向路径，不能推出固定让位时延或所有 Provider 通用性；完整 0–8 步在途 Worker／Delivery 收养仍无真实样本。**

**授权与边界**：本条是对本包「不重挂巡检循环、不建立调度器」原边界的**窄例外**，仅限关联 [#172（协调者操作模式收敛）](https://github.com/Eridanus117/agent-control/issues/172)D9 已批的租约建立、租约检查、自身 cron 自管，以及现有受监督 Dispatch 的提交验活；离线唤醒、自动接管其他 Session、处置无所有权 cron、创建重复派发或修改宿主环境仍在排除范围。三态验活不是 Worker 失败、完成或释放判据；一旦进入工作态，后续仍按当前动态指南等待生命周期消息。**被替代的行为**：租约交割替代「仅靠前任自停＋负责人关旧终端」，`CronList` 查重替代「resume 后直接重建 cron」，精确 JSONL 三态替代「终端刮屏／固定 30 秒猜测／把 `input_accepted` 或存活数当作正在工作」。

### 6. 应用自动更新是独立清场事件；Session 幸存不等于执行资源幸存

2026-08-12 约 22:32–23:06Z，Orca packaged 从 1.4.180 自动更新到 1.4.181 并自重启。该次自然事件中全部 Worker PTY 被清，终端 handle 重新登记，RPC 短暂出现模块缺失后恢复；协调者 Claude Provider 会话幸存，但 Run 绑定从 generation 3 前进到 4，P0 的首次尝试终端死亡，随后按原 Task 建立新尝试。它证明应用更新是继宿主休眠之后第二类已观测的 Session 清场事件，也直接证明“Provider 对话仍在”不能推出 Orca 终端、Worker 尝试或 handle 仍有效。

遇到这类自然更新，先以新二进制重读动态指南并重新发现 runtime／Run／generation／Task／Dispatch／terminal 身份；旧 handle 与旧 PTY 只作历史证据，不作为可写目标。只有原合同允许重试且旧尝试已证明死亡时，才沿原 Task 显式建立新尝试；重绑、重派和消息处理都要写后回读。该单次事件不证明每次更新都会清空全部 PTY、所有 Provider 会话都会幸存、Run generation 固定只前进一代，或 automation 能跨更新保持正向持久性。

本条不授权主动触发更新、重启 Orca、终止 Worker、接管 Run 或处置终端；它只规定自然更新已经发生后的恢复顺序与证据边界。

## 0–8 步恢复协议（操作级，不固化命令拼写）

每一步都按“操作—验证—停止条件”执行。需要使用 Orca 时，先从本 Session 实际解析到的 CLI 动态读取版本匹配的 orchestration 指南，再选择该指南当前给出的动词和参数；下文不构成第二份命令真源。

### 先固定继任分支

| 分支 | 必要前件 | 进入写阶段的额外硬门 |
| --- | --- | --- |
| 计划性交接 | 旧协调者留下明确交接，逐项给出稳定 Run ID、活动 Issue／Task／Dispatch 来源链、写入所有权和交接前 `consumer_generation` | 当前动态指南允许绑定同一 Run，写后能按预期代次核验新消费者；交接信息缺项即只读 |
| 失联恢复 | 旧协调者无法继续的证据与目标 Run 的只读快照可取得；不得把“没有回复”本身当成已失效 | 当前动态指南对该 Run 类型提供可核验围栏，写后能证明旧消费者不再可写且 `consumer_generation` 唯一前进；普通 Run 无此保证即只读 |

两种分支的前件不能互相代替。Run 目标文字可能保留长期创建目标，与当前活动 Issue 不同；它只作背景证据，不要求与恢复指针或活动 Issue 文字相等，也不能替代稳定身份、来源链、所有权和运行代次。

### 0. 确认这是继任，不是双协调

- **操作**：读取仓库入口、权威根、恢复指针和活动 Issue 的远端正文、状态、原生关系与有效决定；按上表确定计划性交接或失联恢复，并核对目标 Run 的稳定 ID、活动 Issue／Task／Dispatch 来源链、当前写入所有权与旧协调者状态。
- **验证**：目标 Run 和活动来源链唯一，远端合同仍适用，分支前件、写入所有权及未解决冲突已经显式呈现。
- **停止条件**：旧协调者仍在线且正在协调；计划性交接缺少明确交接或任一稳定坐标；失联恢复无法证明当前 Run 类型具备可核验围栏。此时保持只读，加入现有协调或取得明确交接；不创建竞争 Run。

### 1. 载入当前工具合同并确认运行时可用

- **操作**：解析本 Session 应使用的 Orca CLI；从同一二进制读取版本匹配的完整 orchestration 指南；只读检查运行时状态。
- **验证**：动态指南与实际二进制同源，运行时可达并处于可操作状态。
- **停止条件**：指南或运行时不可取得。若动态指南与本包不同，以动态指南约束命令和生命周期，并把差异视为本包失效信号。

### 2. 只读盘点 Run、旧协调者与全部在途工作

- **操作**：按稳定 Run ID 读取 Run、`consumer_generation`、Task 图、每个在途 Dispatch、对应 Worker／终端／worktree；把活动 Issue 逐项映射到 Task／Dispatch 来源，只在状态含糊时读取有限现场输出。
- **验证**：稳定 Run ID、活动 Issue／Task／Dispatch 来源链、写入所有权与 `consumer_generation` 快照彼此一致；每个在途 Task 唯一映射到一个尝试，没有第二个活跃尝试；对象来源能区分高层受监督 Worker 与低层 Dispatch。Run 目标文字只记录为历史标签，不与当前主线作文字相等判断。
- **停止条件**：旧协调者状态不明、运行代次缺失或在快照期间变化、同一 Task 存在竞争尝试、来源映射不唯一或写入所有权冲突。低层 Dispatch 缺少高层索引时按 K2 保留对象，不重复派发，也不假设高层生命周期动作可用。

### 3. 在授权边界内绑定既有 Run

- **操作**：计划性交接按明确交出的稳定 Run ID 与交接前 `consumer_generation`，从新协调终端使用动态指南的绑定路径；失联恢复只有在动态指南对当前 Run 类型给出可核验围栏时，才使用该指南明确支持的恢复路径。两者都不冒充旧终端。
- **验证**：写后回读同一稳定 Run ID，确认 `consumer_generation` 从只读基线唯一前进到预期代次、当前消费者与围栏结果可核验，同时 Task、Dispatch 与 Worker 身份保持不变。
- **停止条件**：普通 Run 缺少可核验围栏；`consumer_generation` 未按预期前进或出现竞争变化；旧协调者仍可能写入；动作会扩大授权。此时保留只读快照，不把计划性交接路径套用于失联恢复，也不混用采用旧合同的 Run 与普通 Run 分支。

### 4. 先恢复 Delivery，再决定是否改变 Worker

- **操作**：读取 Run 的最老未确认 Delivery；逐条处理同批的完成、升级与问题。答复绑定原消息；补充指导绑定稳定 Dispatch，而不是旧终端标题或 handle。
- **验证**：同批每条消息都有明确处理结果；现有 Worker 没有被重派。
- **停止条件**：批次尚未完整处理，或某条消息需要超出当前合同的决定。此时不确认 Delivery。

### 5. 按每个 Worker 的当前状态收养

- **运行中**：保留原 Task 与 Dispatch；超时、心跳和 TUI 空闲都不等于完成。
- **已有效结算**：先独立核验远端交付；再依据当前生命周期合同选择释放，或把同一执行者交给已经建立的紧邻后继 Task。
- **已失败或停止**：只有合同允许重试时，才显式给出 placement、Agent 与前次尝试身份；不让重试继承猜测。
- **结果未知**：按动态指南在停止后复核与明确放弃之间选择；放弃不等于执行进程或文件处置。
- **验证**：每个 Worker 都有唯一当前状态、下一责任人和资源处置结论；任何 dirty worktree 均被保留。

### 6. 完整处理后才确认 Delivery

- **操作**：在问题答复、交付核验和 Worker 复用／释放选择全部完成后，以原 Delivery 身份确认该批。
- **验证**：旧批次不再作为未确认批重放；随后读到的是新批次或空结果。
- **停止条件**：任何同批动作仍未完成，或远端写入结果未知。先重读目标状态，不用重试掩盖不确定性。

### 7. 只在指令仍有效时重建 Session 内存态巡检

- **操作**：只从 [`work/current-monitoring-directive.md`](../work/current-monitoring-directive.md) 恢复当前巡检口径；历史评论只沿该页来源链审计，不再自行拼接节律、期限或产能数字。确认 `active`、唯一协调者前件和来源水位后，重新读取 Orca 当前运行面、Git worktree 状态及任务所需的资源观察面，再按动态指南建立本 Session 内的等待／检查循环。
- **验证**：恢复出的目标、节律、期限／时区、候选价值门和资源来源与定位面逐项一致；首个节拍后确实重新读取消息、任务与资源面，并只在安全条件齐全时处置孤儿 worktree。当前数量与运行进度不写回定位面。
- **停止条件**：定位面 `active` 不为 `true`、负责人来源已被更新但 `observedAt` 尚未推进、同一范围无法证明唯一协调者，或产品目标已经变化。Session 退出后循环仍会消失；本步骤不提供离线唤醒，也不因定位面存在而取得额外派发、删除或宿主环境权限。

### 8. 建立新的可恢复水位

- **操作**：把改变目标、授权、决定、交付、证据等级或下一责任人的结果写回当前 Issue／波次回执；只有活动 Issue、Run、观察水位或跨源冲突变化时才更新恢复指针。
- **验证**：另一个新 Session 只读执行第 0–2 步，能得到相同稳定 Run ID、活动 Issue／Task／Dispatch 来源链、授权边界、`consumer_generation` 与在途集合。
- **停止条件**：关键结论只存在于聊天、临时草稿或本地未提交文件。先外化可恢复事实；无法外化的内容明确列为遗失或未知。

## 第一方来源与证据映射

1. [关联 #95（协调者压缩存续与继任协议）调研交付](https://github.com/Eridanus117/agent-control/issues/95#issuecomment-5258844877)：直接核验 Orca 1.4.177 的动态指南与当前 Run，保存易失状态、压缩锚点、0–8 步协议、未知和证据上限；支持本包全部结论。
2. [关联 #95（协调者压缩存续与继任协议）决定回执](https://github.com/Eridanus117/agent-control/issues/95#issuecomment-5258952243)：确认分层承载、Skill 最短路由、description 零净增、动态指南单一命令真源及证据标记；支持本包承载与表达边界。
3. [K2（Orca 受监督派发的路径选择、mutation 回执与收口核验）](./orca-supervised-dispatch.md)：提供高层／低层对象边界、错误后先重读、Worker 收口与终端资源核验；支持步骤 2、5、6。
4. [K8（编码 Agent 会话恢复必须绑定精确身份）](./session-resumption-identity.md)：提供 Provider 精确恢复、Worker 活派不能换绑与外部合同恢复边界；支持三层恢复及能力三分。
5. [关联 #100（夜间新增资产的多视角攻防审计）交叉裁决](https://github.com/Eridanus117/agent-control/issues/100#issuecomment-5259393664)：C9 以当前长期 Run 的目标文字与活动主线不相等为反例，确认停门必须改用稳定 Run ID、活动来源链、写入所有权与 `consumer_generation`；C10 确认裸跨仓相对路径不能证明安装态可发现性。
6. [关联 #100（夜间新增资产的多视角攻防审计）交叉裁决](https://github.com/Eridanus117/agent-control/issues/100#issuecomment-5259393664)与[关联 #113（巡检口径唯一定位面）当前合同](https://github.com/Eridanus117/agent-control/issues/113)：C11 确认巡检口径分散与 15 分钟来源缺口；后者记录负责人 2026-08-12 的当前五项口径，支持步骤 7 只读唯一定位面。
7. [关联 #172（协调者操作模式收敛）重启后调度事实](https://github.com/Eridanus117/agent-control/issues/172#issuecomment-5268487239)：记录 Orca 1.4.180 环境中同 Session resume 复活 cron、盲目重建形成双调度器及 `CronList` 查重处置；支持结论 5 的 resume 分支。
8. [关联 #172（协调者操作模式收敛）重派验活事实](https://github.com/Eridanus117/agent-control/issues/172#issuecomment-5268591611)：记录同环境中 5 个 Codex 重派均 `input_accepted` 但空转、沿原 Task 点火后进入工作态；与 K2 的既有输入提交竞态共同支持结论 5 的验活分支。
9. [关联 #172（协调者操作模式收敛）首次真实计划性交接回执](https://github.com/Eridanus117/agent-control/issues/172#issuecomment-5269558988)与[关联 #172（协调者操作模式收敛）波次回执](https://github.com/Eridanus117/agent-control/issues/172#issuecomment-5269603886)：保存租约新旧持有者、接管与让位时间、前任自删 cron、让位后的负事实、Run 代次唯一前进、第三个 dispatch-race 及最终无在途 Worker／Delivery 的收口态；支持结论 2、3、5 和步骤 0–3、7–8 的窄样本。
10. 2026-08-12 本机 Orca 1.4.180 执行事实：Run `run_65a73145f0e2`、Task `task_5cceed05ece9`、Dispatch `ctx_2ac6cc659fff`、精确终端 `term_714285f1-02f6-489e-bf2a-ee7dfe8be0df` 与协调者 Session 转录共同保存第四个 dispatch-race 的 `input_accepted`、首次验活、一次补交、两次补交后复核及最终完成；远端产物为关联 [#145（生命周期可重入收口）](https://github.com/Eridanus117/agent-control/issues/145)与关联 [#147（行动前双门）](https://github.com/Eridanus117/agent-control/issues/147)的席 A 审阅评论。该来源只支持第四例，不把本地 Run 运行态提升为 GitHub 合同或产品决定。
11. [关联 #31（Orca 生命周期断裂）Y6 分析与补充样本](https://github.com/Eridanus117/agent-control/issues/31#issuecomment-5270403811)及[两例 MCP 签名增量](https://github.com/Eridanus117/agent-control/issues/31#issuecomment-5270706519)：保存窗口分布、Provider／启动状态推断边界、点火与释放非确定性，以及两例 fresh Codex 的 `codex_apps` 同现细节；支持结论 5 的边界和新增 cohort 的部分明细。
12. [关联 #184（协调者运营与管理能力）波次回执](https://github.com/Eridanus117/agent-control/issues/184#issuecomment-5271396248)：冻结 V1／V6／V7／S1 四例、4/4 MCP 启动签名、一次点火恢复与零重派；支持新增 cohort 的有界相关性。
13. [关联 #203（Claude Code 本体能力面调研）研究交付](https://github.com/Eridanus117/agent-control/issues/203#issuecomment-5270830002)与[负责人决定回执](https://github.com/Eridanus117/agent-control/issues/203#issuecomment-5271454219)：复核 Claude Code 2.1.228 checkpoint／resume 覆盖与不恢复状态，并批准 C4 修订；支持结论 1 的 Provider 局部恢复边界。
14. [关联 #204（Codex CLI 本体能力面调研）研究交付](https://github.com/Eridanus117/agent-control/issues/204#issuecomment-5270952054)与[负责人决定回执](https://github.com/Eridanus117/agent-control/issues/204#issuecomment-5271454711)：保存 0.147.0 JSONL 事件探针、成本／风险／失效条件并批准候选；支持 `turn.started` 事件语义与 0.147.0 flag 边界。
15. [关联 #209（L2 turn.started 验活面）](https://github.com/Eridanus117/agent-control/issues/209)与 [`tools/codex_liveness`](../tools/codex_liveness/README.md)：实现三态解析、精确 Dispatch 绑定、stdout／rollout 双事件形状与 flag 位置守卫，并通过两个真实历史会话验证；支持当前交付验证，不支持自然收益或产品采用。
16. [关联 #207（Mode B P0 前检）自动更新自然事件](https://github.com/Eridanus117/agent-control/issues/207#issuecomment-5273853234)与[前检交付](https://github.com/Eridanus117/agent-control/issues/207#issuecomment-5273905832)：保存 1.4.180→1.4.181 的 Worker PTY 清场、handle 重注册、generation 3→4、首次尝试死亡与沿原 Task 重派，以及更新后动态指南复核；支持结论 6，不支持 automation 正向持久性。
17. [关联 #211（tui-idle 竞态对照）实验交付](https://github.com/Eridanus117/agent-control/issues/211#issuecomment-5274155258)：保存 1.4.181 的低层 `input-missing 5/5`、高层 `submitted 5/5`、一次 Enter 对缺失态无效及 6 条低层残留；支持结论 5 的状态扩充。
18. [关联 #216（Mode C 混合试点第一阶段）试点交付](https://github.com/Eridanus117/agent-control/issues/216#issuecomment-5274571465)与[负责人验收回执](https://github.com/Eridanus117/agent-control/issues/216#issuecomment-5274677733)：两个 1.4.181 自然 Codex Dispatch 的 JSONL／人工判定均为“已开始”、分歧 `0/2`；支持版本复核与高层自然验活的小样本，不支持长期准确率。

## 两道准入门逐项判定

### 修订版 9 增量候选判定

| 候选 | 价值门 | 可信门 | 判定依据 |
| --- | --- | --- | --- |
| D9 首次真实易主让位 | 通过 | 通过 | 它直接更新本包“真实易主让位未知”的既有缺口，并会在每次计划性交接中复用；关联 [#172（协调者操作模式收敛）](https://github.com/Eridanus117/agent-control/issues/172)回执给出问题、可执行结论、同机 Orca 1.4.180 对象／时间、租约与 cron 精确身份、让位后负事实、单次样本边界、失效条件和下次自然交接复核步骤。 |
| dispatch-race 第三／第四自然事件 | 通过 | 通过 | 它们更新既有验活结论并直接影响每次受监督派发；第三例有远端接管／波次回执，第四例有稳定 Run／Task／Dispatch／终端与协调者转录的可重复本机核验链，并有远端最终交付。两例均限定 `input_accepted`、一次补交、后续精确复核、对象／版本／时间、未知触发原因、失效条件与下次最少复核；不据此给出固定发生率或等待时长。 |
| fresh Codex 四样本与 `codex_apps` 签名 | 通过 | 通过（仅限有界相关性） | 它直接更新验活触发未知并会在自然派发中复用；远端波次回执冻结 4/4、一次点火恢复和零重派，两例有附加细节，同时明确非预注册、无阴性基线、无因果与无固定率边界。 |
| Codex JSONL Provider 验活适配器 | 通过 | 通过（当前交付验证） | 0.147.0 单次只读探针证明 `turn.started`，两个真实历史 rollout 覆盖 0.144.5／0.147.0 消息形状；工具已给出精确 Dispatch 三态并守住 0.147.0 flag 位置。自然竞态收益、Provider 中立生命周期与产品采用未验证。 |
| Claude checkpoint／resume 局部边界 | 通过 | 通过 | 更新 K8／K12 既有三层恢复且会重复使用；一手官方文档复核给出 2.1.228／Windows／日期、覆盖与不恢复状态、失效条件和最少复核步骤，结论只到 Provider 局部补强。 |
| 1.4.181 自动更新清场事件 | 通过 | 通过（单次自然事件） | 更新“哪些状态可恢复／重建／遗失”，并会在后续更新恢复中复用；关联 [#207（Mode B P0 前检）](https://github.com/Eridanus117/agent-control/issues/207)保存版本、时间、PTY／handle／generation／原 Task 重派链、未知与最少复核。不能推出固定更新行为或 automation 持久性。 |
| `input-missing` 与 1.4.181 高层验活 | 通过 | 通过（当前环境的样本有效） | 关联 [#211（tui-idle 竞态对照）](https://github.com/Eridanus117/agent-control/issues/211)的预注册 A／B 对照给出低层缺失态和资源后态，关联 [#216（Mode C 混合试点第一阶段）](https://github.com/Eridanus117/agent-control/issues/216)的两个自然 Codex 样本给出结构化／人工一致的“已开始”；共同更新恢复重派的诊断边界，不支持跨 Provider 稳定率。 |

### 结论级判定

| 结论 | 价值门 | 可信门 | 判定依据 |
| --- | --- | --- | --- |
| 1. GitHub／Orca／Provider 三层恢复 | 通过 | 通过 | 长程协作反复需要；三层各有一手合同与可重复只读核验，Claude checkpoint／resume 新证据进一步限定 Provider 层只能局部补强，边界互不替代。 |
| 2. Worker 活派与协调者 Run 继任分离 | 通过 | 通过 | 直接防止把 Run 绑定外推为 Worker 换绑；K8、动态指南与关联 [#95（协调者压缩存续与继任协议）](https://github.com/Eridanus117/agent-control/issues/95)只读核验相互印证。 |
| 3. 易失状态的恢复／重建／遗失映射 | 通过 | 通过 | 每次继任都要逐项使用；远端载体、内存态和不可恢复内容均有明确判据。 |
| 4. 六项压缩存续锚点 | 通过 | 通过 | 反复压缩后用于定位必要真源；每项职责和不可推出内容均已限定。 |
| 5. D9 租约、resume 查重与重派验活 | 通过 | 通过 | 协调 resume、易主与重派会反复使用；批准回执、一个同 Session 双 cron 样本、一次真实易主让位、K2 既有竞态、一个 5/5 空转批、第三／第四自然事件、fresh Codex cohort 与 JSONL 三态当前交付共同支持。发生率、MCP 因果、点火时延、自然收益与权限边界仍明确受限。 |
| 6. 0–8 步操作级协议与证据上限 | 通过 | 通过 | 步骤可由新 Session 只读推演；一次无在途 Worker／Delivery 的计划性交接已验证部分步骤，稳定 Run ID、活动来源链、写入所有权与运行代次均有停门，普通 Run 围栏与完整在途收养未知仍原样保留。 |
| 7. 自动更新后的身份重发现与原 Task 重派 | 通过 | 通过（单次自然事件） | 未来 Orca 更新恢复会重复使用；1.4.180→1.4.181 事件保存新二进制指南、PTY 清场、handle 重注册、generation 前进、首次尝试死亡及原 Task 重派。外推边界明确。 |

### 八项可信门共同核对

| 可信门 | 判定 | 依据 |
| --- | --- | --- |
| 1. 明确回答的问题 | 通过 | 问题限定为 Orca Run 协调者在压缩、计划交接或意外终止后的职责恢复。 |
| 2. 可直接使用的结论和必要解释 | 通过 | 给出三层模型、易失状态映射、六项锚点、resume 查重／验活纪律和带验证／停止条件的 0–8 步协议。 |
| 3. 第一方来源或可重复验证过程 | 通过 | 关联 [#95（协调者压缩存续与继任协议）](https://github.com/Eridanus117/agent-control/issues/95)保存动态指南与 Run 的只读核验边界；关联 [#172（协调者操作模式收敛）](https://github.com/Eridanus117/agent-control/issues/172)保存 resume、5/5 重派、计划性交接、易主让位与第三例的远端自然证据；关联 [#207（Mode B P0 前检）](https://github.com/Eridanus117/agent-control/issues/207)保存 1.4.181 自动更新恢复链；关联 [#211（tui-idle 竞态对照）](https://github.com/Eridanus117/agent-control/issues/211)与关联 [#216（Mode C 混合试点第一阶段）](https://github.com/Eridanus117/agent-control/issues/216)保存低层对照和高层自然验活；本机稳定 Run／Task／Dispatch／终端与转录保存第四例；关联 [#31（Orca 生命周期断裂）](https://github.com/Eridanus117/agent-control/issues/31)／关联 [#184（协调者运营与管理能力）](https://github.com/Eridanus117/agent-control/issues/184)保存新增 cohort；关联 [#203（Claude Code 本体能力面调研）](https://github.com/Eridanus117/agent-control/issues/203)／关联 [#204（Codex CLI 本体能力面调研）](https://github.com/Eridanus117/agent-control/issues/204)保存 Provider 文档复核与 JSONL 探针；K2 保存既有竞态复现。 |
| 4. 对象、版本、环境和核验时间 | 通过 | 页首分开列明 Windows、0–8 原核验与 1.4.180／1.4.181 增量自然样本的版本、日期及证据等级；来源映射保存必要的稳定身份与时间。 |
| 5. 例外、仍未知内容和不能推出的结论 | 通过 | 下节明确只有一次无在途工作的计划性交接、普通 Run 围栏与完整在途收养未知、自然事件／证据批计数、30 秒非超时、点火非即时保证、无离线唤醒及不可恢复草稿。 |
| 6. 明确的失效条件 | 通过 | 下节列出动态指南、对象模型、Delivery、Worker 生命周期、Provider resume／cron 与输入提交语义的变化信号。 |
| 7. 下次最少复核步骤 | 通过 | 只需读取动态指南、当前 Run 与合同，并在下一次自然 resume、易主或派发中查重、核对让位负事实和验活；不为取样制造重启、易主或故障。 |
| 8. 人容易理解、Agent 足以复用的表达 | 通过 | 中文正文按问题、模型、状态、步骤、验证、停止门与证据展开，不依赖会漂移的命令清单。 |

## 例外、未知和不能推出的结论

- **只有一次无待处理 Delivery、无在途 Worker 的真实计划继任样本，证据最多支持当前交付验收。** 它验证稳定 Run 绑定、运行代次唯一前进、D9 易主让位与干净收口，不验证在途 Worker 收养、FIFO Delivery 恢复或失联强制接管；不能宣称完整 0–8 步已经有效、普通 Run 已具备无歧义强制接管或 Worker 已被成功收养。
- 同 Session resume 复活 cron 只有一个自然样本；它足以推翻“重启后 cron 必然消失”，但不能推出所有 Provider、版本和 resume 路径都会复活，也不能让跨 Session 租约查出同 Session 重复项。
- D9 易主让位只有一次同机计划性交接样本；它支持“旧持有者在后续 tick 读到易主后自删并停止写入”这一正向路径，不能推出固定让位时延、故障时必然执行、所有 Provider 通用或仓外租约本身具有原子围栏。
- dispatch-race 的修订版 6 基线为四个自然事件／批次，其中 5 个 Codex 空转来自同一个重启后重派波次；另有一个 `n=4` fresh Codex cohort，不与批次数相加。新增 cohort 的 4/4 `codex_apps` 签名只有相关性，没有阴性基线或机制隔离；不能推出 MCP 因果、必要／充分条件或自动恢复动作。历史约 30 秒只是一种首次检查点，不是固定 SLA、失败率或 Worker 处置依据；第四例在补交约 20 秒后仍显示零输出、再过约 30 秒才进入工作态，也不能据此制定固定点火等待时长。现在优先使用事件三态，补交／点火后的释放分支继续按 K2 与当前回执处理。
- 1.4.181 的 `input-missing` 只来自 Claude 的“`tui-idle`＋低层注入”组合路径；它不证明高层 `worker-start`、Codex 或其他版本会同样丢失输入。一次 Enter 对该态无效，不能据此增加 Enter 次数或新建第二个 Task／Dispatch。
- 自动更新清场只有一次 1.4.180→1.4.181 自然事件；它证明 Provider 会话、Run 绑定、PTY 与 handle 的存活边界不同，不证明所有更新、所有终端或所有 Provider 都按同一方式变化，也不证明 automation 定义跨重启持久。
- `turn.started` 仍只在一次 Codex 0.147.0 非交互只读探针中直接验证；适配器和两个真实 rollout 只证明结构化映射可用，不能推出自然竞态收益、Provider 中立生命周期、现有 Orca batch 派发已建立或其他 Provider 已覆盖。
- Claude checkpoint／resume 只补强 Provider 局部恢复；它们不能恢复 Bash／外部并发／Git 状态、完整权限与启动参数，也不能替代 GitHub 合同或 Orca 执行事实。
- 普通 Run 在旧协调终端失联时的竞争与围栏语义尚未直接验证；没有动态指南支持且可回读的围栏证据时，失联恢复分支必须保持只读。下一次带待处理 Delivery 或在途 Worker 的计划性交接要保存明确交接、代次基线、消息完整性与 Worker 零重复证据；第一次自然失联样本要保存旧消费者被围栏的直接证据。
- Session 内等待循环不是持久调度器；Session 退出后不会离线唤醒。离线连续性需要另一个经负责人决定的产品合同。
- 临时草稿、未外显推理与本地未提交文件没有自动恢复通道；本协议只能要求外化，不能恢复已经遗失的内容。
- 本包不改变 K2 的低层 Dispatch 边界，也不改变 K8 的 Worker 活派换绑结论；协调者 Run 继任不能外推到这两类对象。
- 除第 5 条已批的租约、自身 cron 自管及现有 Dispatch 验活外，本包不授权实际绑定 Run、终止协调者、迁移 Worker、处置终端／worktree、修改宿主环境或建立调度器。

## 失效条件

出现以下任一情况时，让受影响结论先退出直接复用：

1. Orca 升级，或动态指南改变 Run 绑定、`consumer_generation`、协调者围栏、Delivery 确认、Worker 复用／释放、重试或结果未知的语义；
2. Orca 增加经验证的 Worker 活派换绑、持久巡检或离线唤醒能力；
3. 真实继任样本显示 Run／Dispatch 身份变化、Delivery 遗漏、Worker 重复派发、旧协调者在让位后仍可写入或首个巡检节拍未触发；
4. GitHub 合同、恢复指针或负责人决定协议改变其真源和消费规则；
5. 一次自然继任证明新 Session 无需 Skill 路由也能稳定发现本包；此时按 95-D1 的翻转条件重审是否退回仅知识承载。
6. Provider／Orca 改变 resume 与 session cron 的恢复、枚举或删除语义，或 `CronList` 不再能完整列出本 Session 的 cron；
7. `worker-start` 的回执新增可核验的已提交／已工作状态，或自然样本证明 `input_accepted` 已稳定等价于实际进入工作态。
8. Codex CLI 改变 JSONL 的 `turn.started` 事件语义，`codex_apps` 的 MCP 初始化／横幅行为变化，或 Claude Code 改变 checkpoint／resume 覆盖与不恢复状态。
9. Orca 更新器改变应用更新时的 runtime 重启、PTY／terminal 重注册、Run generation 或在途 Worker 保留语义，或者提供可核验的排水／恢复协议。

## 下次最少复核步骤

1. 从本 Session 实际解析到的 Orca CLI 读取版本匹配的完整 orchestration 指南，只对照 Run 绑定、Delivery、Worker 生命周期、更新恢复和重试分支；版本不再是 1.4.181 或发现变化时即局部更新本包。
2. 只读执行第 0–2 步：从远端 Issue、恢复指针和当前 Run 对账稳定 Run ID、活动 Issue／Task／Dispatch 来源链、写入所有权、`consumer_generation`、Delivery、终端与 worktree 身份；Run 目标文字只记录，不作相等停门，也不为复核执行绑定或接管。
3. 下一次自然 resume 时，在创建 cron 前先运行 `CronList`，记录零／一／多项及处置结果；不得为了复核主动重启或制造重复 cron。
4. 下一次自然 Codex 派发或恢复重派时，记录 `worker-start` 回执，并立即以 `tools/codex_liveness` 读取精确 Task／Dispatch 三态；在相关事件或合同中的有界启动门到来时再读，而不固定等待 30 秒或刮终端正文。Provider 精确观察需另分 `composer-pending` 与 `input-missing`：只对前者沿原身份补一次 Enter，随后再次运行结构化验活并核对最终释放分支；后者停止并保留失败证据。不从 `codex_apps` 签名或一次即时 post-Enter 空白直接推出失败，也不新建对照派发或主动制造 MCP 故障。
5. 若自然任务建立 Codex 非交互 lane，只把排他绑定到一个 Dispatch 的 stdout 交给 `events` 适配器，并记录 `thread.started`／`turn.started`、精确 Task／Dispatch／thread、CLI 版本和失败分支；继续比较 accepted-but-not-executed、人工判读、token 与时延，未取得自然样本时不把当前交付验证外推为产品收益。
6. 下一次自然 Claude 恢复时，核对精确 Session 身份、权限模式和任务依赖的启动参数；checkpoint 覆盖只在真实需要中记录，不为复核主动制造并发编辑或破坏性 rewind。
7. 下一次自然计划性交接时，记录租约易主时间、旧持有者下一 tick 的判断与自身 cron 处置，并复核让位后租约和共享面没有被旧持有者再写；不得为了复核主动制造易主。
8. 下一次带待处理 Delivery 或在途 Worker 的计划性交接，或第一次自然失联恢复时，记录稳定 Run ID 与既有 Dispatch 是否保持、运行代次是否唯一前进、旧消费者是否被围栏、待处理 Delivery 是否完整、Worker 是否零重复派发、首个巡检节拍是否触发。
9. 若样本不满足前述判据，让受影响结论退出当前知识并保留失败证据；不得为了证明协议主动终止协调者或制造故障。
10. 下一次自然 Orca 更新时，记录更新前后 app／runtime、Run generation、Task／Dispatch、PTY／terminal handle、Provider 会话和消息完整性；只在更新已经自然发生后复核，不主动触发更新或重启。

## 不适用范围

- 未经明确授权的 Run 绑定、Worker 接管、故障演练、资源处置或宿主环境修改；
- Orca 之外的编排器、非 Windows 环境、跨主机 Session 迁移与 Provider 转录长期保留；
- 离线调度、自动唤醒、自动接管、调度器建设或 Orca 长期产品依赖决定；
- GitHub 合同、负责人决定协议和任务拆分本身的编写规则。
