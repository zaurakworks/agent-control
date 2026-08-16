# profile —— 锁定一个 agent 状态，并核验它没漂

把一份声明（`manifest.toml`）物化成可运行的配置 home，跑完再比对**实际生效态**。

目的是「锁定某个智能体的最优状态」：声明进 git，可 diff、可 tag、可回滚；生效态每次运行捕获，跟声明比对。**只有声明是锁不住的，只有生效态是没法回滚的，所以两半都要。**

## 用法

```
python profile.py materialize <profile-dir>              # 只物化，不跑
python profile.py probe       <profile-dir>              # 秒级，无模型调用
python profile.py run         <profile-dir> --task <t.md>  # 分钟级，要 token
python profile.py diff        <profile-dir>              # 比对上一次 run
```

现有 profile：`observe/`（Claude）、`observe-codex/`（Codex）。两个跑同一个观察任务，用来自检。

## 两个量具，量的不是同一个东西

| | `probe` | `run` |
| --- | --- | --- |
| 手段 | CLI 只读子命令 + 文件系统 | 真跑一次 agent，读它的自报 |
| 实测耗时 | Claude 4.6 s / Codex 0.14 s | Claude 232 s / Codex 281 s |
| 成本 | 0 token | 一次完整会话 |
| 量的是 | **配置面**（配了什么） | **生效面**（运行时看得见什么） |

**两个方向都会错，所以 `probe` 只能降低 `run` 的频率，不能取代它：**

- **Claude 侧 `probe` 多报**：`claude mcp list` 不接受 `--strict-mcp-config`，会报出运行期已被拦掉的连接器；
- **Codex 侧 `probe` 少报**：`codex mcp list` 报「一个都没配」，而 agent 实际看得见内置的 `codex_apps` 及其 3 个连接器。

第二种更危险——**配置面上完全不可见的能力**。差值本身是要看的信号。

`run` 依赖 agent 自报，而自报的标识符不稳定：同一批 Codex 连接器两轮运行一次报 id、一次报显示名。所以 `[uncontrollable]` 里两种写法都列。

## 受检的三个维度

| 维度 | 声明 | 运行时标记 |
| --- | --- | --- |
| skill | `[skills] allow` / `deny` | `SKILLS-AVAILABLE` |
| MCP | `[mcp] allow` / `strict` | `MCP-AVAILABLE` |
| 上下文文件 | `[context] allow` | `CONTEXT-FILES` |

标记的确切格式由 [`.claude/skills/stage`](../../.claude/skills/stage/SKILL.md) 的「运行面自述」一节承载，四个阶段共用一份。

**`none` 和 `unknown` 必须分开**：`none` 是观察结果，`unknown` 是观测失败。把 `unknown` 当成 `none`，漂移检测就会报假阴性——这是已经发生过一次的错误。

## 白名单是物理的

`CLAUDE_CONFIG_DIR`（Claude）和 `CODEX_HOME`（Codex）都是整个配置目录重定向。物化时只把白名单里的 skill 复制进去，**不在名单里的在磁盘上根本不存在**——比 `skillOverrides` 那种黑名单强，因为黑名单要求你先知道有什么可关。

但重定向管不住一切，实测边界如下。

## `[uncontrollable]` 是有据的，不是懒得管

没证据就声明「管不了」，等于把可修的问题登记成既成事实，比漏掉更危险。每一条都要有证据：

| 对象 | 真实来源 | 能不能关 |
| --- | --- | --- |
| Claude 的 `dataviz` / `keybindings-help` / `fewer-permission-prompts` / `security-review` / `simplify` / `claude-api` | `claude.exe` 二进制内（grep 命中，用户目录全树无同名） | 部分可用 `skillOverrides` 黑名单逐个关 |
| Claude 的 `code-review` | `~/.claude/plugins/marketplaces/claude-plugins-official/` | 磁盘上，但该发现路径不受 `CLAUDE_CONFIG_DIR` 影响 |
| Codex 的 5 个 `.system` skill | 真实 `~/.codex/skills/.system/`，且 Codex 会在物化 home 里自建一份 | 原则上可控（是文件），未验证怎么阻止 |
| Claude 的账号级 MCP 连接器 | 账号，非配置文件 | **能关**：`--strict-mcp-config` 且不给 `--mcp-config` |
| Codex 的 `codex_apps` | 内置，不进配置表 | 未找到开关 |
| 用户级 `~/.claude/CLAUDE.md` | 真实用户目录 | **关不掉**，见下 |

### 用户级 `CLAUDE.md`：四个变体都失败

| 变体 | 结果 |
| --- | --- |
| 基线 | 加载 |
| `--setting-sources project,local` | 加载 |
| 同上 + `--settings <home>/settings.json` | 加载 |
| 重定向 `HOME` + `USERPROFILE` | 加载 |

Claude Code 用 OS API 解析真实用户目录，不看环境变量。唯一的修法是删掉那个文件。

**顺带一个陷阱**：`--setting-sources project,local` 会把 `skillOverrides` 一起干掉（被 deny 的 5 个 skill 全部回来，可用数 8 → 13）。想关一个东西却打开了五个能写的 skill——这种反向漂移不做实验看不出来。

## 物化 home 在仓库之外

默认落在 `%LOCALAPPDATA%/agent-control-profiles/<profile>/`，可用 `[homes] root` 覆盖。两个理由：

1. `CLAUDE.md` / `AGENTS.md` 按 cwd 及其祖先发现。home 放在仓库里，仓库根就是祖先，本仓那 12 KB 入口会进每一次运行的上下文——量具污染被测对象。
2. home 里有播种进去的凭据。放在仓库外，「不小心提交」在物理上不可能，而不是靠一条 `.gitignore` 撑着。

## workdir 为什么是第三个目录

`[run] workdir` 默认 `<work>`，落在 `%LOCALAPPDATA%/agent-control-profiles/<profile>-work/`。它既不是仓库，也不是物化 home。三个约束叠出来只剩这一个位置：

1. **不能在仓库里**——`CLAUDE.md` / `AGENTS.md` 按 cwd 及其祖先发现，仓库根一旦成为祖先，本仓那 12 KB 入口会进每一次运行的上下文；
2. **不能是物化 home 本身**——home 就是 `CODEX_HOME`，Codex 的 `workspace-write` 沙箱**拒绝 agent 往自己的配置目录写**（实测 `out.md` 写入被拒，整轮无交付）；
3. **任务文件得在 cwd 内**——同一个沙箱只放行 cwd 内的读写。任务留在仓库里时，三次读取尝试全部挂起且无输出。

所以 `run` 会先把任务文件拷进 workdir，再把 agent 指向那个副本。

前两次尝试（`workdir = profile 目录`、`workdir = <home>`）各撞上其中一条，都是落仓之后才暴露的——**在 scratchpad 里跑，这三条一条都不会触发。**

两次失败里量具本身都表现正确：它把「读不到」和「写不进」都报成 `unknown`，没有说成「无漂移」。需要在某个项目里干活的 profile 显式声明 `workdir` 指向那个项目。

每次物化建一个带时间戳的新目录，保留最近 3 个。不复用不是洁癖：Windows 上 CLI 建的 `projects/` / `sessions/` 在进程退出后仍被短暂持有，`rmtree` 会以 `WinError 145` 失败。

## manifest 里的路径令牌

manifest 进 git，所以不写死任何一台机器的绝对路径：

| 令牌 | 展开为 |
| --- | --- |
| `<repo>` | 仓库根 |
| `<skills>` | `<repo>/.claude/skills` |
| `<userhome>` | 真实用户目录 |
| `<home>` | 本次物化出来的 home |

## 规则只有一份来源

阶段规则**不进系统提示词**，唯一来源是 `.claude/skills/stage`，由锚点第 5 条按名触发加载。锚点本身也指向 skill 树里的 `anchor.md`。

profile 目录里因此没有任何一份规则副本。上一版有过两份（`stage.md` 和 `_shared/anchor.md`），其中 `stage.md` 已经比仓库里的 `references/observe.md` 旧了一个版本，导致同一个上下文里出现两套冲突的指令。
