# Issue 短引用迁移改写器

本工具把 Git 跟踪的 Markdown 中仍依赖当前仓库上下文的 GitHub 短引用，改成指向 `Eridanus117` 老仓的完整链接。默认行为是只读 dry-run；写入必须显式传入 `--apply`。非 Markdown 跟踪文件也会进入残留审计，但不会被写入 Markdown 链接。

```text
python tools/issue_reference_rewrite/issue_reference_rewrite.py
python tools/issue_reference_rewrite/issue_reference_rewrite.py --dry-run
python tools/issue_reference_rewrite/issue_reference_rewrite.py --apply
python -m unittest discover -s tools/issue_reference_rewrite/tests -v
```

脚本通过当前已认证的 `gh` CLI 批量查询 GitHub GraphQL，只有远端实际存在的 Issue 或 PR 才会被改写。PR 同样生成 `/issues/N` 形式的链接，由 GitHub 重定向到 `/pull/N`；不存在的编号和同一语句内出现多个候选仓库的引用进入「需人工判定」，不会被改写。

围栏代码、行内代码、已有 Markdown 链接与原始 URL 都受保护。`work/history/` 和普通 `work/records/` 会纳入改写，因为迁仓后历史材料仍必须指回当时的老仓对象；但由联邦入口验证器要求逐字保真的 `work/records/2026-08-10-federated-session-entry/raw/current-before-migration.md` 保持原样。`tools/ops-metrics/current.*`、`tools/ops-metrics/reports/`、`tools/worker_snapshot/current.*` 和 `tools/worker_snapshot/samples/` 属于运行期或快照产物，也只审计、不改写。
