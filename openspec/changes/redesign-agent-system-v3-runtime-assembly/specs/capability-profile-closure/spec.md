## MODIFIED Requirements

### Requirement: 闭包必须区分资产来源和能力平面

验证 MUST 分别输出 machine-context、asset-inventory、capability plane、instruction plane、project defaults、role profile 和 runtime policy 的状态。机器候选不得因被观察而成为 effective capability。

#### Scenario: 用户目录存在 active Skill
- **WHEN** Skill 未被项目 allow 或 external import
- **THEN** 它只出现在 asset-inventory
- **AND** 不出现在有效 Skill inventory

### Requirement: unknown 必须保守处理

对 active Agent-facing 资产，若客户端无法证明未加载，验证结果 MUST 为 blocked；passive 或不影响能力面的观察不足 MAY 保持 warning/unknown。

#### Scenario: OMP 无法证明完整工具面
- **WHEN** 配置态显示没有额外 MCP 但实际 probe 不完整
- **THEN** 生效态保持 unknown 或 reported_client_limited
- **AND** 系统不得将其升级为 confirmed safe

### Requirement: lock、render 与 runtime evidence 必须分层

闭包验证 MUST 区分声明态、配置态和生效态。通过 lock 或 render 不得单独声称客户端已经实际加载或隔离。

#### Scenario: profile lock 通过
- **WHEN** 项目 lock 和 runtime render hash 一致
- **THEN** 声明态和配置态可以标记通过
- **AND** 未执行真实 probe 的客户端生效态仍为 unknown
