# claude-surface-closure Specification

## Purpose
定义 CAP 能力闭包如何映射到 Claude 的原生能力表面，以及 Claude ambient 面（用户级、项目级和管理层配置）如何被关闭、观察和分类，使「项目声明了什么」与「Claude 实际看到什么」之间的差距可被检查而不是被假设。

## Requirements

### Requirement: CAP 中间态与 Claude 原生格式必须分层

Claude adapter MUST 先产出由 CAP 拥有语义的中间配置，再由一个显式投影步骤生成 Claude 原生文件。Claude 的原生文件名、配置键和目录布局 MUST NOT 成为 CAP 的跨客户端源 schema，也 MUST NOT 被其他客户端 adapter 读取或复用。

#### Scenario: Claude 原生配置键发生改名
- **WHEN** Claude 升级导致某个原生配置键改名
- **THEN** 只需修改投影步骤并提升 Claude 的 adapter version
- **AND** CAP 中间态的语义字段与项目声明保持不变

#### Scenario: 另一个客户端 adapter 需要相同语义
- **WHEN** 其他客户端 adapter 需要表达同一条语义策略
- **THEN** 它 MUST 从同一套 CAP 语义输入独立投影自己的原生文件
- **AND** MUST NOT 读取 Claude 的原生配置

### Requirement: 原生投影只允许使用已留证的配置面

投影步骤中使用的每一个 Claude 原生文件名、环境变量、命令行参数和配置键 MUST 在版本化的核对证据中留有来源、抓取时间、验证方式和结论。未留证的原生键 MUST NOT 出现在实现中。

#### Scenario: 实现者需要一个尚未核对的原生键
- **WHEN** 投影需要一个尚未核对的 Claude 原生配置键
- **THEN** 必须先完成核对并写入证据
- **AND** MUST NOT 依据推测编码该键

#### Scenario: 中间态出现未映射字段
- **WHEN** CAP 中间配置中存在投影步骤未覆盖的字段
- **THEN** 投影 MUST 失败并指出该字段
- **AND** MUST NOT 静默丢弃该字段

### Requirement: Skill 闭包必须以显式副本进入 Claude 发现路径

由于 Claude 的 Skill 发现目录不可自定义，闭包内的 Skill MUST 以文件副本形式进入受 CAP 控制的配置目录，MUST NOT 使用符号链接或硬链接，且 Skill 允许清单 MUST 在中间态、原生配置和 generation manifest 三处保持一致。

#### Scenario: 闭包中的 Skill 被 Claude 发现
- **WHEN** 项目闭包包含若干 Skill
- **THEN** 这些 Skill MUST 出现在 Claude 的有效 Skill 集合中
- **AND** 三处允许清单 MUST 一致且被内容摘要覆盖

#### Scenario: 使用链接代替副本
- **WHEN** 配置目录中出现符号链接或硬链接
- **THEN** 校验 MUST 失败关闭
- **AND** MUST NOT 因为链接目标内容正确而放行

### Requirement: Claude ambient 面必须被关闭或降级为观察

用户级和项目级的 Claude Agent 资产 MUST 被关闭或排除在有效闭包之外。无法通过配置关闭的 ambient 面 MUST 由 fail-closed 门禁检查其是否携带能力，或被记录为 unknown 并计入证据。

#### Scenario: 用户级全局配置携带能力声明
- **WHEN** 用户级全局配置中出现 MCP、插件、钩子或 Skill 相关的能力键
- **THEN** 启动 MUST 失败关闭
- **AND** 错误信息 MUST 指出具体的配置来源

#### Scenario: 用户级全局配置只携带非能力偏好
- **WHEN** 用户级全局配置只包含不影响能力面的界面或运行偏好
- **THEN** 启动 MUST 正常继续
- **AND** 该配置 MUST 被记录为 passive 观察

#### Scenario: 工作目录携带客户端旁路配置
- **WHEN** 工作目录中存在未经项目声明的 Claude 客户端配置面
- **THEN** 启动 MUST 失败关闭
- **AND** MUST NOT 把该配置合并进有效闭包

### Requirement: 闭包验证必须分别报告 Claude 的三层证据

Claude 的闭包验证 MUST 分别输出声明态、配置态和生效态，并逐能力维度给出观察结论。通过 lock、generation 或水合校验 MUST NOT 被表述为客户端已经实际加载或已被完全隔离。

#### Scenario: lock 与 generation 均通过
- **WHEN** 项目 lock、generation 与水合校验全部通过
- **THEN** 声明态与配置态 MAY 标记通过
- **AND** 未经真实探测的维度生效态 MUST 保持 unknown

#### Scenario: 客户端输出不足以证明完整工具面
- **WHEN** 客户端输出不足以证明完整的 Skill 或工具面
- **THEN** 对应维度 MUST 标记 reported_client_limited 或 unknown
- **AND** MUST NOT 声称与其他客户端等价

### Requirement: Claude 资产观察不得授予能力

在用户目录中观察到的 Claude Agent 资产 MUST 只进入 asset-inventory。它们 MUST NOT 因为被观察、被安装或与项目同名而进入有效能力面；只有项目显式 allow、override 或经批准且摘要匹配的 external import 才能进入闭包。

#### Scenario: 用户目录存在与项目同名的 Skill
- **WHEN** 用户目录中存在一个与项目闭包内 Skill 同名的资产
- **THEN** 有效闭包 MUST 使用项目声明的来源
- **AND** 用户目录中的同名资产 MUST 只作为观察项记录

#### Scenario: 外部导入未获批准
- **WHEN** 一个用户级资产被引用为 external import 但未获批准或摘要不匹配
- **THEN** 校验 MUST 失败关闭
- **AND** 该资产 MUST NOT 进入任何 role 的闭包

### Requirement: 证据记录不得包含敏感内容

Claude 的 generation manifest、水合回执、receipt 和闭包报告 MUST 只记录摘要、路径、状态和计数。它们 MUST NOT 记录令牌、密钥、cookie、端点凭据、会话正文、历史正文或转发参数的取值。

#### Scenario: 转发参数中包含敏感取值
- **WHEN** 用户转发的客户端参数中包含敏感取值
- **THEN** 证据只记录转发参数的数量
- **AND** MUST NOT 记录任何参数取值

#### Scenario: 配置来源文件中包含凭据字段
- **WHEN** 被观察的配置来源中包含凭据字段
- **THEN** 证据只记录该来源的摘要与状态
- **AND** MUST NOT 复制凭据内容
