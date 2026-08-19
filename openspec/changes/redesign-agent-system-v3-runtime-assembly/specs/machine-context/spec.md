## Purpose

定义经过审批的机器宿主运行上下文，保留客户端进程正常运行所需的 HOME、Git、SSH、工具链和必要宿主集成，同时阻止用户目录中的 Agent 资产自动成为能力来源。

## ADDED Requirements

### Requirement: 宿主上下文与 Agent 能力必须分离

系统 MUST 将机器宿主运行底座与 Agent-facing capability plane 分开表示。宿主上下文不得因为包含用户 HOME 而自动授权 Skill、MCP、Hook、Plugin、Prompt、Rule 或 Agent。

#### Scenario: 真实 HOME 提供宿主工具链
- **WHEN** OMP profile 需要 Git、SSH 或语言工具链
- **THEN** 进程可以使用批准的 machine-context
- **AND** 用户级 Agent 资产不会因此进入当前 profile 的能力闭包

### Requirement: machine-context 必须可审批和检测漂移

系统 MUST 为 machine-context 生成不含 secret 的摘要，并通过独立 pin 表示已批准状态。active 变化 MUST 使摘要失效；passive 变化 MAY 只产生告警。

#### Scenario: active 宿主上下文发生变化
- **WHEN** 影响宿主行为或可用性的一项 active machine-context 输入发生变化
- **THEN** 当前 binding 必须被视为 stale
- **AND** 非交互启动 MUST 停止

### Requirement: machine-context 记录不得携带秘密

machine-context manifest、pin、binding 和 receipt MUST NOT 保存 token、cookie、session、history、私钥正文或 endpoint secret。

#### Scenario: 生成宿主上下文摘要
- **WHEN** 系统记录 machine-context
- **THEN** 只保存路径类别、状态、mode、内容摘要和聚合 digest
- **AND** secret-only 内容不得被写入仓库或公共工件
