# Agent System assembly

本目录说明 `.cap` 中的 Agent role、prompt、Skill、能力闭包和验证证据。当前可运行 role：`general` 与 `assembly-helper`。

## v3 边界

v3 将以下输入面分开：

- `machine-context`：经 pin 批准的宿主底座摘要；不授予 Agent-facing 能力；
- `asset-inventory`：用户目录能力候选的观察面；默认不进入 closure；
- `project-defaults`：项目拥有或显式批准的公共能力；
- role profile：叶子角色的 prompt、能力增量和 runtime override；
- runtime policy：按 client/runtime-id 隔离的运行语义，不是 Skill、MCP、Hook、Plugin 或 prompt。

角色只使用 `allow`、`deny`、`override`。旧 `real-home`、`work`、`add`、`mask`、`replace` 不再是长期运行语义。未声明用户级 MCP/Skill/规则不会进入 OMP closure；`idea` 即使出现在 inventory 中，也只产生观察证据。

当前客户端注册表为 Codex、Qoder 和 OMP。Claude 没有本仓已验证的 adapter；其配置、运行和生效态保持 `unknown`，不得复用 OMP native config。

## 常用命令

```bash
uv run cap
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

`lock`、`assembly-bind`、`verify` 通过属于声明态或配置态；只有真实 OMP run、generation manifest、receipt 和 probe 才能提供生效态证据。

## OMP runtime

持久状态和 render CAS 位于：

```text
$HOME/.agent-system-state/runtimes/omp/default/
$HOME/.agent-system-state/renders/omp/<effective-hash>/
```

runtime 保存 Session、history、cache、agent.db 和认证；每次项目运行仍创建独立 render。`.cap/runtime/omp.toml` 当前只允许 `memory_backend = "off"` 和 `enable_project_mcp = false`；未知字段进入 evidence，但不猜测 native key。

系统策略固定为：系统安全门禁 > project policy > role override > `omp/default` 用户 preference。OMP adapter 输出 `config.yml`、`mcp.json`、隔离 system prompt 和 Skill allowlist，并固定关闭 ambient extensions/rules 与 project MCP discovery。

迁移不在启动时隐式执行：

```bash
uv run cap migrate-omp-runtime
uv run cap migrate-omp-runtime --apply
uv run cap migrate-omp-runtime --rollback
uv run cap migrate-omp-runtime --cleanup
```

`--rollback` 从显式 quarantine backup 恢复旧 runtime 并移除新 runtime；`--cleanup` 只删除已验证迁移留下的旧 project 状态和 backup。冲突、权限、secret 或 digest 不明确时保持旧状态不变。

## 装配助手合同

`assembly-helper` 用于审查和修改 Agent 装配源文件。它必须先恢复目标 Agent 合同、能力闭包和证据层；不得从用户目录、ambient MCP、模板、其他仓库或 provider 配置补齐业务能力。常驻 prompt 保持短约束，条件性流程使用项目内 Skill。

Codex 后续 adapter 必须独立声明支持的 runtime policy 字段、native 文件边界和 evidence ceiling。Claude 后续 adapter 必须在真实 CLI 可运行、render 可核验、probe 可观察后才接入；未满足条件时保持 unknown。

## OpenSpec

```bash
uv sync --locked
npm install
npx openspec validate --all --strict
```

OpenSpec proposal、design、spec 和 tasks 是变更包的审阅合同；应用代码、lock、binding 和 runtime evidence 必须按合同分别验证。
