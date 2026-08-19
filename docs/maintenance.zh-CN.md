# 仓库维护指南

目标：让任何新 Session 都能从仓库文件恢复装配边界、能力闭包和验证状态，而不是依赖聊天历史。

## 修改前

1. 读 [`AGENTS.md`](../AGENTS.md) 和 [`README.md`](../README.md)。
2. 读取当前 profile。TTY 中可以先选择；脚本必须显式指定 profile：

   ```bash
   uv run cap show
   uv run cap show assembly-helper
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
- 项目新增或替换的运行时能力必须落在当前仓库 `.cap/capabilities/` 下，并由 profile 的 `add`／`replace` 显式引用。
- 用户环境只允许通过已审批 `real-home` manifest、workspace pin 和 derived binding 进入；不得从未绑定的用户目录、模板目录、其他仓库或 ambient provider 配置补齐业务能力。
- 不把认证材料、token、个人运行态、临时 receipt、base manifest、pin 或 binding 写入本仓。
- 常驻 prompt 只放短约束；长流程放 Skill。
- 快速迭代阶段，Skill 的 `description` 和正文使用中文；`name`、目录 id、路径、命令和配置键保持规范形式。
- `.cap/capabilities/skills/<name>/SKILL.md` 是唯一全文合同；不在 `docs/skills/` 维护需要逐项同步的另一语言镜像。
- 外部仓库内容先作为证据读取；复制进本仓后必须说明来源、边界和验证方式。

## OpenSpec 工作流

OpenSpec 固定为仓库内开发依赖。先执行 `npm install`；CAP migration 的 YAML 读写依赖由 `python3 -m pip install -r requirements.txt` 安装。随后通过 `npx openspec` 调用，不得依赖用户级全局 OpenSpec。

```bash
npx openspec status --change <change-id> --json
npx openspec instructions <artifact> --change <change-id> --json
npx openspec validate <change-id> --strict --json
```

供人阅读的 proposal、spec、design、tasks 正文使用中文，保留 OpenSpec 解析要求的英文结构关键字。初始化保持 `--tools none`：OpenSpec CLI 管理 `openspec/` 规划资产；六个中文 Workflow Skill 合同由 `.cap` 显式声明，不向 `.agents`、`.omp`、`.qoder` 生成 profile 外运行时能力。

## 修改后

从仓库根目录执行：

```bash
# 1. 检查 Skill 标准元数据
uv run cap skills-validate

# 2. 更新项目层 lock：只有声明内容确实改变时执行
uv run cap lock

# 3. 项目层变化后重建 work 与两个 derived binding；不得自动刷新 base pin
for profile in work general assembly-helper; do
  uv run cap \
    --base-manifest "$HOME/.cap-user-state/locks/real-home.manifest.json" \
    --base-pin "$HOME/work/_org/locks/agent-system/real-home.pin.json" \
    --binding-dir "$HOME/work/_org/locks/agent-system/bindings" \
    bind "$profile"
done

# 4. 检查元数据、项目 lock、base pin 和全部 binding
uv run cap verify

# 5. 查看最终公共 inventory，并展开一个 CLI 的真实目标文件树
uv run cap show assembly-helper
uv run cap show general
uv run cap show general --cli omp

# 6. 验证活动 OpenSpec change
npx openspec validate <change-id> --strict --json
```

裸 `cap` 进入 TUI，只选择 profile；默认是 `general`，选择后直接启动默认 `omp`。TUI 不再选择客户端或 AI 配置方式。需要修改 Agent 系统配置时，直接进入 `assembly-helper`，由该 profile 根据当前项目文件恢复源头、修改所需文件并重新完成 lock、binding、render 和 verify。`cap show` 专用于查看；`run` 与带 `--output` 的 `render` 是参数完整、可在非 TTY 中执行的自动化接口。旧 `interactive` / `i` 不保留兼容层。

Profile engine 已打包在当前 `agent-system` uv 项目中，仅由 `uv run cap` 内部调用；用户不直接运行底层 profile engine，也不依赖 sibling checkout。

## OMP 用户级 runtime 与全局 CAS 维护

持久 OMP 默认使用 `$HOME/.cap-user-state/runtimes/omp/default` 共享认证、settings、Session、history、cache 和 `agent.db`；`memory.backend` 固定为 `off`。Profile 可以跨 workdir 使用，但 profile/prompt/capability 的唯一权威仍是当前 Git 项目 `.cap`，用户级目录不得保存可编辑 catalog 或作为能力 discovery 来源。

全局 render CAS 位于 `$HOME/.cap-user-state/renders/omp/<effective-hash>`。每次命中前必须先完成当前项目 manifest/profile/lock/base pin/binding 验证，再用 portable tree、profile/layer digest、adapter version、effective config与fixed gates计算期望hash并核对manifest/content。CAS删除后必须能由当前项目重建；cache存在不是声明态证据。

路径参数：

```bash
--omp-runtime-id default
--omp-runtime-root $HOME/.cap-user-state/runtimes/omp/default
```

显式 root 必须等于批准真实 HOME 与 runtime id 推导出的精确路径，拒绝真实 `~/.omp`、symlink ancestor、路径别名和越界目录。`--agent-home-root` 只表示当前项目旧状态/迁移来源。

项目级 shared runtime 到用户级迁移：

```bash
# 1. dry-run：验证当前项目closure、项目源、global目标和无secret状态摘要
uv run cap migrate-omp-runtime

# 2. 无冲突后安装/合并用户级runtime
uv run cap migrate-omp-runtime --apply
```

目标不存在时私有stage后原子安装；目标存在时比较schema、settings与credential identity，等价时合并内容不冲突的Session，实质差异在写入前停止。项目级renders不迁移，当前项目重新materialize到global CAS。WAL/SHM、terminal breadcrumb和临时文件不作为迁移真源。

运行门禁保持：

- 真实 HOME 与real-home drift gate；
- 当前项目manifest/lock/binding先验证；
- Skill custom directory与双allowlist；
- ambient Skill来源和project MCP discovery关闭；
- `--no-extensions`、`--no-rules`；
- 全局runtime MCP denylist；
- provider/API/OAuth/cloud credential环境清理；
- `PI_AUTH_NO_BORROW`与metadata防护。

Session默认按encoded cwd组织只是查找/展示约定，不是授权边界。显式id/path可跨profile/worktree/workdir恢复；必须观察同一Session identity和transcript连续，同时当前项目/profile prompt与Skill marker切换。

真实验证要求：

- 至少两个不同workdir共享一次登录/settings；
- `general`、`assembly-helper`使用不同已验证global generations；
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

cleanup只删除当前项目级shared runtime、project render cache和migration backup；不得删除global runtime/CAS、当前 `.cap`、真实 `~/.omp`、其他客户端配置或其他runtime id。全局CAS GC不在本change范围。

本变化不修改当前项目profile、prompt、中文Skill、inventory或lock。Codex、Qoder和`--fresh`继续使用原有`--auth-root`。

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
- `$HOME/.cap-user-state/locks/real-home.manifest.json`
- `$HOME/work/_org/locks/agent-system/real-home.pin.json`
- `$HOME/work/_org/locks/agent-system/bindings/*.binding.json`
- `uv run cap show`
- `uv run cap render <profile> --cli <client> --output <existing-empty-dir>`
- 真实客户端 runtime environment

检查：项目 lock 没有 stale，base active digest 被 workspace pin 明确批准，derived binding 同时匹配 base digest 与 layer digest，portable render hash 与 lock 一致；持久 OMP 另外显示共享 runtime root、当前 profile generation、effective hash 和固定门禁。真实 `HOME` 保留，但共享 runtime 不得因此继承未审批能力。

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
