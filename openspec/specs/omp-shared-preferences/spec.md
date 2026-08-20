# omp-shared-preferences Specification

## Purpose
定义普通 OMP 与 CAP OMP runtime 如何共享用户模型、advisor、界面、provider 和认证配置，同时保证 CAP 的能力闭包、项目安全门禁及 secret 不因共享配置而失效。

## Requirements

### Requirement: CAP 必须投影已验证的共享用户偏好

CAP OMP launch MUST 从唯一显式的共享用户 preference source 读取受支持字段，并在当前 profile generation 的 native OMP 配置中投影其有效值。支持字段至少包含模型角色、`extendedContext`、推理和 service tier、advisor、theme、status line 与 composer 配置。共享 source 的有效配置变化 MUST 使后续 CAP launch 生成新的 effective generation；旧 generation 不得被报告为当前配置命中。

#### Scenario: 标准计费窗口进入 CAP generation
- **WHEN** 共享 preference source 将 `extendedContext` 设为 `false`
- **THEN** 使用 GPT-5.6 的后续 CAP OMP launch 的有效 context window SHALL 为标准计费窗口
- **AND** generation 记录不包含 preference 的敏感值

#### Scenario: Advisor 与外观进入当前 profile
- **WHEN** 用户在共享 preference source 修改 advisor、theme 或 status line
- **THEN** 后续 CAP launch SHALL 使用该值
- **AND** profile prompt、Skill、MCP、Hook、Plugin 与 project runtime policy SHALL 不因该修改改变

### Requirement: CAP 必须保持项目安全门禁优先

CAP MUST 只投影经过验证的 preference allowlist。系统固定门禁、项目 runtime policy 和当前 profile override MUST 优先于共享用户 preference；共享 preference MUST NOT 启用 ambient capability、放宽工具审批、改变 CAP runtime path、开启 project MCP discovery 或启用 memory backend。

#### Scenario: 用户 preference 包含能力字段
- **WHEN** 共享 preference source 包含 MCP、Skill、Hook、Plugin、extension、规则、工具审批或 runtime-path 字段
- **THEN** CAP generation SHALL 不投影这些字段
- **AND** 当前 profile 的显式能力闭包与固定门禁保持不变

#### Scenario: 项目策略拒绝共享偏好值
- **WHEN** 共享 preference 与系统固定门禁或项目 runtime policy 冲突
- **THEN** CAP SHALL 采用优先级更高的值
- **AND** 配置态证据 SHALL 标明发生覆盖但不得泄露原始敏感值

### Requirement: Provider 与认证必须共源且不复制 secret

普通 OMP 与 CAP OMP MUST 使用同一个明确批准的 provider 配置与认证来源。CAP SHALL 将必要 credential 仅注入启动的 OMP 进程，并允许当前 profile 的有效配置解析同一批准 endpoint；secret value MUST NOT 出现在项目文件、portable render、effective generation、lock、binding、receipt、诊断输出或日志中。

#### Scenario: 共享 API credential 启动 CAP OMP
- **WHEN** 普通 OMP 已可通过批准的共享认证来源访问一个 provider
- **THEN** CAP OMP SHALL 能以同一来源访问该 provider
- **AND** CAP 的认证投影、generation 和 receipt SHALL 不包含 token、API key、cookie 或 broker secret

#### Scenario: 未批准 endpoint 或认证来源
- **WHEN** provider endpoint 或 credential source 不属于允许的共享来源
- **THEN** CAP SHALL 在启动前拒绝该配置
- **AND** SHALL 不回退到 ambient credential 或 endpoint

### Requirement: 共享状态必须分层报告

CAP 的报告 MUST 分别说明 preference/认证 source 的声明态、投影后的有效配置态和实际 OMP 启动生效态。配置态通过 MUST NOT 在没有实际启动证据时声称 provider、advisor 或模型行为已生效。

#### Scenario: 未执行 OMP 行为 probe
- **WHEN** preference projection、generation 与 binding 已验证但未启动 OMP 请求
- **THEN** CAP SHALL 报告配置态通过
- **AND** 实际 provider 与 advisor 行为 SHALL 保持 `unknown`
