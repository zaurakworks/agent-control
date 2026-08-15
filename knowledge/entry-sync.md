# K5：入口母本同步工具 entry_sync 的用途与用法

> 状态：正式当前公共知识。
> 最近核验：2026-08-12。
> 适用对象：本仓 `scripts/entry_sync`（Python 包）与母本 `entrypoints/agent-system.md`。
> 环境：本仓 `0bc5312`（当前 main 基线）；Python 3.13.13 标准库，无外部依赖。
> 版本边界：`targets.json` 声明与工具接口随仓演进，以仓内当前版本为准。
> 本次核验水位（2026-08-12，一手来源）：`python -B -m unittest tests.test_entry_sync` 实际运行 21 项并全部通过；`python -B -m scripts.entry_sync check --scope repository` 实际核对 3 个版本化目标并全部通过。

## 回答的问题与价值门

系统入口规则同时存在于多处拷贝（仓库 3 份、用户目录 3 份），修改母本后如何同步全部拷贝并验收一致？

入口文本此前手抄维护已实际出过章节不一致与换行差异问题；每次入口改动都要走本工具，且合并当日的首次真实运转即检出并刷新了三份过期安装拷贝，通过价值门。

## 可直接复用的结论

`entrypoints/agent-system.md` 是唯一母本；`scripts/entry_sync/targets.json` 声明式列出全部目标（README 三节投影、AGENTS 六节子集、三份安装目标），选节规则不藏在生成器代码里。母本或选节规则改动后按三步执行：

1. **生成**：`python -B -m scripts.entry_sync generate` 把全部目标生成到暂存目录并打印源→目标映射；加 `--write-repository` 才写仓内三个版本化目标；任何路径都不会直接写 `~/.claude`、`~/.codex` 或 `%APPDATA%`。
2. **安装**：把暂存生成物应用到用户侧安装目标——这一步需要相应授权，工具刻意不自动执行。
3. **验收**：`python -B -m scripts.entry_sync check` 对全部目标做换行规范化比对，输出逐目标统一差异与 CI 可用退出码；`--scope repository` 只查版本化目标。

## 第一方来源

- 仓内实现与说明：`scripts/entry_sync/README.md`、`scripts/entry_sync/core.py`、`scripts/entry_sync/targets.json`、`tests/test_entry_sync.py`（2026-08-12 在 `0bc5312` 直接运行：21 项单测全部通过；项数是核验水位，不是固定验收常量）；
- [关联 #47（入口单一真源生成器）](https://github.com/Eridanus117/agent-control/pull/47)：S3 交付说明与合并当日首次真实运转记录（检出并刷新三份过期安装拷贝）；
- `work/records/2026-08-10-federated-session-entry/record.md` §40。

## 例外、未知和不能推出的结论

- 只覆盖 `targets.json` 已声明的目标；新增拷贝位置必须先入声明，否则不受同步与验收保护。
- 工具只保证目标与母本投影一致，不判断母本内容本身正确。
- 安装步骤的授权边界由当次任务合同决定，工具不代作决定。

## 失效条件

1. 母本路径、`targets.json` 或命令接口发生变化；
2. 入口不再采用单一真源模型。

## 下次最少复核步骤

1. 运行 `python -B -m unittest tests.test_entry_sync`，记录命令实际报告的用例数与结果；用例数只作为当次水位，不把 21 写成测试套件必须恒定的断言。
2. 运行 `python -B -m scripts.entry_sync check --scope repository`，并对照 `scripts/entry_sync/README.md` 核对命令接口。测试失败、命令或选项消失、目标范围变化时，让受影响结论先退出直接复用；仅用例数变化而接口与行为仍通过时，只刷新核验水位。
