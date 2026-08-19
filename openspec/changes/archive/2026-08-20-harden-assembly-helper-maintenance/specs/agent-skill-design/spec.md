## Purpose

规定可移植、可发现且可维护的 Agent Skill 合同，包括明确路由边界、渐进披露和标准合规证据。

## ADDED Requirements

### Requirement: 运行时 Skill 必须公开标准发现元数据
每个运行时 Skill MUST 提供有效 YAML frontmatter；其中 `name` 必须与小写连字符目录 id 一致，非空 `description` 必须同时说明 Skill 做什么和何时使用。

#### Scenario: 新增或修改 Skill
- **WHEN** 维护者创建或修改运行时 Skill
- **THEN** 在报告闭包完成前，标准验证确认其发现元数据有效

#### Scenario: 闭包通过但元数据无效
- **WHEN** 本地 profile 引用均可解析，但某个 Skill 缺少有效发现元数据
- **THEN** 助手分别报告本地闭包和标准合规结果，不给出无差别成功结论

### Requirement: Skill 路由边界必须可测试
每个 Skill MUST 定义聚焦触发条件、不适用边界、预期输出和完成条件，使其能与相邻 Skill 区分。

#### Scenario: 两个 Skill 看似都适用
- **WHEN** 一个任务同时涉及 prompt 设计和 Skill 设计
- **THEN** 助手依据声明边界选择或排序，而不是为了完整而加载两者

#### Scenario: 任务不需要 Skill 工作流
- **WHEN** 请求很简单，且常驻 prompt 已完整约束该任务
- **THEN** 助手不激活无关的多步骤 Skill

### Requirement: Skill 内容必须使用渐进披露
Skill MUST 保持激活合同简洁，并将条件性细节、可复用参考、确定性脚本或大型资产放入仅在需要时加载的聚焦项目内文件。

#### Scenario: 条件指引增长
- **WHEN** 某一节仅适用于一个客户端、格式或流程分支
- **THEN** Skill 链接一级聚焦参考文件，而不是在每次激活时加载该分支

### Requirement: 运行时能力授权始终来自 profile
Skill 元数据或工具提示 MUST NOT 授予选定 `.cap` profile 未声明的能力。

#### Scenario: 外部 Skill 引用未声明工具
- **WHEN** 外部 Skill 假定存在 profile 未声明的工具、MCP、Hook 或 Plugin
- **THEN** 助手在采纳前拒绝或改造该依赖，不把 Skill 元数据视为授权
