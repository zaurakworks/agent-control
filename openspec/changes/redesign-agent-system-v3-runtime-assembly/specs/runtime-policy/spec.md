## Purpose

定义客户端运行策略与 Agent 能力装配之间的边界，使上下文压缩、advisor、预算和停止策略可按用户 runtime、项目和 role 组合并被审计。

## ADDED Requirements

### Requirement: runtime policy 必须独立于 Agent 能力

runtime policy MUST NOT 被表示为 Skill、MCP、Hook、Plugin 或 prompt。它描述客户端运行行为，不授予新的工具能力。

#### Scenario: 配置上下文压缩阈值
- **WHEN** 用户设置 OMP 的压缩策略
- **THEN** 该值进入 runtime policy
- **AND** 不改变 profile 的 Agent-facing capability closure

### Requirement: 全局默认必须按 client 和 runtime-id 隔离

用户全局 runtime preference MUST 按 `<client>/<runtime-id>` 分区。一个客户端的 native 配置不得直接成为另一个客户端的配置来源。

#### Scenario: OMP 与 Codex 使用相同 runtime-id
- **WHEN** 两者都使用 `default`
- **THEN** 它们仍必须拥有独立的 runtime namespace
- **AND** OMP 的 native config 不得被 Codex 直接读取

### Requirement: policy 合成顺序必须稳定

有效 runtime policy MUST 按以下顺序合成：系统固定安全门禁、项目 runtime policy、role override、用户全局默认。项目和 role 不得覆盖系统安全门禁。

#### Scenario: 项目覆盖用户默认压缩设置
- **WHEN** 用户全局值与项目 policy 不同
- **THEN** 项目 policy 生效
- **AND** receipt 记录全局输入摘要与最终 effective value

### Requirement: 客户端专属字段必须经过 adapter 管理

跨客户端通用语义 MAY 投影为各客户端支持的 native 字段；客户端专属字段 MUST 由目标 adapter 的 allowlist、版本和验证规则管理，不得开放任意 native passthrough。

#### Scenario: OMP 支持的 advisor 字段被投影
- **WHEN** OMP adapter 声明该字段受支持且项目 policy 允许
- **THEN** OMP render 可以生成对应 native 配置
- **AND** 不得声称 Codex 或 Claude 具有等价生效语义

### Requirement: runtime policy 必须有 effective 证据

每次运行 MUST 能关联 runtime-id、policy digest、effective settings、generation 和 render hash。不得用用户自述或 native 文件存在冒充实际生效态。

#### Scenario: 运行 OMP one-shot
- **WHEN** CAP 启动 OMP
- **THEN** receipt 记录 policy 和 effective render 摘要
- **AND** secret、Session 正文和 history 不得进入 receipt
