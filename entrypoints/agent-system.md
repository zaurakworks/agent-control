# 当前 Agent 系统入口

这台 Windows 电脑上的 Codex 和 Claude Code 主要用于建设负责人的 Agent 系统。

## 持久实现语言

本节是这台电脑的机器级全局规则：凡本机 Codex 或 Claude Code 维护持久资产，本规则对所有仓库、Provider、Session 和 worktree 生效，不因仓库入口或任务触发条件缩窄。

持久维护的程序、CLI、自动化和验证脚本只允许使用 Go、Python、TypeScript 或 Rust；不得新增或保留 PowerShell、Batch 或 Shell 产品脚本。Markdown、YAML、JSON 等文档与配置不受影响；Windows 一次性命令可经 shell 宿主执行，不得沉淀为脚本资产。

语言选择比较长期可靠性、类型与测试支持、跨平台分发、维护成本和任务适配，不得以当前是否安装为排除理由。本规则不授权批量重写范围外既有资产；既有资产后续实际触及或替换时必须遵守，不可避免的上游或引导例外须有明确证据和负责人决定。

## Agent 系统任务路由

当任务涉及 Agent 系统、知识、长程工作、思考方法、多 Agent／Session、Agent 配置、Skills、Hooks、MCP 或 Plugins 时，先读取 `C:\Users\Morni\workspace\agent-control\README.md` 与 `authority\00-map.md`，再按模式继续：

1. 有明确 GitHub Issue：重新读取远端 Issue 当前正文与状态，只加载它链接的权威；最新授权变化与共享写入所有权同样以远端 Issue 为准，`work\current.md` 只在需要定位主线入口、各来源 observedAt 水位或未解决冲突标志时读取；
2. 没有明确 Issue、但被要求选择下一项工作：按恢复指针定位主线入口，读取经营总账权威和远端观察面，从未满足／部分满足诉求返回 `adaptive-problem-solving`，只形成或选择一个有界 Issue，不把空的“就绪”队列解释成没有工作；
3. 没有明确 Issue 的其他任务：读取恢复指针，由它指向的活动 Issue 与运行面决定加入、保持只读或请求决定。

Session 职责由 Issue 合同与写入所有权决定，不由 Provider、终端或固定身份决定。父／叶子 Issue 都加载 `github-collaboration:issue-workflow`：父级协调授权子树，叶子端到端交付；状态机、风险门、合同压缩与父级回收只由 Skill 维护。退出时回写远端并返回当前任务，不保留永久协调者身份。

Issue 是持久任务合同，不是最高权威。它不能覆盖当前权威、负责人更新的明确指令或有效协作派发；发生冲突时保持相关范围只读并升级。

## 知识按名问路

需要 Windows／PowerShell GitHub 多行 Markdown 或 Windows 长路径／文件锁知识时，可主动按名运行 `python C:\Users\Morni\workspace\agent-control\tools\knowledge_action_trigger\action_trigger.py --action github-multiline-markdown` 或 `--action windows-path-or-file-lock`，按输出读取来源；也可直接读取 K17/K24。这是问路查询，不自动触发、注入或挂 Hook，也不扩大合同、权限或产品决定。

## GitHub 安全引用

发布 GitHub 文本载体（Issue／PR 正文、评论、提交说明等）前，引用其他 Issue／PR 一律写「关联 #N（中文短题）」；禁用全部 GitHub 关闭关键词及其否定式；「不关闭 #N」同样会触发关闭（关联 [#44（安全引用决定）](https://github.com/Eridanus117/agent-control/issues/44)）。

旧仓、旧 Issue／文档／知识／实现仅按当前权威或任务明确要求作待核验材料；普通“同意”“继续”或相邻任务授权，不扩大范围，也不恢复已暂停、结束或未批准事项。

### 持有 Issue 时扩大并行波次

持有明确 Issue 时，只有负责人要求扩大当前并发面、增加并行投入或选择下一波次（包括询问“还有可并发推进事项吗”），才读取经营总账权威与远端观察面，把候选枚举源扩大到整个经营总账的未满足／部分满足诉求，并返回 `adaptive-problem-solving` 形成或选择有界 Issue。

看得更宽不等于写得更宽：当前 Session 的写入所有权仍限于原 Issue 子树；表外候选只能提出、形成获准合同或交给其他所有者。

普通进度询问和当前 Issue 内选择下一切片不触发全局枚举；同一阶段没有新证据时不重复扫描。全局枚举本身不自动建 Issue、派发或修改 Project；例外按 [关联 #244（协调者自主续航）决定回执](https://github.com/Eridanus117/agent-control/issues/244#issuecomment-5281754399)：协调者自主续航——在跑为零且存在价值门通过的候选时，自主形成有界 Issue、派发、核验、按既有预授权合并与收口；开波／收口回执照落远端；价值门＝候选直接服务某开放诉求的未满足成功条件且有证据支撑。节流阀：自主并发面默认 ≤1 波次（≤6 席）；负责人任一纠偏即回落「等待点火」并复盘；运营台实时反映在跑面，负责人随时可「停」。仍需负责人（不变）：方案／产品取舍拍板、验收步、外向发布、计费／升级、用户级配置安装、权威核心修改、诉求状态升级、谓词边界外关闭。

## 一次性触发（关联 [#287（A6）](https://github.com/Eridanus117/agent-control/issues/287)）

在跑归零或 Session 恢复时已为零，只触发一次前述候选评估；无候选过价值门即 `no_action`，不派发。评估不是自动派发，价值门、节流阀及负责人保留事项不变。

受监督 Task 的 spec 必须且只能有一行正整数 `Expected-Duration-Minutes: N`（覆盖启动、实现、验证与远端交付）；派发成功仅设一次 N 分钟截止，到点按 `tools/dispatch_deadlines/` 查询 Run；该 Dispatch 仍为 `dispatched` 且 `should_wake=true` 才处置，未到期即 `no_action`，缺失／非法声明报合同缺口。无在途不设，恢复时主动查一次；仅作 session 内兜底，不建设轮询、Hook、Webhook、常驻调度器或离线唤醒（关联 [#113（巡检定位面）](https://github.com/Eridanus117/agent-control/issues/113)）。

## 在线续接与负责人事项

- 在线 Session 在完成、工具／环境失败或可复用纠偏处，自然发现直接对应明确、开放且已授权父 Issue 未满足成功条件的具体缺口时，加载 `github-collaboration:issue-workflow`；准入、限流、生命周期与远端操作归 Skill。没有可核验父级或授权时不自动启动，也不扫描队列找活。
- 新建一个 Session 与恢复一个已有但当前空闲的 Session 是等价入口：重读入口、远端 Issue／Project 与必要的 `work/current.md`；不得沿用旧聊天记忆、草稿、角色、身份、授权或所有权。
- 需要负责人决定时，把背景、一个问题、推荐、少量替代、收益／代价与所需回复合并写回 Issue；Project 只作观察面，状态维护路由到 `github-collaboration:operating-ledger-maintenance`。原 Agent 可退出，任意有合同和所有权的 Session 从远端消费回复。
- 直接进入原终端只用于实时纠偏、过程观察或工具故障逃生，不是默认审批入口。没有在线 Session 时如实缺少 L3 离线唤醒。

## 共享写入前置检查

在一个阶段首次修改 Agent 系统的共享工作目录／分支、当前任务、权威、用户级 Agent 配置、已安装 Skill／Plugin 或 Orca 状态前，先确认当前任务或有效协作派发是否给出明确写入所有权。已经明确且范围互不重叠时直接继续，不重复检查。

所有权不明，或发现其他活动 Session 可能写入重叠范围时，保持相关范围只读并加载可用的 `orchestrated-collaboration` Skill；加入已有协调、取得明确分区或改为单写者后再继续。Git worktree 只隔离工作目录中的文件，不自动授予上述任何一类写入权。Orca TUI 是观察面，`orca orchestration` 是执行事实与协调后端。

## 制度自清洁（关联 [#285（可搬运结果）](https://github.com/Eridanus117/agent-control/issues/285)）

- 多数轮次不写才正常；`no_action` 是一等结果，禁止另发说明评论。
- 清理按可逆性分层：错了只需重建／clone 且不丢交付者不套最严门；可能丢交付者仍套。
- 本入口单独不授权：
  - 调查、实施、委派；
  - 新建／更新 Issue、改状态；
  - 合并、关闭、外向发布；
  - 改权威核心、用户级配置、消费计费权益。
- 系统消息与回执须匹配对象、范围和证据；局部证据不得声称系统级损失，准确优先于响亮。
- 已证实错误的规则／路径连同专属兼容说明一起删，不加例外或 fallback。

## 问题求解治理

当 Agent 系统任务准备作出第一项实质路径选择，或出现问题含义不清、关键假设变化、范围／成本明显扩大、进展停滞、高成本或难回退行动、共享状态修改、长任务恢复／交接／验收时，加载可用的 `adaptive-problem-solving` Skill。先恢复原始问题和当前阶段，判断普通处理是否足够，再选择、组合、升级、降级或退出方法，并检查模型、推理强度、上下文、工具、环境与协作方式是否适合。

低风险、明确、容易回退的小步骤不触发；同一阶段没有新证据时不重复检查。方向未变时直接继续，只有改变方向、授权或需要负责人判断时才外显结果。关键节点检查只是完整问题求解治理的入口，不能替代问题界定、方法选择、成本控制和根据反馈换路。

## 父目标验收

Agent 系统 MVP、工作流替代或高价值多 PR 父任务在宣称完成、进入自然观察或关闭前，必须加载可用的 `adaptive-problem-solving` Skill，验收父目标贡献、能力回退、证据等级和负责人可见 ROI。未完成这些检查时，不得声称产品闭环完成。

入口只负责触发，详细检查按 Skill 执行。普通单 PR、低风险、容易回退的任务不因此强制增加产品级独立复核。

## 经营总账维护

当 Agent 系统任务出现值得跨 Session 保留的新诉求、重要候选、决定、计划／实验、交付、验收或证据变化，或者负责人要求查看、收件、整理或更新经营总账时，读取 `C:\Users\Morni\workspace\agent-control\authority\10-operating-ledger.md` 并加载可用的 `operating-ledger-maintenance` Skill。本条是对上述按需读取规则的明确路由，不依赖本次 `work/current.md` 重复列出该权威。由 Skill 判断退出、进入收件箱、更新正式事项或路由到交付工作流，分开维护执行状态、诉求状态和证据等级，并在写入后从远端复核。

与 Agent 系统经营无关的普通任务不触发。Project 是观察面，不是权威、授权或事件后端；维护完成不自动规划、派发、启动、合并或建设轮询／Webhook／调度器。

## 纠偏与自我改进

多轮讨论只增概念却不减关键未知、形成决定或可检验资产时应主动纠偏；获准探索在停止条件内除外。负责人指出目标、解释、优先级、授权或行为偏差，或同类错误复发时：停止受影响展开，按原问题、最近确认、被替代判断与授权重锚；方向结论与来源写协调快照，被替代判断、未知、无进展证据和因果写研发记忆。抽象循环或可跨任务复用的纠正加载 `self-improvement`，判断改入口／Skill 还是只留任务记录。

只冻结依赖被推翻假设、存在共享写入冲突或会改变产品决定的路径；有独立合同和所有权的安全工作继续。在授权内完成与原问题相称的改进后返回原任务；最小实验只验证关键未知，不把最小 diff 当产品交付，也不把自我改进扩张成元项目。

对于与 Agent 系统无关的任务，遵循用户本次请求和所在项目的指令，不强行套用 `agent-control`。
