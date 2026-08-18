# Agent System assembly

本目录说明根 `.cap` 中的显式 Agent profiles、提示词、Skills 与验证证据；当前包含通用工程 `general` 和 Agent 装配 `assembly-helper`。

本仓库面向中文使用者。快速迭代阶段，`.cap/capabilities/skills/*/SKILL.md` 的中文正文是唯一执行合同；不维护需要逐项同步的另一语言全文镜像。

## 这个仓库解决什么问题

它不是通用 Plugin Marketplace，也不是用户级配置仓库。它只回答：

- 当前 Agent profiles 分别是什么目标、边界和输出格式；
- 哪些 prompt / skills / MCP / hooks / plugins 被显式声明；
- 声明态、配置态和实际生效态分别有什么证据；
- 外部仓库的能力如何经过评估后，最小、可逆地进入项目闭包。

当前有两个可运行 profile：通用工程 `general` 与装配专用 `assembly-helper`；两者经内部 `work` 层继承 `real-home`。未受 CAP 管理的客户端不属于任何 profile。

## 快速开始

从仓库根目录执行：

```bash
# 高频使用：选择 profile、CLI 和可选客户端参数后直接启动
uv run cap

# 独立查看：TTY 中选择 profile，先看公共闭包，再决定是否展开一个 CLI
uv run cap show

# 非交互查看公共闭包，或直接展开 OMP 的真实目标文件树
uv run cap show general
uv run cap show general --cli omp

# 查看可用 Agent
uv run cap agents

# 校验 Agent Skills 标准元数据
uv run cap skills-validate

# 校验 Skill 元数据、项目 lock、real-home pin 与三层 profile binding
uv run cap verify
```

两个可运行 profile 都显式遵循 `real-home -> work -> derived` 链：`real-home` 提供真实 HOME 与原生 context，`work` 显式提供共享 OpenSpec Skills，derived 层提供角色 prompt 和专属能力。Profile 可以从不同 workdir 使用，但其权威定义、选择和闭包始终来自当前 Git 项目的 `.cap/manifest.toml`、profile files、capabilities、lock 和 binding。用户级目录只保存共享 OMP runtime 与经当前项目验证的内容寻址 render cache，不能枚举或补齐 profile。

裸 `cap` 只承担高频启动，不显示动作菜单。`cap show` 是独立查看入口；CLI 展开使用自动清理的临时 render，不启动客户端，也不要求输出目录。脚本应使用带完整参数的显式子命令。旧 `interactive` / `i` 已直接移除，不提供兼容别名或弃用期。

当前客户端注册表只有 Codex、Qoder 和 OMP。Claude 尚无本仓可运行、可渲染并经过验证的 adapter，因此当前不属于支持范围；后续在有真实 Claude CLI 的机器完成 adapter 与运行验证后再接入。

### OMP 用户级 runtime 与全局 CAS

持久 OMP 默认使用：

```text
$HOME/.cap-user-state/
├── runtimes/omp/default/          # auth、settings、Session、agent.db
└── renders/omp/<effective-hash>/  # 当前项目验证后的不可变 cache
```

可通过稳定 runtime id 表示不同用户状态域：

```bash
uv run cap --omp-runtime-id default use general --cli omp
```

`--omp-runtime-root` 只接受与批准真实 HOME 和 runtime id 推导出的精确路径，不能指向真实 `~/.omp` 或任意目录。`--agent-home-root` 只保留为当前项目级旧状态的迁移来源。

Profile render 的真源仍是当前 Git 项目。每次 cache 命中前，CAP 都先验证项目 manifest/lock/base pin/binding，重新计算 portable tree、profile/layer digest、adapter version、effective config 和固定门禁，再核对 generation manifest/content。删除整个 CAS 后应能仅凭当前项目重建；CAS 中同名目录或其他项目内容不会授权 profile。

从当前项目级 shared runtime 升级：

```bash
# 无写入 dry-run：比较项目源与用户级目标
uv run cap migrate-omp-runtime

# plan 无冲突后原子迁移到用户级 runtime
uv run cap migrate-omp-runtime --apply
```

目标已存在时会无 secret 比较 schema、settings、credential identity 和 Session；等价时合并不冲突 Session，实质差异在覆盖前停止。项目级 renders 不迁移，必须由当前项目重新 materialize 到全局 CAS。`memory.backend` 始终为 `off`。

每次启动仍固定使用当前 generation 的 config、system prompt、Skill allowlist、显式 extension、`--no-extensions` 和 `--no-rules`。全局 runtime MCP denylist 屏蔽已观察 ambient server；真实 `/mcp reload` 应为 connected servers `0`，disabled source 不是 active capability。Hook、Plugin 无可靠观察时保持 `unknown`。

Session 保存在全局 runtime 并按 encoded cwd 组织默认列表；该分组只是查找/展示约定，不是权限边界。显式 Session id/path 可以跨 profile、worktree 或 workdir 恢复，恢复时应用当前项目/profile overlay。

全局 runtime/CAS、跨 workdir resume、并发和无 secret 验证通过后，才执行：

```bash
uv run cap migrate-omp-runtime --cleanup
```

cleanup 只删除当前项目的 `<project>.agent-homes/shared/omp`、项目 render cache 和 migration backup；保留用户级 runtime/CAS、当前 `.cap`、真实 `~/.omp` 与其他客户端配置。

OpenSpec 作为仓库内开发依赖，通过 `npx` 使用：

```bash
uv sync --locked
npm install
npx openspec list
npx openspec validate --all --strict
```

初始化时使用 `--tools none`，不生成 `.agents`、`.omp`、`.qoder` 等 profile 外能力路径。

CAP 与 profile engine 已打包在当前 `agent-system` uv 项目中。正常使用分别执行 `uv run cap` 和 `uv run agent-profile`，不依赖 sibling checkout；`--profile-tool` 仅保留为明确测试或诊断输入。

首次使用或审查真实 HOME 后，显式刷新、审批并绑定；manifest、pin 和 binding 都不得提交到本仓：

```bash

uv run agent-profile --project . base-lock \
  --home "$HOME" \
  --manifest "$HOME/.cap-user-state/locks/real-home.manifest.json"

uv run agent-profile --project . base-approve \
  --manifest "$HOME/.cap-user-state/locks/real-home.manifest.json" \
  --pin "$HOME/work/_org/locks/agent-system/real-home.pin.json"

for profile in work general assembly-helper; do
  uv run agent-profile --project . bind \
    --profile "$profile" \
    --base-manifest "$HOME/.cap-user-state/locks/real-home.manifest.json" \
    --base-pin "$HOME/work/_org/locks/agent-system/real-home.pin.json" \
    --binding-dir "$HOME/work/_org/locks/agent-system/bindings"
done
```

运行 OMP smoke test（需要现有 OMP 认证状态，不要把认证文件放进本仓）：

```bash
uv run cap run assembly-helper --cli omp -- \
  -p "只输出：SKILLS-AVAILABLE: <skills>"
```

恢复既有 OMP Session，并在新的运行实例中装配 `general`：

```bash
uv run cap use general --cli omp -- --resume <session-id-or-path>
```

OMP Session 固定保留在共享 runtime；恢复时可用 Session id 或文件路径。同一 Session 可以在 `general` 与 `assembly-helper` 之间往返，历史 transcript 保留，当前 system prompt 与 Skill roster 按本次启动 profile 重新应用。`--` 后参数由 CAP 原样交给 OMP。

## 我应该先读什么

| 目的 | 入口 |
|---|---|
| 了解仓库边界 | [`AGENTS.md`](AGENTS.md) |
| 了解通用与装配 Agent | [`.cap/prompts/general.md`](.cap/prompts/general.md)、[`.cap/prompts/assembly-helper.md`](.cap/prompts/assembly-helper.md) |
| 看中文 Skill 目录 | [`docs/skill-catalog.zh-CN.md`](docs/skill-catalog.zh-CN.md) |
| 了解如何修改和验收 | [`docs/maintenance.zh-CN.md`](docs/maintenance.zh-CN.md) |
| 查看机器可核验闭包 | [`.cap/lock.json`](.cap/lock.json) |
| 查看 profile 索引 | [`.cap/manifest.toml`](.cap/manifest.toml) |

## Skill 目录

运行时文件位于 `.cap/capabilities/skills/<name>/SKILL.md`，中文正文是唯一全文合同；总目录见 [`docs/skill-catalog.zh-CN.md`](docs/skill-catalog.zh-CN.md)。

| Skill | 用途 |
|---|---|
| `assembly-helper` | 装配 Agent 的总入口：目标、边界、能力闭包和交付证据 |
| `agent-prompt-design` | 设计常驻 prompt 的角色、权威、安全、路由和输出不变量 |
| `agent-skill-design` | 设计条件性 Skill 的元数据、路由、渐进披露和验收 |
| `capability-profile-closure` | 检查本地闭包、Skill 标准合规和各状态层证据 |
| `capability-lifecycle` | 调研、评估、引入、升级和退役外部能力 |
| `agent-behavior-evaluation` | 建立行为基线、正反场景和可比较运行证据 |
| `spec-change-pack` | 用 OpenSpec 组织较大的行为变更和长期审计证据 |
| `openspec-explore` | 实施或建 change 前探索问题、边界与取舍 |
| `openspec-propose` | 创建完整 Proposal、delta specs、design 与 tasks |
| `openspec-update-change` | 修订已有 change 的现存规划工件并保持一致 |
| `openspec-apply-change` | 按已有 change 实施任务并逐项验证 |
| `openspec-sync-specs` | 把 delta specs 合并到长期主规格而不归档 |
| `openspec-archive-change` | 校验、同步并归档已完成 change |

## 三态语义

不要把“文件存在”当成“Agent 已生效”：

1. **声明态（declared）**：version 2 manifest、`extends`、项目层操作、prompt、Skill 文件。
2. **配置态（configured）**：项目 lock、私有 real-home manifest、workspace pin、derived binding、render tree。
3. **生效态（effective）**：真实客户端运行时的可观察输出；必须同时确认真实 HOME 与隔离的客户端状态根。

Hook / Plugin 当前按 `opaque-staging` 处理；没有真实端加载证据时必须保持未知。本仓目前不声明 MCP、Hook 或 Plugin。

## 外部来源策略

外部仓库只提供可审查的历史或来源证据，不自动成为运行时依赖。可安装 Plugin 已迁入根 `plugins/`，profile/Skill 的唯一运行时声明仍是当前项目 `.cap`；引入新能力时先经过 `capability-lifecycle`，再更新显式声明和 lock。

## 单仓逻辑边界

- 根 `.cap/`：`general`、`assembly-helper`、`work` 的 profile、prompt 和中文 Skill 合同；
- `src/agent_system/`：公共 profile、CAP 和 OMP 实现；
- `plugins/`：跨任务、跨客户端可安装的 Plugin／Skill 资产；
- `openspec/`：固定 OpenSpec 工作流和长期规格。

## License

MIT。见仓库根 [`LICENSE`](../../LICENSE)。
