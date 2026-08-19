# CAP 中文使用指南

CAP（Capability Assembly and Profiles）是本仓库的 Agent 装配入口。它把“使用哪个 profile、允许哪些能力、如何绑定当前机器、如何启动客户端”变成可以检查和复现的配置，而不是依赖聊天记忆或用户目录里的隐式配置。

如果第一次接触 CAP，先记住这一条：

> **先看 role 和 capability closure；修改声明后刷新 lock，绑定 machine-context，最后 verify。**

本指南面向日常使用。完整 schema 和安全边界见 [`profile.md`](./profile.md)，仓库维护流程见 [`maintenance.zh-CN.md`](./maintenance.zh-CN.md)。

## 1. CAP 管什么

CAP 管理四类 Agent-facing 能力：

| 类型 | 作用 | 当前仓库状态 |
| --- | --- | --- |
| Skill | 条件性工作流和操作方法 | 已声明多个项目内 Skill |
| MCP | 模型可调用的外部工具服务 | 当前没有项目内 MCP；用户级 `idea` 只作为 inventory 观察 |
| Hook | 客户端生命周期钩子 | 当前没有项目内 Hook |
| Plugin | 客户端扩展或插件 | 当前没有项目内 Plugin |

同时管理这些 v3 输入和证据：

- **Role**：叶子角色，例如 `general`、`agent-assembler`；
- **Prompt**：role 的常驻行为约束；
- **项目声明**：`.cap/manifest.toml`、`project-defaults.toml`、`.cap/skill-imports.toml`、`.cap/profiles/*.toml`；
- **宿主与观察**：machine-context manifest/pin、asset inventory；
- **锁定与运行**：`.cap/lock.json`、assembly binding、runtime policy、generation、receipt。

CAP **不**接管认证、token、provider 账号、Git/SSH、语言工具链或任意用户目录。认证通过显式 `--auth-root` 提供，业务能力不能从用户目录或 provider ambient 配置隐式补齐。

## 2. 三个最重要的概念

### Profile

Profile 是一次运行的装配选择。每个 profile 有：

- 一个 prompt；
- 一个 role profile；
- 显式 `allow`／`deny`／`override` 能力操作；
- 独立的 `project-defaults`、`machine-context`、asset inventory 与 runtime policy 输入。

当前 v3 运行模型是：

```text
machine-context + project-defaults + general
                                  agent-assembler
```

`machine-context` 只描述经 pin 批准的宿主底座；asset inventory 只观察候选，不授予能力；`project-defaults` 描述项目公共能力；`general` 与 `agent-assembler` 是可运行的叶子 role。用户目录不会被隐式继承为 Agent-facing 能力。

例如，用户 HOME 中即使存在 `idea` MCP，inventory 也只记录观察证据；`agent-assembler` 的有效 MCP 仍为空。它的 `grilling` 来自 manifest 明示的项目 Skill import，而不是用户级 Plugin 安装态。`cap show`、lock、binding 和 verify 的通过属于声明态或配置态，不等于客户端原生生效态。

如果只想知道“我现在实际能选什么”，先看：

```bash
uv run cap agents
uv run cap show general
uv run cap show agent-assembler
```

### 能力闭包

能力闭包是某个 profile 最终能看到的 Skill、MCP、Hook、Plugin 集合。

```toml
[skills]
allow = ["some-skill"]
deny = ["ambient-skill"]
override = ["shared-skill"]
```

- `allow`：只能引用 `.cap` capability store、manifest 明示的项目 Skill import，或有 provenance 的 external import；
- `deny`：屏蔽已观察或已继承候选；
- `override`：在不解除系统安全门禁的前提下替换已声明实现；
- 不要直接改 render 目录或客户端 native 配置来“临时修复”。

### 三层证据

| 层级 | 回答什么 | 主要证据 |
| --- | --- | --- |
| 声明态 | 仓库说自己要装什么 | manifest、defaults、role、prompt、capabilities、policy |
| 配置态 | lock、binding、render 是否一致 | `.cap/lock.json`、machine-context pin、binding、generation |
| 生效态 | 客户端实际加载了什么 | 真实 `run` 输出、receipt、marker、probe/diff |

文件存在或 lock 通过，不等于客户端已经原生加载。Hook、Plugin、MCP/context 观察不足时保持 `unknown`。

## 3. 日常使用流程

以下命令从仓库根目录运行。

### 3.1 查看可用 profile

```bash
uv run cap agents
uv run cap profiles
uv run cap show agent-assembler
uv run cap show general --cli omp
```

- `agents`：查看可运行的 Agent profile；
- `profiles`：查看 manifest 中的 profile 名称；
- `show`：查看能力闭包、继承链、操作和客户端渲染 hash；
- `--cli`：展开某个客户端的目标装配。

### 3.2 只启动并使用一个 profile

交互式选择：

```bash
uv run cap
```

显式运行：

```bash
uv run cap run agent-assembler -- -p "检查当前 Agent 装配边界"
```

需要真实客户端交互时使用 `use`（它是 `launch` 的用户入口别名）。脚本和自动化优先使用显式 profile、client、auth-root 和 workdir。

### 3.3 修改 profile 或能力声明后

顺序固定：

```bash
uv run cap skills-validate
uv run cap lock
uv run cap assembly-bind general
uv run cap assembly-bind agent-assembler
uv run cap verify
```

说明：

1. `skills-validate`：检查本地与项目 import Skill 的 frontmatter、目录名和描述；
2. `lock`：锁定项目 defaults、Skill import、role、policy 和渲染结果；
3. `assembly-bind`：绑定已批准的 machine-context digest；
4. `verify`：检查 lock、pin、binding、asset closure 和 runtime policy。

`lock` 不会批准新的 machine-context；`assembly-bind` 也不会自动刷新 pin。渲染结果用于检查 prompt、Skill 和客户端配置，不代表客户端一定已经生效。

### 3.4 只渲染、不启动客户端

输出目录必须是项目外的既有空目录：

```bash
mkdir -p /private/tmp/cap-render
uv run cap render agent-assembler --cli omp --output /private/tmp/cap-render
```

OMP 的 `config.yml`、`mcp.json` 等文件名只属于 adapter 输出；它们不能成为项目能力或跨客户端配置源。

## 4. 使用 Agent 装配者

`agent-assembler` 是执行角色，不是建议助手。它从负责人目标恢复 Agent 合同，从零选择能力，修改 manifest、profile、prompt、Skill 和当前调用方，再生成 lock、binding、render 并按证据层交付。事实能由仓库或工具确定时直接调查；只有产品取舍、授权、长期依赖、外部副作用或不可逆风险需要负责人决定。

它的专用能力闭包包括总装配、prompt 设计、Skill 设计、能力生命周期、profile closure、行为评测、变更包和 `grilling`，并继承项目 OpenSpec 工作流。MCP、Hook、Plugin 均为空。`grilling` 常驻不等于自动盘问：只有负责人直接要求 grilling／盘问／压力测试，或明确接受一次建议后才能执行。

`.cap/skill-imports.toml` 把 `grilling` 绑定到仓内唯一正文 `plugins/grilling/skills/grilling/SKILL.md`。source 必须位于项目根内、不得经过 symlink、必须与 Skill id 同名，并进入 lock inputs、标准验证和客户端 render；不得在 `.cap` 复制第二份正文。

因此看到某个用户级能力存在，不等于它已被当前 profile 允许。它必须同时通过 profile 闭包和客户端启动门禁。

## 5. 看到能力告警怎么办

如果看到类似告警：

```text
profile: warning: out-of-scope MCP is observed but not in project closure
```

不要只重新运行。按下面顺序处理：

1. 记录 profile、能力名称和来源路径；
2. 执行 `uv run cap show <profile>`，确认声明态、inventory 和最终 closure；
3. 如果能力不应使用，保持默认拒绝或在 profile 中加入 `deny`；
4. 如果确实需要，先把能力作为项目内资产或已批准 external import 声明，并使用 `allow` 或 `override`；
5. 重新执行 `lock`、`assembly-bind`、`verify`；
6. 只有 verify 通过后再启动客户端。

“被用户目录发现”不能自动变成“被 profile 允许”；Hook、Plugin、MCP 和客户端生效结果不足时必须保持 `unknown`。

## 6. 常见失败的含义

| 现象 | 含义 | 处理 |
| --- | --- | --- |
| `capability lock drift detected` | 声明改了但 lock 没刷新 | 审阅差异后运行 `uv run cap lock` |
| `binding is stale` | lock 或 machine-context digest 变化，旧 binding 不再匹配 | 审阅后重新 `assembly-bind` |
| `active machine-context drift detected` | 已批准宿主上下文的 active 输入发生变化 | 重新检查 manifest 和 pin，不要盲目继续 |
| `passive machine-context drift` | 观察到非 active 配置变化 | 可继续，但要记录告警原因 |

## 7. 需要记住的最短版本

```text
看 profile：       cap show <profile>
改了声明：         cap lock
绑定机器基座：     cap bind <profile>
确认可运行：       cap verify
只看渲染结果：     cap render <profile> --cli <client> --output <empty-dir>
实际启动：         cap run <profile> ...
```

CAP 的目标不是让配置文件更多，而是让每次 Agent 运行都能回答：

1. 当前是谁在运行？
2. 它被允许使用哪些能力？
3. 这些能力来自哪里？
4. lock、机器基座和客户端配置是否一致？
5. 哪些结论已经真实观察，哪些仍然未知？
