# 原始材料索引

本目录保存从两个仓的本地 `codex-work/` 抢救出的研发过程材料，原样保留目录结构。共 48 个文件、317 KB。

材料性质与限制见 [`../record.md`](../record.md)。**这些是非权威的调研、方案与评审过程，不是当前权威。**

## 与旧索引的格式差别

旧记录的 `raw/index.md` 逐条抄录字节数与 SHA-256，因为被引用的文件在版本控制之外。本目录的内容已在 Git 中，对象 ID 即内容哈希，因此不再重复抄录；需要校验用 `git log` 与 `git show`。

## R01｜`agent-control/research/`

- 类型：事实调研与方案综合，非权威；
- 位置：`agent-control/research/{adaptive-problem-solving-definition, agent-system-global-design, issue-3-autonomous-parent-acceptance}/`；
- 内容：每个主题的 `research.md`（事实与来源）、`innovate.md`（候选与取舍），部分含 `plan.md`；
- 来源：本地 `agent-control/codex-work/research/`，Git 忽略目录；
- 备注：`adaptive-problem-solving-definition` 即 `2026-08-09-agent-system-bootstrap/raw/index.md` 的 S04 所指对象，SHA-256 已在 `../record.md` 核验一致。

## R02｜`agent-control/reviews/20260811/pr-47/`

- 类型：PR 评审记录，非权威；
- 内容：`commit-list.md` 与 `review-743a315.md`；
- 关联：PR-47（`impl/s3-entry-generator`，入口单一真源生成与校验工具）。

## R03｜`agent-control/shadow-49/`

- 类型：影子评审对照实验，非权威；
- 内容：`external-*` 为外部线的 research/plan/innovate 与代码质量评审；`own/` 为自评线的 research/options/plan 与评审；
- 用途：同一 PR-47 由两条独立线各评一次，用于对照，不是最终结论。

## R04｜`agent-control/issue-98-recall/`

- 类型：可复算实验，非权威；
- 内容：`experiment.py`（实验脚本）、`queries.json`（查询集）、`report.md`（结论）、`results_final_rerun.json`（最终一轮结果）；
- 限制：**四轮结果只保留最后一轮**，无法比对轮次差异；四轮结论一致，见 `report.md`。

## R05｜`agent-plugins/research/`

- 类型：事实调研与方案综合，非权威；
- 位置：`agent-plugins/research/{issue-1-cross-provider-method-assets, issue-2-method-asset-conformance-contract, issue-4-grilling-dual-provider-plugin, issue-6-grilling-upstream-review}/`；
- 内容：各主题 `research.md` / `innovate.md` / `plan.md`；`issue-4` 另含 `implementation-evidence.md` 与两端探针配置；
- 关联：`zaurakworks/agent-plugins` 的 Issue #1 / #2 / #4 / #6。

## R06｜`agent-plugins/reviews/20260808/`

- 类型：PR 评审记录，非权威；
- 内容：`pr-3/` 与 `pr-5/` 各自的 `commit-list.md` 与逐 commit 评审。

## R07｜`agent-plugins/experiments/issue-4/`

- 类型：实验环境快照，非权威；
- 内容：两次运行（`run-20260808-a1` / `-a2`）捕获的 `codex-home/config.toml`、`claude-home/` 的 `.claude.json`、`settings.json` 与插件注册；
- 限制：**是当时的实验快照，不代表任何当前配置**；已排除自动备份、插件目录缓存与运行期临时文件（见 `../record.md`）。
