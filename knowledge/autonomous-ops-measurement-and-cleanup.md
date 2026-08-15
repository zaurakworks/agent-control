# K19：自治运营以 Token 日聚合测燃烧，以任务运行态保留集收口 worktree 清理

> 状态：正式当前公共知识。
> 最近核验：2026-08-13。
> 适用对象：本机 Codex 多 Session／长任务的人工资源判断，以及 Orca 管理的 worktree 终局清理；不授权自动调度、自动消费权益或无界巡检。
> 环境：Windows 11；America/New_York；Orca 1.4.180 packaged；`ccusage 20.0.19`；本机 Orca worktree 与 terminal 运行面。
> 证据上限：燃烧结论来自一次可重复的本机日聚合与今夜自然工作负载；清理结论来自一次误删两个活跃 Worker worktree 的真实事故，以及今夜一次 38→8 的直接清理样本。两者支持当前运营纪律，不证明供应商计费公式、固定 Token→周窗换算或跨版本自动清理安全性。

## 回答的问题与价值门

自治运营中，怎样判断 Codex 实际烧了多少，避免把冻结的账户周窗百分比当成实时信号？巡检清理 worktree 时，怎样既避免分支名碰撞误伤正在运行的执行现场，又回收终端停在 Ready 的已完成任务残留？

这两个动作会在多 Session 波次中重复出现：测量错误会污染继续、加派或停止判断，清理错误则可能直接丢失尚未持久化的成果。两条结论都能减少高代价误判，通过价值门。

## 可直接复用的结论

### 1. 燃烧测量：以 `ccusage codex daily` 的当日 Token 聚合为主信号，账户周窗百分比只作滞后代理

#### 触发条件

出现以下任一情况时读取一次日聚合：

- 多 Session、高推理强度或长程任务运行后，需要判断实际燃烧量；
- 准备继续、加派、降级或停止一波高成本工作；
- `orca account list --json` 的周窗百分比没有变化，需要区分“没有消耗”与“仍是旧快照”；
- 需要比较一天内不同运营形态的 Token 量级，而不是推断供应商账户总容量。

#### 最短可执行结论

运行：

```text
ccusage codex daily --json --offline
```

从本地日期对应行记录采集时刻、`totalTokens`、`outputTokens`、`inputTokens`、`cacheReadTokens` 与 `costUSD`。运营判断以 total 的实际增量和组成作为主信号；`costUSD` 是 `ccusage` 按模型价目给出的估算，不是账单。

同一账户与 Provider 计量语义不变时，券／周窗燃烧与 Token 消耗同向，Token 可作相对燃烧量的一阶信号；不能从账户整数百分比反推出固定比例、套餐总量或当前 Session 贡献。`orca account` 只有在 `updatedAt` 严格前进且窗口身份不变时，才可作为新的账户观测点；相同 `updatedAt` 下的百分比不动，只能说明又读到同一快照。

运营记法可以写成 `Codex 券／周窗燃烧 ∝ Token`；这里的 `∝` 只表示同向的相对燃烧量，不表示已经测得固定系数。

2026-08-12 01:12 EDT 直接运行 `ccusage 20.0.19` 所得本机样本如下：

| 本地日期 | 样本性质 | total | output | input | cache-read | `costUSD` |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 2026-08-11 | 全天 | 889,979,990 | 4,163,437 | 31,405,673 | 854,410,880 | 790.908693 |
| 2026-08-12 | 截至 01:12 EDT 的部分日 | 98,393,580 | 467,337 | 4,060,259 | 93,865,984 | 81.254397 |

两行中 `input + cache-read` 都约占 total 的 99.5%；8 月 11 日约 8.90 亿 Token、估算 790.91 美元。今夜自然工作负载包含长上下文、多轮审阅、修订与交叉复核，因此本样本支持一条运营优先级：**重上下文、多轮、长 Session 应先按高燃烧形态预算**。这是由 Token 组成与工作负载共同支持的一阶推论，不是某一任务的因果归因；要归因到单个 Session，仍需单 Session 回执。

#### 不能推出的结论

- 本机日聚合不覆盖其他设备、缺失日志或未被 `ccusage` 解析的活动，不能冒充完整账户账本。
- `costUSD` 不等于实际收费、订阅价值或券的货币价值。
- total 中 cache-read 占比高，不证明所有长任务都比短任务低效；它只说明反复携带和读取上下文是当前燃烧的大头。
- 周窗百分比和 Token 同向，不等于存在可复用的线性系数；账户并发、整数百分点量化、缓存刷新与 Provider 计量都可能混杂。

#### 失效条件

出现以下任一情况时，受影响结论停止直接复用：

1. `ccusage` 改变 Codex 日聚合的扫描范围、字段、total 组成、模型价目或本地日期边界；
2. Codex 本地日志格式变化、日志不完整，或任务跨设备／远程环境运行；
3. Provider 改变 Token、缓存读取、券或周窗口的计量关系；
4. Orca 改变账户快照缓存、`updatedAt` 或窗口身份语义；
5. 新的第一方账户接口提供更细、更新鲜且可核验的实际消耗数据；
6. 后续按 Session 取证推翻“重上下文、多轮、长 Session 是当前高燃烧形态”的运营推论。

#### 下次最少复核步骤

1. 核对 `ccusage --version`，再运行一次 `ccusage codex daily --json --offline`；只读取任务所需日期，不保存整份动态历史。
2. 检查当日行的 total 是否仍由 input、cache-read 与 output 构成，并记录采集时刻；部分日必须显式标注。
3. 若还要结合账户周窗，只读两次 `orca account list --json`；`updatedAt` 未严格前进就停止差值解释，不为等待刷新制造 Token。
4. 只有确需归因时才补单 Session 回执；日聚合已经足够回答总燃烧量时不扩大取证。

### 2. worktree 清理：以运行任务、两仓 main 与保护对象组成保留集，永不按分支名匹配

#### 触发条件

任何删除 worktree 的动作都触发本纪律，包括巡检孤儿、Worker 交付后的资源收口、失败任务回收，以及准备清理旧起草现场。任务名、worktree 显示名或分支名“看起来像旧任务”不能降低触发门。

#### 最短可执行结论

删除前先动态读取当前版本的 Orca CLI／orchestration 指南，取得 Task／Dispatch 运行态、精确 worktree 绑定和两仓 worktree 清单；在本次核验版本中，相关命令面是：

```text
orca orchestration task-list --json
orca orchestration worker-show --dispatch <dispatch-id> --json
orca worktree list --repo <repo-selector> --json
```

把当前处于 `dispatched`／`running` 的 Task／Dispatch 所绑定 worktree、Agent 系统两仓（`agent-control`、`agent-plugins`）各自的 `main` worktree，以及明确受保护对象组成保留集 `R`；保护对象包括 [关联 #125（实验：迁移转换器大规模全流程压力测试）](https://github.com/Eridanus117/agent-control/issues/125) 的子仓克隆等已登记例外。除 `R` 之外的非 main、非保护 worktree 一律进入待清队列：它们属于已完成、已释放、已合并或已否决任务的残留。进入待清队列不等于立即删除；每个对象仍须逐个通过 Git 安全门：

```text
Normalize(candidate.path) 不属于 R
且 git status 显示 0 个未提交改动
且精确远端比较显示 0 个未推送提交
且删除对象使用精确 path／worktree id，连带终端、Hook 与子仓影响已核对
```

任一 Git 安全门未知或失败就暂停该对象；先检查未提交成果、未推送提交或嵌套子仓／克隆占用，再按证据处置，禁止 force。**分支名只帮助人辨认，永远不能成为删除匹配键、活跃性证明或成果已持久化证明。**

上述保留集与安全门现已有版本化实现 [`tools/worktree-gc`](../tools/worktree-gc/README.md)（关联 [#247（worktree 清理例程）](https://github.com/Eridanus117/agent-control/issues/247)，经未参与者核验后合入）：默认 dry-run，显式 `--execute` 才删除；候选须同时满足工作区（含未跟踪文件）全净、已并入 `origin/main` 或经刷新证明原 upstream 消失、无精确路径绑定的活动终端／Dispatch、且不是当前执行树；活动面或 Git 判据不可读时 fail closed，每个实际删除前重读完整活动面并重算判据，未使用 `git worktree remove --force`。首个真实批次 18 根中 12 根通过并全部移除、动作失败 0，保留项均有结构化原因；协调者已把「每波收口跑一次」采纳为例程。工具不可用或其判据命中失效条件时，退回本节手工程序。

今夜事故中，巡检按 `issue-139-p01`／`issue-140-p03` 分支名识别“旧起草孤儿”，实际命中的却是两个活跃修订 Worker：它们通过 PR 检出后，worktree 恰好显示同名 PR head 分支。两个 worktree 与终端在实施中途被移除；只是因为成果此前已经推送并送达 `worker_done`，才没有丢失。这个样本直接反证“分支名能唯一标识 worktree 生命周期”。

#### 守恒律置换

**被替代原文**：`把仍存在且未被精确证明已释放的 terminal 所有非空 worktreePath 规范化为排除集 A。`

旧判据把 terminal 是否仍存在当作 worktree 是否仍活跃的代理，但已完成任务的终端常停在 Ready 而不释放，其 `worktreePath` 仍在排除集内；因此这些对象即使已经终局且工作树干净，也会被持续保留，形成系统性漏清。

**新判据**：`保留集 R ＝ 当前处于 dispatched／running 的任务所绑定 worktree ＋ agent-control／agent-plugins 两仓 main worktree ＋ 明确受保护对象；其余非 main、非保护 worktree 一律进入待清队列，再逐个通过 0 未提交／0 未推送安全门。`

这是对旧 terminal 排除集判据的守恒律置换，不是叠加第二套保留规则：terminal 留在 Ready 不再产生保留资格，任务当前运行态才产生；main 与保护对象继续由显式身份保留。

#### 今夜一手样本

2026-08-12 今夜直接核验的 38 个 worktree 中，30 个是已完成任务残留；对应终端仍停在 Ready 并保有 `worktreePath`，旧判据对这 30 个对象全部漏清。按新判据形成保留集、逐个通过 Git 安全门后，一次清理把 worktree 总数从 38 个降到 8 个。该样本直接支持“Ready terminal 的路径不能代表运行中任务”与本次判据置换，不证明无人值守自动删除已经安全。

#### 不能推出的结论

- worktree 不在保留集只说明它进入待清队列，不证明已经通过 Git 安全门，也不单独授予删除所有权。
- terminal 处于 Ready 或仍有 `worktreePath` 不等于 Task／Dispatch 正在运行；运行态必须从当前 orchestration 事实核对。
- `worker_done` 只证明 Worker 报告交付；不能单独替代协调者验收、标准释放回执或 worktree 清理四项证明。
- 本结论不授权删除其他 Session、负责人或预先存在的 worktree，也不授权建设自动清理器或定时巡检。

#### 失效条件

出现以下任一情况时，先停用旧字段与步骤并做最少复核：

1. Task／Dispatch 的 `dispatched`、`running` 或 worktree 绑定语义改变；
2. 两仓 main worktree 的身份或保护对象登记方式改变；
3. 标准 Worker 释放开始可靠覆盖并删除 worktree，且回执能逐对象证明该副作用；
4. 任务使用远程 placement，而当前 orchestration 与 worktree 清单不能覆盖目标主机；
5. Git 未提交／未推送核验，或 worktree 删除命令的选择器、Hook、归档、子仓与连带终端语义改变；
6. 后续事故证明运行任务保留集与逐对象 Git 安全门仍会误删有主对象；
7. `tools/worktree-gc` 的候选判据、fail-closed 行为或执行语义变化。

#### 下次最少复核步骤

1. 动态读取当前 Orca CLI／orchestration 指南，确认 Task／Dispatch 运行态、worktree 绑定、标准释放和 worktree 处置语义。
2. 在下一次自然清理中先运行 `tools/worktree-gc` 默认 dry-run，核对候选与保留原因和本节判据一致后再决定 `--execute`；工具不可用时按本节手工读取 Task／Dispatch 与两仓 worktree 清单组成保留集。不为复核另造待删 worktree。
3. 对每个待清对象逐项记录：精确 path／id、不在保留集、0 未提交、0 未推送、删除连带影响和所有权；失败先检查未提交成果或子仓／克隆。
4. 执行后重新读取 Task／Dispatch 与 worktree 清单，确认目标消失且保留集对象不变；任何不一致立即停止同批后续删除。

## 第一方来源与证据映射

1. 2026-08-12 01:12 EDT 本机直接验证：`ccusage --version` 返回 `20.0.19`，`ccusage codex daily --json --offline` 返回上表两行及其 Token 组成；直接支持燃烧量、部分日标注和 input／cache-read 占比。
2. [K13（Orca 账户快照必须以 updatedAt 前进判定新鲜度）](./orca-account-snapshot-freshness.md)：两次预注册实验保存冻结快照、`updatedAt` 与窗口身份边界；支持周窗百分比只作滞后代理、同时间戳不作差值解释。
3. [今夜自治运营记录 §48（三方审阅真实样本与知识库决定）](../work/records/2026-08-10-federated-session-entry/record.md)：保存长上下文、多轮审阅、否决、修订与复核的自然工作负载；与日聚合共同限定“高燃烧形态”推论的适用背景。
4. [今夜自治运营记录 §49（worktree 清理误删活跃 Worker）](../work/records/2026-08-10-federated-session-entry/record.md)：保存两个误删对象、远端成果幸存事实、分支名碰撞根因与 `worktreePath` 排除集程序；直接支持清理结论。
5. 2026-08-12 今夜本机直接验证：38 个 worktree 中 30 个是已完成任务残留，旧 terminal 排除集判据全部漏清；运行任务保留集配合逐对象 Git 安全门后一次清到 8 个。直接支持旧判据失效与新判据的当前样本有效性。
6. [关联 #243（worktree 清理例程与本批清理）交付回执](https://github.com/Eridanus117/agent-control/issues/243#issuecomment-5281742367)、[独立核验结论](https://github.com/Eridanus117/agent-control/issues/243#issuecomment-5281942587)与[收口回执](https://github.com/Eridanus117/agent-control/issues/243#issuecomment-5282124103)：保存 `tools/worktree-gc` 的安全门、11/11 单测、真实批次 18→7（12 根移除、0 失败）与例程采纳事实；支持结论 2 的工具化落点。

## 两道准入门逐项判定

### 结论级判定

| 结论 | 价值门 | 可信门 | 判定依据 |
| --- | --- | --- | --- |
| 1. Token 日聚合测燃烧 | 通过 | 通过 | 日聚合可重复读取且给出精确的 total／output／input／cache-read／cost；K13 独立限定账户快照冻结与不可换算边界。 |
| 2. 运行任务保留集收口清理 | 通过 | 通过 | 两个真实活跃 worktree 误删事故反证分支名匹配；38→8 的今夜直接样本反证 terminal 排除集，并验证新判据在当前环境可用。 |

### 八项可信门共同核对

| 可信门 | 判定 | 依据 |
| --- | --- | --- |
| 1. 明确回答的问题 | 通过 | 问题限定为本机自治运营的燃烧测量和 Orca worktree 终局清理。 |
| 2. 可直接使用的结论和必要解释 | 通过 | 两条结论各给出触发条件、最短动作、拒绝门和不能推出的内容。 |
| 3. 第一方来源或可重复验证过程 | 通过 | `ccusage` 命令可重复；K13 含预注册实验；§48／§49 保存今夜自然工作负载与事故链。 |
| 4. 对象、版本、环境和核验时间 | 通过 | 页首与数据表列明 Windows、Orca、`ccusage`、时区、日期及部分日水位。 |
| 5. 例外、仍未知内容和不能推出的结论 | 通过 | 分别排除账单／容量／固定换算／单任务归因，以及 Ready terminal／分支名／`worker_done` 的过度解释。 |
| 6. 明确的失效条件 | 通过 | 两条结论分别列出日志、字段、计量、版本、远程运行与生命周期变化。 |
| 7. 下次最少复核步骤 | 通过 | 只需自然读取日聚合与下一次自然清理的列表和状态证据，不另造消耗或待删对象。 |
| 8. 人容易理解、Agent 足以复用的表达 | 通过 | 正文按触发、最短动作、边界、失效与复核组织，危险匹配键明确排除。 |

## 不适用范围

- 供应商账单、订阅价值、套餐总容量或 Token→周窗口的精确换算；
- 自动扩缩容、自动切模型、自动消费券、自动提醒或固定轮询；
- 仅凭一天聚合评价单个 Agent、模型、任务或方法的效率；
- 未经授权的终端、进程、worktree、远端分支或其他 Session 资源处置；
- 把本包升级成常驻清理脚本、Hook、调度器或新的产品依赖。
