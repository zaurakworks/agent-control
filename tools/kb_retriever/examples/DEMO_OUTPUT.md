# 主动问路端到端演示记录

- 运行日期：2026-08-13
- 运行命令：`python tools/kb_retriever/examples/workflow_checkpoints.py`
- 卡片来源：`knowledge/retrieval-cards.md`
- 结果：3/3 个显式查询命中预期卡，进程返回码为 0。

## 命中结果

| 场景 | 查询上下文 | 命中 | reason | BM25 | 本次演示中由最短卡排除的分支 |
| --- | --- | --- | --- | ---: | --- |
| 装端指纹验收 | `pre-acceptance` / `agent-plugin.installed-copy` | 卡 B（三端指纹） | `matched` | 14.668377 | 按原始哈希直接判坏，或跨版本通配到旧缓存后再返工 |
| Token 燃烧测量决策 | `pre-capacity-decision` / `codex.token-burn` | 卡 J（Token 燃烧测量） | `matched` | 15.386123 | 把 `costUSD` 当账单，或把 Token 与周窗百分比固定换算后据此加派 |
| worktree 删除前置门 | `pre-worktree-delete` / `orca.worktree` | 卡 V（运行任务保留集） | `matched` | 14.172380 | 仅凭 Ready terminal 或分支名判断空闲，然后尝试删除 worktree |

## 主动查询返回的最短候选动作

```text
[装端指纹验收]
先冻结目标版本并锁定精确缓存目录，再将 CRLF 规范化为 LF 比较 SHA-256；原始哈希与跨版本通配均不能定案。

[Token 燃烧测量决策]
用 `ccusage codex daily --json --offline` 的当日 `totalTokens` 增量与组成作相对燃烧主信号；`costUSD` 不是账单，Token 与周窗不得固定换算，单 Session 归因另需回执。

[worktree 删除前置门]
先以 dispatched／running 任务绑定、两仓 main 与明确保护对象组成保留集 R；其余候选仍逐个核验零未提交、零未推送和连带影响，禁止按分支名或 Ready terminal 判活。
```

## 证据解释

本记录直接证明当前仓库中的示例脚本能读取现有 A–V 卡，在三个预先给定的模拟场景中由调用者主动构造查询上下文，并由未修改的生产检索器返回预期卡。表中的“排除分支”是演示合同里预先写明的错误路径，用来说明最短动作卡怎样收窄当前决定；它不是自然任务的节时测量。

卡 B 已有既往小样回放证据；卡 J 与卡 V 在本记录中仍只完成模拟查询接线、当前交付验收与现有场景回放。本记录没有验证主动问路的自然采用率、误命中成本、独立自然样本准确率、长期召回率、Agent 实际采用、产品采用或长期依赖。
