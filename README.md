# Agent Control

本仓是 `agent-control` 的公共产品与政策仓：保存可公开复用的 Agent 系统原则、协议、知识和装配量具。它不保存个人当前工作状态，也不是 Plugin 仓或完整多 Agent 平台。

## 持久实现语言

本仓新增或实质修改的持久程序、CLI、自动化和验证脚本只使用 Go、Python、TypeScript 或 Rust；不把 PowerShell、Batch 或 Shell 沉淀为产品脚本。文档和配置不受影响，Windows 一次性命令仍可通过 shell 宿主执行。该规则是本仓贡献约束，不自动扩大到其他仓库或用户级配置。

## 迁移与历史边界

- 2026-08-15 从私有 `Eridanus117/agent-control` clean-slate 迁入的 Issue #1–#34 标记为 `迁移索引/待分诊`；它们默认不是当前授权或活动 backlog。
- 迁入事项只有补齐公开、自足的目标、范围、验收和当前授权后才能重新激活。旧仓评论与 PR 可以作历史来源，但公共规范不得以私有链接为理解前提。
- 旧仓保持私有；必要决定与证据先脱敏蒸馏，再机械 archive。当前落地工作见 [Issue #58](https://github.com/zaurakworks/agent-control/issues/58)。

## 开始工作

每个新的 Session 先读取 [`authority/00-map.md`](./authority/00-map.md)，再按本次请求分流：

1. **负责人明确激活一个公开、自足的 Issue**：重新读取该 Issue 当前正文与状态，只加载它明确链接的政策和证据；授权、写入所有权和验收均以远端当前内容为准。
2. **Issue 带 `迁移索引/待分诊` 标签**：默认只允许分诊和只读核验；不能从旧正文、私有评论或开放状态恢复实施授权。
3. **没有明确 Issue**：保持自由对话或当前请求的最小范围。负责人要求选择工作时，可以查看公开 Issue 列表并提出一个有界候选，但不能自行激活、派发或恢复迁入事项。

Session 的职责由负责人当前明确指令、公开自足的 Issue 合同和写入所有权共同决定，不由 Provider、终端名称或固定身份决定。Issue 不能覆盖更高层权限边界；冲突时保持相关范围只读并升级。

明确 Issue 的工作直接按远端当前合同实施、验证并通过 PR 或自足证据评论交付；不把源码存在、Issue 开放或历史安装当作额外行为、权限或流程来源。GitHub 授权、PR 合并和 Issue 正文重写的安全边界见项目入口。

### 扩大工作范围

公共规则见 [`entrypoints/agent-system.md` 的同名章节](./entrypoints/agent-system.md#扩大工作范围)。

## 在线续接与负责人事项

公共规则见 [`entrypoints/agent-system.md` 的同名章节](./entrypoints/agent-system.md#在线续接与负责人事项)。

## 运行与观察

- 本仓不提供仓内“当前运行状态”文件；当前工作、授权和验收存在于公开 Issue／PR，过程执行态存在于实际运行后端。
- [`tools/worker_snapshot/`](./tools/worker_snapshot/)、[`tools/ops-metrics/`](./tools/ops-metrics/) 和 [`tools/ops-console/`](./tools/ops-console/) 是可选观察工具；生成的 `current.md` 只是带新鲜度边界的本机快照，不是公共产品状态、授权源或等待清单。
- 迁移前的私有 Project 和运营台只作历史证据，不是本公共仓的当前入口。

## 文件职责

- `authority/`：保存版本化产品政策；正文必须自足，私有历史链接只能作可选来源。迁移内容在公开 Issue 重新确认前不产生实施授权；
- `knowledge/`：通过价值门与可信门的当前公共知识包与检索卡，覆盖 Windows 运维（长路径、文件锁）、GitHub 引用与 PowerShell 多行正文等已验证陷阱；入口表见 [`knowledge/README.md`](./knowledge/README.md)；
- `work/records/`：保存非权威、可追溯的研发过程；默认不读取，只在当前任务明确链接时按需读取；
- `work/history/`：首次归档已完成任务时再创建；历史记录不是当前指令；
- `work/` 根目录下的其余 Markdown（`configuration-inventory.md`、`current-monitoring-directive.md`、`knowledge-mvp-proposal.md`、`knowledge-mvp-boundary-candidate.md`、`knowledge-mvp-decision.md`、`permission-strategy-research.md`）与 `work/knowledge-trial/`：具名的调研、清单与候选，非权威；默认不读取，只在当前任务明确链接时按需读取。新增同类内容优先进 `work/records/<日期>-<主题>/`，不再往根目录堆放；已退出当前工作面的旧候选移入 `work/history/` 并明确标出被替代入口。
- `entrypoints/agent-system.md`：本仓项目级 Agent 行为入口；不作为用户级全局提示词安装源；
- `AGENTS.md`：Codex 的最小仓库入口，只保留仓库增量并回指 `entrypoints/agent-system.md`；公共系统规则的唯一版本化正文由后者承载；
- `CLAUDE.md`：Claude Code 导入同一份入口规则，并在本仓内加载 `entrypoints/agent-system.md`；用户级入口只保留与任务无关的锚点，本仓正文不进全局常驻面；
- `.claude/skills/`：本仓的工作阶段 Skill（`stage`：观察／提议／执行／判定的完成判据与产出形状），供本仓内支持该发现约定的客户端直接使用；
- [`tools/profile/`](./tools/profile/)：Codex／Qoder／OMP 项目能力面的唯一声明、content+mode lock、渲染、隔离启动和生效态核验入口；profile 必须显式选择，运行根与无 secret 收据落在仓库之外，边界见 [`tools/profile/README.md`](./tools/profile/README.md)。

私有旧仓、迁移索引、历史记录、分析和实验只提供来源；公共产品政策必须在本仓自足表达，历史材料不能反向产生当前授权。

## 方案审阅

准备请负责人确认一项会改变产品边界、架构、长期依赖或显著投入的方案时，不得只在聊天、本地文件、当前任务或研发记录中分散表达。默认先在当前 GitHub 仓建立一个可由负责人直接访问的方案 Issue，至少包含：

- 原始问题和预期结果；
- 推荐方案和完整运行过程；
- 可信替代方案与选择理由；
- 范围、明确不做事项、成本、风险、可逆性和升级条件；
- 实施与验收方式；
- 负责人需要确认的少量决定。

纯方案默认使用公开、自足的 GitHub Issue；需要审阅已经形成的仓库文件差异时才使用 Draft PR。方案获得确认后，只把已确认结论进入产品政策；被拒绝或替代的方案作为 Issue 或研发记录保留，不继续冒充当前方向。GitHub 暂时不可用时，本地草稿必须明确标为临时载体。

## 改变权威

分析、提案和实验结果在负责人明确确认前都不是权威。改变 `authority/` 时，需要同时记录被替代的内容和新的确认结果，不能静默修改方向。
