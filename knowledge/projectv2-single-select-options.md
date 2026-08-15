# K7：ProjectV2 单选字段选项修改是全量替换

> 状态：正式当前公共知识。
> 最近核验：2026-08-11。
> 适用对象：GitHub.com GraphQL API 的 `updateProjectV2Field` 与 `updateProjectV2ItemFieldValue`；ProjectV2 单选字段。
> 环境：GitHub.com 托管服务；以官方 GraphQL 参考页、在线 schema introspection 与一次真实事故回执交叉核验。
> 版本边界：托管服务没有可固定的产品版本号；GraphQL schema、官方说明或实测行为变化即为失效信号。

## 回答的问题与价值门

给 ProjectV2 单选字段新增、改名或调整选项时，`updateProjectV2Field` 的 `singleSelectOptions` 是增量补丁，还是完整选项集？怎样避免既有选项及条目取值被意外移除？这项语义是否也约束 `updateProjectV2ItemFieldValue`？

本仓经营观察面曾因误把完整选项集当成增量补丁，造成 40 个条目的 Status 取值同时被清空，并需要依据快照与上下文逐项重建。以后每次修改 ProjectV2 单选字段定义都会复用本结论；它还能长期解释该事故及防复发要求，因此通过价值门。

## 可直接复用的结论

1. `updateProjectV2Field` 的 `singleSelectOptions` 是**全量替换输入**：省略或传入空输入时，GitHub 忽略这一项；一旦提供非空列表，列表就覆盖字段的全部既有选项，而不是只追加或修改列出的选项。
2. 任何涉及 `singleSelectOptions` 的字段定义修改都必须先读取完整既有选项，再把**全部既有选项及其原始 `id`** 一并传回；只写名称、颜色和说明不能保留选项身份。未列出的既有选项会被删除；既有选项即使同名，漏传 `id` 也会失去原身份。使用被删除身份的条目字段值随之被清空。
3. 新增选项没有既有 `id`，只为新选项提供 `name`、`color` 和 `description`；修改既有选项时则保留其 `id`，并在完整列表内更新目标属性。写入后重新读取字段选项，并检查受影响条目的空值数量。

安全顺序固定为：

```text
读取字段及全部 options { id name color description }
→ 在本地完整列表上作目标修改
→ 每个既有选项保留原 id，新选项省略 id
→ 一次性提交完整 singleSelectOptions
→ 回读字段定义并核对条目取值
```

## 错误调用与正确调用

以下示例假设字段当前恰有「收件箱」和「进行中」两个选项，现在要新增「长期」。示例 ID 是占位值；实际调用必须使用刚从目标字段读取的 ID。

### 错误：只提交新增选项

```graphql
mutation AddLongTermWrong($fieldId: ID!) {
  updateProjectV2Field(
    input: {
      fieldId: $fieldId
      singleSelectOptions: [
        {
          name: "长期"
          color: PURPLE
          description: "需要持续维护的长期事项"
        }
      ]
    }
  ) {
    projectV2Field {
      ... on ProjectV2SingleSelectField {
        options { id name }
      }
    }
  }
}
```

这个调用不是“新增一个选项”，而是把完整选项集改成只剩「长期」；原有两个选项被删除，引用其身份的条目取值被清空。

### 正确：提交全部既有选项及其 ID，再加入新选项

```graphql
mutation AddLongTermSafely($fieldId: ID!) {
  updateProjectV2Field(
    input: {
      fieldId: $fieldId
      singleSelectOptions: [
        {
          id: "option_inbox"
          name: "收件箱"
          color: GRAY
          description: "尚未进入正式执行的事项"
        }
        {
          id: "option_in_progress"
          name: "进行中"
          color: YELLOW
          description: "正在推进的事项"
        }
        {
          name: "长期"
          color: PURPLE
          description: "需要持续维护的长期事项"
        }
      ]
    }
  ) {
    projectV2Field {
      ... on ProjectV2SingleSelectField {
        options { id name color description }
      }
    }
  }
}
```

真实字段若有更多既有选项，正确调用必须把它们全部列入；示例中的两个既有选项不能被误读成数量上限。

## 适用边界

- 本包约束的是**字段定义修改**：`updateProjectV2Field` 改变选项集本身，`singleSelectOptions` 因而采用全量替换语义。
- `updateProjectV2ItemFieldValue` 修改的是**一个项目条目的字段取值**。它通过 `value: { singleSelectOptionId: $optionId }` 选择已经存在的选项，不改写字段定义，也不要求提交完整选项集；本包所述全量替换风险不适用于这一条目写入操作。
- GitHub 当前对 `multiSelectOptions` 给出相似的覆盖说明，但本包只准入经过本次证据链核验的单选字段结论；多选字段、迭代字段、项目设置界面和 GitHub Enterprise Server 均需按各自对象另行核验。

## 第一方来源与证据映射

1. GitHub 官方 [Projects GraphQL 参考](https://docs.github.com/en/graphql/reference/projects#updateprojectv2fieldinput) 明确说明：`singleSelectOptions` 的非空输入会覆盖既有选项，局部修改前应先读取既有选项；同页的 [`ProjectV2SingleSelectFieldOptionInput`](https://docs.github.com/en/graphql/reference/projects#projectv2singleselectfieldoptioninput) 说明，更新时携带既有选项 `id` 才能保留其身份并避免条目字段值被清空。核验日期：2026-08-11。
2. GitHub 在线 GraphQL schema introspection 于 2026-08-11 返回与官方参考相同的两段字段说明，并将 `updateProjectV2ItemFieldValue` 明确建模为 `projectId + itemId + fieldId + value` 的条目写入。
3. 关联 [#44](https://github.com/Eridanus117/agent-control/issues/44)：[事故与恢复回执](https://github.com/Eridanus117/agent-control/issues/44#issuecomment-5256000767) 记录了真实结果——未携带六个既有选项 ID 后，40 个条目的 Status 取值被清空；随后依据已完结 Issue、维护批快照和协调上下文完成 40/40 重建，复核时零空值。该回执同时提供事故证据与恢复证据。

## 八项可信门逐项判定

本包的三条可复用结论——全量替换、既有 ID 保持身份、条目写入不改字段定义——共享同一证据链；逐项判定如下。

| 可信门 | 判定 | 依据 |
| --- | --- | --- |
| 1. 明确回答的问题 | 通过 | 问题限定为 GitHub.com ProjectV2 单选字段的定义修改、身份保留与条目写入边界。 |
| 2. 可直接使用的结论和必要解释 | 通过 | 给出全量替换结论、安全顺序、错误／正确 GraphQL 对照及写后核验要求。 |
| 3. 第一方来源或可重复验证过程 | 通过 | GitHub 官方参考、在线 schema introspection 与真实事故／恢复回执相互印证。 |
| 4. 对象、版本、环境和核验时间 | 通过 | 对象与环境限定为 GitHub.com GraphQL API；托管服务无固定版本号；最近核验为 2026-08-11。 |
| 5. 例外、仍未知内容和不能推出的结论 | 通过 | 明确区分字段定义与条目取值，并排除多选、迭代、界面操作及 GitHub Enterprise Server 的直接泛化。 |
| 6. 明确的失效条件 | 通过 | 下节列出官方说明、在线 schema、实测行为和接口形态变化四类失效信号。 |
| 7. 下次最少复核步骤 | 通过 | 只需复查官方两段说明和在线 schema；发生变化时才进入隔离样本验证。 |
| 8. 人容易理解、Agent 足以复用的表达 | 通过 | 中文正文自足，给出可执行顺序、最小 GraphQL 对照、证据映射与清晰边界。 |

## 例外、未知和不能推出的结论

- 官方说明把空输入定义为忽略；全量替换风险发生在提供非空 `singleSelectOptions` 时。本包没有分别实测省略、`null` 与空列表在所有客户端封装中的序列化差异。
- 选项名称相同不等于身份相同；本包只把官方声明的 `id` 视为身份保持依据。
- 事故证明删除选项会清空引用该身份的条目值，但不能推出所有字段定义改动都会清空值；保留原 `id` 的既有选项不属于该事故路径。
- 本包没有证明平台提供通用撤销能力。事故中的恢复依赖既有状态来源重建，不能把“本次恢复成功”当成破坏性写入可轻易回退的保证。
- `updateProjectV2ItemFieldValue` 不受选项集全量替换语义约束，不表示它没有权限、字段类型、选项有效性或并发方面的其他失败条件。

## 失效条件

出现以下任一情况时，相关结论立即停止直接复用，重新核验前只作为历史证据：

1. GitHub 官方参考不再说明非空 `singleSelectOptions` 覆盖既有选项，或不再要求通过 `id` 保留选项身份；
2. GitHub.com 在线 schema 的字段说明或输入类型发生变化；
3. 授权的隔离样本显示保留完整列表与既有 ID 后仍清空条目值，或漏列既有选项后不再删除该选项；
4. GitHub 提供独立的增量新增／修改选项接口，任务改用该接口；
5. 任务对象变为 GitHub Enterprise Server、项目设置界面或其他未核验环境。

## 下次最少复核步骤

1. 打开 GitHub 官方 Projects GraphQL 参考，只检查 `UpdateProjectV2FieldInput.singleSelectOptions` 是否仍写明“非空输入覆盖既有选项、局部更新前读取既有选项”。
2. 在同页检查 `ProjectV2SingleSelectFieldOptionInput.id` 是否仍写明“更新时保留选项身份、避免条目字段值被清空”。
3. 用只读 schema introspection 查询上述两个输入字段，并确认 `UpdateProjectV2ItemFieldValueInput` 仍是条目级 `projectId + itemId + fieldId + value` 写入。
4. 三处一致时继续复用；任一处变化时先让受影响结论退出当前知识。只有确有必要且取得明确写入授权时，才在可丢弃的隔离 Project 中验证，不以经营观察面或其他真实项目作探测对象。

## 不适用范围

- ProjectV2 多选、迭代及其他字段类型的定义修改；
- GitHub Enterprise Server 的版本差异；
- 项目设置界面的内部调用语义；
- ProjectV2 权限、速率限制、并发控制和通用备份方案；
- 经营观察面的字段设计与条目分类规则。
