# Agent 系统全局研究基线

> 状态：R 阶段 8/8 已收齐并综合，非权威、非授权、非方案。正式合同与负责人审阅面见 https://github.com/Eridanus117/agent-control/issues/43 。
> 综合者：Fable 5 全局协调 Session（term_30a4317a-79a0-4ead-84bb-9692496ca347）；各分区事实以研究者原评论为准，本文件是压缩索引，冲突时以原评论为准。
> 观察时间：2026-08-11（America/New_York）。R 阶段评论发布于 2026-08-11T12:49–12:58Z。

## 范围

研究当前 Agent 系统全部已确认问题领域及其关系：原始诉求与产品边界、知识与研发记忆、问题求解与自我改进、长程工作与 Session 恢复、多 Agent／多 Provider 协作、资源运营、Agent 配置与扩展面、GitHub／Orca／工作环境与外部生态。

本阶段只记录会改变整体架构选择或产品边界的事实、约束、失败样本和未知；不提出修复、方案、路线图或实施建议。

## 输入索引（全部可追溯）

**#43 R 阶段八条事实评论：**

| 分区 | 评论 | 规模 |
| --- | --- | --- |
| R1 诉求与产品边界 | [5253406856](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253406856) | 9.4K |
| R2 知识与研发记忆 | [5253414521](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253414521) | 6.1K |
| R3 问题求解与方法资产 | [5253393620](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253393620) | 12.9K |
| R4 长程工作与 Session 恢复 | [5253461458](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253461458) | 5.8K |
| R5 协作与并发 | [5253386158](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253386158) | 11.8K |
| R6 资源与经营指标 | [5253439235](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253439235) | 7.6K |
| R7 配置、Skills、Plugins 与分发 | [5253398159](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253398159) | 9.0K |
| R8 平台、Windows 与生态复用 | [5253478669](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253478669) | 7.9K |

**#42 攻防两轮七条评论**（联邦控制面、并发与 Session 生命周期）：第一轮 [A 饥饿](https://github.com/Eridanus117/agent-control/issues/42#issuecomment-5253247059)、[B 并发](https://github.com/Eridanus117/agent-control/issues/42#issuecomment-5253210484)、[C Session](https://github.com/Eridanus117/agent-control/issues/42#issuecomment-5253211904)、[D 控制面](https://github.com/Eridanus117/agent-control/issues/42#issuecomment-5253220837)、[E 极简红队](https://github.com/Eridanus117/agent-control/issues/42#issuecomment-5253242848)；第二轮 [F 矛盾矩阵裁决](https://github.com/Eridanus117/agent-control/issues/42#issuecomment-5253365921)、[G 原生复用红队](https://github.com/Eridanus117/agent-control/issues/42#issuecomment-5253339051)。

## 研究分区

### R1 原始诉求、诉求树与产品边界

- 总目标（#6）与四领域＋一横向结构一致同源；四领域中只有 #7（协作）、#11（长程）两支有开放下级投入，#8/#9 开放子项为 0、#10 子项为 0。
- 证据等级全表上限是「样本有效」（8 项）；「产品采用」「长期依赖」均为 0；唯一「当前满足」是已关闭的 #13。字段间互不推导只有 #13 一个实证。
- 6 项诉求树覆盖空白：Agent 配置/Skills/Plugins 分发、工作环境、复用-Fork-自建决定、研发记忆、控制面自身维护、资源运营投入不可见（#10 有 0 子项但该领域已有交付资产）。
- 7 项事实冲突：#28/#30/#31 完全不在 Project；#17 执行状态为空而隐身；5 个一级诉求「样本有效」高于其全部交付子级且无样本出处；#10 标「尚无实现」与已交付资产矛盾；「就绪」唯一条目是 90 天后定时维护。
- 被明确否定/撤回清单与「本轮没有确认」白名单是当前唯一授权边界；大量「明确不授权」项跨权威重复出现（Actions Runner、锁、Hook、Webhook、常驻调度器、自动派发/合并、评测平台、自建 UI 等）。

### R2 知识、研发记忆、研究复用与可信度

- 正式公共知识面 = 1 条（K1 项目指令加载规则）；知识入口唯一（knowledge/README.md）；价值门＋八项可信门是准入合同；保存≠可信≠权威。
- 保存、发现、可信复用、行为改变是四个可独立失败的环节，各有实证：#35 发现失败（靠全库搜索兜底）、E21 可读层压缩丢五样本七概念族且原始索引产物不持久（只能回读 37.7MiB transcript）、PR #39 两轮人工复核修 6+4 个精度问题、Skill 仅解决流程。
- 外部第一方记忆能力（Claude auto memory[本机关闭]、Codex Memories[本机关闭且公开合同不详]、Copilot Memory[28 天未用即删、preview]、Spaces/Projects[上下文聚合非可信结论]）语义均不同于当前「公共当前结论＋逐条可信门」合同。
- 关键未知：自然复用 ROI 无端到端样本；包数量增长后的检索/冲突/退出成本；私域零样本；跨 Host 原始记忆完整性。

### R3 问题求解、元方法、自我改进与行为资产

- 六类方法路线中仅 2 类有独立可执行资产（grilling、knowledge-maintenance），4 类仅控制文本——与 authority/03「六类不是六个新 Skill」一致而非遗漏；但除 2、3 路线外方法是否运行只能靠执行者自述。
- grilling 是唯一同时规定产出格式、推进单位、轮次判据的方法资产；「退化为 grilling」更可能是资产形态差异（I1 推断）。
- aps 0.1.3 已内置「持久行为入口」判据、五级证据链、最小实验 vs 最小完整交付判据表；authority/ 版本记录落后安装态两个补丁。
- 两类相反根因并存：#36 触发谓词前件不覆盖「丰裕态」（已排除 Skill 路由断裂）；#28 E04/§29 规则已加载但执行者不遵守（已决定观察遵循率而非加规则）。修复方向相反。
- 第一方 Skill 预算约束：描述预算=上下文 1%、单条 1536 字符上限、溢出按调用最少者丢弃；issue-workflow 描述（1999 字符）本 Session 已实际截断。方法资产数量存在第一方上界信号。
- 本次 R/I/C 方法本身是 #43 正文手写的零资产一次性文本，按 aps 自身判据属「持久行为入口未满足」（S1）。

### R4 长程工作、上下文、Session 恢复与人机对齐

- 「精确恢复同一 Session」与「新 Session 接管任务」是两种能力，各有半程证据，尚无一个非中心完整样本合拢（#26：精确恢复但仅评论写权 / 新 Session 领取真实分区但由中心启动）。
- Provider resume 事实：Codex resume 按 UUID/name/--last（#34 反样本：--last 在并发现场恢复错 Session，后续 PID 终止又伤及根 Session）；Claude --resume 带回完整对话史但不恢复若干启动参数；闲置 1h＋100k token 可选摘要恢复，摘要路径丢失未保留内容；同一 Session 双终端恢复会交错写同一 transcript；默认 30 天清理。
- Orca 公开 CLI 无「按 Provider Session ID 恢复 Agent」子命令；#18 实测运行所有权发现假阴性（浮动终端不属 worktree、占用只在 Run objective 自由文本中）。
- #21 三 Session 样本：15m15s 双交付、逐步介入 0 次、25.34M token 多为缓存读；但无方向纠正、无串行对照、无统一度量——证据上限「有限单样本有效」。

### R5 多 Agent／多 Session／多 Provider 协作与并发

- **隔离面＝零**：探测时 11 终端中 10 个共用同一 checkout，git worktree 仅 1 个；文件级隔离 0，隔离全由合同文本承担（F1）。
- **共享写入检测能力＝0 的直接运行证据**：8＋只读 Worker 运行期间共享 main 被另一 Session 提交 d499d29，无任何 Orca 冲突信号；安全完全来自「另一侧恰好只读」（F3）。终端无归属校验，任意持 handle 者可写（F4）。
- Orca 明文不调度、不推断冲突（F6）；生命周期权威在 Dispatch 不在终端（F7）；Task 仅 6 状态无暂停语义（F8）；Dispatch 已带类租约字段 capability_hash/capability_revoked_at/process_incarnation/contract_version，但 CLI 未暴露签发/撤销动词（F9）。
- 高层 worker-start 曾 ≥4 批次 selector_not_found；低层 dispatch 路径 worker-release 稳定返回 dispatch_not_found（截至本批累计 10 次），需人工精确关闭 tab；该模式未修复（F17）。
- 终端元数据无 provider/sessionId/taskId，agentKind 全 null；跨 Session 决定交接仍不可核验（F15）；Run 与 GitHub 无结构化外键，worktree.linked* 槽位存在但全 null（F18/F19）。
- 已验证并发形态仅一种：同一 Issue 多执行者各追加一条评论（append-only 天然不相交）；对正文/Project 字段/分支/文件的并发安全从未验证（F27）。
- 非中心派发第三次反例：#41/#42/#43 全部由中心 Session 发起（F26）；跨 Provider 组寻址接口存在但与可见性缺口并存（F12 vs F15）。

### R6 资源、Token、成本、容量与经营指标

- 至少六个不可互换观测面：瞬时上下文占用/压缩、账户窗口/权益、Session 累计 Token、货币账单、运行并发/终端资源、验收产出/注意力。现有工具只覆盖部分且分散。
- 实测分离证据：会话累计 4.08M token vs 同时刻上下文占用 193K（不同分母）；Claude 官方 /cost /usage /context 三命令佐证。
- 账户快照跨时刻变形：Codex reset credit 同日 object(1)→null→object(1) 原因未知；weekly 23%/08-15→3%/08-18 未归因；账户百分比跨 surface 共享无法归因单 Session。
- 货币成本不可读：自有入口 --no-cost、Orca 白名单无账单字段；窗口容量≠货币成本。
- #10 与 #16 状态漂移（同一能力在缺口 Issue 与实验父 Issue 各表述）；#17 并行批次仅证明「并行没有制造问题」不支持「并行提高吞吐」（样本 2、无串行对照、观测 CLI 当批失败）。
- 负责人注意力无单位、无计时工具、无统一 batch receipt；#26 P1-4 运行度量零记录。

### R7 Agent 配置、系统入口、Skills、Hooks、MCP、Plugins 与分发

- 同一套入口规则 6 份副本（3 版本化＋3 安装产物）＋验证器常量≈第 7 份；镜像义务只覆盖 3 份中 2 节；「父目标验收」「经营总账维护」两节一致性无规则约束。换行符差异使 hash 不能做一致性验收。
- 恒定开工预算：无条件入口 10.3KB＋任务必读 34.6KB ≈ 44.8KB；current.md 12.6KB 已超「短快照」定义。
- 跨 Provider 差异：Claude 9 插件 vs Codex 21 插件（14 个 Claude 无对应物，含 codex-marketplace 3 件与 11 个 openai-bundled）；Hooks Claude 11 类全指向 Orca 转发脚本 vs Codex 空；MCP Claude 1 个 vs Codex 3 个；Codex 47 条权限规则全 allow 且 2.5 个月未更新。
- 安装证据链缺陷：directory 型 marketplace 下 gitCommitSha 不随内容刷新，不能作为「安装内容=某提交」证据；Claude 缓存累积 17 个孤儿版本目录（946KB）而 Codex/Orca 不保留（GC 行为不同）；`openai-curated` 插件启用但 marketplace 未声明。
- 运行面配置（启用集合、权限规则、Hook 绑定、MCP、Skill 禁用表）不可跨主机重建；入口正文与 Skill 正文可重建。
- `issue-to-merge` 仍在两个 Codex 运行面启用；权威定位为「待审计候选，不因存在成为长期依赖」；Claude 缺其等价能力是否有意的产品决定，authority 无记录。

### R8 GitHub、Orca、工作区、Windows 与外部生态

- GitHub 原生表达能力：sub-issue 8 层/100 子项、dependencies、Project 17 字段＋6 个 enabled 内建 workflow（具体过滤条件未读出）、issue/issue_comment 事件可触发 Actions（需 default branch 有 workflow 文件，当前 0 workflow、0 runner、无 .github/）。
- **强制门当前不可用**：私人仓＋免费账户下 branch protection/rulesets 返回 403（需 Pro 或公开仓）；「能表达/能触发」≠「能强制」。
- Windows 环境：Win11 Pro、PS 7.6.3、git 2.55、进程级 CODEX_HOME 指向 Orca runtime home（User/Machine 均未设置）；PATH 当前可发现全部 CLI，只证明当前进程。
- Orca：MIT 开源（stablyai/orca），本机 1.4.177 vs 上游 release 1.4.180；status 公布 remote environments/federation/worker launch/linked-work-item/文件 mutation ownership 等 capability；上游含 PS/Shell/Batch 文件与机器级语言规则的冲突范围未分类。
- codex-marketplace（seven332）：3 插件/21 SKILL.md，仓级 LICENSE 缺失（licenseInfo=null），schemas 明确非官方派生；issue-to-merge/research-to-plan 改写自 vm0-ai/team-skills；安装 revision 与远端 HEAD 一致。
- 跨 Agent Skill 生态：mattpocock/skills ADR 记录 Codex plugin manifest 单 skills path/symlink 在 cache copy 后为空的失败样本（2026-08-05，未本机复验）；vercel-labs/skills 兼容矩阵显示 fork context 仅 Claude、Hooks Codex 无；Agent Skills 规范 allowed-tools 仍 experimental。「文件可安装」不能推出「行为等价」。

## 跨域约束（会约束任何整体架构的综合事实）

1. **写入安全当前完全是合同约定，不是机制**：隔离面零＋共享写入检测零＋终端无归属校验（R5 F1/F3/F4）。任何提高并发的方案必须先回答这一层，或诚实接受合同约定。
2. **通用原子认领在当前后端不存在**：GitHub REST 无通用写 CAS（#42 B/F 已按官方文档裁决出局）；私人仓无 branch protection（R8）；Orca 不推断冲突且租约字段未暴露动词（R5 F9）。依赖原子租约的设计在当前组件上不可实现。
3. **身份四层断裂**：合同（Issue）/编排（task/ctx/dcap）/运行面（term/pty/incarnation）/Agent 会话（sessionId/rollout）无持久交叉引用；#34 实证误恢复；worktree.linked* 与 Orca 内部 session 映射是存在但未接通的槽位（#42 C、R5、R4）。
4. **生命周期收口存在稳定断裂**：低层 dispatch 的 worker-release 10 次 dispatch_not_found；高层 worker-start 曾稳定 selector_not_found；人工精确关 tab 是当前唯一可靠收口（R5 F17，本批 4 次复现）。
5. **上下文与配置预算是硬约束**：开工必读 ≈44.8KB；Skill 描述 1% 预算＋1536 上限＋按频次丢弃已实际截断 issue-workflow；入口 6+1 份副本的同步成本随规则增长（R7、R3）。
6. **度量与证据基础薄弱**：统一运行度量零记录、负责人注意力无基线、证据等级上限「样本有效」且 5 个一级节点的该值无样本出处、43% 状态债、authority 版本记录滞后（R1/R3/R6、#41、#26）。任何 ROI 主张当前不可证伪；X3（注意力口径）是唯一必须先行的度量。
7. **需求 100% 内生**：37/37 Issue 自产自评；「饥饿」不可观测为真问题；唯一证伪路径是外生任务样本（#42 E、X4）。
8. **非中心联邦未验证**：三次全中心派发反例；L1 自然触发 0；跨 Session 决定交接不可核验（R4/R5）。「联邦式」当前是入口规则文本，不是运行事实。
9. **出口债先于入口机制**：已观测失败全部在出口侧（3 项已满足未关闭、4 项观察中无唤醒、状态空值隐身、就绪被占用），入口侧（发现/排序/认领）零失败观测（#42 A/E/F 一致）。
10. **外部依赖的可逆性差异**：Orca MIT 可 Fork 但版本/语言规则冲突未分类；codex-marketplace 无仓级许可且非官方 schemas，负责人倾向渐进脱离（能力盘点/依赖映射/替代/可逆迁移已纳入本轮 I/C 范围）；GitHub 强制门被账户计划约束；跨 Agent Skill 格式可移植但行为不等价（R7/R8）。
11. **方法与知识资产的准入-复用闭环尚未跑通**：方法有效性无独立度量（有意不建评测平台）；知识自然复用零端到端样本；最大方法应用是零资产手写文本（R2/R3）。

## 未知（按对架构选择的影响排序）

1. Orca Dispatch 类租约字段（capability_revoked_at/process_incarnation）能否作为显式撤销/代次原语（R5 U2）——决定「合同约定」能否升级为「机制」而不自建。
2. 新 Session 能否为已 dispatched task 取得可用令牌；dispatch 能否 rebind 新 handle（#42 X1）——决定 takeover 是否真实路径。
3. worktree.linkedIssue 可否 CLI 写入并被其他 Session 用于所有权发现（R5 U4）——决定 Issue↔运行面外键的最低成本实现。
4. 同一 Issue 被两个 Run 同时派发是否被阻止（R5 U1）；Actions issue 事件能否安全唤醒本机 Orca（R8）——决定 L3 离线唤醒与自动派发的下界。
5. 负责人注意力口径（#42 X3=#26 P1-4，必须在下一自然波次前定）；外生任务样本（X4）。
6. Codex/Claude 精确 resume 的恢复边界实测（R4）；observability 会话回执与上下文剩余的缺口（R6）。
7. skillListingBudgetFraction 0.02 的绝对预算与当前截断面（R7 U3）；Codex 端 Skill 预算规格（R3 U2）。
8. codex-marketplace 三件的能力清单、依赖面、替代与可逆迁移成本（负责人新增，I/C 必答）。
9. E21 两个缺失研究文件的消失原因与同类索引悬空频率（R2）。
10. Orca 上游 PS/Shell/Batch 与机器级语言规则的实际冲突范围（R8）。

## 验证面（近零成本，I/C 阶段可直接引用）

- X1：dispatch-show --preamble 对新终端能否产出可用令牌＋rebind 实验（两次命令）。
- X2：为现存 4 个「观察中」条目试写可判定唤醒谓词（近零成本）。
- X3：负责人注意力记账口径先行（约 5 分钟/波，阻塞全部 ROI 结论的可证伪性）。
- X4：一件外生（非 Agent 系统）工作端到端。
- X5：每次准入判定留一行记录（修复「门不触发」与「无候选」同形）。
- X6：capability 撤销原语探测；linkedIssue 写入探测（R5 U2/U4）。
- X7：双 Run 同 Issue 竞态实验（隔离沙箱）。

## #42 已裁决候选（供 I 阶段继承，非权威）

第二轮 F/G 一致方向：控制面只存**合同（Issue 正文含授权对象化条目与唤醒谓词）、回执（attempt/交付收口/冲突有界结果三种 Issue 评论）、指针（current 降级）**，其余派生；并发用**五项共享单点清单（单写者）＋其余 worktree/分支＋PR**，同一 worktree 至多一个可写 Session（派发时判定）；删除租约/心跳/fence 定时器/原子认领/老化分/配额/公平轮转/Session 一等对象/自动派发/新增存储状态/事件后端。F 与 G 的分歧面很小：F 保留 attempt 回执为必须，G 认为 Orca Task/Dispatch 已是受监督尝试不必复制——该分歧留给 I/C 处理。两轮均明确：只修出口、X3 先行、不做第三轮攻防。
