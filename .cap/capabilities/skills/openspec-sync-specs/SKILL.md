---
name: openspec-sync-specs
description: 把已有 change 的 delta specs 合并到长期主规格，但保留 change 不归档。用户要求更新主规格、同步 delta 或在归档前单独核对规格时使用。
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: 仅兼容 OpenSpec CLI 1.9.0；升级 CLI 时必须复核本合同
source: @fission-ai/openspec 1.9.0 openspec-sync-specs 的中文项目内适配
---

# OpenSpec Sync Specs

## 流程

1. 确定 change；歧义时运行 `openspec list --json` 并让用户选择。若选择注册 store，保持 `--store <id>`。
2. 运行 `openspec status --change "<name>" --json`，使用返回的 `changeRoot`、spec artifact 路径和 planning home。
3. 在写任何主规格前运行：
   ```bash
   openspec instructions specs --change "<name>" --json
   ```
   命令必须成功且返回有效 instruction；失败时停止，不能部分写入主规格。
4. 读取全部 delta specs 和对应主规格。`<capability-path>` 是相对 `specs/` 的完整路径，必须保留嵌套目录。
5. 逐项合并：
   - `ADDED`：仅在主规格不存在同名 Requirement 时加入完整 Requirement 和 Scenarios；
   - `MODIFIED`：用 delta 中完整 Requirement 替换同名主 Requirement，同时保留 delta 未明确删除的有效内容；
   - `REMOVED`：删除同名 Requirement；最后一个 Requirement 被移除时删除空 capability spec，而不是留下空壳；
   - `RENAMED`：仅在行为不变时改名，并保证旧名消失、新名存在。
6. 保留不受 delta 影响的主规格内容、排序约定和项目语言规则。合并后逐 capability 对照 delta，确认无遗漏或重复。
7. 运行主规格 strict validation，报告新增、修改、删除和未改变的 capability。change 目录保持原位。

## Guardrails

- 不实现代码，不勾选实施任务，不移动或归档 change。
- 不把 delta spec 整文件覆盖主规格；按 Requirement 语义合并。
- 出现名称歧义、主规格漂移或无法无损合并时停止并请求决定，不猜测。
