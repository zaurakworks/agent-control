## Why

CAP 已完成 v3 源模型和 OMP 主路径；`uv run cap show assembly-helper` 能解析 `project-defaults + assembly-helper`，声明态与 lock 配置态正常。本变更不再迁移或重新设计 CAP，而是把现有“辅助装配”配置重新装配为真正的执行角色。

当前 profile、prompt 与总 Skill 仍以维护助手为中心：名称弱化执行职责，能力闭包沿用历史结果而非从目标重选，也没有把“目标澄清→装配源文件→lock/binding/render→行为证据”作为一个端到端结果。负责人已确认 clean cutover 到 `agent-assembler`，并要求 `grilling` 常驻。

`grilling` 的唯一正文位于 `plugins/grilling/skills/grilling`。现有 `.cap` store 只接受 `.cap/capabilities/skills/<id>`，而 v3 `external_imports` 只批准 machine inventory 资产，不负责把 Skill staged 进 render。复制正文会形成第二真源，因此需要一个窄的项目 Skill source-path 声明。

## What Changes

- **BREAKING** 将 `assembly-helper` clean cutover 重命名为 `agent-assembler`；更新所有现有调用方、CLI 标签、测试、文档和 binding 名称，不保留旧 id 或兼容别名。
- 从零重写 `agent-assembler` 的 profile、常驻 prompt 与总 Skill，使其交付可审查、可运行、可回滚的 CAP Agent 装配。
- 重新确认完整能力闭包：总装配、`grilling`、prompt 设计、Skill 设计、能力生命周期、closure、行为评测和变更包；继续继承项目 OpenSpec defaults；MCP、Hook、Plugin 为空。
- 新增可选 `.cap/skill-imports.toml`：只允许项目根内、非 symlink、被 lock 覆盖的 Skill source path。`agent-assembler` 直接 render Plugin 中的唯一 `grilling` 正文。
- 修正 Skill origin，使 project-defaults 与 imported Skills 都从已验证最终路径进入 render。
- lock 直接覆盖 project-defaults、runtime policy、Skill import 声明与 import 源树。
- 保持 CAP v3 machine-context、asset inventory、runtime policy、OMP generation、CLI 交互模型和其他 profile 行为不变。

## Non-goals

- 不增加动态 role 发现、兼容层、旧 id alias 或第二个装配 role。
- 不接管认证、token、provider 账号、Git/SSH、语言工具链或 ambient 用户配置。
- 不让 `grilling` 绕过明示同意、退出或实施前确认合同。
- 不在本次实现 Codex 或 Claude runtime adapter，也不声称跨客户端实际生效。
- 不复制 `grilling` 正文到 `.cap`。

## Capabilities

### New Capabilities

- `v3-assembly-executor`：定义装配者从目标合同到配置、派生状态和分层证据的完整行为。
- `project-skill-imports`：定义仓内唯一 Skill 正文的显式来源、路径安全、闭包、lock 和 render 合同。

### Modified Capabilities

- `research-first-assembly`：从外部调研路由扩展为装配执行中的事实／决定边界。
- `agent-behavior-evaluation`：增加同意门、装配执行、拒绝和证据分层的正反场景。

## Impact

- CAP/profile 实现：只修改项目 Skill source-path、最终 Skill origin 和完整 lock input。
- 装配声明：manifest、project-defaults、profile、prompt、总 Skill、closure Skill 和 lock。
- clean cutover 调用方：CAP role 常量／标签、OMP 旧状态选择、命令示例、测试和文档。
- 验证：Skill import、project-defaults render、lock drift、重命名后 TUI／show／render／OMP smoke。

## Baseline Evidence

- 2026-08-20：`uv run cap show assembly-helper` 通过，chain 为 `project-defaults -> assembly-helper`，证明当前产品已是 v3；本变更不以“迁移到 v3”为理由。
- `RUNNABLE_PROFILES`、CLI 标签、OMP migration 和文档仍引用 `assembly-helper`，clean cutover 必须迁移全部调用方。
- `.cap` 没有可指向 `plugins/grilling/skills/grilling` 的项目 Skill 来源声明；external import 不会生成 render Skill 文件。
- renderer 目前从固定根二次拼接 Skill 路径，不能表达仓内 source path，也会让 project-defaults origin 指向错误位置。
- `$HOME/.agent-system-state` 当前不存在，因此修改前没有可比较的 live binding／OMP 行为基线；不得制造改善结论。

## Rollback Boundary

恢复旧 id、profile、prompt、总 Skill、manifest 和调用方；移除 Skill source-path 声明与实现；刷新 lock 与 bindings。Plugin 中的 `grilling` 正文始终保持唯一，不因实施或回滚被复制。认证和 Session 不属于本变更。
