---
name: assembly-helper
description: 创建、审查和修改项目内 Agent 装配，包括 prompt、Skills、能力闭包、调研证据和验证。用于 Agent profile 的设计或维护，不用于普通任务执行。
---

# assembly-helper

## 流程
1. 恢复目标 Agent 合同：稳定 id、目标、非目标、触发条件、输入、输出、允许和禁止的能力，以及验收证据。
2. 建立本地基线。当决定依赖外部标准、客户端行为、当前版本、安全属性、兼容性结论或候选资产时，先用 `capability-lifecycle` 调研一手来源。
3. 常驻指令使用 `agent-prompt-design`，条件工作流使用 `agent-skill-design`。只加载当前决定需要的 Skill。
4. 所有运行时能力必须位于项目内，并由选定 profile 显式引用。拒绝来自用户级配置、模板、ambient MCP、Hook、Plugin、Skill 或 marketplace 的隐藏继承。
5. 对声称改变行为的修改，使用 `agent-behavior-evaluation` 记录可比较基线、正反平衡场景和观察结果。
6. 使用 `capability-profile-closure` 分别报告标准合规、声明态、配置态和实际运行证据。
7. 新 profile、可观察行为变化、跨客户端变化、风险迁移或未来维护者必须审计的变化，使用 `spec-change-pack`。
8. 交付准确文件路径、控制决定的调研来源、验证命令和结果、行为证据以及剩余未知。

## 配置维护路由
当任务是修改 Agent 系统自身配置时，assembly-helper 负责从文件恢复源头并直接完成装配，不通过额外的 CAP 配置菜单转译任务。可按任务需要修改当前项目或相关运行资产，不预设目录 allowlist；先识别源文件、派生文件和外部基座，再执行修改。

重点路径：
- `.cap/profiles/*.toml`：profile 继承和能力操作；
- `.cap/prompts/*.md`：profile prompt；
- `.cap/capabilities/`：Skill、MCP、Hook、Plugin 等能力源；
- `.cap/lock.json`、base manifest、pin、bindings：锁定、绑定和验证状态。

修改后从源文件重新生成适用的 lock、binding 或 render，并执行 `cap verify` 或更窄的相称检查。交付必须区分源文件修改、派生状态更新和实际客户端生效证据。

## 完成条件
只有当 manifest、profile、prompt 和引用能力形成项目内闭包，每个 Skill 通过元数据验证，交付准确标明已检查的证据层，并且所有行为改善结论都有可比较观察证据时，装配才算完成。
