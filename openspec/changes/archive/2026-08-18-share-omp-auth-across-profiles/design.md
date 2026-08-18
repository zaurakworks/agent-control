## Context

见 `proposal.md` 的 Why。CAP 对 Codex、Qoder 和 `--fresh` OMP 已把认证交给公共 profile 工具的 client 级 `--auth-root`；只有持久 OMP 为保留 profile Session 而走 `tools/cap.py:_run_omp_agent_home`，直接构造命令与环境，因而遗漏共享认证绑定。该路径必须同时满足三项约束：真实 `HOME` 不变、profile agent home 持久且隔离、认证不得来自 profile 或 ambient 配置。

OMP 17.3.7 的一手实现规定 `OMP_AUTH_BROKER_URL`／`OMP_AUTH_BROKER_TOKEN` 优先于配置与本地 SQLite store；配置 broker 后不可达即失败，不自动回落。公共 profile 工具已把私有输入固定为 `<auth-root>/omp/{broker.json,token}`，但不托管 broker。broker 的登录在 broker host 上通过 `omp auth-broker login` 完成，profile 客户端只消费共享 snapshot。

## Goals / Non-Goals

**Goals:**

- 让持久 OMP 与现有临时 runtime 使用同一个 client 级 auth-root 合同。
- 在不合并 agent home 的前提下，让两个 runnable profile 观察同一认证身份。
- 在创建 OMP 进程前验证认证输入，并保持失败关闭与无 secret 输出。
- 保持 profile 能力闭包、render tree、prompt 与 Skill 完全不变。

**Non-Goals:**

- 不建立第二套 broker、secret 管理器或后台服务 supervisor。
- 不让 profile 内 `/login` 负责写远端 broker；登录与迁移仍使用 OMP 原生 `auth-broker` 命令在 broker host 完成。
- 不共享 OMP agent home、Session、history、cache 或设置。
- 不修改 prompt 或 Skill；认证是 launcher/runtime 约束，不是模型行为合同。
- 不替用户复制、删除或提交既有 profile 本地认证数据库。

## Decisions

### 1. 共享 OMP broker，不共享 agent home 或本地 SQLite 文件

持久 OMP 启动固定读取同一 `<auth-root>/omp/broker.json` 和 `<auth-root>/omp/token`，并通过 OMP 官方最高优先级环境变量绑定 broker。`PI_CODING_AGENT_DIR`、`PI_CONFIG_DIR` 与 `PI_CONFIG_FILES` 继续按 `<agent-home-root>/<profile>/omp` 生成。

未采用共享整个 agent home：这会合并 Session、历史、设置和 cache，破坏 profile 隔离。未采用复制或 symlink `auth.db`：SQLite 多进程写入和 schema 演进会形成不受支持的共享文件协议，也绕过 OMP 已提供的 broker 边界。未采用真实 HOME 自动借用：它重新引入 ambient 配置，违反显式能力面。

### 2. 在持久路径中实现窄的认证输入门禁

`tools/cap.py` 增加只面向 OMP broker 的读取器；不抽象三端通用 credential framework。读取器复用公共 profile 工具已经声明的外部合同：

- auth root 与 `omp/` 必须位于项目外，且目录非 symlink、由当前用户拥有、owner 可读写执行、group/other 无权限；
- `broker.json` 与 `token` 必须是当前用户拥有、单一硬链接的普通文件，拒绝 symlink 和 group/other 权限；
- 通过 no-follow 文件描述符读取受限大小的稳定快照，并在读取前后核对 inode、size、mtime 与 ctime，避免检查后替换；
- metadata 只接受 `version: 1` 与无 userinfo、path、query、fragment 的 URL；远端必须 HTTPS，loopback 可用 HTTP；
- token 只接受非空、无空白的可打印 ASCII，任何错误均不回显正文。

未采用“只让 OMP 自己报错”：那会在客户端进程创建后才发现权限、symlink 或格式问题，也会让持久路径弱于既有 `--fresh` 合同。这里存在与公共工具校验规则同步的维护成本；通过聚焦测试和维护文档中的来源版本明确承担，而不引入跨仓私有 Python API 依赖。

### 3. 环境顺序显式固定，broker 最后写入

环境从宿主副本开始，先移除客户端配置根和可能携带 provider/API/OAuth/cloud 凭据的 ambient 变量，再设置：

1. 真实 `HOME`；
2. profile 专属 `PI_CODING_AGENT_DIR`、`PI_CONFIG_DIR`、`PI_CONFIG_FILES` 与固定 profile 名；
3. 禁止认证借用和 metadata 探测的防护值；
4. 已验证的 `OMP_AUTH_BROKER_URL` 与 `OMP_AUTH_BROKER_TOKEN`。

broker 环境最后写入，调用方和 ambient 环境不能覆盖。认证缺失或无效时不构造 OMP 命令。broker 可达性与响应认证由 OMP 启动检查负责；其官方行为是显式 broker 失败时不回落本地 store。

### 4. 认证不进入 render、lock、binding 或 receipt

认证绑定只存在于单次子进程环境。`_render_for_agent_home` 仍只物化 profile 配置；`.cap-rendered`、项目 lock、binding 和 tree hash 均不含认证。receipt 保持现有 schema，不新增 auth root、URL、token 或环境摘要。错误消息只命名字段或相对合同，不输出 token、文件正文或私有路径。

### 5. 证据分层且真实 smoke 必须跨 profile

- 标准合规：本 change 不改 `SKILL.md`；`skills-validate` 只能证明无回归。
- 声明态/配置态：比较两个 profile、三客户端变更前后的 inventory 与 render tree hash；预期完全不变。
- 聚焦行为：单元测试用同一测试 auth root 启动两个 profile，断言 broker URL/token 相同而 agent home、Session 根不同；覆盖权限、symlink、格式、替换、ambient override 和 receipt 无 secret。
- 生效态：在私有 broker 已运行且已有测试身份时，分别用 `general` 与 `assembly-helper` 发起真实 OMP provider 请求，确认第二个 profile 不要求登录；再创建或列举 Session，确认两边状态不串用。没有这一步只能报告配置态。

## Risks / Trade-offs

- [公共 profile 工具与 CAP 的 OMP auth 校验规则漂移] → 只复制已发布的窄 broker 合同，测试所有安全边界；升级 profile 工具或 OMP 时按维护指南同时复核两处。
- [broker 未运行导致所有持久 OMP 启动失败] → 启动错误明确指向 `omp auth-broker serve`／`status`；不自动启动服务，也不静默回落。
- [用户误以为可在 profile 内直接登录远端 store] → 文档明确登录发生在 broker host，并给出 OMP 原生命令；CAP 不伪造可写 remote store。
- [ambient credential 清理影响原先偶然可用的 provider] → 这是显式失败关闭的有意 clean cutover；用户应把所需身份放入 broker，不保留兼容开关。
- [真实 smoke 暴露 secret] → 测试只观察退出状态、非敏感身份标记和隔离目录，不打印环境、token 或认证文件。

## Migration Plan

1. 实施认证读取门禁、环境绑定和聚焦测试，不修改 profile 声明或 render 输入。
2. 更新 README 与维护指南：说明 auth root 私有权限、broker host 的 `login`／`serve`／`status` 流程，以及 profile 内认证只读边界；不记录真实 URL 或 token。
3. 运行单元测试、Skill 标准验证、CAP verify、两个 profile 的三端 render hash 对比和 OpenSpec strict validation。
4. 在测试 broker 上完成一次 provider 登录，依次运行两个 profile 的真实 OMP 请求并检查 Session 隔离；仅在该观察通过后报告重复登录问题已实际解决。
5. clean cutover 后不迁移也不删除旧 profile 本地认证文件；显式 broker 始终优先且失败不回落。
6. 回滚时整体回退持久 OMP 的 broker 绑定与文档。auth root 与 broker 由用户控制，不随代码回滚修改；不得复制 token 或认证库到 profile agent home。
