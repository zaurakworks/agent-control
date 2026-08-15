# 原始来源索引

本索引登记 `work/current.md` 收敛与联邦式入口实施所依据的原始材料。来源保留不表示内容仍然有效；当前权威、最新负责人指令和远端当前合同优先。

## S01｜迁移前 `work/current.md` 完整快照

- 位置：[`current-before-migration.md`](./current-before-migration.md)；
- 来源提交：`fcfba814de4ac0e31480fe0d7ac5e715478d5b2c` 的 `work/current.md`；
- 大小／SHA-256：`22074` 字节／`219B4C271DBFBDF61F3F0798FBE32F72B47B3A90BD43E13DF0AA1B7ED00E9A2B`；规范化 Git blob 与来源均为 `7e8ea6048c5033265f56feb89cef3657c5c8c33f`；
- 保存方式：迁移前逐行复制；仅将工作树 CRLF 规范化为仓库使用的 LF，`git diff --no-index --ignore-space-at-eol` 无内容差异；
- 核对方式：`git show fcfba814de4ac0e31480fe0d7ac5e715478d5b2c:work/current.md`、`git diff --no-index --ignore-space-at-eol`；
- 限制：它是 2026-08-10 的活动状态快照，包含已经被替代的判断、旧授权和动态工具状态，不能用于恢复授权。

## S02｜`agent-control` Git 历史

- 仓库：`https://github.com/Eridanus117/agent-control`；
- 关键提交：`e37e3e0`（切换诉求传递主线）、`a047de7`（记录看板状态纠正）、`d323bca`（异步验收与额度速度候选）、`5e08cd2`（低成本审阅与默认整合）、`fcfba81`（升级为联邦式自主闭环）；
- 核对方式：`git log --oneline`、`git show <commit>:work/current.md`；
- 限制：Git 保存文件变化，不保存所有会话理由；历史提交不是当前权威。

## S03｜诉求传递链方案与负责人纠正

- [agent-control#19](https://github.com/Eridanus117/agent-control/issues/19)：原始问题、方法、成功条件、成本和授权；
- [基线诊断](https://github.com/Eridanus117/agent-control/issues/19#issuecomment-5242819066)；
- [攻防](https://github.com/Eridanus117/agent-control/issues/19#issuecomment-5242832673)；
- [受限调研](https://github.com/Eridanus117/agent-control/issues/19#issuecomment-5242879534)；
- [负责人纠正与联邦式完整闭环](https://github.com/Eridanus117/agent-control/issues/19#issuecomment-5242997604)；
- 限制：评论保存推演和已表达纠正；正式长期结论仍以当前权威为准。

## S04｜相关 GitHub 交付合同与证据

- [agent-control#16](https://github.com/Eridanus117/agent-control/issues/16)：资源观测与并发实验父合同；
- [agent-control#17](https://github.com/Eridanus117/agent-control/issues/17)：真实并发批次；
- [agent-control#18](https://github.com/Eridanus117/agent-control/issues/18)：共享写入协作方案；
- [agent-control#20](https://github.com/Eridanus117/agent-control/issues/20)：本次入口与快照交付合同；
- [agent-control#21](https://github.com/Eridanus117/agent-control/issues/21)：三个 Session 整合验收；
- [agent-plugins#19](https://github.com/Eridanus117/agent-plugins/issues/19)、[agent-plugins#21](https://github.com/Eridanus117/agent-plugins/issues/21)、[agent-plugins#24](https://github.com/Eridanus117/agent-plugins/issues/24)：资源观测、Windows 修复和 Issue 子树工作流合同；
- 相关 PR 与提交：`agent-control` PR [#20](https://github.com/Eridanus117/agent-control/issues/20)；`agent-plugins` PR [#22](https://github.com/Eridanus117/agent-plugins/issues/22)、[#23](https://github.com/Eridanus117/agent-plugins/issues/23)；提交 `68012a50c609cb424e35167f7c9d506ec1b7d878`、`ea8f66ed7ed9df554b5240e2b7513e7f04088c42`、`b2572dc901135708c650dd1fc334a3540820692e`；
- 限制：Issue／PR 的旧正文和旧 head 可能被后续状态替代，恢复时必须重读远端当前状态。

## S05｜Orca 协调运行记录

- Run：`run_8f829c43983e`；
- 资源并发批次：Task `task_8b3ab48b27c3`／Dispatch `ctx_5d26157ad9ce`，Task `task_5068369b44de`／Dispatch `ctx_f402ba9f5221`；
- 安装验收样本：Task `task_eec136df2cbf`／Dispatch `ctx_3e7c7c93c5c8`；
- 本次入口交付：Task `task_7453a1e6b730`／Dispatch `ctx_4bfaa4a38dbe`；
- 核对方式：`orca orchestration run-show`、`task-list`、`dispatch-show` 与持久消息；
- 限制：Orca 运行态证明任务与消息来源，不是产品权威、GitHub 持久合同或长期依赖决定。

## S06｜本记录的外部研究来源

受限调研使用的 Scrum Guide、NASA 双向追踪、GitHub Sub-issues／Projects、OpenAI Harness engineering、Anthropic Context engineering 和多 Agent 生产案例都列在 S03 的“受限调研”评论中。本记录只保留已经影响方案的结论，不复制原文，也不把案例升级为权威。

## S07｜负责人新增的全局脚本语言规则

- Orca 消息：`msg_6f7a25bce52d`，Run `run_8f829c43983e`，发给本次 Dispatch `ctx_4bfaa4a38dbe`；
- 合并前作用域纠正：Task `task_2b4478780c1a`／Dispatch `ctx_5266427014cb` 明确该规则对这台电脑上 Codex／Claude Code 参与维护的所有仓库、Provider、Session 和 worktree 生效，不因仓库入口条件而缩窄；
- 当前结论：持久程序、CLI、自动化和验证脚本只允许 Go、Python、TypeScript 或 Rust；不得沉淀 PowerShell、Batch 或 Shell 产品脚本；文档配置与 Windows 一次性 shell 命令保持边界；语言当前是否安装不能作为排除理由；
- 本次影响：删除尚未提交的 `scripts/Test-FederatedEntry.ps1`，以 `scripts/test_federated_entry.py` 替代；入口、权威、短快照和本记录同步该纠正，其他不受影响路径继续；
- 限制：该规则不授权批量改写当前 Issue 范围外既有资产；后续实际触及或替换时才按当前规则处理。

## S08｜`NORMALIZE-20260811-1` 远端合同与 Orca 运行

- 授权与父级：[agent-control#26](https://github.com/Eridanus117/agent-control/issues/26)、[agent-control#27](https://github.com/Eridanus117/agent-control/issues/27)；
- 四个交付：[agent-control#37／PR #39](https://github.com/Eridanus117/agent-control/issues/37)、[agent-control#38／PR #40](https://github.com/Eridanus117/agent-control/issues/38)、[agent-plugins#30／PR #31](https://github.com/Eridanus117/agent-plugins/issues/30)、[agent-plugins#32／PR #33](https://github.com/Eridanus117/agent-plugins/issues/32)；
- [#32](https://github.com/Eridanus117/agent-plugins/issues/32) 的过程纠正：[首次误判纠正](https://github.com/Eridanus117/agent-plugins/issues/32#issuecomment-5251139788)、[反向样本事实纠正](https://github.com/Eridanus117/agent-plugins/issues/32#issuecomment-5251379620)、[整合验收回执](https://github.com/Eridanus117/agent-plugins/issues/32#issuecomment-5251413856)；
- Orca Run：`run_66ae8eb4d020`；代表 Dispatch 为 `ctx_f32697c048c5`、`ctx_9d56dc0ade58`、`ctx_406a3ea7a42b`；
- 保存方式：远端 Issue／PR 保存合同、审查、纠正和整合回执；本记录只保存可读因果，不复制 Orca 数据库或完整终端转录；
- 限制：远端评论保留历史但可能被后续纠正；Orca 错误码、命令形态和资源状态是 1.4.177 当前环境观察，不是长期产品合同。恢复时必须重读当前 Issue、PR、Project 与工具指南。

## S09｜[#26](https://github.com/Eridanus117/agent-control/issues/26) 父目标级独立复核与新增摩擦

- 复核来源：[父目标级独立只读复核](https://github.com/Eridanus117/agent-control/issues/26#issuecomment-5251678848)；[时区事实纠正](https://github.com/Eridanus117/agent-control/issues/26#issuecomment-5251742364)；[#27 最终整合回执](https://github.com/Eridanus117/agent-control/issues/27#issuecomment-5251784524)；
- Orca 身份：Run `run_66ae8eb4d020`、Task `task_c1b95c710642`、Dispatch `ctx_ded75d7d689d`、Claude Session `2298bdaf-684c-4565-8ab7-0e0d40ccfaed`；
- 新摩擦：[低层 capability 写路径缺失](https://github.com/Eridanus117/agent-control/issues/31#issuecomment-5251708510)、[Claude Marketplace 实际来源](https://github.com/Eridanus117/agent-control/issues/32#issuecomment-5251708961)、[无时区时间误标](https://github.com/Eridanus117/agent-control/issues/28#issuecomment-5251742718)；
- Project 校正：agent-control[#26](https://github.com/Eridanus117/agent-control/issues/26) 与 agent-plugins[#28](https://github.com/Eridanus117/agent-plugins/issues/28) 的证据等级均为“当前交付验收”；
- 限制：审查评论中的原时间区间已经被后续纠正；Orca rejected `worker_done` 不能作为生命周期成功回执，结论以远端复核评论与 Delivery 原始正文共同锚定。

## S10｜Orca 环境与 Skill 描述预算收口

- 远端事实：[环境与 Skill 预算收口](https://github.com/Eridanus117/agent-control/issues/27#issuecomment-5252498930)；
- 合同与纠偏：[#27 当前压缩正文](https://github.com/Eridanus117/agent-control/issues/27)、[#28 E04](https://github.com/Eridanus117/agent-control/issues/28#issuecomment-5252564055)；
- 官方来源：[OpenAI Plugins 文档](https://learn.chatgpt.com/docs/plugins)；
- 本机来源：`codex plugin list --json`、已启用 Plugin 目录中的 `SKILL.md` frontmatter、注册表 Machine／User PATH、恢复后进程 PATH；
- 限制：15,790 是本机当前启用 Plugin 目录中描述字符的近似合计，不是 OpenAI 公布的预算阈值或 Token 数；一次截短提示不证明错误路由或能力失效。
