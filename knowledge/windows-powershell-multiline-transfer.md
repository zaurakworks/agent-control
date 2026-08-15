# K17：Windows 下 PowerShell／GitHub CLI 多行 Markdown 传输边界

> 状态：正式当前公共知识；由 [`knowledge/README.md`](./README.md) 作为唯一入口发现与直接复用。
> 最近核验：2026-08-12。
> 适用对象：Windows 原生 PowerShell 中，经 GitHub CLI 写入或回读 Issue／PR 正文、评论，以及经 Git 写入或回读多行提交说明。
> 环境：Windows 11 10.0.26200；PowerShell 7.6.3；GitHub CLI 2.97.0；Git 2.55.0.windows.3；GitHub.com；本仓已认证账号。
> 版本边界：PowerShell 解析规则、原生命令参数／标准输入传递、GitHub CLI 的 `--body-file` 合同、Git 的 `--file` 合同或 GitHub 字段限制变化，均为失效信号。

## 回答的问题与触发条件

在 Windows 原生 PowerShell 中，怎样把多行 Markdown 可靠地交给 `gh` 或 `git`，避免 `$`、反引号、引号、空行和换行在宿主解析、原生命令参数或回读阶段改变含义？

以下条件同时成立时命中本包：

1. 当前宿主是 Windows 原生 PowerShell；
2. 当前动作通过 `gh` 写 Issue／PR 正文或评论，或通过 `git` 写多行提交说明；
3. 正文跨行，或含 `$`、反引号、代码围栏、引号、空行等 Markdown 敏感内容；
4. 写入后还要比较、替换或逐字复核远端正文。

单行简单文本可以直接作为一个已构造的参数传递；Bash／zsh、浏览器编辑器、直接使用结构化 API 客户端和二进制内容均不在本包范围内。

这项知识具有重复使用价值：GitHub Issue 与 PR 是当前任务合同和审阅面，而[关联 #30（PowerShell 多行正文摩擦）](https://github.com/Eridanus117/agent-control/issues/30)已经记录 2 个事件、3 次失败／修复循环；[关联 #130（知识库覆盖缺口盘点）](https://github.com/Eridanus117/agent-control/issues/130#issuecomment-5262242274)把它判为现有 K1–K16 唯一达到新增内容候选强度的覆盖缺口。

## 最短可靠写法：六条

### 1. 先用单引号字面 here-string 构造正文

单引号 here-string 不展开变量，也不把反引号当 PowerShell 转义符；开始标记后立即换行，结束标记单独占一行并从第 1 列开始。需要插入少量动态值时，先完成字面量正文，再对明确占位符调用 `Replace()`，不要把整段 Markdown 改成双引号 here-string。

````powershell
$body = @'
## 结果

`$name` 保持 Markdown 原文。

```text
$name
```

来源：{{SOURCE_URL}}
'@

$body = $body.Replace('{{SOURCE_URL}}', $sourceUrl)
````

结束标记若缩进，PowerShell 7.6.3 的解析器直接返回 `WhitespaceBeforeHereStringFooter`。同一环境的直接对照还显示：上例内容放进双引号 here-string 后，`$name` 被展开，含 `text` 语言标识的三反引号代码围栏变成含制表转义的 `` `\text``；这与[关联 #30（PowerShell 多行正文摩擦）事件 E01](https://github.com/Eridanus117/agent-control/issues/30#issuecomment-5247792063)的远端格式缺陷一致。PowerShell 官方 [`about_Quoting_Rules`](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_quoting_rules?view=powershell-7.6)说明了 here-string 的首尾格式，以及单引号 here-string 不作变量替换的语义。

### 2. 回读时先取得一个标量字符串

PowerShell 会枚举原生命令的逐行输出。2026-08-12 直接运行 `gh issue view 30 --json body --jq .body`，得到 `System.Object[]`、42 个元素；将其直接用于 `Contains()`、`Substring()` 或换行比较会把“多行正文”误当“对象数组”。精确回读优先保留 JSON，再由 PowerShell 解析字段：

```powershell
$remote = (gh issue view $number --repo $repo --json body | ConvertFrom-Json).body
```

若既有命令已经使用 `--jq .body`，先显式连接：

```powershell
$remote = (gh issue view $number --repo $repo --json body --jq .body) -join "`n"
```

本次对[关联 #30（PowerShell 多行正文摩擦）](https://github.com/Eridanus117/agent-control/issues/30)正文的直接验证中，连接结果与 JSON 标量逐字相等；[事件 E02](https://github.com/Eridanus117/agent-control/issues/30#issuecomment-5247792243)保存了两次把数组当字符串而触发安全检查失败的事故。`-join` 不能证明原始文本是否带末尾换行；末尾换行有语义时使用 JSON 标量路径。

### 3. 比较或写盘前只做一次明确的换行规范化

把 CRLF 与孤立 CR 统一为 LF，并让本地候选与回读标量使用同一规则：

```powershell
$body = $body -replace '\r\n?', "`n"
$remote = $remote -replace '\r\n?', "`n"
```

不要在对象数组、`Out-String` 结果和原始字符串之间混用 `Contains()`、`Substring()` 或相等比较；`Out-String` 还会引入面向显示的换行。该动作直接来自[关联 #30（PowerShell 多行正文摩擦）事件 E02](https://github.com/Eridanus117/agent-control/issues/30#issuecomment-5247792243)的恢复过程。它只规范化换行，不修改行尾空格、BOM 或正文内容。

### 4. 用 UTF-8 无 BOM 的临时文件建立清晰的字节边界

复杂正文不要继续穿过 `PowerShell → Windows 原生命令行 → CLI flag` 的内联引用层。先把已经构造、规范化的标量正文写到精确临时路径；显式编码同时避免 Windows PowerShell 与 PowerShell 7 默认编码差异：

```powershell
$tmp = New-TemporaryFile
try {
    $utf8 = [Text.UTF8Encoding]::new($false, $true)
    [IO.File]::WriteAllText($tmp.FullName, $body, $utf8)

    # 下一条命令在这里使用 $tmp.FullName
}
finally {
    Remove-Item -LiteralPath $tmp.FullName
}
```

`.NET` 官方 [`UTF8Encoding(Boolean, Boolean)`](https://learn.microsoft.com/en-us/dotnet/api/system.text.utf8encoding.-ctor)说明第一个 `false` 使编码器不提供 BOM，第二个 `true` 使无效字符触发异常；[`File.WriteAllText`](https://learn.microsoft.com/en-us/dotnet/api/system.io.file.writealltext?view=net-10.0)提供字符串到文件的明确写入边界。临时文件只用于本次命令，不沉淀为 PowerShell 产品脚本。

### 5. 正文和提交说明优先使用文件参数

把上一条的命令位置替换为对应写入动作：

| 目标 | 可靠参数形状 | 当前一手合同 |
| --- | --- | --- |
| 新建／编辑 Issue 正文 | `gh issue create ... --body-file $tmp.FullName`／`gh issue edit $number ... --body-file $tmp.FullName` | GitHub CLI 官方 [`gh issue create`](https://cli.github.com/manual/gh_issue_create) 与 [`gh issue edit`](https://cli.github.com/manual/gh_issue_edit) |
| 新建／编辑 PR 正文 | `gh pr create ... --body-file $tmp.FullName`／`gh pr edit $number ... --body-file $tmp.FullName` | GitHub CLI 官方 [`gh pr create`](https://cli.github.com/manual/gh_pr_create) 与 [`gh pr edit`](https://cli.github.com/manual/gh_pr_edit) |
| Issue／PR 评论 | `gh issue comment $number ... --body-file $tmp.FullName`／`gh pr comment $number ... --body-file $tmp.FullName` | GitHub CLI 官方 [`gh issue comment`](https://cli.github.com/manual/gh_issue_comment) 与 [`gh pr comment`](https://cli.github.com/manual/gh_pr_comment) |
| 多行提交说明 | `git commit --cleanup=verbatim --file $tmp.FullName` | Git 官方 [`git commit`](https://git-scm.com/docs/git-commit) 的 `-F`／`--file` 与 `--cleanup=verbatim` 合同 |

当前 GitHub CLI 2.97.0 对上表六个 `gh` 动词逐一显示 `--body-file`，并允许以 `-` 读取标准输入。默认仍用真实临时文件：它减少 PowerShell 标准输入编码、自动补换行和多层引用的未知。Git 的 `--cleanup=verbatim` 明确选择不改写提交说明；若团队需要其他 cleanup 规则，应先把它视为提交语义而非传输误差。短文本且已经安全构造为单一变量时，`--body $body` 可以工作；本包推荐文件参数，是为了减少传输层数和正文长度带来的返工，并非声称 `--body` 必然失败。

### 6. 写入回执之后，以目标端正文作最终验收

命令成功只证明客户端收到成功回执。正文、评论或提交说明写入后，重新读取目标端标量，按同一换行规则比较；不相等时停止后续发布动作并保留实际远端状态。

```powershell
$remote = (gh issue view $number --repo $repo --json body | ConvertFrom-Json).body
$remote = $remote -replace '\r\n?', "`n"

if ($remote -cne $body) {
    throw '远端正文与本地候选不一致'
}
```

PR 正文使用 `gh pr view ... --json body`；评论使用返回的稳定评论身份经 GitHub API 回读 `.body`；提交说明使用 `git show -s --format=%B HEAD` 并先连接为一个字符串。关联 [#30（PowerShell 多行正文摩擦）](https://github.com/Eridanus117/agent-control/issues/30)的 E01 由写后复核发现远端格式缺陷，E02 则在写前安全检查与写后复核中守住了远端合同，因此这一步是传输闭环的一部分，而非可省略的展示检查。

## 一段可直接改目标的完整模板

下面模板适合 Issue／PR 正文和评论；只替换目标命令与回读命令，不把正文重新嵌回命令参数。

````powershell
$body = @'
## 总览

包含 `$variable`、反引号与代码围栏的 Markdown。

```text
literal
```
'@

$body = $body -replace '\r\n?', "`n"
$tmp = New-TemporaryFile

try {
    $utf8 = [Text.UTF8Encoding]::new($false, $true)
    [IO.File]::WriteAllText($tmp.FullName, $body, $utf8)
    gh issue edit $number --repo $repo --body-file $tmp.FullName
}
finally {
    Remove-Item -LiteralPath $tmp.FullName
}

$remote = (gh issue view $number --repo $repo --json body | ConvertFrom-Json).body
$remote = $remote -replace '\r\n?', "`n"
if ($remote -cne $body) { throw '远端正文与本地候选不一致' }
````

## 第一方来源与直接验证

1. [关联 #30（PowerShell 多行正文摩擦）](https://github.com/Eridanus117/agent-control/issues/30)及其 E01／E02 评论：保存双引号 here-string 改写 Markdown、原生命令多行输出成为数组、三次失败／修复循环、远端影响和稳定绕过。
2. [关联 #130（知识库覆盖缺口盘点）交付评论](https://github.com/Eridanus117/agent-control/issues/130#issuecomment-5262242274)：在 106 个 Issue、34 个 PR 和 402 条讨论评论的观察窗中，把本主题判为现有包唯一达到新增内容候选强度的缺口；证据上限仍是该窗口样本。
3. 2026-08-12 本 worktree 直接验证：PowerShell 7.6.3 的 indented footer 解析错误为 `WhitespaceBeforeHereStringFooter`；单引号 here-string 保留 `$sample` 与三反引号代码围栏，双引号版本则展开前者并改写后者；`gh --jq .body` 回读为 42 元素 `System.Object[]`，显式连接后与 `ConvertFrom-Json` 得到的 1,305 字符标量逐字相等。
4. 当前命令自带帮助与 GitHub CLI 官方手册：GitHub CLI 2.97.0 的 Issue／PR create、edit、comment 六个动词均提供 `--body-file`；Git 2.55.0.windows.3 提供 `git commit --file`，Git 官方手册定义 `--cleanup=verbatim`。
5. PowerShell、GitHub CLI、Git 与 .NET 的官方文档：分别支持字符串解析、正文文件参数、提交说明文件参数和明确 UTF-8 写盘语义；它们是一手合同，不替代本仓事故对组合边界的直接证据。

## 两道准入门逐项判定

| 准入项 | 判定 | 依据 |
| --- | --- | --- |
| 价值门 | 通过 | GitHub 合同与审阅面反复写入；本仓已有 2 个事件、3 次循环，覆盖盘点将其列为最强新增候选。 |
| 1. 明确回答的问题 | 通过 | 只回答 Windows PowerShell 与 `gh`／`git` 之间的多行 Markdown 传输。 |
| 2. 可直接使用的结论和必要解释 | 通过 | 提供六条清单与一段端到端模板。 |
| 3. 第一方来源或可重复验证过程 | 通过 | 本仓事故、版本匹配的 CLI 帮助、官方文档与可重复解析／类型检查。 |
| 4. 对象、版本、环境和核验时间 | 通过 | 页首记录 Windows、PowerShell、`gh`、Git、GitHub.com 与日期。 |
| 5. 例外、仍未知内容和不能推出的结论 | 通过 | 下节限定外壳、编码、末尾换行、正文规模、标准输入和 API 上限。 |
| 6. 明确的失效条件 | 通过 | 下节列出 PowerShell、CLI flag、编码、字段限制和新反例变化。 |
| 7. 下次最少复核步骤 | 通过 | 只需三个本地解析／类型检查与当前 CLI 帮助核对；不需要向真实合同写探测正文。 |
| 8. 人容易理解、Agent 足以复用的表达 | 通过 | 清单按构造、标量化、规范化、文件边界、写入、回读顺序展开。 |

## 例外、已知失效边界与不能推出的结论

- 直接行为样本限定于 PowerShell 7.6.3、GitHub CLI 2.97.0 与 Git 2.55.0.windows.3；Windows PowerShell 5.1、未来 PowerShell 版本及其他 shell 尚未做同一组直接复现。
- 单引号 here-string 会按设计保留所有 `$` 与反引号；任务确实需要 PowerShell 表达式求值时，应对明确占位符逐个替换。正文若本身含一行从第 1 列开始的 `'@`，该 here-string 边界会提前结束，应改用编辑器或其他明确文件生成路径。
- `-join "`n"` 可以恢复逐行输出之间的 LF，不能凭逐行 stdout 判断末尾换行是否存在；逐字验收优先使用 JSON 标量。
- LF 规范化只处理 `CRLF → LF` 与 `CR → LF`，不处理 BOM、行尾空格、Unicode 规范化或 GitHub 渲染差异。
- `--body-file -` 是当前 GitHub CLI 的官方入口，但本包没有把 PowerShell 标准输入编码和自动补换行纳入默认已验证路径；需要无临时文件路径时，先在非合同对象或纯本地接收端复核精确字节。
- 文件参数减少 PowerShell 与原生命令行的引用和长度风险，不绕过 GitHub 字段大小、API、权限、并发或内容语义限制。
- 本包只证明安全传输和比较，不证明正文内容、授权、引用或关系本身正确；GitHub 远端写入报错后的重试语义仍由 K11 处理。

## 失效条件

出现以下任一情况时，受影响结论停止直接复用并先做最少复核：

1. PowerShell 改变 here-string footer、单／双引号展开、原生命令 stdout 枚举或标准输入编码语义；
2. GitHub CLI 的 Issue／PR create、edit、comment 任一动词移除或改变 `--body-file`，或 Git 改变 `git commit --file`；
3. 新的本仓直接样本显示“字面 here-string → UTF-8 文件 → file flag → JSON 标量回读”仍会改变正文；
4. 任务需要 Windows PowerShell 5.1、跨 shell、超大正文、末尾换行敏感文本、Unicode 规范化或二进制内容；
5. GitHub.com 改变正文／评论字段限制、编码或回读语义。

## 下次最少复核步骤

1. 记录 `$PSVersionTable.PSVersion`、`gh --version` 与 `git --version`；版本未变化且没有命中上面其他信号时，只继续下面两个低成本检查。
2. 用 PowerShell parser 对含两个空格缩进的 `'@` 做只读解析，确认仍返回 footer 错误；再对含 `$sample` 与三反引号代码围栏的单／双引号 here-string 各求值一次，确认字面量与展开边界未变。
3. 对任一已存在的多行 Issue 正文分别运行 `--jq .body` 与 `--json body | ConvertFrom-Json`：确认前者仍为逐行集合，显式连接后与后者标量相等；不为复核创建或修改远端对象。
4. 运行六个 `gh ... --help`，确认 Issue／PR 的 create、edit、comment 仍提供 `--body-file`；运行 `git commit -h`，确认 `--file` 与 `--cleanup` 仍存在。
5. 只有上述检查变化，或自然任务出现新反例时，才在获准的可丢弃对象上做一次文件写入与回读；真实任务合同、负责人评论和正式提交说明不作为探测对象。

## 与既有知识包的边界

- [K2（Orca 受监督派发）](./orca-supervised-dispatch.md)处理 Orca Task／Dispatch、输入提交与终端生命周期；本包只处理正文进入 PowerShell／`gh`／`git` 的文本边界。
- [K4（Plugin 维护）](./claude-plugin-maintenance.md)处理 Plugin 安装、缓存、description 上限和三端验收；本包不涉及 Plugin 生命周期。
- [K5（入口母本同步）](./entry-sync.md)处理入口母本生成、安装与一致性检查；本包不生成入口副本，也不修改同步工具。
- [K6（跨端换行一致性）](./newline-normalized-acceptance.md)回答文件副本验收时为何先规范化换行；本包只在多行正文传输中借用 LF 规范化，不扩展 K6 的文件哈希结论。
- [K11（GraphQL mutation 恢复）](./github-graphql-mutation-recovery.md)处理远端写入报错、部分成功和安全重试；本包处理调用发生前后的字符串构造、文件参数与逐字回读。若 `gh` 返回错误，先完成本包的远端正文回读，再按 K11 判断是否补做。
- GitHub 引用安全、Issue 生命周期、PR 审查与合并授权仍由各自入口和 Skill 承载；本包不会把“正文按字节送达”提升为“合同已正确、交付已验收或产品决定已成立”。
