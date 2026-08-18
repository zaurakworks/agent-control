## Why

当前持久 OMP 启动把 `PI_CODING_AGENT_DIR` 与 `PI_CONFIG_DIR` 都指向 profile 专属 agent home，却没有使用 CAP 已声明的共享 `--auth-root`，因此 OMP 回落到各 profile 的本地认证库，`general` 与 `assembly-helper` 需要分别登录。认证身份不属于 profile 能力或 Session 状态；同一客户端应复用一份显式私有认证源，同时继续隔离 profile 配置和 Session。

## What Changes

- 让持久 OMP `use`、`launch` 与 `run` 路径和现有一次性 runtime 一样，从 `<auth-root>/omp` 绑定同一 OMP auth broker，而不是从 profile agent home 读取或刷新认证。
- `general` 与 `assembly-helper` 共享客户端级认证；一次有效登录或凭据刷新对两个 profile 均可用，切换 profile 不再要求重复登录。
- 继续把 OMP 配置、Skills、历史与 Session 写入 `<agent-home-root>/<profile>/omp`，不合并两个 profile 的运行状态。
- 缺失、权限不安全或无效的共享认证配置在启动客户端前失败；broker 已配置但不可达时明确失败，不回落 profile 本地认证或 ambient provider 凭据。
- receipt、render、lock 和诊断输出不得保存 broker token、认证环境值或认证文件正文。
- 更新使用与维护说明，明确共享认证库的预置条件、profile 状态隔离边界和无 secret 迁移方式。
- 非目标：不跨 Codex、Qoder、OMP 共享凭据；不复制或迁移既有 profile 本地 credential store；不由 CAP 托管 broker、生成 token 或自动执行登录；不改变 profile 能力闭包、prompt、Skill、lock schema 或 Session 归属。
- 回滚边界：整体回退持久 OMP 的共享认证绑定及对应说明；不得把认证复制回各 profile，也不得恢复 ambient credential 借用。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `layered-agent-profile`: 把“profile 专属客户端状态”细化为“配置与 Session 按 profile 隔离、认证按客户端从显式私有认证源共享”，并规定失败关闭和无 secret 边界。

## Impact

- 受影响实现：`tools/cap.py` 的持久 OMP 启动、环境构造、认证校验与错误处理；`tests/test_cap.py` 的共享认证、隔离、失败关闭和 secret 不落盘覆盖。
- 受影响文档：`README.md`、`docs/maintenance.zh-CN.md`；不修改 `.cap` profile、prompt、Skill 或 `.cap/lock.json`。
- 受影响 profile：`general`、`assembly-helper` 的 OMP 启动体验；Codex/Qoder 及 `--fresh` 现有认证合同保持不变。
- 基线证据：`tools/cap.py:_agent_home_dir` 按 profile 生成 OMP agent home，`_run_omp_agent_home` 当前未消费 `args.auth_root`；公共 profile 工具已把三端认证定义为 client 级 `--auth-root`，其中 OMP 使用 broker URL/token。
- 控制设计的一手来源：本机发布包 `@oh-my-pi/pi-coding-agent` 17.3.7 的 `src/session/auth-broker-config.ts` 明确认证发现优先使用 `OMP_AUTH_BROKER_URL`／`OMP_AUTH_BROKER_TOKEN`，配置 broker 后替代本地 SQLite store且不可达时不自动回落；仓库依赖的 `agent-control/tools/profile/profile.py:_staged_auth` 与其 README 定义 `<auth-root>/omp/{broker.json,token}` 的私有权限和无 secret 运行合同。
- 兼容性：CLI 参数保持兼容；持久 OMP 从隐式 profile 本地认证 clean cutover 到显式共享认证。尚未准备共享 broker 的启动会失败并给出操作指引，这是为避免静默借用或重复登录而接受的行为变化。
