# 2026-08-15｜抢救 `codex-work/` 研发资产并纳入版本控制

## 摘要

把两个仓本地 `codex-work/` 目录下的研发过程资产（调研、方案、评审、实验）迁入 `work/records/`，纳入版本控制。原目录被 Git 忽略，只存在于单台主机，在一次本地清空操作前被抢救出来。

共 48 个文件、317 KB。来源仓：`zaurakworks/agent-control` 与 `zaurakworks/agent-plugins` 的本地工作副本。

## 为什么

这不是新发现的问题。`work/records/2026-08-09-multi-session-shared-write/record.md` 已经写明：

> **持久化边界不符合当前需求**：调研、选项、计划和审查资产被强制放到仓内不跟踪的 `codex-work/`，并明确禁止提交。过大内容只在 GitHub 留摘要时，新主机不能仅靠仓与 Issue 恢复完整研发依据。

同一批记录里 `2026-08-09-agent-system-bootstrap/raw/index.md` 的 S04 条目也自陈：「保存状态：仅当前主机可用，目录被 Git 忽略」「限制：不能跨 Host 恢复」。

诊断在 08-09 就有了，修复没有落地。08-15 迁仓到 `zaurakworks` 时 `codex-work/` 被整个丢下，新仓从未包含它；随后准备清空本地工作副本，这批文件距离永久丢失只差一步。

本条记录就是那次修复。

## 来源核验

`raw/index.md` 的 S04 条目记录了两个文件的字节数与 SHA-256。抢救回来的副本经 CRLF→LF 归一化后逐字节匹配：

| 文件 | 记录值 | 归一化后实测 |
| --- | --- | --- |
| `research/adaptive-problem-solving-definition/research.md` | `15985` / `811563D6…6C2126` | `15985` / `811563D6…6C2126` ✅ |
| `research/adaptive-problem-solving-definition/innovate.md` | `9172` / `110EE3C2…0B86071` | `9172` / `110EE3C2…0B86071` ✅ |

差异只来自 Git checkout 的行尾转换，内容未变。其余文件没有历史哈希可比对，只能确认来自同一主机的同一目录。

## 内容索引

日期按目录名或所属 PR/Issue 推断，**不是精确的创建时间**；无法推断的标为「未知」。

### 来自 `agent-control`

| 主题 | 路径 | 推断日期 | 内容 |
| --- | --- | --- | --- |
| 自适应问题求解定义 | `raw/agent-control/research/adaptive-problem-solving-definition/` | 08-09 前 | research + innovate，被 S04 引用 |
| Agent 系统全局设计 | `raw/agent-control/research/agent-system-global-design/` | 未知 | research + innovate |
| 父目标自主验收（#3） | `raw/agent-control/research/issue-3-autonomous-parent-acceptance/` | 未知 | research + innovate + plan |
| PR-47 评审 | `raw/agent-control/reviews/20260811/pr-47/` | 08-11 | commit-list + review |
| 影子评审对照（#49） | `raw/agent-control/shadow-49/` | 08-11 前后 | 外部与自评两条线的 research/plan/innovate 与两份 PR-47 评审 |
| 召回实验（#98） | `raw/agent-control/issue-98-recall/` | 未知 | experiment.py + queries.json + report.md + 一份结果 |

### 来自 `agent-plugins`

| 主题 | 路径 | 推断日期 | 内容 |
| --- | --- | --- | --- |
| 跨 provider 方法资产（#1） | `raw/agent-plugins/research/issue-1-cross-provider-method-assets/` | 08-08 前后 | research + innovate + plan |
| 方法资产一致性合同（#2） | `raw/agent-plugins/research/issue-2-method-asset-conformance-contract/` | 08-08 前后 | research + innovate + plan |
| grilling 双 provider 插件（#4） | `raw/agent-plugins/research/issue-4-grilling-dual-provider-plugin/` | 08-08 | research + innovate + plan + 实现证据 + 两端探针配置 |
| grilling 上游评审（#6） | `raw/agent-plugins/research/issue-6-grilling-upstream-review/` | 08-08 后 | research + innovate + plan |
| PR-3 / PR-5 评审 | `raw/agent-plugins/reviews/20260808/` | 08-08 | 各自 commit-list 与逐 commit 评审 |
| 双 Host 实验（#4） | `raw/agent-plugins/experiments/issue-4/` | 08-08 | 两次运行捕获的 codex-home / claude-home 配置 |

## 已排除

9 项，都是缓存、重复或运行期临时文件：

- `issue-98-recall/results.json`、`results_rerun.json`、`results_final.json` — 同一实验四轮结果中的前三轮，只保留最终一轮 `results_final_rerun.json`（30.6 KB）。四轮结论一致，保留全部只是四倍体积。
- `plugin-catalog-cache.json`（397 KB）— 插件目录缓存，可重建。
- `.claude.json.backup.*`（2 个）— 探针自动备份。
- `codex-probe/tmp/arg0/` 下的 `.lock`、`apply_patch.bat`、`applypatch.bat` — 运行期临时文件。

## 与旧索引的差别

旧 `raw/index.md` 为每个条目记录字节数与 SHA-256，因为文件在版本控制之外，没有别的办法证明「你读到的和我引用的是同一份」。

**现在内容在 Git 里，这个字段是冗余的** —— Git 的对象 ID 就是内容哈希，`git log` 能给出每次变更。所以本条记录的 `raw/index.md` 只保留来源、类型与限制，不再逐文件抄哈希。S04 那两个哈希在上面「来源核验」一节保留，因为它们是跨越那次断链的唯一凭据。

## 限制

- 这批资产是**非权威**的调研、方案与评审过程，不能反向定义 `authority/`。
- 日期多为推断。需要精确时间的场合应以对应 GitHub Issue/PR 的时间戳为准。
- 探针捕获的 `config.toml` / `.claude.json` 是当时的实验环境快照，不代表当前配置。
- 实验结果只保留最后一轮，若需比对四轮差异，本记录不足以支撑。

## 遗留

`work/` 根目录下另有 8 项未被 `README.md` 的「文件职责」声明（`configuration-inventory.md`、`current-monitoring-directive.md`、`knowledge-mvp-*.md` 三件、`permission-strategy-research.md`、`system-capability-backlog.md`、`knowledge-trial/`）。同批一并在 `README.md` 中补充声明，未移动位置。
