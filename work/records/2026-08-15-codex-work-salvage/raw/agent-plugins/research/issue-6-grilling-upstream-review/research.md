# Issue #6 Research：`grilling` 上游手工回顾

## 范围

- 决策用途：为“月度自动化、低频手工、停止主动回顾”提供一次真实维护样本。
- 上游：`mattpocock/skills`。
- 基线提交：`84fdeffd12f2ee307994d1eb6feb48173b6e0502`。
- 唯一比较路径：
  - `skills/productivity/grilling/SKILL.md`
  - `skills/productivity/grilling/agents/openai.yaml`
  - `LICENSE`
- 开始时间：`2026-08-08T23:06:39.5560691-04:00`。

## 调研合同

- 一次上游快照；先比较 Git blob，只有变化路径才读差异。
- 无变化立即停止事实收集。
- 不扫描其他 Skill，不研究 Provider 生态，不派发子 Agent，不实现自动化或修改资产。
- GitHub API 请求、命令、经过时间、人工判断点和可行动结果都要记录。
- 若需要扩大对象或成本，先触发调研升级门。

## 已读取的仓库指导

- `README.md`
- `docs/asset-model.md`
- `docs/conformance.md`
- `plugins/grilling/UPSTREAM.md`
- 父事项 #1、已完成 C1 #4、D1 #6 与 framing Challenge

## 基线事实

| 路径 | Git blob | 字节 | SHA-256 |
| --- | --- | ---: | --- |
| `skills/productivity/grilling/SKILL.md` | `95bd01ee9049a7e08120d54af9cd6ceeef282335` | 1872 | `FA5C1E5EE76B1C8F1AE56101F52C9E239DE75D5C578ADC61227B92D10B7E52EF` |
| `skills/productivity/grilling/agents/openai.yaml` | `ddbdb96139c0c1dfe6bca698f39d0465674b8a39` | 113 | `1411D7DF7D99B7E621A1FF8283C8133CC2464BE63D064E52D8CE169C6800EE9B` |
| `LICENSE` | `f1dd2c09108dde1a5f56097cee8461b3ea834499` | 1068 | `0E7AC423BF2C6E223B7C5B156F8CF72DA49D748E56A1641402C31F22AD07DBB5` |

## 成本计数

- 上游网络请求：`1`（一个 GitHub GraphQL 请求同时固定候选提交并读取三条路径的基线/候选 blob）。
- 调研命令：`2`（记录起点与本地基线；获取并比较上游快照）。
- 人工判断点：`2`：
  1. 确认三条路径足以支持本次维护 ROI 样本；
  2. 候选提交与基线相同后应用“无变化立即停止”，不扩大调研。
- 开始时间：`2026-08-08T23:06:39.5560691-04:00`。
- 事实收集结束：`2026-08-08T23:07:22.9357643-04:00`。
- 经过时间：约 `43.4` 秒（包含本地基线读取和一次上游请求）。
- 模型 Token / 美元成本：当前工具没有为这段操作提供可分离数据，保持未知；未为补齐它增加遥测。

## 上游快照

- 默认分支：`main`。
- 候选提交：`84fdeffd12f2ee307994d1eb6feb48173b6e0502`。
- 候选提交时间：`2026-08-06T19:49:51Z`。
- 候选提交标题：`Merge pull request #788 from mattpocock/grill-me-align`。
- 候选提交与基线提交完全相同。

## 三路径结果

| 路径 | 基线 blob | 候选 blob | 基线 / 候选字节 | 事实结论 |
| --- | --- | --- | ---: | --- |
| `skills/productivity/grilling/SKILL.md` | `95bd01ee9049a7e08120d54af9cd6ceeef282335` | `95bd01ee9049a7e08120d54af9cd6ceeef282335` | `1872 / 1872` | 无变化 |
| `skills/productivity/grilling/agents/openai.yaml` | `ddbdb96139c0c1dfe6bca698f39d0465674b8a39` | `ddbdb96139c0c1dfe6bca698f39d0465674b8a39` | `113 / 113` | 无变化 |
| `LICENSE` | `f1dd2c09108dde1a5f56097cee8461b3ea834499` | `f1dd2c09108dde1a5f56097cee8461b3ea834499` | `1068 / 1068` | 无变化 |

Git blob 相同表示对应原始字节相同，因此候选仍沿用 `UPSTREAM.md` 中的 SHA-256；无需下载或重算第二份正文。

## 停止结果

- 三条路径均无变化，没有需要分析的差异。
- 没有发现影响本地派生合同、许可证或 Provider 元数据的新事实。
- 没有产生资产修改、版本更新或其他可执行动作。
- 按事前停止条件结束事实收集；没有扫描其他 Skill、其他仓库或 Provider 生态。

## 剩余未知

- 本次只观察到“零变化”样本，不能估计未来发生真实变化时的语义判断成本。
- 本次没有独立可取得的模型 Token 或美元成本。
