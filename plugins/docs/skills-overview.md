<!-- 生成产物：node plugins/scripts/skills-overview.ts --write。不要手改；
     三句话的来源是 plugins/tests/workflow-routing.json 的 skillOverview。 -->

# Skill 选型面

这是给人看的入口：每个 Skill 替你做什么、什么时候会用到、你怎么看出它在起作用，
以及它在不同加载层和维护面上的实测体积。`SKILL.md` 是给 Agent 执行的行为合同，优先保证触发、硬门、分支和退出完整，不是按顺序阅读的教程；只有维护或审查行为时才需要下钻。

当前 7 个 Skill：L1 descriptions 4,189 字节；L2 主合同 59,706 字节；L3 按需 references 167,608 字节；递归维护面合计 227,314 字节。

L1 受每项 1000 UTF-8 字节可见性门约束；L2 只在选择 Skill 后加载；L3 只在正文明确路由后按需加载。三者不是同一个运行上下文预算。维护面递归计量全部可执行 Markdown，但不设置会诱导搬运文字的字节上限。

| Skill | 版本 | L1 描述 | L2 主合同 | L3 引用 | 维护面占比 | 上次复核 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| [adaptive-problem-solving](#adaptive-problem-solving) | 0.2.12 | 703 B | 8.6 KB | 123.4 KB | 59.5% | 2026-08-15 |
| [orchestrated-collaboration](#orchestrated-collaboration) | 0.2.7 | 876 B | 21.3 KB | 28.9 KB | 22.6% | 2026-08-15 |
| [self-improvement](#self-improvement) | 0.1.7 | 673 B | 8.8 KB | 7.2 KB | 7.2% | 2026-08-15 |
| [resource-observability](#resource-observability) | 0.2.4 | 608 B | 5.6 KB | 4.1 KB | 4.4% | 2026-08-15 |
| [knowledge-maintenance](#knowledge-maintenance) | 0.1.3 | 644 B | 6.3 KB | 0.0 KB | 2.9% | 2026-08-15 |
| [grilling](#grilling) | 0.1.2 | 351 B | 3.9 KB | 0.0 KB | 1.8% | 2026-08-15 |
| [skill-maintenance](#skill-maintenance) | 0.1.0 | 334 B | 3.8 KB | 0.0 KB | 1.7% | 2026-08-16 |

## adaptive-problem-solving

**它替你做什么** 问题求解治理：选方法、控成本、该退出就退出，别在一条路上耗死。

**什么时候用** 第一次实质路径选择、进展停滞、范围明显扩大或要交接验收时。

**你怎么知道它在起作用** 方向变了会明确说出来；没变就直接继续，不额外汇报。

**什么会让它失效** 方法登记面的证据等级分布与登记面 README 声明不符；或三端 description 可见预算的实测基线（2026-08-11 测得 1000 UTF-8 字节）被新的实测推翻。

所属 Plugin `adaptive-problem-solving` `0.2.12`｜L1 703 B｜L2 8.6 KB｜L3 123.4 KB｜递归维护面 132.0 KB（占总维护面 59.5%）｜Agent 行为合同（维护／审查时读取）[`plugins/adaptive-problem-solving/skills/adaptive-problem-solving/SKILL.md`](../adaptive-problem-solving/skills/adaptive-problem-solving/SKILL.md)

## orchestrated-collaboration

**它替你做什么** 多 Agent、多 Session 时的写入所有权、派发合同与独立验收。

**什么时候用** 已授权的多席协作或共享写入碰撞。单 Session 不触发。

**你怎么知道它在起作用** Issue 上出现类型化派发合同，以及与实施者不同的独立验收回执。

**什么会让它失效** 所选协调后端（当前 orca orchestration）的 Run／Task／Dispatch 语义或标准释放回执格式变化；或其唯一原则源 agent-control/authority/05-resource-operations.md 的资源投入原则变化，使 R1–R6 派发门失去依据。

所属 Plugin `orchestrated-collaboration` `0.2.7`｜L1 876 B｜L2 21.3 KB｜L3 28.9 KB｜递归维护面 50.2 KB（占总维护面 22.6%）｜Agent 行为合同（维护／审查时读取）[`plugins/orchestrated-collaboration/skills/orchestrated-collaboration/SKILL.md`](../orchestrated-collaboration/skills/orchestrated-collaboration/SKILL.md)

## self-improvement

**它替你做什么** 把一次纠正变成系统改进，并判断该改入口、改 Skill 还是只记任务。

**什么时候用** 你指出漂移、误解，或同类错误复发时。一次性小错不触发。

**你怎么知道它在起作用** 纠正落到某个持久载体，而不只是当次口头改了。

**什么会让它失效** 入口、Skill、任务记录三个改进承载面之一消失或职责变更，使路由判据指向不存在的去向。

所属 Plugin `self-improvement` `0.1.7`｜L1 673 B｜L2 8.8 KB｜L3 7.2 KB｜递归维护面 16.0 KB（占总维护面 7.2%）｜Agent 行为合同（维护／审查时读取）[`plugins/self-improvement/skills/self-improvement/SKILL.md`](../self-improvement/skills/self-improvement/SKILL.md)

## resource-observability

**它替你做什么** 分开看两件事：账户还剩多少额度何时恢复，和这次工作实际花了多少。

**什么时候用** 准备扩大并发、资源接近耗尽，或你问额度时。

**你怎么知道它在起作用** 给出带时间戳的读数；取不到就明说未知，不猜。

**什么会让它失效** orca account list --json 的返回结构变化：顶层 ok、result.rateLimits.claude／codex 的 status 与 updatedAt，或 usedPercent／windowMinutes／resetsAt／rateLimitResetCredits 这些窗口字段不再按 Skill 正文描述提供。

所属 Plugin `resource-observability` `0.2.4`｜L1 608 B｜L2 5.6 KB｜L3 4.1 KB｜递归维护面 9.7 KB（占总维护面 4.4%）｜Agent 行为合同（维护／审查时读取）[`plugins/resource-observability/skills/resource-observability/SKILL.md`](../resource-observability/skills/resource-observability/SKILL.md)

## knowledge-maintenance

**它替你做什么** 知识准入：价值门、可信门、失效条件与下次最少复核步骤。

**什么时候用** 多来源调研、可重复实验，或结论会影响权威与重要决定时。

**你怎么知道它在起作用** 写下的知识带失效条件和下次复核步骤，做不到复核就退出当前知识。

**什么会让它失效** agent-control/authority/01-knowledge.md 的两道准入门或可信门八项条件发生变化。

所属 Plugin `knowledge-maintenance` `0.1.3`｜L1 644 B｜L2 6.3 KB｜L3 0.0 KB｜递归维护面 6.3 KB（占总维护面 2.9%）｜Agent 行为合同（维护／审查时读取）[`plugins/knowledge-maintenance/skills/knowledge-maintenance/SKILL.md`](../knowledge-maintenance/skills/knowledge-maintenance/SKILL.md)

## grilling

**它替你做什么** 用结构化追问压力测试一个计划或决定，把没想清楚的地方逼出来。

**什么时候用** 你直接要求，或明确接受建议时。它不会因为任务复杂就自动开始。

**你怎么知道它在起作用** 你会被连续追问，且随时可以喊停或换普通路径。

**什么会让它失效** 明示同意门被取消，或运行端改为按关键词自动进入长期盘问。

所属 Plugin `grilling` `0.1.2`｜L1 351 B｜L2 3.9 KB｜L3 0.0 KB｜递归维护面 3.9 KB（占总维护面 1.8%）｜Agent 行为合同（维护／审查时读取）[`plugins/grilling/skills/grilling/SKILL.md`](../grilling/skills/grilling/SKILL.md)

## skill-maintenance

**它替你做什么** 创建、审计、拆分、升级或退役 Skill 时，把行为合同、调用者、版本、预算和验证一次维护完整。

**什么时候用** 已经确定要维护某个 Skill 时；尚未决定行为该放哪里时不用。

**你怎么知道它在起作用** 改动前有行为判据，改动后没有旧调用者，版本、生成物、预算、验证和独立审查能相互对上。

**什么会让它失效** Skill 的发现入口、版本声明、复杂度预算、生成物或发布／退役工具发生变化，使正文盘点面和 clean cutover 步骤不再覆盖真实运行路径。

所属 Plugin `skill-maintenance` `0.1.0`｜L1 334 B｜L2 3.8 KB｜L3 0.0 KB｜递归维护面 3.8 KB（占总维护面 1.7%）｜Agent 行为合同（维护／审查时读取）[`plugins/skill-maintenance/skills/skill-maintenance/SKILL.md`](../skill-maintenance/skills/skill-maintenance/SKILL.md)
