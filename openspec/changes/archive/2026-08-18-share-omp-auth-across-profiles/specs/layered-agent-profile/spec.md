## MODIFIED Requirements

### Requirement: 真实 HOME 与客户端状态隔离并存

继承 `real-home` 的客户端进程 SHALL 保留真实 `HOME`，使 Git、SSH、语言工具链和原生父级 context discovery 可用。客户端配置、Skills、历史和 Session 状态 SHALL 写入 profile 专属隔离根；同一客户端的认证 SHALL 来自 profile 外的显式私有认证源，并 SHALL 在 `general` 与 `assembly-helper` 之间共享。CAP SHALL NOT 复制整份 HOME、复制 profile 本地认证、借用 ambient provider 凭据，或把用户配置正文、认证正文、认证路径、token 与环境值写入项目 lock、render、binding、receipt 或诊断输出。

#### Scenario: OMP 从项目 worktree 启动

- **WHEN** `general` 或 `assembly-helper` 从当前 Git worktree 启动持久 OMP
- **THEN** `HOME` SHALL 等于真实用户 HOME，`PI_CODING_AGENT_DIR` 与 `PI_CONFIG_DIR` SHALL 指向所选 profile 的专属 agent home
- **THEN** 两个 profile SHALL 连接同一个由 `--auth-root` 显式选择的 OMP auth broker，且 SHALL NOT 从各自 agent home 或 ambient provider 环境读取认证

#### Scenario: 一次登录后切换 profile

- **WHEN** 用户已在共享 OMP auth broker 完成一次 provider 登录，并依次用 `general` 与 `assembly-helper` 执行需要该 provider 的真实请求
- **THEN** 两个 profile SHALL 使用 broker 提供的同一认证身份成功请求，不得要求第二个 profile 再次登录
- **THEN** 两个 profile 的 Session 列表、历史和配置 SHALL 继续保持互相隔离

#### Scenario: 共享认证输入无效

- **WHEN** 持久 OMP 所需的共享认证目录、broker metadata 或 token 缺失、权限不安全、格式无效或在启动前发生替换
- **THEN** CAP SHALL 在创建 OMP 进程前失败并给出不含 secret 的可操作错误
- **THEN** CAP SHALL NOT 回落到 profile 本地认证、真实 HOME 下的 OMP 认证或 ambient provider 凭据

#### Scenario: 共享 broker 不可达

- **WHEN** 已配置的 OMP auth broker 在客户端启动时不可达或拒绝认证
- **THEN** OMP 启动 SHALL 明确失败，且 SHALL NOT 自动回落本地 credential store

#### Scenario: 声明态与配置态闭包

- **WHEN** 共享认证绑定被实现但 profile、prompt、Skill、MCP、Hook、Plugin 和渲染配置均未改变
- **THEN** `general` 与 `assembly-helper` 的能力 inventory、项目 lock 与各客户端 render tree hash SHALL 保持不变
- **THEN** 认证 metadata、token 和 profile 本地认证正文 SHALL NOT 成为声明态或配置态闭包的一部分

#### Scenario: Skill 标准合规证据

- **WHEN** 本变更未修改任何 `SKILL.md`
- **THEN** Skill 元数据验证结果 SHALL 保持不变，且该结果 SHALL NOT 被报告为共享认证已生效的证据

#### Scenario: 共享认证生效态证据

- **WHEN** 只完成静态认证输入校验、单元测试、lock、render 或 `cap verify`，但未通过两个 profile 对同一 broker 身份执行真实 OMP 请求
- **THEN** 结果 SHALL 只报告声明态或配置态，不得声称重复登录问题已在实际客户端中解决

#### Scenario: 运行收据

- **WHEN** OMP 运行完成且 post-run binding 校验通过
- **THEN** receipt SHALL 包含 base、layer、effective 和 render tree digest，且 SHALL NOT 包含参数值、认证路径、环境值或 secret
