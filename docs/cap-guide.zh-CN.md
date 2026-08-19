# CAP 中文使用指南

CAP（Capability Assembly and Profiles）是本仓库的 Agent 装配入口。它把“使用哪个 profile、允许哪些能力、如何绑定当前机器、如何启动客户端”变成可以检查和复现的配置，而不是依赖聊天记忆或用户目录里的隐式配置。

如果第一次接触 CAP，先记住这一条：

> **先看 profile，再看能力闭包；修改声明后刷新 lock，绑定 real-home，最后 verify。**

本指南面向日常使用。完整 schema 和安全边界见 [`profile.md`](./profile.md)，仓库维护流程见 [`maintenance.zh-CN.md`](./maintenance.zh-CN.md)。

## 1. CAP 管什么

CAP 管理四类运行时能力：

| 类型 | 作用 | 当前仓库状态 |
| --- | --- | --- |
| Skill | 条件性工作流和操作方法 | 已声明多个项目内 Skill |
| MCP | 模型可调用的外部工具服务 | 当前没有项目内 MCP；`assembly-helper` 屏蔽 real-home 的 `idea` |
| Hook | 客户端生命周期钩子 | 当前没有项目内 Hook |
| Plugin | 客户端扩展或插件 | 当前没有项目内 Plugin |

同时管理这些装配资产：

- **Profile**：角色和能力闭包的选择，例如 `general`、`assembly-helper`；
- **Prompt**：profile 的常驻行为约束；
- **系统入口**：`entrypoints/agent-system.md` 和根 `AGENTS.md`；
- **项目声明**：`.cap/manifest.toml`、`.cap/profiles/*.toml`；
- **锁定与绑定**：`.cap/lock.json`、私有 `real-home` manifest、workspace pin、derived binding；
- **客户端渲染**：Codex、Qoder、OMP 各自的隔离配置和 prompt；
- **运行观察**：声明态、配置态和实际生效态的 probe、run、receipt 证据。

CAP **不**接管认证、token、provider 账号、Git/SSH、语言工具链或任意用户目录。认证通过显式 `--auth-root` 提供，业务能力不能从用户目录或 provider ambient 配置隐式补齐。

## 2. 三个最重要的概念

### Profile

Profile 是一次运行的装配选择。每个 profile 有：

- 一个 prompt；
- 一条继承链；
- 四类能力的 `add`、`mask`、`replace` 操作。

当前链路是：

```text
real-home -> work -> general
                       assembly-helper
```

`work` 是共享工作层；`general` 和 `assembly-helper` 是可运行的叶子 profile。

### 能力闭包

能力闭包是某个 profile 最终能看到的 Skill、MCP、Hook、Plugin 集合。

```toml
[skills]
add = ["some-skill"]       # 增加项目内能力
mask = ["ambient-skill"]   # 移除继承能力
replace = ["shared-skill"] # 用项目内同名能力替换继承能力
```

- `add`：只能引用当前项目内存在的能力；
- `mask`：屏蔽已继承能力；
- `replace`：用当前项目内同名实现替换已继承能力；
- 不要直接改渲染目录或客户端原生配置来“临时修复”，下一次启动会被 CAP 覆盖或拒绝。

### 三层证据

| 层级 | 回答什么 | 主要证据 |
| --- | --- | --- |
| 声明态 | 仓库说自己要装什么 | manifest、profile、prompt、capabilities |
| 配置态 | lock、binding、render 是否一致 | `.cap/lock.json`、real-home manifest、pin、binding、render |
| 生效态 | 客户端实际加载了什么 | 真实 `run` 输出、marker、probe/diff |

文件存在或 lock 通过，不等于客户端已经原生加载。Hook、Plugin，以及部分客户端的 MCP/context 观察结果可能是 `unknown`。

## 3. 日常使用流程

以下命令从仓库根目录运行。

### 3.1 查看可用 profile

```bash
uv run cap agents
uv run cap profiles
uv run cap show assembly-helper
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
uv run cap run assembly-helper -- -p "检查当前 Agent 装配边界"
```

需要真实客户端交互时使用 `use`（它是 `launch` 的用户入口别名）。脚本和自动化优先使用显式 profile、client、auth-root 和 workdir。

### 3.3 修改 profile 或能力声明后

顺序固定：

```bash
uv run cap skills-validate
uv run cap lock
uv run cap bind work
uv run cap bind general
uv run cap bind assembly-helper
uv run cap verify
```

说明：

1. `skills-validate`：检查 Skill frontmatter、目录名和描述；
2. `lock`：把当前项目声明和渲染结果锁定；
3. `bind`：把 profile 绑定到已批准的 real-home digest；
4. `verify`：检查 lock、base pin、binding 和能力闭包。

`lock` 不会批准新的机器基座；`bind` 也不会自动刷新 base pin。

### 3.4 只渲染、不启动客户端

输出目录必须是项目外的既有空目录：

```bash
mkdir -p /var/tmp/cap-render
uv run cap render assembly-helper --cli omp --output /var/tmp/cap-render
```

渲染结果用于检查 prompt、Skill 和客户端 MCP 配置，不代表客户端一定已经生效。

## 4. real-home 是什么

`real-home` 是当前机器的只读基座。它可能包含：

- 用户级 context 和规则文件；
- 用户级 Skill、MCP、Hook、Plugin 候选；
- 客户端 settings 和配置入口。

CAP 不把这些内容复制进仓库，而是用以下链路绑定：

```text
真实 HOME
   -> 私有 real-home manifest
   -> workspace pin 审批 digest
   -> profile binding
   -> 项目 profile 的 mask/add/replace
   -> 客户端隔离 render/runtime
```

因此看到某个用户级能力存在，不等于它已被当前 profile 允许。它必须同时通过 profile 闭包和客户端启动门禁。

## 5. 看到能力告警怎么办

如果看到类似告警：

```text
profile: warning: ... out-of-scope base MCP(s): idea (...); they are not part of the project-declared capability closure
```

不要只重新运行。按下面顺序处理：

1. 记录 profile、能力名称和来源路径；
2. 执行 `uv run cap show <profile>`，确认当前声明闭包；
3. 如果能力不应使用，在 profile 中加入对应 `mask`；
4. 如果确实需要，先把能力作为项目内受审查资产声明，并使用 `add` 或 `replace`；
5. 重新执行 `lock`、`bind`、`verify`；
6. 只有 verify 通过后再启动客户端。

所有 profile 都应对实际工具面中未列入当前 inventory 的 MCP 立即告警。相同原则也适用于后续扩展到 Skill、Hook、Plugin 等纳管能力；“被用户目录发现”不能自动变成“被 profile 允许”。

## 6. 常见失败的含义

| 现象 | 含义 | 处理 |
| --- | --- | --- |
| `capability lock drift detected` | 声明改了但 lock 没刷新 | 审阅差异后运行 `uv run cap lock` |
| `binding is stale` | lock 或 base digest 变化，旧 binding 不再匹配 | 审阅后重新 `bind` |
| `active real-home drift detected` | 已批准基座的 active 能力发生变化 | 重新检查 manifest 和 pin，不要盲目继续 |
| `passive real-home drift` | 观察到非 active 配置变化 | 可继续，但要记录告警原因 |
| `project capability bypass detected` | 项目里出现未纳管的原生能力旁路 | 移除旁路或纳入当前声明；不要加例外 |
| `unknown` | 没有足够的真实客户端证据 | 不要当作“没有能力”，改为报告观察缺口 |

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
