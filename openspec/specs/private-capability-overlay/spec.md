# private-capability-overlay Specification

## Purpose
为公共 Agent profile 提供一个显式、可锁定且不泄露公司 Skill 内容的私有能力层，使依赖私有能力的 profile 只在授权机器和本地 source 上形成有效闭包。

## Requirements

### Requirement: 私有 overlay 必须显式绑定公共 source

系统 SHALL 支持一个明确指定的公共 source、一个明确指定的私有 overlay source 和一个目标 profile。私有 overlay 的 source、profile、lock 与 binding SHALL 通过显式路径或等价配置提供；系统 MUST NOT 通过用户目录扫描、ambient Skill、symlink 或缓存名称推断私有 overlay。

#### Scenario: 公共 profile 不依赖私有能力

- **WHEN** 用户启动只声明公共能力的 `general`
- **THEN** 系统 SHALL 只使用公共 source 和已验证的公共 profile 闭包
- **THEN** 私有 overlay 不存在、不可读或未绑定 SHALL NOT 影响该公共 profile

#### Scenario: 私有 profile 显式引用公共 profile

- **WHEN** 私有 profile `company-general` 显式指定公共 `general` 为 base，并增加公司 Skill
- **THEN** 系统 SHALL 解析公共与私有两层的有序 profile chain
- **THEN** effective inventory SHALL 包含公共能力和私有新增能力

#### Scenario: 私有 source 未获授权

- **WHEN** 私有 source、private lock 或 private binding 缺失、过期、摘要不匹配或路径越界
- **THEN** 系统 SHALL 在创建客户端进程前失败
- **THEN** 系统 SHALL NOT 回退到 ambient Skill、旧 render、其他私有 source 或公共同名能力

### Requirement: 分层能力操作必须显式且可逆

私有 overlay SHALL 沿用 `add`、`mask`、`replace` 的能力级操作。重复 `add`、未继承目标的 `mask`/`replace`、未声明的同名覆盖和跨层继承环 SHALL 失败。移除私有 overlay binding 后，公共 profile SHALL 能独立重建。

#### Scenario: 私有层新增公司 Skill

- **WHEN** 私有层以 `add` 声明一个公共层不存在的公司 Skill
- **THEN** private lock 和 effective inventory SHALL 记录该新增及其来源
- **THEN** 公共 lock SHALL NOT 包含该 Skill 名称或正文

#### Scenario: 私有层替换公共能力

- **WHEN** 私有层以 `replace` 指向一个已继承的公共能力
- **THEN** 系统 SHALL 在 effective inventory 中使用私有实现并记录替换关系
- **THEN** 未写明 `replace` 的同名实现 SHALL 被拒绝

#### Scenario: 回滚私有层

- **WHEN** 用户删除或禁用 private binding 并重新验证公共 profile
- **THEN** 公共 profile SHALL 使用原公共 lock 和公共 render 重新生成
- **THEN** 私有 source 的删除 SHALL NOT 删除公共 source、公共 lock 或公共 runtime

### Requirement: 私有内容与公共证据分离

公共仓库、公共 lock、公共 preview、公共 receipt 和公共诊断 SHALL NOT 包含私有 Skill 名称、正文、prompt、私有 profile 名称或私有 source 路径。私有 source MAY 位于用户状态下的独立 overlay 目录，但认证、token、session、history 和 cache SHALL 保持在独立运行态目录。

#### Scenario: 公共 preview

- **WHEN** 用户只请求公共 profile 的 closure 或 render preview
- **THEN** 输出 SHALL 只列出公共 source 的能力和摘要
- **THEN** 私有 overlay 的存在与内容 SHALL NOT 因本地目录存在而泄露

#### Scenario: 私有 preview

- **WHEN** 用户显式请求带 private overlay 的 effective preview
- **THEN** 输出 MAY 展示私有能力给本机授权用户
- **THEN** 输出 SHALL 仍然省略 token、cookie、认证正文、session 和 secret 值
