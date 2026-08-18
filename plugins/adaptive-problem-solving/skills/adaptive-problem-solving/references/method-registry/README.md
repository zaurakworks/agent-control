# 方法登记面

本目录是 `adaptive-problem-solving`（APS）按需读取的方法登记面，不是第二个控制器。APS 先判断普通路径是否足够、识别当前主问题类型，再从 [`INDEX.md`](./INDEX.md) 读取少量候选卡；具体 Skill、文档或工具继续负责执行，任务状态与效果样本继续留在远端任务证据中。

## 五层承载

| 层 | 唯一职责 | 当前载体 |
| --- | --- | --- |
| 权威／入口 | 领域边界、常驻短触发与硬不变量 | Agent 系统权威与入口 |
| 控制器 | 归型，比较普通路径与方法，选择、组合、降级或退出 | APS `SKILL.md` |
| 登记面 | 按类型、成本、风险、证据与硬门检索方法卡 | 本目录 |
| 可执行资产 | 执行方法 | 独立 Skill、文档、工具或卡内步骤 |
| 证据与状态 | 保存自然任务样本、失败、决定与当前事实 | Issue、知识流程与研发记忆 |

登记只说明“有哪些候选、在什么边界下可选择”，不产生新的同意、授权、写入所有权、知识有效性、产品采用或长期依赖。

## 每卡必填 schema

每张卡必须完整保留下列十一组字段；卡片只作能力级独立重写，不复制来源原文。

1. 身份与来源：`method_id`、名称、版本、维护者、来源、许可／私域级别、核验时间；
2. 目的与类型：要减少的未知／决定、主类型、可选次类型、预期效果；
3. 进入条件：可观察信号、前置证据、输入、所需工具／上下文；
4. 硬门与禁用：明示同意、授权、风险、写入所有权与不适用情形；
5. 执行定义：步骤或执行资产指针、输出与完成条件；
6. 成本画像：墙钟、Token／工具调用、协调 Agent、负责人问询与维护成本；
7. 风险与回退：主要失败方式、可逆性、失败门与恢复路径；
8. 组合关系：前序、后序、冲突方法与最多组合深度；
9. 控制规则：继续、降级、升级、换路、退出与翻转条件；
10. 有效性证据：来源等级、能力证据等级、适用环境、成功／失败样本与未知；
11. 维护：失效条件、下次最少复核、替代者与选择级别。

## 两套证据等级

来源等级回答“这项主张离来源有多远”：`本次直接验证`、`一手来源核验`、`二手转述`、`未核验推断`。能力等级回答“这张卡最多证明到哪里”：

| 等级 | 含义 | 选择资格 |
| --- | --- | --- |
| M0 实现完成 | 定义自洽、可执行、可退出；尚无足够自然任务证据 | 只供人工点名或 APS 在明确说明未验证后建议；不得成为默认触发 |
| M1 当前交付验收 | 至少一个真实任务完成并被复核 | 只可在相同边界下建议 |
| M2 样本有效 | 多个异质自然任务记录收益、失败与成本 | 只有风险低、没有额外同意门且入口已获准时，才可进入自动候选 |
| M3 产品采用 | 负责人明确接受产品角色与边界 | 可作为当前能力说明，仍按卡片触发 |
| M4 长期依赖 | 持续复用、维护、替代与回退均有证据 | 才能作长期依赖判断 |

当前首批 30 张卡中，18 张为 M0、12 张为 M1；没有 M2–M4。来源成熟、Skill 已安装或实现补丁已交付，都不等于方法在自然任务中已经有效。

## 选择与维护规则

- O0 明确执行型直接走普通路径；P1–P5 查询主索引。P6 保持补充类型，但当关键争点已可由低成本、可逆行动区分时可直接首跳；P7–P8 只查询补充索引。无法归型时先运行最小可逆探针或问一个最小问题。
- 一次先读一张主卡；只有前后依赖清楚且净收益为正时才组合，组合深度不得超过卡片与索引两者中更小的上限。
- 卡片中的同意门、授权门、风险门与写入所有权门都是硬门；索引命中、M1 或外部框架成熟均不能绕过。
- 触及卡片时只复核其失效条件、来源水位和新样本；证据不足时降级选择资格，不以“已经登记”为由保留默认地位。
- 新增校准样本至少记录介入前的阶段、主瓶颈原句、普通路径、候选类型、实际方法、是否换型、改变的决定、成本与遗漏；缺少这些水位时只能作事后解释，不据此计算漏触发率或宣称方法事前命中。
- Orrery 或其他私域种子到位后只按来源、许可与修正流程增量修订；私域原文不进入本公开登记面。

## 当前来源水位

- 旧仓 [Eridanus117/agent-control#70（方法模型与方法库的目标形态）](https://github.com/Eridanus117/agent-control/issues/70) 的方法卡 schema、P1–P8 类型学、五层承载与 70-D1／70-D2 决定回执；核验时间：2026-08-11。当前问题求解诉求已迁至 [zaurakworks/agent-control#4](https://github.com/zaurakworks/agent-control/issues/4)，两者编号不可互换。
- 仓内 APS `0.2.8`、`grilling` `0.1.0`、`self-improvement` `0.1.4`；首批登记面基线核验提交：`a11176fddc70c50f32984cfef9da18d8768370fa`。
- [关联 Eridanus117/agent-control#85（Premortem 方法卡实战）的证据升级评论](https://github.com/Eridanus117/agent-control/issues/85#issuecomment-5258420709)与[关联 Eridanus117/agent-control#86（关键假设检查方法卡实战）的自然任务评论](https://github.com/Eridanus117/agent-control/issues/86#issuecomment-5258418149)；本批只支持两张卡在原适用边界升为 M1。
- [关联 Eridanus117/agent-control#92（红队方法卡实战）的红队评论](https://github.com/Eridanus117/agent-control/issues/92#issuecomment-5258711541)与[收口回执](https://github.com/Eridanus117/agent-control/issues/92#issuecomment-5258729826)；本批只支持 `red-team-analysis` 在私域迁移链路只读安全审查边界升为 M1。
- [关联 Eridanus117/agent-control#93（问题类型学首批真实样本校准）的实证评论](https://github.com/Eridanus117/agent-control/issues/93#issuecomment-5258734377)；21 个真实决策时刻只支持 INDEX 的阶段判别、P6 首跳出口、两张相关卡的有界修订与后续样本水位，不支持产品采用或长期依赖。
- [关联 Eridanus117/agent-control#98（知识包检索召回对照）的实验评论](https://github.com/Eridanus117/agent-control/issues/98#issuecomment-5259163307)、[关联 Eridanus117/agent-control#102（检索规模拐点）的实验评论](https://github.com/Eridanus117/agent-control/issues/102#issuecomment-5259493468)及[收口回执](https://github.com/Eridanus117/agent-control/issues/102#issuecomment-5259500823)支持 `comparative-experiment` 只在技术检索方法的可控对照与规模压力实验边界升为 M1；[关联 Eridanus117/agent-control#112（Orca 依赖三方向 ROI）的交付评论](https://github.com/Eridanus117/agent-control/issues/112#issuecomment-5261062363)及[决定回执](https://github.com/Eridanus117/agent-control/issues/112#issuecomment-5261160382)支持 `aps-roi-options` 只在运行底座依赖的有界产品与实施取舍边界升为 M1，同时把“维持现状不应被包装成负责人决定”保留为失败样本。本批没有取得足以排除事后套用的 `outside-in-thinking` 与 `sequential-experiment` 明确使用证据，两张卡如实保持 M0。
- [关联 Eridanus117/agent-control#109（三方审阅机制方案）的成型方案](https://github.com/Eridanus117/agent-control/issues/109#issuecomment-5260729739)及[决定回执](https://github.com/Eridanus117/agent-control/issues/109#issuecomment-5260909104)支持 `devils-advocacy` 只在 Agent 系统高影响产品决定的反方论证边界升为 M1；[关联 Eridanus117/agent-control#79（系统运营指标基线）的调研评论](https://github.com/Eridanus117/agent-control/issues/79#issuecomment-5258121023)及[决定回执](https://github.com/Eridanus117/agent-control/issues/79#issuecomment-5258166941)支持 `goal-question-metric` 只在 Agent 系统运营指标的人工低成本基线与复核边界升为 M1。本批复核的其他候选只呈现相似任务形状，缺少完整执行链或卡片级复核，均保持 M0。
- 两批显式方法卡实战把跨任务证据收敛到四个窄边界：`quality-of-information-check` 用资源快照失效、投入规则形成与交付链校准多来源投入判断；`outside-in-thinking` 用知识真实复用与覆盖缺口两项实验校准知识产品的外部使用方／运行环境约束；`paired-observation` 用两批安装指纹验收校准精确版本目录下的三端文本一致性；`indicators-signposts` 用来源 Issue 与经营 Project 的一致／漂移样本校准生命周期投影重评。四张卡只在各自边界升为 M1，证据上限均为当前交付验收；`what-if-analysis` 只有一项显式复核，`high-impact-low-probability` 仍属事后重放，两者保持 M0。**置换对象**：四张卡原有“本系统尚无”M0 证据占位，以及 README／INDEX 的 M0 22／M1 8 旧水位；本批不改方法执行定义。
- CIA《A Tradecraft Primer》、Cynefin 官方说明、NASA GQM 资料与 NIST 工程统计手册；本批只使用公开一手来源校准能力形状，卡片均独立改写。
