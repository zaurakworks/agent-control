## Purpose

记录机器上发现但未获授权的 Agent-facing 资产候选，提供来源、漂移和隔离证据，而不把发现结果转化为当前 Agent 的使用权。

## ADDED Requirements

### Requirement: inventory 必须覆盖 Agent-facing 候选

系统 MUST 能记录 Skill、MCP、Hook、Plugin、Prompt、Rule、Agent、Marketplace 和相关客户端 settings 候选，并区分 capability plane 与 instruction plane。

#### Scenario: 用户目录存在未声明 MCP
- **WHEN** asset-inventory 发现 active MCP 且当前项目未显式导入
- **THEN** 记录其类型、来源、状态和 digest
- **AND** 不把它加入任何 profile 的有效闭包

### Requirement: inventory 记录必须无 secret

inventory MUST 只记录名称、类型、来源标识、active/passive/unknown 状态、mode、digest 和发现时间，不记录配置正文、命令参数、endpoint、token、cookie、session 或 history。

#### Scenario: 候选配置包含凭据
- **WHEN** 系统扫描候选 Agent 资产
- **THEN** 凭据内容不得进入 manifest、lock、binding、receipt 或 render
- **AND** 仍可记录非秘密结构摘要和变化状态

### Requirement: 未声明候选默认不得使用

asset-inventory MUST be observation-only。只有 project-defaults 或 role profile 中的显式 allow/import 才能使资产进入有效闭包。

#### Scenario: 候选未被项目导入
- **WHEN** 候选存在于 inventory 但未被项目声明
- **THEN** 状态至少为 observed 或 stripped
- **AND** 客户端能力面不得包含该候选

### Requirement: 无法确认隔离时必须阻断

当 active Agent-facing 候选未被声明且客户端无法证明已剔除时，当前客户端启动 MUST 被标记 blocked。

#### Scenario: 客户端无法观察候选是否被加载
- **WHEN** active 候选未授权且隔离结果为 unknown
- **THEN** 非交互启动 MUST 失败关闭
- **AND** receipt MUST 记录候选和 unknown 原因
