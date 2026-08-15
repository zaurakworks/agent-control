# Code Review: 743a315

## Commit Information

- Hash: `743a315ad5c8261d2fbaff8b16994c4bf29c8cac`
- Subject: `增加入口单一真源生成与校验工具`
- Author: `eridanus <maodingxuan@foxmail.com>`
- Date: `2026-08-11T10:39:54-04:00`

## Changes Summary

```text
 scripts/entry_sync/README.md            |  21 ++
 scripts/entry_sync/__init__.py          |  27 ++
 scripts/entry_sync/__main__.py          | 136 ++++++++++
 scripts/entry_sync/core.py              | 338 ++++++++++++++++++++++++
 scripts/entry_sync/targets.json         | 175 ++++++++++++
 scripts/test_federated_entry.py         | 199 ++++----------
 tests/test_entry_sync.py                | 239 +++++++++++++++++
 tests/test_federated_entry_validator.py |  95 +++----
 8 files changed, 1032 insertions(+), 198 deletions(-)
```

## Findings

### P1: fenced code block 内的 Markdown 示例会被当成真实章节边界并静默截断投影

- Location: `scripts/entry_sync/core.py:14`（`HEADING_PATTERN`）与 `scripts/entry_sync/core.py:148`（`find_markdown_section`）
- Category: Correctness
- Impact: 章节扫描对全文逐行应用标题正则，不维护 Markdown fence 状态。只要某个被镜像的入口章节加入合法的反引号或波浪线代码围栏，并在围栏内展示同级或更高级 ATX 标题（例如 `## Example`），扫描器就会把它当成下一真实章节，导致源章节在围栏开头处结束。只读探针以 `~~~text` 围栏复现，`find_markdown_section(..., "Shared", 2)` 只返回了 `'## Shared\n\n~~~text\n'`，围栏余下内容和后续规则全部丢失。该错误不会主动报错；`generate --write-repository` 会写出未闭合围栏和缺失规则，而后续 `check` 又使用同一个错误解析器生成 expected，因此可能把这个错误结果视为一致。
- Recommendation: 使用能识别 fenced code block 的 Markdown token/parser，或实现明确的 fence-aware ATX 扫描器；至少补 backtick fence、tilde fence、围栏内同级/高层标题、标题末尾字面 `#` 的回归用例，并验证生成结果完整保留正文。

### P2: 仓内三个目标的写入不是原子的，失败会留下截断文件或半同步批次

- Location: `scripts/entry_sync/__main__.py:70` 与 `scripts/entry_sync/__main__.py:83`
- Category: Error handling
- Impact: `run_generate` 先逐个直接 `write_bytes` 写 staging 文件，再在 `--write-repository` 路径逐个直接写仓内目标。虽然所有投影已先在内存中生成，但写入阶段没有临时同目录文件、原子替换、回滚或失败后的最终一致性检查；Windows 文件锁、权限变化、磁盘错误或进程中断发生在第二/第三个仓内目标时，会使早先目标已经更新、后续目标仍旧，甚至把当前正在写的入口截断。这个命令的核心服务目标正是消除多副本漂移，因此部分失败状态应由工具自身收口，而不应依赖操作者事后发现。
- Recommendation: 对每个目标先写同目录临时文件并用 `os.replace` 原子替换；在批次层保留原始字节并在任一替换失败时回滚已替换目标，或采用可验证的事务式两阶段写入。捕获并归一化 `OSError`，成功返回前再运行同一批次的内存/磁盘一致性复核。

## Category Notes

- Correctness: 当前六项目标在现有入口正文上生成正确；发现 1 个对合法 Markdown 输入会静默截断的边界错误。
- Tests: 新增测试覆盖章节选择、换行规范化、目标路径越界、差异退出码和重复 ID；未覆盖 fenced code block、真实 CLI 写入、写入失败或回滚。
- Mock boundaries: 测试主要使用真实临时文件，仅对 `repository_root` 和 `Path.home` 做窄替换，未发现不当内部模块 mock。
- Error handling: 读取与配置解析多数转换为 `EntrySyncError`；直接写文件的 `OSError` 仍会以 traceback 退出，且可能留下部分状态。
- Security/privacy: 路径包含检查会拒绝 `..` 越界；未发现凭据、日志敏感信息或远端写入。
- Data/migrations: 无数据库或 schema migration；配置版本为 1。
- Performance: 文件规模小、处理为线性扫描，未见实质性能风险。
- Maintainability: 模块分层和数据类清晰；`preserve_unselected` 字段当前未被代码读取，属于后续 schema 明确化点，但本次未单列 finding。

## Verification

- Ran: `gh pr view 47 --json ...`，确认 PR 已合并、单提交 head 为 `743a315...`、merge commit 为 `206c371...`，且远端没有 review、comment 或 check rollup。
- Ran: `gh pr diff 47 --patch`，审查 8 个变更文件、1032 additions / 198 deletions 的合并 patch；再以 `git show 743a315:<path>` 补齐被终端截断的文件正文。
- Ran: `python -B -m unittest discover -s tests -p test*.py`，19 项通过。
- Ran: `python -B -m scripts.entry_sync check --scope repository`，`repository-source`、`repository-readme`、`repository-agents` 三项通过。
- Ran: fence 定向只读探针，确认围栏内 `## Example` 会提前终止 `## Shared` 的选择结果。
- Not run: `generate --write-repository`，因为本任务禁止修改仓库受跟踪文件；installed scope check，因其验证当前机器安装态而非 PR 代码；Ruff/lint，仓库未提供相关配置且 PR 明确记录环境未安装 Ruff。
- Gap: 当前 `main` 已包含 PR #47 之后的提交，并且后续提交修改了 federated validator 及其测试；本次没有创建隔离 checkout，所以整套 19 项测试不是对 merge commit 的完全冻结重放。`scripts/entry_sync/` 与 `tests/test_entry_sync.py` 自 PR #47 后未变，核心新增模块与其单元测试仍与被审提交一致。

