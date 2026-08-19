## Purpose

定义 `agent-assembler` 如何在 CAP v3 中把负责人目标交付为独立叶子 role、显式能力闭包、派生配置和分层证据，同时保留人工决定与审批边界。

## ADDED Requirements

### Requirement: Agent 装配者必须交付完整叶子 role

Agent 装配者 MUST 为每个目标 Agent 建立稳定 id、目标、非目标、触发、输入、输出、独立 prompt、显式能力操作、runtime 选择和验收证据；不得靠临时改写共享 profile 模拟多个 Agent。

#### Scenario: 创建新的项目 Agent
- **WHEN** 负责人确认一个新的 Agent 合同
- **THEN** 装配者创建一个 manifest 叶子 role及其独立 prompt
- **AND** role 的能力只来自 project-defaults、role 操作、项目 Skill import 或已批准 external import

#### Scenario: 目标仍有关键价值取舍
- **WHEN** 未决答案会改变 role 身份、能力或风险边界
- **THEN** 装配者先给出建议并取得负责人决定
- **AND** 不把 Agent 自己的偏好写成已确认合同

### Requirement: Grilling 必须保留明示同意门

Agent 装配者 MAY 发现并建议 `grilling`，但 MUST 只在用户直接要求或明确接受一次建议后开始结构化问询。

#### Scenario: 用户直接要求 grilling
- **WHEN** 用户要求使用 grilling 压力测试装配方向
- **THEN** 装配者加载独立 `grilling` Skill并按其问题轮次、退出和实施前确认合同执行

#### Scenario: 普通装配请求没有同意
- **WHEN** 任务复杂但用户没有要求或接受 grilling
- **THEN** 装配者不得自动开始盘问
- **AND** 可以直接处理可查事实，只把真正的价值决定交给用户

### Requirement: 派生状态不得替代源声明或人工审批

Agent 装配者 MUST 从 manifest、project-defaults、role、prompt、Skill source 和 runtime policy修改源头，再刷新 lock、binding 与 render；machine-context pin MUST 继续由明确审批产生。

#### Scenario: role 源文件发生变化
- **WHEN** prompt 或能力操作改变
- **THEN** 装配者刷新项目 lock并重建受影响 role 的 binding
- **AND** 不自动刷新 machine-context pin

#### Scenario: machine-context 尚未批准
- **WHEN** manifest 已生成但 pin 不存在或 active digest 改变
- **THEN** 装配者报告差异并请求明确批准
- **AND** 未获批准前不得把 verify 或 run 报告为通过

### Requirement: 交付必须分层报告证据

Agent 装配者 MUST 分别报告标准合规、声明态、配置态和实际运行行为；低层证据不得冒充高层生效。

#### Scenario: lock 和 render 通过但没有模型运行
- **WHEN** Skills、lock、binding 和 render 均通过，但认证或客户端行为 trial 不可用
- **THEN** 装配者报告标准／声明／配置态通过
- **AND** 把模型行为生效态保持为 `unknown`
