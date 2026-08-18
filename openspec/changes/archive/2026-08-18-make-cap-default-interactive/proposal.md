## Why

当前日常入口是 `cap i`，而裸 `cap` 只打印帮助；用户仍需记住一个实现子命令。现有交互菜单还把高频启动与低频 `run` / `render` 混在同一链路，增加每次启动的选择成本，也没有提供独立、直接的装配查看入口。因此需要把裸 `cap` 固定为高频使用链路，并把查看能力收敛到独立的 `cap show` 链路。

## What Changes

- 裸 `cap` 在交互终端中只执行高频使用链路：选择 profile、选择 CLI、收集可选客户端参数并启动 CLI；不再显示动作菜单。
- `cap show` 成为独立查看链路：先选择 profile，显示与 CLI 无关的公共能力闭包和各 CLI tree hash，再由用户选择是否展开某个 CLI 的实际装配。
- `cap show <profile>` 直接输出公共闭包；`cap show <profile> --cli <client>` 对指定客户端执行真实 render，在终端显示目标相对文件树和 tree hash。
- CLI 展开使用自动清理的临时渲染目录，不启动客户端，也不要求用户输入输出目录。
- **BREAKING**：直接移除 `interactive` / `i`，改变裸 `cap` 和无参数 `cap show` 语义；当前没有外部依赖方，因此不提供兼容 shim、弃用期或旧行为回退。
- 保留 `agents`、`profiles`、`clients`、`show`、`use`、`run`、`render`、`lock`、`verify` 和 `skills-validate` 的显式接口；`run` 与持久落盘 `render` 不进入裸 `cap`。
- 裸 `cap` 或无 profile 的交互式 `cap show` 在非 TTY 环境中快速失败并提示显式参数，避免 CI 或脚本等待输入。
- 客户端选择来自现有适配器注册表。本次只实现和验证 Codex、Qoder、OMP；不添加未安装、未适配的 Claude 占位入口，但保留未来 adapter 接入同一使用与查看链路的接口。
- 更新帮助与使用说明，明确 `cap` 是使用链路，`cap show` 是查看链路，并一次性迁移仓库内调用。

## Non-Goals

- 不改变默认 profile、默认 CLI、启动路径或客户端参数透传。
- 不接管 Agent CLI 内部的认证、模型、Session、Slash commands 或 OpenSpec UI。
- 查看链路不是完整文件浏览器；它展示能力清单、目标路径与 hash，不把全部 prompt、Skill 和配置正文倾倒到终端。
- 不修改任何 profile、prompt、Skill、MCP、Hook、Plugin 或运行时能力闭包。
- 不改变显式 `run` / `render`、`caprun`、lock 格式或 receipt 格式。
- 不在没有 Claude CLI、原生 adapter 和运行证据的本机实现或宣称 Claude 支持。
- 不为已变更入口保留兼容别名、兼容参数或旧默认行为。

## Capabilities

### New Capabilities

- `cap-default-interactive-entry`: 定义裸 `cap` 的高频使用链路、独立 `cap show` 查看链路、CLI 特定装配预览、非 TTY 边界和客户端扩展边界。

### Modified Capabilities

无。

## Impact

- 受影响代码：`tools/cap.py` 的参数解析、无子命令启动分支、`show` 交互协调和终端预览输出。
- 受影响文档：README 与维护指南中的使用、查看和自动化入口说明。
- 受影响 profile 和能力：无；`general` 与 `assembly-helper` 的闭包及 Codex/Qoder/OMP tree hash 应保持不变。
- 基线证据：当前 `_build_parser()` 注册 `interactive` / `i`，`main()` 在无参数时打印帮助，`_interactive()` 混合 `use/run/render`；底层 `explain` 已提供公共 inventory 与各端 hash，真实数据表明同一 profile 的 Codex、Qoder、OMP tree hash 不同，`render` 已能生成指定端文件树。当前客户端注册表不含 Claude；用户确认当前 CLI 没有外部依赖方。
- 回滚边界：通过版本控制整体回退入口、`show` 和文档改动；不提供运行时兼容开关。查看只使用自动清理的临时目录，不涉及 Session、认证数据或 profile lock 迁移。
