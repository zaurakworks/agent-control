# 已完成任务：让经营总账成为跨 Session 可发现的维护行为

> 状态：已完成。经营总账维护 Skill、权威和短入口已经合并并安装到三端，一个全新只读 Session 已发现并正确使用该行为；合并后父目标独立复核通过，负责人确认该窄能力“当前满足”并关闭 Parent [#13](https://github.com/Eridanus117/agent-control/issues/13)。
> 开始日期：2026-08-10。

## 原始问题

负责人要建设一套可管理的 Agent 系统，使不同模型和 Session 能在低成本对齐后持续推进，并保持方向、状态和证据可恢复。

已经验收的 [`Agent 系统经营总账`](https://github.com/users/Eridanus117/projects/3) 解决了“负责人在哪里看全局”的问题，但没有解决“新 Session 怎样稳定维护全局”的问题。当前只有 GitHub Project、Issue、活动任务和研发记录；不存在负责收件、分类、状态更新、证据更新、远端复核和退出的经营总账维护 Skill。

因此，资产虽然可读，Agent 行为仍依赖本次长上下文。新 Session 可能完全不读取总账，也可能把普通想法误建成正式诉求，或再次把交付完成写成上层诉求满足。

## 负责人的纠正

负责人在验收后追问：“你只是构建完了，skills 化了吗”。该纠正指出旧完成判定遗漏了跨 Session 行为入口。

被替代的判断：经营总账观察面通过一次人工验收，就可以把整个能力任务标成完成。

当前判断：原 `#12` 的观察面交付仍可保持完成；但“经营总账成为可复用 Agent 能力”尚未完成，需要一个独立、窄、可逆的行为交付。

## 已批准的最小范围

负责人批准以下完整范围：

1. 在 `agent-plugins` 建立一个窄的经营总账维护 Skill；
2. 触发条件覆盖 Agent 系统中的新诉求、重要候选、决定、任务状态、验收与证据变化；
3. Skill 负责读取当前总账、区分收件箱与正式事项、维护执行状态／诉求状态／证据等级、远端复核并返回原任务；
4. 在 `agent-control` 固化已确认的经营总账产品边界，并加入一条短运行入口触发规则；
5. 给最终验收补上通用检查：声称跨 Session 能力完成时，必须存在并核验持久行为入口；
6. 把 Skill 安装到普通 Codex、Orca Codex 与 Claude，并检查真实入口、版本、内容和可发现性；
7. 使用当前非平凡 Agent 系统交付质量门完成自审、独立复核和整合。

## 明确不做

- 不实现 GitHub 轮询、Webhook、Actions Agent Runner、Hook、自动调度或常驻服务；
- 不让 Project 自动规划、派发、启动、暂停或合并工作；
- 不把所有 GitHub Issue 操作塞进本 Skill，不复制 `objective-to-issues`、`issue-delivery` 或 `pr-integration`；
- 不批量迁移旧 Issue、旧 Project、旧仓知识或零散历史；
- 不把一次安装或受控检查升级为产品采用或长期依赖；
- 不为验证另建评测平台。

## 载体与职责

- 新权威保存已经确认的总账产品边界和状态语义；
- 系统入口只保存短触发规则，不复制维护流程；
- 新 Skill 保存条件性、多步骤维护行为；
- GitHub Issue／Project 保存真实事项和动态状态；
- 研发记录保存本次遗漏、原因、实验和限制；
- GitHub 或 Orca 的事件触发能力继续作为未批准候选，不由 Skill 假装提供。

## 与现有 Skill 的边界

- `objective-to-issues` 只把已经对齐、获准写入的长程交付目标转成父／子 Issue 图，并明确不默认管理 Project；
- 新 Skill 只决定总账是否应当记录变化、记录到哪一层、怎样维护三类状态并远端复核；
- 需要建立交付任务图时路由到 `objective-to-issues`；需要交付单个 Issue 或整合 PR 时继续使用现有协作 Skill；
- 未确认的重要候选只能进入收件箱或等待负责人，不能由维护 Skill 自动升级成正式诉求。

## GitHub 交付合同

- Parent：[`agent-control#13 能力：让经营总账成为跨 Session 可发现的维护行为`](https://github.com/Eridanus117/agent-control/issues/13)；
- Skill 切片：[`agent-plugins#17 交付：实现经营总账维护 Skill 与跨 Session 完成检查`](https://github.com/Eridanus117/agent-plugins/issues/17)；
- 入口切片：[`agent-control#14 交付：固化经营总账权威并接入 Agent 入口`](https://github.com/Eridanus117/agent-control/issues/14)。

`#13` 已作为根目标 `#6` 的原生子 Issue；两个交付 Issue 已作为 `#13` 的原生跨仓子 Issue。两个切片可以并行开发，但整合顺序是先 Skill、后入口与安装，避免入口短暂指向不存在的能力。

## 本阶段方法、成本与停止条件

- 使用 self-improvement 诊断并保存完成判定缺口；
- 使用 objective-to-issues 建立两个跨仓、文件所有权不重叠的交付切片；
- 实现采用最小 Skill + 短入口 + 权威边界，不做平台调研；
- 两个仓分别通过 Draft PR 交付，Agent 入口与 Skill 都要自审和独立当前 head 复核；
- 若发现必须建设事件后端、改变 Project 产品模型或扩大到实际业务组合，立即停止并请求负责人决定；
- 当远端 PR、安装一致性和至少一个全新 Session 的可发现性证据足以支持当前交付验收时停止，不追求自然使用证明。

## 完成门

只有以下条件同时成立，才可称为“当前交付验收就绪”：

1. 权威、短触发入口、Skill 正文和真实运行入口职责一致；
2. 新 Session 能从持久入口发现维护 Skill，而不是依赖本次聊天；
3. 收件箱、正式事项、执行状态、诉求状态和证据等级的边界可静态走通；
4. 两个仓的精确提交通过自审和独立复核；
5. 三端安装与版本化源码一致；
6. 经营总账中的当前事项、状态和证据与远端事实一致；
7. 最终结论明确区分实现完成、当前交付验收、样本有效、产品采用和长期依赖。

## 当前授权

负责人已经授权上述完整实施，包括修改 `agent-control`、`agent-plugins`、版本化入口、相关权威、真实三端安装、GitHub Issue／PR／Project 状态、必要验证、提交和推送。

授权不包含本文件“明确不做”中的能力，也不自动授权在验收后继续扩展。

## 当前整合证据

- `agent-plugins#18` 验收 head `2ab313c0f39af5ff976260595c933aedd7aaf8e6` 已合并为 `341fb4fb76cac5fb11accd0cf83061a680a61192`；
- `agent-control#15` 验收 head `2eee6a58eb462beadebc291953581e2dd6b33d0d` 已合并为 `d98721e1ee46f6dcb9a5cbeac9e3f051060c5d1a`；
- 两个 head 都经过自审、不同 Agent 独立复核和修复后复核，最终 P0／P1／P2 均为零；
- 普通 Codex、Orca Codex 与 Claude 均安装 `github-collaboration 0.2.0`、`adaptive-problem-solving 0.1.2`，三端 Skill 正文哈希与版本化源码一致；
- 三份真实 Agent 入口与版本化入口的规范化文本一致；
- 一个新的 Orca Codex 临时只读 Session 不依赖本次聊天，实际发现专用权威和 `operating-ledger-maintenance`，并正确回答收件箱与“不自动启动工作”边界；
- 该检查约使用 120,123 输入 Token，其中 98,048 cached，外加 1,536 输出 Token。它满足一次受控发现检查，但成本偏高，因此没有复制第二次行为会话；
- 当前证据候选只到“当前交付验收”，不代表自然样本收益、产品采用或长期依赖。
- 未参与实现的 Agent 已完成合并后父目标复核并判定 PASS：[`Parent #13 最终审查评论`](https://github.com/Eridanus117/agent-control/issues/13#issuecomment-5238922119)。Parent 继续保持开放、诉求状态“未满足”、证据“当前交付验收”，没有由 Agent 自动改变产品状态。
- 负责人随后批准按推荐收口：Parent [#13](https://github.com/Eridanus117/agent-control/issues/13) 已关闭，诉求状态为“当前满足”，证据仍为“当前交付验收”；GitHub Workflow 自动写入的能力项执行状态已按权威清除，上层根目标 [#6](https://github.com/Eridanus117/agent-control/issues/6) 保持开放。

## 新的授权摩擦候选

负责人在本次精确 head 合并授权后追问，这类合并是否其实不需要再次同意。当前之所以必须询问，是因为两个交付合同明确禁止自动合并，且系统尚无“门槛全部通过即可合并”的条件式预授权。

候选方向是：未来在任务开始时允许负责人一次性授予条件式合并权；只有当前 head、检查、独立复核、反馈、依赖和可合并性均满足约定时，Agent 才可直接合并。它可能降低人类注意力成本，也可能扩大 Agent 对共享远端状态的权限。本轮已把“候选：交付合同预授权满足门槛后的合并”保存为经营总账收件箱草稿，不改变现有合并规则。

## 本任务相关权威与记录

- [`../../authority/00-map.md`](../../authority/00-map.md)
- [`../../authority/03-thinking-methods.md`](../../authority/03-thinking-methods.md)
- [`../../authority/04-collaboration.md`](../../authority/04-collaboration.md)
- [`../../authority/08-mvp-implementation-direction.md`](../../authority/08-mvp-implementation-direction.md)
- [`../../authority/09-rd-memory.md`](../../authority/09-rd-memory.md)
- [`../../authority/10-operating-ledger.md`](../../authority/10-operating-ledger.md)
- [`../records/2026-08-09-agent-system-bootstrap/record.md`](../records/2026-08-09-agent-system-bootstrap/record.md)

## 下一步

本任务已完成并归档；后续 Session 不得从本文恢复授权或自动继续扩展。条件式合并仍保留在经营总账收件箱，只有新的自然证据和负责人决定才可升级。
