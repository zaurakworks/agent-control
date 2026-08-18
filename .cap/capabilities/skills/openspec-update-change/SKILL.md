---
name: openspec-update-change
description: 修订已有 OpenSpec change 的现存规划工件，并保持 proposal、specs、design 和 tasks 相互一致。用户补充决定、改变计划或要求一致性检查时使用；不得创建缺失工件或修改应用代码。
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: 仅兼容 OpenSpec CLI 1.9.0；升级 CLI 时必须复核本合同
source: @fission-ai/openspec 1.9.0 openspec-update-change 的中文项目内适配
---

# OpenSpec Update Change

## 流程

1. 从用户输入或会话上下文确定 change。只有一个活动 change 时可选择它；存在歧义时运行 `openspec list --json` 并让用户选择。明确报告正在使用的 change。
2. 若用户选择注册 store，先解析 store，并在后续支持的命令上固定 `--store <id>`。
3. 运行：
   ```bash
   openspec status --change "<name>" --json
   ```
   使用 `artifactPaths.<id>.existingOutputPaths` 定位现存文件。不得把 glob `resolvedOutputPath` 当作文件路径。
4. 读取请求直接涉及的工件及其他全部现存工件。检查任意方向的矛盾、缺口和重复；构建顺序只是阅读顺序，不限制回改早期工件。
5. 逐个说明建议修改和理由。需要实质重写时，先获取对应规则：
   ```bash
   openspec instructions "<artifact-id>" --change "<name>" --json
   ```
6. 用户确认后只修改已经存在的具体文件；每次修改后重新检查其他工件的一致性。
7. 运行 strict validation，并报告修改、拒绝或延期的内容及推荐下一步。

## Guardrails

- 只修改规划工件，永不修改实现代码。
- 不创建尚不存在的 artifact，也不在 glob artifact 下自行增加新文件；缺失工件应交给继续构建流程。
- 若新请求改变了 change 的根本意图，应建议建立新的 change，而不是把旧 change 改成另一个问题。
- 不自动 Apply 或 Archive；更新计划后等待用户明确请求。
