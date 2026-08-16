# K21：可浏览思考工具箱

> **定位**：本页是 B1 思考法／元认知范围的单一当前知识载体，服务负责人学习、浏览、比较与迁移；它不属于 `authority/`，也不是 Agent 的触发器、执行清单或第二个方法控制器。
>
> **当前对象**：`agent-control` 中的 Agent 系统决策，以及 `adaptive-problem-solving`（APS）`0.2.11` 的 30 张方法卡（M0 18 张、M1 12 张）。
>
> **整合来源**：[关联 #161（建立可浏览思考工具箱）](https://github.com/Eridanus117/agent-control/pull/161)与[关联 #163（新增可浏览思考工具箱）](https://github.com/Eridanus117/agent-control/pull/163)；本页完成去重和价值门复核后置换两份分散草稿。
>
> **最近核验**：2026-08-16；对照当前 APS 方法登记面的 README、类型索引、30 张卡与符合性检查，证据分布未变。
>
> **证据上限**：来源支持概念原义、部分人类或领域证据，以及本页与现有 APS 卡的关系；本仓例子只说明怎样迁移概念，尚无证据证明这些方法必然改善当前 Agent 系统。

## 先选阅读入口

如果你是负责人或普通读者，不要从 `SKILL.md` 开始顺序通读。`SKILL.md`、类型索引和方法卡是给 Agent 按任务选择性加载的可执行合同，优先保证触发、硬门、分支、退出和责任边界完整，不按教程组织。

| 你现在想做什么 | 从哪里开始 |
| --- | --- |
| 快速知道 APS 替你做什么、什么时候会用到 | [给负责人的 Skill 选型面](https://github.com/zaurakworks/agent-plugins/blob/main/docs/skills-overview.md#adaptive-problem-solving) |
| 学习、浏览和比较思考概念 | 继续读本页 |
| 维护或审查 Agent 实际怎样选择和执行方法 | [APS 行为合同](https://github.com/zaurakworks/agent-plugins/blob/main/plugins/adaptive-problem-solving/skills/adaptive-problem-solving/SKILL.md) → [方法类型索引](https://github.com/zaurakworks/agent-plugins/blob/main/plugins/adaptive-problem-solving/skills/adaptive-problem-solving/references/method-registry/INDEX.md) → 命中的单张方法卡 |

## 怎么用这页

先从一个真实问题进入，通常只挑一个主角度；若低成本、可回退的普通行动能更快给出反馈，就直接行动。概念页回答“这个角度是什么意思、何时值得想”，[APS 方法登记面](https://github.com/zaurakworks/agent-plugins/tree/main/plugins/adaptive-problem-solving/skills/adaptive-problem-solving/references/method-registry)回答 Agent “何时触发、怎样执行、成本多大、何时停止、证据到哪一级”。

概念被收录或建议登记都不产生同意、授权、写入所有权、产品采用或默认触发资格。需要执行时，APS 仍先判断普通路径是否足够、当前主瓶颈是什么，并遵守对应卡片的硬门与组合上限。

| 当前卡点 | 先看 | 与 APS 的总关系 |
| --- | --- | --- |
| 问题被现有方案或分类框住 | 1 MECE、2 苏格拉底式诘问、3 第一性原理 | 已被问题建模、问询与结构化发散覆盖 |
| 想找失败、反方或隐藏前提 | 4 逆向、6 奥卡姆剃刀、7 变更前恢复原意、13 钢人化 | 7 是净增卡建议，其余并入现卡 |
| 要在多个方向与风险间取舍 | 5 二阶思维、8 机会成本、9 期望值与概率—影响分离 | 5 是净增卡建议，8、9 并入 ROI／风险卡 |
| 需要诊断、归因或预测 | 10 因果反事实、11 基率、12 参考类预测 | 10、12 是净增卡建议，11 是概率底座 |
| 要检查指标、迁移和多 Agent 行为 | 14 Goodhart 定律、15 类比迁移、16 激励与委托—代理视角 | 留在学习面，执行时组合现卡 |

## 价值门

本页只保留同时满足四项的概念：能改变一类真实决定；有清楚的适用与禁用边界；与 APS 现有卡的关系可准确定位；预计复用价值高于学习与维护成本。古老、流行、被名人推荐或已经写进一份草稿，都不提高选择资格。

两份草稿合并后保留 16 项，未取并集：

- **贝叶斯更新**并入 `analysis-of-competing-hypotheses` 与 `indicators-signposts` 的证据更新纪律；当前本仓很少有足以支撑定量先验和似然的数据，单列容易制造伪精确。
- **可证伪性**并入 `aps-adversarial-falsification`、`preregistered-experiment-card` 与 `aps-minimum-experiment`；它是跨方法的主张质量要求，不再复制成近义条目。
- **地图不是领土**并入 `quality-of-information-check`、`aps-problem-modeling`、`aps-execution-configuration-check` 及本仓既有观察面知识；保留提醒语不值得再维护一份方法正文。
- **均值回归**暂留在来源材料：它是有用的统计护栏，但当前自然复用频次低、对同总体与抽样机制的要求高，误用成本高于独立条目的预计价值。

## 精选 16 项

### 1. MECE：互斥且穷尽的切分

- **是什么**：在同一层把对象切成尽量互不重叠、合起来足以覆盖当前范围的部分；它是分类自检，不是真理保证。
- **最有用**：界定范围、切任务、比较候选，或检查重复计数与漏项时。
- **别用**：对象天然多归属、因果耦合比分类更重要，或为追求形式整齐会制造无价值类别时。
- **本仓真实例子**：整合本页时，把候选分为“保留独立条目／并入既有 APS 卡或知识护栏／暂不收录”，同时允许基率与参考类预测保持前后依赖，避免把现实硬说成绝对互斥。
- **与 APS 的关系**：**已覆盖／并入** `aps-problem-modeling` 与 `structured-brainstorming`；MECE 只作为两卡的分类质量检查，不建议新增卡。

### 2. 苏格拉底式诘问：沿主张追问定义、依据与矛盾

- **是什么**：围绕定义、依据、反例、后果和翻转条件连续追问，使隐含前提显形。
- **最有用**：关键术语含混、论证跳步，或各方看似同意却使用不同定义时。
- **别用**：事实可由 Agent 低成本查明、下一步已明确且低风险，或对人进行高强度盘问却尚未取得相应同意时。
- **本仓真实例子**：评估四张净增建议时，依次追问“哪类真实决定会因此改变、现有 30 张卡为何不够、什么自然观察会撤回建议”，把“概念有趣”和“需要执行卡”分开。
- **与 APS 的关系**：**已覆盖／并入** `aps-alignment-questioning`；若升级为决定树式压力测试，仍须路由 `grilling-decision-tree` 并保留明示同意门。

### 3. 第一性原理：从目标、事实与硬约束重建

- **是什么**：暂时拿掉继承做法和表面类比，从目标、已证事实、必要因果与硬约束重新推导方案。
- **最有用**：历史实现或流行框架已经悄悄替代真实目标，只剩在旧方案参数上微调时。
- **别用**：成熟规则已有充分验证、领域依赖大量经验，或所谓“第一原理”只是未经核验的个人断言时。
- **本仓真实例子**：本任务的目标是形成一个可检索、维护税可控的负责人学习资产，而不是完整保留两份 Draft PR 或追求最多条目；因此可以合并、降级和舍弃原材料。
- **与 APS 的关系**：**已覆盖／并入** `aps-problem-modeling`、`key-assumptions-check` 与 `aps-minimum-experiment` 的组合边界，不建议新增卡。

### 4. 逆向思维：从失败或反目标倒推

- **是什么**：先问怎样会得到相反结果或走向失败，再反推必须避免、缓解或验证的路径。
- **最有用**：正向成功路径太熟、风险容易被共识遮住，或需要快速构造失败门与停止门时。
- **别用**：对象尚未成形、失败代价很低且反馈很快，或逆向只产生灾难故事而没有可观察路径时。
- **本仓真实例子**：要让 B1 失去价值，最直接的做法是同时保留两份重叠工具箱、继续追加术语、不给禁用边界与 APS 关系；本次交付据此设定“单一资产＋16 项上限＋逐项五字段”。
- **与 APS 的关系**：**已覆盖／并入** `premortem`、`what-if-analysis`、`high-impact-low-probability` 与 `aps-adversarial-falsification`，不建议新增卡。

### 5. 二阶思维与反馈回路：追问动作之后的下一轮行为

- **是什么**：在直接结果之后再追一至两步参与者反应、延迟、正负反馈、维护税与能力回退。
- **最有用**：修改规则、指标、自动化、权限或协作机制，直接收益明显但间接行为可能反噬时。
- **别用**：行动低风险、容易回退且真实反馈更便宜，或推演已变成没有停止条件的三阶四阶故事时。
- **本仓真实例子**：新增常驻触发可能先减少漏用，随后增加入口体积、判断税和误触发，并进一步诱导更多规则进入入口；这正是守恒律需要约束的反馈链。
- **与 APS 的关系**：**净增卡建议** `second-order-effects-map`，主类型 P5、次类型 P4；现有 `alternative-futures`、`indicators-signposts` 与 `aps-roi-options` 分别覆盖未来、信号和取舍，尚无以“一阶结果／二阶行为与反馈／护栏／观察信号”为独立输出的低成本卡。

### 6. 奥卡姆剃刀：解释力相当时少加假设

- **是什么**：多个解释同样覆盖事实时，优先验证额外实体、假设或机制更少者；简短本身不证明正确。
- **最有用**：诊断中有多个都能解释现象的模型，需要决定先验证哪个时。
- **别用**：较简单解释遗漏反例、权限或状态，或复杂度来自真实机制与不同风险边界时。
- **本仓真实例子**：现有 APS 30 张卡加一个负责人学习工具箱已经覆盖“执行选择＋概念浏览”，就不为结构好看再建方法平台或第二控制器。
- **与 APS 的关系**：**已覆盖／并入** `analysis-of-competing-hypotheses` 的假设比较与 `aps-bounded-research` 的最小翻转事实，作为排序启发式即可。

### 7. 变更前恢复原意（Chesterton 栅栏）

- **是什么**：删除或改写既有规则、流程、护栏前，先恢复它解决的原问题、依赖与当前是否仍成立。
- **最有用**：清理旧规则、压缩入口、重构兼容逻辑、移除权限或恢复机制，错误删除代价高于短暂调查时。
- **别用**：明显有害的状态需要立即止损、来源已证明只是事故或死代码，或低风险可逆探针能更快取得反馈时。
- **本仓真实例子**：不能只因远端写入前的恢复快照步骤繁琐就移除它；先确认它是否仍承担跨 Session 恢复与防止旧草稿覆盖新状态的职责，再决定保留、置换或移除实现。
- **与 APS 的关系**：**净增卡建议** `change-rationale-recovery`，主类型 P1／P4；`key-assumptions-check`、`quality-of-information-check` 与 `aps-problem-modeling` 都未专门约束“改既有资产前先恢复原目的与依赖”。

### 8. 机会成本：选择占用的最好替代收益

- **是什么**：一项选择的成本还包括同一资源因此放弃的最佳可执行替代用途。
- **最有用**：多个都有价值的方向争抢负责人注意力、验收容量、Agent 波次或维护预算时。
- **别用**：候选并不互斥、替代项不可执行，或为显得精确而虚构收益数字时。
- **本仓真实例子**：继续整理第 50 个心智模型的成本，还包括少做一次真实任务中的自然复用观察；因此本页止于 16 项而不追求百科全书。
- **与 APS 的关系**：**已覆盖／并入** `aps-roi-options` 的总周期、有用吞吐、负责人注意力与机会成本比较，不建议新增卡。

### 9. 期望值与概率—影响分离

- **是什么**：先把发生可能性和发生后的影响分开估计，再结合暴露、缓解成本、不可逆性与风险偏好作决定。
- **最有用**：风险不对称、小概率高损失事件，或多个赌注需要相称缓解时。
- **别用**：安全或法律底线不可用平均收益抵消、概率没有依据，或尾部损失会被一个平均数掩盖时。
- **本仓真实例子**：GitHub 安全引用误触的概率可以很低，但远端关系被意外改变的影响足够大，因此仍值得保留窄而明确的引用硬门。
- **与 APS 的关系**：**已覆盖／并入** `high-impact-low-probability` 与 `aps-roi-options`；前者已经要求分开概率依据、影响路径和缓解成本。

### 10. 因果图与反事实：区分相关、干预与归因

- **是什么**：显式写出变量、因果箭头、混杂和可干预点，再问“若只改变候选原因，结果是否仍会不同”。
- **最有用**：相关容易被误当效果、故障有多个共同原因，或需要决定实验应改变哪一环时。
- **别用**：无法说明哪些机制保持不变、多个机制同时变化，或只有观察相关性却要给出强因果结论时。
- **本仓真实例子**：安装新 Skill 后输出质量上升，仍可能被模型版本、任务难度、负责人介入与同时发生的入口修改混杂；没有对照就只能保留“因果仍未知”。
- **与 APS 的关系**：**净增卡建议** `causal-counterfactual-map`，主类型 P3／P6；现有 `comparative-experiment`、`paired-observation` 与 `aps-minimum-experiment` 管比较和采样，尚缺“变量图／反事实／不变机制／混杂／识别上限”的建模入口。

### 11. 基率：先看同类事件通常怎样

- **是什么**：判断个案前先找相关总体或同类样本的先验频率，再用个案的区别证据更新。
- **最有用**：估计故障率、成功率或返工概率，而且有可比历史样本时。
- **别用**：参考总体选错、环境结构已变，或个案已有强而可靠的区别证据时。
- **本仓真实例子**：看到一次三端安装成功，不能推断以后都可靠；应先看既往批次中跨版本通配、旧缓存和漏装出现的频率，再按本批是否锁定目标版本修正判断。
- **与 APS 的关系**：**部分覆盖／并入** `quality-of-information-check`、`comparative-experiment` 与 `outside-in-thinking`；作为概率素养保留，真正可执行的预测动作交给下一项参考类预测。

### 12. 参考类预测：用同类实际分布校准当前计划

- **是什么**：选择一组结构相似且已经完成的案例，读取其实际结果分布，再按当前个案有证据的差异调整预测。
- **最有用**：估计交付周期、成本、返工、成功率或采用率，而内部计划容易受乐观与“本次特殊”影响时。
- **别用**：参考类不可辩护、样本口径不一致，或环境变化已使旧分布失效时；此时应保留未知。
- **本仓真实例子**：估计一项“知识资产＋Draft PR”的周期，不只拆自己的理想步骤，还应看最近同仓知识 PR 的实际调查、写作、验证和发布周期，并说明本次逐项 APS 去重为何需要调整。
- **与 APS 的关系**：**净增卡建议** `reference-class-forecasting`，主类型 P3、次类型 P5；现有 `outside-in-thinking`、`alternative-futures` 与 `comparative-experiment` 都没有“定义参考类／取结果分布／定位当前个案／证据化调整”的预测合同。

### 13. 钢人化：先重建最强可信反方

- **是什么**：回应一个观点前，先把其主张、证据和适用边界重述成对方会认可的最强版本。
- **最有用**：产品取舍、架构争议和资源配置中，反方容易被简化成稻草人时。
- **别用**：替对方发明其并不接受的立场、给无证据主张制造假平衡，或借更强版本绕过原问题时。
- **本仓真实例子**：工具箱方案的最强反方是“真实使用频次可能低，维护 16 项的税高于临时查找”，而不是“负责人对思考方法没有兴趣”。
- **与 APS 的关系**：**已覆盖／并入** `devils-advocacy` 的最强可信反方与 `team-a-team-b` 的独立模型比较，不建议新增近义卡。

### 14. Goodhart 定律：指标成为控制目标后会改变行为

- **是什么**：当观察指标被用来奖惩或控制时，参与者会适应，指标与真实目标原有的关系可能失效。
- **最有用**：设计利用率、通过率、Issue 数、Token 燃烧等运营指标、排行榜或自动验收时。
- **别用**：把它泛化成“所有指标都无效”而拒绝测量，或尚无控制压力和可观察适应路径时。
- **本仓真实例子**：若把方法卡数量设成进度目标，系统会倾向增加 M0 卡，而不是改善经真实任务复核的决定；因此登记面明确区分卡数与证据等级。
- **与 APS 的关系**：**已覆盖／并入** `goal-question-metric` 的代理指标风险、`quality-of-information-check` 的口径核验与 `aps-roi-options` 的父目标净贡献检查。

### 15. 类比迁移：迁移关系结构，不迁移表面

- **是什么**：把源领域中对象之间的关系映射到目标领域，并逐项检查对应关系、关键差异与失效点。
- **最有用**：缺少直接经验，但存在机制和结构可比较的系统，可借此生成新假设或验证面时。
- **别用**：只有名称或外观相似、关键激励和权限不同，或把类比直接当成证据与授权时。
- **本仓真实例子**：可以把数据库事务的“提交后回读”类比到 GitHub mutation 恢复，因为两者都区分调用回执与持久后态；但对象身份、幂等边界和权限模型仍须逐项核验。
- **与 APS 的关系**：**部分覆盖／并入** `outside-in-thinking`、`structured-brainstorming` 与 `key-assumptions-check`：先生成跨域候选，再验证映射假设；自然样本证明需要独立执行形状前不增卡。

### 16. 激励与委托—代理视角：看目标、信息与后果由谁承担

- **是什么**：从委托方与执行方的目标差异、信息差、行动成本和后果归属出发，预测行为会怎样偏离委托目标。
- **最有用**：多 Agent、负责人审批、外部服务、自动验收或长期维护安排中，报告者与结果承担者不是同一主体时。
- **别用**：没有行为与信息结构证据，却把普通差异都解释成恶意或利益冲突时。
- **本仓真实例子**：若 Worker 只因“报告完成”获得正反馈，就可能高估交付；因此 `worker_done` 只触发协调者回读远端 head、验证和交付范围，不能自动成为验收结论。
- **与 APS 的关系**：**部分覆盖／并入** `aps-parent-goal-acceptance`、`multi-perspective-adversarial-review` 与 `aps-roi-options`；当前尚无足够自然样本证明通用激励映射值得独立卡，先留在学习面。

## 四张净增卡建议

这些建议只说明现有登记面的独立缺口，不修改 APS 或 `agent-plugins`，也不代表已经获准实施。若后续形成独立合同，均应按 APS 十一组 schema 从 M0 起步，并重新检查相邻卡、组合上限、硬门与自然任务证据。

| 建议 `method_id` | 独立缺口 | 最小执行输出 | 主要禁用／退出 |
| --- | --- | --- | --- |
| `reference-class-forecasting` | 缺少用历史同类结果分布校准周期／成本／成功率的预测合同 | 参考类定义、样本分布、当前定位、调整依据、区间、失效条件 | 类不可辩护、口径不同或结构已变时退出未知 |
| `second-order-effects-map` | 缺少轻量追踪动作后的行为适应与反馈回路 | 一阶结果、二阶行为／反馈、受影响者、护栏、观察信号 | 低风险即时反馈走普通路径；默认两步停止 |
| `change-rationale-recovery` | 缺少删改既有资产前恢复原目的与依赖的专门门 | 原问题、当时约束、当前是否仍成立、连带影响、处置建议 | 紧急止损或低风险可逆探针可直接行动；不得成为维持现状的否决权 |
| `causal-counterfactual-map` | 缺少事前因果结构与事后反事实识别合同 | 变量图、实际结果、反事实、不变机制、混杂、可识别结论／未知 | 无法定义反事实或多机制同时变化时禁止强因果结论 |

## 两个承载面的分工

| 载体 | 服务对象 | 保存什么 | 不做什么 |
| --- | --- | --- | --- |
| 本工具箱 | 负责人学习、浏览、比较与迁移 | 概念解释、适用／禁用、本仓例子、与 APS 的关系、净增候选 | 不触发任务、不授权行动、不记录卡片效果等级，不把所有概念卡片化 |
| APS 方法登记面 | Agent 在真实任务中的方法选择 | 可执行卡的类型、进入门、硬门、步骤、成本、退出、证据等级和维护规则 | 不复制百科式概念正文，不因名气或本页推荐提高选择资格 |

## 来源、可信边界与复核

### 本次直接核验

- 2026-08-16 对照 APS `0.2.11` 的[方法登记面说明](https://github.com/zaurakworks/agent-plugins/blob/main/plugins/adaptive-problem-solving/skills/adaptive-problem-solving/references/method-registry/README.md)、[方法类型学索引](https://github.com/zaurakworks/agent-plugins/blob/main/plugins/adaptive-problem-solving/skills/adaptive-problem-solving/references/method-registry/INDEX.md)、30 张卡与符合性检查，确认 18 张 M0、12 张 M1，以及逐项“覆盖／并入／净增建议”关系未变。
- 本仓职责边界来自[思考模式与元方法权威](../authority/03-thinking-methods.md)，知识准入与退出边界来自[知识权威](../authority/01-knowledge.md)；本页不修改两者。
- 本仓例子来自当前知识包、近期远端合同与[关联 #136（今夜自治运行的反向反思）跟丢审计补正](https://github.com/Eridanus117/agent-control/issues/136#issuecomment-5263279476)。这些材料支持例子真实性，不单独证明方法有效。

### 概念与领域来源

- [McKinsey：Barbara Minto 对 MECE 的定义与沿革](https://www.mckinsey.com/alumni/news-and-events/global-news/alumni-news/barbara-minto-mece-i-invented-it-so-i-get-to-say-how-to-pronounce-it)、[Stanford Encyclopedia of Philosophy：Socrates](https://plato.stanford.edu/archives/spr2023/entries/socrates/)与[MIT Classics：Aristotle《Metaphysics》第一卷](https://classics.mit.edu/Aristotle/metaphysics.1.i.html)支持前三项的概念背景；概念古老不构成选择资格。
- [Oxford Academic：奥卡姆剃刀的历史与简约边界](https://academic.oup.com/brain/article/145/6/1870/6575832)说明常见拉丁格言并未见于已知 Ockham 文本，且简约不等于较短解释自动为真。
- [G. K. Chesterton《The Thing》“The Drift from Domesticity”](https://catholiclibrary.org/library/view?chunk.id=00000011&docId=%2FContemporary-EN%2FXCT.165.html)支持变更前先理解既有安排用途的原始比喻；本页把它转写为变更治理候选。
- [Federal Reserve Education：Opportunity Cost](https://www.federalreserveeducation.org/teaching-resources/economics/scarcity/opportunity-cost-module)与 [NIST SP 800-30 Rev. 1](https://csrc.nist.gov/pubs/sp/800/30/r1/final)分别支持机会成本、可能性与影响分离；本页不把货币或安全风险模型直接外推为所有 Agent 决策的精确算法。
- [Tversky 与 Kahneman：Judgment under Uncertainty](https://pubmed.ncbi.nlm.nih.gov/17835457/)与[世界银行：Policy and Planning for Large Infrastructure Projects](https://documents.worldbank.org/en/publication/documents-reports/documentdetail/968761468141298118)支持基率忽略、内部视角和参考类预测的基本形状；大型基建效果量不外推到本仓。
- [UCLA：Pearl《Structural Counterfactuals》](https://escholarship.org/uc/item/6cp3673m)支持反事实需要结构模型；本页不声称只凭想象即可识别因果。
- [Reserve Bank of Australia：Goodhart 原始书目水位](https://www.rba.gov.au/publications/rdp/1990/9013/conference-volumes.html)、[Gentner：Structure-Mapping](https://onlinelibrary.wiley.com/doi/abs/10.1207/s15516709cog0702_3)、[Meadows：Leverage Points](https://donellameadows.org/archives/leverage-points-places-to-intervene-in-a-system/)与[Jensen、Meckling：Theory of the Firm](https://econpapers.repec.org/article/eeejfinec/v_3a3_3ay_3a1976_3ai_3a4_3ap_3a305-360.htm)分别支持指标目标化、关系结构迁移、反馈回路与委托—代理问题的概念边界。

外部来源只支持概念、历史原义或部分人类／领域证据；它们不证明本页对 Agent 系统的净收益。本仓例子是 2026-08-12 的迁移说明，不是效果实验。

### 失效条件

命中任一项时，相关结论停止直接复用，先做增量复核：

1. APS 方法登记面新增、删除或重写卡片，使“已覆盖／净增建议”判断变化；
2. APS 类型学、卡片 schema、证据水位或选择资格规则变化；
3. `authority/03-thinking-methods.md` 改变工具箱、控制器与登记面的职责边界；
4. 本仓真实例子的远端来源无法恢复，或后续证据推翻其依赖事实；
5. 新证据表明某条目的维护或误用成本高于它减少的返工，或外部来源被撤回、版本变化或存在实质误述。

### 下次最少复核

1. 读取本仓思考方法权威和 APS 方法登记面的 README／INDEX，比较版本、卡片清单与 M0／M1 水位；只重查新增、删除或正文变化的卡。
2. 对准备实际使用的单个概念，只重读本页禁用边界、对应 APS 卡与本仓例子来源，通常不重查全部 16 项。
3. 只搜索四个建议 ID 是否已经进入登记面；若要推进建议，再复核相邻卡与至少一个自然任务进入门，并从 M0 建卡。
4. 在自然任务中低成本记录概念是否改变问题定义、证据需求、选项排序或停止条件，以及增加的判断税；连续两个自然波次没有可见决定变化，或维护与误用成本更高时，降级或移出相应条目。

## 不能推出什么

- 16 项不是“最重要心智模型”的客观排名，也不是完整名单。
- 四张候选不是已批准的 APS 变更；本页没有修改 `agent-plugins`、已安装 Skill、Plugin 或权威。
- 本页进入公共知识入口，只说明它通过当前知识的价值门与可信门；不表示每个概念都通过 APS 的自然任务证据门。
- 任何概念都不能替代一手事实、领域专业知识、风险授权、用户同意或真实反馈。
