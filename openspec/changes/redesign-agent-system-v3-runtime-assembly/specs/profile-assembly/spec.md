## MODIFIED Requirements

### Requirement: role profile 必须是叶子角色组合

v3 role profile MUST 只表达角色 prompt、角色能力增量、project-defaults 引用和可选 runtime override。`real-home` 和 `work` 不得再作为用户可选 role 或公共继承层。

#### Scenario: 查看可运行 Agent
- **WHEN** 用户列出 profiles
- **THEN** 结果只包含 general、assembly-helper 及其他 role profile
- **AND** 不包含 machine-context、asset-inventory 或 project-defaults

### Requirement: 装配操作使用默认拒绝语义

role profile MUST 使用 allow、deny、override 表达能力装配。未显式 allow 的 Agent-facing 资产不得进入闭包；role 不得覆盖系统安全门禁。

#### Scenario: role 未声明机器候选
- **WHEN** machine inventory 有 MCP 但 role 没有 external import
- **THEN** role 的有效闭包不包含该 MCP
- **AND** 校验结果必须说明 observed、stripped 或 blocked 状态

### Requirement: profile 来源必须可锁定

role、project-defaults、runtime policy、machine-context pin 和 assembly-binding MUST 形成可验证的输入集合。旧继承链命名不得作为 v3 的运行时来源。

#### Scenario: role 源文件发生变化
- **WHEN** prompt、allow/deny/override 或 runtime override 改变
- **THEN** lock 或对应 digest 校验失败
- **AND** 启动必须要求显式刷新并重新审阅
