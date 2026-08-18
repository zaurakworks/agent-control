## Why

`zaurakworks` 当前把同一 Agent 系统拆在 `agent-control`、`agent-contracts`、`agent-plugins`、`agent-assembly` 与 `agent-state-lab` 五个仓中，已经出现 CAP 实现分叉、远端产品目录与本地 checkout 库存不一致、相邻路径依赖和职责边界难以发现的问题。负责人已决定以现有 `agent-control` 为目标仓并将其改名为 `agent-system`，把日常产品开发收敛为一个公开活跃仓，同时保留私有研究证据的保密边界和旧仓历史。

## What Changes

- **BREAKING**：将现有 `zaurakworks/agent-control` 重命名为 `zaurakworks/agent-system`，并把它作为唯一活跃产品仓、Issue/PR 入口和本地 canonical checkout；调用方、文档、remote 与 worktree 路径迁移到新名称，不依赖 GitHub 旧 URL redirect 作为长期接口。
- **BREAKING**：把 `agent-contracts`、`agent-plugins`、`agent-assembly` 的当前产品资产和验证入口迁入 `agent-system`，完成全部调用方、Marketplace、profile、文档和 CI 的 clean cutover 后将三个源仓设为只读 archive；不继续双写或保留兼容实现。
- 把 `agent-control` 与 `agent-assembly` 中已经分叉的 CAP 实现收敛为一个正式 Python package/CLI：通用 profile、render、lock、verify 与客户端适配归统一实现，项目 profile、prompt 和 capability 继续由显式 `.cap` 声明决定。
- 将合同 Schema、样例、捕获/回执工具与测试迁入独立 `contracts/` 边界；将可安装 Plugin、Skill、双端 Marketplace 与发布验证迁入独立 `plugins/` 边界；将当前 profile 组合迁入根 `.cap/` 声明面。
- 从 private `agent-state-lab` 只毕业经负责人确认、完成脱敏且为公开产品所必需的最小结论、测试或 fixture；原始实验、审计 JSON、私有路径、Session 记录、未采纳候选和历史概念账本不进入 public monorepo。完成结论毕业和入口改写后把 `agent-state-lab` 保留为 private archive，而不是活跃控制面。
- 为每个源仓记录 remote/default branch/head、开放 Issue/PR、dirty/untracked、本地 checkout、registered worktree、local-only commit、迁移路径、验证入口和回滚 ref；未完成基线和未保全资产时禁止迁移或归档。
- 本地物理入口收敛为 `~/work/agent-system` 与 `~/work/worktrees/agent-system/<slug>`；旧 clone、主仓和 worktree 只按 Git 生命周期与 `_org` 迁移计划处理，不直接移动或删除受管 worktree。
- 迁移保持现有 `general`、`assembly-helper`、`work` profile 的闭包和声明态语义，保持 Plugin 可安装接口、合同机械校验和公开政策内容；仓库存在、lock/CI 通过与真实客户端生效态继续分层报告。
- 客户端在当前实施环境不可用时，允许在已保存静态、配置态和可用客户端基线后开始内容迁移；缺失客户端的实际生效态必须保持 `unknown`，并继续硬阻塞对应 Plugin/source archive，直到在真实环境补证。

非目标：

- 不新建第六个协调仓或第二套仓库目录。
- 不把 private `agent-state-lab` 原始证据公开，也不把实验候选自动升级为产品权威。
- 不恢复已退役 Plugin、Skill、工作流、用户级 Hook 或 ambient 能力。
- 不删除 GitHub 源仓、Issue/PR 历史、dirty clone、local-only commit 或未跟踪资产；源仓最终只 archive。
- 不因物理单仓而合并政策、合同、Plugin、assembly 与研究证据的逻辑权威边界。

## Capabilities

### New Capabilities
- `agent-system-monorepo`: 定义唯一公开活跃仓、五仓资产迁移与逻辑边界、private 研究证据毕业、源仓 archive、本地 canonical 路径和端到端验证要求。

### Modified Capabilities

无。现有 profile、Skill 和运行时能力的需求语义保持不变；本 change 改变其仓库承载、工具实现和发布入口。

## Impact

- 远端仓库：`zaurakworks/agent-control`（目标并改名）、`agent-contracts`、`agent-plugins`、`agent-assembly`、private `agent-state-lab`。
- 本地仓库与 worktree：当前 `~/work/tools/agent-assembly`、`~/work/tools/agent-control`、旧 `~/work/agent-control`、`~/work/agent-plugins`、`~/workspace/agent-assembly`、`~/workspace/agent-control`、相关 registered worktrees，以及 `_org` inventory/move plans。
- 受影响实现：两份 CAP CLI、`tools/profile/`、合同 Schema/CLI、Plugin/Skill/Marketplace、`.cap` manifest/profile/prompt/capabilities、CI、测试、README 和维护指南。
- 兼容性：GitHub rename redirect 只用于迁移；canonical remote、本地路径、文档和自动化必须 clean cutover。公开 Plugin 名称/版本、合同格式和 profile inventory 若无独立规格变更则保持兼容。
- 回滚边界：每个源仓迁移前固定 remote head 和回滚 ref；目标仓在全部源验证和集成验证通过前不 archive 源仓。失败时回退目标迁移提交并恢复原 canonical 入口，不删除源历史或私有证据。
- 基线证据：`agent-state-lab` README/FINDINGS 明确其非权威研究边界和 `agent-contracts` 候选地位；`agent-state-lab#5` 记录旧仓蒸馏/冻结决定；`agent-control#67` 确认 profile engine 与 assembly 声明的职责关系；当前 `agent-control/tools/cap.py` 与 `agent-assembly/tools/cap.py` 已显著分叉；当前 assembly 单元测试 28/28、13 个 Skill 元数据检查通过，但 worktree 默认 `profile.py` 定位失败。
- 控制设计的一手来源：五个 `zaurakworks` 仓的当前 README、`agent-state-lab/FINDINGS.md`、`agent-state-lab#5` 负责人裁决、`agent-control#67` 已确认 profile 分层方案，以及负责人本次明确的单公开活跃仓、允许合并和接受 `agent-system` 改名决定。
