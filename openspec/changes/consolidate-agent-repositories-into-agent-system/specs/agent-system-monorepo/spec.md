## Purpose

定义 `zaurakworks` Agent 系统从五个活跃仓收敛为一个公开活跃 `agent-system` monorepo 时，仓库身份、逻辑能力边界、private 研究证据保护、兼容迁移、源仓归档、本地 canonical 路径和分层验证必须满足的可观察合同。

## ADDED Requirements

### Requirement: 唯一公开活跃仓
系统 SHALL 通过重命名现有 `zaurakworks/agent-control` 得到 `zaurakworks/agent-system`，并在迁移完成后只把该仓作为 Agent 产品代码、公开政策、合同、Plugin、profile 装配和新 Issue/PR 的 canonical 入口；系统 SHALL NOT 为收敛新建第六个协调仓。

#### Scenario: 现有目标仓完成改名
- **WHEN** 仓库身份切换完成
- **THEN** `zaurakworks/agent-system` SHALL 继承原 `agent-control` 仓身份和历史，所有当前文档、remote、自动化和本地 canonical 路径 SHALL 指向新名称

#### Scenario: 旧 URL 被继续作为长期入口
- **WHEN** 调用方只依赖 `zaurakworks/agent-control` redirect 或继续把任一源仓作为新工作入口
- **THEN** 迁移 SHALL 视为未完成，源仓 SHALL NOT 进入 archive

### Requirement: 逻辑能力边界在单仓内保持显式
`agent-system` SHALL 为公共政策与知识、合同协议、可安装 Plugin、profile 装配和通用 CAP/profile 工具保留唯一且可发现的逻辑承载位置；同一规范正文、工具实现或发布清单 SHALL NOT 在两个边界中并行维护。

#### Scenario: 源资产完成 clean cutover
- **WHEN** `agent-contracts`、`agent-plugins` 和 `agent-assembly` 的当前产品资产迁入目标仓
- **THEN** 合同 Schema/工具/样例、Plugin/Skill/Marketplace、`.cap` profile/prompt/capability、对应测试和文档 SHALL 各自具有一个目标位置，全部调用方 SHALL 指向该位置

#### Scenario: 迁移形成第二实现
- **WHEN** 目标仓保留迁入实现，同时源路径、复制文件或兼容 shim 仍被当前调用方使用
- **THEN** 迁移 SHALL 失败并保持源仓可回滚状态，不得报告单仓收敛完成

### Requirement: CAP 只有一个正式实现
系统 SHALL 提供一个正式 CAP Python package/CLI，统一承载可复用的 profile、render、lock、verify、客户端适配和命令入口；项目 profile、prompt、capability 与项目专属策略 SHALL 继续由显式 `.cap` 声明和具名策略模块决定。

#### Scenario: 现有 CAP 行为等价迁移
- **WHEN** 原 `agent-control` 与 `agent-assembly` CAP 路径完成收敛
- **THEN** `general`、`assembly-helper`、`work` 的公共 inventory、三客户端 portable render hash、既有 CLI 合同和安全门 SHALL 与批准基线等价，除非另有独立规格明确改变

#### Scenario: 发现重复 CAP 入口
- **WHEN** 仓内或 archived source 之外仍存在两个可运行、可被文档调用的 CAP 实现
- **THEN** verify SHALL 失败并报告重复入口，不得用弃用别名或 silent fallback 掩盖

### Requirement: Private 研究证据不得因合仓公开
系统 SHALL 只把 `agent-state-lab` 中经负责人确认、完成脱敏并为公开产品行为所必需的最小结论、测试或 fixture 毕业到 `agent-system`；原始实验、审计载荷、私有路径、Session 记录、未采纳候选和历史概念账本 SHALL 保持 private，且 SHALL NOT 成为公开产品运行依赖。

#### Scenario: 已确认结论毕业
- **WHEN** 一项 state-lab 结论具有负责人决定、公开产品拥有者、脱敏结果和可验证消费方
- **THEN** 目标仓 SHALL 保存自足的最小产品合同及来源标识，且无需读取 private 仓即可理解和验证

#### Scenario: 候选或私有证据被选中迁移
- **WHEN** 资产缺少负责人确认、无法证明已脱敏、包含私有运行信息或仅记录实验历史
- **THEN** 迁移 SHALL 拒绝该资产并保持其在 private state-lab 中，不得通过改名、摘要或生成物绕过

### Requirement: 迁移前必须建立可回滚基线
每个 source 和 target SHALL 在首次写入前记录 remote、default branch、remote head、visibility、开放 Issue/PR、本地 checkout/head、dirty/untracked、registered worktree、local-only commit、验证入口、迁移路径和回滚 ref；任何 source 身份、资产、提交或工作树的未知、冲突或未保全状态 SHALL 阻止相应迁移和归档。真实客户端在当前实施环境不可用时，其实际生效态 MAY 保持 `unknown` 并允许内容迁移继续，但 SHALL 阻止对应 Plugin/source archive，直到在该客户端真实环境补证。

#### Scenario: 干净且完整的迁移基线
- **WHEN** source/target 身份、提交、工作树、worktree、未跟踪资产和验证入口均已记录且无冲突
- **THEN** 迁移 SHALL 绑定这些不可变输入，并能在目标验证失败时恢复原 canonical 入口

#### Scenario: 存在未跟踪资产或 local-only commit
- **WHEN** 任一待迁或待归档 checkout 存在未分类 untracked、dirty、local-only commit 或未判定 worktree
- **THEN** 该对象 SHALL 保持原位并阻止 archive，直到资产被迁移、明确保留或由负责人单独处置

#### Scenario: 真实客户端当前不可用
- **WHEN** source 的静态、标准合规、配置态和可用客户端基线已经保存，但一个目标客户端在当前实施环境不存在或无法安全取得认证
- **THEN** 内容迁移 MAY 继续，缺失客户端的实际生效态 SHALL 明确报告为 `unknown`，对应 Plugin/source archive SHALL 保持阻塞

### Requirement: 源仓只在端到端验证后归档
`agent-contracts`、`agent-plugins`、`agent-assembly` SHALL 在目标仓完成源验证、集成验证、调用方 clean cutover、入口重定向和回滚演练后转为只读 archive；private `agent-state-lab` SHALL 在已确认结论毕业和当前工作入口关闭后保留为 private archive。系统 SHALL 保留源仓 Issue/PR 和 Git 历史，不得用删除代替归档。

#### Scenario: 全部归档门通过
- **WHEN** 目标仓对每个 source 的资产清单、原验证、集成验证、公开入口、历史来源和回滚 ref 均核验通过
- **THEN** source README SHALL 指向 `agent-system` 的 successor 位置，source SHALL archive 且不再接收新工作

#### Scenario: 目标验证尚未完成
- **WHEN** 任一 source 验证、真实运行探针、调用方迁移或回滚证明缺失
- **THEN** 对应 source SHALL 保持未归档和可回滚，文件存在、CI 通过或 GitHub redirect SHALL NOT 替代缺失证据

### Requirement: 本地物理入口唯一且符合 worktree 生命周期
完成迁移后，本地 canonical 主仓 SHALL 位于 `~/work/agent-system`，新任务 worktree SHALL 位于 `~/work/worktrees/agent-system/<slug>`；旧 clone 和 worktree SHALL 通过 `_org` inventory/move plan 与 Git worktree API 分类处理，不得直接移动或删除 registered worktree。

#### Scenario: 新任务进入 Agent 系统
- **WHEN** 创建新的可写 Agent 系统任务 worktree
- **THEN** 主仓 SHALL 是 `~/work/agent-system`，worktree SHALL 使用 `~/work/worktrees/agent-system/<slug>`，且任务无需搜索其他 clone 选择权威

#### Scenario: 旧 common dir 仍承载活动 worktree
- **WHEN** 旧主仓仍是任一 registered worktree 的 common Git dir
- **THEN** 物理迁移 SHALL 停止，直到通过主仓 Git worktree 生命周期完成保全和重新绑定；不得直接 `mv` 或 `rm` 该目录

### Requirement: 分层验证不得相互替代
迁移验收 SHALL 分别证明声明态闭包、Skill/Plugin/合同标准合规、配置态 lock/render/package/Marketplace 一致性和实际客户端生效态；任一较低层通过 SHALL NOT 被报告为较高层生效证据。

#### Scenario: 声明与配置保持等价
- **WHEN** `.cap`、合同、Plugin 和 CAP 工具迁入目标仓
- **THEN** profile inventory 与 render、合同正负样例、Plugin 双端 manifest/版本/符合性和单元测试 SHALL 对照源基线通过

#### Scenario: 仅 CI 与 lock 通过
- **WHEN** 目标仓静态检查、单元测试和 lock 均通过，但真实 Codex、Qoder、OMP 或 Plugin 安装/调用探针尚未执行
- **THEN** 系统 SHALL 报告声明态和配置态结果，实际生效态 SHALL 保持 `unknown`，源仓 SHALL NOT 因此提前归档
