# `grilling` 上游来源

## 人话结论

本目录中的方法来自 Matt Pocock 的 `grilling`，但不是未经修改的镜像。本仓固定了一个上游提交，保留其 MIT 许可证，并把本地加入的同意、成本、拒绝抑制、降级和交接规则逐项写在下面。

Codex 与 Claude 的清单文件、Marketplace 文件和本页都是本仓创建的包装，不是上游文件。

## 固定来源

- 上游仓库：<https://github.com/mattpocock/skills>
- 固定提交：[`84fdeffd12f2ee307994d1eb6feb48173b6e0502`](https://github.com/mattpocock/skills/commit/84fdeffd12f2ee307994d1eb6feb48173b6e0502)
- 上游提交时间：`2026-08-06T19:49:51Z`
- 本次复核时间：`2026-08-08`（America/New_York）
- 上游许可证：MIT，Copyright 2026 Matt Pocock
- 本地许可证副本：[`LICENSES/mattpocock-skills-MIT.txt`](LICENSES/mattpocock-skills-MIT.txt)

哈希均基于固定提交中的原始字节计算；Git blob 是 Git 对相同字节计算的对象标识。

| 上游文件 | Git blob | 字节 | SHA-256 |
| --- | --- | ---: | --- |
| `skills/productivity/grilling/SKILL.md` | `95bd01ee9049a7e08120d54af9cd6ceeef282335` | 1872 | `FA5C1E5EE76B1C8F1AE56101F52C9E239DE75D5C578ADC61227B92D10B7E52EF` |
| `skills/productivity/grilling/agents/openai.yaml` | `ddbdb96139c0c1dfe6bca698f39d0465674b8a39` | 113 | `1411D7DF7D99B7E621A1FF8283C8133CC2464BE63D064E52D8CE169C6800EE9B` |
| `LICENSE` | `f1dd2c09108dde1a5f56097cee8461b3ea834499` | 1068 | `0E7AC423BF2C6E223B7C5B156F8CF72DA49D748E56A1641402C31F22AD07DBB5` |

## 上游到本地的映射

| 上游文件 | 本地文件 | 关系 |
| --- | --- | --- |
| `skills/productivity/grilling/SKILL.md` | `skills/grilling/SKILL.md` | 翻译为中文并修改；共同方法正文只有这一份 |
| `skills/productivity/grilling/agents/openai.yaml` | `skills/grilling/agents/openai.yaml` | 派生并增加显式调用政策 |
| `LICENSE` | `LICENSES/mattpocock-skills-MIT.txt` | 原样复制 |

## 本地改造记录

| 类型 | 上游语义 | 本地处理 |
| --- | --- | --- |
| 保留 | 用决定树表示依赖关系 | 保留为内部组织方式，不要求用户理解方法术语 |
| 保留 | 分轮处理当前可以回答的独立问题 | 保留；依赖未决答案的问题延后 |
| 保留 | 每题给 Agent 推荐答案 | 保留，并要求说明主要理由 |
| 保留 | 事实由 Agent 调查，决定由用户作出 | 保留事实与价值决定的分工 |
| 保留 | 共同理解确认前不行动 | 保留，并补充人话总结与交接内容 |
| 修改 | 上游正文使用英文 | 共同正文以中文作为唯一权威版本；`description` 保留中英双语入口，运行时不再维护英文翻译副本 |
| 修改 | 描述主要由 `grill` 等触发词匹配 | 只在用户直接请求，或已明确接受一次建议时进入；复杂度和关键词本身不是同意 |
| 修改 | 必须派发子 Agent 调查事实 | 改为按当前工具和成本选择调查方式，不强制委派 |
| 修改 | “relentlessly”追问直到树为空 | 改为按决定价值控制成本；收益不足、问题已清楚或方法不合适时可以停止 |
| 新增 | 无问询前同意守卫 | 未见直接请求或明确接受时不得展开问题；最多建议一次并等待选择 |
| 新增 | 无拒绝后的重复建议规则 | 用户拒绝后，同一方法和理由不得换措辞重提；只有重要新证据才能重新建议 |
| 新增 | 无表达约束 | 跟随用户语言，优先普通词，问题编号清楚，不用内部实验术语描述选择 |
| 新增 | 无降级、换方法和退出交接 | 允许随时改变路径，并保留原任务、已确认决定与未知项 |
| 新增 | 只说“共同理解”，未定义完成交接 | 确认前先总结所选方向、拒绝的关键替代、未知和后续证据；确认后交回正常工作流 |
| 新增 | Codex 调用政策未显式声明 | 在 `agents/openai.yaml` 写明 `allow_implicit_invocation: true`，作为可审查的首次试验输入 |

## 本仓自行创建的包装

以下文件没有对应的上游原件：

- `.codex-plugin/plugin.json`
- `.claude-plugin/plugin.json`
- 仓根 `.agents/plugins/marketplace.json`
- 仓根 `.claude-plugin/marketplace.json`
- 本 `UPSTREAM.md`

它们只负责身份、版本、发现、安装和来源说明，不拥有第二份方法语义。

## 后续上游回顾规则

后续回顾只比较上述两个已采用的上游文件和根许可证。先固定新的候选提交，再逐项判断上游变化是否仍适用于本地合同；不得自动把上游当前内容合并或覆盖本地正文。

是否值得把这一步自动化，要等至少一次人工回顾产生真实成本和行动价值后再决定。
