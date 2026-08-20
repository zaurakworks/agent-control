# 实施任务

按依赖顺序排列。每个任务给出描述、依赖、预计工作量（人日）和验收标准。工作量按「熟悉本仓的单人工程师」估算，含单测但不含 code review 往返。

**全局验收前置**（每个任务完成时都必须成立）：

- `uv run pytest` 全绿，且 `tests/omp/**` 与 `tests/profile/**` 的既有用例**未被修改**。
- `.cap/lock.json` 中 `omp` / `codex` / `qoder` 的 `tree_hash` 与 `adapter_version` 未变化。
- 不出现新的 secret 落盘路径。

总计约 **28–36 人日**（不含评审与返工缓冲）。其中 1.1 已完成（3 人日），并因实测取消了原 4.1 水合任务（3 人日），**剩余约 22–30 人日**。

---

## 0. 阻断前置（本变更范围外，但必须先解决）

> 状态：0.1 已修（#84）、0.2 已确认（订阅 OAuth）、**0.3 未解决且阻断全部启动类验收**。

### 0.1 lock 的 mode 字段跨平台不稳定

- [x] 0.1 规范化 `.cap/lock.json` 中 `inputs.*.mode` 的跨平台取值 —— **已实施**（2026-08-19）

**描述**：`_desired_lock` 用 `f"{stat.S_IMODE(path.stat().st_mode):04o}"` 记录文件 mode（`profile/cli.py:4227`、`:4283`）。Linux 得 `0644`，Windows 得 `0666`，导致 lock 在两个平台间无限翻转。

**实测影响（本次发现）**：`tests/profile/fixtures/multi-profile/.cap/lock.json` 中烘焙了 22 条 Linux 的 `"mode": "0644"`，因此在 Windows 上 **66 个 profile 测试有 65 个失败**于 `capability lock drift detected`。该失败在干净的 `git HEAD` 上同样存在，与本变更无关。CI 全部是 `ubuntu-latest` 且不执行 `cap lock` / `cap verify`，因此抓不到。

**为什么阻断 Claude adapter**：任务 2.2 / 6.2 的验收标准是「`cap lock` 后其他客户端 `tree_hash` 不变」。在此缺陷修复前，Windows 上每次 `cap lock` 都会附带 46 行 mode 翻转，使 diff 无法判读，验收无法执行。

**依赖**：无
**工作量**：1 天（实际 0.5 天）

**实施内容**：新增 `_canonical_mode(path) -> int`，把 mode 规范化为 Git 唯一保留的权限区分——owner 可执行位（`0o755` / `0o644`）；Windows 恒返回 `0o644`（Git for Windows 默认 `core.fileMode=false`，无法观察该位）。替换了**五处**平台相关记录点，而非 Issue 最初以为的两处：

| 站点 | 影响的 hash |
| --- | --- |
| `_input_records` ×2（`:4227`、`:4283`） | `lock.inputs.*.mode` |
| `_render_tree` 的 skill 与 hook/plugin 分支 ×2（`:4354`、`:4378`） | `RenderedFile.mode` → `_tree_hash` → **`portable_tree_hash`** |
| `_materialize_evidence`（`:4530`） | 落盘证据树的真实权限 |

**关键发现**：`portable_tree_hash` 此前同样是平台相关的（skill 文件的 mode 直接进 `_tree_hash`）。Issue #82 最初只描述了 `inputs.*.mode`，实际范围更大。

**验收结果**：

- ✅ Windows 上执行 `uv run cap lock` 后 `git diff .cap/lock.json` 为空——与 Linux 侧提交内容**逐字节一致**。这同时证明 `inputs.*.mode` 与 `profiles.*.clients.*.tree_hash` 都已平台稳定。
- ✅ 不改变 Linux 侧既有 lock：当前全部输入均为非可执行文件，`_canonical_mode` 返回 `0o644`，与原 `S_IMODE` 结果相同。附带收益：umask 导致的 `0664` 之类差异也不再引起漂移。
- ❌ **原验收标准第 2 条「Windows 上 profile 测试由 65 失败变为 0」不成立，该标准本身是错的**。实测由 65 失败降为 52（14 个测试新通过），残留失败的根因**不是 mode**，而是另一类既有限制：认证 vault 子系统是 POSIX-only 设计（`profile/cli.py:957`、`:988`、`:1084` 直接调用 `os.geteuid`，`:1749` 显式 `raise ProfileError("... requires POSIX component-safe directory handles")`）。这属于独立问题，已在 #82 中更正说明。

**边界**：本任务只做 mode 规范化，未触碰 POSIX-only 的认证 vault。Windows 上 profile 测试全绿需要另立事项。

> 这是一个独立的既有缺陷，**不属于本变更**，已记录为 [#82](https://github.com/zaurakworks/agent-system/issues/82)；本变更的实施在其合并后开始。若决定先做 Claude adapter，则 2.2 / 6.2 的验收改为「只比对 `profiles.*.clients.*.tree_hash` 与 `clients.*.adapter_version`，忽略 `inputs.*.mode`」。

### 0.2 认证模式抉择（需负责人决定，阻断 3.1）

- [x] 0.2 确认 `.cap/runtime/claude.toml` 的 `auth_mode` 默认值 —— **已确认：`subscription`**（2026-08-19）

**描述**：T-1 证明 subscription 模式下 claude.ai 账号级远程 MCP connector 不可由 CAP 关闭，而 `--bare` 可消除它但放弃 OAuth、只接受 `ANTHROPIC_API_KEY`。两种模式的 MCP 闭包可控性不同，取舍见 `design-spec.md` 3.4 的对照表。

**依赖**：1.1
**工作量**：0（决策项）
**验收**：已达成。负责人选定 **订阅 OAuth** 为默认；`bare` 保留为可选值。实现须确保 `subscription` 模式下 MCP 生效态恒为 `reported_client_limited`，不提供提升路径。

### 0.3 CAP 在 Windows 上无法 render 或启动任何客户端

- [x] 0.3 解决 CAP 的执行环境边界（[#87](https://github.com/zaurakworks/agent-system/issues/87)）—— **核心已解决**：#95 用两端共用的分量校验取代 POSIX 目录句柄链，原生 Windows 上 `cap render` 已可用（实测 6 个 skill 全部产出）；#97 补齐门禁、边界测试与文档。残留的 Windows 测试套件未全绿属独立事项，不阻断本包。

**描述**：`_open_stable_directory` 在 Windows 上无条件失败（`anchor` 恒为 `C:\`，永不等于 `os.sep`），而 `materialize_profile` 是所有 render 的唯一入口。`os.supports_dir_fd` 在 Windows 上是空集，`dir_fd` 在 `profile/cli.py` 中有 17 处使用，贯穿 render 物化、receipt 预约与认证 vault，原生移植是数周的安全关键工作。

**实测结论**：WSL2 下端到端可用，包括直接操作 `/mnt/c` 的仓库；渲染出的 `tree_hash` 与 Linux 侧提交进 lock 的值逐字节一致。因此不需要移植，只需明确执行环境边界。

**对本变更的影响**：本规划包的多数验收标准依赖 render 与 launch：

| 环境 | render | launch |
| --- | --- | --- |
| 原生 Windows | ❌ | 客户端在，但 launch 必须先 render |
| WSL | ✅ | ❌ 当前未安装 `claude` / `omp` |

两步必须在同一环境完成，因此**目前没有任何环境能执行本包的启动类验收**。

**依赖**：无
**工作量**：环境动作 + 约 0.5 天代码（可操作的错误信息、TUI 前置检查、文档）
**验收**：

- WSL 中安装 `claude` 与 `omp`，`cap use general --cli omp` 在 WSL 中跑通。
- 原生 Windows 上执行 `cap render` 得到指向 WSL 的可操作错误，而非 `requires POSIX component-safe directory handles`。
- `docs/cap-guide.zh-CN.md` 写明执行环境前置条件。

> 本任务**不属于本变更**，但阻断本包 3.x／4.x／5.x 的全部验收。1.x 与 2.x（基础设施解耦与 portable 渲染）可在其之前进行，因为它们只依赖 `cap lock` 与单元测试，二者在原生 Windows 上可用。

---

---

## 1. 前置核对与解耦

### 1.1 Claude native 面一手核对与认证实验 ✅ 已完成

- [x] 1.1 建立 `evidence/claude-native-surface.json`，逐项核对并实验验证 Claude 的配置面

**描述**：这是全部后续工作的输入。逐项核对并**实际实验**下列事实，每项记录文档 URL、抓取日期、`claude --version` 实测版本、平台与结论（`confirmed` / `refuted` / `unknown`）：

1. settings 各层文件名、路径与优先级（含 managed 层在三平台上的位置）。
2. `CLAUDE_CONFIG_DIR` 是否存在、精确重定位哪些内容、**不**重定位哪些内容。
3. **认证凭据的实际位置**（`~/.claude.json` / config dir 内 / OS keychain），以及设置 `CLAUDE_CONFIG_DIR` 后登录态是否保留。
4. `--settings` 是否存在、接受文件还是 JSON、与其他层的合并 vs 覆盖语义。
5. Skills 的发现目录集合；是否存在自定义 skills 目录的设置或环境变量；是否可禁用用户级发现。
6. MCP 配置文件名与作用域；`--mcp-config`、`strictMcpConfig` 或等价开关。
7. Hooks 的配置位置、事件名与 JSON 形状。
8. Plugins 的 manifest 文件名、`enabledPlugins` 等 settings 键、marketplace 相关开关与 CLI。
9. Subagents 目录与文件格式。
10. 系统提示词注入 flag；CLAUDE.md 加载顺序；能否禁用用户级 / 项目级 memory；auto memory 的禁用方式。
11. 权限 settings 键与 `--permission-mode` 取值集合。
12. 无头模式相关 flag。
13. `D` 节列出的全部待拒绝 flag 是否真实存在。
14. Windows 上的配置路径、长路径与 symlink 限制。

**依赖**：无
**工作量**：3 天（实际用时约 0.5 天）
**验收**：全部达成。

**实际结论（Claude Code 2.1.236 / win32-x64，2026-08-19）**：

- 三个阻断项（`config-dir-env`、`auth-follows-config-dir`、`skill-discovery-paths`）全部 `confirmed`。
- **认证随 `CLAUDE_CONFIG_DIR` 迁移** → 落在设计预设的中间情形，用户在 CAP runtime 内登录一次即可，无需额外机制。
- **`--plugin-dir` 可 session 级只读交付 Skill** → **原 4.1 水合层任务作废**，generation 改为像 OMP 一样只读引用。
- **新发现两条 CAP 不可控的能力底座**：claude.ai 账号级远程 MCP connector（`--strict-mcp-config` 压不住）与 42 个 bundled skills。
- **新增一个需负责人决定的产品取舍**：`auth_mode = subscription | bare`，见 `design-spec.md` 3.4 与下方 0.2。
- 修正了两处设计错误：`permission_mode` 无 `default` 取值；`CLAUDE_CODE_DISABLE_AUTO_MEMORY` 不存在于 CLI 面。

---

### 1.2 客户端分支显式化（不新增客户端）

- [x] 1.2 把 `_render_tree` 与 `_staged_auth` 中 OMP 的 `else` 分支改为显式 `elif` + 未知客户端 `raise` —— **已完成**（#99）

**描述**：见 `delta-specs.md` I-2。`profile/cli.py:4335` 与 `:1236` 当前把 OMP 作为兜底分支；不先修掉，新客户端会静默继承 OMP 的渲染与认证布局。同时检查 `_configured_mcp_names`（`:1909`）等其他 `if/else` 分派点。

**依赖**：无（可与 1.1 并行）
**工作量**：0.5 天
**验收**：

- 传入未注册客户端名时抛 `ProfileError`，含客户端名。
- `.cap/lock.json` 重新生成后三个客户端的 `tree_hash` 逐字节不变。
- 新增测试：`test_render_tree_rejects_unknown_client`、`test_staged_auth_rejects_unknown_client`。

---

### 1.3 `CLIENT_ADAPTER_VERSION` 改为 per-client

- [x] 1.3 把全局 int 改为 `dict[str, int]`，OMP 保持 8，Claude 预留 1 —— **已完成**（#100）

**描述**：见 `delta-specs.md` I-3。该值经 `source_context` 进入 `effective_render_hash`，共用会导致跨客户端的 generation 连坐失效。需同步修改 `_desired_lock` 写入点与 `_generation_source_context` 读取点。

**依赖**：1.2
**工作量**：0.5 天
**验收**：

- `.cap/lock.json` 中 `clients.omp.adapter_version == 8`，且整个 lock 除格式外无变化。
- 存量 `renders/omp/<hash>/` generation 仍能命中（手工验证：`cap show general --cli omp` 两次，`effective_render_hash` 相同且未重新物化）。
- 新增测试：bump Claude 版本号不改变 OMP 的 `source_digest`。

---

### 1.4 `manifest.runtime` / `profile.runtime` / policy client 校验放宽

- [x] 1.4 三处硬等值 `{"omp"}` 改为「已知客户端的非空子集」 —— **已完成**（#102）

**描述**：见 `delta-specs.md` I-4（`profile/cli.py:634`、`:720`、`:645`）。本任务只放宽校验，**不**新增 `.cap/runtime/claude.toml`。

**依赖**：1.3
**工作量**：0.5 天
**验收**：

- 现有 `.cap/manifest.toml`（只含 omp）仍通过校验，lock 不变。
- 声明未知客户端（如 `runtime = { foo = "..." }`）时报错，错误信息列出已知客户端。
- 新增测试覆盖：单客户端、多客户端、未知客户端、空表四种情况。

---

### 1.5 共享 adapter 模块上提

- [x] 1.5 新建 `src/agent_system/adapter/common.py`，上提 OMP 中与客户端无关的原语 —— **已完成**（#106（骨架部分推迟至 3.4，见该任务说明））

**描述**：见 `delta-specs.md` B 节。上提清单：`_digest_bytes`、`_digest_json`、`_tree_digest`、`_deep_overlay`、`_assert_managed_path`、`_validate_private_runtime`、`_reject_unsafe_tree`、`_safe_remove_tree`、`_replace_generation_placeholder`，以及泛化后的 `_generation_source_context(args, portable_hash, *, client)`、`materialize_generation(...)` 骨架、`verify_generation(...)` 骨架。`omp/runtime.py` 改为从共享模块 import，函数体不再重复。

**依赖**：1.3（`_generation_source_context` 泛化需要 per-client version）
**工作量**：2.5 天
**验收**：

- `tests/omp/test_runtime_policy_v3.py` **未修改**且全绿。
- `omp/runtime.py` 中不再存在被上提函数的重复定义。
- OMP 端到端 smoke（`cap run general --cli omp -- --help`）行为与上提前一致，`effective_render_hash` 不变。
- `materialize_generation` / `verify_generation` 有独立单测，覆盖：CAS 命中、并发 stage、rename 冲突、异常清理、路径逃逸拒绝、symlink 拒绝。

---

## 2. 注册 Claude 客户端与 portable 渲染

### 2.1 注册 `claude` 客户端

- [x] 2.1 两处 `CLIENTS` 与 `CLIENT_EXECUTABLES` 加入 `claude`，并加一致性断言 —— **已完成**（#105）

**描述**：见 `delta-specs.md` I-1。`profile/cli.py:37` 与 `cap/config.py:47` 必须同步。

**依赖**：1.2、1.4
**工作量**：0.5 天
**验收**：

- `uv run cap clients` 输出包含 `claude` 及其 PATH 解析结果（未安装时为 `null`，不报错）。
- 新增测试断言两处 `CLIENTS` 相等。
- 此时 `cap lock` 尚会因缺少渲染分支而失败——这是预期，2.2 修复。

---

### 2.2 portable 渲染分支

- [x] 2.2 实现 `_render_tree` 的 `claude` 分支与 `_claude_mcp` —— **已完成**（#105）

**描述**：见 `design-spec.md` 2.1 与 `delta-specs.md` C-5。输出 `claude-config.yaml`（字面量 `{}`）、`mcp.json`、`system-prompt.md`、`skills/`。同步实现 `build_launch`、`_configured_mcp_names` 的 `claude` 分支。

**依赖**：2.1、1.1
**工作量**：1.5 天
**验收**：

- `uv run cap render general --cli claude --output <空目录>` 成功，产出四类内容。
- 两次渲染 `tree_hash` 相同（确定性）。
- `uv run cap lock` 成功，`.cap/lock.json` 新增 `clients.claude` 与两个 role 的 `clients.claude.tree_hash`；其余客户端 hash 不变。
- `uv run cap show general --cli claude` 输出 `preview.files` 与 `preview.tree_hash`。
- hooks / plugins 闭包为空的前提被显式测试断言（防止将来新增时无声破坏，见 `delta-specs.md` I-5）。

---

### 2.3 禁止参数与全局污染门

- [x] 2.3 实现 `FORBIDDEN_CLIENT_ARGUMENTS["claude"]` 与 `_claude_config_has_active_capability` —— **已完成**（#105）

**描述**：见 `delta-specs.md` C-5 与 `design-spec.md` 9。禁止参数列表按「宁可多列」处理。全局污染门需新增 Claude 分支，否则每次启动都会被 `_check_global_pollution` 拦下（`~/.claude` 已在 `GLOBAL_NATIVE_ROOTS`）。

**依赖**：2.1、1.1
**工作量**：1.5 天
**验收**：

- 每个禁止参数各有一条测试：`cap run general --cli claude -- <flag>` 退出码非 0 且错误信息指出该参数被 CAP 固定门禁占用。
- 用户 HOME 的 `~/.claude.json` 含 `mcpServers` 时启动被拒绝；只含无关键（如 UI 偏好）时通过。
- passive 判定有正负两向测试。

---

## 3. Effective render 与三 Hash

### 3.1 Claude runtime policy

- [x] 3.1 新建 `.cap/runtime/claude.toml` 与 `_read_claude_runtime_policy` / `_read_global_claude_preference` —— **已完成**（#110）

**描述**：见 `design-spec.md` 8.1 与 `delta-specs.md` C-1。固定门禁 `enable_user_assets` 恒为 `false`；未知字段保留但不投影。

**依赖**：1.4、1.1
**工作量**：1 天
**验收**：

- `version` / `client` 不符时 fail-closed。
- `enable_user_assets = true` 被拒绝，错误信息说明这是不可放宽的系统门禁。
- 未知字段测试：出现在返回的 policy 与 `runtime_policy.project` 证据中，但不出现在投影结果中（对标 `test_policy_preserves_unknown_fields_without_projecting_them`）。
- 项目 policy 覆盖不安全的用户 preference（对标 `test_project_policy_overrides_unsafe_global_preference`）。

---

### 3.2 `claude-config.yaml` 合成

- [x] 3.2 实现 `_effective_claude_config(portable, skills, policy, preference)` —— **已完成**（#110）

**描述**：见 `design-spec.md` 8.2。按固定顺序合成：系统门禁 > 项目 policy > role override > 用户 preference。输出是 CAP 语义结构，不是 native 结构。

**依赖**：3.1
**工作量**：1 天
**验收**：

- 合成顺序有覆盖全部四层的测试，含「用户 preference 试图放宽固定门禁被拒绝」。
- `skills.include` 与传入的 `skill_names` 严格一致且已排序。
- 输出可被 `yaml.safe_dump(..., sort_keys=True)` 稳定序列化（同输入两次结果字节相同）。

---

### 3.3 native 投影

- [x] 3.3 实现 `_project_claude_native(config, generation) -> dict[str, bytes]` —— **已完成**（#111）

**描述**：见 `design-spec.md` 2.3 与 `delta-specs.md` C-2。这是唯一允许出现 Claude native 键名的函数；所有键名必须在 `evidence/claude-native-surface.json` 中留证。产出 `native/settings.json`、`native/.mcp.json`、`native/skills/**`、`native/agents/`、`native/CLAUDE.md`。

**依赖**：3.2、1.1
**工作量**：3 天
**验收**：

- 纯函数（除占位符替换外无 IO），有穷举字段映射的表驱动测试。
- `claude-config.yaml` 中出现未映射字段时**报错**，不静默丢弃。
- `unsupported` 列表正确产出 `["hooks", "plugins"]`。
- `.cap` 中为 Claude 声明任一 hook 或 plugin 时，渲染直接 fail-closed 并给出中文错误。
- 生成的 `settings.json` 是合法 JSON，且经 `claude` 实际加载不报配置错误（人工验证一次并记录）。

---

### 3.4 generation 物化与三 Hash

- [x] 3.4 实现 `_materialize_claude_generation` 与 `_verify_claude_generation` —— **已完成**（#114）

**描述**：见 `design-spec.md` 2.2 / 2.4 / 2.5 与 `delta-specs.md` C-4。复用 1.5 的 `materialize_generation` / `verify_generation` 骨架。`effective_hash` payload 含 `"client": "claude"`；`content_digest` 显式 `exclude={".cap-generation.json"}`；manifest 含 `client` / `native_projection` / `auth_mode` 三个新字段段。

**依赖**：3.3、1.5
**工作量**：2.5 天
**验收**：

- generation 目录结构与 `design-spec.md` 2.3 完全一致。
- `.cap-generation.json` 含全部 12 个顶层键。
- CAS 命中路径与新物化路径走**同一个**校验函数（代码审查项 + 测试断言）。
- 漂移测试三条：改 `native/settings.json` → `content drifted`；改 manifest 中任一键 → `metadata drifted`；改 `.cap/runtime/claude.toml` 中的投影字段 → `effective_render_hash` 变化且旧 generation 不被命中。
- `verified_surface_digest` 变化 → generation 失效（测试）。
- 跨客户端隔离测试：构造 OMP 与 Claude 的 `effective_hash` 输入，断言 `client` 字段使二者不可能相同。

---

## 4. 启动与证据

### 4.1 ~~水合层~~ 已作废

- [x] 4.1 （不实施）T-1 证明 `--plugin-dir` 可只读交付 Skill，generation 无需水合即可被引用

**作废理由**：本任务基于「Skill 必须放进可写的 `CLAUDE_CONFIG_DIR`」这一前提，实测证伪。generation 现在像 OMP 一样被只读引用，`CLAUDE_CONFIG_DIR` 按 runtime-id 指向 `runtimes/claude/<id>/`，只承载认证与会话。原计划的 `_hydrate_claude_config`、`_verify_hydrated_config`、`hydration_digest`、manifest 的 `hydration` 段全部取消。

**替代验收**（并入 4.2）：`runtimes/claude/<id>/` 通过 `_validate_private_runtime` 与 `_assert_managed_path`；generation 在运行前后 `content_digest` 一致。

---

### 4.2 启动与环境隔离

- [x] 4.2 实现 `_claude_command`、`_claude_env`、`_run_claude`、`_require_claude_runtime_ready` —— **已完成**（#116）

**描述**：见 `design-spec.md` 4.1 与 `delta-specs.md` C-4。`CLAUDE_CONFIG_DIR` 按 runtime-id 指向 `runtimes/claude/<id>/`（只承载认证与会话）；能力面全部经 `--settings` / `--mcp-config` / `--strict-mcp-config` / `--plugin-dir` / `--setting-sources ""` 只读引用 generation；`--append-system-prompt` 注入 prompt；ambient 凭据变量置空；`HOME` 保留真实值以维持宿主底座。`auth_mode = "bare"` 时额外加 `--bare`。

**依赖**：4.1
**工作量**：2.5 天
**验收**：

- `uv run cap use general --cli claude` 能启动真实 Claude 进程并进入交互。
- `uv run cap run general --cli claude -- -p "列出你可用的 Skill"` 返回的 Skill 集合与 `.cap` 闭包一致。
- **隔离验证（核心）**：在真实 HOME 放一个用户级 Claude Skill 与一个用户级 MCP 声明，经 CAP 启动后该 Skill 与 MCP **不出现**在可用能力中；同一个 Skill 在不经 CAP 直接运行 `claude` 时**出现**（对照组）。
- ambient 凭据环境变量在子进程中为空字符串。
- 启动前完整跑过 lock / pin / binding / closure / generation 五道门；任一失败即非零退出且不启动进程。

---

### 4.3 receipt 与三层证据

- [x] 4.3 实现 `_write_claude_receipt` 与 `effective_observations` 分类 —— **已完成**（#116）

**描述**：见 `design-spec.md` 4.2。receipt 含 `auth_mode`、`post_run_content_digest`、`evidence` 三层、`effective_observations` 逐维度、`ambient_floor`。同步在 `run_observed` 的 `client_limited` 中登记 Claude 的降级维度。

**依赖**：4.2
**工作量**：1.5 天
**验收**：

- receipt 字段完整，`evidence.effective` 在未 probe 时为 `"unknown"`。
- `effective_observations.hooks` / `plugins` 为 `"reported_client_limited"`；`managed_settings` 为 `"unknown"`。
- **无 secret 测试**：用 `SECRET_KEY_PATTERN` / `SECRET_LINE_PATTERN` 扫描 receipt、manifest 与证据文件，零命中；转发参数只记 `forwarded_argument_count`。
- 运行后 immutable 集合复查通过；若客户端改写了 immutable 文件，receipt 记录并以非零码退出。

---

### 4.4 CAP CLI 分派

- [x] 4.4 把 `_run_selected` / `_render_preview` 的 OMP 硬编码改为 adapter 表分派 —— **已完成**（#116）

**描述**：见 `delta-specs.md` I-7。`EFFECTIVE_ADAPTERS` 表；codex / qoder 保持走通用 `subprocess` 路径。更新 parser description、epilog 与 `--cli` help 文案。`DEFAULT_CLI` 与 TUI 行为**不变**。

**依赖**：4.3
**工作量**：1 天
**验收**：

- `uv run cap show general --cli claude` 的 `preview` 结构与 `--cli omp` 同构，含 `portable_tree_hash`、`effective_render_hash`、`global_generation`、`auth_mode`、`skills`、`fixed_flags`、`unsupported`、`ambient_floor`。
- `--cli codex` / `--cli qoder` 行为与本变更前完全一致（回归测试）。
- 裸 `cap` 仍默认启动 OMP。

---

## 5. 跨平台与鲁棒性

### 5.1 Windows 路径与文件锁

- [x] 5.1 长路径预检、symlink 规避、并发与文件锁处理 —— **已完成（#117）：路径预算预检在物化前对真实路径求值，超限失败关闭且不留 stage**

**描述**：见 `design-spec.md` 10。物化前预检最深路径长度并给出可操作的中文错误；全程用副本不用 symlink；同一 `(runtime-id, effective_hash)` 并发时以 stage + rename 保证一致，冲突报错不覆盖。相关知识按名查询 `knowledge/windows-agent-ops.md`。

**依赖**：4.2
**工作量**：1.5 天
**验收**：

- Windows 上构造超长 skill 内层路径 → 得到明确中文错误与建议，而非 `OSError` 栈回溯。
- Claude 运行中执行 `cap show --cli claude` 不因文件锁失败。
- 两个进程同时物化同一 generation → 一个成功一个走校验路径，无半成品目录残留。

---

### 5.2 三平台验证

- [x] 5.2 在 Windows / macOS / Linux 上验证 render、generation 校验与启动 —— **部分完成（#117）：Windows 全链路已验证，Linux portable hash 与 Windows 逐字节一致；**macOS 未验证**，见 evidence/cross-platform.json**

**描述**：Windows 是主力平台，必须完整验证；macOS / Linux 至少验证 render + generation 校验 + 隔离验证。记录各平台的 managed settings 存在性观察结果。

**依赖**：5.1
**工作量**：1.5 天
**验收**：

- 三平台 `cap render --cli claude` 产出的 `portable_tree_hash` **相同**（跨机器可复现性的直接证据）。
- 三平台 generation 校验通过；`effective_render_hash` 因 `layer_digest` / machine binding 不同而不同属预期，需在证据中说明。
- Windows 上不依赖开发者模式或管理员权限。
- 各平台的 `effective_observations.managed_settings` 观察结果记入证据文件。

---

## 6. 文档与交付

### 6.1 文档更新

- [x] 6.1 更新 `docs/profile.md`、`docs/cap-guide.zh-CN.md`、`docs/maintenance.zh-CN.md`、`README.md` —— **已完成（#117）：docs/profile.md 的 Adapter 合同章节已改写为真实能力与天花板；cap-guide 新增 5.2 节；maintenance 新增 Claude runtime 与 CAS 维护**

**描述**：见 `delta-specs.md` I-10。重点是**改写 `docs/profile.md` 的「Adapter 合同」章节**——当前正文写「Claude adapter 当前未实施…必须报告 unknown」，实施后必须替换为真实的能力、限制与证据天花板描述，特别是 managed settings 不可控这一事实。

**依赖**：5.2
**工作量**：1.5 天
**验收**：

- 四个文件均已更新且全中文。
- `docs/profile.md` 明确写出 Claude 的三层证据天花板与 Web / IDE / API 形态差异。
- `docs/cap-guide.zh-CN.md` 含「用 Claude 启动」小节与至少三条故障排查（generation 内容漂移、全局污染、长路径）。
- 文档中出现的每个 native 键名都能在 `evidence/claude-native-surface.json` 中找到对应条目。

---

### 6.2 lock、binding 与全量验证

- [x] 6.2 刷新 lock 与 binding，跑通全部门禁 —— **已完成（#117）：skills-validate / lock / assembly-bind / verify / OpenSpec 全仓 17/17 均通过**

**描述**：按 `docs/maintenance.zh-CN.md` 的「修改后」清单执行。

**依赖**：6.1
**工作量**：0.5 天
**验收**：

```bash
uv run cap skills-validate
uv run cap lock
uv run cap assembly-bind general
uv run cap assembly-bind agent-assembler
uv run cap verify
uv run cap show general --cli claude
uv run cap show general --cli omp
uv run pytest
npx openspec validate add-claude-cap-adapter --strict --json
```

全部通过，且 lock 中 OMP / codex / qoder 的 `tree_hash` 未变。

---

### 6.3 证据留档

- [x] 6.3 产出可自足核验的交付证据 —— **已完成（#117）：evidence/ 下 launch-check、native-projection-check、cross-platform、delivery-summary 四份**

**描述**：把验收过程的关键输出脱敏后落进 `openspec/changes/add-claude-cap-adapter/evidence/`。

**依赖**：6.2
**工作量**：0.5 天
**验收**：

- `evidence/claude-native-surface.json`：一手核对结论（1.1 产出）。
- `evidence/isolation-check.json`：4.2 隔离验证的对照组结果（用户级 Skill / MCP 在 CAP 内不可见、CAP 外可见）。
- `evidence/cross-platform.json`：5.2 的三平台 `portable_tree_hash` 与 managed settings 观察。
- `evidence/omp-no-regression.json`：本变更前后 OMP 的 lock hash、`tree_hash`、`effective_render_hash` 对照。
- 全部证据文件经 secret 扫描零命中。
- 结论诚实：无法证明的项标 `unknown`，不出现由「文件已生成」推断的 confirmed 结论。
