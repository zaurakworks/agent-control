---
name: openspec-propose
description: 为已明确的变更建立完整 OpenSpec 规划包，包括 proposal、delta specs、design 和 tasks。用户要求创建 Proposal 或把讨论结论正式化时使用；只授权规划，完成工件后必须停止，不得同轮实施。
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: 仅兼容 OpenSpec CLI 1.9.0；升级 CLI 时必须复核本合同
source: @fission-ai/openspec 1.9.0 openspec-propose 的中文项目内适配
---

# OpenSpec Propose

## Planning boundary

本工作流只创建规划工件。即使最初请求包含“实现”或“修复”，触发本 Skill 也只授权规划；工件完成后停止，等待用户新的 Apply 请求。

## 流程

1. 明确意图、可观察范围、兼容性和验收条件。只有会改变这些内容的歧义才询问；其他细节采用保守默认并记录。
2. 从需求派生唯一 kebab-case change 名。若用户选择注册 store，先解析 store，并在后续支持的命令上固定 `--store <id>`。
3. 默认使用项目配置 schema；仅在用户明确指定时增加 `--schema`：
   ```bash
   openspec new change "<name>"
   ```
   禁止手工创建 change 目录；CLI scaffold 必须生成 `.openspec.yaml`。
4. 运行：
   ```bash
   openspec status --change "<name>" --json
   ```
   使用返回的 `applyRequires`、artifact 依赖边、`planningHome`、`changeRoot` 和路径，不硬编码工件集合或目录。
5. 建立 todo，按依赖拓扑处理每个 `ready` 工件：
   ```bash
   openspec instructions "<artifact-id>" --change "<name>" --json
   ```
   - 重新读取所有 completed dependency 文件；
   - 遵循返回的 `context`、`rules`、`template` 和 `instruction`，但不把约束原文复制进工件；
   - 写入 `resolvedOutputPath`；glob 输出按 instruction 选择具体路径；
   - 每完成一个工件立即重跑 status。
6. 一直完成 `applyRequires` 及其传递依赖所覆盖的全部规划工件，而不是只生成 proposal。
7. 运行 change 的 strict validation；失败则修正规划工件，不通过抑制校验完成。
8. 报告 change 名、schema、创建的工件、验证结果和明确的下一步 `openspec-apply-change`，然后停止。

## Guardrails

- 不修改应用代码、测试、运行时声明或发布资产。
- 不猜测路径；以 CLI JSON 返回值为准。
- 不在同一响应中自动 Apply、Sync 或 Archive。
- 意图尚未明确时不得创建 change。
