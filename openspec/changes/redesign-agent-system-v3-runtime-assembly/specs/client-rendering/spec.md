## MODIFIED Requirements

### Requirement: render 必须使用 v3 有效输入

client render MUST 从当前 role、project-defaults、runtime policy、machine-context-pin、assembly-binding 和已验证的 external import 计算输出。用户目录 ambient 配置不得作为未声明输入。

#### Scenario: OMP 生成临时 render
- **WHEN** 当前 OMP role 通过 lock、pin 和 binding 校验
- **THEN** render 只包含有效 prompt、能力和受控 runtime policy projection
- **AND** render 不复制未授权用户级资产

### Requirement: OMP native 文件只属于 adapter 输出

OMP MUST 只能在隔离 render 中生成客户端要求的 `config.yml`、`mcp.json` 和其他 native 文件；这些文件名和格式 MUST NOT 成为 CAP 的跨客户端源 schema。

#### Scenario: Codex 后续使用相同 v3 policy
- **WHEN** Codex adapter 实现同一 policy
- **THEN** 它可以生成自己的 native 文件
- **AND** 不得读取或复用 OMP 的 native config

### Requirement: render hash 必须覆盖 runtime policy

effective runtime policy、adapter version、profile/layer digest、能力闭包和固定门禁 MUST 参与 render hash 或关联 generation。策略变化不得命中旧 render。

#### Scenario: OMP 压缩策略发生变化
- **WHEN** effective compression setting 改变
- **THEN** OMP render generation 或 hash 必须改变
- **AND** 旧 generation 不得被当作当前配置使用
