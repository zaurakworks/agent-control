---
name: openspec-explore
description: 在实施或建立 change 前，与用户自由探索想法、问题、边界和取舍。用户要求先讨论、调查、澄清或评估方向时使用；不得修改应用代码，也不得自动进入 Proposal 或 Apply。
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: 仅兼容 OpenSpec CLI 1.9.0；升级 CLI 时必须复核本合同
source: @fission-ai/openspec 1.9.0 openspec-explore 的中文项目内适配
---

# OpenSpec Explore

## 姿态

- 做思考伙伴，不做问卷主持人。问题应从当前事实和分叉自然产生。
- 同时展开多个有价值的方向；用图、表或反例澄清真实结构，不强迫快速收敛。
- 调查仓库、规格和外部事实以降低不确定性，但不实施功能或修复。
- 可以在用户明确要求“记录结论”时更新 OpenSpec 规划工件；不得修改应用代码。

## 上下文

1. 若用户明确选择注册 store，先运行 `openspec store list --json`，此后所有支持 store 的命令都固定带 `--store <id>`。
2. 运行 `openspec list --json`，了解活动 change。存在相关 change 时运行：
   ```bash
   openspec status --change "<name>" --json
   ```
3. 使用 CLI 返回的 `planningHome`、`changeRoot` 和 `artifactPaths`；不得假设一定是仓库内 `openspec/changes`。
4. 阅读与问题直接相关的现有工件和代码。查事实是为了讨论，不是暗中开始实现。

## 可做的事

- 重述问题，识别隐含假设、边界和失败模式。
- 比较候选设计及其代价，找出必须由用户决定的分叉。
- 从已有 change 的 proposal、spec、design、tasks 识别矛盾或缺口。
- 当结论成熟时，总结已经确定、仍未知和可选择的下一步。

## Guardrails

- 永不修改应用代码、测试、运行时声明或发布资产。
- 不因用户最初提到“实现”就跳过 Explore 边界；若要实施，先明确退出 Explore。
- 不自动创建 Proposal。只能建议用户显式进入 `openspec-propose`。
- 不把讨论强制转成工件；有时清晰结论就是完整交付。
