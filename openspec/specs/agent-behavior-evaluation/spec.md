# agent-behavior-evaluation Specification

## Purpose
规定 Agent 装配行为的可比较证据，使维护者能够区分真实能力提升、回归和仅配置成功，并要求每项检查标明证据层级、可观察终态与仍未验证的边界，避免把标准或配置成功冒充真实模型行为。

## Requirements

### Requirement: 行为变更必须从基线开始
在声称 prompt、Skill、profile 或能力变更改善行为前，维护者 MUST 对旧装配运行代表性任务，或记录无法获得可比较基线的原因。

#### Scenario: 优化 prompt 工作流
- **WHEN** 变更旨在改善调研、路由、拒绝、输出或验证行为
- **THEN** 评测在判断新结果前记录旧装配在代表性场景中的结果

#### Scenario: 纯元数据合规修复
- **WHEN** 变更仅修复机器可读元数据，且不声称行为改善
- **THEN** 标准验证可以证明修复，不虚构行为提升结论

### Requirement: 评测场景必须正反平衡
行为评测 MUST 同时包含目标行为应发生和不应发生的场景。

#### Scenario: 评测调研触发
- **WHEN** 套件检查助手是否调研外部事实
- **THEN** 套件同时包含必须调研的外部当前事实任务和不应调研的纯仓库任务

### Requirement: Trial 必须可比较并面向结果
比较 trial MUST 记录客户端、可观察的模型、prompt 和 Skill inventory、工具面、输入任务、观察到的 transcript 或动作、最终输出，以及与成功有关的环境终态。

#### Scenario: Agent 自述完成但没有生效态
- **WHEN** transcript 声称某能力已激活，但客户端运行或环境结果没有确认
- **THEN** 评测不得把实际生效态判为成功

#### Scenario: 多条有效路径满足合同
- **WHEN** 不同工具序列产生相同且有效的可观察结果
- **THEN** 评测检查结果和必要安全边界，不强制偶然的工具调用顺序

### Requirement: 评测证据必须标明状态层
每项检查 MUST 标明它证明的是声明态、配置态、标准合规还是实际运行行为。

#### Scenario: Lock 和静态验证均通过
- **WHEN** lock 验证和 Skill 元数据验证均成功
- **THEN** 助手报告配置态和标准合规已证明，并在真实运行前把实际运行行为保持为 unknown
