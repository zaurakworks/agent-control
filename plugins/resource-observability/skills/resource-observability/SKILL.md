---
name: resource-observability
description: >-
  当用户查询 Codex／Claude 账户额度、重置时间、Codex 重置券、单 Session Token，或高成本／多 Agent 工作要决定启动、并行、降级、延后或停止时，按需读取 Orca 账户快照与固定 ccusage 回执，区分状态、来源、可信度和未知值。不要用于低风险任务、轮询、自动调度／消费权益、账单推断或长期保存快照。Use for account capacity, reset times, credits, session tokens, or consequential resource decisions. Skip routine work, polling, scheduling, automatic credit use, billing inference, and durable snapshot storage.
---

# 资源观测

目标是在真正需要资源决定时，低成本看见两类不同信息：账户还有多少可用窗口、何时恢复；某个 Session 已经实际消耗多少 Token。不要因为已经装了某个工具，就把另一类需求删除。

## 一、先确认需要哪一层

- **账户层**：任务开始、准备扩大并发、资源接近耗尽或用户询问额度／重置券时使用；
- **会话层**：用户要求单 Session 回执，或高成本／多 Agent 工作已经决定需要记录实际消耗时使用；
- **两层一起**：需要比较“现在还有多少容量”与“这项工作实际花了多少”时使用。

普通低风险任务不因本 Skill 可用而自动增加观测。不要为了消耗额度创建 Session。

## 二、账户层：读取 Orca 当前快照

运行：

```powershell
orca account list --json
```

只读取返回文档中的 `result.rateLimits.claude` 与 `result.rateLimits.codex`。至少检查顶层 `ok == true`，并逐个 Provider 检查 `status`、`updatedAt` 和实际存在的窗口。窗口字段只接受：

- `usedPercent`：0 到 100；
- `windowMinutes`：正整数或 `null`；
- `resetsAt`：Unix 毫秒时间戳或 `null`；
- Codex `rateLimitResetCredits.availableCount` 与 `nextExpiresAt`；
- Claude `usageMetadata.source`，只用于说明来源，不输出凭据位置。

把结果整理为负责人可读的结构化摘要，至少包含 Provider、已用百分比、由 `100 - 已用` 得到并明确标注为派生值的剩余比例、重置时刻、采集时刻、来源和状态。Codex 另列可用重置券数量与最近过期时刻。不存在的窗口保持未知，不补成 0。

不得输出或转述原始 JSON 中的邮箱、账户 ID、组织 ID、运行时 ID、凭据来源路径、其它 Provider、原始错误正文或整份上游响应。`orca` 缺失、运行时不可达、顶层失败、Provider 状态不是 `ok`、字段越界或协议无法识别时，将对应账户层标为不可用并说明最小错误类别；不读取凭据、不改走内部 HTTP、不沿用旧快照。

Claude Code 的 `/usage` 可以在人工复核或接口漂移时做目视交叉检查，不是每次调用的前置步骤。Codex App Server 生成协议可以在字段漂移时复核，也不是日常重复调研步骤。

## 三、会话层：读取固定 ccusage 回执

从本文件所在目录向上两级取得 `<plugin-root>`，入口是：

```powershell
node "<plugin-root>\scripts\resource-observability.ts" session --provider codex --id "<session-id-or-uuid>" --json
node "<plugin-root>\scripts\resource-observability.ts" session --provider claude --id "<session-id>" --summary
```

默认上游命令为 `ccusage`，固定要求版本 `20.0.19`，每次调用都带 `--json --offline --no-cost`。在测试或非标准安装中可以明确提供受控命令路径：`--ccusage-command "<absolute-path>"`；不得把不可信 Session ID 或命令拼接进 shell。

`ccusage` 会扫描本地 Codex／Claude Session 使用记录以聚合 Token。由 Node 直接运行的 TypeScript 薄门面只承担命令边界、协议校验、脱敏和摘要，不读取账户额度，也不定义完整资源产品。它不输出原始正文、目录、文件路径、上游 stderr、凭据或未经裁剪的响应。

JSON 标准输出恰好一个 `resource-observability.session/v1` 回执。未知字段保持 `null`，不会伪造 `0`。退出码为 `0`（成功）、`2`（用法／依赖不可用／未找到或歧义）和 `1`（上游、协议、超时或安全限制失败）。遇到未知协议、版本不符或缺失依赖时停止并报告，不下载、不安装、不缓存，也不改读其他来源补齐。

## 四、形成资源决定上下文

只陈述本次决定真正需要的内容：

1. 账户窗口的已用、派生剩余、恢复时点和读数时间；
2. 即将到期但尚未自动消费的 Codex 重置券；
3. 已知单 Session 实际消耗；
4. 数据来源、年龄、失败和仍未知内容；
5. 结合当前任务价值、预计成本和并发边界，比较继续、降低规格、延后或停止。

本 Skill 不设置通用阈值，不自动启动任务、扩大并发、消费重置券或停止 Agent。需要改变已确认计划、产品边界或负责人权益时，返回对应问题求解或负责人决定。

当一个本来就值得推进、已有授权且资源信息可能改变投入选择的高成本／多 Agent 自然事件出现时，完整读取[自然资源决定闭环](./references/natural-decision-loop.md)，按它登记无资源数据时的原决定、取得同窗成对账户快照、为每个实际参与 Session 生成回执，并在决定后记录交付结果、返工、验收容量、负责人打扰和总记录成本。不要为取得样本制造任务；没有自然决策点时直接退出这条路径。

动态额度和重置时间只属于带时间的运行状态。除非当前任务明确需要保存实验快照，否则不要把它们写进权威或长期知识。
