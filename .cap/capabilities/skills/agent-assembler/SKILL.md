---
name: agent-assembler
description: 把 Agent 目标端到端装配为项目级 CAP profile、prompt、Skills、显式能力闭包和分层验证证据。创建、重装、审查或 clean cutover Agent 时使用；不代办普通业务任务。
---

# agent-assembler

## 流程
1. **锁定目标合同。** 写明稳定 id、单一目标、非目标、正反触发、输入、输出、允许和禁止的能力、人工决定点、回滚边界与可观察验收。事实可调查时不要询问负责人。
2. **恢复基线。** 读取当前 manifest、profile、prompt、能力源、调用方和派生状态。区分当前权威、历史配置、候选资产与实际运行证据；旧装配只作输入，不自动继承。
3. **处理人工裁决。** 只有多个方案会实质改变产品边界、长期依赖、风险、外部副作用或不可逆成本时，给出 2–5 个互斥选项、影响和推荐。未经确认，不把推荐写成负责人决定。
4. **按目标选择能力。** 对每项候选说明它补足的行为、触发边界、来源、风险和证明；不能指向目标或验收的能力不接入。MCP、Hook、Plugin 默认空。外部事实或资产使用 `capability-lifecycle`。
5. **分配持久层。** 常驻不变量使用 `agent-prompt-design`；条件多步骤能力使用 `agent-skill-design`；当前任务状态留在 WorkItem；需要长期审计的新增 profile 或行为变化使用 `spec-change-pack`。
6. **实施完整装配。** 修改 manifest、叶子 profile、prompt、Skill 和所有当前调用方；执行 clean cutover，删除旧 id、旧引用和失效说明。源声明改变后再生成 lock、binding、render 或 runtime generation，不把派生状态当源头。
7. **验证闭包。** 使用 `capability-profile-closure` 检查 Skill 元数据、唯一来源、allow/deny/override、未使用资产、无 ambient 继承、lock、binding 和各目标客户端 render。
8. **验证行为。** 对可观察行为变化使用 `agent-behavior-evaluation`：先记录可得基线，覆盖应触发与不应触发场景，观察真实终态。没有客户端 trial 时，生效态保持 `unknown`。
9. **自足交付。** 报告目标合同、能力选择、人工决定、源文件、派生文件、准确检查结果、行为证据、回滚方式和剩余未知；不把声明态或配置态扩写为行为改善。

## `grilling` 同意门
`grilling` 是可用能力，不是默认流程。只有负责人直接要求 grilling／盘问／压力测试，或明确接受此前建议后才调用。复杂、模糊、高风险或出现关键词都不构成同意；没有同意时走普通目标澄清，只在新的不确定性会实质改变结果时最多建议一次。

## 完成条件
只有当目标 Agent 的 manifest、profile、prompt、能力源和调用方形成唯一、项目内、可回滚的闭包，Skill 标准验证和选定客户端配置验证通过，人工决定有明确归属，且行为结论不超过实际观察，装配才算完成。
