# 当前权威总图

> 状态：本次 Session 已确认，现为当前权威。  
> 权威地位：本文件是 `authority/` 的权威根与瘦路由索引；领域正文按下表按需读取。
> 来源：只使用本次 Session 中负责人的表达和确认；旧仓不具有默认权威。  
> 索引化来源：负责人批准的 [关联 #44（规则只加不减的收敛实施）决定回执](https://github.com/Eridanus117/agent-control/issues/44#issuecomment-5258111511)，依据 [关联 #66（权威与 Skill 资产的多视角攻防审计）L4-1 四臂实验](https://github.com/Eridanus117/agent-control/issues/66#issuecomment-5257944842)；本次只搬迁结构，不改变语义。

## 权威规则

1. 本次 Session 中经过负责人确认的内容，以及这些内容在本目录中的固化版本，是当前基准。
2. 旧仓、旧 Issue、旧文档和旧实现只能作为待核验材料，不能反向定义当前需求、架构或方法。
3. 实验结果只能作为证据，不能因为已经做过就自动升级为产品决定。
4. Agent 的推论、候选方案和未确认扩展不能写成已确认事实。
5. 后续改变当前权威时，需要明确指出被替代的内容及新结论，不能静默漂移。

## 使用方式

先按 [`README.md`](../README.md) 的“开始工作”判断本次是否带有明确 Issue。有明确 Issue 时，先从远端恢复当前合同、原生关系与有效决定，再按合同主题、领域标签和显式链接读取下表最窄的一组权威；没有明确 Issue 时，沿 README 规定的恢复指针或经营总账路径进入。冲突时以当前权威及负责人最新明确指令为先。跨域任务读取每个命中域的权威，并优先读取会改变授权、风险或产品边界的文件。Issue 合同已经自足、且领域路由保持空集时，合同恢复停在远端合同；执行阶段再按入口与 Skill 触发补读。方案、实验与历史记录保持证据角色；权威变更候选进入负责人审阅面后再形成当前结论。

机器级持久实现语言与常驻 Agent 系统规则的唯一版本化正文见 [`entrypoints/agent-system.md`](../entrypoints/agent-system.md)；本总图不复制。

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
