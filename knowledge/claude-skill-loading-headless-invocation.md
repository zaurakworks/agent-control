# K27：Claude Code skill 装载时机与 headless 斜杠调用的已验证陷阱

> 状态：正式当前公共知识。
> 最近核验：2026-08-13。
> 适用对象：Claude Code 项目级 `.claude/skills/` 的装载发现时机；`claude -p` headless 子会话中以斜杠命令调用用户显式技能与真跑含命令技能；Git Bash（Git for Windows，MSYS 环境）作为发起宿主。
> 环境：Windows 11 本机；2026-08-13 两轮真跑（worktree w260-skills-eval 与 w263-matt-full-trial），子会话为 `claude -p`（claude-fable-5）；本机当日 Claude Code CLI 运行水位为 2.1.22x 代，子会话回执未逐次记录精确 CLI 版本号；`/reload-skills` 需 v2.1.152+（官方文档）。
> 版本边界：Claude Code 的 skill 目录监听、斜杠命令解析或权限模式语义变化，MSYS2／Git for Windows 的参数转换规则变化，均为失效信号。

## 回答的问题与价值门

会话中途把 skill 复制进新建的 `.claude/skills/` 后为什么报 `Unknown skill`？headless 子会话里斜杠命令为什么没有展开？Git Bash 发起 `claude -p "/cmd …"` 时命令为什么根本没送达？`--permission-mode acceptEdits` 下为什么技能中途瘫痪？

本仓以 `claude -p` 子会话真跑项目级 skills 是已建立的评测与交付手法（关联 [#260（skills 手上评测）](https://github.com/Eridanus117/agent-control/issues/260)、关联 [#263（matt 全量试用）](https://github.com/Eridanus117/agent-control/issues/263)合计 40+ 次子会话），四个陷阱全部为静默失败——没有报错、体感是「没反应」或「技能不灵」，逐个都实际耗费过重跑。后续每次以子会话装载或调用 skill 都会复用这些结论，通过价值门。

## 可直接复用的结论

### 1. 会话中途新建顶层 `.claude/skills/` 不被监听；先建目录或重启会话

Claude Code 对 skill 目录有 live change detection，但**只监听会话启动时已存在的顶层目录**。会话中途 `mkdir .claude/skills` 再复制 skill 进去，Skill 工具直接报 `Unknown skill`，新 spawn 的子代理清单同样不含它（实测：本会话 27 项清单不见新增项）。最短动作：v2.1.152+ 用 `/reload-skills`，否则新起 Session（启动时自然发现项目级 skills）。顶层目录已存在时向其中增删 skill 的行为不在本结论内（未单独实测）。

机制来源已核官方：关联 [#260（skills 手上评测）](https://github.com/Eridanus117/agent-control/issues/260)中由 research 技能真跑产出 16 个官方来源的调研文档并纠正「清单会话冻结」的过泛表述——准确机制是顶层目录监听时点，不是清单冻结。

### 2. 斜杠命令必须置于 prompt 首；`disable-model-invocation` 是工具层硬边界

`claude -p "<prompt>"` 中的斜杠命令只有位于 prompt 首才会被 harness 展开（转录中以 `<command-name>` 注入为证）。放在句中或句尾都不展开，且同型错误在同一 Session 里连犯两次（`wait-what` 置中段、`to-spec` 置句尾，均实测未展开）。斜杠未展开时模型可能好心尝试 Skill 工具调用，对 `disable-model-invocation: true` 的用户显式技能会被**工具层硬拦**——这同时证明用户显式是硬边界而非君子协定。置首重发后展开正常；关联 [#263（matt 全量试用）](https://github.com/Eridanus117/agent-control/issues/263)中 20 个用户显式技能置首调用 20/20 走通。

### 3. Git Bash 的 MSYS 路径转换会吃掉不含冒号的行首斜杠参数

Git Bash（MSYS）下发起 `claude -p "/teach …"` 时，若参数不含 `:`，MSYS 路径转换把行首 `/teach` 转成 `C:/Program Files/Git/teach`，斜杠命令根本没送达 CLI；参数含 `:` 则幸免（关联 [#263（matt 全量试用）](https://github.com/Eridanus117/agent-control/issues/263)前 5 个斜杠 prompt 全部恰好含冒号，纯属侥幸才未更早暴露）。症状词：子会话转录首条用户消息出现 `C:/Program Files/Git/<命令名>`。最短动作：命令加 `MSYS_NO_PATHCONV=1` 前缀（Git for Windows 抑制参数转换的机制）；命中该坑的技能在规避后重跑走通。失效信号：MSYS2／Git for Windows 转换规则或 claude CLI 参数处理变更。

### 4. headless `--permission-mode acceptEdits` 默认拒绝全部 Bash；真跑命令类技能须按域放行

`claude -p --permission-mode acceptEdits` 的子会话中 Bash 调用全部被拒；要真跑带命令的技能须按域显式加 `--allowedTools "Bash(git:*),Bash(python:*)"` 等。附带一个有界行为样本：tdd 技能首跑撞此权限墙时拒绝在跑不了红灯的情况下硬写实现，停在第一红灯前如实上报（25 turns）；放开 python 后 4 轮红绿全部真跑（单样本，不能推出所有技能在权限墙下都会如此守纪律）。

## 第一方来源与证据映射

1. [关联 #260（skills 手上评测）评测回执](https://github.com/Eridanus117/agent-control/issues/260#issuecomment-5283921655)：`Unknown skill` 实测、27 项清单不含新增项、research 真跑产出的官方来源调研与「顶层目录监听时点」纠正、`/reload-skills` 版本门；支持结论 1。
2. [关联 #263（matt 全量试用）评测交付](https://github.com/Eridanus117/agent-control/issues/263#issuecomment-5285930698)：自察记录①（同型置位错误两次）、wait-what 首跑「斜杠不展开＋模型代调被工具层硬拦」标本、20/20 用户显式走通计分板、蒸馏候选 1–3 的 MSYS 转换细节（含「前 5 个恰好含冒号」的侥幸边界）与 headless 权限墙及 tdd「宁停不假」样本；支持结论 2、3、4。
3. 工作产物与转录：两轮评测的子会话转录在本机 `~/.claude/projects/` 可复查，worktree 内 `.claude/skills/` 装载布局与微任务靶场未提交保留（复核入口见各评测回执尾部运行备忘）。

## 两道准入门逐项判定

| 准入项 | 判定 | 依据 |
| --- | --- | --- |
| 价值门 | 通过 | 以 `claude -p` 子会话装载与真跑 skill 是本仓已建立手法；四个陷阱全部静默失败且已各造成一次真实重跑成本。 |
| 1. 明确回答的问题 | 通过 | 四条结论分别限定装载时机、斜杠置位、MSYS 转换与权限模式四个具体故障。 |
| 2. 可直接使用的结论和必要解释 | 通过 | 每条给出症状、机制与最短动作。 |
| 3. 第一方来源或可重复验证过程 | 通过 | 两份远端评测回执保存实测细节；结论 1 另有官方文档核验；转录与 worktree 产物可复查；四条均可低成本重放。 |
| 4. 对象、版本、环境和核验时间 | 通过 | 页首列明环境、日期与版本记录边界（CLI 精确版本未逐次记录，如实声明）。 |
| 5. 例外、仍未知内容和不能推出的结论 | 通过 | 见下节。 |
| 6. 明确的失效条件 | 通过 | 页首版本边界与各结论内失效信号。 |
| 7. 下次最少复核步骤 | 通过 | 见最少复核节，每条一分钟内可重放。 |
| 8. 人容易理解、Agent 足以复用的表达 | 通过 | 症状词、机制与最短动作按坑卡形态组织。 |

## 例外、未知和不能推出的结论

- 结论 1 未覆盖「顶层目录已存在时增删单个 skill」的监听行为；也未测 `/reload-skills` 本身（本机当日未升级到该版本路径，版本门数值来自官方文档）。
- 结论 2 的 20/20 计分板来自 35 技能同场的单日环境；不能推出斜杠解析在所有 CLI 版本与交互式会话中行为一致（交互式会话未单独测）。
- 结论 3 只在 Git Bash（Git for Windows）实测；MSYS2 原生、WSL、PowerShell 宿主未测（PowerShell 无此转换机制，但未在本场景实证）。`MSYS_NO_PATHCONV=1` 为 Git for Windows 机制，MSYS2 原生对应物（`MSYS2_ARG_CONV_EXCL`）未测。
- 结论 4 的「按域放行」清单只核验过 git／python 域；tdd「宁停不假」是单样本行为观察，不是所有技能的保证。
- 四条结论都不能推出 Claude Code 官方对这些行为的长期承诺；均为运行端实测＋（结论 1）文档核验。

## 失效条件

1. Claude Code 变更 skill 目录监听、`/reload-skills`、斜杠命令解析或 `--permission-mode`／`--allowedTools` 语义（CHANGELOG 为信号面）；
2. MSYS2／Git for Windows 变更参数转换规则或 `MSYS_NO_PATHCONV` 语义；
3. 本机发起宿主从 Git Bash 迁移（结论 3 停止适用，其余仍待各自信号）。

## 下次最少复核步骤

1. 下次子会话装载 skill 前：确认 `.claude/skills/` 在会话（或子会话）启动前已存在；中途新建则直接新起子会话，不排查「为什么 Unknown skill」。
2. 下次斜杠调用：把斜杠命令置于 prompt 首；Git Bash 宿主且参数不含 `:` 时加 `MSYS_NO_PATHCONV=1`；发出后以转录首条用户消息核验命令送达（无 `C:/Program Files/Git/` 前缀、有 `<command-name>` 展开）。
3. 下次 headless 真跑含命令技能：按任务域预置 `--allowedTools`；技能中途「瘫住」时先查权限拒绝而不是技能质量。
4. Claude Code 升级后首次使用本包：快速重放上述任一条，行为变化即让对应结论退出直接复用。

## 不适用范围

- Codex 及其他 Provider 的 skill 装载机制（跨端验收见 [K10](./external-agent-capability-lifecycle.md)）；
- Plugin 安装、版本化缓存与 marketplace 语义（见 [K4](./claude-plugin-maintenance.md)）；
- 交互式会话的斜杠命令行为与用户级 `~/.claude/skills/` 目录（未实测）；
- 权限模式的安全策略选型（本包只记录实测边界，不建议放行范围）。
