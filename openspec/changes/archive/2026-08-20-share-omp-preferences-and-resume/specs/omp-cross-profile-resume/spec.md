## Purpose

定义 CAP profile 之间共享 OMP session 存储与 `/resume` 发现行为，使用户可在当前 profile 中选择任意空闲 session，并以当前 profile 的有效运行配置继续该 transcript。

## ADDED Requirements

### Requirement: CAP profile 必须使用共享 session root

使用同一 OMP runtime id 的 CAP profile MUST 使用同一个受管理的 session root。该 root 中的 session MUST 可被任意已装配 CAP profile 的 `/resume` 发现；session root 不得以 profile 名、render hash 或 generation 目录隔离。

#### Scenario: 当前 profile 发现另一 profile 的 session
- **WHEN** session 由 profile A 创建且用户打开 profile B 的 OMP `/resume`
- **THEN** picker SHALL 显示该 session

### Requirement: 跨 profile 选择 session 必须使用当前 profile 继续

用户在当前 profile 的 `/resume` 选择 session 时，CAP MUST 保留该 session 的 transcript 与 identity，并以当前 profile 的模型、advisor、prompt、runtime policy 和 capability closure 继续。CAP MUST NOT 重新启用创建 profile 的能力、配置、运行中 tool call、子 Agent、worktree 或 extension。

#### Scenario: 从 general session 切换至 agent-assembler
- **WHEN** 用户打开 `agent-assembler` 并选择由 `general` 创建的 session
- **THEN** 下一次 OMP 请求 SHALL 使用 `agent-assembler` 的有效 profile 配置
- **AND** session transcript SHALL 保持可读和连续

#### Scenario: 当前模型窗口小于历史上下文
- **WHEN** 所选 session 的可用历史超过当前 profile 模型的有效 context window
- **THEN** CAP/OMP SHALL 在下一次请求前按当前模型配置压缩或拒绝继续
- **AND** SHALL 不为保留旧 history 自动提升到 premium long-context window


### Requirement: 共享 session 不得合并 profile runtime 状态

共享 session root MUST NOT 使 profile runtime root、render、prompt、能力闭包、MCP、Skill、Hook、Plugin、运行中任务、数据库写入锁、worktree 或临时 artifact 变为跨 profile 共享状态。跨 profile resume 只恢复 transcript 与 session identity，不得把 credential、provider token、endpoint secret、tool result secret 或 profile 配置全文写入 session metadata。

#### Scenario: 恢复旧 transcript
- **WHEN** 用户以当前 profile 恢复另一 profile 创建的 session
- **THEN** 当前 profile runtime SHALL 保持独立
- **AND** 旧 transcript SHALL 不作为恢复旧能力或认证的输入
