# K11：GitHub GraphQL mutation 重试必须以远端目标状态为准

> 状态：正式当前公共知识。
> 最近核验：2026-08-11。
> 适用对象：GitHub.com GraphQL API 的 `updateProjectV2ItemFieldValue`、`updateIssue`，以及能够按稳定对象身份和目标值回读的同类远端写入。
> 环境：GitHub.com 托管服务；Windows 11；GitHub CLI 已认证；实证样本为同一账号、同一 Session、顺序执行的两对象部分失败夹具。
> 版本边界：GitHub.com 托管服务没有可固定的版本号；GraphQL schema、目标对象事件语义或具体 mutation 的幂等合同变化即为失效信号。

## 回答的问题与价值门

GitHub GraphQL 写入报错、超时或只完成一部分时，重复使用同一个 `clientMutationId` 能否证明服务端只执行一次？什么证据足以决定继续、补做或停止？

Agent 系统会反复更新 Issue、PR 与 Project；一次错误恢复若重复创建对象、重复改变状态或覆盖新值，会破坏远端任务合同。该结论已直接进入当前协作写入的恢复顺序，后续 GitHub 交付会重复使用，因此通过价值门。

## 可直接复用的结论

### 1. `clientMutationId` 是客户端关联字段，不是已获保证的服务端幂等键

2026-08-11 对 GitHub.com 在线 GraphQL schema 的直接 introspection 显示：

- `UpdateProjectV2ItemFieldValueInput.clientMutationId` 与 `UpdateIssueInput.clientMutationId` 都只描述为执行 mutation 的客户端标识；
- 对应 payload 会原样返回 `clientMutationId`；
- schema 没有声明相同值会去重、只执行一次或拒绝重放。

因此，可以用 `clientMutationId` 把请求和响应关联起来，但不能仅凭它判断远端动作是否已经发生，也不能把“再次提交同一个值”当成服务端提供的 exactly-once 保证。

### 2. 单次重放的表面幂等，只证明该样本的可观察目标收敛

[agent-plugins 关联 #44（决定消费收口部分失败轨迹夹具）](https://github.com/Eridanus117/agent-plugins/issues/44#issuecomment-5257940065)按预注册顺序执行了两遍：第一遍把一个 Project item 写到目标单选值，随后故意让来源 Issue 写入因对象标识失配而失败；第二遍以相同 `clientMutationId`、同一 item、字段和目标值重放 Project 写入，再把来源写入定向正确对象。

可观察结果是：Project 仍只有一个 item、一次状态变化事件和同一个 `updatedAt`，来源 Issue 也只有一次归档事件。这个样本支持“先按稳定对象和目标值回读，可以避免应用层双写”；它不证明 GitHub 对所有 mutation、并发重放或内部执行过程提供通用幂等保证。

### 3. 恢复依据是“稳定操作身份＋稳定对象身份＋目标状态”，不是本地回执

写入前至少记录：

1. 应用层稳定操作身份，例如决定编号或交付动作编号；
2. 精确远端对象身份，例如 Issue node ID、Project item ID、字段 ID 或 PR 当前 head；
3. 预期目标状态或目标值；
4. 多对象动作的既定顺序和唯一物理写入者。

写入返回错误、超时或部分成功后，按下面顺序恢复：

```text
重读精确远端对象与目标字段／事件／当前 head
→ 已达到目标：从远端事实继续，不重复写入
→ 明确未达到目标：只补做原动作的缺失步骤
→ 状态无法取得或无法唯一判断：保留未知，停止新增写入
```

多对象动作必须逐对象回读；一个对象成功不能替另一个对象证明完成。应用层恢复定位符宜组合“稳定操作身份＋对象身份＋目标值”，使新 Session 能从远端状态而非旧终端输出继续。

## 第一方来源与结论映射

1. GitHub.com 在线 GraphQL schema introspection（2026-08-11）：查询 `UpdateProjectV2ItemFieldValueInput`、`UpdateIssueInput` 及对应 payload，直接支持 `clientMutationId` 的字段说明、输入／输出位置与未声明幂等保证这一边界；可从 GitHub 官方 [GraphQL input objects 参考](https://docs.github.com/en/graphql/reference/input-objects#updateprojectv2itemfieldvalueinput)复核当前字段。
2. [agent-plugins 关联 #44（决定消费收口部分失败轨迹夹具）](https://github.com/Eridanus117/agent-plugins/issues/44#issuecomment-5257940065)：保存预注册边界、逐次 mutation、`clientMutationId`、稳定对象 ID、目标值、返回、远端事件计数与最终状态；支持单样本观察和恢复定位符。
3. [关联 #66（权威与 Skill 资产的多视角攻防审计）L2-F3 补证](https://github.com/Eridanus117/agent-control/issues/66#issuecomment-5257964613)：独立汇总物理写入者、部分失败、重放与双对象回读，支持多对象恢复顺序和证据上限。

## 两道准入门逐项判定

| 准入项 | 判定 | 依据 |
| --- | --- | --- |
| 价值门 | 通过 | GitHub Issue、PR 与 Project 是当前任务合同和经营观察面的反复写入面；错误重试会直接影响可恢复性。 |
| 1. 明确回答的问题 | 通过 | 问题限定为 `clientMutationId` 的保证边界，以及远端写入报错或部分成功后的恢复证据。 |
| 2. 可直接使用的结论和必要解释 | 通过 | 给出写前四项定位信息和写后三分恢复顺序。 |
| 3. 第一方来源或可重复验证过程 | 通过 | 在线 schema 可只读复查；预注册夹具保存逐次 mutation、响应和远端事件。 |
| 4. 对象、版本、环境和核验时间 | 通过 | 页首限定 GitHub.com、两个实测 mutation、顺序单账号环境与核验日期。 |
| 5. 例外、仍未知内容和不能推出的结论 | 通过 | 下节排除通用 exactly-once、并发、创建型写入与不可回读动作的直接泛化。 |
| 6. 明确的失效条件 | 通过 | 下节列出 schema、服务端合同、事件语义和 mutation 类型变化。 |
| 7. 下次最少复核步骤 | 通过 | 只需 introspection 三组字段，并在自然失败样本中按稳定对象与目标值回读。 |
| 8. 人容易理解、Agent 足以复用的表达 | 通过 | 正文以字段边界、单样本证据和三分恢复顺序组织，不要求读者还原实验终端。 |

## 例外、未知和不能推出的结论

- 实验只有同一账号、同一 Session、顺序两遍执行；多账号或多 Session 并发仍未知。
- 一次可见事件与相同 `updatedAt` 只能证明该样本的可观察状态收敛，不能证明服务端内部从未重复执行。
- 直接实测只覆盖 `updateProjectV2ItemFieldValue` 与 `updateIssue`。创建评论、创建 Issue、增加关系等 mutation 可能产生新对象；若首次响应丢失且新对象身份未知，必须先按业务唯一键或远端列表查找，不能机械重放。
- schema 没有幂等承诺，不等于所有 mutation 都一定产生重复副作用；具体目标值本身可能具有收敛语义。
- 本包不证明 GitHub REST API、Git 推送、Orca mutation 或其他平台具有相同合同；Orca 的错误回执边界见 [K2](./orca-supervised-dispatch.md)。
- “唯一物理写入者”是应用层降低并发歧义的安全约束，不是 GitHub GraphQL 自动提供的锁。

## 失效条件

出现以下任一情况时，受影响结论停止直接复用并先做最少复核：

1. GitHub 官方 schema 或文档明确把 `clientMutationId` 定义为服务端去重／幂等键，并说明作用域、保留期与并发语义；
2. 目标 mutation 增加独立的幂等键、条件写入、版本前置条件或事务合同；
3. GitHub.com 改变 Project item、Issue、PR head 或事件时间线的可回读语义；
4. 新的直接样本显示相同对象与目标值重放会产生额外可见副作用，或回读无法辨认动作是否完成；
5. 任务对象扩展到不可按稳定身份和目标状态复核的写入。

## 下次最少复核步骤

1. 用只读 GraphQL introspection 检查 `UpdateProjectV2ItemFieldValueInput.clientMutationId`、`UpdateIssueInput.clientMutationId` 以及对应 payload 的字段说明；若仍只有客户端标识与回显语义，继续沿用本包边界。
2. 只打开上面两条实验回执，核对单账号、顺序执行、稳定对象和目标值的限制仍在，不把夹具扩大解释。
3. 下一次自然发生写入报错、超时或部分成功时，记录应用层稳定操作身份、对象 ID、目标值和回读结果；已经达到目标就停止重放，明确缺失才补做，仍不可知则停止新增写入。
4. 只有具体 mutation 的行为会改变高影响决定、且自然样本不足时，才在可丢弃夹具中做一次受控重放；不以真实任务合同或经营 Project 作为探测对象。

## 不适用范围

- GitHub GraphQL 的通用事务、锁或并发控制设计；
- GitHub REST API、Git 引用更新与分支 lease；
- 无法稳定识别目标对象或目标状态的外部副作用；
- Orca、Provider 与本地文件系统的错误恢复；
- 自动重试器、消息队列或分布式事务平台的选型。
