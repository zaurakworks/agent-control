# Claude CAP Adapter 设计说明

本文件是 `add-claude-cap-adapter` 的设计文档（OpenSpec design 工件）。背景与授权见 `proposal.md`，与 OMP 的实现差异与集成点见 `delta-specs.md`，执行顺序见 `tasks.md`。

## Context

CAP 当前有两层渲染，但只有一层是跨客户端的：

- **portable 层**（`src/agent_system/profile/cli.py`）：`materialize_profile()` 把 role、project-defaults、能力闭包渲染成一棵与客户端相关但与机器无关的文件树，产出 `tree_hash`。`codex`、`qoder`、`omp` 都有这一层。
- **effective 层**（`src/agent_system/omp/runtime.py`）：`_materialize_profile_generation()` 把 portable 树 + runtime policy + 机器绑定合成 generation，落进 CAS，产出 `effective_render_hash` 和 `.cap-generation.json`。**只有 OMP 有这一层**。

Claude adapter 必须同时补齐这两层。这是本设计的第一性约束：**Claude 不是在 OMP 旁边加一个分支，而是要成为第二个走完全程的客户端。**

第二个约束来自 Claude 本身：与 OMP 不同，Claude Code **没有单一的 `--config <file>` 入口**。它的配置面分散在 settings 层级、config 目录、MCP 文件、skills 目录、agents 目录、plugin marketplace 和 managed policy 上，并且其中一部分（managed settings）在任何情况下都会加载。这决定了 Claude 的隔离强度和证据天花板都低于 OMP，设计必须诚实表达这一点，而不是假装等价。

> **一手来源纪律**：本文中出现的所有 Claude native 文件名、环境变量、CLI flag 和 settings key 都必须在 `evidence/claude-native-surface.json` 中留证。T-1 已针对 Claude Code **2.1.236 / win32-x64** 完成核对与受控实验，本文已按实测结论定稿；仍标注「待核对」的少数项目（settings 中 auto-memory 的具体键名、hooks 形状、SDK 选项名）**不在本变更的实现范围内**，若将来触及必须先补齐核对。任何未留证的 native 键都不得进入代码。

## Goals / Non-Goals

**Goals**

- 让 Claude 成为与 OMP 结构同构的一等 CAP 客户端：同样的命令、同样的证据字段、同样的故障模式。
- 建立 Claude 的 `portable_tree_hash` / `effective_render_hash` / `content_digest` 三 Hash 闭环。
- 建立 generation（不可变、只读引用、可校验）与 runtime（可写、含认证与会话）的清晰分层。
- 把 Claude 的 ambient 面从「隐式运行时来源」降级为「只读观察对象」，并在无法证明隔离时 fail-closed 或诚实标记 `unknown`。
- 明确 Web / IDE / API 三种形态各自能达到的证据等级上限。

**Non-Goals**

- 不实现 Hooks / Plugins 的完整 native 投影（当前无真实用例，保持 fail-closed + `unsupported`）。
- 不为 Claude Web 提供自动化装配。
- 不接管 Claude 的认证、订阅或 provider 账号。
- 不修改用户已有的 `~/.claude`、`~/.claude.json`、`~/.claude-plugin`。
- 不把 CAP 变成 Agent 运行时框架；SDK 形态只是 generation 的消费者。

## 1. 架构概览：Claude adapter 在 CAP 中的位置

```text
                      .cap/ （唯一权威声明）
   manifest.toml · project-defaults.toml · profiles/<role>.toml
   prompts/<role>.md · capabilities/{skills,mcp,hooks,plugins}/
   runtime/omp.toml · runtime/claude.toml        ← 本变更新增
   lock.json                                      ← 新增 clients.claude
                              │
                              ▼
        ┌──────────── profile engine（portable 层，共享）────────────┐
        │  load_project → _desired_lock → _verify_lock               │
        │  → _select_profile → _render_tree(client) → _tree_hash     │
        └────────────────────────────────────────────────────────────┘
             │ client=omp                        │ client=claude ← 本变更新增分支
             ▼                                   ▼
   omp/runtime.py（effective 层）        claude/runtime.py（effective 层，新增）
   generation CAS                        generation CAS
   renders/omp/<effective_hash>/         renders/claude/<effective_hash>/
             │                                   │
             ▼                                   ▼
   omp --config … --extension …          claude --settings/--mcp-config/--plugin-dir
   runtimes/omp/<id>/                    runtimes/claude/<id>/
             │                                   │
             └───────────► receipt.json ◄────────┘
                    （统一证据格式，client 字段区分）
```

三类输入的职责不变，Claude 只是新增一个消费者：

| 输入面 | 是否参与 Claude 闭包 | 说明 |
| --- | --- | --- |
| `machine-context` + pin | 是（作为绑定前置） | 只描述宿主底座，不授予能力 |
| `asset-inventory` | 否 | `~/.claude/**` 只作为观察项；不 allow 就不进闭包 |
| `project-defaults` + role profile | 是 | 能力与 prompt 的唯一来源 |
| `runtime policy`（`.cap/runtime/claude.toml`） | 是（不授予工具） | 只投影已验证的语义字段 |
| external imports | 是（需显式批准 + digest 匹配） | 沿用 `_validate_external_imports` |

## 2. Render 设计

### 2.1 portable render（profile engine 层）

新增 `client = "claude"` 分支。输出树刻意**与 OMP 保持相同的抽象结构**，把客户端差异全部推迟到 effective 层：

```text
<output>/
  claude-config.yaml     # CAP adapter 中间态（非 Claude native），portable 部分
  mcp.json               # 与 _omp_mcp 同结构：{"mcpServers": {name: {command,args,env,type:"stdio"}}}
  system-prompt.md       # role prompt chain 拼接结果
  skills/<skill>/…       # .cap/capabilities/skills/<skill>/** 的完整副本（含 SKILL.md）
```

设计要点：

- `claude-config.yaml` 在 portable 阶段是**空对象 `{}`**，与 OMP 的 `config.yml` 一致（`_render_tree` 中 OMP 分支写入字面量 `b"{}\n"`）。真实内容在 effective 阶段由 policy 合成后写回。这样 portable `tree_hash` 只反映声明态，不被机器 preference 污染。
- **不在 portable 层生成任何 Claude native 文件**（不生成 `settings.json`、不生成 `.claude/` 目录）。理由：native 投影依赖 effective policy 和 generation 绝对路径，portable 层没有这些信息；提前生成会让 portable 树与机器耦合，破坏跨机器可复现性。
- `skills/` 是文件副本，不是 symlink。`_tree_digest` 明确拒绝 symlink 与 hard link，且 Windows 建 symlink 需要管理员或开发者模式。

### 2.2 effective render（Claude adapter 层）

`claude/runtime.py` 的 `_materialize_claude_generation(args, env) -> (generation, portable_hash, effective_hash, skill_names)`，严格镜像 `omp/runtime.py:1180`：

```text
1. tempfile.TemporaryDirectory(prefix=f"cap-render-{profile}-claude-")
2. subprocess: agent-profile materialize --client claude --output <tmp> …
   → 解析 stdout JSON 的 "tree_hash" → portable_hash
3. skill_names = sorted(非 symlink 子目录名 of <tmp>/skills)
4. policy            = _read_claude_runtime_policy(args)        # .cap/runtime/claude.toml
   global_preference = _read_global_claude_preference(args)     # runtimes/claude/<id> 内受控 preference
   config_template   = _effective_claude_config(portable_cfg, skill_names, policy, global_preference)
5. fixed_launch = {固定门禁 + skills + runtime_policy 证据}
6. source_context, source_digest = _generation_source_context(args, portable_hash)
7. effective_hash = _digest_json({"version":1,"client":"claude",
                                  "source_context","source_digest","config","launch"})
8. generation = <REAL_HOME>/.agent-system-state/renders/claude/<effective_hash 去前缀>
9. 命中 → _verify_claude_generation(...) → 返回
   未命中 → stage 目录 → copytree → 写 claude-config.yaml → 写 native 投影
          → content_digest → 写 .cap-generation.json → os.rename 原子提升
```

与 OMP 的两处**有意偏离**：

1. `effective_hash` 的输入 payload 增加 `"client": "claude"` 字段。OMP 的 payload 没有 client 字段，因为它是唯一的 effective 客户端；一旦有第二个，必须防止两个客户端在极端情况下算出同一个 hash 而互相命中彼此的 CAS。CAS 路径已按 client 分目录，此字段是第二道防线。
2. `content_digest` 必须显式写成 `_tree_digest(stage, exclude={".cap-generation.json"})`。OMP 侧当前写的是 `_tree_digest(stage)`（`omp/runtime.py:1316`），只因为写 digest 时 manifest 尚不存在才与校验侧（`:1171` 带 `exclude`）碰巧一致。Claude 侧不复制这个隐式依赖。

### 2.3 generation 目录结构

```text
$HOME/.agent-system-state/renders/claude/<effective_hash>/
  .cap-generation.json          # 见 2.5
  claude-config.yaml            # CAP adapter 中间态（唯一的"配置真相"）
  system-prompt.md              # 来自 portable
  mcp.json                      # 来自 portable（CAP 中间格式）
  skills/<skill>/…              # 来自 portable
  native/                       # ← 由 claude-config.yaml 投影出的 Claude 原生产物
    settings.json               #    --settings 的目标
    mcp.json                    #    --mcp-config 的目标（Claude 原生 mcpServers 格式）
    plugin/                     #    --plugin-dir 的目标，Skill 的唯一交付通道
      .claude-plugin/
        plugin.json             #      {name, version, description, skills: "./skills/"}
      skills/<skill>/…          #      SKILL.md 及其附属文件（副本）
```

`native/plugin/` 采用本仓 `plugins/*/` 已有的 Claude plugin 布局（`.claude-plugin/plugin.json` + `skills/`），T-1 已实测该布局可被 `--plugin-dir` 正确加载。整个 generation 在运行期间只读，不需要区分可变子集。

**为什么保留 `claude-config.yaml` 与 `native/` 两份**：

- `claude-config.yaml` 是 CAP 拥有的语义中间态，字段名由 CAP 定义、稳定、可跨 Claude 版本演进。
- `native/` 是 Claude 拥有的格式，字段名随 Claude 版本变化。
- 中间层的存在强制「投影」这一步显式存在。Claude 升级导致 native 键改名时，只需改投影函数与 `adapter_version`，`claude-config.yaml` 的语义与仓库文档不变。这正是 v3 design 决策 8「客户端原生文件名只在隔离 render 中保留」的要求。
- 两者都在 `content_digest` 覆盖范围内，因此投影结果同样防篡改。

### 2.4 三个 Hash

| Hash | 计算者 | 输入 | 用途 | 失配后果 |
| --- | --- | --- | --- | --- |
| `portable_tree_hash` | profile engine `_tree_hash()` | portable 树的 `{path: {mode, sha256}}`，`_canonical_json`（`indent=2`）后 sha256 | 声明态指纹；跨机器可复现；写入 `.cap/lock.json` 的 `profiles.<role>.clients.claude.tree_hash` | `materialize_profile` 报 `rendered output drifted after lock verification` |
| `effective_render_hash` | claude adapter `_digest_json()` | `{version, client:"claude", source_context, source_digest, config, launch}`，紧凑 JSON 后 sha256 | 配置态指纹；**同时是 CAS 目录名**；policy / binding / adapter_version 任一变化必变 | CAS 未命中 → 重新物化（正常路径，非错误） |
| `content_digest` | claude adapter `_tree_digest()` | generation 目录内除 `.cap-generation.json` 外全部路径与字节流 | 落盘防篡改；不含 mode | `profile generation content drifted`，fail-closed 拒绝启动 |

**两套 canonical JSON 并存是既有事实，不在本变更中统一**：`profile/cli.py:_canonical_json` 用 `indent=2`，`omp/runtime.py:_digest_json` 用 `separators=(",", ":")`。Claude adapter 沿用 `_digest_json`（紧凑）计算 `effective_hash` 与 `source_digest`，与 OMP 保持一致；只在 `claude/runtime.py` 顶部注释中记录该差异，不跨模块重构。

**`effective_render_hash` 必须覆盖的输入**（缺一即视为设计缺陷）：

```text
source_context = {profile, layer_digest, effective_digest, portable_tree_hash, adapter_version}
source_digest  = digest(source_context)
config         = 合成后的 claude-config.yaml 内容（含 skills allowlist、MCP 开关、权限模式）
launch         = {固定门禁 flag 集合, skills, runtime_policy{project, global_preference_digest, effective}}
```

其中 `adapter_version` 必须是 **Claude 自己的版本号**。当前 `CLIENT_ADAPTER_VERSION = 8` 是一个全局 int，被所有客户端共用；直接复用会让 Claude 的版本变动作废全部 OMP generation。见 `delta-specs.md` 的 I-3。

### 2.5 generation manifest（`.cap-generation.json`）

```jsonc
{
  "version": 1,                       // Claude adapter 自己的 manifest 版本，从 1 起（OMP 当前为 2）
  "client": "claude",                 // 新增：OMP manifest 无此字段
  "profile": "general",
  "portable_tree_hash": "sha256:…",
  "effective_render_hash": "sha256:…",// == 目录名
  "source_context": {
    "profile": "general",
    "layer_digest": "sha256:…",
    "effective_digest": "sha256:…",
    "portable_tree_hash": "sha256:…",
    "adapter_version": 1
  },
  "source_digest": "sha256:…",
  "content_digest": "sha256:…",       // _tree_digest(generation, exclude={".cap-generation.json"})
  "skills": ["openspec-explore", "…"],
  "runtime_policy": {
    "project": { /* .cap/runtime/claude.toml 的 [policy] 原样 */ },
    "global_preference_digest": "sha256:…",
    "effective": { "permission_mode": "default", "enable_project_mcp": false, "auto_memory": false }
  },
  "native_projection": {
    "adapter_version": 1,
    "files": ["native/settings.json", "native/mcp.json", "native/plugin"],
    "unsupported": ["hooks", "plugins"],       // 声明存在但本版本不投影的能力类别
    "verified_surface_digest": "sha256:…"      // evidence/claude-native-surface.json 的 digest
  },
  "auth_mode": "subscription"                  // subscription | bare，见 3.4
}
```

`_verify_claude_generation()` 逐键精确比对 `version`、`client`、`profile`、`portable_tree_hash`、`effective_render_hash`、`source_context`、`source_digest`、`runtime_policy`、`native_projection`、`auth_mode`，任一不等即 `profile generation metadata drifted`；随后重算 `content_digest` 比对，不等即 `profile generation content drifted`。

初稿中的 `hydration` 段已随水合层一并取消（见 3.2）。`auth_mode` 参与 manifest 与 `effective_render_hash`：切换认证模式必须产生新的 generation，不允许同一份 generation 在两种隔离强度下复用。

## 3. 能力交付与状态分离（T-1 实测后的定稿）

> 本节在 T-1 实验后被**整体改写**。设计初稿假设「Skill 必须放进 `CLAUDE_CONFIG_DIR`，而该目录必须可写，因此需要一个水合层」。实测证明该前提不成立：`--plugin-dir` 提供了一条 session 级、只读的 Skill 交付通道。**水合层已从设计中移除。**

### 3.1 实测结论

全部结论来自 `evidence/claude-native-surface.json`（Claude Code 2.1.236，win32-x64）：

| 事实 | 实测证据 |
| --- | --- |
| `CLAUDE_CONFIG_DIR` 真实生效，且 `.claude.json` 随之迁移 | 重定向后目标目录内生成 `.claude.json`、`backups/` |
| **认证随 config dir 迁移** | 重定向后 `claude doctor` 报 `Not signed in to claude.ai`；`claude -p` 返回 `Not logged in · Please run /login` |
| Skill 发现路径共五类 | 日志：`Loading skills from: managed=…, user=<CLAUDE_CONFIG_DIR>\skills, project=[]`；`getSkills returning: 0 skill dir commands, 1 plugin skills, 42 bundled skills` |
| **`--plugin-dir` 可只读交付 Skill** | 日志：`Loaded 1 session-only plugins from --plugin-dir`；`Loaded 1 skills from plugin cap-probe default directory` |
| `--setting-sources ""` 可屏蔽用户级 settings | 传空值后日志不再 watch 用户级 `settings.json` |
| **`--strict-mcp-config` 压不住 claude.ai 账号级 connector** | 传 `--strict-mcp-config --mcp-config <空>` 后仍有 `[claudeai-mcp] Fetched 2 servers`、`MCP server "claude.ai Google Drive": Connection established` |
| `--bare` 消除 connector，但代价是放弃 OAuth | `--bare` 下无任何 `claudeai-mcp` 行；同时 `claude --bare -p` 在 OAuth 有效时返回 `Not logged in` |
| 42 个 bundled skills 不可由本地配置控制 | `--bare` 与非 `--bare` 下均为 `42 bundled skills` |

### 3.2 定稿模型：generation 只读 + runtime 可写

Claude 与 OMP 的结构差异**比初稿预计的小得多**。generation 可以像 OMP 一样被只读引用：

```text
能力面（只读，来自 CAS generation，参与 content_digest）
  Skills   → --plugin-dir <generation>/native/plugin
  MCP      → --mcp-config <generation>/native/mcp.json  --strict-mcp-config
  Settings → --settings    <generation>/native/settings.json
  Prompt   → --append-system-prompt "$(cat <generation>/system-prompt.md)"
  Agents   → --agents <JSON>（当前为空）
  来源门禁 → --setting-sources ""

状态面（可写，来自 runtime 命名空间，不参与任何 digest）
  CLAUDE_CONFIG_DIR = $HOME/.agent-system-state/runtimes/claude/<runtime-id>/
    .claude.json        认证、oauthAccount、projects 索引
    settings.json       CAP 写入的空对象；被 --settings 与 --setting-sources 覆盖
    history.jsonl / statsig/ / todos/ / shell-snapshots/ / backups/
```

三条设计后果：

1. **不再需要 `configs/<effective_hash>/` 水合目录**，`hydration` manifest 段、`_hydrate_claude_config`、`_verify_hydrated_config`、`hydration_digest` 全部取消。
2. `CLAUDE_CONFIG_DIR` 按 **runtime-id** 而非 `(runtime-id, effective_hash)` 分配，与 OMP 的 `runtimes/omp/<id>/` 完全对齐：认证与会话跨项目、跨 generation 共享。
3. generation 目录**在运行期间保持只读**，运行后可直接复查 `content_digest`，无需区分 immutable / mutable 子集。

### 3.3 认证：已确定为「CAP 内登录一次」

实测确认凭据随 `CLAUDE_CONFIG_DIR` 迁移，因此落在设计初稿预设的**中间情形**：

- 用户首次执行 `cap use <role> --cli claude` 时需在 CAP runtime 内登录一次；
- 此后凭据留在 `runtimes/claude/<runtime-id>/`，跨项目、跨 role、跨 generation 共享；
- 与 OMP 的 `runtimes/omp/default/` 保存认证的模型一致，不需要任何特殊处理。

该目录含真实凭据，因此：必须 `0o700`、必须通过 `_validate_private_runtime`、**永远不进入任何 digest、receipt 或证据文件**。

### 3.4 认证模式抉择（需负责人决定）

T-1 暴露了一个初稿完全没有预见的 ambient 面：**claude.ai 账号级远程 MCP connector**。它不来自任何本地文件，从 `api.anthropic.com/v1/mcp_servers` 拉取，`--strict-mcp-config` 无效。这迫使一个二选一：

| | A. 订阅 OAuth | B. `--bare` + API key |
| --- | --- | --- |
| 认证 | CAP runtime 内登录一次 | `ANTHROPIC_API_KEY` 或 `apiKeyHelper` |
| claude.ai connector | **加载，CAP 不可控** | 不拉取 |
| hooks / auto-memory / CLAUDE.md 自动发现 / keychain | 需逐项用 flag 关闭 | `--bare` 一并关闭 |
| `--plugin-dir` 交付 Skill | 正常 | 正常（实测） |
| bundled skills | 不可控 | 不可控 |
| MCP 闭包生效态 | 只能记 `reported_client_limited` | 可接近 `observed` |
| 成本 | 用订阅额度 | 单独 API 计费 |

**已定稿（负责人 2026-08-19 决定）**：采用 **A. 订阅 OAuth** 作为默认。`.cap/runtime/claude.toml` 的 `auth_mode` 默认 `"subscription"`，`"bare"` 保留为可选值。该字段参与 `effective_render_hash` 与 receipt。

**强制后果**：`subscription` 模式下 receipt 的 `effective_observations.mcps` **恒为** `reported_client_limited`，`ambient_floor.claudeai_connector_count` 只记数量、不记名称与端点。实现中**不得**提供任何把该维度提升为 `observed` 的路径——`--strict-mcp-config` 压不住 connector 已被实测证明。

## 4. Claude 启动流程

```text
cap use <role> --cli claude [-- <forwarded args>]
 │
 ├─ 0. 前置门禁（复用现有实现，不新增语义）
 │     _check_project_pollution        项目内不得有 .claude/、CLAUDE.md 以外的旁路面
 │     _check_global_pollution         用户级不得有 active 的 Claude 能力面（见 5.2）
 │     lock 校验                        .cap/lock.json 与当前声明一致
 │     machine-context pin 校验         宿主底座未漂移
 │     assembly-binding 校验            role↔machine-context 绑定有效
 │     enforce_asset_closure            无 blocked / 无未证明的 active 资产
 │     _require_shared_runtime_ready    runtimes/claude/<id>/ 已就绪且为当前用户私有目录
 │
 ├─ 1. RENDER
 │     _materialize_claude_generation()
 │       portable materialize → portable_tree_hash
 │       policy 合成 → claude-config.yaml
 │       native 投影 → native/
 │       effective_render_hash → CAS 定位
 │       原子 stage → rename 提升
 │
 ├─ 2. VALIDATE effective_hash
 │     _verify_claude_generation()
 │       manifest 9 键精确比对 → metadata drifted?
 │       重算 content_digest      → content drifted?
 │     ★ 命中已有 CAS 与新物化都走同一个校验函数，无快捷路径
 │
 ├─ 3. LAUNCH（generation 只读引用，无水合步骤）
 │     env  = _claude_env(base_env, runtime_dir, real_home)
 │     argv = _claude_command(generation, skill_names, auth_mode, forwarded)
 │     subprocess.run(argv, cwd=workdir, env=env)
 │
 ├─ 4. POST-VERIFY
 │     agent-profile verify        闭包与 lock 在运行后仍一致
 │     content_digest 复查          generation 在运行期间未被改写
 │
 └─ 6. RECEIPT
       _write_claude_receipt()  →  <project>.runs/<role>-claude-<ts>.receipt.json
```

### 4.1 启动命令与环境

全部 flag 均已在 T-1 中确认存在（`evidence/claude-native-surface.json` 的 `forbidden-flags-exist`、`setting-sources-flag`、`mcp-flags`、`plugin-dir-readonly-skill-delivery`）：

```python
def _claude_command(generation, skill_names, auth_mode, forwarded) -> list[str]:
    executable = shutil.which("claude") or "claude"
    native = generation / "native"
    prompt = (generation / "system-prompt.md").read_text("utf-8").strip() + "\n"
    argv = [executable]
    if auth_mode == "bare":
        argv.append("--bare")               # 关 hooks/auto-memory/CLAUDE.md 发现/keychain/connector
    argv += [
        "--settings",        str(native / "settings.json"),
        "--setting-sources", "",            # 屏蔽 user / project / local 三个来源
        "--mcp-config",      str(native / "mcp.json"),
        "--strict-mcp-config",
        "--append-system-prompt", prompt,
    ]
    if skill_names:                          # Skill 的唯一交付通道，只读引用 CAS
        argv += ["--plugin-dir", str(native / "plugin")]
    return [*argv, *forwarded]
```

```python
def _claude_env(base_env, runtime_dir, real_home) -> dict[str, str]:
    env = base_env.copy()
    for name in AMBIENT_CONFIG_ENV:             # 清除其他客户端的 ambient 指针
        env.pop(name, None)
    for name in CLAUDE_AMBIENT_AUTH_ENV | 动态匹配的凭据变量名:
        env[name] = ""                           # 置空而非删除，沿用 OMP 的做法
    env["HOME"] = str(real_home)                 # 保留宿主底座（Git / SSH / 工具链）
    env["CLAUDE_CONFIG_DIR"] = str(runtime_dir)  # 按 runtime-id，不按 generation
    return env
```

固定门禁的取值来源是 `claude-config.yaml` 的 `launch` 段，并整体参与 `effective_render_hash`。任何一个门禁被关闭，hash 必变，旧 generation 不被命中。

三点说明：

- **`--setting-sources ""` 是主要隔离手段**，实测可使用户级 `settings.json` 不再被加载；`--settings` 提供命令行优先级层，二者叠加而非二选一。
- `auth_mode = "bare"` 时**不需要**逐项关闭 hooks 与 auto-memory，`--bare` 已一并覆盖；`auth_mode = "subscription"` 时这些面需要靠 `--setting-sources ""` 与 settings 投影关闭，且 claude.ai connector 仍不可控（见 3.4）。
- 初稿中的 `CLAUDE_CODE_DISABLE_AUTO_MEMORY` 未在 `--help` 中出现，**不采用**；auto-memory 的关闭改由 `--bare` 或 settings 投影承担，具体键名须在实现前补充核对。

### 4.2 receipt

沿用 OMP receipt 的字段骨架，Claude 侧新增 4 个字段：

```jsonc
{
  "version": 1,
  "client": "claude",
  "profile": "general",
  "runtime_id": "default",
  "global_runtime_root": "…/runtimes/claude/default",
  "global_generation": "…/renders/claude/<hash>",
  "auth_mode": "subscription",                                         // 新增：subscription | bare
  "project_root": "…",
  "project_source_context": { … },
  "project_source_digest": "sha256:…",
  "runtime_policy": { … },
  "base_digest": "sha256:…",
  "layer_digest": "sha256:…",
  "effective_digest": "sha256:…",
  "portable_tree_hash": "sha256:…",
  "effective_render_hash": "sha256:…",
  "post_run_content_digest": "sha256:…",                               // 新增：运行后复查 generation 未被改写
  "workdir": "…",
  "exit_code": 0,
  "forwarded_argument_count": 2,
  "evidence": {                                                        // 新增：三层证据显式化
    "declared":   "ok",
    "configured": "generation-verified",
    "effective":  "unknown"
  },
  "effective_observations": {                                          // 新增：逐维度生效态
    "skills":  "unknown",
    "mcps":    "reported_client_limited",   // subscription 模式下强制；见 3.4
    "context": "unknown",
    "hooks":   "reported_client_limited",
    "plugins": "reported_client_limited",
    "bundled_skills":   "reported_client_limited",  // 42 个自带 Skill，CAP 不可控
    "managed_settings": "unknown"
  },
  "ambient_floor": {                                                   // 新增：不可控面的无 secret 观察
    "managed_settings_present": false,
    "claudeai_connector_count": 2,          // 只记数量，不记名称与端点
    "bundled_skill_count": 42
  }
}
```

receipt **不得**包含：token、cookie、endpoint secret、API key、会话正文、history 正文、转发参数的**值**（只记数量）。这一约束由现有的 `SECRET_KEY_PATTERN` / `SECRET_LINE_PATTERN` 复用测试覆盖。

## 5. Capability 闭包支持

### 5.1 四类能力的投影策略

| 能力 | lock 中的 `capability_semantics` | Claude 投影目标 | 本变更实现 |
| --- | --- | --- | --- |
| Skills | `native-staging` | `native/plugin/skills/<name>/SKILL.md`，经 `--plugin-dir` 只读加载（T-1 实测通过） | **完整实现**。仓库现有 13 个 Skill 是唯一有真实用例的类别 |
| MCP | `native-config` | `native/mcp.json` + `--mcp-config` + `--strict-mcp-config` | **完整实现**（当前闭包为空，但格式与门禁必须就位）。注意 `--strict-mcp-config` 对 claude.ai 账号级 connector 无效，见 3.4 |
| Hooks | `opaque-staging` | 需投影进 `settings.json` 的 `hooks` 键 | **不实现**。声明非空即 `ProfileError`；manifest 记 `unsupported` |
| Plugins | `opaque-staging` | 需 marketplace + `enabledPlugins` | **不实现**。声明非空即 `ProfileError`；manifest 记 `unsupported` |

Hooks / Plugins 采取「fail-closed 而非静默降级」：`.cap` 中一旦为 Claude 声明了 hook 或 plugin，`cap render --cli claude` 直接报错并指出本 adapter 版本不支持，而不是渲染出一个缺少这些能力的树。理由：静默降级会让 lock 通过、render 成功、但实际能力面与声明不符——这正是三层证据体系要杜绝的情形。

`skills` 的 allowlist 同时出现在三处，必须一致：`claude-config.yaml` 的 skills 段、`native/plugin/skills/` 的实际目录集合、generation manifest 的 `skills` 数组。三者由同一个 `skill_names` 列表生成，且全部落在 `content_digest` 内。

### 5.2 ambient 面的关闭与观察

Claude 的 ambient 面比 OMP 大。按「能关的先关，关不掉的降级为观察并诚实标记」处理：

| ambient 面 | 处理 | 关闭手段（T-1 实测） | 关不掉时 |
| --- | --- | --- | --- |
| 用户级 `<CLAUDE_CONFIG_DIR>/skills`、`agents`、`commands` | 关闭 | `CLAUDE_CONFIG_DIR` 指向 CAP runtime 目录（其中不含这些子目录） | — |
| 用户级 `settings.json` | 关闭 | `--setting-sources ""`（实测不再被 watch）+ `--settings` 覆盖 | — |
| 用户级 / 项目级 MCP 配置 | 关闭 | `--mcp-config` + `--strict-mcp-config` | — |
| 项目级 `<workdir>/.claude/**`、`.mcp.json` | 关闭 | `_check_project_pollution`（`PROJECT_BYPASS_DIRS` 已含 `.claude`）+ `--setting-sources ""` | fail-closed |
| 项目级 `CLAUDE.md` | 受控允许 | 本仓 `CLAUDE.md` 内容固定为 `@AGENTS.md`，已由 `profile/cli.py:2805` 精确校验 | fail-closed |
| 用户级 `.claude.json` | 关闭 | 实测随 `CLAUDE_CONFIG_DIR` 迁移；`_check_global_pollution` 仍作为第二道门检查 `{enabledPlugins, hooks, mcpServers, plugins, skills}` | fail-closed |
| auto memory / hooks / CLAUDE.md 自动发现 | 关闭 | `auth_mode = "bare"` 一并关闭；`subscription` 模式下靠 settings 投影（具体键待核对） | 降级为 `unknown` |
| **claude.ai 账号级远程 MCP connector** | **关不掉**（subscription 模式） | 仅 `auth_mode = "bare"` 可消除 | `effective_observations.mcps = "reported_client_limited"`，`ambient_floor.claudeai_connector_count` 记数量 |
| **42 个 bundled skills** | **关不掉** | 无（`--disable-slash-commands` 的效果未验证） | `effective_observations.bundled_skills = "reported_client_limited"` |
| **managed settings**（`C:\Program Files\ClaudeCode\managed-settings.json`、`.claude/{skills,agents,commands}`、MDM） | **关不掉** | 无。`--safe-mode` 帮助原文亦称 policy settings 仍生效 | 记录存在性进 `ambient_floor`，`managed_settings = "unknown"` |

**Claude 存在三层 CAP 无法接管的能力底座**（managed policy、bundled skills、claude.ai connector），而 OMP 一层都没有。因此 Claude 的隔离声明上限是：「CAP 控制了用户级与项目级的声明能力面；自带 Skill、企业 managed 层、以及订阅模式下的账号级 connector 不在 CAP 控制范围内」。这句话必须原样进入 `docs/profile.md` 的 Adapter 合同章节，不得弱化。

### 5.3 闭包验证的输出分层

`cap show <role> --cli claude` 的输出结构与 `--cli omp` 相同，并额外给出 Claude 特有的 ambient 观察：

```jsonc
{
  "profile": "general",
  "inventory": { "skills": [...], "mcps": [], "hooks": [], "plugins": [] },
  "evidence": { "declared": "ok", "configured": "lock-verified", "effective": "unknown" },
  "preview": {
    "client": "claude",
    "files": [...],
    "tree_hash": "sha256:…",
    "portable_tree_hash": "sha256:…",
    "effective_render_hash": "sha256:…",
    "global_generation": "…",
    "project_source_context": { … },
    "project_source_digest": "sha256:…",
    "skills": [...],
    "fixed_flags": ["--settings", "--append-system-prompt", "…"],
    "unsupported": ["hooks", "plugins"],
    "ambient_floor": {
      "managed_settings_present": "unknown",
      "user_global_config_keys": []
    }
  }
}
```

## 6. 与 OMP adapter 的平行对标

| 维度 | OMP（已实现） | Claude（本变更） | 是否同构 |
| --- | --- | --- | --- |
| portable 渲染 | `_render_tree` 的 else 分支 | `_render_tree` 新增显式 `claude` 分支 | 是 |
| portable 输出 | `config.yml`(`{}`)、`mcp.json`、`system-prompt.md`、`skills/` | `claude-config.yaml`(`{}`)、`mcp.json`、`system-prompt.md`、`skills/` | 是 |
| effective 模块 | `omp/runtime.py` | `claude/runtime.py` | 是 |
| CAS 根 | `renders/omp/<effective_hash>/` | `renders/claude/<effective_hash>/` | 是 |
| runtime 根 | `runtimes/omp/<id>/` | `runtimes/claude/<id>/` | 是 |
| manifest | `.cap-generation.json` v2 | `.cap-generation.json` v1 + `client`/`native_projection`/`auth_mode` | 结构同构，字段扩展 |
| 三 Hash | portable / effective / content | 同名同义 | 是 |
| policy 文件 | `.cap/runtime/omp.toml` | `.cap/runtime/claude.toml` | 是 |
| policy 合成顺序 | 系统门禁 > 项目 policy > role override > 用户 preference | 同 | 是 |
| 配置注入 | `--config` + `PI_CONFIG_FILES`（只读指向 generation） | `--settings` + `--mcp-config` + `--plugin-dir`（**同样只读指向 generation**） | **是**（T-1 后由「最大差异」翻转为同构） |
| Skills 注入 | `--skills a,b` + `skills.customDirectories` 指向 generation | `--plugin-dir <generation>/native/plugin`（session 级只读） | 是 |
| prompt 注入 | `--append-system-prompt` | `--append-system-prompt` | 是 |
| 关闭 ambient | `--no-extensions --no-rules` + `enableClaudeUser/Project=false` 等开关 | `--setting-sources ""` + `--strict-mcp-config`（+ `--bare`） | 是 |
| 不可关闭的底座 | 无 | **managed settings + 42 bundled skills + claude.ai connector（订阅模式）** | **否，最大差异** |
| 认证位置 | `runtimes/omp/<id>/` 内，已验证 | `runtimes/claude/<id>/` 内，**T-1 已实测确认** | 是 |
| 会话状态 | `runtimes/omp/<id>/`（`agent.db`、history） | `runtimes/claude/<id>/`（`.claude.json`、`history.jsonl`） | 是 |
| receipt | v4 | v1，字段超集 | 结构同构 |
| 生效态观察 | `omp` 被降级维度：`mcps` | Claude 降级维度：`hooks`、`plugins`、`managed_settings`，其余待 probe 能力确定 | 是（机制相同） |

**必须复制的 OMP 安全实践**（逐项在实现中对照）：

- `_assert_managed_path`：拒绝 CAS / runtime 路径逃逸出 CAP 状态根，且路径链上任一段是 symlink 即拒绝。
- `_validate_private_runtime`：目录属主与权限校验（Windows 上跳过 uid / mode 检查，`sys.platform != "win32"` 分支）。
- `_reject_unsafe_tree`：拒绝 symlink、hard link、特殊文件。
- stage + `os.rename` 原子提升；`rename` 失败且目标已存在时 `rmtree` stage 并转为校验既有 generation。
- `except BaseException: rmtree(stage)` 的清理路径。
- `mkdir(mode=0o700)` / `chmod(0o600)`（Windows 上为 no-op，不作为唯一防线）。

## 7. Claude 三种形态的差异与证据天花板

| 形态 | CAP 参与方式 | 可达证据等级 | 说明 |
| --- | --- | --- | --- |
| **CLI / IDE**（`claude` 可执行文件，含 IDE 内嵌终端） | 完整：render → validate → launch → receipt | 声明态 ✅ / 配置态 ✅ / 生效态 **部分**（能 probe 的维度为 observed，其余 `unknown`） | **本变更的唯一实现目标** |
| **API / SDK**（`claude-agent-sdk`） | 部分：SDK 消费 generation 产物 | 声明态 ✅ / 配置态 ✅ / 生效态 **由调用方负责** | SDK 通过等价于 `--setting-sources ""` 的选项 + 显式 system prompt / skills / MCP 配置消费 generation（SDK 选项名待核对，不在本变更实现范围）。CAP 只提供 generation 与一个只读读取器；不代替调用方写 receipt |
| **Web**（claude.ai） | 无：不消费本地文件 | 声明态 ✅ / 配置态 ❌ / 生效态 ❌ | CAP 只能产出可人工粘贴的 `system-prompt.md` 与 Skill 清单。**任何 Web 使用都不得产生 receipt**，避免伪造生效证据 |

**IDE 形态的额外风险**：IDE 集成可能由 IDE 插件自行拉起 `claude` 进程，绕过 `cap use`。本变更不试图接管 IDE 的启动路径；对应的定位是「IDE 内在 CAP 提供的终端里运行 `cap use <role> --cli claude`」。IDE 插件直接启动的会话不在 CAP 证据范围内，文档必须明说。

**SDK 形态的边界**：CAP 提供 `claude/sdk_export.py` 级别的只读函数（读 generation → 返回 `{system_prompt, skills_dir, mcp_servers, settings}`），**不**提供运行循环、不代管密钥、不写 receipt。SDK 消费者若需要证据，自行调用 `cap show --cli claude` 取配置态摘要。

## 8. 数据结构定义

### 8.1 `.cap/runtime/claude.toml`

```toml
version = 1
client = "claude"

[policy]
# 只声明已在 evidence/claude-native-surface.json 中核对过的语义字段。
auth_mode          = "subscription"  # subscription | bare，见 3.4；参与 effective_render_hash
permission_mode    = "manual"        # 实测合法取值：acceptEdits auto bypassPermissions manual dontAsk plan
enable_project_mcp = false           # 是否允许工作目录的项目级 MCP 进入闭包
enable_user_assets = false           # 是否允许用户级 skills/agents/commands（固定 false，不可放宽）
auto_memory        = false           # 是否允许 auto memory
```

`permission_mode` 的取值集合来自 `claude --help` 实测，**不存在 `default`**；设计初稿中的 `"default"` 是错误的。`bypassPermissions` 必须被系统固定门禁拒绝。

校验规则（`_read_claude_runtime_policy`，镜像 `_read_omp_runtime_policy`）：

- `version == 1` 且 `client == "claude"`，否则 `_ClaudeError`。
- `[policy]` 必须是 table。
- **系统固定门禁**：`enable_user_assets` 必须为 `false`，`enable_project_mcp` 必须为 `bool`。违反即 fail-closed，role override 与用户 preference 都不能放宽。
- **未知字段原样保留**在返回的 policy dict 中（参与 `runtime_policy.project` 证据与 `effective_hash`），但**不投影**到 native。这是 v3 tasks 3.7「不猜测 native 配置键」的直接要求，且已有测试范式（`tests/omp/test_runtime_policy_v3.py::test_policy_preserves_unknown_fields_without_projecting_them`）。

### 8.2 `claude-config.yaml`（CAP adapter 中间态）

```yaml
version: 1
client: claude
skills:
  include: [openspec-explore, openspec-propose, "…"]
  enable_user: false        # 固定门禁
  enable_project: false     # 固定门禁
  enable_plugin: false      # 固定门禁
mcp:
  enable_project: false
  servers: {}               # 来自 portable mcp.json
memory:
  auto_memory: false
  load_user_claude_md: false
  load_project_claude_md: true    # 仅限已校验的 <project>/CLAUDE.md == "@AGENTS.md"
permissions:
  default_mode: default
  allow: []
  deny: []
prompt:
  append_system_prompt_from: system-prompt.md
unsupported: [hooks, plugins]
```

字段名是 **CAP 自有语义**，不是 Claude native 键名。投影函数 `_project_claude_native(config, generation) -> dict[str, bytes]` 负责翻译成 native 文件字节流；它是本 adapter 中唯一允许出现 Claude native 键名的地方。

### 8.3 Python 类型骨架

```python
class _ClaudeError(ValueError):
    """Report a fail-closed Claude adapter error."""

@dataclass(frozen=True)
class ClaudeGeneration:
    root: Path                    # renders/claude/<effective_hash>/
    profile: str
    portable_tree_hash: str
    effective_render_hash: str
    content_digest: str
    skills: tuple[str, ...]
    auth_mode: str                # "subscription" | "bare"
    runtime_policy: Mapping[str, object]
    native_projection: Mapping[str, object]

@dataclass(frozen=True)
class AmbientFloor:
    """CAP 无法接管的能力底座；只记可计数的无 secret 观察。"""
    managed_settings_present: bool
    claudeai_connector_count: int | None   # None 表示本次未能观察
    bundled_skill_count: int | None
```

初稿中的 `HydrationPlan` / `HydratedConfig` 已随水合层取消。

### 8.4 `evidence/claude-native-surface.json`

```jsonc
{
  "version": 1,
  "captured_at": "2026-08-__",
  "claude_cli_version": "…",           // `claude --version` 实际输出
  "platform": "win32|darwin|linux",
  "facts": [
    {
      "id": "config-dir-env",
      "claim": "CLAUDE_CONFIG_DIR 重定位用户级 settings/skills/agents/commands/.mcp.json/projects",
      "source": "https://docs.claude.com/…",
      "verified_by": "doc|experiment|both",
      "status": "confirmed|refuted|unknown",
      "notes": "…"
    }
  ],
  "digest": "sha256:…"                 // 供 generation manifest 的 native_projection 引用
}
```

**规则**：`native_projection.verified_surface_digest` 参与 `content_digest`。核对结论更新 → digest 变 → generation 失效 → 重新物化。这把「Claude 变了，我们的假设过期了」这件事变成一个可被 hash 发现的事件，而不是一次静默的错误。

## 9. 安全边界

**必须保持**

1. `.cap` 是 Agent-facing 能力的唯一权威。用户目录只作为 asset-inventory 观察项。
2. 默认拒绝。未被 `allow` / `override` / 已批准 external import 覆盖的资产不进入闭包。
3. 系统固定门禁不可被 role override 或用户 preference 放宽（`enable_user_assets`、hooks/plugins 的 unsupported 状态）。
4. 认证与能力分离。`runtimes/claude/<id>/` 保存认证与会话；它**不是**能力发现来源，任何从 runtime 反向发现能力的代码路径都是缺陷。
5. 无 secret 落盘。generation、manifest、receipt 一律只记摘要与计数；`runtimes/claude/<id>/` 含真实凭据，永不进入任何 digest 或证据文件。
6. 不写用户 Claude 目录。CAP 对 `~/.claude`、`~/.claude.json`、`~/.claude-plugin` 只读。
7. 路径安全。CAS 与 runtime 目录必须位于 CAP 状态根内，路径链无 symlink，无 hard link，无特殊文件。
8. 原子性。generation 物化用 stage + rename；失败清理 stage，不留半成品。

**必须诚实**

9. managed settings 层不在 CAP 控制范围内 → `effective_observations.managed_settings = "unknown"`，文档明说。
10. 配置态通过 ≠ 生效态通过。generation 校验成功只证明 CAP 侧一致，不证明 Claude 实际加载了什么。
11. 无法证明的维度保持 `unknown` / `reported_client_limited`，不由「文件已生成」推断为 confirmed。
12. Web 形态不写 receipt。

**明确的攻击面与缓解**

| 风险 | 缓解 |
| --- | --- |
| 用户手工改 generation 里的 `native/settings.json` 提权 | 启动前 `content_digest` 全树比对，不符即 fail-closed；运行后再复查一次 |
| 用户在 `~/.claude.json` 塞 `mcpServers` | 实测该文件随 `CLAUDE_CONFIG_DIR` 迁移已不生效；`_check_global_pollution` 仍作第二道门 |
| 通过 claude.ai 账号后台新增远程 connector | **CAP 无法阻止**（subscription 模式）。只能记 `ambient_floor.claudeai_connector_count` 并把 MCP 生效态降级；需要真正闭包时改用 `auth_mode = "bare"` |
| 工作目录里放 `.claude/settings.local.json` | `_check_project_pollution` 的 `PROJECT_BYPASS_DIRS` 已含 `.claude`；叠加 setting-sources 门禁 |
| CAS 目录被预置成恶意内容（hash 碰撞或抢占） | `content_digest` + manifest 9 键比对；CAS 父目录 `0o700` 且 `_validate_private_runtime` |
| 转发参数关闭门禁（如 `--dangerously-skip-permissions`、`--plugin-dir`、`--mcp-config`、`--setting-sources`、`--settings`） | 新增 `FORBIDDEN_CLIENT_ARGUMENTS["claude"]` 拒绝列表，在 `--` 之后的用户参数中出现即拒绝启动 |
| 通过 `--add-dir` 扩大文件访问面 | 计入 `FORBIDDEN_CLIENT_ARGUMENTS["claude"]` 的评审项；默认拒绝，需求出现时再显式放开并纳入 policy |

`FORBIDDEN_CLIENT_ARGUMENTS["claude"]` 是本设计中**优先级最高的单个防御**：任何允许用户在 `--` 之后重新打开被 CAP 关掉的门的 flag，都必须在这里被拒绝，否则整套 hash 与证据体系可以被一个命令行参数绕过。

## 10. 跨平台

| 平台 | 关注点 | 处理 |
| --- | --- | --- |
| Windows | 无 `os.geteuid`、POSIX mode 位是 no-op | 沿用 `sys.platform != "win32"` 分支跳过 uid / mode 校验，改以路径归属（在 `%USERPROFILE%` 下）+ 无 symlink 作为主要保证 |
| Windows | 260 字符路径限制。`renders/claude/<64 hex>/native/plugin/skills/<name>/references/…` 比 OMP 更深，容易越界 | 物化前预检最深路径长度，超限即给出明确中文错误与建议（缩短 skill 内层路径 / 启用长路径支持）；不静默失败 |
| Windows | symlink 需管理员或开发者模式 | 全程使用文件副本，不使用 symlink（`_tree_digest` 本就拒绝 symlink） |
| Windows | 文件锁：Claude 运行中占用 `CLAUDE_CONFIG_DIR` 内文件 | generation 只读、与 runtime 目录分离，因此运行期不会锁住 CAS；并发物化同一 generation 时以 stage + rename 保证一致，冲突则报错而非覆盖 |
| Windows | managed policy 在 `HKLM\SOFTWARE\Policies\ClaudeCode` 与 `C:\Program Files\ClaudeCode\` | 只做存在性与 digest 观察，不读取内容、不修改 |
| macOS | managed 在 `/Library/Application Support/ClaudeCode/` 与 plist；凭据可能在 Keychain | 同上；Keychain 情况下认证与 config dir 解耦，属最优情形 |
| Linux / WSL | managed 在 `/etc/claude-code/`；WSL 可能继承 Windows 策略 | 同上；WSL 场景在文档中标注为未验证 |

本仓的 Windows 知识入口（长路径、文件锁）见 `knowledge/windows-agent-ops.md`，实现遇到相关问题时按名查询。

## 11. Risks / Trade-offs

- ~~**认证位置未知**~~ **已由 T-1 解决**：凭据随 `CLAUDE_CONFIG_DIR` 迁移，落在预设的中间情形——用户在 CAP runtime 内登录一次，此后跨项目共享。无需额外机制。
- ~~**水合目录膨胀**~~ **已随水合层取消而消失**。`CLAUDE_CONFIG_DIR` 按 runtime-id 分配，数量恒定。
- **claude.ai 账号级 connector 不可控（新增，最高）**。subscription 模式下 CAP 无法声称控制了 MCP 闭包。缓解：`auth_mode` 二选一交由负责人决定；subscription 模式下强制把 `effective_observations.mcps` 记为 `reported_client_limited`，并在文档中明写。**不得**因为传了 `--strict-mcp-config` 就声称 MCP 已闭包——实测证明这是错的。
- **bundled skills 不可控（新增）**。42 个自带 Skill 始终在场，可能与项目 Skill 语义重叠或抢占。缓解：记入 `ambient_floor`；若将来出现真实冲突，再评估 `--disable-slash-commands` 的适用性（其对 bundled 的效果尚未验证）。
- **`--setting-sources ""` 的长期稳定性**。它是主要隔离手段，但属 CLI 行为而非文档化契约。缓解：`verified_surface_digest` 参与 hash，使核对结论过期成为可发现事件；并在启动后 probe 中验证用户级 settings 确实未加载。
- **`CLIENTS` 扩容的连带影响**。加入 `claude` 会让 lock 为所有 role 多渲染一个客户端树，并让每个 hook / plugin 都被要求提供 `targets/claude/`。当前仓库 hooks / plugins 闭包为空，因此实际 blast radius 为零，但**这是一个必须在 T-2 中验证的前提**，一旦将来新增 hook / plugin 就会被触发。详见 `delta-specs.md` I-5。
- **`CLIENT_ADAPTER_VERSION` 是全局 int**。不改成 per-client 就会让 Claude 的版本变动作废全部 OMP generation。必须在实现早期改掉。详见 `delta-specs.md` I-3。
- **managed settings 不可控**。企业环境下 CAP 的隔离声明有天花板。这不是缺陷而是事实，必须写进 `docs/profile.md` 的 Adapter 合同章节。
- **投影层与 Claude 版本耦合**。Claude 改 native 键名会让投影失效。缓解：`verified_surface_digest` 进 hash，使假设过期变成可发现事件；`adapter_version` 独立于其他客户端，便于单独 bump。

## 12. Migration Plan

Claude adapter 是纯新增路径，没有存量状态需要迁移。上线顺序：

1. T-1 一手核对与认证实验，产出 `evidence/claude-native-surface.json`。**未完成不得进入实现。**
2. 基础设施解耦（per-client adapter version、`manifest.runtime` 放宽、`_render_tree` / `_staged_auth` 的 else 分支显式化）。这一步**不新增客户端**，只让结构可扩展，单独验证 OMP 无回归。
3. 注册 `claude` 客户端 + portable 渲染分支，`cap render --cli claude` 可用。
4. effective 层：generation、三 Hash、manifest、校验。
5. 启动流程与 env 隔离。
6. receipt、probe、证据分层。
7. 门禁与隔离验证。
8. 文档与 lock / binding 刷新。

每一步都以「OMP 全部既有测试通过 + `.cap/lock.json` 中 OMP 的 `tree_hash` 不变」作为不回归的硬性判据。

## 13. Rollback Strategy

- 回滚 = 从 `CLIENTS` 移除 `"claude"`、删除 `src/agent_system/claude/`、删除 `.cap/runtime/claude.toml`、重跑 `cap lock` 与 `assembly-bind`。
- `renders/claude/**` 是可重建派生物，可直接删除。
- `runtimes/claude/**` 含认证与会话，**回滚时不删除**，只停止使用。
- 第 2 步的基础设施解耦（per-client adapter version 等）在回滚时**保留**：它本身是对既有设计缺陷的修复，与 Claude 无关。
- 任何时刻若发现实现需要写入用户的 `~/.claude` 目录，或需要放宽 `enable_user_assets` / hooks / plugins 的固定门禁，必须停止并升级给负责人，不得自行扩大授权。
