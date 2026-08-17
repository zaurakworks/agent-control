# profile —— 显式能力面、三端隔离与生效态核验

`tools/profile/profile.py` 是唯一入口。它用一套严格 schema 锁定项目能力声明，用同一棵渲染树物化并启动 Codex、Qoder 或 OMP，再把声明态、配置态和实际生效态分开记录。没有默认 profile、自动推断或“上次选择”；每个需要 profile 的命令都必须同时给出 `--client` 和 `--profile`。

## 唯一 schema

一个受管项目只有下面这一套结构：

```text
AGENTS.md                              # 项目公共基线，只由客户端原生发现
.cap/manifest.toml                    # profile 名到 profile 文件的唯一索引
.cap/profiles/<profile>.toml          # 扁平闭包：prompt/skills/mcps/hooks/plugins
.cap/prompts/<profile>.md
.cap/capabilities/skills/<name>/...
.cap/capabilities/mcp/<name>.json
.cap/capabilities/hooks/<name>/targets/{codex,qoder,omp}/...
.cap/capabilities/plugins/<name>/targets/{codex,qoder,omp}/...
.cap/lock.json                        # 输入 content+mode、renderer 与三端 tree hash
```

所有路径必须是 `.cap` 下的规范 POSIX 相对路径，禁止 symlink、未引用能力、重复名字、未知字段和 overlay 路径冲突。能力来源首版只接受项目内文件；固定 commit vendoring 应先落成同样的项目内普通文件。根 `AGENTS.md` 不复制进 profile prompt，避免公共基线被加载两次。

隔离 fixture 在 [`fixtures/multi-profile/`](./fixtures/multi-profile/)；`review` 与 `implementation` 各有独立的 Skill、MCP、Hook、Plugin sentinel。

## 命令

以下命令都从仓库根运行；`<project>` 是包含 `AGENTS.md` 和 `.cap/` 的 Git worktree 根。

```text
python tools/profile/profile.py --project <project> list
python tools/profile/profile.py --project <project> explain --profile review
python tools/profile/profile.py --project <project> lock
python tools/profile/profile.py --project <project> verify

python tools/profile/profile.py --project <project> materialize \
  --client codex --profile review --output <existing-empty-dir>

python tools/profile/profile.py --project <project> launch \
  --client qoder --profile review --receipt <new-receipt.json> -- <client-args>

python tools/profile/profile.py --project <project> probe \
  --client omp --profile review --state <existing-empty-state-dir>

python tools/profile/profile.py --project <project> run \
  --client codex --profile review --state <existing-empty-state-dir> \
  -- exec "<prompt requesting the markers below>"

python tools/profile/profile.py --project <project> diff \
  --client codex --profile review --state <state-dir-from-run>
```

`lock` 是显式更新操作；它记录 manifest、profile、根 `AGENTS.md`、prompt、每个能力文件的 SHA-256 与 mode，并锁定 renderer、adapter 和三端输出树。`list`、`explain` 以及所有执行命令都先按当前输入重算并严格比对 lock；stale lock 不能只读未锁定声明。`materialize` 只接受项目和用户级原生能力根之外的既有空目录。
平台边界：首版安全写入后端依赖 POSIX `dir_fd`／`openat`／`O_NOFOLLOW`，当前试点支持 macOS 和 Linux；Windows 没有静默降级，会 fail closed。Windows 不是 Issue #62 的 fixture 验收范围；进入 Windows 前必须另行实现并验证 HANDLE-relative、拒绝 reparse point 的等价后端。


`launch` 是交互式薄 launcher；`run` 走完全相同的校验、渲染、参数门禁和临时运行根，只额外捕获一次 batch 输出供 observer 解析。Codex batch 参数通常是 `-- exec "<prompt>"`，Qoder 和 OMP 的 one-shot 参数是 `-- -p "<prompt>"`。工具不替调用者虚构跨客户端 task 参数。

## 三端会话根

每次 `launch` 或 `run` 都创建新的临时根，进程退出后清理：

| 客户端 | 隔离根与固定启动约束 |
| --- | --- |
| Codex | `CODEX_HOME=<runtime>`；profile prompt 渲染为 `<runtime>/AGENTS.md` |
| Qoder | `QODER_CONFIG_DIR=<runtime>`；清除 ambient `QODER_WORKING_DIR`，固定进程 cwd 为项目根；固定 `--config-dir`、`--strict-mcp-config`、`--mcp-config`，profile prompt 以文本传给 `--append-system-prompt` |
| OMP | `PI_CODING_AGENT_DIR=<runtime>`、`PI_CONFIG_DIR=<runtime>`；把 `OMP_PROFILE`/`PI_PROFILE` 固定为非空 `default`，把 `PI_CONFIG_FILES` 固定为 `<runtime>/config.yml`，阻止工作目录 `.env` 回填配置根；固定 Skill allowlist、`--no-extensions`、`--no-rules` |

启动前会移除所有 ambient 配置根和工作目录环境变量，再写入所选客户端的固定值。转发参数不能覆盖 config/profile/cwd/worktree/MCP/Skill/Hook/Plugin/Extension 根；Codex 的 `-p` 和 Qoder 的 `--worktree` 等原生别名同样被拒绝。门禁或 lock 失败发生在创建客户端进程之前。项目必须等于 Git worktree 根；项目中的 provider 原生目录、嵌套指令文件和 MCP 旁路按大小写不敏感路径语义拒绝，避免 macOS／Windows 上的大小写变体绕过。已知用户级业务能力路径及配置中的 capability-bearing key 也会被拒绝；只含模型、主题等运行参数的用户配置不算业务能力污染。

lock 校验后、启动前会重新渲染并再次核对 tree hash，并在最终创建进程前重新核对全部 lock inputs 和项目旁路，防止校验、物化与启动之间的漂移。物化树和 observer state 从文件系统根开始逐级持有 no-follow 目录描述符；只允许把 macOS `/var` 这类 root-owned 第一层系统 symlink 规范到其固定目标，其他 symlink ancestor 一律拒绝。render output、state 和 receipt 的“项目外／原生能力根外”边界按持有描述符的祖先 inode 身份判断，大小写别名不能绕过。目录项被换成 symlink 或其他 inode 时失败，写入不会跟随新路径；launcher 与 probe 从已锁的内存渲染树读取 prompt、Skill 和 MCP 元数据，不按可替换的 runtime pathname 回读。收据只保存 client/profile、adapter、inventory、lock/tree hash、参数数量、退出码和临时根清理结果；不保存参数值、环境值、输出正文或临时路径。显式收据路径的所有祖先都不得是 symlink，目标必须尚不存在；启动前用 exclusive create 预留目标，最终只通过已持有且身份复核过的文件描述符写入。收据 inode 在提交前后必须保持单一硬链接；同一路径的并发启动不能覆盖已有收据。

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

本工具不修改用户级配置，不接管 PATH，不是通用包管理器、CAS/GC、secret broker、权限 sandbox 或 MCP supervisor，也不承诺 Qoder/OMP 的 MCP 子进程失败会阻断会话。认证文件不会从真实 home 自动复制到临时根；三端认证 staging 仍是阻断未知项，未核实前不得据本试点实施全局封存。
