# K16：多 Session 审阅必须机械核验联合身份并先密封后公开

> 状态：正式当前公共知识。
> 最近核验：2026-08-12。
> 适用对象：已有明确替代授权、需要把多个 Session 的判定作为决定消费前件的审阅流程；当前直接实现是 Orca `orchestrated-collaboration` 0.2.2 所含 CF-6 0.2.0。
> 环境：Windows 11；Orca 1.4.180；GitHub.com 评论 API；CF-6 静态实现合并提交 `73a4494842cbe0422e89273f7cc6946b27deb93b`，当前安装态与 agent-plugins 提交 `3baccec0d83115bb3123382b34fb0ec944512741` 的 CF-6 正文规范化一致；Node 直接运行仓内 TypeScript 验证器与合同测试。
> 证据上限：联合身份、机械映射和先密封后公开已完成静态实现与回归验收；P0-1 与 P0-3 两个自然样本又证明机制能在当前边界发现真实缺陷并经修订完成三席一致复核，但仍没有长期错误率、假阳性率或负责人注意力收益证据。

## 回答的问题与价值门

多个 Session 都留下“认可”评论时，什么证据足以证明三张席位来自正确且互异的运行身份，评论没有被人工错绑，并且各票在公开前没有被先票锚定？

多 Session 审阅若参与授权内决定消费，身份错配或伪独立会把评论数量误当成独立判断。该验证会在每次使用三方替代授权时重复出现，错误又会影响后续合同与持久资产，因此通过价值门。

## 可直接复用的结论

### 1. 席位凭证必须与运行时身份的联合类型同构，不能强迫所有角色使用同一字段

协调者和受派评审的生命周期身份不同，正确模型是带 `seat_kind` 标签的联合类型：

| 席位或判定 | 稳定关联键 | 只作交叉核验的观察字段 | 不能替代 |
| --- | --- | --- | --- |
| 协调者席 | `run_id + consumer_generation` | `observed_terminal_handle`、`observed_at` | terminal 句柄不能单独证明当前协调消费者 |
| 受派评审席 | `task_id + dispatch_id` | `run_id`、`observed_terminal_handle`、`observed_at` | Task 不能单独证明某一次尝试，terminal 也不是持久身份 |
| GitHub 判定 | `decision_id + role_id + comment_url` | 作者类型、可信账号、目标 Issue、编辑水位 | 同一 GitHub 账号的多条评论不能证明来自不同 Session |

“同构”指证据清单保留运行时身份的分支类型和稳定键，再把它们归一化为统一映射行；不是把协调者伪装成拥有 Task／Dispatch，也不是把所有角色压成 terminal 句柄。每票还必须绑定同一决定包哈希、唯一反方角色、密封消息 ID／哈希、公开判定和评论编辑水位。

### 2. 映射必须由稳定键机械生成并两次回读，不能按数组、发布时间或人工顺序配对

[关联 agent-plugins#54（三方审阅机制 0.2.0）](https://github.com/Eridanus117/agent-plugins/pull/54)落地的[只读验证器](https://github.com/Eridanus117/agent-plugins/blob/73a4494842cbe0422e89273f7cc6946b27deb93b/plugins/orchestrated-collaboration/scripts/verify-three-party-review.ts)按以下顺序核验：

1. 从 Orca `run-show` 读取协调者 Run 与代际，从 `worker-show` 读取受派评审的 Task、Dispatch、Run 和终端落点；从 GitHub 评论 API 读取 URL、作者、目标 Issue、正文与编辑水位。
2. 以 `decision_id + role_id + stable_runtime_key` 键连接；映射行固定按 R1、R2、R3 规范排序，而不是按返回数组或评论发布时间配对。
3. 对 Run、Dispatch 与评论做两轮只读取证；任一来源变化、未知或不一致都输出 `verified=false`。
4. 直接生成规范化 JSON 与 Markdown 映射表；决定回执嵌入该输出，不再人工换序抄写。

验证器同时检查三席数量、角色／URL／运行身份／terminal 唯一性、起草者与实施者回避、异族模型席、可信 GitHub User、目标 Issue、代际、编辑水位、决定包哈希、密封哈希和判定内容。工具失败是未知或失败，不解释为通过。

### 3. 独立运行身份不等于认知独立；判定必须先密封、后统一公开

不同 Session、模型和 Dispatch 只能证明执行来源不同。若第一票先出现在目标 Issue，后续评审仍可能被其结论和论证锚定。当前 CF-6 采用程序性密封：

```text
冻结决定包与哈希
→ 三席分别通过自身 Dispatch 的 ask 提交完整判定并取得密封消息 ID
→ 三封齐且身份预检通过
→ 各席原封公开到目标 Issue
→ 比较公开载荷与密封哈希
→ 两轮机械映射核验
→ 全部认可且授权类别合规，才可消费；否则只保留审阅证据并转负责人
```

密封防止判定按公开顺序相互锚定，并使公开正文可由哈希回查；它不是密码学隔离，也不能证明拥有本机高权限的人绝无旁路查看。协调者若占一席，必须在读取其他评审 Delivery 以前先密封自己的判定，否则只能主持、不计票。

### 4. 历史反向绑定回归证明机械门能拒绝错配；后续自然样本证明机制能挡住真实缺陷

[关联 #90（M43 摘要水位滞后修复）](https://github.com/Eridanus117/agent-control/issues/90)的两名评审在各自评论中自报不同 Task；历史决定回执却把两张 Task 与评论反向配对。`orchestrated-collaboration` 0.2.0 把该真实缺陷归一化为负向夹具。

[验证器合同测试](https://github.com/Eridanus117/agent-plugins/blob/73a4494842cbe0422e89273f7cc6946b27deb93b/plugins/orchestrated-collaboration/tests/verify-three-party-review.test.ts)直接断言：合规夹具 `verified=true`；Task／Dispatch 对调必须被拒；[#90](https://github.com/Eridanus117/agent-control/issues/90) 反向绑定夹具必须 `verified=false`，并包含 `comment_mapping_mismatch`。关联 [#110（三方审阅机制修复实施）](https://github.com/Eridanus117/agent-control/issues/110)的[实施回执](https://github.com/Eridanus117/agent-control/issues/110#issuecomment-5261087345)与[收口回执](https://github.com/Eridanus117/agent-control/issues/110#issuecomment-5261121460)记录 R2、R3 均命中该失败码，合同测试与符合性检查通过。

这证明静态身份门能够拒绝一种历史错绑，也证明规范化排序不会把人工顺序当成身份。此后，[关联 #139（P0-1 迭代回执地基）](https://github.com/Eridanus117/agent-control/issues/139#issuecomment-5262365043)与[关联 #140（P0-3 类型化派发与写后核验门）](https://github.com/Eridanus117/agent-control/issues/140#issuecomment-5262365257)均完成“首轮真实否决 → 修订 → 原否决点复核 → 三席一致落地”，把证据上限提升到两个自然样本有效。具体触发边界、否决内容与不能外推的结论见 [K18（三方审阅一致落地）](./three-party-review-consensus.md)。

## 第一方来源与证据映射

1. [关联 #100（夜间新增资产的多视角攻防审计）交叉裁决](https://github.com/Eridanus117/agent-control/issues/100#issuecomment-5259393664)：确认 C1 身份链不统一与 C2 公开顺序不构成盲评，保存 [#90](https://github.com/Eridanus117/agent-control/issues/90) 反向绑定的一手证据；支持结论 1、3、4。
2. [关联 #109（P0 三方审阅机制方案起草）方案](https://github.com/Eridanus117/agent-control/issues/109#issuecomment-5260729739)与[109-D1（三方审阅机制整包批准）决定回执](https://github.com/Eridanus117/agent-control/issues/109#issuecomment-5260909104)：给出字段级联合类型、键连接、密封状态机、失败门与 C3=A 授权边界，并由负责人本人批准；支持结论 1–3。
3. [关联 agent-plugins#54（三方审阅机制 0.2.0）](https://github.com/Eridanus117/agent-plugins/pull/54)：绑定精确 head `0523ec35a35e9cab53c70faccd70e9fa988677cc`、合并提交、差异、测试命令与范围；支持静态实现事实。
4. 合并提交中的 [CF-6 0.2.0](https://github.com/Eridanus117/agent-plugins/blob/73a4494842cbe0422e89273f7cc6946b27deb93b/plugins/orchestrated-collaboration/skills/orchestrated-collaboration/references/collaboration-shapes/cf-6.md)、[验证器](https://github.com/Eridanus117/agent-plugins/blob/73a4494842cbe0422e89273f7cc6946b27deb93b/plugins/orchestrated-collaboration/scripts/verify-three-party-review.ts)与[合同测试](https://github.com/Eridanus117/agent-plugins/blob/73a4494842cbe0422e89273f7cc6946b27deb93b/plugins/orchestrated-collaboration/tests/verify-three-party-review.test.ts)：提供可重复实现和负向回归；支持结论 1–4。
5. [关联 #139（P0-1 迭代回执地基）首轮裁决](https://github.com/Eridanus117/agent-control/issues/139#issuecomment-5262189283)与[三席一致回执](https://github.com/Eridanus117/agent-control/issues/139#issuecomment-5262365043)，以及[关联 #140（P0-3 类型化派发与写后核验门）首轮裁决](https://github.com/Eridanus117/agent-control/issues/140#issuecomment-5262189536)与[三席一致回执](https://github.com/Eridanus117/agent-control/issues/140#issuecomment-5262365257)：保存两条“否决成立 → 修订 → 独立复核 → 三席一致”自然链；支持结论 4 的自然样本增量。

## 两道准入门逐项判定

| 准入项 | 判定 | 依据 |
| --- | --- | --- |
| 价值门 | 通过 | 每次使用多 Session 替代授权都要证明席位、评论和运行身份正确绑定；错配会影响决定消费。 |
| 1. 明确回答的问题 | 通过 | 问题限定为多 Session 席位身份、评论映射与公开前认知独立的可核验证据。 |
| 2. 可直接使用的结论和必要解释 | 通过 | 给出三分支联合类型、稳定键连接、两轮回读和密封—公开—消费顺序。 |
| 3. 第一方来源或可重复验证过程 | 通过 | 负责人批准、合并源码、合同测试、正负夹具、[#90](https://github.com/Eridanus117/agent-control/issues/90) 真实失败样本及 [#139](https://github.com/Eridanus117/agent-control/issues/139)／[#140](https://github.com/Eridanus117/agent-control/issues/140) 两条自然链均可远端复查。 |
| 4. 对象、版本、环境和核验时间 | 通过 | 页首限定 oc 0.2.0、合并提交、Orca、GitHub、Windows 与日期。 |
| 5. 例外、仍未知内容和不能推出的结论 | 通过 | 下节排除自然有效性、内容质量、密码学隔离、授权来源与其他后端的泛化。 |
| 6. 明确的失效条件 | 通过 | 下节列出 Orca／GitHub 语义、授权、验证器和自然假阳性变化。 |
| 7. 下次最少复核步骤 | 通过 | 复跑一项合同测试、复核动态字段，并等待首个自然样本的未参评复核。 |
| 8. 人容易理解、Agent 足以复用的表达 | 通过 | 正文以联合身份表、机械流程、密封顺序和回归边界组织。 |

## 例外、未知和不能推出的结论

- 验证器只证明来源身份、映射、密封载荷和三票判定满足合同；不评价论证是否正确、选项是否完整或决定是否值得。
- `verified=true` 不产生授权。只有当前合同已存在、且决定类别落在负责人批准的 C3=A 边界内，映射才是消费前件之一。
- GitHub 评论作者是可信 User，只能证明发帖主体；不能替代 Orca 运行身份。terminal 只作观察值，也不能替代稳定关联键。
- 程序性密封防公开顺序锚定，不提供密码学保密、恶意管理员隔离或跨后端机密提交保证。
- [#90](https://github.com/Eridanus117/agent-control/issues/90) 是一个真实负向回放；[#139](https://github.com/Eridanus117/agent-control/issues/139) 与 [#140](https://github.com/Eridanus117/agent-control/issues/140) 是两个自然正例，均由首轮否决促成真实修订后再完成一致复核。它们只支持当前边界的样本有效，不替代每次运行的身份与密封核验。
- 两个同夜、同仓群自然样本不能证明长期降低错误率、减少负责人问询、假阳性率可接受或产生正 ROI；这些需要更多自然任务与成本观察。
- 本包绑定 Orca 1.4.180 与 GitHub.com 评论语义；其他协调后端需要等价的稳定身份和密封见证，不能直接套字段名。

## 失效条件

出现以下任一情况时，受影响结论停止直接复用并先做最少复核：

1. Orca 改变 Run、`consumer_generation`、Task、Dispatch、worker-show、run-show、ask 或终端句柄的对象语义；
2. GitHub 改变评论 URL、作者类型、目标 Issue、编辑水位或评论 API 的可回读语义；
3. CF-6、验证器 schema、失败码、规范化哈希或两轮取证流程发生变化；
4. 负责人修改 C3=A 边界、席位构成、回避规则或三方替代授权；
5. 自然样本出现 `verified=true` 的错消费、先票可见改变判断，或评论与运行身份仍可错绑；
6. 连续自然样本显示维护成本高于负责人直接决定，且没有减少问询或返工；
7. 任务改用不能提供等价稳定身份、密封消息与评论回读的协调后端。

## 下次最少复核步骤

1. 在 agent-plugins 当前 checkout 运行 `node plugins/orchestrated-collaboration/tests/verify-three-party-review.test.ts`；确认合规夹具仍通过、[#90](https://github.com/Eridanus117/agent-control/issues/90) 夹具仍因 `comment_mapping_mismatch` 被拒。
2. 动态读取当前 Orca orchestration 指南，并只读核对 `run-show`、`worker-show` 与 `ask` 仍能提供本包使用的对象和恢复语义；字段或语义变化时更新适配，不以旧输出猜测。
3. 对照当前 CF-6 与验证器源码，确认稳定键仍按席位联合类型分支，terminal 仍只是观察值，映射仍由键连接和两轮取证生成。
4. 下一次自然、低风险、已获替代授权的三方任务出现时，继续保留三封、三条公开评论、规范映射和决定回执；由未参评者复核 [#90](https://github.com/Eridanus117/agent-control/issues/90) 型错绑、先票可见和授权类别，并记录否决是否后来被证实为真故障。
5. 只有更多自然样本提供假阳性、墙钟、负责人问询和返工方向证据后，才讨论产品采用或长期收益；当前两个样本不得继续外推。

## 不适用范围

- 没有负责人替代授权的普通多人意见收集；
- 论证质量评分、自动投票、自动消费决定或自动合并；
- 密码学投票、匿名投票、抗恶意管理员的保密系统；
- 产品采用、长期依赖、父目标满足、根诉求状态或授权变化的代理决定；
- 非 Orca 后端在尚未定义等价运行身份与密封见证时的直接复用。
