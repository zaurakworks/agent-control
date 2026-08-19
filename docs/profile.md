# profile —— 真实 HOME 基座、显式能力层与生效态核验

`uv run cap` 是唯一用户入口；profile engine 只作为 CAP 的内部执行层。`real-home` 是机器本地、只读且需审批的基座 profile；仓库 profile 只能声明单继承链和显式 `add`／`mask`／`replace` 操作。CAP 用 workspace 外的私有 manifest、审批 pin 和 binding 把项目层绑定到特定机器基座，再用同一棵渲染树物化并启动 Codex、Qoder 或 OMP。没有默认 profile、自动推断或“上次选择”；每个需要 profile 的命令都必须显式给出 profile 和 `--cli`。

## 唯一 schema

一个受管项目只有下面这一套结构：

```text
AGENTS.md                              # 项目公共基线，只由客户端原生发现
.cap/manifest.toml                    # version=2；profile 名到文件的唯一索引
.cap/profiles/<profile>.toml          # version=2；extends + 四类 add/mask/replace
.cap/prompts/<profile>.md             # 当前层 prompt；按基座到叶子顺序拼接
.cap/capabilities/skills/<name>/...
.cap/capabilities/mcp/<name>.json
.cap/capabilities/hooks/<name>/targets/{codex,qoder,omp}/...
.cap/capabilities/plugins/<name>/targets/{codex,qoder,omp}/...
.cap/lock.json                        # 只锁仓库内可移植层

<private-user-state>/real-home.manifest.json  # 当前机器基座摘要，不入 Git
<workspace-control>/real-home.pin.json        # workspace 审批，不入 profile 仓
<workspace-control>/bindings/<profile>.binding.json
```

所有项目路径必须是 `.cap` 下的规范 POSIX 相对路径，禁止 symlink、未引用能力、重复名字、未知字段和 overlay 路径冲突。每个 profile 最多一个 `extends`；继承链必须无环且最多出现一次 `real-home`。`add` 遇到同名继承能力会失败，`mask` 与 `replace` 只能指向已继承名称；`replace` 使用项目内同名能力替换基座或上层实现。能力来源只接受项目内普通文件。根 `AGENTS.md` 不复制进 profile prompt，避免公共基线被加载两次。

`real-home` manifest 只记录候选路径、状态、能力 id、mode/内容摘要和聚合 digest；不记录配置正文、命令、endpoint、token、cookie、session、history 或 cache。Secret-only 值变化不改变摘要；影响能力集合或执行行为的变化会改变 active digest。manifest 必须为私有文件，pin 与 binding 不得提交到 profile 仓。

```toml
version = 2
extends = "real-home"
prompt = ".cap/prompts/review.md"

[skills]
add = ["review-skill"]
mask = ["ambient-skill"]
replace = ["shared-skill"]

[mcps]
add = []
mask = []
replace = []

[hooks]
add = []
mask = []
replace = []

[plugins]
add = []
mask = []
replace = []
```

## 命令

以下命令都从仓库根运行；`<project>` 是包含 `AGENTS.md` 和 `.cap/` 的 Git worktree 根。

```text
uv run cap --project <project> profiles
uv run cap --project <project> show review
uv run cap --project <project> lock

uv run cap --project <project> --base-manifest <private-user-state>/real-home.manifest.json \
  base-lock
uv run cap --project <project> --base-manifest <private-user-state>/real-home.manifest.json \
  --base-pin <workspace-control>/real-home.pin.json base-approve
uv run cap --project <project> --base-manifest <private-user-state>/real-home.manifest.json \
  --base-pin <workspace-control>/real-home.pin.json \
  --binding-dir <workspace-control>/bindings bind review

uv run cap --project <project> --base-manifest <private-user-state>/real-home.manifest.json \
  --base-pin <workspace-control>/real-home.pin.json \
  --binding-dir <workspace-control>/bindings verify

uv run cap --project <project> --base-manifest <private-user-state>/real-home.manifest.json \
  --base-pin <workspace-control>/real-home.pin.json \
  --binding-dir <workspace-control>/bindings \
  render review --cli codex --output <existing-empty-dir>

uv run cap --project <project> --base-manifest <private-user-state>/real-home.manifest.json \
  --base-pin <workspace-control>/real-home.pin.json \
  --binding-dir <workspace-control>/bindings \
  --auth-root <private-auth-root> \
  use review --cli omp --receipt <new-receipt.json> --workdir <git-worktree-root> \
  -- <client-args>
```

`lock` 是项目层的显式更新操作；它记录 manifest、profile、根 `AGENTS.md`、prompt、每个项目能力文件的 SHA-256 与 mode，并锁定 renderer、adapter 和三端输出树。`base-lock` 只刷新机器基座观察，不产生批准；`base-approve` 把观察到的 active digest 写入 workspace pin；`bind` 把一个已锁项目层绑定到该批准 digest。基座更新不会自动刷新 pin 或所有 derived binding。

`list`、`explain` 以及所有执行命令都严格比对项目 lock。使用 `real-home` 的 profile 还必须提供 manifest、pin 和 binding：batch 执行遇到 active drift 直接失败；交互 launch 会列出变化路径并要求输入 `continue`，但不会自动批准或改写 pin。passive drift 仅告警。`materialize` 只接受项目和用户级原生能力根之外的既有空目录。


`launch` 是交互式薄 launcher；`run` 走相同的项目 lock、base binding、参数门禁和临时运行根，只额外捕获一次 batch 输出供 observer 解析。Codex batch 参数通常是 `-- exec "<prompt>"`，Qoder 和 OMP 的 one-shot 参数是 `-- -p "<prompt>"`。工具不替调用者虚构跨客户端 task 参数。

## 三端运行根与真实 HOME

每次 `launch` 或 `run` 都创建新的临时 runtime；进程退出后清理。对于继承 `real-home` 的 profile，客户端进程保留真实 `HOME`，使 Git、SSH、语言工具链和其他宿主集成继续按用户环境工作；客户端配置与 Session 状态仍写入显式隔离根：

| 客户端 | 隔离根与固定启动约束 |
| --- | --- |
| Codex | `CODEX_HOME=<runtime>`；profile prompt 渲染为 `<runtime>/AGENTS.md`；认证只来自显式 `--auth-root` |
| Qoder | `QODER_CONFIG_DIR=<runtime>`；固定 `--config-dir`、`--strict-mcp-config`、`--mcp-config`；profile prompt 通过 `--append-system-prompt` 注入 |
| OMP | `PI_CODING_AGENT_DIR=<runtime>`、`PI_CONFIG_DIR=<runtime>`，但 `HOME=<real-home>`；固定 `PI_CONFIG_FILES=<runtime>/config.yml`、Skill allowlist、`--no-extensions`、`--no-rules` |

启动前会移除 ambient 客户端配置根和工作目录变量，再写入所选 profile 的隔离配置根；继承 `real-home` 时不改写 `HOME`。用户级业务能力不会被复制到渲染树：其可见性来自已审批基座，项目层只通过 `add`／`mask`／`replace` 改变闭包。OMP 仍清空可能绕过显式 broker 的 provider/API/OAuth/endpoint/cloud credential 环境变量，并禁用 AWS metadata；Git、SSH、语言工具链和其他非客户端宿主能力继续从真实 HOME 工作。转发参数不能覆盖 config/profile/cwd/worktree/MCP/Skill/Hook/Plugin/Extension 根。门禁、lock、binding 或认证库校验失败发生在创建客户端进程之前；客户端退出后会再次核对 base drift。项目必须等于 Git worktree 根，项目内 provider 原生目录、嵌套指令文件和 MCP 旁路仍按大小写不敏感路径语义拒绝。

不继承 `real-home` 的旧式全隔离 profile 仍使用窄宿主底座门禁：只允许逐字匹配内置 `host-floor-v1` 的用户级基线和已知、禁用或不可移除的宿主适配器。该门禁不是 `real-home` 的替代品；需要正常用户环境的 profile 必须显式继承、审批和绑定 `real-home`。

lock 校验后、启动前会重新渲染并再次核对 tree hash，并在最终创建进程前重新核对全部 lock inputs 和项目旁路，防止校验、物化与启动之间的漂移。物化树和 observer state 从文件系统根开始逐级持有 no-follow 目录描述符；只允许把 macOS `/var` 这类 root-owned 第一层系统 symlink 规范到其固定目标，其他 symlink ancestor 一律拒绝。render output、state 和 receipt 的“项目外／原生能力根外”边界按持有描述符的祖先 inode 身份判断，大小写别名不能绕过。目录项被换成 symlink 或其他 inode 时失败，写入不会跟随新路径；launcher 与 probe 从已锁的内存渲染树读取 prompt、Skill 和 MCP 元数据，不按可替换的 runtime pathname 回读。收据只保存 client/profile、adapter、inventory、lock/tree hash、参数数量、退出码和临时根清理结果；不保存参数值、环境值、输出正文或临时路径。显式收据路径的所有祖先都不得是 symlink，目标必须尚不存在；启动前用 exclusive create 预留目标，最终只通过已持有且身份复核过的文件描述符写入。收据 inode 在提交前后必须保持单一硬链接；同一路径的并发启动不能覆盖已有收据。

## 持久认证库

认证与业务能力分开。`--auth-root` 必须指向项目和三端原生全局能力根之外的既有私有目录：

```text
<auth-root>/
├── codex/
│   └── auth.json       # Codex 原生登录状态
├── qoder/
│   └── .auth/          # Qoder 原生登录状态目录
└── omp/
    ├── broker.json     # {"version":1,"url":"https://…"}；loopback 可用 http
    └── token           # 单行 bearer token
```

认证根及其可变目录必须由当前用户拥有、具备 owner `rwx` 且不得授予 group/other 权限。Codex `auth.json` 必须是 owner 可读写、无 group/other 权限、单一硬链接的普通文件；OMP metadata/token 必须 owner 可读且同样拒绝 group/other 权限和硬链接别名。读取凭据时会核对 inode、size、mtime、ctime；并发原地刷新最多重读三次，稳定但尚未形成完整 JSON/token 的快照也会重试。Qoder 会自行维护 `.auth/` 下的事务文件，因此普通文件允许只读共享位，但拒绝 group/other 写权限、symlink、特殊文件、硬链接别名、超过 256 个目录项、16 层或 16 MiB 的树。启动期间 Codex `auth.json` 与 Qoder `.auth/` 通过临时根内的定向 symlink 连接到这套持久认证源，刷新结果直接留在认证库；symlink 不属于 profile 渲染树，临时根删除不会删除认证源。OMP 只接收已验证且无控制字符的 broker URL/token；本工具不托管或启动 broker。子进程输出返回 observer 前会按最长匹配清除 token、调用路径与规范物理路径；收据和 observer state 不记录认证路径、token 或环境值。

## `probe`、`run`、`diff` 量的不是同一层

| | `probe` | `run` |
| --- | --- | --- |
| 是否启动 agent | 否 | 是 |
| 证据 | 已锁渲染树中的原生配置和落盘 Skill | 客户端输出中的自述 marker |
| 量的是 | 配置态 | 实际生效态 |
| 输出 | `declared.json` + `probed.json` | `declared.json` + `effective.json` + 无 secret 收据 |

`probe` 能可靠回答渲染树里有哪些 Skill 和 MCP 配置，但“文件存在”不能证明客户端加载了上下文、Hook 或 Plugin；这些维度写成 JSON `null`（unknown），候选和 staged inventory 分栏保存。它不会把不可观测项写成空数组。

`run` 从 stdout/stderr 的最后一个有效 marker 读取：

```text
SKILLS-AVAILABLE: name1, name2
MCP-AVAILABLE: none
CONTEXT-FILES: unknown
HOOKS-AVAILABLE: unknown
PLUGINS-AVAILABLE: unknown
```

`none` 是“已观察且为空”，落盘为 `[]`；`unknown`、缺少 marker 或明确“未知”都是观测失败，落盘为 `null`。两者绝不互换。`diff` 必须重新指定同一个 client/profile，并先确认当前 lock 与 `declared.json` 一致；观测到缺失或越界返回 1，任一维度 unknown 且无已知漂移返回 2，只有所有维度都实际观察且一致才返回 0。

Codex/Qoder/OMP 的运行时自述能力并不对称。Codex 的内置 MCP 不进配置表、名称多轮不稳定，且无法从提示内容可靠反推上下文文件路径；OMP 的 MCP 只核实到会话内 `/mcp`，未核实 one-shot 自述能等价列举 runtime resolved MCP。因此 Codex 的 MCP/context 与 OMP 的 MCP marker 只旁存为 `reported_client_limited`，effective observation 固定保持 unknown。Qoder 有静态 MCP/Plugin 列举接口；本工具首版不为这些差异另造第二套 schema，也不把配置文件解析冒充 runtime resolved 列表。真实产品无法可靠观测时保持 unknown。

## Hook、Plugin 与范围边界

Skill 是 `native-staging`，MCP 是 `native-config`。Hook 和 Plugin 的 target overlay 目前只证明“按 profile、按客户端进入隔离渲染树”，尚未完成三端原生加载验证，所以 lock 固定标为 **`opaque-staging`**；每个 Hook target 的唯一第一层根必须是 `hooks/`，每个 Plugin target 的唯一第一层根必须是 `plugins/`，不得写入另一 kind、Skill、配置或 prompt 路径。即使 batch 输出带有 Hook/Plugin marker，也只旁存为 `reported_opaque_staging`，不会升级成 effective observation。不得据 sentinel 落盘或 agent 自报宣称已经原生生效。

本工具不修改用户级配置，不接管 PATH，不是通用包管理器、CAS/GC、权限 sandbox、secret broker 或 MCP supervisor，也不承诺 Qoder/OMP 的 MCP 子进程失败会阻断会话。全局封存必须在三端都用显式认证库完成真实登录态验证后另行实施；launcher 不会从真实 home 自动回退或复制认证。
