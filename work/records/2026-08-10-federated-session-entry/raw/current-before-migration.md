# 当前任务

> 状态：进行中。
> 主线审阅面：[计划／实验 #19：修复原始诉求到并发执行的传递链](https://github.com/Eridanus117/agent-control/issues/19)。
> 当前并行实施：[agent-control#20：联邦式 Session 入口与活动协调快照](https://github.com/Eridanus117/agent-control/issues/20)；[agent-plugins#24：任意 Session 的 Issue 子树闭环](https://github.com/Eridanus117/agent-plugins/issues/24)。
> 整合验收：[agent-control#21：三个 Session 真实验收](https://github.com/Eridanus117/agent-control/issues/21)，原生依赖上述两项。
> 独立并行交付：[agent-plugins#19：恢复完整的资源观测入口](https://github.com/Eridanus117/agent-plugins/issues/19)；它不参与主线需求方法设计。
> Orca 协调：复用 `run_8f829c43983e`；当前 Session 是该 Run 的唯一协调者。

## 当前主线问题与目标

负责人已经提出大量困难、长期且彼此关联的 Agent 系统诉求，但系统不能稳定地把这些诉求持续转化成下一项高价值、可执行、可并发的工作；局部工具、看板字段、单一当前任务或某个实现会反向替代原始诉求。本阶段先用现有问题求解能力做基线诊断，再只对已证实缺口做受限调研和方案比较。完整问题模型、成功条件、成本和停止条件以 agent-control#19 为准；任何入口、`current`、权威、Skill、Plugin、Project 字段或自动化实现都要先回到该 Issue 审阅。

基线诊断、攻防和六个官方／原始来源的受限调研已经写入 agent-control#19。负责人随后批准了其中的分层方向，但指出其默认追求最小改动，不能显著减少负责人依赖或释放并发产能；当前 Token 资源充足，真正稀缺的是负责人注意力、有用吞吐和技术闭环速度。此前资源观测窄能力耗时数小时、一个中央 Session 长时间串行推进和本 Session 多次依赖负责人发现漂移，均是这项纠正的观察证据。

当前实施目标因此从“短快照和两条窄行为补丁”升级为“在合理成本内形成最小完整自主工作闭环”：保留短活动协调快照、GitHub 任务合同和按需研发记忆，但任何 Session 都能按合同执行叶子任务，也能在授权内协调自己负责的子树；任务选择、合同压缩、风险分级审查、结果回写和继续规划应能闭环，不依赖永久中央协调者。Codex Marketplace 的 Issue 压缩和端到端工作流只作为待核验样本；不继承其本地草稿依赖、统一重型门禁或默认串行。具体方案、成本和实施切片先写回 agent-control#19，再依批准范围推进。

agent-plugins#19 的安装／行为验收与上述主线假设无依赖，允许作为完整所有权交接在后台继续：执行者只按远端 Issue 和强制入口恢复，完成剩余机械验收；全部通过可在原 Issue 发布一条中文证据并关闭，失败则留在原 Issue，不机械新建事项。它不得修改本仓、系统入口、`current`、权威、Project、Plugin 安装或 Orca 共享状态。

## 并行资源实验的原始问题

当前 Codex 与 Claude 额度存在闲置和到期压力，但机械增加 Session 可能只放大启动、上下文、协调和返工成本。本任务先交付一组按需、只读、明确失败的资源观测能力：账户层看两边额度、恢复时间与可用权益，会话层看单次实际消耗；再用这些信息运行一次最多三个真实任务的跨供应商并发批次，判断并发是否提高了有用吞吐。

完整目标、初始证据、成功条件、成本、停止条件和不做事项以 GitHub #16 为准；本文件不复制完整方案。

## 当前阶段

PR #20 已按授权合并为 `a0e6c42379760c4963d599c857ea81e597a7293a`，候选 `resource-observability 0.1.0` 已安装到 Windows 原生的 Orca Codex、普通 Codex 与 Claude，固定依赖为 `ccusage 20.0.19`，三端 Skill 与合并源码哈希一致。

Orca `worker-start` 对新建和既有 worktree 连续三次返回 `selector_not_found`，没有产生实现写入。协调者按停止条件不再重试该入口，改用 Orca 创建独立 worktree／终端后显式 Dispatch；基础 Dispatch 已成功。该兼容性问题计入本实验的协调成本，不改变 GitHub 合同或 D0 文件所有权。

D0 的首次真实 Codex 回执返回安全的 `upstream_failed`；直接运行固定 `ccusage` 能找到同一 Session，因此问题已收敛到薄 CLI 在真实 Windows npm / nvm4w `.cmd` shim 下的调用路径。D0 暂不判定真实环境可运行，agent-plugins#19 保持开放。

当前进入 D1：[agent-control#17：运行带观测回执的真实并发批次](https://github.com/Eridanus117/agent-control/issues/17)。任务选择门只得到两个合格任务，已建立为 #17 的原生子 Issue：

- [agent-plugins#21：修复真实 Windows `.cmd` 调用失败](https://github.com/Eridanus117/agent-plugins/issues/21)，独占新的 `agent-plugins` 分支／worktree 和 `plugins/resource-observability/**`，交付 Draft PR；
- [agent-control#18：为任意多 Session 共享写入选择下一项最小协作能力](https://github.com/Eridanus117/agent-control/issues/18)，本地只读，独占向自身 Issue 发布一条交付评论。

两项无依赖且写入范围不重叠，分别交给 Codex 与 Claude；不为消耗额度制造第三项。修复完成后可从其固定分支回溯本批 Session 用量，不安装未合并版本；修复失败则如实记录观测失败。

Orca 已在同一 Run `run_8f829c43983e` 同时派发：

- #21：Task `task_8b3ab48b27c3`、Dispatch `ctx_5d26157ad9ce`、Codex 终端 `term_485328d8-3b2a-431b-a1b0-15fa3b939422`、worktree `resource-observability-d1-windows`；
- #18：Task `task_5068369b44de`、Dispatch `ctx_f402ba9f5221`、Claude 终端 `term_d912d063-0c37-4150-a9fd-8655d5558bb5`；本地保持只读。

## 2026-08-10 负责人纠偏：负责人可读性再次漂移

当 #21／PR #22 和 #18 已形成交付、协调者正准备继续父目标收口时，负责人指出“似乎开始漂移了，我看到英文了”。当前路径立即暂停，不再派发父目标复核、不关闭事项、不合并或安装 #22，也不继续发布 ROI 综合。

已确认的偏差不是单个词，而是负责人可见资产逐渐由流程和工具语言主导：PR #22 标题与提交信息为英文，复核使用 `LGTM`，#18 方案用 `E1`／`E2` 和较多未翻译的英文角色词；协调者还开始继续增加复核、状态和收口动作，使“负责人容易理解并能快速判断”让位于流程完整性。

被替代的判断：技术工作流默认使用英文标题、缩写和模板，只要结论本身正确就足够。当前恢复的表达目标：面向负责人的 GitHub 标题、摘要、决定、方案比较、验收与 ROI 默认使用自然中文；命令、文件名、API、版本号和不可替代的代码标识可以保留原文，但首次出现时用中文说明，不用英文缩写代替负责人需要理解的概念。

下一步先与负责人确认这条中英文边界，以及是否只修正当前负责人可见资产，还是把它进一步固化为跨 Session 的最小行为规则；确认前不继续 D1 收口。

## 2026-08-10 负责人纠偏：工具能力反向收窄了产品诉求

负责人指出，原始资源运营诉求还包括 Codex 与 Claude 两个账户的额度／已用／剩余／重置时间，以及 Codex 重置券；当前工作却逐渐变成了围绕 `ccusage` 和 Node 薄门面修复单 Session Token 回执。

已确认的偏差：`ccusage` 只能提供会话层的已消耗 Token。协调者错误地把“可复用的一个数据源”当成了“完整资源观测产品”，并在没有负责人明确确认产品降级的情况下，修改 #16，把账户层从本轮完成门中移除。随后关于 Node、Rust、Windows 命令入口和并发实验的工作，都建立在这个被错误收窄的合同上。

当前恢复的产品边界：

- **账户层**：按需读取 Codex 与 Claude 的额度、已用／剩余和重置时间；读取 Codex 重置券数量与过期时间；不可可靠取得的字段明确为未知；不得自动消费权益；
- **会话层**：按需读取单 Session 的实际 Token 消耗；`ccusage` 只作为这一层的候选组件；
- **决策层**：把账户容量、恢复时间、权益和会话消耗与任务价值、预计成本及并发容量一起用于启动、并行、降级、延后或停止判断。

被替代的判断：“固定 `ccusage` 后可以把账户动态额度从 D0 拆出并暂缓”。当前不再成立。Node／Rust 只可能是某个采集器的实现选择，不能替代产品范围判断。

当前动作：暂停 PR #22 合并、安装和 D1 父目标收口；保留已经形成的会话层实现与实验数据，但只按局部证据评价。先恢复 #16 的账户层完成条件，再以最低成本确认 Codex 已知只读接口和 Claude 尚未知的账户接口分别怎样进入同一个按需入口。动态快照不写成长效知识。

增量核验已经关闭“账户来源未知”：Orca 1.4.177 的 `orca account list --json` 能在 Windows 原生环境同时返回 Claude／Codex 账户窗口与 Codex 重置券；新建 Claude Code 2.1.226 会话执行官方 `/usage` 后，5 小时、本周与 Fable 本周读数和重置时间与 Orca JSON 一致；Codex CLI 0.147.0 本机生成协议仍包含 `account/rateLimits/read`、`account/usage/read` 与重置券结构。带时间的实际快照只记录在 #16 评论，不进入长期知识。

当前可逆 MVP 选择：账户层先直接复用 Orca CLI，会话层继续复用固定 `ccusage`，自有 `resource-observability` Skill 只统一语义、脱敏、失败和资源决定提示。不复制 Orca／Orrery 的采集核心，不继续语言赛马；只有后续决定脱离 Orca，或自然使用证明其可靠性、升级或退出成本不可接受时，才评估抽出独立 Rust CLI。该选择不表示 Orca 已被产品采用或成为长期依赖。agent-plugins#19 已据此恢复为完整资源观测交付合同。

`resource-observability 0.2.0` 已由负责人明确批准并通过 [agent-plugins#23](https://github.com/Eridanus117/agent-plugins/pull/23) 合并，固定 head 为 `ea8f66ed7ed9df554b5240e2b7513e7f04088c42`，主分支 squash 提交为 `b2572dc901135708c650dd1fc334a3540820692e`。它没有新增账户采集代码：Skill 直接调用 `orca account list --json` 并白名单化两边窗口与 Codex 重置券；现有 Node 薄门面继续只服务 `ccusage` 单 Session 回执。PR 同时吸收 #22 的 Windows npm `.cmd` 修复，因此 #22 已被主分支中的 #23 实质取代，但尚未依据本次合并授权自动关闭。合同测试、JSON 解析、真实 Orca 快照、Claude `/usage` 交叉核验、当前提交自审与合并后远端 Manifest／Skill 复核均通过；尚未安装，也没有新 Session 可发现性证据。

## 2026-08-10 负责人纠偏：减少重复授权，但保留低成本审阅

负责人确认：在一个已经批准的 Plugin 交付中，代码合并后把该已合并版本安装到本机既定运行端并执行可逆冒烟验证，属于正常整合步骤，不应再次请求授权。只有安装会引入新凭据、不可逆迁移、外部付费／权益消费、扩大运行范围或长期采用决定时，才升级负责人决定。此前把“合并授权”和“紧接着的常规安装验证”机械拆开，提高了负责人负担。

同时，本轮从完整资源运营诉求漂移到 `ccusage`／Node 会话工具，证明语义审阅仍然必要：测试和代码检查可以通过，但产品能力已经回退。当前采用的低成本审阅形态是两道窄检查，而不是给每个小改动增加完整流程：

1. 实现前只核对原始问题、成功条件，以及方案删除／延期了哪些能力；任何未获负责人确认的能力回退都停止；
2. 合并前把结论绑定当前 head，只核对当前合同、能力增减、自动验证、剩余未知和是否需要负责人决定。

普通低风险小改动默认由实现者自审和自动检查完成；高价值、多 PR、改变长期行为或能力边界的交付才增加未参与实现者的父目标复核。后续在自然任务中只记录审阅是否抓到漂移、审阅近似耗时、返工和负责人纠偏；若没有持续收益，不建设评分平台或重型审阅系统。

## 2026-08-10 新候选：异步验收与额度速度

负责人提出把合并后的安装／验收收敛为一个可派发的 GitHub Issue：Issue 预先写明合同、验收与关闭权限，执行 Agent 完成检查后，全部通过即可自行回写证据并关闭，协调者可以继续推进不冲突的工作。当前采用的最小边界是：普通子交付可以这样做；失败保留在原 Issue，不机械制造新 Issue，只有出现可独立交付的新根因才建立子项；父诉求、产品采用和长期依赖不随子项自动关闭。

当前以 agent-plugins#19 做第一次自然样本。`resource-observability 0.2.0` 已安装到普通 Codex、Orca Codex 与 Claude；三端全新 Session 验收通过 Orca Task `task_eec136df2cbf`、Dispatch `ctx_3e7c7c93c5c8` 派给一个只读 Claude 验收者。它只在全部验收信号通过时向 #19 发布一条中文证据并关闭，失败则保持开放且不新建事项。Orca 组合式 `worker-start` 再次返回 `selector_not_found`，未产生 Worker 或写入；协调者复用同一 Task，通过现有工作区的新 Claude 终端和低层 Dispatch 成功派发，该失败计入协调成本。

负责人还明确下一项资源运营期望：系统不仅看到某一时刻的额度和重置时间，还要看到额度消耗速度、临近到期且可能闲置的容量，并据此提高有价值任务的资源利用率。当前 `0.2.0` 只有按需账户快照和单 Session 消耗，不能从单点读数推出速度。当前候选 MVP 是在自然的任务批次开始／结束和资源决定点做事件式快照，比较同一窗口的百分点变化、经过时间、重置／权益到期压力和已完成任务价值；不先建设轮询、常驻监控、仪表盘或自动调度，也不为了消耗额度制造任务。该候选尚未升级为权威或正式交付合同。

## 2026-08-10 负责人纠偏：看板执行状态再次替代了原始诉求

协调者随后把经营总账中“只有一个事项显式标为就绪”解释成“当前没有值得投入额度的任务”。负责人指出这与已经提出的大量困难、长期诉求明显矛盾，并怀疑当前系统提示词、单一 `work/current.md` 和它们的强制读取方式正在影响并发协作；同时，刚派出的全新验收 Session 也出现了任务注入未进入上下文、为了恢复合同读取大量材料和机械检查迅速膨胀的问题。

已确认的错误是把三种不同对象混成一种：长期诉求／能力缺口说明**有什么值得解决**；计划和交付 Issue 说明**已经怎样拆成可执行工作**；`就绪` 只说明**某个已拆事项目前能否直接领取**。就绪队列为空只证明当前规划／拆解或状态维护有缺口，不能推出没有工作，更不能让低优先级的 11 月维护事项替代当前重大诉求。被替代的结论是“资源充足但没有高价值任务”；当前事实是重大诉求很多，但需求全景、分解结果、当前执行队列和各角色需要读取的上下文没有可靠衔接。

当时立即暂停 `task_eec136df2cbf` 的新增检查及所有 GitHub 写入／Issue 关闭；已向 Worker 同时发送终端和 Orca 紧急停止消息，只允许它以失败交付报告已有只读发现。下一步先用现有问题求解能力重做一次需求／问题建模，检查：总账是否完整表达原始诉求及衍生诉求；单一 current 是否承担了不适合并发的职责；协调者与 Worker 是否需要不同的最小恢复入口；Issue 合同、权威和 current 的优先关系是否造成重复读取或方向替代。

**后续纠正**：负责人指出 agent-plugins#19 的机械只读验收与主线需求建模可以并行。上述整体冻结已被本文开头的当前快照替代：旧 Orca Task 保持失败收束，但 agent-plugins#19 已作为独立完整交接恢复；主线仍不继续资源调度设计或大规模元方法调研。

## 授权与所有权

负责人已授权：

- 为 #16、#19、#17 及 D1 合格子任务维护 GitHub Issue、Project、父子关系和状态；
- 使用 Orca Run／Task／Dispatch 协调 Codex 与 Claude；
- 在互不重叠的分支或 worktree 中实现、验证、提交、推送并创建 Draft PR；
- 合并已通过当前-head 验收的 PR #20，合并后安装候选 `resource-observability` Plugin；
- 进入最多三个真实任务的 D1 并发实验，从已合并、已安装的候选运行资源观测回执。

当前协调者独占：

- `agent-control` 的 `work/current.md`、经营总账整合、父实验状态和最终综合；
- Orca Run、Task 图、派发、交付确认和 Worker 生命周期；
- 共享安装端、用户级配置和最终整合决定。

D0 Worker 只拥有 agent-plugins#19 正文列出的新 Plugin、必要 Marketplace 条目、README 和直接验证文件；不得修改本仓、安装缓存、用户级配置或其他 Plugin。

## 未授权

- 除本次明确授权的 PR #20 外，不自动合并其他 PR；
- 不安装未合并 Plugin；
- 不消费 Codex 重置券；
- 不建设仪表盘、数据库、常驻监控、Hook、轮询、Webhook 或自动调度器；
- 不改变一级诉求状态、产品采用或长期依赖判断；
- 不把动态额度快照写成长期知识。

## 当前证据与下一检查点

2026-08-10 的初始额度、重置时间和两次冷启动样本已经进入 GitHub #16；此前聊天和临时 Schema 目录不再是唯一来源。当前稳定候选是“Codex 有可读账户与线程用量接口，Codex／Claude 非交互运行可形成 Session 回执”；Claude 账户级剩余额度仍未知。

语言路径检查：D0 Draft PR 已形成可运行的 PowerShell 原型，但实现与测试规模、隐式类型转换和多 Session 输入语义暴露出核心实现风险。负责人指出“当前是否已经安装某种语言”不能作为语言淘汰依据；协调者已暂停 PowerShell 路径，保留原型与测试证据，不恢复该实现。

负责人授权公开资料调研与受限语言实验后，TypeScript／Go 两个隔离切片均通过了各自测试，但没有形成足以抵消继续赛马成本的决定性差异：TypeScript 当前交付较轻，Go 的完整 RPC 路径更深，两者的 Schema 变化测试并不同合同；独立复核还发现 TypeScript 有两个必须先修的严格失败问题。负责人一度明确选择 Rust，以接受当前构建与交付成本换取资源运营能力继续扩展时更大的性能、类型和原生分发余量。完整调研合同见 [agent-plugins#19 的语言选择评论](https://github.com/Eridanus117/agent-plugins/issues/19#issuecomment-5239847075)，该次 Rust 决定记录在同一 Issue 的后续评论。

随后负责人指出，协调者从“交付资源观测能力”过早收窄成“选择语言重写 D0”，没有先回答现成的 `ccusage`／`codexusage` 是否可以直接复用。Rust Worker 已再次暂停且专用 worktree 保持干净；被中断的 WSL 工具链准备只留下 `rustup` 引导程序，没有安装默认 Rust 工具链。该纠正替代“立即 Rust 改写”的下一步，不把已有实现成本当作继续自建的理由。

增量核对确认 `ccusage` 已统一支持 Codex／Claude、单 Session 查询、JSON 报告和多平台原生包，但不提供供应商账户的真实剩余额度、重置时间与重置券。它可以承担会话层的候选解析，不应重复实现其 Provider 解析、历史扫描或多平台核心；此前据此把账户层拆出并暂缓的判断已经被负责人纠正，不再作为当前合同。Orrery 当前 `crates/plimsoll` 只作为待核验的协议、失败语义和测试参考，新实现不得依赖 Orrery crate、路径、缓存或运行状态。

D0 已在 Draft PR #20 的固定 head `68012a50c609cb424e35167f7c9d506ec1b7d878` 收缩为“固定 `ccusage` + 独立窄 CLI + Skill/Plugin 入口”。上一 head 的五个 P1 已修复；独立 Windows 原生窄复审结论为 P0=0、P1=0、P2=0。Windows Node／PowerShell 契约测试通过；隔离打包版 `ccusage@20.0.19` 的 Windows `.cmd` shim 已经薄 CLI 调用并产生安全的 `session_not_found` 回执，临时 npm cache 已清理。Issue／PR 已明确 Windows 原生是唯一当前目标、验收和维护范围。

下一检查点：负责人已批准安装，并明确以后同类已合并 Plugin 的常规安装验证不重复授权。当前直接把 `resource-observability 0.2.0` 安装到三端，再用全新 Codex／Claude Session 验证 Skill 发现、账户摘要、单 Session 回执与脱敏边界。通过前不关闭 agent-plugins#19，不关闭被取代的 #21／PR #22，也不继续 D1 父目标复核、ROI 综合或状态收口。已经完成的两个并发任务保留为局部实验样本，不因合同被纠正而伪装成完整父目标证据。WSL 不属于目标、验收范围或维护承诺，不得恢复语言赛马或复制 `plimsoll` 整体。

## 本任务可读取的其他权威

- [`authority/02-long-horizon-work.md`](../authority/02-long-horizon-work.md)
- [`authority/03-thinking-methods.md`](../authority/03-thinking-methods.md)
- [`authority/04-collaboration.md`](../authority/04-collaboration.md)
- [`authority/05-resource-operations.md`](../authority/05-resource-operations.md)
- [`authority/09-rd-memory.md`](../authority/09-rd-memory.md)
- [`authority/10-operating-ledger.md`](../authority/10-operating-ledger.md)
