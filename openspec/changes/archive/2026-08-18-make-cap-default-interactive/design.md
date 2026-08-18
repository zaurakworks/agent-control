## Context

`tools/cap.py` 的 `_interactive()` 当前把 profile、CLI 与 `use/run/render` 动作放在同一流程；`render` 要求用户提供空目录。`show` / 底层 `explain` 已输出公共 inventory 和各端 hash，但没有人类可用的 CLI 文件树展开。入口方面，`_build_parser()` 注册 `interactive` / `i`，`main()` 在无参数时打印帮助。

高频使用与低频查看应是独立入口。CAP 仍只负责 Agent CLI 启动前的能力装配；查看链路可以展示配置态摘要，但启动后的认证、模型、Session 和命令由客户端负责。当前注册的客户端只有 Codex、Qoder、OMP，本机没有 Claude CLI。用户确认当前 CLI 没有外部依赖方，因此入口可以 clean cutover。

## Goals / Non-Goals

### Goals

- 裸 `cap` 成为没有动作菜单的最短启动链路。
- `cap show` 成为独立查看链路，先展示公共闭包，再可选展开 CLI 特定渲染。
- 查看公共闭包不要求 CLI；展开目标文件树时必须显式确定 CLI。
- 自动化子命令继续显式、非交互地工作。
- 非 TTY 的不完整交互调用不会挂起等待输入。
- profile 能力闭包和现有客户端渲染结果不变。
- 客户端选择复用 adapter 注册表，为未来真实 Claude adapter 保留接入口。

### Non-Goals

- 不在裸 `cap` 中保留“启动/查看”动作选择。
- 不把查看链路扩展为交互式文件浏览器，也不输出全部文件正文。
- 不增加 Session、认证、模型或 OpenSpec 菜单。
- 不修改 profile、能力资产、CAP engine 或现有客户端适配器。
- 不改变显式 `run`、`render` 或启动动作的参数合同。
- 不添加 Claude 占位项、空实现、模拟 render 或未经验证的支持声明。
- 不设计兼容层、弃用期、版本协商或旧默认回退。

## Decisions

### 1. 以“无子命令”而不是“argv 为空”判定交互入口

删除 `main()` 中无参数打印帮助的提前返回。完成 argparse 解析后，若 `args.command is None`，直接进入使用链路：选择 profile、选择 CLI、收集可选客户端参数并调用现有 launch。这样 `cap` 和 `cap --project <path>` 语义一致；`cap --help` 仍由 argparse 处理。

不在裸 `cap` 中增加顶层“使用/查看”菜单；查看始终从显式 `cap show` 进入。

### 2. 非 TTY 裸调用明确失败

在进入裸 `cap` 使用链路前检查标准输入和标准输出的 TTY 状态。`cap show` 未提供 profile 时也执行相同检查。任一不是 TTY 时返回非零状态，并提示补齐显式子命令参数；参数完整的显式子命令不做该检查。

这避免 CI、脚本或管道等待输入。不得静默退回打印帮助并返回成功，因为那会掩盖错误调用。

### 3. 清理 interactive/i 子命令

从 parser 删除 `interactive` 及别名 `i`。同时把 `show` 的隐式默认 profile 改为 TTY 选择或非 TTY 报错。当前没有外部依赖方，仓库内调用一次性迁移；不保留兼容 shim、弃用警告或旧行为开关。

### 4. 使用与查看采用独立入口

无子命令分支进入高频使用函数，只做 profile、CLI、客户端参数和 launch。`run`、`render`、`show` 都不出现在这条链路。

`cap show` 扩展为查看入口：

- 未提供 profile 且在 TTY：交互选择 profile；
- 提供 profile、未提供 `--cli`：直接输出公共闭包；
- 提供 profile 和 `--cli`：直接输出公共闭包及该 CLI 的装配预览；
- 非 TTY 且未提供 profile：失败并要求显式参数。

现有 `cap show <profile>` 的 explain 能力保持；仅把原先隐式默认 profile 改为“TTY 选择或非 TTY 报错”，避免低频查看静默选错对象。

### 5. 查看链路分为公共闭包和 CLI 渲染

第一层调用同一个 profile tool 的 explain，稳定显示 prompt、Skills、MCP、Hooks、Plugins inventory，以及所有已注册客户端的 tree hash。此层不要求 CLI。

交互式 `cap show` 在公共层后提供“不展开”及各已注册客户端选项，默认不展开。选择客户端或显式传入 `--cli` 后，使用 `tempfile.TemporaryDirectory` 执行真实 render，枚举临时根中的相对文件路径，并输出对应 tree hash。

CAP 不输出完整文件正文，不询问持久输出目录，也不启动客户端。临时目录在成功、失败和中断路径都自动清理。explain、render、JSON 解析或文件枚举失败时，错误指出具体阶段并返回非零状态。

显式 `cap render --output` 仍负责持久落盘。查看预览只协调现有 explain/render，不建立第二套 renderer，也不修改 `caprun`。

### 6. 客户端选择复用 adapter 注册表

使用和查看的 CLI 选项都从现有 `CLIENTS` / adapter 注册表生成，不在两个流程中复制端名或条件分支。本 change 只覆盖 Codex、Qoder、OMP。

Claude 延期到有真实 CLI 的机器继续开发。本次不添加不可选择的占位项、空 adapter 或模拟树；未来 Claude adapter 完成 launch、render 和验证后，通过注册表自然进入两条链路。

### 7. 能力资产不参与变更

本变更只修改 launcher 入口、`show` 协调和文档。`.cap`、lock、render tree 和 receipt 不应变化。验证时先记录两个 profile 的 Codex/Qoder/OMP tree hash，实施后逐项比较；若发生变化则视为越界回归。

## Risks / Trade-offs

- [旧入口和默认行为立即失效] → 无外部依赖方；一次性迁移仓库内文档和调用，以版本控制作为唯一回滚手段。
- [查看需要记住 `cap show`] → 这是分离高频与低频链路的明确成本；复用已有命令而不增加 `view` 同义入口。
- [非 TTY 调用从默认对象变为失败] → `cap show <profile>` 保持可脚本化，避免自动化依赖隐式 profile。
- [TTY 判定在特殊终端代理下过严] → 只约束需要提问的不完整调用；参数完整的显式子命令始终可用。
- [预览输出过长或泄露正文] → 只显示有界 inventory、相对路径和 hash，不输出文件正文。
- [临时渲染残留] → 使用 `TemporaryDirectory` 覆盖正常、错误与中断路径，并测试清理。
- [预览与真实启动不一致] → 查看调用同一 profile tool 的真实 render，并比较显式 render tree hash。
- [Claude 接口被误认为已支持] → 不注册 Claude、不输出 Claude hash，文档明确延期；未来以真实 adapter 和运行证据启用。
- [入口改动意外触碰运行闭包] → 使用变更前后 Codex/Qoder/OMP tree hash 和 inventory 比较阻断。

## Migration Plan

1. 记录 `general` 和 `assembly-helper` 当前 Codex/Qoder/OMP inventory 与 tree hash。
2. 删除 `interactive` / `i`，把无子命令路由到没有动作菜单的高频使用链路。
3. 扩展 `show` 参数和 TTY 边界，建立独立查看链路及公共闭包输出。
4. 用临时目录组合 explain、CLI 特定 render 与稳定文件树输出，复用客户端注册表且不添加 Claude。
5. 添加高频启动、公共查看、CLI 展开、非 TTY、预览清理、旧别名和显式低频接口的聚焦测试。
6. 一次性迁移仓库内调用、README、帮助和维护指南，明确四类入口及 Claude 延期边界。
7. 运行 OpenSpec strict validation、CAP verify、三端 tree hash 比较和两条入口的 PTY smoke check。
8. 回滚只通过版本控制恢复旧入口、动作菜单和 `show` 默认；不提供运行时兼容开关。
