## Purpose

为 OMP 主力客户端提供受控的用户级持久 runtime、项目覆盖、隔离 render 和实际运行证据，并为后续客户端 adapter 固定可复用边界。

## ADDED Requirements

### Requirement: OMP runtime 必须按 runtime-id 持久化

OMP MUST 使用 `$HOME/.agent-system-state/runtimes/omp/<runtime-id>/` 作为受控用户级 runtime namespace。Session、settings 和 agent.db 属于 runtime 状态，不得成为项目能力 discovery 来源。

#### Scenario: 两个项目使用 OMP default runtime
- **WHEN** 两个项目选择 `omp/default`
- **THEN** 它们可以共享批准的持久 runtime 状态
- **AND** 每次启动仍必须使用当前项目独立的 profile render 和 runtime policy

### Requirement: OMP 启动必须使用隔离 render

每次 OMP launch 或 run MUST 生成当前项目、role 和 policy 对应的临时 native render，并显式指向该 render。真实 HOME 不得使用户级 Agent 资产自动进入 render。

#### Scenario: OMP 从真实 HOME 启动
- **WHEN** OMP 需要 Git、SSH 或语言工具链
- **THEN** 进程可保留批准的宿主上下文
- **AND** OMP 的 prompt、Skill、MCP、rules 和 extension 来源仍由当前 render 控制

### Requirement: OMP policy 必须投影到 native config

受控 OMP runtime policy MUST 在 render 阶段投影到 OMP 所需的 native config；直接修改 ambient `~/.omp` 不得成为 CAP 的隐式配置入口。

#### Scenario: 用户设置 OMP advisor preference
- **WHEN** preference、项目 policy 和 role override 经过校验并合成
- **THEN** OMP 临时 config 反映最终允许值
- **AND** render hash 与 receipt 能识别该值变化

### Requirement: OMP 能力和 runtime policy 必须独立校验

OMP render MUST 分别校验 Agent-facing capability closure 与 runtime policy。runtime policy 变化不得绕过能力 lock、machine-context pin 或 assembly-binding。

#### Scenario: OMP policy 合法但 machine context stale
- **WHEN** runtime policy 无冲突但 machine-context active digest 已漂移
- **THEN** 非交互启动 MUST 失败
- **AND** 不得仅因为 OMP config 可生成就继续运行

### Requirement: OMP 生效态证据必须保守

OMP 的 MCP、Hook、Plugin、context 和 advisor 观察结果 MUST 按真实 probe 能力分类；无法观察的结果保持 unknown，不得由配置文件存在推断为已生效。

#### Scenario: OMP one-shot 无法列举完整 resolved MCP
- **WHEN** 客户端输出不足以证明完整工具面
- **THEN** receipt 标记 `reported_client_limited` 或 `unknown`
- **AND** 不得声称跨客户端等价
