# 影子对照 #49：外部侧 A（code-quality 对 PR #47 的只读审查）

## 结论总览

本产物使用 `code-quality` Plugin 的 `code-quality` Skill 0.1.0，以 `review PR #47` 模式审查已合并 diff；未执行 cleanup，未修改代码、配置、分支或 GitHub 远端。审查得到 **P0 0、P1 1、P2 1**：主要风险是 Markdown 章节扫描器会把 fenced code block 内的示例标题当作真实边界并静默截断入口投影；次要风险是 `--write-repository` 的多文件直写缺少原子性与批次失败收口。现有输入上的 19 项测试和仓内三目标只读检查均通过，但没有冻结重放 merge commit 的完整测试环境，也没有执行写模式、installed scope 或 Ruff。

## 审查身份与范围

- 服务目标：为 `agent-control#49` 影子对照提供外部插件侧代码审查产物。
- Review operation: `review PR #47`；明确未进入 `cleanup`。
- Repository: `Eridanus117/agent-control`
- PR: `#47 S3：增加 D5 入口单一真源生成器`
- Base/head: `main` ← `743a315ad5c8261d2fbaff8b16994c4bf29c8cac`
- Merge commit: `206c371677d57bcfd11d531a7d787ff17859db05`
- Diff source: `gh pr view 47` + `gh pr diff 47 --patch`；本地 `git show` 只用于补齐显示截断与定位行号。
- Changed surface: `scripts/entry_sync/`、`scripts/test_federated_entry.py`、`tests/test_entry_sync.py`、`tests/test_federated_entry_validator.py`，合计 8 文件、1032 additions、198 deletions。
- Read-only boundary: GitHub 只读；未评论、未改标签/正文/分支；仓库受跟踪文件零修改。唯一任务产物写在被忽略的 `codex-work/`。

## 项目特定审查基准

读取了 `README.md`、`AGENTS.md`、`CLAUDE.md`、`authority/00-map.md`、`scripts/entry_sync/README.md`、远端 Issue #49 与 #44 合同以及 PR #47 正文。适用于本 diff 的本地约束是：持久程序只允许 Go/Python/TypeScript/Rust；共享入口正文以 `entrypoints/agent-system.md` 为单一真源；README、AGENTS 与三个安装入口由声明式目标生成/校验；审查应优先检查入口内容完整性、路径包含、错误传播、部分写入和真实测试边界。

## Findings

### P0

无。

### P1 — fenced code block 内的 Markdown 示例会被当成真实章节边界并静默截断投影

- Location: `scripts/entry_sync/core.py:14`（`HEADING_PATTERN`）与 `scripts/entry_sync/core.py:148`（`find_markdown_section`）
- Category: Correctness
- 事实：扫描器对规范化后的全文直接应用 ATX 标题正则，再以“下一个同级或更高级标题”确定章节结束位置；它没有跟踪反引号/波浪线 fenced code block。定向探针把合法的 `~~~text` 围栏和围栏内 `## Example` 放在 `## Shared` 中，函数只返回 `'## Shared\n\n~~~text\n'`。
- 影响判断：入口正文以后只要加入展示 Markdown 的常见代码示例，生成器就可能输出未闭合围栏并删除该示例之后的真实 Agent 规则。该路径不报错，且 `check` 与 `generate` 共享同一解析器，错误结果写入后仍可能自洽为“全绿”；这是会破坏核心工作流的 P1，而不只是格式偏好。
- 最小可信修复：改用可识别 fence 的 Markdown token/parser，或实现明确的 fence-aware ATX 扫描；加入 backtick/tilde fence、围栏内同级/高层标题、标题末尾字面 `#` 的回归测试，并断言完整正文保留。

### P2 — 仓内三个目标的写入不是原子的，失败会留下截断文件或半同步批次

- Location: `scripts/entry_sync/__main__.py:70` 与 `scripts/entry_sync/__main__.py:83`
- Category: Error handling
- 事实：staging 和仓内目标都通过循环中的 `Path.write_bytes` 直接逐个写入；写入期没有临时同目录文件、原子替换、回滚，也没有成功返回前的最终磁盘复核。写入 `OSError` 亦不在 `EntrySyncError` 收口范围内。
- 影响判断：Windows 文件锁、权限变化、磁盘错误或进程中断可能使当前文件截断，或使 README 已更新而 AGENTS 仍旧。工具的服务目标正是消除多副本漂移；失败后重新运行虽可恢复，却依赖操作者先发现，属于 P2 可靠性缺口。
- 最小可信修复：每个目标先写同目录临时文件并用 `os.replace` 原子替换；批次保留原始字节，在任一替换失败时回滚已替换目标，或提供等价的两阶段写入；统一捕获 `OSError`，成功返回前复核所有仓内目标。

## Findings 计数

| Severity | Count |
| --- | ---: |
| P0 | 0 |
| P1 | 1 |
| P2 | 1 |

| Category | Count |
| --- | ---: |
| Correctness | 1 |
| Tests | 0 |
| Mock boundaries | 0 |
| Error handling | 1 |
| Security/privacy | 0 |
| Data/migrations | 0 |
| Performance | 0 |
| Maintainability | 0 |

每个根问题只计一次；测试缺口作为相应 finding 的证据与验证缺口记录，没有重复计数。

## 未单列为 finding 的观察

- 路径解析会拒绝绝对的 target 相对路径和 `..` 越界，当前默认六个目标均位于声明根内。
- installed copy 目标在生成阶段不读取/写入用户目录，符合 PR 的“只生成 staging，不安装”边界。
- overlay 会保留未选章节；配置中的 `preserve_unselected: true` 当前没有代码读取或 schema 验证，语义实际上由 `strategy == "overlay"` 固定。它是 schema 清晰度后续点，但当前两个声明都为 true，未形成独立运行故障，故未计入 P2。
- 测试使用真实临时文件验证核心 IO，仅窄 mock `repository_root`/`Path.home`；未发现过度 mock 或只断言 mock 调用的问题。
- PR #47 远端没有 review、comment、review decision 或 CI/check rollup；因此“已合并”本身不提供独立当前-head 审查证据。

## Verification

### 已运行

- `gh pr view 47 --json ...`：确认 MERGED、单提交 head `743a315...`、merge commit `206c371...`、8 个变更文件。
- `gh pr diff 47 --patch`：读取合并 patch；对被终端输出上限截断的正文以 `git show 743a315:<path>` 只读补齐。
- `python -B -m unittest discover -s tests -p test*.py`：**19 tests passed**。
- `python -B -m scripts.entry_sync check --scope repository`：`repository-source`、`repository-readme`、`repository-agents` **3/3 OK**。
- fenced-heading 定向只读探针：确认围栏内 `## Example` 使所选章节在围栏开头提前结束。
- `git diff 743a315..HEAD -- scripts/entry_sync tests/test_entry_sync.py`：核心模块与其专属单测在 PR #47 后未变化。

### 未运行与验证缺口

- 未运行 `generate --write-repository`：合同禁止修改受跟踪文件，因而真实多文件写入、权限失败和回滚路径没有端到端验证。
- 未运行 installed scope：它主要验证当前机器的安装副本状态，不是 PR 合并 diff 的代码质量；PR 自身已记录当时三份安装副本因 S1 变更而预期 stale。
- 未运行 Ruff/lint：仓库没有发现 lint/typecheck 配置，PR 也明确记录环境未安装 Ruff；本任务不授权安装依赖。
- 未在隔离 checkout 重放 merge commit：当前 `main` 已有后续提交，并修改了 federated validator 及其测试。19 项结果不是对 `206c371` 的完全冻结重放；不过 `scripts/entry_sync/` 与 `tests/test_entry_sync.py` 自 PR #47 后未变，新增核心模块和专属单测仍与审查 head 一致。
- 现有测试未覆盖 fenced code block/字面尾随 `#`、真实 CLI 写入、单文件中断、批次部分失败/回滚、installed 环境变量缺失等路径。

## Open questions

- 当前文档没有声明入口源文件只允许“无 fenced code block 的 Markdown 子集”。若这是有意限制，应在 `scripts/entry_sync/README.md` 和配置 schema 中显式写明并在写入前拒绝不支持的输入；否则应修复解析器。
- `preserve_unselected` 是仅供人阅读的声明，还是未来应有 `false` 语义的配置字段？当前实现静默忽略该字段。

## 外部侧交付摘要

- Findings: **P0 0 / P1 1 / P2 1**。
- 当前证据：现有输入下单测与 repository scope 检查通过；未发现路径越界、敏感信息或不当 mock。
- 核心未决：Markdown fence 解析应在后续写入口规则前修复；多文件写路径需要原子/失败收口；验证缺口如上，不把本次只读审查表述为修复或重新验收。

