# claude-runtime Specification

## Purpose
为 Claude 客户端提供与 OMP 同构的受控 render、generation、水合配置目录、启动门禁和运行证据，使 Claude 成为可审计、可复现的 CAP 一等客户端，并明确其相对 OMP 更低的隔离与证据上限。

## Requirements

### Requirement: Claude 必须使用隔离 generation 启动

每次 Claude launch 或 run MUST 先由当前 role、project-defaults、能力闭包和 Claude runtime policy 生成 generation，并显式指向该 generation 的产物。用户目录中的 Agent 资产 MUST NOT 因为进程从真实 HOME 启动而自动进入有效能力面。

#### Scenario: 用户 HOME 存在未声明的 Claude Skill
- **WHEN** 用户级目录中存在一个 active 的 Claude Skill，且该 Skill 未被项目 allow、override 或已批准 external import 覆盖
- **THEN** 经 CAP 启动的 Claude 有效 Skill 集合中不出现该 Skill
- **AND** 该 Skill 只出现在 asset-inventory 观察结果中

#### Scenario: Claude 需要宿主工具链
- **WHEN** Claude 需要 Git、SSH 或语言工具链
- **THEN** 进程可保留已批准的宿主上下文
- **AND** Claude 的 prompt、Skill、MCP、settings 和 subagent 来源仍由当前 generation 控制

### Requirement: Claude generation 必须由三个 Hash 共同锁定

Claude adapter MUST 计算并记录 `portable_tree_hash`、`effective_render_hash` 和 `content_digest`。`effective_render_hash` MUST 覆盖能力闭包、effective runtime policy、adapter version、固定门禁和已核对的 native 面摘要，并作为 generation 的内容寻址目录名。

#### Scenario: Claude runtime policy 中的投影字段改变
- **WHEN** `.cap/runtime/claude.toml` 中一个会被投影的字段取值改变
- **THEN** `effective_render_hash` 必须改变
- **AND** 旧 generation 不得被当作当前配置命中使用

#### Scenario: generation 目录内容被手工改写
- **WHEN** generation 中任一被 `content_digest` 覆盖的文件被修改
- **THEN** 启动前校验必须失败并报告内容漂移
- **AND** 不得回退为重新生成后静默继续

#### Scenario: 已核对的 Claude native 面结论更新
- **WHEN** native 面核对证据的摘要发生变化
- **THEN** 依赖该摘要的 generation 必须失效
- **AND** 必须重新物化后才能启动

### Requirement: Claude 配置目录必须区分不可变与可变子集

Claude 的配置目录必须可写，因此 adapter MUST 把 generation 水合成一个位于 runtime 命名空间下的配置目录，并按 generation manifest 声明的清单区分不可变子集与可变子集。不可变子集 MUST 在每次启动前逐路径校验；可变子集 MUST NOT 参与内容校验。

#### Scenario: 水合目录中的 settings 被手工提权
- **WHEN** 水合配置目录中属于不可变子集的文件被修改
- **THEN** 启动 MUST 失败并指出需要重新水合
- **AND** 不得以「文件可重新生成」为由继续启动

#### Scenario: 客户端写入会话与缓存
- **WHEN** Claude 在运行中写入已声明的可变子集路径
- **THEN** 下次启动的校验 MUST 通过
- **AND** 这些写入 MUST NOT 影响 `content_digest` 或 `hydration_digest` 的比对结果

#### Scenario: 配置目录出现未声明的能力面路径
- **WHEN** 水合目录中出现未在清单中声明、且命中已知能力面名称的路径
- **THEN** 启动 MUST 失败关闭
- **AND** 该路径 MUST 出现在错误信息与证据记录中

### Requirement: Claude 能力闭包与 runtime policy 必须独立校验

Claude generation MUST 分别校验 Agent-facing capability closure 与 runtime policy。runtime policy 的变化 MUST NOT 绕过能力 lock、machine-context pin 或 assembly-binding；系统固定门禁 MUST NOT 被 role override 或用户全局 preference 放宽。

#### Scenario: policy 合法但 machine context 已漂移
- **WHEN** Claude runtime policy 无冲突但 machine-context active digest 已漂移
- **THEN** 非交互启动 MUST 失败
- **AND** 不得仅因为 Claude 配置可以生成就继续运行

#### Scenario: 用户全局 preference 试图开启用户级资产
- **WHEN** 用户全局 preference 试图允许用户级 Skill、subagent 或 command 进入闭包
- **THEN** 合成 MUST 失败关闭
- **AND** 错误信息 MUST 说明该项属于不可放宽的系统门禁

### Requirement: 转发参数不得重新打开固定门禁

Claude 启动 MUST 拒绝会重新打开 CAP 已关闭能力面的客户端参数，包括但不限于重新指定 settings、设置来源、MCP 配置、插件目录、子代理目录、附加访问目录、权限模式、系统提示词替换和跳过权限确认的参数。

#### Scenario: 用户在分隔符后传入插件目录参数
- **WHEN** 用户在 `--` 之后传入一个会旁路加载插件的参数
- **THEN** 启动 MUST 失败并指出该参数由 CAP 固定门禁占用
- **AND** MUST NOT 启动客户端进程

#### Scenario: 用户传入普通业务参数
- **WHEN** 用户在 `--` 之后传入不影响能力面与门禁的参数
- **THEN** 启动 MUST 正常继续
- **AND** receipt 只记录转发参数数量，不记录参数值

### Requirement: Claude 生效态证据必须保守且区分形态

Claude 的 Skill、MCP、Hook、Plugin、context 和 managed settings 观察结果 MUST 按真实可证明的能力分类；无法观察的结果 MUST 保持 unknown 或 reported_client_limited。CLI 与 IDE 形态 MAY 达到部分生效态；API/SDK 形态的生效态 MUST 由调用方负责；Web 形态 MUST NOT 产生 receipt。

#### Scenario: 存在无法接管的企业管理配置层
- **WHEN** 宿主上存在 CAP 无法控制的 Claude 管理配置层
- **THEN** 证据 MUST 标记该层为 unknown
- **AND** MUST NOT 声称 Claude 已被完全隔离

#### Scenario: 本次运行未执行真实能力探测
- **WHEN** generation 与水合校验均通过但未执行真实探测
- **THEN** 声明态与配置态 MAY 标记通过
- **AND** 生效态 MUST 保持 unknown

#### Scenario: 通过 Web 形态使用同一 role
- **WHEN** 用户在 Claude Web 中使用 CAP 产出的声明态内容
- **THEN** CAP MUST NOT 写出 receipt 或任何生效态结论
- **AND** 只允许提供可人工核对的声明态产物

### Requirement: Claude 认证与会话状态不得成为能力来源

Claude 的认证材料、会话、历史和缓存 MUST 保存在 runtime 命名空间内，按 runtime-id 跨项目共享。这些状态 MUST NOT 被反向读取为项目能力发现来源，generation MUST NOT 修改它们。

#### Scenario: 两个项目使用同一 Claude runtime-id
- **WHEN** 两个项目选择同一个 Claude runtime-id
- **THEN** 它们可以共享已批准的认证与会话状态
- **AND** 每次启动仍必须使用各自项目的 generation、能力闭包与 runtime policy

#### Scenario: runtime 中存在历史遗留的能力声明
- **WHEN** Claude runtime 状态中出现能力相关的配置内容
- **THEN** 该内容 MUST NOT 进入有效能力闭包
- **AND** 只能作为观察证据被记录

### Requirement: 未实现的能力类别必须失败关闭

本 adapter 未实现 native 投影的能力类别 MUST 在 generation manifest 中显式标记为 unsupported。若项目为 Claude 声明了这些类别的能力，render MUST 失败关闭，MUST NOT 渲染出缺少这些能力的结果。

#### Scenario: 项目为 Claude 声明了未支持类别的能力
- **WHEN** 项目闭包中包含本 adapter 未实现投影的能力类别
- **THEN** render MUST 失败并说明该类别未被支持
- **AND** MUST NOT 产出一个静默丢弃该能力的 generation

#### Scenario: 项目未声明未支持类别的能力
- **WHEN** 项目闭包中该类别为空
- **THEN** render MUST 成功
- **AND** manifest MUST 记录该类别为 unsupported
