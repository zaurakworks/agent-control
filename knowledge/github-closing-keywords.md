# K3：GitHub 关闭关键词不解析否定句

> 状态：正式当前公共知识。
> 最近核验：2026-08-11。
> 适用对象：GitHub.com 对 PR 正文中关闭关键词（close/closes/fix/fixes/resolve/resolves 等 + #编号）的解析。
> 环境：github.com 托管服务，Eridanus117/agent-control 仓库实例。
> 版本边界：托管服务行为无版本号；平台解析行为变更即失效信号。

## 回答的问题与价值门

在 PR 正文里写「不关闭 #N」（如 "does not close #N"）安全吗？如何在 PR 中引用一个不应被它关闭的 Issue？

本仓所有分片 PR 都要求引用父合同而不关闭它；此陷阱已造成一次真实误关（父合同 [#44](https://github.com/Eridanus117/agent-control/issues/44) 被单分片 PR 合并时关闭、需人工重开），结论在每次开 PR 时复用，通过价值门。

## 可直接复用的结论

GitHub 按「关键词 + #编号」的模式匹配关闭引用，不理解否定语境：正文含 "does not close [#44](https://github.com/Eridanus117/agent-control/issues/44)" 的 PR [#47](https://github.com/Eridanus117/agent-control/issues/47) 于 2026-08-11 合并时照样自动关闭了 [#44（14:49:52Z 关闭，14:55:47Z 人工重开）](https://github.com/Eridanus117/agent-control/issues/44)。且这一解析可随时零成本复现：截至 2026-08-11，PR [#47](https://github.com/Eridanus117/agent-control/issues/47) 当前正文只剩否定句，`gh pr view 47 --json closingIssuesReferences` 仍返回 [#44](https://github.com/Eridanus117/agent-control/issues/44)——解析器把否定句中的关键词照常入账。

对策（本仓现行惯例）：PR 正文、提交说明中引用不应关闭的 Issue 时，禁用关键词模式，一律写「关联 #N」「Part of #N」等无关键词表述；确需否定表述时不要让关键词与 #编号 相邻出现。

## 第一方来源

- PR Eridanus117/agent-control[#47](https://github.com/Eridanus117/agent-control/issues/47) 当前正文（含 "This PR does not close [#44](https://github.com/Eridanus117/agent-control/issues/44) …" 句）；
- `gh pr view 47 --json closingIssuesReferences` 实测输出（2026-08-11）：返回 Issue [#44](https://github.com/Eridanus117/agent-control/issues/44)；
- Issue [#44](https://github.com/Eridanus117/agent-control/issues/44) 时间线：2026-08-11T14:49:52Z closed → 14:55:47Z reopened；[#44](https://github.com/Eridanus117/agent-control/issues/44) 内「状态更正」评论记录根因与对策。
- 辅助来源：GitHub 官方文档「Linking a pull request to an issue」列出关键词清单，未承诺任何否定语境解析。

## 例外、未知和不能推出的结论

- 未逐个实测全部关键词变体与跨仓引用格式；结论基于 close 系实例与官方关键词清单的模式一致性。
- 未知 GitHub 是否会改进该解析，无公开承诺。
- 本包只核验 PR 正文语境；提交说明进入默认分支时的同类解析未单独实测。Issue 评论中的关键词不会关闭 Issue，不属本包范围。

## 失效条件

1. `closingIssuesReferences` 对否定句不再返回被引用 Issue；
2. GitHub 官方文档宣布关闭引用解析的语义变更。

## 下次最少复核步骤

运行 `gh pr view 47 --repo Eridanus117/agent-control --json closingIssuesReferences`：仍返回 [#44](https://github.com/Eridanus117/agent-control/issues/44) 则结论成立；不再返回则用一个新样本重测并更新本包。
