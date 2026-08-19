## Purpose

定义项目公共 Agent 能力的显式装配，替代 `work` profile，并为所有 role 提供可审计的默认能力集合。

## ADDED Requirements

### Requirement: project defaults 必须显式声明来源

project-defaults MUST 只包含项目拥有的能力或经过显式 external import 的能力。机器 inventory 中仅被发现的候选不得自动进入 defaults。

#### Scenario: 项目声明公共 Skill
- **WHEN** 项目 defaults 显式 allow 一个仓库内 Skill
- **THEN** 该 Skill 可被有效 role 闭包继承
- **AND** lock MUST 记录其项目源和 digest

### Requirement: 默认拒绝 Agent 能力

未被 project-defaults 或 role profile 显式 allow 的 Skill、MCP、Hook、Plugin MUST 不进入有效闭包。

#### Scenario: 机器存在未声明能力
- **WHEN** inventory 中有未导入的用户级能力
- **THEN** project-defaults MUST 不得间接继承它
- **AND** 当前 profile MUST 收到 observed、stripped 或 blocked 证据

### Requirement: defaults 与 role 必须可组合

系统 MUST 支持 role 对 project-defaults 做显式 allow、deny 或 override；role 不得解除更高层安全拒绝或隐式导入机器候选。

#### Scenario: assembly-helper 屏蔽公共能力
- **WHEN** project-defaults 包含一项公共 MCP 且 assembly-helper 声明 deny
- **THEN** assembly-helper 的有效闭包不得包含该 MCP
- **AND** general 的闭包不受该 role deny 影响

### Requirement: external import 必须保留 provenance

external import MUST 记录来源标识、digest、审批状态和适用 role。机器拥有权不得等同于项目使用权。

#### Scenario: profile 只允许使用外部 MCP
- **WHEN** 项目显式导入一个机器来源 MCP 并仅绑定 assembly-helper
- **THEN** assembly-helper 可以使用已批准版本
- **AND** general 不得获得该 MCP
