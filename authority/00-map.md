# 当前权威总图

> 状态：2026-08-15 clean-slate 迁入的产品政策快照；正文按公开 Issue 逐项复核。
> 权威地位：本文件是 `authority/` 的公共路由索引；它不保存当前工作，也不自行产生实施授权。
> 历史来源：私有 `Eridanus117/agent-control` Issue／评论只作可选证据；当前公共规则必须在本仓自足表达。
> 当前迁移裁决：[Issue #58](https://github.com/zaurakworks/agent-system/issues/58)。

## 权威规则

1. 本目录只保存稳定产品政策，不保存当前任务、运行态、ownership、lease 或下一步。
2. 带 `迁移索引/待分诊` 标签的 Issue、私有旧仓、旧文档和旧实现只能作为待核验材料，不能反向定义当前需求、架构、方法或授权。
3. 实验结果只能作为证据，不能因为已经做过就自动升级为产品决定。
4. Agent 的推论、候选方案和未确认扩展不能写成已确认事实。
5. 后续改变产品政策时，需要公开、自足地指出被替代内容和新结论，不能要求读者访问私有评论才能理解当前规则。

## 使用方式

先按 [`README.md`](../README.md) 的“开始工作”判断本次是否有负责人明确激活的公开 Issue。只有公开、自足且未被迁移标签降级的当前合同才能进入实施；否则保持分诊、只读核验或自由对话。再按合同主题和显式链接读取下表最窄的一组政策。冲突时以负责人最新明确指令和更高层权限边界为先。方案、实验与历史记录保持证据角色；政策变更候选进入公开审阅面后再形成当前结论。

项目级 Agent 规则的唯一版本化正文见 [`entrypoints/agent-system.md`](../entrypoints/agent-system.md)；本总图不复制。

## 文件路由索引

| 权威文件 | 去哪找什么 |
| --- | --- |
| [`00-map.md`](./00-map.md) | 当前权威根、按需读取路由与最短权威规则 |
| [`01-knowledge.md`](./01-knowledge.md) | 知识定义、公共与私域边界、价值门、可信门、复用、维护与检索 |
| [`02-long-horizon-work.md`](./02-long-horizon-work.md) | Agent 系统总目标、领域关系、长程委托的问题、期望结果、边界与渐进建设原则 |
| [`03-thinking-methods.md`](./03-thinking-methods.md) | 思考模式、元方法、问题求解治理、APS、方法登记面、具体方法与 Skill 的职责边界 |
| [`04-collaboration.md`](./04-collaboration.md) | 多 Agent／多 Session 协作产品模型、GitHub／Orca、运行面、产品事实、依赖策略与共享单点清单 |
| [`05-resource-operations.md`](./05-resource-operations.md) | 资源与运营的横向定位、数据可信度、观察边界与 ROI 原则 |
| [`06-first-mvp-direction.md`](./06-first-mvp-direction.md) | 首个 MVP“最小防漂移闭环”的目标、选择理由、保留目标与悬置项 |
| [`07-mvp-validation-strategy.md`](./07-mvp-validation-strategy.md) | MVP 早期验证方式、观察信号、成本上限、证据上限与允许结论 |
| [`08-mvp-implementation-direction.md`](./08-mvp-implementation-direction.md) | MVP 实施历史与当前承载语义、实施授权、Windows 入口、权限、窄行为资产、守恒律与受限自清理 |
| [`09-rd-memory.md`](./09-rd-memory.md) | 研发记忆的原始记录层、可读记录层及其与权威、知识和行为资产的边界 |
| [`10-operating-ledger.md`](./10-operating-ledger.md) | 经营总账准入、节点、执行／诉求／证据状态、Project 观察面与维护行为 |
| [`11-execution-state.md`](./11-execution-state.md) | 当前执行的最小充分装配、重新判断条件、外部 WorkItem 状态边界与显式激活 |
