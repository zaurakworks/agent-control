# 当前公共知识

本目录是仓库唯一正式公共知识入口，只列同时通过价值门与可信门、当前仍可直接复用的公共知识包。准入、复核、更新和退出规则以 [`authority/01-knowledge.md`](../authority/01-knowledge.md) 为准。

`work/**`、历史、试用材料、研发记录和未列入下表的文件都不是当前知识。某条结论无法按包内的最少步骤确认仍有效时，应立即停止直接复用该结论；包内不再有可复用结论时，才将整个包从本入口移出。

## 发现通道与可命中性（实测）

关联 [#227（知识消费实验）](https://github.com/Eridanus117/agent-control/issues/227)的 6 次 fresh 被试 run 实测了知识被自然发现的通道：仓根 `README.md`「文件职责」与目录列表 → 文件名语义 Glob、正文症状词 Grep、[检索卡](./retrieval-cards.md)，以及 orchestration 等 Skill 的互补指引；本入口表在该轮 6 次 run 中零次被读（观察记录，见 [关联 #227（知识消费实验）结论评论](https://github.com/Eridanus117/agent-control/issues/227#issuecomment-5277106002)）。本表仍是唯一正式公共知识准入登记面，`authority/01-knowledge.md` 的入口结论不变；「唯一正式入口」发现假设与实际行为差距的重新审视，按该轮候选留给后续波次。本次只按实测通道加固入口：

1. **文件名语义**：新包文件名延续「域＋症状／动作」语义（如 `windows-agent-ops`、`orca-supervised-dispatch`），不使用只有编号或抽象主题的文件名；
2. **症状词可命中性**：包正文保留错误码、界面文案与中英别名密度（如 `0x80070020`、`LongPathsEnabled`、`input_accepted`、sharing violation），下表每组另附「常见症状与别名」行，使症状词 Grep 也能命中本表；
3. **看似通用任务盲区**：看似通用、实则本机有已验证边界的动作（如在 PowerShell 中构造并发布 GitHub 多行正文、修改 ProjectV2 单选字段、GraphQL 写入报错后重试），实测存在「任务看似通用 → 零检索」盲区；需要本机知识时，主动按[检索卡](./retrieval-cards.md)的 `stage`／`object` 或可查询工具的 action 名问路。关联 [#240（知识入口重构）](https://github.com/Eridanus117/agent-control/issues/240)合同内的 S2 场景冒烟复测（2 次 fresh headless）进一步定界：prompt 明示「针对本机实际情况」仍 0/2 零检索、入口改动未被行使——**盲区比 S1 型自足任务更宽，静态入口改造不足以触达**（n=2 观察，不外推频率，也不构成入口回归证据；见[关联 #240（知识入口重构）收口回执](https://github.com/Eridanus117/agent-control/issues/240#issuecomment-5282120269)）。关联 [#251（动作型知识触发）](https://github.com/Eridanus117/agent-control/issues/251)的 251-D1 已否决注入式 Hook 投递；当前路线是便宜、好记、由 Agent 主动选择的 ask 式按名问路。

## 当前知识包

按当前任务主题进入下列分组；每个知识包仍独立适用自己的对象、环境、失效条件与最少复核步骤。

### 项目入口

需要确认 Codex 与 Claude Code 如何加载仓库指令并以最低重复成本共享入口规则时，从本组开始。

常见症状与别名：`AGENTS.md`、`CLAUDE.md`、项目指令加载、入口规则共享、指令重复维护。

| 编号 | 窄问题与适用范围 | 当前包 | 最近核验 |
| --- | --- | --- | --- |
| K1 | Codex 与 Claude Code 在代码仓库中加载项目指令，以及以最低重复成本共享入口规则 | [Codex 与 Claude Code 的项目指令加载规则](./project-instructions.md) | 2026-08-11 |

### Orca 运行与协调

需要派发与收口受监督 Worker，或在协调 Session 中断后安全继任时，查看本组。

常见症状与别名：`worker-start`、`input_accepted`、`input-missing`、`composer-pending`、`dispatch-show`、派发后没动静、验活、单次点火、收口释放、`retained`、双协调、headless 车道、事件唤醒、`Stop` 回执、cron 兜底。

| 编号 | 窄问题与适用范围 | 当前包 | 最近核验 |
| --- | --- | --- | --- |
| K2 | 用 Orca 受监督路径派发与收口 Claude/Codex Worker：路径选择、提交竞态、Provider 开始证据候选、三态验活与单次点火工具、mutation 回执与 tab／PTY 核验 | [Orca 受监督派发的路径选择、mutation 回执与收口核验](./orca-supervised-dispatch.md) | 2026-08-13 |
| K12 | Orca 协调 Session 经压缩、计划交接或意外终止后，如何恢复合同、Run、Delivery 与在途 Worker，同时避免双协调并核验重派是否真正开始 | [协调者压缩存续与继任协议](./coordinator-succession-protocol.md) | 2026-08-13 |
| K23 | Orca 1.4.181 的最窄战术消费者前件是否成立，以及机械窄任务的受限 headless 车道已有何种收益、成本与观察损失证据 | [机械窄任务的 headless 车道已有单波次样本，Orca 窄战术消费者前件仍不成立](./bounded-headless-mechanical-lane.md) | 2026-08-13 |
| K25 | 协调者等待 Claude Worker 完成时，事件唤醒的当前生效状态、聚合桥设计不变量、单样本时延与退化边界 | [Claude 完成事件唤醒是前台加速通道，聚合版桥已合并未安装](./coordinator-event-wakeup.md) | 2026-08-13 |

### GitHub 协作与恢复

需要安全引用 Issue、在 GraphQL mutation 报错或部分成功后判断能否重试，或在 PowerShell 中构造与发布多行 Markdown 正文时，查看本组。

常见症状与别名：关闭关键词误关 Issue、「关联 #N」、`clientMutationId`、mutation 超时、部分成功、here-string、`--body-file`、多行正文、UTF-8 BOM、CRLF、逐字回读。

| 编号 | 窄问题与适用范围 | 当前包 | 最近核验 |
| --- | --- | --- | --- |
| K3 | 在 GitHub PR 中安全引用不应被关闭的 Issue（关闭关键词不解析否定句） | [GitHub 关闭关键词不解析否定句](./github-closing-keywords.md) | 2026-08-11 |
| K11 | GitHub GraphQL 远端写入报错或部分成功后，如何区分客户端关联标识与可安全重试的远端证据 | [GitHub GraphQL mutation 重试必须以远端目标状态为准](./github-graphql-mutation-recovery.md) | 2026-08-11 |
| K17 | Windows 原生 PowerShell 中如何可靠构造、传递与逐字回读 GitHub／Git 多行 Markdown | [Windows 下 PowerShell／GitHub CLI 多行 Markdown 传输边界](./windows-powershell-multiline-transfer.md) | 2026-08-12 |

### Windows Agent 运维

需要在 Windows Agent 任务中处理脚本策略、深路径／临时目录、文件锁、PTY 生命周期或管理员动作时，查看本组。

常见症状与别名：长路径、`MAX_PATH`、`LongPathsEnabled`、深子目录无法创建文件、文件正被另一个进程使用、`0x80070020`、sharing violation、文件锁、`%TEMP%` 清扫、PTY 残留、执行策略、Defender。

| 编号 | 窄问题与适用范围 | 当前包 | 最近核验 |
| --- | --- | --- | --- |
| K24 | Windows Agent 如何只在命中风险时读取宿主事实，并以短根、任务自有临时目录、句柄感知发布、PTY 五事实与高权分段避免自动修机和误收口 | [Windows Agent 运维先按需实测，再隔离路径、句柄、PTY 与高权动作](./windows-agent-ops.md) | 2026-08-12 |

### Plugin 维护

需要升级 Claude Code／Codex Plugin、验收版本化缓存、处理 Skill description 限制，或在会话中装载项目级 skills、以 headless 斜杠命令真跑 skill 时，查看本组。

常见症状与别名：安装成功但内容没变、版本化缓存、旧缓存、卸载重装、directory marketplace、Skill description 长度、`Unknown skill`、`/reload-skills`、斜杠命令不展开、`C:/Program Files/Git/` 前缀、`MSYS_NO_PATHCONV`、`--allowedTools`、headless 权限拒绝。

| 编号 | 窄问题与适用范围 | 当前包 | 最近核验 |
| --- | --- | --- | --- |
| K4 | Claude Code／Codex plugin 的升级、版本化缓存验收与 Skill description 限制 | [Claude Code 与 Codex Plugin 维护、验收的已验证陷阱](./claude-plugin-maintenance.md) | 2026-08-11 |
| K27 | Claude Code 项目级 skill 的装载发现时机，以及 `claude -p` headless 子会话中斜杠调用与真跑含命令技能的静默失败 | [Claude Code skill 装载时机与 headless 斜杠调用的已验证陷阱](./claude-skill-loading-headless-invocation.md) | 2026-08-13 |

### 一致性验收

需要同步入口母本与全部副本，或在 Windows 混合换行环境中核验内容一致时，查看本组。

常见症状与别名：`entry_sync`、入口母本、副本漂移、状态不一致、CRLF／LF、SHA-256 不一致、换行规范化。

| 编号 | 窄问题与适用范围 | 当前包 | 最近核验 |
| --- | --- | --- | --- |
| K5 | 修改系统入口母本后同步全部拷贝并验收一致（entry_sync 三步） | [入口母本同步工具 entry_sync 的用途与用法](./entry-sync.md) | 2026-08-11 |
| K6 | 本机 Windows 混合换行环境下，版本化来源与安装副本的一致性验收方法 | [跨端文件一致性验收必须先规范化换行](./newline-normalized-acceptance.md) | 2026-08-11 |

### ProjectV2

需要安全修改 GitHub ProjectV2 单选字段选项、避免破坏既有选项与条目取值时，查看本组。

常见症状与别名：单选字段、选项被删、条目取值被清空、全量替换、`updateProjectV2Field`。

| 编号 | 窄问题与适用范围 | 当前包 | 最近核验 |
| --- | --- | --- | --- |
| K7 | 修改 GitHub ProjectV2 单选字段选项时，如何避免删除既有选项并清空条目取值 | [ProjectV2 单选字段选项修改是全量替换](./projectv2-single-select-options.md) | 2026-08-11 |

### 会话与资源

需要辨明会话恢复与任务接手、区分六类资源观测面，或判断 Orca 账户快照新鲜度时，查看本组。

常见症状与别名：`resume --last`、`--continue`、恢复错会话、Session ID、任务接手、额度、`usedPercent`、`updatedAt` 没动、账户快照陈旧、六观测面。

| 编号 | 窄问题与适用范围 | 当前包 | 最近核验 |
| --- | --- | --- | --- |
| K8 | 并发与长程任务中，如何区分精确会话恢复、Provider 局部 checkpoint／resume、Worker 任务接手与协调者 Run 继任 | [编码 Agent 会话恢复必须绑定精确身份](./session-resumption-identity.md) | 2026-08-12 |
| K9 | 观测 Agent 资源时，如何区分上下文、账户窗口、Session Token、费用、运行资源与交付成果 | [Agent 资源的六个观测面不可互相代替](./resource-observability-boundaries.md) | 2026-08-11 |
| K13 | 读取 Orca Codex 账户快照时，如何用 `updatedAt` 区分新鲜样本与缓存读数 | [Orca 账户快照必须以 updatedAt 前进判定新鲜度](./orca-account-snapshot-freshness.md) | 2026-08-11 |

### 外部能力生命周期

需要引入或退出外部 Agent Skill／Plugin、核验各 Provider 的真实行为与可恢复退场，或评估外部工具型／技能型生态并准备输出对比性结论时，查看本组。

常见症状与别名：可安装不等于行为等价、逐端验收、试用退场、跨 Provider 差异、案头评测、使用锚点、读而未用、防御性对照、「没什么可学」。

| 编号 | 窄问题与适用范围 | 当前包 | 最近核验 |
| --- | --- | --- | --- |
| K10 | 引入或退出外部 Agent Skill／Plugin 时，如何避免把可安装误当成跨 Provider 行为等价 | [外部 Agent Skill 与 Plugin 需要逐端验收和可恢复退场](./external-agent-capability-lifecycle.md) | 2026-08-11 |
| K26 | 评估外部工具型／技能型生态时，什么样的评测设计才允许输出「没什么可学／我方已更好」类对比性结论 | [外部生态评测必须带使用锚点，零使用样本不得输出对比性结论](./ecosystem-evaluation-usage-anchor.md) | 2026-08-13 |

### 思考方法学习与参考

本组是负责人学习／参考面：解释概念原义、适用与误用边界，并用本仓真实决策帮助浏览。Agent 的方法触发、执行步骤、成本、停止和证据资格仍以 APS 可执行方法登记面为准；本组不建立第二个方法控制器，也不产生执行授权。

常见症状与别名：思考方法、行动前三门、APS 登记面、概念参考、工作方式。

| 编号 | 窄问题与适用范围 | 当前包 | 最近核验 |
| --- | --- | --- | --- |
| K21 | 负责人在 Agent 系统真实决策中怎样浏览少量高价值思考方法，并区分概念参考面与 APS 可执行登记面 | [可浏览思考工具箱](./thinking-toolkit.md) | 2026-08-12 |
| K22 | APS 行动前三门能否被更短的薄规则等效替代，以及为什么首个预注册对照选择保留现行三门 | [行动前三门的薄替代在首个预注册对照中未满足等效门](./action-gates-thin-alternative-validation.md) | 2026-08-13 |

### 公共知识检索

需要判断结构化技术知识何时值得评估向量召回，以及篇数能否充当启动阈值时，查看本组。

常见症状与别名：BM25、向量召回、篇数阈值、检索卡、`stage`／`object` 硬筛、改述查询。

| 编号 | 窄问题与适用范围 | 当前包 | 最近核验 |
| --- | --- | --- | --- |
| K14 | 结构化技术知识语料何时值得评估向量召回，以及篇数能否充当启动阈值 | [公共知识检索不以篇数启动向量层](./public-knowledge-retrieval-activation.md) | 2026-08-11 |

本组另登记一项由现有 K 包派生的检索投影。投影只把主动问路所需的阶段、对象、别名、最短动作、来源、证据边界与失效条件结构化，供调用者按 `stage`／`object` 硬筛后以 BM25 取卡；完整结论与两道准入门仍以来源 K 包为准，投影不替代 K 包，也不产生新的结论或授权。

| 类型 | 资产 | 来源范围 | 证据边界 |
| --- | --- | --- | --- |
| 检索投影 | [结构化问路登记与 BM25 检索卡](./retrieval-cards.md) | K2、K3、K4、K5、K6、K8、K11、K13、K16、K17、K18、K19；K14 提供语义层评估边界 | A–C 小样回放有效；D–W 最多完成当前交付验收与现有场景回放；已获首个自然消费样本（关联 [#227（知识消费实验）](https://github.com/Eridanus117/agent-control/issues/227)S3R2：fresh 被试无诱导读取本卡集并定位 K2），不因单样本升级证据或扩大投影范围；主动问路的自然采用率、误命中成本、独立自然样本准确率与长期召回仍待验证 |

### 自治与多 Session 审阅

需要评估 Agent 系统主动自审的作用、机械核验多 Session 审阅的身份绑定与独立性，或在自治运营／协调中逐条核验事实、测量燃烧、安全清理 worktree、判断共享单一来源能否并行时，查看本组。

常见症状与别名：自审、席位身份、先密封后公开、三席一致、Token 燃烧、`ccusage`、worktree 误删、活跃排除集、共享单一来源串行。

| 编号 | 窄问题与适用范围 | 当前包 | 最近核验 |
| --- | --- | --- | --- |
| K15 | 高影响 Agent 系统资产建成后，主动多视角自审能否先于负责人纠偏发现方向缺陷，以及发现后应暂停哪些路径 | [Agent 系统自审在一例中先于负责人纠偏发现方向缺陷](./agent-system-self-audit.md) | 2026-08-12 |
| K16 | 多 Session 审阅如何证明席位、评论与运行身份正确绑定，并避免公开顺序造成伪独立 | [多 Session 审阅必须机械核验联合身份并先密封后公开](./multi-session-review-identity.md) | 2026-08-12 |
| K18 | 三方审阅何时可替代负责人决定、怎样与常规交付验收分界，以及如何以三席一致消费修订后的决定 | [三方审阅只替代已授权决定，且必须三席一致后落地](./three-party-review-consensus.md) | 2026-08-12 |
| K19 | 自治运营中如何以 Token 日聚合测量燃烧，并以任务运行态保留集与逐对象 Git 安全门（`tools/worktree-gc` 例程）收口 worktree 清理 | [自治运营以 Token 日聚合测燃烧，以任务运行态保留集收口 worktree 清理](./autonomous-ops-measurement-and-cleanup.md) | 2026-08-13 |
| K20 | 自治协调如何逐条核验事实、按活跃绑定清理，并在路线图组波前识别共享单一来源的串行依赖 | [自治协调以逐条核验、活跃绑定与单一来源串行守住边界](./autonomous-coordination-discipline.md) | 2026-08-12 |

K20 单独成包而非继续扩充 K19：K19 保持“资源测量＋worktree 清理”的既有适用边界；K20 只引用 K18 的事实核验样本与 K19 的清理程序，并新增“共享单一来源必须串行”的编排纪律。这样既给三条纪律一个统一的协调入口，也不复制两个既有知识包的完整机制。

这里没有全库索引、候选区、私域知识或自动更新机制。
