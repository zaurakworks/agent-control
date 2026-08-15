# Issue #4 实施证据（完成版）

检查时间：2026-08-08（America/New_York）  
分支：`feat/issue-4-grilling-dual-provider`

## 人话结论

`grilling` 已成为一份可追溯、可安装、可移除、能被 Codex 与 Claude 共用的 Plugin 资产。共同方法正文只保存一份，两个运行端各有薄包装和原生 Marketplace 文件。

两端五组合成行为都观察到当前合同：直接请求或明确接受后才开始问询；普通任务不会仅因复杂而展开问卷；拒绝后不重复建议；显式入口可用；退出时保留原任务、决定和未知项。结果证明本轮实现满足已批准的行为合同，但不证明真实工作收益或 ROI。

## 检查结果

| 检查对象 | 运行端与版本 | 操作 | 预期 | 实际 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 固定上游 | GitHub 固定提交 | 重新下载 3 个对象并复算字节、SHA-256、Git blob | 与 Plan 的冻结身份一致 | 三项全部一致 | 通过 |
| 共同正文 | 仓库静态检查 | 检查 Skill 数量、中文正文、双语 `description`、无翻译副本 | 只有一份可编辑正文 | 只有 `skills/grilling/SKILL.md` | 通过 |
| JSON 与路径 | PowerShell + Git | 解析 4 个 JSON，检查身份、版本、相对路径、文件集合、许可证与 `git diff --check` | 无逃逸、无额外能力或脚本 | 全部符合 | 通过 |
| Claude 严格格式 | Claude Code `2.1.221` | 分别校验 Plugin 根和 Marketplace 根，启用 `--strict` | 无错误和警告 | 两项均通过 | 通过 |
| Codex 生命周期 | Codex CLI `0.147.0` | 独立 `CODEX_HOME` 中做 2 次发现、安装、6 文件缓存比对、移除和恢复 | 每轮回到空状态 | 两轮均符合 | 通过 |
| Claude 生命周期 | Claude Code `2.1.221` | 独立 `CLAUDE_CONFIG_DIR` 中做 2 次严格校验、安装、6 文件缓存比对、卸载和恢复 | 每轮回到空状态 | 两轮均符合 | 通过 |
| Claude 行为 | `claude-sonnet-5`，会话级 `--plugin-dir` | 五组新会话 | 守住同意、拒绝、普通路径与退出 | 五组均观察到预期结果 | 本轮通过 |
| Codex 行为 | Codex CLI `0.147.0`，模型标识未由 CLI 输出 | 真实 Plugin 临时安装；五组新会话；只读 sandbox | 读取完整正文并守住同一合同 | 五组均观察到预期结果 | 本轮通过 |

## 用户实际看到的行为

| 场景 | Codex | Claude | 结论与边界 |
| --- | --- | --- | --- |
| 直接请求 | 读取完整中文 `SKILL.md` 后直接进入 Q1–Q5，没有重复索要同意 | 直接进入第一轮，没有重复询问是否同意 | 通过；均未实施 |
| 建议后接受 | 先给普通分析、升级选项和约一轮问题的成本；接受后同会话读取 Skill 并开始问询 | 先说明影响、收益、额外成本和普通出口；接受后自动调用 | 通过；接受后不要求再输入命令 |
| 普通或只是复杂 | 直接改写句子并给出恰好 15 项清单；没有读取 Skill 或展开问卷 | 直接完成改写和清单 | 通过；复杂度本身没有触发问询 |
| 建议后拒绝 | 只建议一次；拒绝后直接给普通路径三个原则 | 只建议一次；拒绝后直接给普通路径三个原则 | 通过；没有新风险证据，因此没有再次建议 |
| 显式入口与退出 | `$grilling` 被识别并读取 Skill；停止后只交接原任务、已确认决定、未知项和普通路径 | `/grilling:grilling` 被识别；停止后保留交接 | 通过；停止后没有继续提问 |

## Windows sandbox 临时处理

首次 Codex 行为检查失败在读取 Skill 的工具命令之前，错误为 `orchestrator_helper_launch_canceled: ShellExecuteExW failed to launch setup helper: 1223`。本机日志同时记录 `sandbox users missing or incompatible with marker version`。

复核结果：

- sandbox helper 文件存在，安装目录和 6 个 Plugin 缓存文件完整；
- 两个本地 sandbox 用户和 `CodexSandboxUsers` 组存在且启用；
- 无人处理 UAC 时，`elevated` 的最小只读探针卡在 helper/UAC 路径；
- 同一个探针仅增加单次 `windows.sandbox="unelevated"` 覆盖后成功；
- 用户在电脑旁可处理 UAC 后，重新执行 `codex sandbox -- cmd.exe /d /c echo sandbox-elevated-ok`，`elevated` 模式在 0.6 秒内输出 `sandbox-elevated-ok` 并以 0 退出；
- [OpenAI 官方文档](https://learn.chatgpt.com/docs/windows/windows-sandbox#configure-the-windows-sandbox)把 `unelevated` 定义为 elevated 初始化失败时的回退，仍保留受限 token 与文件边界，但隔离更弱；
- [openai/codex#36865](https://github.com/openai/codex/issues/36865)记录了不同 Codex 运行时共享或轮换 sandbox marker 后反复初始化的同类问题；精确的 1223 报告至少可追溯到 [#18845](https://github.com/openai/codex/issues/18845)，不是 0.147.0 Ratatui 升级才首次出现的错误。

因此，五组 Codex 行为测试只在各自命令上显式使用该覆盖，没有修改持久 `[windows] sandbox = "elevated"`，也没有使用 `danger-full-access`。人工可处理 UAC 后，最小 elevated 探针已经通过；完整五场行为矩阵仍保留为 unelevated 条件下的结果。上游问题仍开放，升级运行时或 marker 再变化时应先复测 elevated。

## 可观察成本

- Claude `plugin details` 估算：每会话常驻约 `67` token；Skill 单次调用约 `330` token。五个有效行为会话合计费用约 `$0.4135794`，实际模型为 `claude-sonnet-5`。
- Codex 五个有效行为场景共 8 个 turn，CLI 合计报告输入 `252811`、其中缓存输入 `175616`，输出 `10377`、推理输出 `5119`；可见运行时间约 `290.5` 秒。CLI 未报告模型标识或美元费用，因此两项记为未知。
- Codex 另有一次因结果转发错误而无法审查的直接请求调用，以及一次位置参数顺序错误的新会话；后者报告输入 `16214`、缓存输入 `11008`、输出 `69`、推理输出 `33`，并已按 UUID 删除。两次都不计为通过证据，但计入操作损耗。
- 当前没有真实任务收益、返工减少或打断成本数据，因此不能得出 ROI 结论。

## 状态恢复

- 真实运行根恢复为事前 3 个 Marketplace、13 个 Plugin，不含 `agent-plugins` 或 `grilling`；
- 应用运行根与默认 `~/.codex` 下的 `agent-plugins` 缓存均为 0 文件；
- 两个有效多轮会话和一次无效会话均按 UUID 精确删除；单轮会话使用 `--ephemeral`；
- Provider 写入时额外留下一个 77 字节的项目 trust 区块。先在内存中证明只移除该区块会把配置从 15745 字节恢复到 15668 字节，并得到事前 SHA-256，再做精确删除；
- 最终 `config.toml` SHA-256 为 `E42AE3E1C1684B08AA5F7392573D317AF96F9017873C7FC6CBD5E071FBFB6C76`，与事前一致；
- 没有修改、禁用、更新或删除其他 Marketplace、Plugin、Hook、规则或认证材料。

## 仍然未知

- 本轮是合成任务的单次观察，不代表所有模型、提示和长期使用都稳定；
- Codex CLI 没有输出实际模型标识；
- 最小 elevated 探针已经通过，但五场行为矩阵没有在 elevated 条件下整套重跑；
- 首版回退只证明恢复事前状态并可重新安装同一 `0.1.0`，不代表已经验证跨版本降级；
- 真实任务 ROI、维护成本和一个月后的上游变化仍需后续证据。
