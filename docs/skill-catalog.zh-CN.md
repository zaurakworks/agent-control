# Skill 目录

运行时 Skill 默认位于 `.cap/capabilities/skills/<name>/SKILL.md`；manifest 也可声明项目根内、非 symlink、由 lock 覆盖的唯一 Skill source。当前 `grilling` 直接使用 `plugins/grilling/skills/grilling/SKILL.md`，不在 `.cap` 复制。快速迭代阶段，中文 `SKILL.md` 同时是唯一执行合同和唯一全文维护源；本目录只提供导航和摘要。

## 阅读顺序

1. 创建、重装、审查或 clean cutover Agent 时，先读 [`agent-assembler`](../.cap/capabilities/skills/agent-assembler/SKILL.md)。
2. 只有负责人直接要求 grilling／盘问／压力测试或明确接受建议时，读 [`grilling`](../plugins/grilling/skills/grilling/SKILL.md)。
3. 设计常驻提示词时，读 [`agent-prompt-design`](../.cap/capabilities/skills/agent-prompt-design/SKILL.md)。
4. 设计条件性多步骤能力时，读 [`agent-skill-design`](../.cap/capabilities/skills/agent-skill-design/SKILL.md)。
5. 修改 `.cap` 声明或 lock 时，读 [`capability-profile-closure`](../.cap/capabilities/skills/capability-profile-closure/SKILL.md)。
6. 调研、引入、升级或退役外部能力时，读 [`capability-lifecycle`](../.cap/capabilities/skills/capability-lifecycle/SKILL.md)。
7. 需要建立基线、证明改善或检查回归时，读 [`agent-behavior-evaluation`](../.cap/capabilities/skills/agent-behavior-evaluation/SKILL.md)。
8. 变更较大、需要 durable proposal/delta/design/tasks 时，读 [`spec-change-pack`](../.cap/capabilities/skills/spec-change-pack/SKILL.md)。
9. 进入具体 OpenSpec 阶段时，按意图选择下面六个 `openspec-*` Workflow Skill；不要用 `spec-change-pack` 代替阶段入口。

## 当前 Skills

### `agent-assembler`

执行总入口。恢复 Agent 合同和人工决定，从目标选择能力，完成 manifest、profile、prompt、Skill、调用方与派生状态，并交付准确证据边界。

### `grilling`

在明示同意后通过结构化问题压力测试计划、决定或想法。复杂性、关键词或 Agent 偏好不构成同意；未同意时不得自动盘问。

### `agent-prompt-design`

设计 system prompt、profile prompt 和常驻指令。负责稳定角色、权威顺序、安全边界、路由和输出不变量；条件性多步骤流程不放入 prompt。

### `agent-skill-design`

设计条件性多步骤 Agent Skill。负责标准发现元数据、相邻路由边界、渐进披露、自由度选择、验证循环和完成条件。

### `capability-profile-closure`

检查 manifest、profile、prompt、能力文件和 lock 的项目内闭包，并分别报告 Skill 标准合规、声明态、配置态和生效态。

### `capability-lifecycle`

对依赖外部标准、版本、客户端行为或候选资产的决定进行一手来源调研，选择最小可逆的引入、升级或退役路径。

### `agent-behavior-evaluation`

建立行为基线和正反平衡场景，在可比较条件下检查 transcript、最终输出和环境终态，并把结论限制在实际证据覆盖范围内。

### `spec-change-pack`

使用仓库已授权的 OpenSpec 工作流组织较大的 Agent 行为变更。Proposal、delta、design、tasks/evidence 各自承担不同职责；规划不自动授权实施。

### `openspec-explore`

在实施或建立 change 前探索问题、边界和取舍；保持思考伙伴模式，不修改应用代码。

### `openspec-propose`

创建完整 planning package；完成 schema 要求的 proposal、delta specs、design 和 tasks 后停止，等待独立 Apply 请求。

### `openspec-update-change`

修订已有 change 的现存规划工件并保持相互一致；不创建缺失工件，不修改实现代码。

### `openspec-apply-change`

读取 change 当前工件和 apply instructions，逐项实施、验证并即时更新 tasks；不自动归档。

### `openspec-sync-specs`

按 Requirement 语义把 delta specs 合并到长期主规格，同时保留活动 change。

### `openspec-archive-change`

检查工件、tasks、规格和验证状态后，通过 OpenSpec CLI 完成同步和归档。

## 协作关系

```text
OpenSpec 基础工作流
    ├── openspec-explore
    ├── openspec-propose
    ├── openspec-update-change
    ├── openspec-apply-change
    ├── openspec-sync-specs
    └── openspec-archive-change

general
    └── OpenSpec 基础工作流

agent-assembler
    ├── grilling（仅明示同意后）
    ├── agent-prompt-design
    ├── agent-skill-design
    ├── capability-lifecycle
    ├── agent-behavior-evaluation
    ├── capability-profile-closure
    ├── spec-change-pack
    └── OpenSpec 基础工作流
```

这不是固定状态机。具体任务只加载必要 Skill，不为了“完整”串行执行全部流程。
