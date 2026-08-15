# Issue 创建命令

这条命令把 `objective-to-issues` 第三节的共享创建骨架变成失败即停的执行入口。它先完成本地正文与分类校验，再预检仓库 label、Project 和可选父 Issue；Issue 一旦创建，后续任一步失败都会输出已有 Issue、已完成步骤和失败步骤，并明确要求修复同一个对象，不会自动重建。

```text
python tools/issue_create/issue_create.py \
  --type 调研 --domain 横向 \
  --title "当前可做事项枚举、排期与归属" \
  --body-file tools/issue_create/example-body.md \
  --status "In Progress" \
  --parent 287 \
  --repo Eridanus117/agent-control
```

`--type` 只接受 `目标|诉求|交付|实验|调研|摩擦|方案`，并从 Skill 表实时取得标题前缀、类型 label、经营节点与是否使用执行状态。`--domain` 只接受 `总目标|知识|长程工作|思考方法|协同协作|资源运营|横向`，对应已存在的 `领域/` label。`--title` 只写短题，不能再写 `调研：`、`清单：` 等任何前缀。

执行状态适用的类型必须传 `--status`，不适用的类型禁止传。参数可以是 Project 当前选项的精确名称；为匹配中文调用形状，也接受 `待办`、`进行中`、`完成`，它们分别解析到当前默认选项 `Todo`、`In Progress`、`Done`。目标、诉求和摩擦不写 `Status`，且回读时要求该字段留空。

## 规则源与默认值

类型映射没有在代码中复制。命令运行时按以下顺序读取 `objective-to-issues/SKILL.md`：

1. `--skill-file`；
2. 环境变量 `OBJECTIVE_TO_ISSUES_SKILL`；
3. `AGENT_PLUGINS_ROOT` 下的标准相对路径；
4. `~/workspace/agent-plugins/plugins/github-collaboration/skills/objective-to-issues/SKILL.md`；
5. 已安装的 Codex `agent-plugins` 缓存。

找不到文件、表不是完整七行，或前缀／label 与同一行类型不一致时，命令在创建前停止。若以后 Skill 的表结构发生有意变化，需要同步更新本目录的 Markdown 表解析器和测试；不得在代码里补一份映射绕过规则源。

默认仓库是当前尚未完成转移的 `Eridanus117/agent-control`，可用 `--repo OWNER/NAME` 覆盖，仓名没有写进 GraphQL 查询。默认 Project 是负责人在 2026-08-14 指定的新运营台：`zaurakworks` Project 1，节点 ID `PVT_kwHOEua8Pc4BgZbR`。旧 `Eridanus117` Project 3 仍供协调者做账，但不是这条创建入口的默认观察面；确有另一份当前权威时可显式传 `--project-id`，命令仍会先从远端读取其 `Status` 字段与选项。

## 硬校验与部分成功

创建前会拒绝：非法类型／领域、手写标题前缀、缺少三个必需二级标题、正文中的 GitHub 英文关闭关键词（包含否定式）、缺失的两维 label、不可读的 Project、缺失的 `Status` 选项及不存在的父 Issue。正文关键词闭集是 GitHub 支持的 `close/closes/closed`、`fix/fixes/fixed`、`resolve/resolves/resolved`，不依赖关键词后是否紧跟 Issue 引用。

创建后必经 `addProjectV2ItemById`；适用时只用 `updateProjectV2ItemFieldValue` 设置 `Status`。`--parent` 只调用带 `GraphQL-Features: sub_issues` 请求头的 `addSubIssue`，正文链接不会被当成关系。最后从远端重新读取正文、标题、两维 label、Project 条目、`Status` 值和原生父级并逐项比较。Project 条目按 `addProjectV2ItemById` 返回的稳定 item ID 直接回读，同时核对它的 `content` 确为新 Issue；这是跨仓 Project 的可靠读面，因为 GitHub 当前不会总在 `Issue.projectItems` 连接中返回另一所有者的 Project 条目。

退出码 `2` 表示创建前失败，没有新对象；退出码 `3` 表示 Issue 已存在但后续批次不完整，标准错误中的 JSON 是修复同一对象的恢复依据；退出码 `0` 才表示全部回读项一致。命令不重试远端写入，也不清理部分成功对象。

## 自检

```text
python -m unittest discover -s tools/issue_create/tests -v
python tools/issue_create/issue_create.py --type 非法 --domain 横向 --title "拒绝样本" --body-file tools/issue_create/example-body.md
```

单测覆盖 Skill 表解析、手写前缀、三节正文、九个关闭关键词、执行状态适用性、完整写入顺序、远端逐项回读与部分成功停止。真实 GitHub 验证仍是发布前必需步骤；单测不能替代它。
