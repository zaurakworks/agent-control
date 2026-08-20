## Why

普通 OMP 与 CAP 使用不同的 runtime 配置根：用户修改模型窗口、advisor、主题、状态栏、provider 或认证后，CAP 不会自动继承；CAP 当前也不会让已打开的 profile 在 `/resume` 中选择其他 profile 创建的 session。用户需要一份共享的 OMP 用户偏好、认证来源和 session 目录，同时继续以当前 CAP profile 的 prompt 与能力闭包运行。

## What Changes

- 新增受控的 OMP 共享用户偏好投影：模型角色、上下文计费窗口、推理／tier、advisor、主题、status line、composer 和其他已验证的非能力配置从唯一用户偏好源进入 CAP 的隔离 runtime。
- 新增共享认证与 provider 配置来源：CAP 与普通 OMP 使用同一份批准的认证存储和 provider endpoint 配置；secret 仅在启动时注入，绝不写入 render、lock、generation manifest、receipt 或日志。
- 新增跨 profile session resume：所有 CAP profile 使用同一个 OMP session root；在当前 profile 打开 `/resume` 时可选择该 root 中任意空闲 session，并以当前 profile 继续。
- 选择其他 profile 创建的 session 时，当前 profile 的模型、advisor、prompt、Skill/MCP/Hook/Plugin 闭包和项目 runtime policy 生效；session transcript 与 identity 保持，不恢复旧 profile 的运行中任务、tool call、worktree 或能力配置。
- 在 session 中保留创建 profile 与最近一次恢复 profile 的无 secret 摘要，供 picker 与诊断区分来源；同一 session 同时只允许一个写入实例。
- **BREAKING**：CAP 不再要求手工镜像普通 OMP 的模型、advisor 和外观设置；CAP runtime 的这些字段由共享偏好投影管理，直接编辑 CAP 派生 `config.yml` 不再是持久配置入口。

## Capabilities

### New Capabilities

- `omp-shared-preferences`: 定义普通 OMP 与 CAP 之间可投影的用户偏好、provider 配置与认证来源、secret 边界、优先级、变更检测和 generation 证据。
- `omp-cross-profile-resume`: 定义共享 session root、跨 profile `/resume` picker、当前 profile 续接语义、单写者约束和 session 来源摘要。

### Modified Capabilities

- 无。现有全局 OpenSpec capability 未定义上述可观察行为；本变更以新增 capability 固化合同。

## Scope

### In scope

- OMP runtime preference 的严格 allowlist、配置合成顺序、CAP generation/hash/binding 失效条件和 CLI 诊断。
- 普通 OMP 与 CAP 共用的认证／provider source adapter；仅共享声明、引用或启动期注入，不复制 credential value。
- 统一 CAP profile 的 OMP session root，并让 `/resume` 发现并选择跨 profile 的空闲 session。
- 恢复时按当前 profile 重建 OMP adapter、系统提示、能力闭包、模型、advisor 与 native 配置；必要时按当前有效 context window 压缩历史。
- `general` 与 `agent-assembler` profile 的配置态和实际 OMP 行为验证。

### Out of scope

- 共享 CAP render root、profile prompt、Skill/MCP/Hook/Plugin、审批规则、worktree、运行中子 Agent、tool execution 或 profile capability declaration。
- 把 API key、OAuth token、broker token、cookie 或 endpoint credential 写入项目文件、OpenSpec 工件、lock、generation manifest、receipt 或日志。
- 支持同一个 session 的并发写入、无提示地继续已运行的 session，或在 resume 时恢复旧 profile 的未完成运行态。
- 改变 Codex、Claude、Qoder 或其他客户端的 runtime／session 行为。

## Affected Profiles and Clients

- 受影响 profile：`general`、`agent-assembler`，以及使用同一 OMP runtime id 的后续 CAP profile。
- 受影响客户端：OMP；普通 OMP 与由 `cap` 启动的 OMP 都必须消费同一共享偏好和认证来源。

## Baseline Evidence

- `docs/profile.md` 当前规定 OMP adapter 只把 `memory_backend` 与 `enable_project_mcp` 投影到隔离 `config.yml`，advisor、预算和压缩等 native key 未接入。
- `src/agent_system/omp/runtime.py` 当前只从隔离 OMP runtime 读取 preference，并在 `_effective_config_template()` 中仅投影 memory、MCP 与 CAP Skill 门禁。
- `src/agent_system/profile/cli.py` 的 OMP launch adapter 为 profile generation 设置独立 `PI_CODING_AGENT_DIR`、`PI_CONFIG_DIR` 与 `PI_CONFIG_FILES`，因此普通 OMP 的 `~/.omp/agent` 设置不会自动成为 CAP 生效配置。
- 本机 OMP 17.4 source 的 `settings-schema.ts` 定义 `extendedContext`：关闭时 GPT-5.6 在 272K 标准计费窗口前压缩；OMP CLI 支持 `--session-dir` 和 `PI_CODING_AGENT_SESSION_DIR` 作为 session 存储与 lookup 根。
- 归档的 `share-omp-runtime-across-profiles` 记录了共享 runtime 与显式跨 profile resume 的历史设计；它仅作为待核验背景，本变更以当前源码与可观察行为重新建立合同。

## Rollback Boundary

实现必须在更改共享 session root 或 credential binding 前生成可回读的迁移预览；冲突、active session、不可识别 credential source 或 secret 可能落盘时停止且不改写旧状态。回滚只恢复上一份 runtime binding、session-root 指针和 preference projection；保留原 session JSONL 与认证存储，不删除 transcript、token 或 cache。回滚后 CAP 继续使用隔离 runtime，不再从共享 preference source 投影新增字段。