---
name: spec-change-pack
description: 为 Agent 装配行为创建和维护可审查的 OpenSpec 或等价变更包。新增 profile、可观察行为变化、跨客户端能力变化、风险迁移或未来维护者必须审计的变化时使用；普通小修改跳过。
---

# spec-change-pack

## 流程
1. 只在审查仪式值得时使用：新增 profile、可观察 Agent 行为变化、跨客户端能力变化、风险迁移或长期审计需求。
2. 每个 change 只保留一个意图。实施前拆分无关的“顺便”条款。
3. 项目存在已授权 OpenSpec 工作流时使用它，否则使用等价 issue 或审查段落。未经项目授权绝不初始化 OpenSpec。
4. OpenSpec 启用后，使用仓库内 CLI JSON 接口：`openspec status --json`、`openspec instructions <artifact> --json`、`openspec validate --json`，以及 archive 或 sync 输出。遵循 `openspec/config.yaml` 的 context、资产语言规则和 operation guidance。
5. 保持四类资产独立：
   - proposal：意图、范围、非目标、受影响 profile 和能力、基线来源、可逆边界；
   - delta behavior：可观察的新增、修改、删除或重命名，包括触发、不触发、输出、拒绝或退出、状态层场景；
   - design：能力来源、prompt 与 Skill 分层、客户端差异、lock/render 影响、可观察性、无 secret 边界、回滚；
   - tasks and evidence：实施清单、准确验证命令、观察输出和剩余未知。
6. Delta 必须面向行为。路径、命令、迁移和实施细节放在 design 或 tasks。
7. 谨慎使用 delta operation：
   - ADDED 表示新行为；
   - MODIFIED 必须包含完整更新行为；
   - REMOVED 必须说明原因和迁移或回滚影响；
   - RENAMED 仅用于行为不变的命名变化。
8. 完整规划包只授权规划。除非用户同时授权实施，否则不编辑运行时声明。
9. 实施后更新长期 profile、prompt 和 Skill truth。只有标准验证、闭包验证、任务完成，并且每项运行时结论都有证据后才归档。

## 完成条件
只有当审查者无需聊天历史即可恢复意图、行为 delta、实施决定、完成任务、验证证据、语言约定和归档或回滚状态时，变更包才算完成。
