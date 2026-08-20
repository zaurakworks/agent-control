# profile —— v3 装配、运行策略与证据

`uv run cap` 是唯一用户入口。profile engine 只作为 CAP 内部执行层。v3 将宿主上下文、资产观察、项目默认能力、叶子 role 和 client runtime policy 分开；`general` 与 `agent-assembler` 是当前可运行的叶子 role。当前实现并验证 OMP adapter，Codex/Claude 只消费后续合同，不共享 OMP native 配置。

## 源模型

```text
AGENTS.md
.cap/manifest.toml
.cap/project-defaults.toml
.cap/skill-imports.toml                 # 可选：仓内唯一 Skill source 声明
.cap/profiles/<role>.toml
.cap/prompts/<role>.md
.cap/capabilities/{skills,mcp,hooks,plugins}/...
plugins/<plugin>/skills/<skill>/...     # manifest 明示时可作 Skill source
.cap/runtime/omp.toml
.cap/lock.json

$HOME/.agent-system-state/machine-context/manifest.json
$HOME/.agent-system-state/machine-context/pin.json
$HOME/.agent-system-state/bindings/<role>.binding.json
```

- `machine-context`：已批准宿主底座摘要和 drift 输入，不授予 Agent-facing 能力。
- `asset-inventory`：对用户目录候选的只读观察，默认不进入 closure。
- `project-defaults`：项目拥有或显式批准的公共能力。
- `project Skill import`：可选的仓内唯一 Skill source；必须位于项目根内、非 symlink、被 role 引用并纳入 lock/render。
- `role profile`：prompt、角色能力增量和可选 runtime override。
- `runtime policy`：client/runtime-id 的语义 preference；不属于 Skill、MCP、Hook、Plugin 或 prompt。

角色 profile 使用 `allow`、`deny`、`override`；未知字段、未批准 external import 和观察到但未声明的资产默认 fail-closed。旧 `real-home`、`work`、`add`、`mask`、`replace` 不是 v3 长期运行 API。

## Runtime policy

`.cap/runtime/omp.toml` 只声明已验证的 OMP 语义字段：

```toml
version = 1
client = "omp"

[policy]
shared_preference_source = "omp-user"
memory_backend = "off"
enable_project_mcp = false
```

合成顺序固定为：系统安全门禁 > project policy > role override > 普通 OMP 用户 preference。`omp-user` 只投影模型角色、`extendedContext`、thinking/tier、advisor、theme、status line、composer 与显示字段；MCP、Skill、Hook、Plugin、extension、工具审批、路径和 memory 不得从该 source 进入 CAP native config。共享 preference 的摘要与 allowlist 版本参与 OMP generation；值变更后旧 generation 不得作为当前命中。

Provider endpoint 与认证只允许由明确批准的私有 source adapter 在启动期注入。API key、OAuth token、cookie、broker token 与完整 secret 配置不得进入 portable render、lock、binding、generation、receipt 或日志。配置态只证明投影正确；未执行真实客户端请求时，provider、advisor 与模型行为保持 unknown。

## 命令

```bash
uv run cap profiles
uv run cap agents
uv run cap show agent-assembler
uv run cap show agent-assembler --cli omp
uv run cap skills-validate
uv run cap lock
uv run cap assembly-bind general
uv run cap assembly-bind agent-assembler
uv run cap verify
uv run cap render agent-assembler --cli omp --output <existing-empty-dir>
uv run cap run agent-assembler --cli omp -- --help
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
- 生效态：真实客户端 run、generation manifest、receipt 和 probe。OMP 与 Claude 各有独立的 generation 与 receipt；Claude 的天花板见下方 Adapter 合同。

receipt 关联 `runtime_id`、policy/effective digest、source context、generation、portable tree hash、effective render hash、exit code 和 runtime policy evidence；不记录 token、cookie、endpoint secret、Session/history 正文或命令参数值。文件存在或 lock 通过不能冒充客户端生效。

## Adapter 合同

Codex adapter 后续必须从 v3 role、project-defaults、runtime policy、pin、binding 和 external import closure 独立投影自己的 native 文件，声明支持字段、adapter version 和 evidence ceiling；不得读取 OMP `config.yml`。

Claude adapter 已实施，与 OMP 同构：portable render → runtime policy 合成 → native 投影 → effective render hash → 内容寻址 generation → 启动 → receipt。它自行投影 `native/settings.json`、`native/mcp.json` 与 `native/plugin/`，不读取 OMP `config.yml`。

`.cap/runtime/claude.toml` 的 `login_mode` 选择认证方式，默认 `subscription`。该字段的名字刻意避开 secret 遮蔽正则：`.cap/runtime/*.toml` 是 lock 输入且在哈希前会被遮蔽，取一个含 `auth`／`token`／`secret` 的名字会让两个不同取值哈希相同，从而使 `cap verify` 对它失效。

### Claude 的证据天花板

**Claude 存在三层 CAP 无法接管的能力底座，而 OMP 一层都没有：**

- **管理层配置**（`C:\Program Files\ClaudeCode\managed-settings.json` 等）始终加载，`--safe-mode` 亦声明 policy settings 仍生效；
- **42 个 bundled skills** 由客户端自带，不受任何本地配置控制；
- **claude.ai 账号级远程 MCP connector**（仅 `subscription` 模式）从 `api.anthropic.com/v1/mcp_servers` 拉取，不来自任何本地文件，`--strict-mcp-config` 压不住——已两次独立复现。

因此 CAP 对 Claude 的隔离声明上限是：**CAP 控制了用户级与项目级的声明能力面；自带 Skill、企业 managed 层，以及订阅模式下的账号级 connector 不在 CAP 控制范围内。**

`subscription` 模式下 receipt 的 `effective_observations.mcps` 恒为 `reported_client_limited`，实现中不存在把该维度提升为 `observed` 的路径。`hooks`、`plugins`、`bundled_skills` 同样恒为 `reported_client_limited`；本 adapter 没有逐项 probe，因此 `evidence.effective` 保持 `unknown`，不由启动期观察升级。

### 认证与用户目录边界

Claude 的认证随 `CLAUDE_CONFIG_DIR` 迁移。CAP 把该变量指向自己的 `runtimes/claude/<runtime-id>/`，因此**首次在 CAP 下使用需要单独登录一次**；此后凭据留在 CAP 的 runtime 内，跨项目共享。

CAP 对用户自己的 `~/.claude`、`~/.claude.json` 与 `~/.claude-plugin` **既不读、也不写、也不迁移**。

### 未支持的能力类别

hooks 与 plugins 尚未投影。为 Claude 声明这两类能力会**失败关闭**，而不是渲染出一棵静默缺少该能力的树。
