## Purpose

提供从旧 `real-home`、`work`、继承链、状态根、pin/binding 和 OMP runtime 到 v3 命名与路径的一次性迁移，并保留可审计的失败和回滚边界。

## ADDED Requirements

### Requirement: 迁移必须显式分阶段

迁移 MUST 支持 dry-run、apply、verify 和 quarantine 阶段。普通 profile 启动不得隐式修改旧状态或自动批准新 machine-context。

#### Scenario: 用户执行迁移 dry-run
- **WHEN** 旧状态存在且用户未选择 apply
- **THEN** 系统输出旧到新对象的映射、冲突、丢弃项和 secret 风险
- **AND** 不修改旧路径、新状态或 pin

### Requirement: 旧语义必须映射到 v3 对象

迁移 MUST 明确映射：

```text
real-home -> machine-context
用户级 Agent 候选 -> asset-inventory
work -> project-defaults
role profile -> role profile
base pin -> machine-context-pin
binding -> assembly-binding
```

#### Scenario: 旧 profile 包含 mask
- **WHEN** 系统迁移旧 `mask`
- **THEN** 必须说明它被转换为 deny、移除或人工审阅项
- **AND** 不得默默把旧继承能力变为 v3 allow

### Requirement: 旧路径不得长期作为运行来源

apply 和 verify 成功后，旧状态 MUST 只保留在隔离备份和迁移报告中。v3 runtime、lock、binding 和 render 不得继续读取旧路径。

#### Scenario: 新状态校验通过
- **WHEN** v3 machine-context、runtime 和 binding 验证完成
- **THEN** 旧 `$HOME/.cap-user-state` 只可由显式 migration rollback/cleanup 操作访问
- **AND** 普通启动不得自动回退到旧状态

### Requirement: 迁移失败必须停止且不破坏旧状态

发生权限、冲突、secret 边界、digest 或 schema 不明确时，迁移 MUST 停止并保留旧状态不变。

#### Scenario: OMP settings 合并冲突
- **WHEN** 旧 runtime 与 v3 runtime 的同一设置具有实质冲突
- **THEN** apply 失败并报告字段路径
- **AND** 不得覆盖旧 runtime 或生成假成功 receipt
