# cap-default-interactive-entry Specification

## Purpose
定义 CAP 的两条人类链路：裸 `cap` 专用于高频启动，`cap show` 专用于公共闭包与 CLI 特定装配查看；同时保持自动化接口、运行时能力闭包和 Agent CLI 职责边界不变。

## Requirements

### Requirement: 裸 cap 专用于高频使用链路

CAP SHALL 在交互终端中收到全局选项但没有显式子命令时，依次选择 profile、选择 CLI、收集可选客户端参数并进入原有 launch 路径。该链路 SHALL NOT 显示动作菜单、装配预览或 batch `run`。

#### Scenario: 裸 cap 启动 CLI

- **WHEN** 用户在交互终端执行 `cap`
- **THEN** CAP SHALL 依次选择 profile 和 CLI、收集可选客户端参数并启动所选客户端

#### Scenario: 带全局选项但无子命令

- **WHEN** 用户执行带合法全局选项但未指定子命令的 `cap`
- **THEN** CAP SHALL 使用这些选项进入同一高频使用链路

#### Scenario: 高频链路没有动作选择

- **WHEN** 用户完成 profile 和 CLI 选择
- **THEN** CAP SHALL 直接进入客户端参数与启动步骤，不询问 `use`、`run`、`render` 或“启动/查看”动作

#### Scenario: 显式子命令

- **WHEN** 用户执行 `cap show`、`cap verify` 或其他保留的显式子命令
- **THEN** CAP SHALL 只执行该子命令，不进入裸 `cap` 使用链路

### Requirement: cap show 提供独立查看链路

CAP SHALL 使用 `cap show` 承载全部人类查看行为，并把公共能力闭包与 CLI 特定渲染分为两层。进入公共层 SHALL NOT 要求先选择 CLI；只有展开实际装配时才需要 CLI。

#### Scenario: 交互式查看公共闭包

- **WHEN** 用户在 TTY 中执行未指定 profile 的 `cap show`
- **THEN** CAP SHALL 先选择 profile，再显示 prompt、Skills、MCP、Hooks、Plugins 的公共 inventory 和全部已注册客户端的 tree hash

#### Scenario: 可选展开一个 CLI

- **WHEN** 公共闭包显示完成且用户选择展开一个 CLI
- **THEN** CAP SHALL 对所选 profile 和 CLI 执行真实 render，并显示目标相对文件树和与显式 render 一致的 tree hash
- **THEN** CAP SHALL NOT 启动客户端、询问输出目录或保留临时渲染目录

#### Scenario: 查看后不展开

- **WHEN** 用户在公共闭包后选择不展开任何 CLI
- **THEN** CAP SHALL 成功退出，不执行 render

#### Scenario: 直接查看指定 profile

- **WHEN** 用户执行 `cap show <profile>` 且未指定 CLI
- **THEN** CAP SHALL 不询问交互问题，直接输出该 profile 的公共闭包和全部已注册客户端的 tree hash

#### Scenario: 直接查看指定 CLI 装配

- **WHEN** 用户执行 `cap show <profile> --cli <client>`
- **THEN** CAP SHALL 不询问交互问题，直接输出公共闭包、该客户端目标相对文件树和 tree hash

#### Scenario: 非 TTY 未指定 profile

- **WHEN** 在非 TTY 环境执行未指定 profile 的 `cap show`
- **THEN** CAP SHALL 返回非零状态并要求显式提供 profile，且 SHALL NOT 调用交互输入函数

#### Scenario: 显式低频接口仍可用

- **WHEN** 用户或自动化显式执行 `cap run ...` 或 `cap render ... --output <目录>`
- **THEN** CAP SHALL 按现有参数和语义执行，不受使用与查看链路拆分影响

#### Scenario: CLI 展开失败

- **WHEN** explain、render、输出解析或目标文件枚举失败
- **THEN** CAP SHALL 返回非零状态、报告具体阶段，并清理已创建的临时渲染目录

### Requirement: 非交互环境不得等待输入

CAP SHALL 在裸 `cap` 没有显式子命令，或 `cap show` 没有显式 profile，且标准输入或标准输出不是交互终端时快速失败，并输出可操作的显式调用说明。

#### Scenario: 脚本裸调用 cap

- **WHEN** 脚本在非 TTY 环境执行没有子命令的 `cap`
- **THEN** CAP SHALL 返回非零状态且 SHALL NOT 调用交互输入函数

#### Scenario: 非交互显式调用

- **WHEN** 脚本执行 `cap show <profile>`、`cap verify` 或其他参数完整的显式子命令
- **THEN** CAP SHALL 按现有方式执行，不因非 TTY 被拒绝

### Requirement: 交互别名完成清理切换

CAP SHALL 移除 `interactive` 和 `i` 子命令，不保留兼容 shim。帮助文本和普通使用说明 SHALL 只把裸 `cap` 描述为使用入口，把 `cap show` 描述为查看入口。

#### Scenario: 旧交互别名不再接受

- **WHEN** 用户执行 `cap i` 或 `cap interactive`
- **THEN** 参数解析 SHALL 以未知命令失败，并提示使用 `cap`

#### Scenario: 帮助仍然显式可用

- **WHEN** 用户执行 `cap --help`
- **THEN** CAP SHALL 显示帮助并退出，且 SHALL NOT 进入交互流程

### Requirement: 客户端扩展边界保持显式

使用链路和查看链路 SHALL 从同一个客户端 adapter 注册表获取选项，不在交互逻辑中复制 Codex、Qoder、OMP 分支。本 change SHALL NOT 添加 Claude 占位客户端；未来只有在真实 Claude adapter、render 行为和运行验证可用后才能注册 Claude。

#### Scenario: 当前客户端范围

- **WHEN** 用户进入 CLI 选择或查看全部客户端 hash
- **THEN** CAP SHALL 只展示当前已注册的 Codex、Qoder、OMP，不展示 Claude

#### Scenario: 未来注册真实 Claude adapter

- **WHEN** 后续变更注册具备真实 render 与 launch 实现的 Claude adapter
- **THEN** 现有使用与查看链路 SHALL 能从注册表发现它，而无需增加 Claude 专用交互分支

### Requirement: 运行时能力闭包保持不变

该入口与查看变化 SHALL NOT 修改任何 profile、prompt、Skill、MCP、Hook、Plugin、lock schema、现有客户端适配器或 receipt。给定相同 profile 和现有 client，`cap show --cli` 的 tree hash SHALL 与显式 render 一致，且变更前后的渲染 tree hash SHALL 相同。

#### Scenario: 配置态闭包比较

- **WHEN** 在变更前后解释并渲染 `general` 与 `assembly-helper`
- **THEN** 两个 profile 的 inventory 和三端 tree hash SHALL 分别保持一致

#### Scenario: 生效态双链路 smoke check

- **WHEN** 在 PTY 中分别执行裸 `cap` 和 `cap show`
- **THEN** 裸 `cap` SHALL 到达原有客户端启动路径，`cap show` SHALL 显示公共闭包并可选展开真实目标清单且不启动客户端；证据只覆盖实际执行的客户端，不得外推 Claude 或其他未运行端
