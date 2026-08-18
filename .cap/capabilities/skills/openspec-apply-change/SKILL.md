---
name: openspec-apply-change
description: 实施已有 OpenSpec change 的任务。用户明确要求开始或继续实现某个 change 时使用；先恢复工件和任务状态，逐项完成并验证，不得自动归档。
allowed-tools: Bash(openspec:*)
license: MIT
compatibility: 仅兼容 OpenSpec CLI 1.9.0；升级 CLI 时必须复核本合同
source: @fission-ai/openspec 1.9.0 openspec-apply-change 的中文项目内适配
---

# OpenSpec Apply Change

## 流程

1. 从用户输入或上下文确定 change。歧义时运行 `openspec list --json` 让用户选择；明确报告正在使用的 change。若选择注册 store，保持 `--store <id>`。
2. 运行：
   ```bash
   openspec status --change "<name>" --json
   openspec instructions apply --change "<name>" --json
   ```
3. 若 instructions 状态为 blocked，报告缺失工件并停止；若为 all_done，报告无需实施并建议 Archive；其他状态继续。
4. 读取 instructions 返回的所有 context files、operation guidance、任务进度和 change 路径。不得依赖旧会话记忆代替磁盘当前内容。
5. 建立与 change tasks 对应的工作 todo。按依赖顺序逐项实施：
   - 宣告当前任务；
   - 修改真实源头并迁移受影响调用方；
   - 执行该任务所需的最小验证；
   - 完成后立即把 change 的对应 checkbox 改为 `[x]`。
6. 遇到无法解决的阻塞时停止，准确记录已完成任务、失败证据和缺失前提；不得把未完成任务标记完成。
7. 完成后运行 change strict validation 和适用的真实行为验证。报告完成任务、验证结果和残留风险。

## Guardrails

- 只实施 planning artifacts 授权的范围；新需求先更新 change。
- 不通过忽略错误、关闭验证或伪造收据完成任务。
- 不批量预先勾选 tasks；每项完成后即时更新。
- 不自动 Sync 或 Archive。实施完成只建议下一步，等待用户明确请求。
