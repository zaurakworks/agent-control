# Agent Control

这个仓库保存当前权威和当前工作的控制状态。它是首个 MVP，不是完整的知识库、多 Agent 平台或 Plugin 仓。

## 机器级持久实现语言

凡这台电脑上的 Codex 或 Claude Code 参与维护持久资产，语言规则都对所有仓库、Provider、Session 和 worktree 生效，不因当前仓库、仓库入口或 Agent 系统任务的触发条件而缩窄：持久程序、CLI、自动化和验证脚本只使用 Go、Python、TypeScript 或 Rust，不把 PowerShell、Batch 或 Shell 沉淀成产品脚本。文档和配置不受影响，Windows 一次性命令仍可通过 shell 宿主执行；语言选择按长期可靠性与维护投入产出判断，不以当前是否已安装为淘汰依据。

该规则不授权批量重写范围外既有资产；既有资产在后续实际触及或替换时遵守，确有不可避免的上游或引导例外时需要明确证据和负责人决定。

## 开始工作

每个新的 Session 先读取 [`authority/00-map.md`](./authority/00-map.md)，再按本次任务是否带有明确 GitHub Issue 分流：

1. **有明确 Issue**：重新读取远端 Issue 当前正文与状态，把它作为本次持久任务合同；只读取该合同链接的权威。最新授权变化与共享写入所有权同样以远端 Issue 为准，[`work/current.md`](./work/current.md) 只在需要定位主线入口、各来源 observedAt 水位或未解决冲突标志时读取；
2. **没有明确 Issue，但负责人要求选择下一项工作**：按恢复指针定位主线入口，读取 [`authority/10-operating-ledger.md`](./authority/10-operating-ledger.md) 和经营总账远端观察面，从未满足／部分满足诉求回到 `adaptive-problem-solving`，只形成或选择一个有界 Issue，不把空的“就绪”队列解释为没有工作；
3. **没有明确 Issue 的其他任务**：读取恢复指针，按它指向的活动 Issue 与运行面判断加入现有工作、保持只读或请求决定。

Session 的职责由当前 Issue 合同和写入所有权决定，不由 Provider、终端名称或固定的“协调者／Worker”身份决定。Issue 保存持久合同，但不能覆盖当前权威、负责人更新的明确指令或有效协作派发；发生冲突时保持相关范围只读并升级。

父 Issue 与叶子 Issue 都加载 `github-collaboration:issue-workflow`：父 Issue 在授权内协调自己的子树，叶子 Issue 完成端到端交付。状态机、风险门、合同压缩与父级回收只保存在 Skill 内；入口不复制它们。退出时把结果写回远端 Issue／父级并返回当前任务，不保留永久协调者身份。没有活动授权时，不要自行恢复已暂停、已完成或尚未批准的事项。

### 持有 Issue 时扩大并行波次

公共规则见 [`entrypoints/agent-system.md` 的同名章节](./entrypoints/agent-system.md#持有-issue-时扩大并行波次)。

## 在线续接与负责人事项

公共规则见 [`entrypoints/agent-system.md` 的同名章节](./entrypoints/agent-system.md#在线续接与负责人事项)。

## 运营入口

- [关联 #237（运营台：Agent 系统观察入口）](https://github.com/Eridanus117/agent-control/issues/237)：手机书签与最多 10 行的最新卡片；正文原地覆盖，评论只承载高注意力事件；
- [`tools/worker_snapshot/current.md`](./tools/worker_snapshot/current.md)：最近一次成功生成的 Worker 点时观察明细；
- [`tools/ops-metrics/current.md`](./tools/ops-metrics/current.md)：最近一次成功生成的运营日报明细；
- [`tools/ops-console/`](./tools/ops-console/)：手动或协调者 tick 调用的一次性卡片生成器。

这些入口是关联 [#236（运营台承载实施）](https://github.com/Eridanus117/agent-control/issues/236)批准的观察面，不是权威、授权源、等待清单或生命周期事实；数据超过卡片新鲜窗后必须重新生成，吞吐不等于价值。

## 文件职责

- `authority/`：只保存已经确认、当前有效的内容；
- `knowledge/`：通过价值门与可信门的当前公共知识包与检索卡，覆盖 Windows 运维（长路径、文件锁）、Orca 派发与收口验活、GitHub 引用与 PowerShell 多行正文等已验证陷阱；入口表见 [`knowledge/README.md`](./knowledge/README.md)；
- `work/current.md`：恢复指针壳，只保存主线入口、各来源 observedAt 水位和未解决冲突标志；它不是状态权威，目标、授权、决定与验收一律以 GitHub Issue／PR 为准；
- `work/records/`：保存非权威、可追溯的研发过程；默认不读取，只在当前任务明确链接时按需读取；
- `work/history/`：首次归档已完成任务时再创建；历史记录不是当前指令；
- `work/` 根目录下的其余 Markdown（`configuration-inventory.md`、`current-monitoring-directive.md`、`knowledge-mvp-proposal.md`、`knowledge-mvp-boundary-candidate.md`、`knowledge-mvp-decision.md`、`permission-strategy-research.md`）与 `work/knowledge-trial/`：具名的调研、清单与候选，非权威；默认不读取，只在当前任务明确链接时按需读取。新增同类内容优先进 `work/records/<日期>-<主题>/`，不再往根目录堆放；已退出当前工作面的旧候选移入 `work/history/` 并明确标出被替代入口。
- `entrypoints/agent-system.md`：Windows 用户级 Agent 系统提示词的版本化来源；实际入口副本不是新的权威来源；
- `AGENTS.md`：Codex 的最小仓库入口，只保留仓库增量并回指 `entrypoints/agent-system.md`；公共系统规则的唯一版本化正文由后者承载；
- `CLAUDE.md`：Claude Code 导入同一份入口规则，并在本仓内加载 `entrypoints/agent-system.md`；用户级入口只保留与任务无关的锚点，本仓正文不进全局常驻面；
- `.claude/skills/`：本仓的工作阶段 Skill（`stage`：观察／提议／执行／判定的完成判据与产出形状）。它既是 Claude Code 在本仓内的直接可用资产，也是 profile 物化到 `CLAUDE_CONFIG_DIR` 与 `CODEX_HOME` 时的**唯一来源**；两个 Provider 共用同一份，不各存一份；
- [`tools/profile/`](./tools/profile/)：把一份声明的 agent 状态物化成可运行的配置 home，跑完再比对实际生效态，用于锁定某个状态并核验它没漂。声明（`manifest.toml`）进版本控制，物化产物和凭据落在仓库之外。两个量具：`probe` 秒级查配置面，`run` 跑一次 agent 查生效面，两者会在两个方向上不一致，差值是信号。边界与已验证的不可控项见 [`tools/profile/README.md`](./tools/profile/README.md)。

旧仓、旧 Issue、旧实现、历史记录、分析和实验都不能反向定义当前权威。

## 何时更新恢复指针

`work/current.md` 已按 D2 降级为指针壳，只在以下事件发生时更新：

1. 主线入口变化：当前活动 Issue 或协调运行面改变；
2. 某个来源被重新观察，需要推进它的 observedAt 水位；
3. 出现或消除一个未解决的跨源冲突。

目标、授权、范围、停止条件、决定、验收、阻塞与下一步都写入对应的 GitHub Issue／PR，不回写本文件；过程执行态按需读取运行面，不投影到仓内。不要记录普通读取、搜索、格式化和没有改变方向的工具调用，也不要用完整聊天记录代替持久合同。

## 方案审阅

准备请负责人确认一项会改变产品边界、架构、长期依赖或显著投入的方案时，不得只在聊天、本地文件、当前任务或研发记录中分散表达。默认先在当前 GitHub 仓建立一个可由负责人直接访问的方案 Issue，至少包含：

- 原始问题和预期结果；
- 推荐方案和完整运行过程；
- 可信替代方案与选择理由；
- 范围、明确不做事项、成本、风险、可逆性和升级条件；
- 实施与验收方式；
- 负责人需要确认的少量决定。

`work/current.md` 只链接唯一的 GitHub 方案资产，不复制完整正文。需要审阅已经形成的仓库文件差异时才使用 Draft PR；不要为了审阅纯方案而先制造文件提交。方案获得确认后，只把已确认结论进入权威；被拒绝或替代的方案作为 Issue 或研发记录保留，不继续冒充当前方向。GitHub 暂时不可用时，必须明确把本地草稿标为临时载体，不能把它当成负责人默认需要打开的审阅面。

## 改变权威

分析、提案和实验结果在负责人明确确认前都不是权威。改变 `authority/` 时，需要同时记录被替代的内容和新的确认结果，不能静默修改方向。
