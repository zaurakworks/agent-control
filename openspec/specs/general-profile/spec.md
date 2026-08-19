# general-profile Specification

## Purpose
TBD - created by archiving change add-general-profile. Update Purpose after archive.

## Requirements

### Requirement: 显式通用 profile

仓库 SHALL 声明名为 `general` 的 profile。该 profile SHALL 使用独立 prompt，并 SHALL NOT 隐式继承 `assembly-helper` 的装配专用 Skills。`general` 仅在调用方显式选择时成立；未受 CAP 管理的会话不得被标记为 `general`。

#### Scenario: 显式选择 general

- **WHEN** 调用方请求列出 profile 或解释 `general`
- **THEN** CAP SHALL 返回 `general` 的 prompt、Skill 清单和各客户端渲染摘要

#### Scenario: 未显式选择 profile

- **WHEN** 客户端不是经 CAP 以 `general` 启动
- **THEN** 系统 SHALL NOT 声称当前运行身份为 `general`

#### Scenario: general 保持通用边界

- **WHEN** 检查 `general` 的能力闭包
- **THEN** 其 Skill 清单 SHALL NOT 包含 `assembly-helper`、`agent-prompt-design`、`agent-skill-design`、`capability-profile-closure`、`capability-lifecycle` 或 `agent-behavior-evaluation`

### Requirement: 所有工作 profile 包含 OpenSpec 工作流

仓库内每个工作 profile SHALL 显式声明 `openspec-explore`、`openspec-propose`、`openspec-update-change`、`openspec-apply-change`、`openspec-sync-specs` 与 `openspec-archive-change`。这些 Skills SHALL 位于 `.cap` 声明闭包，并 SHALL 声明与 OpenSpec CLI 1.9.0 的兼容关系。

#### Scenario: general 的 OpenSpec 闭包

- **WHEN** CAP 解释或渲染 `general`
- **THEN** 六个 OpenSpec Skills SHALL 全部出现在声明态和配置态清单中

#### Scenario: assembly-helper 的 OpenSpec 闭包

- **WHEN** CAP 解释或渲染 `assembly-helper`
- **THEN** 六个 OpenSpec Skills SHALL 全部出现，且原有装配 Skills SHALL 保持存在

#### Scenario: 禁止 provider 旁路

- **WHEN** 检查仓库运行时能力来源
- **THEN** OpenSpec 工作流 SHALL NOT 依赖 `.agents`、`.claude`、`.qoder` 或 `.omp` 下的客户端专属生成物

#### Scenario: Skill 标准合规

- **WHEN** 执行仓库 Skill 标准验证
- **THEN** 六个 OpenSpec Skills SHALL 通过名称、描述、frontmatter 和文件布局检查

### Requirement: OpenSpec 工作流按意图路由

OpenSpec Skills SHALL 分别覆盖自由探索、创建完整变更、继续补齐变更工件、执行任务、同步主规格和完成归档。自然语言请求和客户端已有的显式 Skill 调用 SHALL 路由到同一 Skill 合同；Skill 不得把规划、实施和归档混成一个隐式动作。

#### Scenario: 自然语言触发 Explore

- **WHEN** 用户要求先讨论、探索或澄清而不实施
- **THEN** `openspec-explore` SHALL 保持思考伙伴模式，并 SHALL NOT 修改应用代码

#### Scenario: 创建 Proposal

- **WHEN** 用户要求把已确认方向建立为 OpenSpec change
- **THEN** `openspec-propose` SHALL 创建 proposal、specs、design 和 tasks 所需工件，并在实施前停止

#### Scenario: Apply 未完成变更

- **WHEN** 用户明确要求实施一个已有 change
- **THEN** `openspec-apply-change` SHALL 读取当前工件、按任务执行并及时更新 task 状态

#### Scenario: 不自动推进工作流阶段

- **WHEN** 用户只要求 Explore 或 Proposal
- **THEN** Agent SHALL NOT 自动进入 Apply 或 Archive

### Requirement: 使用新 profile 恢复 OMP Session

CAP 的 OMP 启动入口 SHALL 原样透传 `--` 后的客户端参数，使调用方可以用 `--resume <id-or-path>` 或 `--continue` 在 `general` 运行实例中恢复 Session。恢复 SHALL 保留会话历史，但新运行实例的能力面 SHALL 来自 `general` 的当前已锁定渲染结果。

#### Scenario: resume 参数透传

- **WHEN** 调用方执行 `cap use general --cli omp -- --resume <id-or-path>`
- **THEN** CAP SHALL 选择 `general`、渲染其闭包，并把 resume 参数交给 OMP

#### Scenario: 不热改正在运行的能力

- **WHEN** `general` 声明在一个 OMP 进程运行期间发生变化
- **THEN** 已运行进程的能力快照 SHALL NOT 被原地替换；变化 SHALL 在下一次 launch 或 resume 时生效

#### Scenario: 生效态结论需要真实运行

- **WHEN** 只有 manifest、lock 或 render 证据而未执行真实 OMP smoke check
- **THEN** 结果 SHALL 只报告声明态或配置态通过，不得声称 Session 已成功恢复或 Skill 已被模型使用
