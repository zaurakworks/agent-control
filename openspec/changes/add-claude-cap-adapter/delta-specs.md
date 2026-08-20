# Claude adapter 增量分析（vs OMP adapter）

本文件是给实现者的工程差异清单：哪些能直接复用、哪些必须独立实现、必须改动哪些既有集成点。所有行号基于本变更开始时的 `main`（`26ef782`）。设计理由见 `design-spec.md`，执行顺序见 `tasks.md`。

---

## A. 差异总览

| # | 维度 | OMP | Claude | 差异性质 |
| --- | --- | --- | --- | --- |
| A-1 | 配置注入入口 | 单一文件：`--config <gen>/config.yml` + `PI_CONFIG_FILES` | 无单一入口：`CLAUDE_CONFIG_DIR`（目录）+ `--settings`（文件/JSON）+ 各能力面各自的位置 | **本质差异** |
| A-2 | generation 可写性 | 只读引用即可 | 同样只读引用（T-1 后修正：`--plugin-dir` / `--settings` / `--mcp-config` 均接受 CAS 路径） | **同构**；可写状态另置于 `runtimes/claude/<id>/` |
| A-3 | Skills 注入 | `--skills a,b` + `skills.customDirectories` 指向任意目录 | 发现路径不可自定义，必须物理位于 `$CLAUDE_CONFIG_DIR/skills/` | **本质差异** |
| A-4 | ambient 关闭 | `--no-extensions`、`--no-rules`、`enable*User/Project=false` 一组显式开关 | config dir 重定向 + setting-sources 门禁 + 禁用 auto memory；**managed 层关不掉** | **本质差异** → 证据天花板不同 |
| A-5 | native 文件数量 | 2 个（`config.yml`、`extension/.mcp.json`） | 4+ 个（`settings.json`、`.mcp.json`、`skills/`、`agents/`、`CLAUDE.md`） | 复杂度差异 |
| A-6 | native 格式 | YAML + JSON | 全 JSON + Markdown | 格式差异 |
| A-7 | 中间态 | 无（`config.yml` 既是中间态也是 native） | `claude-config.yaml`（CAP 语义）→ `native/`（Claude 格式）两层 | **有意增加的一层** |
| A-8 | manifest 版本 | `version: 2`，无 `client` 字段 | `version: 1`，含 `client` / `native_projection` / `auth_mode` | 字段扩展 |
| A-9 | `effective_hash` 输入 | `{version, source_context, source_digest, config, launch}` | 额外含 `"client": "claude"` | 防跨客户端碰撞 |
| A-10 | `content_digest` 写入 | `_tree_digest(stage)`（隐式不含 manifest） | `_tree_digest(stage, exclude={".cap-generation.json"})`（显式） | 修正 OMP 的隐式依赖 |
| A-11 | 会话状态位置 | `runtimes/omp/<id>/`（`agent.db`、history） | `runtimes/claude/<id>/configs/<hash>/` 的 mutable 集合 | 布局差异 |
| A-12 | 认证位置 | `runtimes/omp/<id>/`，已验证 | **未知**，T-1 实验确定 | 待定风险 |
| A-13 | Hooks / Plugins | `opaque-staging`，走 `targets/omp/` | 本版本 **不支持**，声明非空即 fail-closed | 范围差异 |
| A-14 | 生效态降级维度 | `{"omp": {"mcps"}}` | `{"claude": {"hooks", "plugins", "managed_settings"} ∪ 待 probe 确定}` | 同机制，不同取值 |
| A-15 | 客户端形态 | 单一 CLI | CLI / IDE / API-SDK / Web 四种，证据等级各不相同 | 需在文档与 receipt 中区分 |
| A-16 | 迁移负担 | 有（从旧状态根迁移） | **无**（纯新增） | Claude 更简单 |

---

## B. 可直接复用的代码

以下函数**语义与 Claude 无关**，应从 `omp/runtime.py` 上提到共享模块 `src/agent_system/adapter/common.py`，由 OMP 与 Claude 共同 import。上提时保持函数体不变，只改导入点，并以「OMP 既有测试全绿」作为等价性判据。

| 函数 | 现位置 | 复用方式 |
| --- | --- | --- |
| `_digest_bytes(payload) -> str` | `omp/runtime.py:118` | 直接上提 |
| `_digest_json(value) -> str` | `omp/runtime.py:121` | 直接上提（紧凑 JSON 约定） |
| `_tree_digest(root, *, exclude=None) -> str` | `omp/runtime.py:954` | 直接上提。已拒绝 symlink / hard link / 特殊文件 |
| `_deep_overlay(base, override) -> dict` | `omp/runtime.py:978` | 直接上提 |
| `_assert_managed_path(root, candidate, label, *, allow_missing=False)` | `omp/runtime.py:130` | 直接上提。路径逃逸与 symlink 链检查 |
| `_validate_private_runtime(root, label)` | `omp/runtime.py:153` | 直接上提。已含 `sys.platform != "win32"` 分支 |
| `_reject_unsafe_tree(root, label)` | `omp/runtime.py:169` | 直接上提 |
| `_safe_remove_tree(root, candidate, label) -> bool` | `omp/runtime.py:770` | 直接上提 |
| `_replace_generation_placeholder(value, generation)` | `omp/runtime.py:1067` | 上提并泛化占位符名（`<PROFILE_GENERATION>` 保持不变，Claude 复用同一占位符） |
| `_generation_source_context(args, portable_hash)` | `omp/runtime.py:1104` | **上提 + 参数化**：把硬编码的 `lock["clients"]["omp"]` 改为 `lock["clients"][client]`，新增 `client` 参数 |
| `_base_args` / `_binding_args` / `_passthrough` / `_run_path` / `_workdir` | `cap/support.py` | 已是共享模块，直接 import |

**CAS 物化骨架**也应上提为一个泛型函数，因为 OMP 与 Claude 的差异只在「写什么文件」：

```python
# adapter/common.py
def materialize_generation(
    *,
    parent: Path,                 # CAS 父目录 renders/<client>/
    effective_hash: str,
    source_tree: Path,            # portable render 临时目录
    write_payload: Callable[[Path], dict[str, object]],  # 写 native 文件，返回 manifest 附加字段
    verify: Callable[[Path], None],
    real_home: Path,
) -> Path:
    """stage → 写入 → content_digest → 写 manifest → os.rename 原子提升。"""
```

覆盖 `omp/runtime.py:1265-1356` 的全部逻辑：CAS 命中检查、`0o700` 目录创建、`_validate_private_runtime`、`_assert_managed_path`、`.stage-<pid>-<ns>` 命名、`os.rename` 冲突处理（rename 失败且目标存在则 `rmtree` stage 并转为校验）、`except BaseException` 清理。

**generation 校验骨架**同理：

```python
def verify_generation(generation: Path, expected: Mapping[str, object]) -> dict[str, object]:
    """逐键比对 manifest + 重算 content_digest。对应 omp/runtime.py:1141。"""
```

`omp/runtime.py:1141` 硬编码了 7 个期望键，泛化为传入 `expected` 映射即可同时服务两个客户端。

**profile engine 侧可直接复用（无需改动）**：`_tree_hash`、`_canonical_json`、`_sha256`、`_safe_relative`、`_materialize_tree`、`_atomic_write`、`_redacted_file_bytes`、`load_project`、`_desired_lock`、`_verify_lock`、`_select_profile`、`_check_project_pollution`、`enforce_asset_closure`、`_validate_external_imports`、`_profile_prompt`、receipt 预约协议（`_prepare_receipt_path` / `_reserve_receipt` / `_commit_receipt` / `_release_receipt`）。

---

## C. 必须独立实现的部分

新建 `src/agent_system/claude/`（`__init__.py` + `runtime.py`）。以下函数**没有可直接复用的 OMP 对应物**，或对应物的语义差异大到必须重写。

### C-1 policy 层

| 函数 | 对标 | 差异 |
| --- | --- | --- |
| `_read_claude_runtime_policy(args)` | `omp/runtime.py:990` | 读 `.cap/runtime/claude.toml`；校验 `client == "claude"`；固定门禁改为 `enable_user_assets is False`、`enable_project_mcp` 为 bool、`auto_memory` 为 bool；**保留未知字段但不投影** |
| `_read_global_claude_preference(args)` | `omp/runtime.py:1014` | 从 `runtimes/claude/<id>/` 读受控 preference。**读取格式取决于 T-1 结论**；若认证与 preference 同文件，必须只读白名单键，不整体读入 |
| `_effective_claude_config(portable, skills, policy, preference)` | `omp/runtime.py:1027` | 产出 `claude-config.yaml` 的 CAP 语义结构（见 design-spec 8.2），**不是** native 结构 |

### C-2 native 投影层（Claude 独有）

```python
def _project_claude_native(config: Mapping[str, object], generation: Path) -> dict[str, bytes]:
    """claude-config.yaml → {"native/settings.json": b"…", "native/.mcp.json": b"…", …}

    这是本 adapter 中唯一允许出现 Claude native 键名的函数。
    所有键名必须在 evidence/claude-native-surface.json 中留证。
    """
```

OMP 没有对应物（它的 `config.yml` 既是中间态也是 native）。这是本变更最大的新增代码块，也是唯一需要随 Claude 版本演进的部分。要求：

- 纯函数，不做 IO（除接收 `generation` 路径用于占位符替换）；便于单测穷举字段映射。
- 未映射的 `claude-config.yaml` 字段必须显式报错，不得静默丢弃。
- 输出 `unsupported` 列表供 manifest 记录。

### C-3 ~~水合层~~ 已取消（T-1 实测）

初稿假设 Skill 必须放进可写的 `CLAUDE_CONFIG_DIR`，因而需要一个水合层。实测证明 `--plugin-dir` 可 session 级只读交付 Skill，因此 `_hydrate_claude_config`、`_verify_hydrated_config`、`HydrationPlan`、`HydratedConfig`、`hydration_digest` **全部不实现**。

Claude 与 OMP 在这一点上是**同构**的：generation 只读引用，可写状态（认证、会话）位于 `runtimes/claude/<runtime-id>/`，按 runtime-id 而非 generation 分配。

### C-4 生成与启动层

| 函数 | 对标 | 差异 |
| --- | --- | --- |
| `_materialize_claude_generation(args, env)` | `omp/runtime.py:1180` | 结构镜像；调用 `materialize_generation` 骨架；`effective_hash` payload 加 `client` 字段；`content_digest` 显式 `exclude` |
| `_verify_claude_generation(...)` | `omp/runtime.py:1141` | 比对键从 7 个扩到 9 个（加 `client`、`native_projection`） |
| `_claude_command(generation, config_dir, skills, forwarded)` | `omp/runtime.py:1358` | flag 集合完全不同；skills 不通过命令行传（靠目录发现） |
| `_claude_env(base_env, runtime_dir, real_home)` | `omp/runtime.py:1389` | `CLAUDE_CONFIG_DIR` 替代 `PI_*`（指向 runtime 目录）；凭据置空集合改为 Claude 相关项。**不设 `CLAUDE_CODE_DISABLE_AUTO_MEMORY`**——该变量不存在于 CLI 面 |
| `_write_claude_receipt(...)` | `omp/runtime.py:1422` | 新增 `auth_mode`、`post_run_content_digest`、`evidence`、`effective_observations`、`ambient_floor` |
| `_run_claude(args, env)` | `omp/runtime.py:1467` | 多一步运行后 `content_digest` 复查；无水合步骤 |
| `_require_claude_runtime_ready(args)` | `omp/runtime.py:923` | 检查 `runtimes/claude/<id>/` 私有性与标记文件；**无迁移逻辑** |

### C-5 profile engine 侧的 Claude 分支

| 位置 | 新增内容 |
| --- | --- |
| `profile/cli.py:4304` `_render_tree` | `elif client == "claude":` → `claude-config.yaml`(`b"{}\n"`)、`mcp.json`(`_claude_mcp`)、`system-prompt.md` |
| 新增 `_claude_mcp(definitions) -> bytes` | 对标 `_omp_mcp`（`:4438`）/ `_qoder_mcp`（`:4426`）；格式待 T-1 核对 |
| `profile/cli.py:1262` `build_launch` | 新增 `claude` 分支（供 `--fresh` 一次性路径使用） |
| `profile/cli.py:1906` `_configured_mcp_names` | 新增 `claude` 分支（读 `mcp.json` 的 `mcpServers`，与 else 分支一致，但需显式化） |
| `profile/cli.py:1212` `_staged_auth` | 新增 `claude` 分支；具体 vault 布局取决于 T-1 |
| `profile/cli.py:384` `FORBIDDEN_CLIENT_ARGUMENTS` | 新增 `"claude"` 条目，**最高优先级防御**，见下 |
| `profile/cli.py:2089` `run_observed` 的 `client_limited` | 新增 `"claude": {"hooks", "plugins", "managed_settings", …}` |
| `profile/cli.py:3272` `_check_global_pollution` | 新增 `_claude_config_has_active_capability()`，对标 `_codex_config_has_active_capability`（`:2971`）/ `_qoder_config_has_active_capability`（`:3085`）。**不新增此分支会导致每次启动都触发全局污染门** |
| `profile/cli.py:3237` `_global_path_is_passive` | 新增 Claude 路径的 passive 判定 |

`FORBIDDEN_CLIENT_ARGUMENTS["claude"]` 的初始集合（每一项都能绕过 CAP 门禁，必须在 `--` 之后被拒绝）：

```text
--settings            # 会覆盖 CAP 注入的命令行层 settings
--setting-sources     # 会重新打开 user/project 设置源
--mcp-config          # 会引入未声明 MCP
--plugin-dir          # 会旁路加载 plugin
--plugin-url          # 同上，且引入远端来源
--agents              # 会引入未声明 subagent
--add-dir             # 会扩大文件访问面
--permission-mode     # 会改变权限模式（含 bypassPermissions）
--dangerously-skip-permissions
--system-prompt       # 会替换整个系统提示词（--append-system-prompt 由 CAP 注入）
--system-prompt-file
--bare / --safe-mode  # 会改变自动发现语义，使 hash 与实际不符
```

具体 flag 名与是否存在**以 T-1 核对结果为准**；核对不到的 flag 保留在拒绝列表中不会造成损害（用户本来也传不进去），核对到但遗漏才是缺陷。因此该列表按「宁可多列」处理。

**已有先例可直接对标**：`FORBIDDEN_CLIENT_ARGUMENTS["qoder"]`（`profile/cli.py:388`）已经拒绝了 `--add-dir`、`--allowed-mcp-server-names`、`--append-system-prompt`、`--config-dir`、`--mcp-config`、`--plugin-dir` 等同类参数。Claude 条目的判定标准与之一致：**凡是能重新指定配置来源、能力来源或提示词来源的参数一律拒绝**。

---

## D. 集成点（必须改动的既有代码）

按依赖顺序排列。**I-1 到 I-5 是纯基础设施解耦，不引入 Claude，应独立提交并单独验证 OMP 无回归。**

### I-1 客户端注册（两处重复定义，必须同步）

```text
src/agent_system/profile/cli.py:37   CLIENTS = ("codex", "qoder", "omp")
src/agent_system/cap/config.py:47    CLIENTS = ("codex", "qoder", "omp")
```

两处都要加 `"claude"`。同时 `profile/cli.py:38` 的 `CLIENT_EXECUTABLES` 加 `"claude": "claude"`。

> **顺带**：两处重复的 `CLIENTS` 本身是隐患。本变更**不**做统一（超出范围），但在实现中加一条断言或测试保证两者相等。

### I-2 `_render_tree` 与 `_staged_auth` 的 `else` 分支必须先显式化

```text
profile/cli.py:4324-4338   _render_tree：omp 是 else 分支（:4335）
profile/cli.py:1212-1247   _staged_auth：omp 是 else 分支（:1236）
```

**在加入 `claude` 之前**，必须先把这两处的 `else` 改为 `elif client == "omp":` + 末尾 `raise ProfileError(f"unsupported client: {client}")`。否则新客户端会静默落入 OMP 分支，拿到 OMP 的渲染结果和 OMP 的认证暂存布局——这是一个会通过全部现有测试的静默错误。

### I-3 `CLIENT_ADAPTER_VERSION` 必须改为 per-client

```text
profile/cli.py:39   CLIENT_ADAPTER_VERSION = 8      # 单个全局 int，所有客户端共用
```

该值经 `_generation_source_context`（`omp/runtime.py:1115`，读 `lock["clients"]["omp"]["adapter_version"]`）进入 `source_context` → `source_digest` → `effective_render_hash`。若 Claude 与 OMP 共用一个版本号，**每次为 Claude bump 版本都会作废全部 OMP generation**，反之亦然。

改为：

```python
CLIENT_ADAPTER_VERSION = {"codex": 8, "qoder": 8, "omp": 8, "claude": 1}
```

`.cap/lock.json` 的 `clients.<name>.adapter_version` 结构不变（已经是 per-client 的），只是写入源变了。需确认 `_desired_lock` 中写入该字段的位置同步修改，且 **OMP 的值必须保持 8**，否则现有 OMP generation 全部失效（可通过「lock 中 OMP 的 `adapter_version` 与 `tree_hash` 均不变」验证）。

### I-4 `manifest.runtime` 与 `profile.runtime` 的硬等值检查必须放宽

```text
profile/cli.py:634   set(raw_runtime) != {"omp"}  → error
profile/cli.py:636   runtime_source = raw_runtime["omp"]        # 单键读取，需改为遍历
profile/cli.py:643-645  _expect_keys(...) + runtime_data["client"] != "omp"
profile/cli.py:719   set(raw_profile_runtime) != {"omp"}  → error
profile/cli.py:721   raw_profile_runtime["omp"]                 # 同样是单键读取
```

三处等值检查都改为「必须是已知客户端的非空子集」；**同时把 `raw_runtime["omp"]` / `raw_profile_runtime["omp"]` 这两处单键读取改为遍历**，每个客户端各解析并校验自己的 policy 文件（`client` 字段必须与表键一致）。只改等值检查而漏掉单键读取，会得到一个「校验通过但只加载 omp policy」的静默错误。改完后 `.cap/manifest.toml` 可写：

```toml
runtime = { omp = ".cap/runtime/omp.toml", claude = ".cap/runtime/claude.toml" }
```

role profile 可写 `runtime = { omp = "default", claude = "default" }`。

### I-5 hooks / plugins 的 `targets/<client>` 要求

```text
profile/cli.py:4359-4381   _render_tree：缺 targets/<client> → ProfileError(f"{kind[:-1]} {name} lacks required {client} target")
profile/cli.py:2733        _validate_capability_tree：targets/ 子目录必须是 CLIENTS 的非空子集
```

加入 `claude` 后，**每个已有 hook / plugin 都会被要求提供 `targets/claude/`**。

当前 `.cap/lock.json` 中两个 role 的 `inventory.hooks` 与 `inventory.plugins` 均为 `[]`，因此**实际 blast radius 为零**。但这是一个必须在实现中显式验证的前提（T-2 的验收项），且将来新增 hook / plugin 时会立即触发。

本变更的选择：**不改这条规则**（保持 fail-closed），并在 `docs/profile.md` 中记录「新增 hook / plugin 时必须同时提供全部已注册客户端的 target，或先把该客户端的能力语义标为 unsupported」。

### I-6 lock 与 evidence 的全客户端循环

```text
profile/cli.py:4139   _desired_lock：为所有 CLIENTS 渲染并写入 profiles.<role>.clients.<client>.tree_hash
profile/cli.py:4564   _materialize_evidence：遍历所有 CLIENTS
profile/cli.py:4605   _verify_evidence：遍历所有 CLIENTS 重渲染并逐字节比对
```

无需改代码，但有两个后果必须验证：

1. `cap lock` 后 `.cap/lock.json` 会新增 `clients.claude`（`adapter_version` + `executable`）与每个 role 的 `clients.claude.tree_hash`。这是预期变更，需在 PR 中作为证据展示。
2. **OMP / codex / qoder 的 `tree_hash` 必须完全不变**。任何变化都说明 I-2 的分支显式化改错了。

> 注：`_materialize_evidence` / `_verify_evidence` 在 `project.overlay is None` 时直接返回（`:4515` / `:4592`），本仓无 overlay，因此 evidence 目录在默认路径下不产生。不在本变更中改这个门。

### I-7 CAP CLI 层

```text
cap/cli.py:820   _run_selected：if args.cli == "omp" and not args.fresh → _run_omp_agent_home
cap/cli.py:739   _render_preview：if args.cli == "omp" → _materialize_profile_generation
cap/cli.py:37-58 从 omp.runtime 直接 import 私有函数
```

改为按客户端分派的表结构，避免继续堆 `if`：

```python
EFFECTIVE_ADAPTERS = {
    "omp":    (_run_omp_agent_home,    _materialize_profile_generation, _omp_runtime_id,    _agent_home_dir),
    "claude": (_run_claude,            _materialize_claude_generation,  _claude_runtime_id, _claude_runtime_dir),
}
```

`_run_selected` 与 `_render_preview` 查表；查不到则走既有的 `subprocess` 通用路径（codex / qoder 保持现状）。

同时：

- `cap/cli.py:319/345/372` 三处 `--cli` 的 `choices=CLIENTS` 自动包含 `claude`（因为 I-1 已改），但 **help 文案需更新**（当前写「默认 omp」，需说明 claude 可用）。
- `DEFAULT_CLI` 保持 `"omp"`。本变更**不改默认客户端**；裸 `cap` 的 TUI（`_tui_use`，`:681` 硬编码 `args.cli = DEFAULT_CLI`）行为不变。是否让 TUI 支持选择客户端是独立决定，不在本变更范围。
- `cap/cli.py:155` 的 parser description 与 `:157` 的 epilog 需要更新示例。

### I-8 `.cap` 声明文件

| 文件 | 改动 |
| --- | --- |
| `.cap/manifest.toml` | `runtime` 表加 `claude = ".cap/runtime/claude.toml"` |
| `.cap/runtime/claude.toml` | 新建，见 design-spec 8.1 |
| `.cap/profiles/general.toml` | `runtime = { omp = "default", claude = "default" }` |
| `.cap/profiles/agent-assembler.toml` | 同上 |
| `.cap/lock.json` | 由 `cap lock` 重新生成，不手工编辑 |

### I-9 测试

| 文件 | 改动 |
| --- | --- |
| `tests/claude/test_claude_runtime.py` | 新建，对标 `tests/omp/test_runtime_policy_v3.py` |
| `tests/claude/test_claude_native_projection.py` | 新建，穷举 `_project_claude_native` 的字段映射与未映射字段报错 |
| `tests/claude/test_claude_launch.py` | 新建，启动 argv/env 构造、禁止参数拒绝、运行后 digest 复查 |
| `tests/profile/test_profile.py` | 补 `claude` 的 render / lock / forbidden-args 用例；补 `CLIENTS` 两处定义一致性断言 |
| `tests/cap/test_cap.py` | 补 `--cli claude` 的 show / render / 分派用例 |
| `tests/omp/test_runtime_policy_v3.py` | **不改**。它必须在共享模块上提后仍然全绿，作为等价性判据 |

### I-10 文档

| 文件 | 改动 |
| --- | --- |
| `docs/profile.md` | 「源模型」加 `.cap/runtime/claude.toml`；「Runtime policy」加 Claude 段；「证据分层」加 Claude 天花板；**改写「Adapter 合同」章节**——当前写的是「Claude adapter 当前未实施…必须报告 unknown」，实施后必须更新为真实的能力与限制描述 |
| `docs/cap-guide.zh-CN.md` | 加「用 Claude 启动」小节与故障排查（水合漂移、全局污染、长路径） |
| `docs/maintenance.zh-CN.md` | 「修改后」检查清单加 `cap show general --cli claude`；加 Claude CAS / 水合目录的维护与清理说明 |
| `README.md` | 「文件职责」中 `src/agent_system/` 一条补充 Claude 实现 |
| `openspec/changes/redesign-agent-system-v3-runtime-assembly/tasks.md` | 5.5 / 5.6 的 Claude 合同已被本变更兑现，可在归档时注明后继变更 id |

---

## E. 实现顺序约束（有向依赖）

```text
T-1 一手核对 + 认证实验
      │  （结论可能反向修改 design-spec 3.1 / 8.1 / C-2）
      ▼
I-2 else 分支显式化 ──► I-3 per-client adapter version ──► I-4 runtime 放宽
      │                                                          │
      └──────────────► B 共享模块上提 ◄─────────────────────────┘
                              │
                              ▼
                    I-1 注册 claude 客户端
                              │
                              ▼
              C-5 portable 渲染分支 ──► cap render --cli claude 可用
                              │
                              ▼
              C-1 policy ──► C-2 native 投影 ──► C-4 generation + 三 Hash
                                                        │
                                                        ▼
                                              C-3 水合 ──► C-4 启动 + receipt
                                                        │
                                                        ▼
                                          I-7 CAP CLI 分派 ──► I-8 .cap 声明 ──► I-9/I-10
```

关键约束：

- **I-2 必须早于 I-1**。先显式化再注册，否则新客户端静默落入 OMP 分支。
- **I-3 必须早于任何 generation 实现**，否则会作废存量 OMP generation。
- **T-1 必须早于 C-2**，否则投影层写的是猜测出来的 native 键名。
- **B（共享模块上提）应该是一次独立提交**，判据是 OMP 全部既有测试不改动且全绿。
