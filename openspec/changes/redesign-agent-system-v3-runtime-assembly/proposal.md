## Why

当前 CAP 把机器宿主环境、用户目录中发现的 Agent 资产、项目共享能力和角色 profile 混在 `real-home -> work -> role` 继承链中，导致“机器上存在”容易被误解为“当前 Agent 被允许使用”。同时，OMP 的持久 runtime、临时 render、模型上下文压缩和 advisor 配置没有独立的可审计语义，无法为 OMP 主力运行建立稳定的全局默认、项目覆盖和生效证据。

本变更把宿主上下文、资产观察、Agent-facing 能力闭包和 client runtime policy 分开，完成一次 v3 命名与路径迁移。当前实现只覆盖 OMP；Codex 和 Claude 的后续 adapter 必须消费同一套 v3 合同，但不在本次实现范围内。

## What Changes

- **BREAKING** 将 `real-home` 从用户可选 profile 改为 `machine-context`，将用户级 Agent 资产发现改为只观察的 `asset-inventory`。
- **BREAKING** 移除 `work` 作为 profile 的语义，以 `project-defaults` 表示项目公共 Agent 能力。
- **BREAKING** 用显式组合替代混合继承链：`machine-context + project-defaults + role profile + runtime policy`。
- **BREAKING** 将 `add`、`mask`、`replace` 重命名并重定义为默认拒绝模型下的 `allow`、`deny`、`override`。
- **BREAKING** 将机器审批与项目装配绑定分为 `machine-context-pin` 和 `assembly-binding`，同步更新 lock、binding、命令、参数、错误和测试命名。
- **BREAKING** 将用户级状态根从 `$HOME/.cap-user-state` 迁移到 `$HOME/.agent-system-state`；旧路径只作为显式一次性迁移来源和隔离备份，不再长期兼容读取。
- 将持久 runtime 统一组织为 `runtimes/<client>/<runtime-id>/`，当前实施 `omp/default`，不创建或声称支持未验证的 Claude runtime。
- 新增 OMP runtime policy：用户全局默认、项目 policy 和可选 role override 按固定优先级合成，再投影到 OMP 临时 runtime。
- 将上下文压缩、advisor、预算等运行策略与 Agent 能力分离；OMP native `config.yml` 只作为 adapter/render 产物，不作为隐式 CAP 源头。
- 新增 external import 的显式来源、digest、审批和 profile 绑定语义；机器 inventory 不能自动授权项目能力。
- 记录 machine-context、asset-inventory、项目 lock、runtime policy、OMP generation、effective render 和 receipt 的可审计摘要，不记录 secret、token、endpoint、cookie、session 或 history 正文。
- 提供从旧 profile、旧状态根、旧 pin/binding 和旧 OMP runtime 的显式 dry-run/apply/quarantine 迁移流程。
- 为 Codex 和未来 Claude 保留 v3 adapter 合同与实施任务边界，但本变更只实现和验证 OMP。

## Capabilities

### New Capabilities

- `machine-context`: 描述经过批准的宿主运行上下文、pin、drift 和非 Agent 宿主底座。
- `asset-inventory`: 记录机器上发现的 Agent-facing 资产候选及其来源、状态和 digest，不授予能力使用权。
- `project-defaults`: 描述项目公共 Agent 能力的显式装配与默认拒绝边界。
- `runtime-policy`: 描述用户全局 runtime preference、项目覆盖、role override、client adapter 投影和 effective runtime 证据。
- `omp-runtime`: 描述 OMP runtime-id、持久状态、临时 render、配置隔离、压缩/advisor policy 和 receipt。
- `v3-migration`: 描述旧名称、路径、profile 继承、pin/binding 和 runtime 状态到 v3 的一次性迁移与隔离回滚边界。

### Modified Capabilities

- `profile-assembly`: 修改 profile schema、能力闭包、显式组合、allow/deny/override、external import 和用户可见 role 列表。
- `capability-profile-closure`: 修改闭包验证，使机器候选默认拒绝，并分别报告 machine-context、asset-inventory、capability plane、instruction plane 和 runtime policy。
- `client-rendering`: 修改 OMP render，使受控 runtime policy 投影到隔离的 native config，并将 effective settings 纳入 hash/receipt。

## Scope

### In scope

- v3 规范、schema、源文件路径、命令和状态对象设计。
- OMP 主路径的源代码、迁移器、render、lock/binding/verify、receipt 和行为验证。
- 资产记录的无 secret 摘要和 active/passive/unknown 证据状态。
- 为 Codex 和 Claude 后续实现定义不可歧义的 adapter contract、字段边界和非目标。

### Out of scope

- 本次实现 Codex runtime policy projection 或新增 Codex 能力。
- 本次实现或验证 Claude CLI；当前机器没有 Claude CLI，生效态保持 unknown。
- 把机器发现的能力自动导入任何 profile。
- 将用户认证、token、provider 账号、Git/SSH 或语言工具链纳入 Agent-facing capability closure。
- 长期兼容旧 `real-home`、`work`、`agent-home-root`、旧状态根或旧操作名称。

## Affected Profiles and Clients

- 受影响 profile：`general`、`assembly-helper` 以及未来所有 role profile；`real-home`、`work` 不再作为用户可选 profile。
- 本次实际客户端：OMP。
- 后续合同客户端：Codex CLI、Claude CLI；不在本次实现和生效验证范围内。

## Baseline Evidence

- 当前 `.cap/profiles/*.toml` 使用 `extends` 和 `add`/`mask`/`replace`；`real-home -> work -> role` 是现有技术链。
- 当前 OMP 用户级 runtime 位于 `$HOME/.cap-user-state/runtimes/omp/default`，启动时使用隔离的 `PI_CONFIG_DIR` 和 `PI_CONFIG_FILES`。
- 当前 OMP renderer 在 `src/agent_system/profile/cli.py` 中生成空的 `config.yml`，因此 ambient OMP settings 不是受控 CAP runtime policy 的可靠来源。
- 当前仓库已有 OMP runtime migration、lock、binding、render、probe/receipt 分层，但尚未有 v3 machine-context、asset-inventory 和 runtime-policy 语义。
- 当前 Claude CLI 未安装；仓库已有的 Claude 支持声明不构成实际 adapter 或生效态证据。

## Rollback Boundary

迁移器必须先 dry-run，比较旧状态与 v3 目标并停止于冲突、权限或 secret 边界不明确的情况。apply 成功并通过 v3 校验后，旧状态只移入隔离备份；不得删除旧状态，除非另有明确 cleanup 操作和用户授权。代码回滚恢复旧版本时只能读取明确保留的迁移备份，不能让旧路径重新成为 v3 的隐式运行来源。
