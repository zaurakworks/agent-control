# Agent 系统整体架构创新对比（I 阶段）

> 状态：I 阶段 6/6 已收齐并综合，非权威、非授权、非实施计划。正式合同与负责人审阅面见 https://github.com/Eridanus117/agent-control/issues/43 。
> 输入：`research.md`（R 阶段事实基线）；六个独立创新 Session 各一条 I 阶段评论。综合者：Fable 5 全局协调 Session。冲突时以各原评论为准。
> 时间：六案发布于 2026-08-11T13:15–13:19Z。

## 六案登记（全部已交付）

| 案 | 一句话主张 | 评论 |
| --- | --- | --- |
| I1 GitHub 原生联邦 | GitHub 是唯一持久联邦控制面；Orca 薄化为可替换运行器；无 CAS／无强制门写成公开产品边界 | [5253666815](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253666815) |
| I2 Orca 运行时优先 | 执行事实与意图事实分家：Orca 记执行、Issue 记意图与验收，单向投影永不双向同步；净新增存储 0 | [5253684712](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253684712) |
| I3 极简人机协作 | 一份合同·一个活动写者·一次人类回合；机制面单调收缩；规模上限 1+1+≤3+1 显式声明 | [5253701791](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253701791) |
| I4 强自动化经营控制面 | 仪表→节流阀→闸门三段闭环；负责人注意力是唯一被控变量；无传感器不许自动化；AIMD 并发律 | [5253700132](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253700132) |
| I5 复用／Fork 外部生态 | 可替换生态内核：外部实现＋内部能力合同；Orca MIT Fork 主运行时；Agent Skills 生态主行为面 | [5253703568](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253703568) |
| I6 分层渐进组合 | 能力×承载层（C0–C5）投资表＋三不变量（证据定层／预算守恒只换不加／降级免授权泵）＋波次计数重评泵 | [5253685413](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253685413) |

## 判别性结构（六案的真实分歧轴）

1. **执行事实的记录者**：Issue 回执（I1）／Orca 原生对象（I2）／一条收口评论＋三个数（I3）／receipts.jsonl＋波次回执（I4）／GitHub 批次回执（I5）／波次回执寄生 C1（I6）。
2. **机制投资时机**：现在就建传感器或身份桥（I2、I4、I5）vs 触发条件命中才建（I3、I6）vs 不建机制、诚实合同化（I1）。
3. **对基线未知的姿态**：正确性不依赖任何未验证未知（I1、I3、I6 第一层）vs 有明示生死线依赖（I2 依赖未知 1[worker-abandon 真伪]、I5 依赖 U10[Fork 语言合规门]）vs 分档解锁依赖（I4）。
4. **Orca 定位谱系**：可替换薄运行器（I1、I3）→ 第一方调度器消费（I4）→ 执行事实权威（I2）→ 受控 MIT Fork 主运行时（I5）→ 按层触发升级（I6）。
5. **对负责人注意力的处理**：I4 把它变成被控变量进反馈律；I3 把它压成单一人类回合原语；I6 把它写进波次回执第一行；I1/I2/I5 作为验收指标而非控制变量。

## 六案共识面（C 阶段可直接作为起点，无需再裁决）

1. **X3 注意力口径先行**——六案全部列为硬前置；X4 外生任务全部引用为唯一 ROI 证伪路径（未知 5 是全场唯一被六案共同强依赖的未知）。
2. **出口优先**：全部继承 #42「先修收口，入口零失败观测不投资」。
3. **current.md 降级方向一致**（指针/三行/删除/投影产物/可再生指针），仅幅度不同。
4. **不依赖 GitHub 强制门**（403 事实全场接受）；**不 Fork codex-marketplace**（许可缺失全场接受）；**marketplace 三件不立即禁用**，盘点/使用计数先行（六案处置收敛度极高）。
5. **Skill 描述预算是硬约束**：无案提出新增大 Skill；分歧只在收缩幅度。
6. **不建评测平台；自动合并保持不授权**（含 I4 也不请求）。
7. **append-only Issue 评论是唯一被验证并发形态**这一事实被全场用作设计地基。

## C 阶段必须裁决的冲突

| # | 冲突 | 两端 |
| --- | --- | --- |
| K1 | 执行事实记录者：GitHub 还是 Orca | I1（Issue 回执）vs I2（Orca 原生对象＋单向投影）；I4/I6 的波次回执是第三种粒度 |
| K2 | attempt 回执（#42 F/G 遗留分歧）的六种站位 | I1 保留回执体系（偏 F）；I2/I3/I4 站 G；I6 按层分派（日常 G、双写/跨接 F）——I6 的分层裁决是否成立 |
| K3 | 新增持久状态：I4 的 receipts.jsonl 与 #42 F/G「删除新增存储状态」正面冲突（I4 自认 B4 交负责人） | 允许唯一 append-only 仪表 vs 零新增存储 |
| K4 | 自动化边界修改：I4 B1–B3（「不授权常驻调度器」收窄为「不授权自建」、允许 orca automations 分档解锁）vs I3/I6 明确接受现边界 | 收窄 vs 维持 |
| K5 | 自有 Skill 收缩幅度：I3 MR3（7→4 合并）vs I4（一个不动）vs I6（复核候选不执行）vs I5（终态收缩为政策叠层） | 立即合并 vs 证据驱动收缩 vs 不动 |
| K6 | Orca 定位（判别轴 4 的五个点位互斥） | 薄可替换 vs 执行权威 vs Fork 主运行时 |
| K7 | aps「持久行为入口」判据：I3 MR4 请求改为「复用≥2 次才沉淀」vs 现行判据（R3 判 #43 方法为 S1 未满足） | 判据松紧 |
| K8 | current.md 终局：删除（I3）vs 保留指针壳（其余五案） | 删 vs 留壳 |

## 修改边界请求总表（全部需负责人决定，C 阶段按帕累托筛选后呈报）

- I1×5：Issue/PR 升为持久任务主干；current 降级；托管 Actions 只做校验/对账；配置期望 manifest；marketplace 逐能力脱离门。
- I2×3：B1 入口文本区分「Orca TUI=观察面／orchestration=执行权威」；B2 automations 记为已知可选能力（不解禁）；B3 执行状态来源改从 worker-list/gate-list 派生。
- I3×5：MR1 删 current；MR2 Project 降为书签；MR3 Skill 7→4；MR4 aps 判据改复用计数；MR5 code-quality 停用决定权。
- I4×4：B1 调度器边界收窄；B2 自动派发分档；B3 自动执行已授权关闭；B4 receipts.jsonl 裁决。
- I5×7：authority/04 改候选组合；Orca Fork 过门后允许；current 降级；依赖锁定清单；Provider memory 隔离试验；自有包收缩；Issue/PR 模板。
- I6×4：M1 渐进阶梯升为控制结构；M2 降级免授权（方案单点）；M3 C2/C3 预算硬顶；M4 明确不请求放宽调度器边界。

## I 阶段带来的新一手运行证据（方案外收获，已并入验证面）

- 高层 `worker-start --worktree current` 6/6 成功；`worker-release` 对高层 Dispatch 正常（released＋自动关终端＋transcript 归档）——低层 10 次断裂在高层路径不存在（I 阶段派发与收口实测）。
- `worker-start` 注入 Claude 的 Enter 竞态：`input_accepted` ≠ 已提交，3/4 Claude 终端文本停输入框，协调者补 Enter 恢复；对策=派发后核对终端标题。
- 被 `terminal send` 干预过的终端 release 可能返回 `retained`（I2/I4）需手动关闭，但非绝对（I3 正常 released）。
- `worktree ps` 的 `agents[].agentType` 已填充（claude/codex）＋ `parentPaneKey` 谱系——R5 F15「agentKind 全 null」只成立于 `terminal list` 面（I2 实测）。
- `dispatch --dry-run --return-preamble` 契约存在（X1 可无副作用化）；`orca automations` CLI 面完整存在（create --precheck/--workspace-mode/cron，list 当前为空）（I2/I4 契约观察）。
- X1 前半正向：`dispatch-show --preamble` 可为已派发 task 重新产出完整令牌上下文；X2 正向：4/4 观察中条目可写出合格唤醒谓词（协调者探测）。

## C 阶段合同要点（给三位交叉审查者）

- C-A 全局一致性与能力回退：六案各自内部一致性、与十一条跨域约束的相容性、能力回退清单的完整性；K1–K8 逐项裁决或给出裁决所需的最小实验。
- C-B 复用/Fork/自建 ROI 与可逆性：判别轴 4 五个点位的维护成本、退出成本、许可与供应链风险；marketplace 渐进脱离路径的统一化。
- C-C 负责人注意力与真实吞吐：以 X3 口径草案与本波样本为基准，评估六案的注意力路径与吞吐假设的可证伪性；帕累托前沿按「负责人注意力×可恢复性×维护面×能力上限」四维绘制。
- 三者共同产出：Pareto 前沿、推荐方向＋最强替代、关键未知、MVP 边界、明确不做、未来重评触发条件（模型能力/系统状态/新证据三类，继承 I6 T-触发形式但不预设采纳 I6）。

## C 阶段结论（3/3 已收齐，2026-08-11T13:34–13:42Z）

- C-A 全局一致性与能力回退：[5253917095](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253917095)。三项交叉发现（五项清单四份外延互不相同且≠入口六类；三案独立收敛波次回执；约束 4 六案中仅 I2 一案正面回答）；K1 三分裁决；28→6 呈报集 P1–P6；M/S/E 系列可判定触发。
- C-B 复用/Fork/自建 ROI 与可逆性：[5253879904](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253879904)。推荐组合点 A（I1+I6+窄 I2+I5 协议）与低维护极值 B；K3/K5/K6 负向裁决；28→2 决定包 D-CB1/D-CB2；marketplace 统一七步协议。
- C-C 负责人注意力与真实吞吐：[5253892547](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253892547)。一手度量（34:1 压缩比、200 秒并行窗口、X3 分母远端零成本派生）；I4 全案出局（AIMD 分母未定义+整定慢于漂移）；I6 判为坐标轴；前沿三点 P1/P2/P3 与「恢复面宽度×写入成本×未验证依赖」真实三角；两条新增触发（出口共识证伪、X3 口径自身失效）。

最终综合（含推荐组合、D1–D6 最小决定集、授权内动作、明确不做、三条未消解张力 T1–T3、三类重评触发）：[5253961205](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253961205)。本轮到此收敛，等待负责人决定。
