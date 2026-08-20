> 方案审阅载体：[#81](https://github.com/zaurakworks/agent-system/issues/81)。阻断项 [#82](https://github.com/zaurakworks/agent-system/issues/82)（lock mode 跨平台缺陷）。关联 [#83](https://github.com/zaurakworks/agent-system/issues/83)（Windows ACL 校验缺口，不阻断）。
> 本规划包在负责人确认 #81 中的三项决定前**不构成实施授权**。

## Why

CAP 当前只有一个端到端实现的客户端 adapter：OMP。`src/agent_system/omp/runtime.py` 已经把「显式声明 → 能力闭包 → 隔离 render → generation manifest → 启动 → receipt」跑通，`.cap/lock.json` 中登记的 `codex`、`qoder` 只有 portable render，没有 effective render、没有 generation、没有 runtime policy 投影，也没有生效态证据。

Claude 是本仓负责人日常使用的主力客户端，但它现在处于最坏的一种状态：**既是 CAP 的观察对象，又不是 CAP 的客户端**。

- `src/agent_system/profile/cli.py` 已经把 `~/.claude`、`~/.claude.json`、`~/.claude-plugin`、`CLAUDE.md` 当成 ambient 污染面来检测（`GLOBAL_NATIVE_ROOTS`、`PROJECT_BYPASS_DIRS`、`_check_global_pollution` 中的 `.claude.json` 键集合 `{enabledPlugins, hooks, mcpServers, plugins, skills}`）；
- 但 `CLIENTS = ("codex", "qoder", "omp")` 不包含 `claude`，`cap use --cli claude` 不存在；
- 结果是：Claude 实际运行时读的是用户目录里的 ambient 配置，完全绕过 `.cap` 声明、lock、machine-context pin 和 assembly binding。仓库对这次运行没有任何可审计记录。

`openspec/changes/redesign-agent-system-v3-runtime-assembly` 已经明确把这件事留给后续实施者：design.md 决策 7 要求「Claude 后续实现必须消费同一套语义 policy，且自行生成 native projection；不得读取 OMP native files」，tasks 5.5／5.6 要求「明确 Claude adapter 的后续合同、未安装时的 unknown 边界」并「确保后续 Claude 实施者可仅凭变更包消费 v3 合同」。本变更就是兑现该合同。

## What Changes

- 新增 `claude` 为 CAP 一等客户端：`CLIENTS` 扩展为 `("codex", "qoder", "omp", "claude")`，`cap show/render/use/run --cli claude` 可用。
- 新增 Claude adapter，采用与 OMP **同构的 Render 模型**：portable render → effective render（generation CAS）→ 校验 → 启动 → receipt。
- 新增 Claude generation 输出：`.cap-generation.json` + `claude-config.yaml` + `skills/` 副本，以及由 `claude-config.yaml` 投影出的 Claude native 文件。
- 新增 `.cap/runtime/claude.toml` 语义 runtime policy，与 `.cap/runtime/omp.toml` 平行，遵循同一固定合成顺序。
- 新增三层证据在 Claude 上的落地：声明态（`.cap` 源）、配置态（lock/pin/binding/generation/effective_hash）、生效态（真实进程 receipt 与 probe），且生效态在无法证明时保持 `unknown` / `reported_client_limited`。
- 新增三个 Hash 的 Claude 侧定义与校验：`portable_tree_hash`、`effective_render_hash`、generation manifest 的 `content_digest`。
- 将 Claude 的 capability 闭包（Skills / MCP / Hooks / Plugins）从「用户目录发现」改为「render 目录显式提供 + ambient 关闭」。
- **BREAKING**（对 Claude 使用方式而言）：经 CAP 启动的 Claude 不再隐式加载用户级 Skills、MCP、Hooks、Plugins、subagents 和用户级 `CLAUDE.md`；这些资产只作为 asset-inventory 观察项，需显式 `allow` 或 external import 才进入闭包。CAP 之外直接运行的 `claude` 不受影响。

## Capabilities

### New Capabilities

- `claude-runtime`：Claude runtime-id、持久状态、隔离 render/generation、三 Hash、启动门禁、receipt 与 evidence ceiling。
- `claude-surface-closure`：Claude 的 Skill／MCP／Hook／Plugin／instruction 面如何从 CAP 闭包映射到 Claude native 表面，以及 ambient 面的关闭与观察边界。

### Modified Capabilities

- 无。本变更不修改 `client-rendering`、`capability-profile-closure` 等 v3 能力的既有需求；Claude 侧的对应约束以新增 capability 表达，避免在 v3 change 归档前产生跨 change 的 MODIFIED 依赖。

## 推荐方案

**采用 Render 模型，与 OMP adapter 严格同构。**

Claude adapter 的核心流程与 OMP 完全一致，只在「native 投影层」分叉：

```text
cap use <role> --cli claude
  → profile engine materialize --client claude --output <tmp>   # portable render，产出 tree_hash
  → 读取 .cap/runtime/claude.toml + 用户 preference           # 语义 runtime policy 合成
  → 计算 source_context / source_digest / effective_render_hash
  → CAS 命中或原子物化 $HOME/.agent-system-state/renders/claude/<effective-hash>/
  → 写入 .cap-generation.json（含 content_digest）
  → 校验 generation：metadata 未漂移 + content_digest 未漂移
  → 投影 claude-config.yaml → native/{settings.json, mcp.json, plugin/}
  → 只读引用 generation 启动：--settings / --mcp-config --strict-mcp-config
                              / --plugin-dir / --setting-sources "" / --append-system-prompt
     CLAUDE_CONFIG_DIR 指向 runtimes/claude/<id>/（只承载认证与会话）
  → cap verify + 运行后 content_digest 复查 + 写 receipt.json
```

被否决的替代方案：

1. **就地改写用户 `~/.claude`（Mutate 模型）**。实现最快，但破坏可复现性（无法并发、无法回滚、无法审计「这次运行到底用了什么」），并且直接违反 `.cap` 唯一权威与「不把用户目录当运行时来源」的产品政策。不采用。
2. **只做只读检查器（Inspect-only）**。仅报告 Claude ambient 配置是否越权，不接管启动。它不能让 Claude 成为一等客户端，负责人日常仍在无审计路径上运行。不采用，但其检测逻辑作为本方案的 ambient 门禁复用。
3. **复用 OMP 的 `config.yml` 作为 Claude 输入**。v3 design 决策 7／8 已明令禁止；不同客户端的 native schema 不得互相污染。不采用。
4. **通过 Claude Agent SDK 内嵌运行，不走 CLI**。SDK 路径不能覆盖负责人在 IDE 与 Web 上的实际使用，且把 CAP 变成运行时框架而非装配器。不采用为主路径；SDK 作为「API 形态」的可选消费者，只消费 generation 目录，不获得独立的 render 语义。

## 设计决策与理由

| 决策 | 内容 | 理由 |
| --- | --- | --- |
| D1 | Claude adapter 使用 Render 模型 | 与 OMP 同构，可复用 `_tree_digest`、`_digest_json`、CAS 原子物化、generation 校验与 receipt 结构，减少语义分叉 |
| D2 | generation 中间产物为 `claude-config.yaml` | 它是 **CAP 自己的 adapter 中间态**，不是 Claude native 格式。native 是 JSON；用 YAML 中间态可以强制「投影」这一步存在，防止有人把 CAP 源 schema 和 Claude native schema 混为一谈 |
| D3 | `skills/` 在 generation 内是副本而非 symlink | `_tree_digest` 显式拒绝 symlink 和 hard link；副本才能被 `content_digest` 覆盖，也才能在 Windows 上无需开发者模式运行 |
| D4 | 三个 Hash 语义与 OMP 一字不差 | `portable_tree_hash` = 跨客户端可复现的声明产物；`effective_render_hash` = generation 目录名与 CAS key；`content_digest` = 落盘后防篡改。三者职责不同，不合并 |
| D5 | Claude 的 runtime policy 单独放 `.cap/runtime/claude.toml` | 与 `omp.toml` 平行；未验证字段保留在 policy evidence 中但不投影，禁止猜测 native key（沿用 v3 tasks 3.7） |
| D6 | 生效态默认 `unknown` | Claude 的 MCP／Hook／Plugin 实际加载结果不一定可从进程输出证明。配置态通过不得升级为生效态通过（沿用 v3 `capability-profile-closure`） |
| D7 | Web 形态不产生生效态 | Claude Web 不消费本地 generation 目录，CAP 只能提供可粘贴的声明态产物，evidence level 封顶在声明态 |
| D8 | ambient 关闭优先于 allowlist | 先确保用户级 Skills／MCP／Hooks／Plugins／memory 不进入进程，再由 render 显式提供；顺序反过来会留下 fail-open 缺口 |

## 权衡分析

**实现难度 vs 设计一致性** —— 本变更明确选择一致性。

- 一致性收益：Claude 与 OMP 共用同一套心智模型、同一套证据字段、同一套故障排查路径（`cap show <role> --cli claude` 与 `--cli omp` 输出结构相同）。维护者不需要记两套语义。
- 代价：Claude 的 native 表面比 OMP 分散（settings JSON、MCP JSON、skills 目录、agents 目录、hooks 内联在 settings、plugins 走 marketplace），投影层比 OMP 的「一个 `config.yml` + 一个 `extension/.mcp.json`」复杂，且部分隔离能力受客户端支持程度限制。
- 缓解：把复杂度全部收敛在 `_project_claude_native()` 一个函数内；投影不了的字段进 `unsupported` 列表并出现在 receipt，而不是静默丢弃。

**隔离强度 vs 可用性**

- 完全隔离会切断负责人已有的 Claude 登录态与会话历史。因此沿用 OMP 的分层：**认证与会话属于 runtime 状态**（`runtimes/claude/<runtime-id>/`，跨项目共享、不参与能力闭包），**能力与指令属于 render**（每次运行独立、参与 hash）。
- 风险：如果 Claude 把某些能力（如已启用 plugin 列表）与认证态存在同一个文件里，runtime 与 render 的边界会被打穿。对策见 design-spec「运行时状态与能力面分离」，并在实现任务中作为门禁项显式验证。

**跨平台**

- Windows 是本仓主力开发平台。generation 路径为 `$HOME/.agent-system-state/renders/claude/<64 位 hex>/native/plugin/skills/…`，比 OMP 更深，有触发 260 字符限制的风险；POSIX 权限位（`0o700` / `0o600`）在 Windows 上是 no-op，`os.geteuid` 不存在。OMP 侧的 `_validate_private_runtime` 已有 `hasattr(os, "geteuid")` 分支，Windows 上改以「必须位于 CAP 管理根内 + 路径链无 symlink/junction」作为等价保证，Claude 侧沿用同一策略，并额外要求长路径预检。

**范围克制**

- 本变更不实现 Claude 的 hooks 投影与 plugins 投影的完整语义，只实现「声明存在即 fail-closed 报错或显式 unsupported」。当前 `.cap` 中 hooks／plugins 闭包均为空（见 `.cap/lock.json` 的 `inventory`），没有可验证的真实用例；按仓库规则不为未证明的需求写实现。

## Scope

### In scope

- `claude` 客户端注册、CLI 参数、TUI 与 `cap show/render/use/run` 支持。
- `src/agent_system/claude/runtime.py`：render、generation CAS、三 Hash、native 投影、env 清洗、启动、receipt。
- `.cap/runtime/claude.toml` 语义 policy schema 与合成顺序。
- Claude ambient 面的 fail-closed 门禁与 asset-inventory 归类。
- Skills 与 MCP 的闭包投影（当前仓库唯一有真实用例的两类）。
- 单元测试、隔离行为测试、跨平台路径测试，以及 `docs/profile.md`、`docs/cap-guide.zh-CN.md`、`docs/maintenance.zh-CN.md` 的中文更新。

### Out of scope

- 不实现 Hooks／Plugins 的完整 native 投影（保持 fail-closed + `unsupported` 记录）。
- 不实现 Claude Web 的自动化装配；只产出可人工消费的声明态产物。
- 不改动 OMP adapter 的既有行为；仅在必要处把公共逻辑上提为共享模块。
- 不把用户级 `~/.claude` 中发现的任何资产自动导入任一 profile。
- 不实现 Codex／Qoder 的 effective render（它们仍只有 portable render）。
- 不接管 Claude 的认证、token、订阅或 provider 账号。

## Affected Profiles and Clients

- 受影响 role：`general`、`agent-assembler`（两者都将获得 `--cli claude` 路径；能力闭包不变）。
- 新增客户端：`claude`。
- 不受影响客户端：`omp`（主力，行为不变）、`codex`、`qoder`（仍只有 portable render）。

## Baseline Evidence

- `src/agent_system/omp/runtime.py:1180` `_materialize_profile_generation`：已验证的 portable→effective render 与 CAS 物化流程，本变更的直接模板。
- `src/agent_system/omp/runtime.py:1141` `_verify_profile_generation`：generation manifest（`version: 2`）与 `content_digest` 的漂移门禁。
- `src/agent_system/omp/runtime.py:1104` `_generation_source_context`：`profile` / `layer_digest` / `effective_digest` / `portable_tree_hash` / `adapter_version` 五元组，Claude 侧字段结构相同。
- `src/agent_system/omp/runtime.py:1422` `_write_receipt`：receipt `version: 4` 字段集合。
- `src/agent_system/cap/config.py:47` `CLIENTS = ("codex", "qoder", "omp")`：当前 Claude 不是客户端的直接证据。
- `src/agent_system/profile/cli.py:3272` `_check_global_pollution` 与 `:3291` `.claude.json` 键集合：Claude ambient 面已被识别为污染源但未被接管的直接证据。
- `.cap/lock.json`：`clients` 仅含 `codex`／`omp`／`qoder`，`adapter_version: 8`；`capability_semantics` 定义 `skills: native-staging`、`mcp: native-config`、`hooks/plugins: opaque-staging`。
- `openspec/changes/redesign-agent-system-v3-runtime-assembly/design.md` 决策 7、8 与 `tasks.md` 5.5／5.6：本变更的授权与合同来源。
- `docs/profile.md`「Adapter 合同」章节：Claude 未实施时必须报告 `unknown`、不得复用 OMP native config 的既有约束。

**一手来源要求（已履行）**：Claude native 配置面已针对 **Claude Code 2.1.236 / win32-x64** 完成逐项核对与受控实验，结论记录在 `evidence/claude-native-surface.json`（18 条 fact，含证据原文）。实验在隔离的 scratchpad 中进行，未修改用户真实 `~/.claude`。

## T-1 实测结论对本提案的修正

核对推翻了初稿的一个核心假设，并暴露了两条初稿完全没有预见的 ambient 面：

| # | 初稿假设 | 实测结论 | 影响 |
| --- | --- | --- | --- |
| 1 | Skill 必须放进可写的 `CLAUDE_CONFIG_DIR`，因此需要一个「水合层」 | **`--plugin-dir` 可 session 级只读交付 Skill**（日志实证：`Loaded 1 session-only plugins from --plugin-dir` → `Loaded 1 skills from plugin`） | **水合层整体取消**。generation 与 OMP 一样被只读引用，设计复杂度和工作量各降一档 |
| 2 | 认证位置未知，是最高风险 | **认证随 `CLAUDE_CONFIG_DIR` 迁移**（重定向后 `Not logged in · Please run /login`） | 落在预设的中间情形：CAP runtime 内登录一次，跨项目共享。风险出清 |
| 3 | `~/.claude.json` 不可重定位，是 ambient 泄漏面 | **它随 `CLAUDE_CONFIG_DIR` 迁移** | ambient 面缩小 |
| 4 | （未预见） | **claude.ai 账号级远程 MCP connector 会被拉取，且 `--strict-mcp-config` 压不住** | 新增最高风险项；产生下方的认证模式抉择 |
| 5 | （未预见） | **Claude Code 自带 42 个 bundled skills，不受本地配置控制** | 新增一条不可控能力底座 |

另修正两处硬错误：`permission_mode` 不存在 `default` 取值（合法值为 `acceptEdits`/`auto`/`bypassPermissions`/`manual`/`dontAsk`/`plan`）；`CLAUDE_CODE_DISABLE_AUTO_MEMORY` 不存在于 CLI 面。

## 需要负责人决定的事项

### 决定 1：认证模式默认值 —— ✅ 已确认：订阅 OAuth（2026-08-19，[决定记录](https://github.com/zaurakworks/agent-system/issues/81#issuecomment-5349961040)）

T-1 证明 CAP 管理下的 Claude 必须在两种模式间取舍，二者的 MCP 闭包可控性不同：

| | A. 订阅 OAuth（建议默认） | B. `--bare` + API key |
| --- | --- | --- |
| 认证 | CAP runtime 内登录一次 | `ANTHROPIC_API_KEY` 或 `apiKeyHelper` |
| claude.ai 远程 connector | **加载，CAP 不可控** | 不拉取 |
| hooks / auto-memory / CLAUDE.md 自动发现 | 需逐项关闭 | `--bare` 一并关闭 |
| MCP 闭包生效态 | 只能记 `reported_client_limited` | 可接近 `observed` |
| 成本 | 用现有订阅 | 单独 API 计费 |

**负责人已选定 A（订阅 OAuth）**。`.cap/runtime/claude.toml` 的 `auth_mode` 默认 `"subscription"`；`"bare"` 保留为可选值（成本只是一个 flag，且它是唯一能真正闭合 MCP 的路径）。该字段纳入 `effective_render_hash` 与 receipt。

**该决定的直接后果**：`subscription` 模式下 `effective_observations.mcps` **强制**为 `reported_client_limited`，`ambient_floor.claudeai_connector_count` 只记数量。CAP 在文档与 receipt 中**不得**声称已闭合 Claude 的 MCP 面。

### 决定 2：是否先修 lock 的跨平台缺陷 —— ✅ 已确认：先修（2026-08-19，[决定记录](https://github.com/zaurakworks/agent-system/issues/81#issuecomment-5349961040)），且已实施

实施本变更时发现一个**与 Claude 无关的既有缺陷**：`.cap/lock.json` 的 `inputs.*.mode` 用平台相关的 `S_IMODE` 记录（Linux `0644` / Windows `0666`），导致 lock 在两平台间翻转。**在 Windows 上，66 个 profile 测试有 65 个因此失败**（在干净 `git HEAD` 上同样失败）。CI 全部 `runs-on: ubuntu-latest`，其 smoke 步骤执行 `cap show general` / `cap show agent-assembler`，而 `cap show` 会校验 lock —— 因此 Windows 生成的 lock 若被提交，Linux CI 会直接失败。

它阻断本变更「lock 中其他客户端 hash 不变」这一验收标准的判读。**已按负责人决定先行修复并验证**：Windows 上 `cap lock` 现在产出与 Linux 提交版逐字节一致的 lock。详见 `tasks.md` 任务 0.1 与 [#82](https://github.com/zaurakworks/agent-system/issues/82)。

### 决定 3：证据天花板的表述 —— ✅ 已确认：照写不弱化（2026-08-19，[决定记录](https://github.com/zaurakworks/agent-system/issues/81#issuecomment-5349961040)）

Claude 存在三层 CAP 无法接管的能力底座（managed policy、42 个 bundled skills、订阅模式下的 claude.ai connector），而 OMP 一层都没有。负责人已确认把这一事实**原样**写进 `docs/profile.md` 的 Adapter 合同章节，不作弱化表述。对应 `design-spec.md` 5.2 结尾的定稿句子与任务 6.1。

## Success Criteria

1. `uv run cap show general --cli claude` 输出与 `--cli omp` 结构同构，包含 `portable_tree_hash`、`effective_render_hash`、`global_generation`、`project_source_context`、`project_source_digest`、`skills`。
2. `uv run cap render general --cli claude --output <empty-dir>` 产出确定性目录；同一输入两次运行 `tree_hash` 一致。
3. generation 目录含 `.cap-generation.json`、`claude-config.yaml`、`skills/`；手工修改 generation 内任一文件后再次启动必须 fail-closed 报「content drifted」。
4. `.cap/runtime/claude.toml` 中任一投影字段变化，`effective_render_hash` 必变，且旧 generation 不被命中。
5. 隔离验证：在用户 HOME 放置一个 active 的用户级 Claude Skill／MCP 声明，经 CAP 启动的 Claude 进程的有效闭包中不出现该资产；`cap verify` 将其归入 asset-inventory 而非 effective inventory。
6. receipt 写出且不含 token、cookie、endpoint secret、会话正文或转发参数值；只记录 `forwarded_argument_count`。
7. 生效态诚实：无法从真实进程证明的项在 receipt 中为 `unknown` 或 `reported_client_limited`，不存在由「文件已生成」推断出的 confirmed 结论。
8. Windows／macOS／Linux 三平台上 `cap render --cli claude` 与 generation 校验通过；Windows 上不依赖 symlink 与开发者模式。
9. `uv run cap skills-validate`、`uv run cap lock`、`uv run cap verify`、`npx openspec validate add-claude-cap-adapter --strict --json` 全部通过。
10. OMP 回归：全部既有 OMP 测试通过，`.cap/lock.json` 中 OMP 的 `tree_hash` 不因本变更改变。

## Rollback Boundary

- Claude adapter 是**纯新增**路径。回滚 = 从 `CLIENTS` 移除 `claude` 并删除 `src/agent_system/claude/`；OMP 主路径不受影响。
- `.cap/runtime/claude.toml` 与 lock 中的 `clients.claude` 条目在回滚时一并移除，需重新执行 `uv run cap lock` 与 `assembly-bind`。
- generation CAS 位于 `$HOME/.agent-system-state/renders/claude/`，是可重建的派生产物，回滚时可直接删除，不需要备份。
- `runtimes/claude/<runtime-id>/` 含认证与会话状态，**不得**在回滚中删除；只允许停止使用。
- 本变更不迁移、不改写、不删除用户已有的 `~/.claude`、`~/.claude.json` 或 `~/.claude-plugin`；它们始终只读观察。若实现过程中出现任何需要写入用户 Claude 目录的需求，必须停止并升级，不得自行扩大授权。
