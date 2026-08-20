# 仓库维护指南

目标：让任何新 Session 都能从仓库文件恢复装配边界、能力闭包和验证状态，而不是依赖聊天历史。

## 修改前

1. 读 [`AGENTS.md`](../AGENTS.md) 和 [`README.md`](../README.md)。
2. 读取当前 profile。TTY 中可以先选择；脚本必须显式指定 profile：

   ```bash
   uv run cap show
   uv run cap show agent-assembler
   ```

3. 确认本次变更属于哪一层：
   - prompt 不变量；
   - 条件性 Skill；
   - profile 声明；
   - 配置 / lock；
   - 文档；
   - 外部参考。
4. 对影响后续 Agent 行为的变更，先写清目标、非目标、触发、输入、输出和验收。

## 修改时

- 保持 id 为小写连字符。
- 项目新增或替换的运行时能力必须位于当前仓库：默认放在 `.cap/capabilities/`；需要复用仓内唯一 Skill 正文时，由 manifest 明示项目相对、非 symlink、lock 覆盖的 source。profile 必须用 `allow`／`deny`／`override` 显式引用。
- 用户环境只允许通过已批准的 `machine-context`、pin、asset inventory 和 assembly binding 进入；inventory 只是观察面，不自动授权 Agent-facing 能力。
- 不把认证材料、token、个人运行态、临时 receipt、machine-context manifest、pin 或 binding 写入本仓。
- 常驻 prompt 只放短约束；长流程放 Skill。
- 快速迭代阶段，Skill 的 `description` 和正文使用中文；`name`、目录 id、路径、命令和配置键保持规范形式。
- 本地 Skill 的 `SKILL.md` 或 manifest 指向的项目 Skill source 是唯一全文合同；不在 `docs/skills/` 或 `.cap` 维护需要逐项同步的镜像。
- 外部仓库内容先作为证据读取；引入本仓后必须说明来源、边界和验证方式。

## OpenSpec 工作流

OpenSpec 固定为仓库内开发依赖。先执行 `npm install`；CAP migration 的 YAML 读写依赖由 `python3 -m pip install -r requirements.txt` 安装。随后通过 `npx openspec` 调用，不得依赖用户级全局 OpenSpec。

```bash
npx openspec status --change <change-id> --json
npx openspec instructions <artifact> --change <change-id> --json
npx openspec validate <change-id> --strict --json
```

供人阅读的 proposal、spec、design、tasks 正文使用中文，保留 OpenSpec 解析要求的英文结构关键字。初始化保持 `--tools none`：OpenSpec CLI 管理 `openspec/` 规划资产；六个中文 Workflow Skill 合同由 `.cap` 显式声明，不向 `.agents`、`.omp`、`.qoder` 生成 profile 外运行时能力。

OpenSpec 官方 CLI 与项目内中文 Workflow Skill 的采用状态由 `.cap/capabilities/skills/capability-lifecycle/references/openspec-upstream.json` 控制。修改 package、lock、六个兼容声明、provenance 或 CAP closure 后运行：

```bash
python tools/openspec_lifecycle/openspec_lifecycle.py --project . verify
python tools/openspec_lifecycle/openspec_lifecycle.py --project . digest --change <change-id>
```

不带 `--revision` 的 digest 只是 working-tree preview，不能回写 Issue 为已同步；受管摘要必须使用固定 Git commit 的 `--revision <commit>` 结果，并通过 `summary-check` 校验字段。检测到新版本只更新 review／candidate，不自动覆盖 adopted。

## 修改后

从仓库根目录执行：

```bash
# 1. 检查 Skill 标准元数据
uv run cap skills-validate

# 2. 更新项目层 lock：只有声明内容确实改变时执行
uv run cap lock

# 3. 项目层变化后重建 assembly binding；不得自动刷新 machine-context pin
for profile in general agent-assembler; do
  uv run cap \
    --machine-context-manifest "$HOME/.agent-system-state/machine-context/manifest.json" \
    --machine-context-pin "$HOME/.agent-system-state/machine-context/pin.json" \
    --assembly-binding-dir "$HOME/.agent-system-state/bindings" \
    assembly-bind "$profile"
done

# 4. 检查元数据、项目 lock、machine-context pin 和全部 binding
uv run cap verify

# 5. 查看最终公共 inventory，并展开一个 CLI 的真实目标文件树
uv run cap show agent-assembler
uv run cap show general
uv run cap show general --cli omp
uv run cap show general --cli claude

# 6. 验证活动 OpenSpec change
npx openspec validate <change-id> --strict --json
```

裸 `cap` 进入 TUI，只选择 profile；默认是 `general`，选择后直接启动默认 `omp`。需要修改 Agent 系统配置时，直接进入 `agent-assembler`，由该执行角色从负责人目标和当前项目源文件恢复合同、完成装配，再重建 lock、binding、render 和 verify。事实可调查时直接执行；产品取舍、长期依赖、外部副作用和不可逆风险仍由负责人决定。`grilling` 只有在负责人直接要求或明确接受建议后才能运行。`cap show` 专用于查看；`run` 与带 `--output` 的 `render` 是参数完整、可在非 TTY 中执行的自动化接口。旧 `interactive` / `i` 不保留兼容层。

Profile engine 已打包在当前 `agent-system` uv 项目中，仅由 `uv run cap` 内部调用；用户不直接运行底层 profile engine，也不依赖 sibling checkout。

## OMP 用户级 runtime 与全局 CAS 维护

持久 OMP 默认使用 `$HOME/.agent-system-state/runtimes/omp/default` 保存认证、settings、Session、history、cache 和 `agent.db`；`memory.backend` 固定为 `off`。profile、prompt、capability 和 project-defaults 的唯一权威仍是当前 Git 项目 `.cap`，用户级目录不得保存可编辑 catalog 或作为能力 discovery 来源。

全局 render CAS 位于 `$HOME/.agent-system-state/renders/omp/<effective-hash>`。每次命中前必须先完成当前项目 manifest/profile/lock、machine-context pin、assembly binding 和 capability closure 验证，再用 portable tree、profile/layer digest、adapter version、effective policy 与 fixed gates 计算期望 hash 并核对 generation/content。

路径参数：

```bash
--omp-runtime-id default
--omp-runtime-root $HOME/.agent-system-state/runtimes/omp/default
```

显式 root 必须等于批准真实 HOME 与 runtime id 推导出的精确路径，拒绝真实 `~/.omp`、symlink ancestor、路径别名和越界目录。旧项目状态根只作为显式 migration 来源。

项目级 shared runtime 到用户级迁移：

```bash
# 1. dry-run：验证当前项目 closure、项目源、global 目标和无 secret 状态摘要
uv run cap migrate-omp-runtime

# 2. 无冲突后安装/合并用户级 runtime
uv run cap migrate-omp-runtime --apply

# 3. 如果需要撤回：从 quarantine backup 恢复旧 runtime
uv run cap migrate-omp-runtime --rollback
```

目标不存在时私有stage后原子安装；目标存在时比较schema、settings与credential identity，等价时合并内容不冲突的Session，实质差异在写入前停止。项目级renders不迁移，当前项目重新materialize到global CAS。WAL/SHM、terminal breadcrumb和临时文件不作为迁移真源。

运行门禁保持：

- machine-context active drift、当前项目 manifest/lock/pin/binding 先验证；
- Agent-facing asset inventory 默认拒绝，只有显式 project-defaults、role、项目 Skill import 或 external import 才能进入 closure；
- ambient Skill、MCP、Hook、Plugin discovery 关闭；
- `--no-extensions`、`--no-rules`；
- 全局 runtime MCP denylist；
- provider/API/OAuth/cloud credential 环境清理；
- `PI_AUTH_NO_BORROW` 与 metadata 防护。

Session默认按encoded cwd组织只是查找/展示约定，不是授权边界。显式id/path可跨profile/worktree/workdir恢复；必须观察同一Session identity和transcript连续，同时当前项目/profile prompt与Skill marker切换。

真实验证要求：

- 至少两个不同workdir共享一次登录/settings；
- `general`、`agent-assembler`使用不同已验证global generations；
- 显式同一Session path跨cwd/profile恢复；
- 不把cwd目录分组报告为安全隔离；
- 不同workdir/profile并发时global SQLite与CAS不变；
- `/mcp reload` connected servers为`0`且无MCP xdev/tool；disabled source不算active capability；
- Hook/Plugin不可可靠观察时保持`unknown`；
- preview/receipt记录runtime id、global root、当前项目source/profile/layer digest、global generation、workdir，不记录secret。

验证全部通过后：

```bash
uv run cap migrate-omp-runtime --cleanup
```

`--rollback` 只读取并验证显式 migration backup，恢复旧 project/global runtime 后移除新 runtime；没有 marker、backup、runtime id 匹配或路径安全校验失败时停止。`--cleanup` 不是 rollback：它只在行为验证完成后删除当前项目级 shared runtime、render cache 和 migration backup。

本变化只实现并验证 OMP adapter；Codex 与 Claude 只消费 v3 合同，未实施或未观察到的字段和客户端生效态保持 `unknown`，不得复用 OMP native config。

## 证据分层

### Skill 标准合规

由 `SKILL.md` frontmatter、目录 id 和 `uv run cap skills-validate` 证明。标准合规不是运行时状态，也不能替代 profile 闭包或客户端观察。

### 声明态

由以下文件证明：

- `.cap/manifest.toml`
- `.cap/profiles/*.toml`
- `.cap/prompts/*.md`
- `.cap/capabilities/**`

检查：profile 能被列出，引用文件存在，命名和路径合规。

### 配置态

由以下证据证明：

- `.cap/lock.json`
- `$HOME/.agent-system-state/machine-context/manifest.json`
- `$HOME/.agent-system-state/machine-context/pin.json`
- `$HOME/.agent-system-state/bindings/*.binding.json`
- `.cap/runtime/omp.toml`
- `uv run cap show`
- `uv run cap render <profile> --cli <client> --output <existing-empty-dir>`
- 真实客户端 runtime environment

检查：项目 lock、machine-context pin、assembly binding、asset closure、runtime policy、portable render hash 和 generation 一致；receipt 关联 runtime id、effective policy、generation 和 render hash。配置态不升级为生效态。

### 生效态

由真实客户端 run 的 marker 或其他可重复观察证明：

```text
SKILLS-AVAILABLE: ...
MCP-AVAILABLE: ...
CONTEXT-FILES: ...
HOOKS-AVAILABLE: ...
PLUGINS-AVAILABLE: ...
```

没有生效态证据时写 `unknown`，不要用文件存在、lock 通过或模型自述替代。

## 外部能力变更

引入或升级外部 Skill / Plugin / MCP / Hook 时：

1. 记录能力缺口和不做事项；
2. 比较候选来源、触发条件、维护成本和退出路径；
3. 只复制最小行为到当前 `.cap`；
4. 更新 profile；
5. 更新 lock；
6. 做配置态检查；
7. 若要声称跨客户端生效，逐端运行并记录证据。

不能因为外部仓库“安装成功”就声称本仓行为已经等价或已经生效。

## 提交和发布

提交前：

```bash
git status --short --branch
git diff --check
git diff --stat
```

然后执行 profile 验证和相称 smoke test。提交信息应说明行为变化，不写“update stuff”这类不可追踪标题。推送后回读远端分支和仓库可见性。

## 维护停止条件

遇到以下情况，不继续扩大修改面：

- 当前项目授权不覆盖新增 profile、外部安装或用户级配置；
- 所有权或共享写入范围不清；
- 关键外部事实无法核验；
- 只能靠猜测判断客户端是否加载；
- 新方案会把本仓变成 Plugin Marketplace、调度器、secret broker 或全局能力安装器。

此时保留已验证的局部结果，报告缺口和下一步所有者。

## OMP 共享 preference 与跨 profile resume

普通 OMP 的 `~/.omp/agent/config.yml` 是 CAP OMP 的唯一共享 preference source。CAP 只投影模型角色、`extendedContext`、thinking/tier、advisor、theme、status line、composer、显示字段和经过校验的无 credential provider endpoint；项目固定门禁仍强制关闭 memory、project MCP discovery 与 ambient capability。

认证使用配置的本地或 HTTPS auth-broker。broker token 只在启动 OMP 子进程时从私有 token 文件或 broker 配置读入环境；不得手工写入 CAP generation、receipt、lock 或项目文件。broker 未配置时 CAP 保持其隔离 credential store，不得借用 ambient API key。

同一 OMP runtime id 下的 CAP profile 共用 OMP 原生 session/history/database/models-cache root。先打开目标 profile，再在同一工作目录执行 `/resume`，即可选择此前 profile 创建的 session；续接后的模型、advisor、prompt 与能力闭包以当前 profile 为准。CAP 不创建 profile 专属 `--session-dir`，也不恢复旧 profile 的运行中 tool、子 Agent 或 worktree。

回滚共享 preference 时移除或恢复普通 OMP source 中的相应字段后重新启动 CAP；CAP generation 将按摘要重建。不要删除 session JSONL、broker token 或 credential store 作为回滚手段。

## Claude runtime 与 CAS 维护

Claude 的持久状态与 OMP 平行：

```text
$HOME/.agent-system-state/runtimes/claude/<runtime-id>/   认证与会话，跨项目共享
$HOME/.agent-system-state/renders/claude/<effective-hash>/ 只读 generation（内容寻址）
```

generation 在运行期间保持只读：Skill 经 `--plugin-dir` 只读交付，MCP 与 settings 经命令行 flag 指向同一目录，因此运行前后 `content_digest` 必须一致。手工改动 generation 会在下次启动被拒绝——正确处理是删掉该目录让它重新物化，而不是修补。

`renders/claude/` 是可重建的派生物，可以直接删除；`runtimes/claude/` 含真实凭据，**不要删**。

CAP 对用户自己的 `~/.claude`、`~/.claude.json` 与 `~/.claude-plugin` 既不读、也不写、也不迁移。

### 新增 runtime policy 字段时的陷阱

`.cap/runtime/*.toml` 是 lock 输入，而 lock 在哈希前会先经 secret 遮蔽。字段名若含 `auth`、`token`、`secret`、`credential` 等词，其取值会被替换成占位符，导致两个不同取值哈希相同、`cap verify` 对该字段失效。

`tests/profile/test_profile.py::RuntimePolicyFieldsSurviveRedactionTests` 会在这种命名出现时立即失败。
