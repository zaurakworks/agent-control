# profile —— v3 装配、运行策略与证据

`uv run cap` 是唯一用户入口。profile engine 只作为 CAP 内部执行层。v3 将宿主上下文、资产观察、项目默认能力、叶子 role 和 client runtime policy 分开；`general` 与 `assembly-helper` 是当前可运行的叶子 role。当前实现并验证 OMP adapter，Codex/Claude 只消费后续合同，不共享 OMP native 配置。

## 源模型

```text
AGENTS.md
.cap/manifest.toml
.cap/project-defaults.toml
.cap/profiles/<role>.toml
.cap/prompts/<role>.md
.cap/capabilities/{skills,mcp,hooks,plugins}/...
.cap/runtime/omp.toml
.cap/lock.json

$HOME/.agent-system-state/machine-context/manifest.json
$HOME/.agent-system-state/machine-context/pin.json
$HOME/.agent-system-state/bindings/<role>.binding.json
```

- `machine-context`：已批准宿主底座摘要和 drift 输入，不授予 Agent-facing 能力。
- `asset-inventory`：对用户目录候选的只读观察，默认不进入 closure。
- `project-defaults`：项目拥有或显式批准的公共能力。
- `role profile`：prompt、角色能力增量和可选 runtime override。
- `runtime policy`：client/runtime-id 的语义 preference；不属于 Skill、MCP、Hook、Plugin 或 prompt。

角色 profile 使用 `allow`、`deny`、`override`；未知字段、未批准 external import 和观察到但未声明的资产默认 fail-closed。旧 `real-home`、`work`、`add`、`mask`、`replace` 不是 v3 长期运行 API。

## Runtime policy

`.cap/runtime/omp.toml` 只声明已验证的 OMP 语义字段：

```toml
version = 1
client = "omp"

[policy]
memory_backend = "off"
enable_project_mcp = false
```

合成顺序固定为：系统安全门禁 > project policy > role override > `omp/<runtime-id>` 用户 preference。未验证字段保留在 policy evidence 中，但不猜测 OMP native key。当前 adapter 将 `memory_backend` 和 `enable_project_mcp` 投影到隔离 `config.yml`；未知的 advisor、预算和压缩键保持未接入。

## 命令

```bash
uv run cap profiles
uv run cap agents
uv run cap show assembly-helper
uv run cap show assembly-helper --cli omp
uv run cap skills-validate
uv run cap lock
uv run cap assembly-bind general
uv run cap assembly-bind assembly-helper
uv run cap verify
uv run cap render assembly-helper --cli omp --output <existing-empty-dir>
uv run cap run assembly-helper --cli omp -- --help
```

启动前必须通过项目 lock、machine-context pin、assembly binding、asset closure、runtime policy 和 generation 校验。OMP 启动固定使用 `--no-extensions`、`--no-rules`、Skill allowlist、隔离 `PI_CONFIG_FILES` 和认证/ambient credential 清理。`config.yml`、`mcp.json` 等 native 文件名只属于 adapter 输出。

## OMP 状态与迁移

持久状态根为：

```text
$HOME/.agent-system-state/runtimes/omp/default/
$HOME/.agent-system-state/renders/omp/<effective-hash>/
```

runtime 保存用户 Session、history、cache、agent.db 和认证；每次项目运行仍生成独立 CAS render。项目 capability closure 不从 runtime 反向发现，render 不修改 runtime 的认证或历史。

迁移必须显式执行，不在普通启动中隐式迁移：

```bash
uv run cap migrate-omp-runtime
uv run cap migrate-omp-runtime --apply
uv run cap migrate-omp-runtime --rollback
uv run cap migrate-omp-runtime --cleanup
```

`--rollback` 从显式 quarantine backup 恢复旧 runtime 并移除新 runtime；`--cleanup` 只删除已验证迁移留下的旧 project 状态和 backup。冲突、权限、secret 或 digest 不明确时停止并保持旧状态不变。

## 证据分层

- 声明态：manifest、project-defaults、role、prompt、capabilities、runtime policy。
- 配置态：lock、machine-context pin、binding、generation、render hash。
- 生效态：真实 OMP run、generation manifest、receipt 和 probe。

receipt 关联 `runtime_id`、policy/effective digest、source context、generation、portable tree hash、effective render hash、exit code 和 runtime policy evidence；不记录 token、cookie、endpoint secret、Session/history 正文或命令参数值。文件存在或 lock 通过不能冒充客户端生效。

## Adapter 合同

Codex adapter 后续必须从 v3 role、project-defaults、runtime policy、pin、binding 和 external import closure 独立投影自己的 native 文件，声明支持字段、adapter version 和 evidence ceiling；不得读取 OMP `config.yml`。

Claude adapter 当前未实施、未安装或未观察到时必须报告 `unknown`，不得生成虚假的生效证据，也不得复用 OMP native config。只有真实 CLI、隔离 render、运行 probe 和 receipt 全部可核验后，才能提升 evidence level。
