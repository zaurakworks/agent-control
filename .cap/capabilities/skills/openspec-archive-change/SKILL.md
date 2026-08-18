---
name: openspec-archive-change
description: 完成并归档已实施的 OpenSpec change，同时按项目策略更新主规格。用户明确要求归档某个 change 时使用；先检查工件、任务、规格同步和验证状态。
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: 仅兼容 OpenSpec CLI 1.9.0；升级 CLI 时必须复核本合同
source: @fission-ai/openspec 1.9.0 openspec-archive-change 的中文项目内适配
---

# OpenSpec Archive Change

## 流程

1. 确定活动 change；歧义时运行 `openspec list --json` 让用户选择。若选择注册 store，保持 `--store <id>`。
2. 可先读取归档指导：
   ```bash
   openspec instructions archive --change "<name>" --json
   ```
   该查询只提供附加指导；查询失败不得掩盖后续真实校验结果。
3. 运行 `openspec status --change "<name>" --json`，读取 schema、artifact 状态、任务完成数、`changeRoot` 和 action context。
4. 重新读取 planning artifacts 和 tasks。存在未完成工件、未勾选任务或未解决验证失败时，准确列出；除非用户明确接受规范允许的警告，否则不归档。
5. 默认让 CLI 在归档时更新主规格并校验：
   ```bash
   openspec archive "<name>" --yes --json
   ```
   只有 change 明确属于无规格变化的 tooling/docs 并经用户授权时，才使用 `--skip-specs`；不得使用 `--no-validate` 逃避失败。
6. 检查命令返回、归档目标和主规格结果，再运行适用的 strict validation。确认活动 change 已消失且归档目录包含完整工件。
7. 报告 change、schema、归档位置、同步的 specs、验证结果和任何警告。

## Guardrails

- Archive 是显式终态操作；不得从 Explore、Proposal、Update 或 Apply 自动进入。
- 不手工伪造完成日期、重复日期前缀或覆盖已有 archive；交给 CLI 检测冲突。
- 归档失败时保持原 change 可恢复，报告实际错误，不移动部分文件冒充成功。
