# 结构化问路登记与 BM25 检索卡

> 状态：现有当前知识包的检索投影。
> 最近核验：2026-08-14。
> 适用对象：Agent 系统需要知识时主动发起的结构化问路，以及从正式公共知识中选取一条最短可执行结论的词法检索。
> 证据上限：原 A–C 卡小样回放有效；D–K 与本批 L–W 卡最多完成当前交付验收和现有场景回放。主动问路的自然采用率、误命中成本、独立自然样本准确率与长期覆盖率仍待自然任务验证。2026-08-13 补记：本资产获得首个自然消费样本（关联 [#227（知识消费实验）](https://github.com/Eridanus117/agent-control/issues/227)S3R2，fresh 被试无诱导读取本卡集并经 `source` 定位 K2 后正确应用）；单样本支持按现有边界继续维护，不升级任何卡的证据等级，也不扩大投影范围。

本资产把现有 K 包中的可执行结论投影为「结构化问路登记＋BM25」检索卡。它只缩短知识发现与动作选择：完整解释、证据、例外、准入门、失效条件和最少复核步骤仍以 `source` 指向的 K 包为准；检索卡不是 K 包的替代物，也不单独扩大授权或结论范围。

当前最小路径是 Agent 需要知识时主动按 `stage`／`object` 或 action 名问路，再以 `operation`、`signals.aliases` 和查询文本做 BM25 排序，只取一张 `one-line-action`。本资产不建设索引服务、语义层、自动触发或注入实现。

## 最小登记 schema

每条登记只包含以下八个顶层字段；`signals.aliases` 保存同义词、界面文案和常见错误词形，供词法召回使用。

| 字段 | 最小语义 |
| --- | --- |
| `stage` | 会自然出现检索需求的工作阶段；也是第一层硬筛键。 |
| `object` | 当前操作的精确对象类别；也是第二层硬筛键。 |
| `operation` | 正在执行或准备决定的动作。 |
| `signals.aliases` | 事件中可观察的术语、界面文案、错误词形及中文别名。 |
| `one-line-action` | 查询命中后返回的一句最短可执行结论，不承载完整解释。 |
| `source` | 一个或多个正式当前 K 包；投影内容不得超出来源结论。 |
| `evidence` | 本卡的检索证据及其上限，不把回放结果升级为产品采用。 |
| `invalidates` | 查询命中后必须停止直接返回、转回来源包做最少复核的条件。 |

## 卡 A：派发回执

| 字段 | 登记值 |
| --- | --- |
| `stage` | `post-dispatch` |
| `object` | `orca.supervised-worker-dispatch` |
| `operation` | `validate-receipt-and-submission` |
| `signals.aliases` | `Orca Worker`、`worker-start`、`input_accepted`、`composer-pending`、`input-missing`、`tui-idle`、`dispatch 回执`、`mutation error`、`effectsApplied=false`、`dispatch-show`、`补交 Enter`、`重试` |
| `one-line-action` | 正式派发走高层路径；accepted 后按同一 Dispatch 区分文本呈现、提交与开始，只有确认 composer-pending 才补一次 Enter，input-missing 停止并保留证据；mutation 错误后先读精确状态。 |
| `source` | [K2（Orca 受监督派发的路径选择、mutation 回执与收口核验）](./orca-supervised-dispatch.md) |
| `evidence` | **小样回放有效**：关联任务 `task_b61df66cc5c0` 的派发点 BM25 top-1 命中本卡，得分 25.665，次名 3.292；证据只支持该真实任务决策点的回放排序。 |
| `invalidates` | Orca 升级或输入提交机制变化；`worker-*`／低层 Dispatch 的对象模型、索引或生命周期语义变化；mutation 回执与 `dispatch-show` 的关系变化。命中任一项时回到 K2 的最少复核步骤。 |

## 卡 B：三端指纹

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-acceptance` |
| `object` | `agent-plugin.installed-copy` |
| `operation` | `fingerprint-acceptance` |
| `signals.aliases` | `Plugin`、`Skill`、`三端`、`目标版本`、`版本化缓存`、`旧缓存`、`hash mismatch`、`SHA-256`、`CRLF`、`LF`、`换行噪声` |
| `one-line-action` | 先冻结目标版本并锁定精确缓存目录，再将 CRLF 规范化为 LF 比较 SHA-256；原始哈希与跨版本通配均不能定案。 |
| `source` | [K4（Claude Code 与 Codex Plugin 维护、验收的已验证陷阱）](./claude-plugin-maintenance.md)；[K6（跨端文件一致性验收必须先规范化换行）](./newline-normalized-acceptance.md) |
| `evidence` | **小样回放有效**：关联任务 `task_b61df66cc5c0` 的三端验收点 BM25 top-1 命中本卡，得分 30.454，次名 5.715；证据只支持该真实任务决策点的回放排序。 |
| `invalidates` | Claude／Codex 的安装语义、缓存布局或历史版本保留方式变化；目标 marketplace 类型变化；所有写盘端统一换行策略并有强制保证；对象扩展到对换行敏感的文件。命中任一项时分别回到 K4／K6 的最少复核步骤。 |

## 卡 C：快照新鲜度

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-capacity-decision` |
| `object` | `orca.codex-account-snapshot` |
| `operation` | `compare-window-usage` |
| `signals.aliases` | `Orca account`、`账户快照`、`额度`、`usedPercent`、`updatedAt`、`resetsAt`、`windowMinutes`、`消耗差值`、`扩产`、`最后已知值` |
| `one-line-action` | 仅在 `updatedAt` 严格前进且窗口身份不变时解释差值；否则只报陈旧的最后已知快照，`null` 保持未知。 |
| `source` | [K13（Orca 账户快照必须以 updatedAt 前进判定新鲜度）](./orca-account-snapshot-freshness.md) |
| `evidence` | **小样回放有效**：关联任务 `task_f94414eedaa9` 的额度扩产决策点 BM25 top-1 命中本卡，得分 19.881，次名 5.939；证据只支持该真实任务决策点的回放排序。 |
| `invalidates` | Orca 改变账户快照缓存、采集方式或 `updatedAt` 定义；新增的新鲜度、缓存年龄或强制刷新字段改变接纳门；Provider、账户窗口或权益字段不再共享同一快照边界；任务转到未核验环境或 Provider。命中任一项时回到 K13 的最少复核步骤。 |

## 卡 D：安全关联 Issue

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-github-publication` |
| `object` | `github.issue-reference` |
| `operation` | `format-non-closing-reference` |
| `signals.aliases` | `关联 #N`、`PR 正文`、`提交说明`、`父 Issue`、`close`、`closes`、`fixes`、`resolves`、`否定句`、`不关闭`、`closingIssuesReferences`、`误关` |
| `one-line-action` | 引用不应由本次交付关闭的 Issue 时使用「关联 #N」等无关闭关键词表述，不要让任何关闭关键词与编号相邻。 |
| `source` | [K3（GitHub 关闭关键词不解析否定句）](./github-closing-keywords.md) |
| `evidence` | **当前交付验收**：本次仅确认现有解析器可读取八字段，且结构化 `stage`／`object` 与词法信号可命中本卡；尚无自然任务的召回、误触发或产品采用证据。 |
| `invalidates` | `closingIssuesReferences` 不再对否定句返回被引用 Issue；GitHub 官方文档改变关闭引用解析语义；对象扩展到 K3 未实测的载体。命中任一项时回到 K3 的最少复核步骤。 |

## 卡 E：入口副本同步

| 字段 | 登记值 |
| --- | --- |
| `stage` | `post-entry-source-change` |
| `object` | `agent-system.entry-copy-set` |
| `operation` | `generate-install-check` |
| `signals.aliases` | `entry_sync`、`入口母本`、`副本漂移`、`状态不一致`、`targets.json`、`generate`、`--write-repository`、`三端安装`、`check`、`--scope repository`、`统一差异`、`换行规范化` |
| `one-line-action` | 母本或选节规则改动后依次生成、在授权范围安装、再用 `entry_sync check` 验收；未声明目标与未授权安装面不得外推。 |
| `source` | [K5（入口母本同步工具 entry_sync 的用途与用法）](./entry-sync.md) |
| `evidence` | **当前交付验收**：本次仅确认现有解析器可读取八字段，且结构化 `stage`／`object` 与词法信号可命中本卡；尚无自然任务的召回、误触发或产品采用证据。 |
| `invalidates` | 母本路径、`targets.json`、命令接口或目标声明改变；入口不再采用单一真源模型；任务需要写入未获授权的安装目标。命中任一项时回到 K5 的最少复核步骤。 |

## 卡 F：精确会话恢复

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-session-resume` |
| `object` | `coding-agent.session` |
| `operation` | `resume-exact-session` |
| `signals.aliases` | `resume --last`、`--continue`、`Session ID`、`Session name`、`最近会话`、`恢复错对象`、`并发终端`、`转录`、`任务接手`、`Run 继任`、`rebind`、`启动参数` |
| `one-line-action` | 并发现场只用已核对的 Session ID 或 name 精确恢复；恢复后仍重读任务合同、环境与启动参数，不把最近会话选择器当作执行者身份。 |
| `source` | [K8（编码 Agent 会话恢复必须绑定精确身份）](./session-resumption-identity.md) |
| `evidence` | **当前交付验收**：本次仅确认现有解析器可读取八字段，且结构化 `stage`／`object` 与词法信号可命中本卡；尚无自然任务的召回、误触发或产品采用证据。 |
| `invalidates` | Codex 或 Claude Code 改变最近会话选择器、精确 ID／name 恢复、转录或启动状态语义；Orca 增加已验证的活派 rebind；任务转到未核验主机或 Provider；精确 ID 仍恢复错对象。命中任一项时回到 K8 的最少复核步骤。 |

## 卡 G：GraphQL 写后恢复

| 字段 | 登记值 |
| --- | --- |
| `stage` | `post-remote-write-error` |
| `object` | `github.graphql-mutation` |
| `operation` | `reconcile-before-retry` |
| `signals.aliases` | `GraphQL mutation`、`clientMutationId`、`超时`、`部分成功`、`重试`、`重放`、`幂等`、`exactly-once`、`目标状态`、`远端回读`、`Project item`、`Issue node ID`、`PR head` |
| `one-line-action` | 写入报错或部分成功后，先按稳定操作身份、精确对象与目标值回读；已达目标就继续，明确未达才补做，无法唯一判断就停止新写入。 |
| `source` | [K11（GitHub GraphQL mutation 重试必须以远端目标状态为准）](./github-graphql-mutation-recovery.md) |
| `evidence` | **当前交付验收**：本次仅确认现有解析器可读取八字段，且结构化 `stage`／`object` 与词法信号可命中本卡；尚无自然任务的召回、误触发或产品采用证据。 |
| `invalidates` | GitHub schema 或官方文档将 `clientMutationId` 明定为服务端幂等键；目标 mutation 增加独立幂等键、条件写或事务合同；远端对象与事件回读语义改变；对象无法按稳定身份与目标状态复核。命中任一项时回到 K11 的最少复核步骤。 |

## 卡 H：三方席位身份

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-review-consumption` |
| `object` | `multi-session.review-evidence` |
| `operation` | `verify-seats-seals-and-comments` |
| `signals.aliases` | `seat_kind`、`run_id`、`consumer_generation`、`task_id`、`dispatch_id`、`comment_url`、`联合身份`、`稳定键`、`反向绑定`、`两轮回读`、`先密封后公开`、`verified=false`、`顺序锚定` |
| `one-line-action` | 按席位联合身份的稳定键机械生成映射并两轮回读，判定先密封后公开；terminal、同账号评论或返回顺序都不能代替运行身份。 |
| `source` | [K16（多 Session 审阅必须机械核验联合身份并先密封后公开）](./multi-session-review-identity.md) |
| `evidence` | **当前交付验收**：本次仅确认现有解析器可读取八字段，且结构化 `stage`／`object` 与词法信号可命中本卡；尚无自然任务的召回、误触发或产品采用证据。 |
| `invalidates` | Orca 的 Run、消费代次、Task、Dispatch、ask 或终端身份语义改变；GitHub 评论 URL、可信作者、目标 Issue 或编辑水位语义改变；CF-6、验证器 schema、密封哈希或两轮取证流程改变；任务改用无等价稳定身份与密封见证的后端。命中任一项时回到 K16 的最少复核步骤。 |

## 卡 I：三方审阅边界

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-decision-routing` |
| `object` | `agent-system.three-party-review` |
| `operation` | `decide-review-or-owner-route` |
| `signals.aliases` | `CF-6`、`C3=A`、`三方审阅`、`替代授权`、`三席一致`、`普通交付验收`、`低风险可逆`、`实施取舍`、`承载位置`、`产品采用`、`长期依赖`、`父目标`、`授权变化` |
| `one-line-action` | 只有负责人已明确授予替代决定权、且事项属已批合同内低风险可逆的实施取舍或承载位置时才进入三方审阅；三席一致且身份、密封与映射门全通过才能消费决定，否则转负责人。 |
| `source` | [K18（三方审阅只替代已授权决定，且必须三席一致后落地）](./three-party-review-consensus.md) |
| `evidence` | **当前交付验收**：本次仅确认现有解析器可读取八字段，且结构化 `stage`／`object` 与词法信号可命中本卡；尚无自然任务的召回、误触发或产品采用证据。 |
| `invalidates` | 负责人改变替代授权、C3=A 边界、席位或回避规则；Orca、CF-6、验证器或密封—公开状态机改变；自然样本出现错消费、身份错绑或否决高假阳性；本仓项目入口或当前合同改变常规验收与负责人专属决定边界。命中任一项时回到 K18 的最少复核步骤。 |

## 卡 J：Token 燃烧测量

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-capacity-decision` |
| `object` | `codex.token-burn` |
| `operation` | `measure-daily-token-burn` |
| `signals.aliases` | `ccusage codex daily`、`totalTokens`、`outputTokens`、`inputTokens`、`cacheReadTokens`、`costUSD`、`Token 日聚合`、`燃烧`、`周窗百分比`、`旧快照`、`长 Session`、`继续加派`、`降级停止` |
| `one-line-action` | 用 `ccusage codex daily --json --offline` 的当日 `totalTokens` 增量与组成作相对燃烧主信号；`costUSD` 不是账单，Token 与周窗不得固定换算，单 Session 归因另需回执。 |
| `source` | [K19（自治运营以 Token 日聚合测燃烧，以活跃路径排除集守住 worktree 清理）](./autonomous-ops-measurement-and-cleanup.md) |
| `evidence` | **当前交付验收**：本次仅确认现有解析器可读取八字段，且结构化 `stage`／`object` 与词法信号可命中本卡；尚无自然任务的召回、误触发或产品采用证据。 |
| `invalidates` | `ccusage` 改变日聚合扫描、字段、total 组成、价目或日期边界；本地日志不完整或任务跨设备；Provider 改变 Token、缓存、券或周窗计量关系；出现更细、更新鲜且可核验的第一方消耗数据。命中任一项时回到 K19 的最少复核步骤。 |

## 卡 K：worktree 活跃排除集

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-worktree-delete` |
| `object` | `orca.worktree` |
| `operation` | `build-active-path-exclusion` |
| `signals.aliases` | `worktreePath`、`活跃排除集`、`terminal list`、`分支名碰撞`、`孤儿清理`、`worker_done`、`completed`、`released`、`failed`、`远端 head`、`git status clean`、`Hook`、`force` |
| `one-line-action` | 删除前先把未精确释放终端的 `worktreePath` 归一化为排除集；候选还必须有任务终局、远端持久化、干净工作树和连带影响证据，任一项未知就保留且禁用 force。 |
| `source` | [K19（自治运营以 Token 日聚合测燃烧，以活跃路径排除集守住 worktree 清理）](./autonomous-ops-measurement-and-cleanup.md) |
| `evidence` | **当前交付验收**：本次仅确认现有解析器可读取八字段，且结构化 `stage`／`object` 与词法信号可命中本卡；尚无自然任务的召回、误触发或产品采用证据。 |
| `invalidates` | Orca 终端列表不再返回 `worktreePath`，或 terminal、tab、pane 与 worktree 身份关系改变；标准 Worker 释放改为逐对象可证的 worktree 删除；Task／Dispatch 终局、远程 placement、删除选择器或 Hook 语义改变；新事故证明四项证据仍会误删有主对象。命中任一项时回到 K19 的最少复核步骤。 |

## 卡 L：任务提交核验

| 字段 | 登记值 |
| --- | --- |
| `stage` | `post-dispatch` |
| `object` | `orca.supervised-worker-dispatch` |
| `operation` | `confirm-task-submission` |
| `signals.aliases` | `任务停在输入框`、`文本没有出现`、`input-missing`、`composer-pending`、`tui-idle`、`codex_liveness`、`没有开始执行`、`terminal read`、`补交回车`、`input_accepted`、`任务已进入对话`、`user_takeover`、`retained` |
| `one-line-action` | `input_accepted` 不证明送达；Codex 先用精确 Dispatch 三态验活，其他 Provider 用精确观察面区分 composer-pending 与 input-missing，只对前者补一次 Enter，并按真实释放回执处理 retained。 |
| `source` | [K2（Orca 受监督派发的路径选择、mutation 回执与收口核验）](./orca-supervised-dispatch.md) |
| `evidence` | **当前交付验收**：投影已按 K2 的 1.4.181 增量区分 composer-pending／input-missing，并保持对结论 2、3 的忠实；既有解析器可读取八字段，尚无本卡更新后的独立自然检索旁路样本或产品采用证据。 |
| `invalidates` | Orca 或被派发端改变 `input_accepted`、输入提交、手工 Enter、`retained` 或释放回执语义；上游输入提交问题已有发布修复；任务转到未核验版本或 Provider。命中任一项时回到 K2 的最少复核步骤。 |

## 卡 M：Plugin 升级落盘验收

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-acceptance` |
| `object` | `agent-plugin.installed-copy` |
| `operation` | `verify-plugin-upgrade-effect` |
| `signals.aliases` | `安装成功但内容没变`、`已安装项`、`卸载重装`、`uninstall`、`install`、`运行端副本`、`directory marketplace`、`remove`、`add` |
| `one-line-action` | 安装输出不能证明升级落盘：Claude 已安装项先卸载再安装，Codex directory marketplace 走 remove／add，最后核对精确目标版本运行端副本。 |
| `source` | [K4（Claude Code 与 Codex Plugin 维护、验收的已验证陷阱）](./claude-plugin-maintenance.md) |
| `evidence` | **当前交付验收**：本次仅确认投影忠实于 K4 的结论 1、4，现有解析器可读取八字段，并在现有场景回放中与同桶卡 B 排序区分；尚无独立自然旁路样本或产品采用证据。 |
| `invalidates` | Claude 或 Codex 改变已安装项升级、uninstall／install、remove／add、directory marketplace 或运行端缓存语义；目标 marketplace 类型变化。命中任一项时回到 K4 的最少复核步骤。 |

## 卡 N：陈旧快照标注

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-capacity-decision` |
| `object` | `orca.codex-account-snapshot` |
| `operation` | `classify-stale-snapshot` |
| `signals.aliases` | `最后已知快照`、`时间戳没动`、`缓存读数`、`null 未知`、`status=ok`、`命令调用时刻`、`同一 updatedAt`、`旧读数` |
| `one-line-action` | 新的命令调用不等于新快照；`updatedAt` 未前进时只报告带陈旧标志的最后已知值，缺失与 `null` 保持未知，不据此解释真实账户无变化。 |
| `source` | [K13（Orca 账户快照必须以 updatedAt 前进判定新鲜度）](./orca-account-snapshot-freshness.md) |
| `evidence` | **当前交付验收**：本次仅确认投影忠实于 K13 的结论 1、2，现有解析器可读取八字段，并在现有场景回放中与同桶卡 C 排序区分；尚无独立自然旁路样本或产品采用证据。 |
| `invalidates` | Orca 改变账户快照缓存、采集或 `updatedAt` 定义；新增新鲜度、缓存年龄或强制刷新字段；同一时间戳不再代表同一快照；任务转到未核验环境或 Provider。命中任一项时回到 K13 的最少复核步骤。 |

## 卡 O：否定关闭词审计

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-github-publication` |
| `object` | `github.issue-reference` |
| `operation` | `audit-negated-closing-keywords` |
| `signals.aliases` | `does not close`、`not fix`、`不关闭`、`否定语境`、`关键词加编号`、`closingIssuesReferences`、`正文扫描`、`提交说明扫描` |
| `one-line-action` | 发布前扫描 PR 正文与提交说明；「不关闭 #N」等否定句仍会被解析，发现关闭关键词邻接编号就改写为「关联 #N」。 |
| `source` | [K3（GitHub 关闭关键词不解析否定句）](./github-closing-keywords.md) |
| `evidence` | **当前交付验收**：本次仅确认投影忠实于 K3 的已验证否定句陷阱，现有解析器可读取八字段，并在现有场景回放中与同桶卡 D 排序区分；尚无独立自然旁路样本或产品采用证据。 |
| `invalidates` | `closingIssuesReferences` 不再把否定句中的关闭关键词与 Issue 关联；GitHub 官方文档改变关闭引用解析；对象扩展到 K3 未实测的载体。命中任一项时回到 K3 的最少复核步骤。 |

## 卡 P：同步目标边界

| 字段 | 登记值 |
| --- | --- |
| `stage` | `post-entry-source-change` |
| `object` | `agent-system.entry-copy-set` |
| `operation` | `verify-declared-target-scope` |
| `signals.aliases` | `目标未声明`、`新增副本`、`repository scope`、`安装目标`、`暂存目录`、`用户目录`、`targets.json`、`选节规则`、`源到目标映射` |
| `one-line-action` | 先以 `targets.json` 与生成映射确认目标全集；未声明副本不受同步保护，generate 只产暂存物，用户侧安装必须另有当次授权。 |
| `source` | [K5（入口母本同步工具 entry_sync 的用途与用法）](./entry-sync.md) |
| `evidence` | **当前交付验收**：本次仅确认投影忠实于 K5 的声明目标与安装授权边界，现有解析器可读取八字段，并在现有场景回放中与同桶卡 E 排序区分；尚无独立自然旁路样本或产品采用证据。 |
| `invalidates` | 母本路径、`targets.json`、生成映射、暂存目录或命令接口改变；入口不再使用单一真源模型；安装授权边界被当前权威替代。命中任一项时回到 K5 的最少复核步骤。 |

## 卡 Q：恢复后状态复核

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-session-resume` |
| `object` | `coding-agent.session` |
| `operation` | `revalidate-contract-and-launch-state` |
| `signals.aliases` | `恢复后重读`、`启动参数丢失`、`权限模式`、`settings 重读`、`compact 摘要`、`外部合同`、`工作树`、`当前授权` |
| `one-line-action` | 精确恢复只选对转录；继续工作前仍重读远端任务合同、工作树、权限与启动参数，不能用聊天历史替代外部当前状态。 |
| `source` | [K8（编码 Agent 会话恢复必须绑定精确身份）](./session-resumption-identity.md) |
| `evidence` | **当前交付验收**：本次仅确认投影忠实于 K8 的结论 3 与外部合同边界，现有解析器可读取八字段，并在现有场景回放中与同桶卡 F 排序区分；尚无独立自然旁路样本或产品采用证据。 |
| `invalidates` | Codex、Claude Code 或 Orca 改变精确恢复、转录、启动参数、权限或活派接手语义；任务转到未核验主机或 Provider；外部合同恢复规则变化。命中任一项时回到 K8 的最少复核步骤。 |

## 卡 R：GraphQL 写入定位符

| 字段 | 登记值 |
| --- | --- |
| `stage` | `post-remote-write-error` |
| `object` | `github.graphql-mutation` |
| `operation` | `identify-operation-object-and-target` |
| `signals.aliases` | `clientMutationId 不是幂等键`、`客户端关联字段`、`稳定操作身份`、`对象 node ID`、`字段 ID`、`目标值`、`多对象顺序`、`唯一物理写入者` |
| `one-line-action` | 不要把 `clientMutationId` 当服务端幂等保证；按稳定操作身份、精确对象 ID、目标值与既定顺序定位本次写入，再逐对象回读。 |
| `source` | [K11（GitHub GraphQL mutation 重试必须以远端目标状态为准）](./github-graphql-mutation-recovery.md) |
| `evidence` | **当前交付验收**：本次仅确认投影忠实于 K11 的结论 1、3，现有解析器可读取八字段，并在现有场景回放中与同桶卡 G 排序区分；尚无独立自然旁路样本或产品采用证据。 |
| `invalidates` | GitHub 将 `clientMutationId` 明定为服务端幂等键；目标 mutation 增加独立幂等键、条件写或事务合同；对象、事件或 PR head 的回读语义变化。命中任一项时回到 K11 的最少复核步骤。 |

## 卡 S：先密封后公开

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-review-consumption` |
| `object` | `multi-session.review-evidence` |
| `operation` | `verify-sealed-before-publication` |
| `signals.aliases` | `三封齐`、`密封消息`、`公开前`、`判定哈希`、`先票锚定`、`原封公开`、`协调者占席`、`读取 Delivery 之前`、`revision hash` |
| `one-line-action` | 三席先分别密封完整判定，三封齐后才原封公开并比对哈希；协调者若占席，必须在读取其他评审 Delivery 前完成自己的密封。 |
| `source` | [K16（多 Session 审阅必须机械核验联合身份并先密封后公开）](./multi-session-review-identity.md) |
| `evidence` | **当前交付验收**：本次仅确认投影忠实于 K16 的结论 3，现有解析器可读取八字段，并在现有场景回放中与同桶卡 H 排序区分；尚无独立自然旁路样本或产品采用证据。 |
| `invalidates` | Orca 改变 `ask`、Delivery、Run、Task 或 Dispatch 语义；GitHub 评论回读或编辑水位语义变化；CF-6 的密封、公开、哈希或席位规则变化；负责人改变替代授权边界。命中任一项时回到 K16 的最少复核步骤。 |

## 卡 T：决定与验收分流

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-decision-routing` |
| `object` | `agent-system.three-party-review` |
| `operation` | `classify-decision-versus-acceptance` |
| `signals.aliases` | `既定成功条件`、`常规验收`、`产品取舍`、`负责人专属`、`预授权谓词`、`新方向`、`产品边界`、`授权类别`、`C3=A` |
| `one-line-action` | 先区分「既定成功条件是否有证据」与「选择新产品／授权方向」：前者走常规验收，后者只有已有替代授权且落在 C3=A 时才进入三方审阅。 |
| `source` | [K18（三方审阅只替代已授权决定，且必须三席一致后落地）](./three-party-review-consensus.md) |
| `evidence` | **当前交付验收**：本次仅确认投影忠实于 K18 的决定／验收分流，现有解析器可读取八字段，并在现有场景回放中与同桶卡 I 排序区分；尚无独立自然旁路样本或产品采用证据。 |
| `invalidates` | 负责人改变三方替代授权、C3=A、负责人专属类别或回避规则；本仓项目入口或当前合同改变常规验收边界；CF-6 触发边界变化。命中任一项时回到 K18 的最少复核步骤。 |

## 卡 U：日聚合证据标注

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-capacity-decision` |
| `object` | `codex.token-burn` |
| `operation` | `label-partial-day-and-attribution` |
| `signals.aliases` | `部分日`、`采集时刻`、`跨设备日志`、`单 Session 归因`、`完整账本`、`cache-read 占比`、`账单`、`估算`、`current day` |
| `one-line-action` | 记录采集时刻并把当日未结束样本标为部分日；日聚合只支持本机总燃烧与组成，`costUSD` 不是账单，单 Session 归因必须另有回执。 |
| `source` | [K19（自治运营以 Token 日聚合测燃烧，以任务运行态保留集收口 worktree 清理）](./autonomous-ops-measurement-and-cleanup.md) |
| `evidence` | **当前交付验收**：本次仅确认投影忠实于 K19 的日聚合证据边界，现有解析器可读取八字段，并在现有场景回放中与同桶卡 J 排序区分；尚无独立自然旁路样本或产品采用证据。 |
| `invalidates` | `ccusage` 改变日聚合扫描、字段、total 组成、价目或日期边界；本地日志不完整或任务跨设备；Provider 计量关系改变；出现更细且可核验的一手消耗数据。命中任一项时回到 K19 的最少复核步骤。 |

## 卡 V：运行任务保留集

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-worktree-delete` |
| `object` | `orca.worktree` |
| `operation` | `build-running-task-retention-set` |
| `signals.aliases` | `dispatched`、`running`、`任务绑定 worktree`、`main worktree`、`受保护对象`、`保留集 R`、`Ready 终端`、`待清队列`、`零未提交`、`零未推送`、`精确 path` |
| `one-line-action` | 先以 dispatched／running 任务绑定、两仓 main 与明确保护对象组成保留集 R；其余候选仍逐个核验零未提交、零未推送和连带影响，禁止按分支名或 Ready terminal 判活。 |
| `source` | [K19（自治运营以 Token 日聚合测燃烧，以任务运行态保留集收口 worktree 清理）](./autonomous-ops-measurement-and-cleanup.md) |
| `evidence` | **当前交付验收**：本次仅确认投影忠实于 K19 现行的运行任务保留集结论，现有解析器可读取八字段，并在现有场景回放中与同桶卡 K 排序区分；尚无独立自然旁路样本或产品采用证据。 |
| `invalidates` | Task／Dispatch 运行态或 worktree 绑定语义变化；两仓 main 或保护对象登记变化；标准释放开始逐对象证明删除；远程 placement、Git 安全门或删除连带影响语义变化。命中任一项时回到 K19 的最少复核步骤。 |

## 卡 W：PowerShell 多行正文传输

| 字段 | 登记值 |
| --- | --- |
| `stage` | `pre-github-publication` |
| `object` | `github.multiline-markdown-body` |
| `operation` | `transfer-and-verify-powershell-markdown` |
| `signals.aliases` | `PowerShell`、`GitHub CLI`、`gh`、`多行正文`、`Markdown`、`here-string`、`反引号`、`System.Object[]`、`--body-file`、`ConvertFrom-Json`、`-join`、`UTF-8`、`CRLF`、`LF`、`逐字回读` |
| `one-line-action` | Windows PowerShell 中先用单引号字面 here-string 构造正文，经 UTF-8 无 BOM 临时文件和 `--body-file` 传递，再从 JSON 标量回读并按同一换行规则逐字验收；既有 `--jq .body` 输出须先显式连接。 |
| `source` | [K17（Windows 下 PowerShell／GitHub CLI 多行 Markdown 传输边界）](./windows-powershell-multiline-transfer.md) |
| `evidence` | **当前交付验收**：投影忠实于 K17 的六条最短可靠写法；关联 [#30（PowerShell 多行正文摩擦）](https://github.com/Eridanus117/agent-control/issues/30)的 W7 当前版本核验再次直接复现数组边界与显式连接结果。主动问路的自然采用率、误命中成本和独立自然样本准确率仍待验证。 |
| `invalidates` | PowerShell 的 here-string／原生命令输出语义，GitHub CLI 的 `--body-file`／JSON 回读合同，Git 的提交说明文件合同，或任务的宿主、编码、正文规模与 K17 适用边界发生变化。命中任一项时回到 K17 的最少复核步骤。 |

## 已知覆盖缺口与检索边界

1. **错仓／标题错配是覆盖未命中。** K2 当前不含 `contractRepo`、`executionRepo` 与 Issue 标题身份的结论，因此卡 A 也不能覆盖错仓或标题错配。该缺口与 P0-3 的修复方向一致；来源知识补齐并重新通过两道准入门以前，不把这些词面别名直接写成可执行结论。
2. **裸自由文本 BM25 有改述误排。** 探索性改述「配额读数没变还能否加开工作者」曾让卡 A 以 2.639 略高于卡 C 的 2.525。这个样本支持 `stage`／`object` 硬筛的必要性，不构成建设语义层的证据。
3. **证据不高于小样回放，新卡仅当前交付验收。** 原 A–C 卡的直接验证覆盖两项真实任务、三个决策点和一次改述误排；D–K 与本批 L–W 卡只验证 schema 解析、结构化 CLI 与现有场景回放。它们都没有验证主动问路的自然采用率、误命中成本、独立自然样本准确率、长期召回率或 Agent 实际采用。只有自然任务出现经人工确认的改述型 top-3 漏检时，才按 [K14（公共知识检索不以篇数启动向量层）](./public-knowledge-retrieval-activation.md) 进入语义对照评估。2026-08-13 补记：关联 [#227（知识消费实验）](https://github.com/Eridanus117/agent-control/issues/227)S3R2 提供本资产首个自然消费样本——fresh 被试在无诱导任务中自行读取本卡集，并经卡内 `source` 定位 K2 后按 rubric 4/4 正确应用；该样本只支持「被自然发现并导向来源包」这一路径存在，不构成主动问路采用率、误命中成本或长期召回的证据，是否扩大投影范围仍按 9-D3 与本节边界判定。
4. **「任务看似通用 → 零检索」是入口层盲区，不是本资产的排序缺陷。** 关联 [#227（知识消费实验）](https://github.com/Eridanus117/agent-control/issues/227)中 S1（PowerShell 多行正文）两次 run 全程零文件读取；卡 W 虽可按 `pre-github-publication`／`github.multiline-markdown-body` 查询，但 Agent 没有主动问路就没有取卡机会。关联 [#251（动作型知识触发）](https://github.com/Eridanus117/agent-control/issues/251)的 251-D1 已否决把查询挂到动作检查点作实时注入；当前对策是把 `stage`／`object` 与 action 名问路做得便宜、好记、由 Agent 主动选择，本资产不扩成自动触发或注入面。

## 维护规则

- 来源 K 包结论退出当前知识、命中 `invalidates`，或 `one-line-action` 与来源正文不再同义时，受影响卡片立即停止直接返回并随来源增量复核。
- 新卡先在来源 K 包中逐条通过价值门与可信门；检索投影不能成为过程证据进入当前知识的旁路。
- 只在自然任务中记录结构化事件、top-k、人工确认的命中／覆盖缺口和实际省掉的决策分支；不为扩大样本而制造任务，也不把小样回放写成产品采用。
