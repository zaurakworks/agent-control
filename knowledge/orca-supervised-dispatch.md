# K2：Orca 受监督派发的路径选择、mutation 回执与收口核验

> 状态：正式当前公共知识。
> 最近核验：2026-08-13。
> 适用对象：本机 Orca CLI 的高层受监督派发（`worker-start` 等 orchestration 动词），以及获得明确实验授权的低层 `dispatch --inject` 探测；Claude Code 与 Codex 作为被派发端。
> 环境：Windows 11 Pro 10.0.26200；Orca 1.4.182 packaged（当前运行水位）；2026-08-10 至 2026-08-11 多个真实并行波次及一次低层 dummy 派发夹具仍绑定 1.4.177，2026-08-12 的 fresh Codex 自然样本绑定 1.4.180，2026-08-13 增补 1.4.181 的低层／高层对照与两个自然 Codex 验活样本（样本量见正文）；2026-08-13 波次4／5 另增两个 fresh Claude 高层 composer-pending 自然样本与同窗 codex 零竞态对照，同日波次6 与对抗席再增 3 例自然样本（claude W250／F261、codex P256A）与首个 dispatch_liveness 工具／人工分歧样本；升级到 1.4.182 后又完成一次当前高层 Codex Dispatch 的结构化最少复核（历史样本回执未单独记录 Provider 版本号，仍按各自当日运行水位归档）。
> 版本边界：被派发端样本含 Claude Code 2.1.227–2.1.228 与 Codex CLI 0.147.0；Orca 升级、Codex JSONL 事件变化、MCP 启动行为变化或上游[关联 #13821（输入提交竞态报告）](https://github.com/stablyai/orca/issues/13821)状态变化是失效信号。

## 回答的问题与价值门

用 Orca 把任务派发给 Claude／Codex Worker 并收口时，应走哪条命令路径？为什么派发后任务可能停着没有开始执行？低层派发为什么不能直接使用 `worker-*` 生命周期索引？mutation 回执显示未落盘时能否立即重试？视觉 tab 消失是否足以证明后台 PTY 已退出？

本仓每个并行波次都要做派发与收口（近两批 20 次以上）；高层路径、输入提交竞态与释放分支已反复命中。新增的四个 Codex fresh 样本会直接影响派发验活，JSONL 验活工具已把 `turn.started`／持久 rollout 的 `task_started` 变成可按精确 Dispatch 读取的开始证据；mutation 回执和 tab／PTY 现象虽各只有一个低层 dummy 样本，但它们直接约束错误恢复与资源处置的安全顺序。因此这些有界结论均通过价值门；自然竞态收益、MCP 因果解释与固定发生率不过可信门，只保留为任务证据或明确未知。

## 2026-08-12 至 2026-08-13 版本失效复核

Orca 从本包原绑定的 1.4.177 升至 1.4.180，已经命中“Orca 升级”失效条件，因此必须先复核，不能把旧版本号静默沿用。本次采用以下一手运行来源做最少复核：

1. `orca status --json` 直接返回当前 packaged 运行端 `appVersion: 1.4.180`、`runtime.state: ready`；
2. `orca skills get orchestration` 返回 1.4.180 动态指南，正式受监督路径仍以 `worker-start` 组合高层生命周期，低层 `dispatch --inject` 仍只作为自定义路径保留，收口仍要求按当前回执选择 `worker-release`、复用、保留或结果未知分支；
3. 本次真实高层派发的 `worker-show` 返回 `state: ready`、`stage: input_accepted` 与精确 agent terminal，`dispatch-show` 返回同一 Dispatch；注入任务已经进入当前 Codex 对话，未补 Enter。这个单次成功样本只证明 1.4.180 当前高层路径可用，不足以推翻“`input_accepted` 不保证已提交”这一非必现结论；
4. Orca 上游[关联 #13821（输入提交竞态报告）](https://github.com/stablyai/orca/issues/13821)在本次 1.4.181 复核时仍为 OPEN；最新远端更新仍是 1.4.180 自然 cohort 的补充，没有已发布修复或新状态语义。
5. 1.4.180 自动更新到 1.4.181 后，`orca status --json` 再次返回 runtime `ready`；从同一 1.4.181 二进制读取的完整 orchestration 动态指南仍把正式受监督路径定义为 `worker-start`，低层 `dispatch --inject` 仍不获得高层 Worker 生命周期。
6. 关联 [#211（tui-idle 竞态对照）](https://github.com/Eridanus117/agent-control/issues/211)在 Windows／Claude Code 2.1.229 上预注册重跑 A／B 各 5 次：A 臂“`tui-idle` 成功＋低层注入 accepted”为 `input-missing 5/5`，B 臂高层 `worker-start` 为 `submitted 5/5`；两臂均为 `composer-pending 0/5`。计入作废首轮的探索样本后，高层为 submitted `7/7`，低层另有 6 条 Task 已失败、终端已消失而 Dispatch 仍为 dispatched 的记录。
7. 关联 [#216（Mode C 混合试点第一阶段）](https://github.com/Eridanus117/agent-control/issues/216)的 1.4.181 自然波次中，两个 Codex 高层 Dispatch 都被精确 JSONL 三态判为“已开始”，与人工判定分歧 `0/2`；两例均未出现先前 cohort 的 MCP 启动异常签名。这个小样本证明当前高层路径仍可用，不证明输入竞态已经修复。
8. 同日自动更新到 1.4.182 后，`orca status --json` 返回 `appVersion: 1.4.182`、runtime `ready`；从同一二进制读取的完整 orchestration 动态指南仍以 `worker-start` 组合正式受监督路径，把 `dispatch --inject` 保留为低层自定义路径，并要求按当前回执在复用、`worker-release`、保留和结果未知分支之间收口。
9. 本次真实高层 Codex Dispatch 的 `worker-show` 返回 `state: ready`、`stage: input_accepted` 与精确 agent terminal，`dispatch-show` 返回同一 Dispatch；`tools/codex_liveness` 以精确 `taskId + dispatchId` 将同一任务判为“已开始”，Codex CLI 仍为 0.147.0 且无 schema 警告。这个单次成功样本只证明 1.4.182 当前高层路径与结构化验活仍可用；它既不把 `input_accepted` 升级成已提交／已开始，也不证明输入竞态已修复。
10. Orca 上游[关联 #13821（输入提交竞态报告）](https://github.com/stablyai/orca/issues/13821)仍为 OPEN，最新更新仍是 2026-08-13 的 1.4.181 三态样本，没有已发布修复或新状态语义。

**复核结论：高层默认与 `input_accepted` 边界继续成立，低层状态模型保留 1.4.181 新证据，1.4.182 只刷新当前运行水位。** 1.4.182 的动态指南与当前真实高层样本没有把 accepted 升级为“文本已呈现／已提交／已开始”，也没有消除高低层生命周期边界；关联 [#211（tui-idle 竞态对照）](https://github.com/Eridanus117/agent-control/issues/211)增加的 `input-missing` 状态仍未被后续证据推翻。2e 的自然 Provider 分布与 2f 的 W250 工具／人工分歧都是绑定历史样本的有界事实，本次没有新样本改变其计数、因果边界或工具语义，因此继续成立但不升级可信等级。结论 4、5 的 mutation／双 pane 直接夹具仍只绑定 1.4.177，不能写成在 1.4.182 已全量重放；结论 3 的释放相关性也没有在本次仍运行的 Dispatch 上补新后态。版本水位与当前高层复核随本次更新，其余结论保持原有证据边界。

## 可直接复用的结论

### 1. 正式受监督派发统一走高层路径；低层 Dispatch 不在 `worker-*` 生命周期索引内

Orca 1.4.177 的实测中，`worker-release`、`worker-abandon` 等生命周期动词只识别高层 `worker-start` 创建的受监督执行。对一个刚创建、状态正常且 `dispatch-show` 可查的低层 Dispatch 执行 `worker-abandon`，仍返回 `dispatch_not_found`；后续 dummy 样本又确认 `worker-show`、`worker-read` 与 `worker-release` 均缺少该低层 Dispatch 的 agent-terminal 索引。既往 10 次收口失败全部源于这条路径断层，而非动词本身不可靠；高层路径同批 13/13 派发与释放正常。

1.4.181 的关联 [#211（tui-idle 竞态对照）](https://github.com/Eridanus117/agent-control/issues/211)补了一条不同形状的同域证据：6 个低层 `input-missing` Task 被明确记为失败、精确终端已处置后，对应 Dispatch 仍停在 dispatched；同实验的 7 个高层样本均正常 `worker_done` 并 released。它不等于重跑 1.4.177 的全部四个 `worker-*` 动词，但足以继续否定“低层记录会自动进入高层资源收口闭环”。

因此，正式派发一律使用 `worker-start`；低层 `dispatch` 只用于合同明确授权的探测。低层交付仍可写入 Run 的 Task result、Dispatch 记录与 `worker_done`，但不能假设高层归档、读取或释放动词会接管其终端资源。收到 `dispatch_not_found` 时，先核对对象来源与 `dispatch-show`，不要靠重复调用或自建租约恢复。

### 2. `input_accepted` 不等于任务已提交

`worker-start` 注入任务文本后的 `input_accepted` 只是注入受理回执，不保证文本已在被派发端提交执行。实测竞态高频且非必现：Claude 端一波 5/6、另一波 10/11 出现任务文本停在输入框；Codex 端 1/3。后续六次配对样本中，手工补 Enter 的 3 次均正常启动，另外 3 次无需干预。

Codex 派发后先运行 [`tools/codex_liveness`](../tools/codex_liveness/README.md)，用精确 `taskId + dispatchId` 读取持久 rollout：“未提交”表示没有绑定两项身份的用户消息，“已提交”表示消息已出现但没有关联的 turn 启动事件，“已开始”才表示关联 turn 已有 `task_started`。这一结构化结果替代先刮终端标题／正文和固定等待约 30 秒的猜测；前两种状态只是当前快照，不单独授权补 Enter、重派、释放或失败判定。只有 JSONL 不可读、schema 命中失效条件或目标不是 Codex 时，才退回对应 Provider 的精确观察面；补交仍只能沿原身份一次并按当前动态指南复核。输入竞态及六次 preamble 字节数证据已进入上游 stablyai/orca#13821；现有六次样本未显示 5,571–5,728 字节区间内的单调长度关系，不能据此把增大固定延迟当作已验证对策。

2026-08-12、Orca 1.4.180 的同一自然波次又出现四个 fresh Codex 样本（V1／V6／V7／S1）：四个都在 `input_accepted` 后没有真正开始，沿原身份补交一次后恢复，且没有重派；四个终端也都同时出现 `MCP startup interrupted` 或 `starting: codex_apps` 启动签名。这个 4/4 只通过了“本批次有界相关性”的可信门：它是第一条可复用触发线索，但样本来自自然运营而非预注册对照，缺少未命中样本中的同签名基线，也没有隔离 MCP 初始化与输入提交时序。因此验活时可以顺手记录该签名，不能把它当作竞态的充分条件、必要条件、因果机制或自动点火依据。

1.4.181 的关联 [#211（tui-idle 竞态对照）](https://github.com/Eridanus117/agent-control/issues/211)把验活结果空间从二态补成三态：`submitted` 表示任务进入对话或已经有提交后活动；`composer-pending` 表示完整文本仍在可编辑输入区，沿原身份一次 Enter 后同一 Task 开始；`input-missing` 表示回执 accepted，但两次读取都没有文本进入对话或 composer，且一次 Enter 后仍未开始。A 臂的 `input-missing 5/5` 直接证明 `tui-idle` 与 accepted 都不是文本送达保证；它比较的是“等待＋低层注入”和高层路径的组合，不能推出等待本身导致丢失。一次 Enter 只覆盖已确认的 `composer-pending`，不能拿来修复 `input-missing`，也不能以新建第二个 Task／Dispatch 猜测恢复。

同夜 1.4.181 样本没有复现 `composer-pending`：关联 [#211（tui-idle 竞态对照）](https://github.com/Eridanus117/agent-control/issues/211)的 14 次主样本与早停样本均为 0，关联 [#216（Mode C 混合试点第一阶段）](https://github.com/Eridanus117/agent-control/issues/216)的两个自然 Codex 高层样本也都直接开始且没有 MCP 启动异常签名。把它与先前 1.4.180 正例中 4/4 MCP 签名并列，只能形成“按 MCP 签名分层保留命中／未命中样本”的条件性观察线索；样本跨 Provider、路径和版本，不能推出 composer 竞态依赖 MCP 异常、升级已经修复竞态或零复现等于零风险。

**2026-08-13 波次4 的两个自然样本已把上述零复现负事实替代**：W229（fresh Claude，高层 `worker-start` 新建 worktree）与 F229（fresh Claude，高层 `worker-start` 进既有 worktree）都出现完整任务文本停在输入框、Ctx/In/Out 全 0、终端保持通用「Claude Code」标题的 composer-pending 签名，各沿原终端一次 Enter 后进入工作态（标题变任务派生名）；两例均未见 MCP 启动横幅（与 codex 4/4 MCP 签名 cohort 不同源）。同窗对照：波次4 claude fresh 4 次派发 2 例竞态、codex 5 次派发 0 例；波次5 竞态 0（其中 claude 席 1 次派发未复现）。关联 [#31（Orca 生命周期断裂）](https://github.com/Eridanus117/agent-control/issues/31)累计 claude fresh composer-pending 已达 5 例。这组样本只通过「有界相关性」可信门：composer 竞态在当前高层路径上仍会自然发生，且近两波正例集中在 claude fresh 派发端；样本来自自然运营而非预注册对照，不能推出 codex 免疫、claude 固定发生率、路径因果或 MCP 签名的必要性。

**同日（2026-08-13）波次6 与对抗席增量**：W250（fresh claude，波次6）、F261（fresh claude 进既有 worktree）各再现 composer-pending 1 例，均沿原终端单次 Enter 恢复；P256A（fresh codex，对抗席）1 例，终端可见「Starting MCP servers (3/4): codex_apps」启动横幅与粘贴文本未提交同现，使 codex fresh 竞态例的 MCP 签名相关性从 4/4 增至 5/5。当日汇总（含早间 F236）：claude fresh 派发竞态率当日 5/8，codex 1/10——Provider 不对称证据继续加厚。全部仍为自然运营样本：不能推出 codex 免疫、claude 固定发生率、路径因果，也不能把 MCP 签名升级为充分或必要条件。

派发后验活与补交现已由 [`tools/dispatch_liveness`](../tools/dispatch_liveness/README.md)（关联 [#246（派发后三态验活与单次点火工具）](https://github.com/Eridanus117/agent-control/issues/246)，经 4 项对抗缺陷修缺与未参与者窄复验后合入）承载：`observe` 优先读取 `worker-read` 的精确 Provider transcript，user-role 消息同时含当前 Task／Dispatch 才判 `submitted`；`composer-pending` 要求 transcript 可取得、尚无该 user 消息、viewport 末端精确标记与已适配可编辑输入 footer 同时成立；仅有标记、渲染歧义或 transcript 不可得一律保守归 `input-missing` 且不发 Enter。点火路径以 OS 用户唯一领取域的原子标记先于 Enter 落盘（16 个独立进程对抗夹具严格 1 winner；产品 CLI 无 `--state-dir`，环境变量不能改领取域），点火前第三次重读加最终 identity/status/connected/writable 门禁拦截已变状态（对抗夹具结果 `pre-ignition-state-changed`、`enter_count=0`）。该工具替代人工判读补 Enter，成为 composer-pending 的默认恢复动作；当前证据支持实现完成、对抗回归与受控单次点火，不支持自然命中率、跨 Provider 稳定率或长期依赖。

**首个工具／人工分歧自然样本（W250，2026-08-13）**：dispatch_liveness 对同一终端判 `input-missing`（走保守分支：transcript 不可得或 footer 未适配即不点火），人工精确读为 composer-pending（完整文本停在输入框、Ctx=0），人工沿原终端单次 Enter 后恢复。分歧原因未定位（候选：fresh 终端上 Claude transcript 路径尚未就绪）。该样本符合工具「宁保守不误点火」的设计语义——分歧不是误点火——但表明保守分支会把部分人工可恢复的 composer-pending 归为 `input-missing` 而不点火。因此工具判 `input-missing` 且回执显示走了保守分支时，先按本包 composer-pending 判据人工复核一次，确认后仍可沿原身份单次 Enter；工具改进候选（composer-pending 判据的 transcript 依赖在 fresh 终端上的可得性）已在关联 [#31（Orca 生命周期断裂）](https://github.com/Eridanus117/agent-control/issues/31)登记。单样本不能推出工具自然误判率。

`codex exec --json` 的 Provider 事件解析现已实施为有界适配器。Codex CLI 0.147.0 的一次 `read-only + never + ephemeral` 只读探针实际依次发出 `thread.started`、`turn.started` 和 `turn.completed`；其中 `turn.started` 证明 Provider 已创建 turn，语义强于只证明终端写入受理的 `input_accepted`。工具同时处理 stdout 的点号事件和持久 rollout 的 `event_msg/task_started`，但前者只接受调用者已经排他绑定到精确 Dispatch 的捕获文件；它不创建 Orca→Codex batch 派发、不改变现有 worker 路径，也没有用该路径重放上述四个竞态样本。该能力仍只覆盖 Codex，batch lane 仍失去现有 TUI steering／ask，且极小输出探针曾产生 16,557 个 input tokens；因此不能把适配器写成竞态修复、Provider 中立生命周期或 Orca Dispatch 的替代品。

### 3. 手工补 Enter 会改变释放分支，`retained` 不是交付失败

后续六次配对样本中，手工补 Enter 的 3 次在 `worker-release` 时均进入 `retained (user_takeover)`，无需补 Enter 的 3 次均正常释放。早期同批还存在手工干预后正常释放的反例，因此不能把当前 3/3 相关性写成所有版本与拓扑中的因果定律。

收口时应把 `retained` 作为需要按当前回执处理的资源分支，不把它冒充任务交付失败，也不把一次相关性扩展成固定产品语义。先读取 `worker-release` 的实际回执，再按其中覆盖、保留与 residual 对象逐项处置。

### 4. 低层 mutation 的错误回执不能单独证明零落盘；重试前必须读取精确状态

一次低层 `dispatch --inject` 夹具返回 `run_required`，同时声明 `effectsApplied=false`；但同一时刻 `dispatch-show` 已能读取新建的 `ctx_94f1a6feb224`，协调者再次派发同一 Task 又得到已派发拒绝。该 Dispatch 随后正常接收唯一 `worker_done` 并进入 `completed`，证明本样本中错误回执与持久化事实不一致。

因此，低层 `dispatch --inject` 返回错误后，先按原 Task 读取 `dispatch-show`，再决定继续等待、恢复或重试；不得从 `effectsApplied=false` 单独推出没有远端副作用。当前只直接验证了 Orca 1.4.177、Windows、由活跃 Worker 发起低层派发这一条路径，不能泛化为所有 mutation 动词都会出现同样结果。

### 5. 视觉 tab 消失不等于其 PTY 已退出；收口要核对 pane 与终端清单

同一 dummy tab 内含 agent pane 与 sibling Python pane。精确处置 agent pane 后，回执为 `ptyKilled=true`，sibling 继续运行；随后以 sibling handle 处置整 tab，视觉布局移除了该 tab，但回执为 `ptyKilled=false`，终端清单仍保留后台 sibling PTY。再按同一精确 handle 处置该 pane 后，回执才变为 `ptyKilled=true`，最终终端清单恢复到实验前的一项。

因此，整 tab 收口不能只看视觉布局；必须同时检查回执中的 PTY 结果、worktree 级终端清单与目标 handle 状态。需要继续处置时逐 pane 使用精确 handle，最后再核对范围外终端与 Git 工作树保持原状。该结论不授权处置预先存在、复用或其他所有者的终端；对象所有权仍由当前任务与协调合同决定。

## 第一方来源与证据映射

1. [关联 #44（实施已批准 D1–D6）S5 探测批](https://github.com/Eridanus117/agent-control/issues/44#issuecomment-5254413472)（2026-08-11）：低层对象的 `worker-abandon` 判定、10 次历史 `dispatch_not_found`、高层路径 13/13 与收口债务账本；支持结论 1。
2. [关联 #66（权威与 Skill 资产的多视角攻防审计）L3-3 补证](https://github.com/Eridanus117/agent-control/issues/66#issuecomment-5257936655)（2026-08-11）：保存 dummy Task `task_8e63823b5560`、Dispatch `ctx_94f1a6feb224`、两个 pane 的精确身份、回执、最终终端清单与 Git 状态；支持结论 1、4、5。
3. [`work/records/2026-08-10-federated-session-entry/record.md`](../work/records/2026-08-10-federated-session-entry/record.md) §36–§40：记录 10 次 `dispatch_not_found` 累计、竞态频次（5/6、1/3、10/11）、`--enter` 补交与早期 `retained` 观察；支持结论 1、2、3。
4. Orca 上游[关联 #13821（输入提交竞态报告）](https://github.com/stablyai/orca/issues/13821)及其[后续六次派发证据](https://github.com/stablyai/orca/issues/13821#issuecomment-5257142758)：保存环境、最小复现、上游源码分析、preamble 字节数、手工补 Enter 与释放结果；支持结论 2、3。
5. 2026-08-12 本机 1.4.180 直接复核：`orca status --json`、`orca skills get orchestration`、当前真实高层 Dispatch 的 `worker-show`／`dispatch-show` 与实际任务进入对话结果；支持当前版本水位以及“仅刷新版本水位、结论不变”的限定结论。
6. [关联 #31（Orca 生命周期断裂）两例线索](https://github.com/Eridanus117/agent-control/issues/31#issuecomment-5270706519)与[关联 #184（协调者运营与管理能力）波次回执](https://github.com/Eridanus117/agent-control/issues/184#issuecomment-5271396248)：后者冻结 V1／V6／V7／S1 四个 fresh Codex 样本的 4/4 `codex_apps` 启动签名、一次补交恢复与零重派，前者保存其中两例的输入框／零输入输出细节；支持结论 2 的新增有界相关性，不支持因果。
7. [关联 #204（Codex CLI 本体能力面调研）研究交付](https://github.com/Eridanus117/agent-control/issues/204#issuecomment-5270952054)与[负责人决定回执](https://github.com/Eridanus117/agent-control/issues/204#issuecomment-5271454711)：保存 Codex CLI 0.147.0 的 JSONL 探针、事件序列、成本、替代方案、风险与失效条件，并批准将 `turn.started` 候选并入 K2／K12；支持“更强 Provider 开始证据的候选路径”，不支持适配器已实施。
8. [关联 #209（L2 turn.started 验活面）](https://github.com/Eridanus117/agent-control/issues/209)与本仓 [`tools/codex_liveness`](../tools/codex_liveness/README.md)：实现精确 `taskId + dispatchId` 会话绑定、三态输出、0.144.5／0.147.0 两种真实历史 rollout 验证和 0.147.0 flag 位置守卫；支持“适配器已实现并通过当前交付验证”，不支持自然竞态收益、跨 Provider 通用性或产品采用。
9. [关联 #211（tui-idle 竞态对照）实验交付](https://github.com/Eridanus117/agent-control/issues/211#issuecomment-5274155258)：保存作废卡、v2 三态预注册、低层 `input-missing 5/5`、高层 `submitted 5/5`、6 条低层残留与全部资源后态；支持结论 1、2 的 1.4.181 增量，不支持纯 `tui-idle` 因果或稳定率。
10. [关联 #216（Mode C 混合试点第一阶段）试点交付](https://github.com/Eridanus117/agent-control/issues/216#issuecomment-5274571465)与[验收回执](https://github.com/Eridanus117/agent-control/issues/216#issuecomment-5274677733)：两个 1.4.181 自然 Codex Dispatch 的结构化／人工判定均为“已开始”、分歧 `0/2`，且没有 MCP 启动异常签名；支持当前高层路径可用与有界阴性观察，不支持“无横幅即必然无竞态”。
11. [关联 #31（Orca 生命周期断裂）W229 样本](https://github.com/Eridanus117/agent-control/issues/31#issuecomment-5276711429)与 [F229 样本](https://github.com/Eridanus117/agent-control/issues/31#issuecomment-5277094082)：保存两例 claude fresh composer-pending 的签名细节、单次 Enter 恢复、波次4 派发分布与累计计数；支持 2e。
12. [关联 #184（协调者运营与管理能力）波次4收口回执](https://github.com/Eridanus117/agent-control/issues/184#issuecomment-5277300947)与[波次5收口回执](https://github.com/Eridanus117/agent-control/issues/184#issuecomment-5282170106)：冻结 claude fresh 4 派 2 例对 codex 5 派 0 例的同窗对照与波次5 竞态 0（claude 1 派未复现）；支持 2e。
13. [关联 #241（派发后自动验活与单次点火工具）修缺回执](https://github.com/Eridanus117/agent-control/issues/241#issuecomment-5281985683)、[窄复验结论](https://github.com/Eridanus117/agent-control/issues/241#issuecomment-5282095720)与[关联 #246（派发后三态验活与单次点火工具）](https://github.com/Eridanus117/agent-control/pull/246)：保存三态判据、唯一领取域跨进程原子领取、点火前重读门禁、对抗夹具与 40/40 测试及合入事实；支持 2f。
14. [关联 #31（Orca 生命周期断裂）W250 工具分歧样本](https://github.com/Eridanus117/agent-control/issues/31#issuecomment-5282217969)、[P256A 样本](https://github.com/Eridanus117/agent-control/issues/31#issuecomment-5282558016)与 [F261 样本](https://github.com/Eridanus117/agent-control/issues/31#issuecomment-5284154532)：保存波次6／对抗席三例签名与单次 Enter 恢复、当日 claude fresh 5/8 对 codex 1/10 分布、codex MCP 签名相关性 5/5 与首个 dispatch_liveness 工具／人工分歧记录；支持 2e、2f 的 2026-08-13 增量。
15. 2026-08-13 本机 1.4.182 直接复核：`orca status --json`、同一二进制的完整 `orca skills get orchestration`、当前真实高层 Dispatch 的 `worker-show`／`dispatch-show`、`tools/codex_liveness` 精确 Task／Dispatch 三态与 Orca 上游关联 #13821（输入提交竞态报告）状态；支持当前版本水位、高层路径与结构化验活仍可用，以及“2e／2f 不变但不升级”的限定结论。

## 两道准入门逐项判定

### 结论级判定

| 结论 | 价值门 | 可信门 | 判定依据 |
| --- | --- | --- | --- |
| 1. 高层路径与低层索引边界 | 通过 | 通过 | 正式派发反复使用；10 次历史失败、13/13 高层样本及新 dummy 的四个 `worker-*` 观察相互印证。 |
| 2. `input_accepted` 与真实提交分离 | 通过 | 通过 | 每次派发都要识别；两轮高频样本、六次配对样本与上游源码分析共同支持。 |
| 3. 手工补 Enter 与释放分支 | 通过 | 通过 | 直接影响每次 workaround 后的收口；六次配对结果明确，同时保留早期反例与因果未知。 |
| 4. mutation 回执与落盘不一致 | 通过 | 通过 | 决定错误后的重试安全；同一 Task 的回执、`dispatch-show`、重复派发拒绝及最终 `worker_done` 构成完整单样本链。 |
| 5. tab 视觉状态与 PTY 生命周期分离 | 通过 | 通过 | 决定资源收口验收；同一 tab 的两个 pane、两类回执与最终清单构成可重复单样本链。 |
| 2a. fresh Codex 四样本与 `codex_apps` 签名 | 通过 | 通过（仅限有界相关性） | 每次自然派发都可低成本记录；远端波次回执冻结 4/4、一次补交恢复与零重派，两例另有细节来源，并明确非预注册、无因果与无固定率边界。 |
| 2b. Codex JSONL Provider 验活适配器 | 通过 | 通过（当前交付验证） | 0.147.0 探针证明 `turn.started` 存在；工具已把显式绑定的 batch stdout 和精确 Dispatch rollout 映射为三态，并通过 0.144.5／0.147.0 两个真实历史会话验证。自然竞态收益、跨 Provider 通用性和产品采用仍未验证。 |
| 2c. `input-missing` 第二机制与 `tui-idle` 反证 | 通过 | 通过（限 1.4.181 组合路径） | 直接改变低层探测的诊断和恢复动作；v2 预注册 A／B 各 5 次、早停样本、精确身份与资源后态完整。它证明“等待＋低层注入”不能保证送达，不证明 `tui-idle` 单变量因果或跨 Provider 稳定率。 |
| 2d. 1.4.181 composer 零复现与 MCP 条件线索 | 通过 | 通过（零复现部分已被 2e 替代） | 关联 [#211（tui-idle 竞态对照）](https://github.com/Eridanus117/agent-control/issues/211)两臂未出现 composer-pending，关联 [#216（Mode C 混合试点第一阶段）](https://github.com/Eridanus117/agent-control/issues/216)两个无 MCP 异常签名的 Codex 高层样本均开始；「零复现」负事实已被波次4 两例自然复现替代（见 2e），MCP 线索的“既非充分也非必要”边界保留。 |
| 2e. 波次4／5／6 claude fresh composer 复现与 provider 不对称 | 通过 | 通过（仅限有界相关性） | 直接改变派发后验活预期与 2d 的零复现边界；各例签名、单次 Enter 恢复、同窗 codex 对照、当日 5/8 对 1/10 分布与 MCP 签名 5/5 均有远端回执，无预注册对照与机制隔离。 |
| 2f. dispatch_liveness 三态观察与单次点火工具 | 通过 | 通过（当前交付验证） | 每次 Claude 派发后验活都会复用；三态判据、跨进程原子领取、点火前重读门禁经对抗夹具与未参与者复验；首个自然分歧样本（W250）表明保守分支在 fresh 终端可能漏点火，自然命中率与跨 Provider 稳定率仍未验证。 |

### 八项可信门共同核对

| 可信门 | 判定 | 依据 |
| --- | --- | --- |
| 1. 明确回答的问题 | 通过 | 问题限定为本机 Orca 的受监督派发、低层探测与终端收口：当前高层复核绑定 1.4.182，低层与终端隔离样本仍绑定 1.4.177。 |
| 2. 可直接使用的结论和必要解释 | 通过 | 五条结论分别给出路径选择、提交核验、释放分支、错误后重读和 pane 级验收动作。 |
| 3. 第一方来源或可重复验证过程 | 通过 | GitHub 回执保存 Run／Task／Dispatch／terminal 身份与结果；上游报告保存复现和源码分析；仓内记录保存历史计数；新增远端波次回执保存四样本聚合，Codex JSONL 探针保存可重复事件序列。 |
| 4. 对象、版本、环境和核验时间 | 通过 | 页首列明 1.4.177／1.4.180／1.4.181 的分层样本与 1.4.182 当前水位、Provider、Windows 环境、日期及样本边界。 |
| 5. 例外、仍未知内容和不能推出的结论 | 通过 | 下节区分单样本、相关性、对象域、视觉状态与所有权，明确不可泛化的范围。 |
| 6. 明确的失效条件 | 通过 | 下节列出 Orca、Provider、对象模型、回执与终端布局语义的变化信号。 |
| 7. 下次最少复核步骤 | 通过 | 只在自然高层派发中复核提交与释放；低层结论仅在确有授权的探测中最少重放。 |
| 8. 人容易理解、Agent 足以复用的表达 | 通过 | 中文正文按现象、结论、动作、边界和证据展开，精确身份只保留复核所需部分。 |

## 例外、未知和不能推出的结论

- 输入提交竞态非必现，触发条件未测得；频次只来自本机两天窗口，不能外推为固定概率。
- `input-missing` 只在 Orca 1.4.181／Claude Code 2.1.229 的“`tui-idle`＋低层注入”组合中取得预注册主样本；不能外推到高层路径、Codex、其他版本或等待单变量。
- fresh Codex 竞态例中的 `codex_apps` 启动签名同现已由 4/4 增至 5/5（P256A），但仍没有阴性对照、时序隔离或机制探针；不能推出 MCP 中断导致竞态，也不能因看见或没看见该横幅自动点火或跳过验活。
- 1.4.181 当夜 composer-pending 零复现是小样本负事实，且已被 2026-08-13 波次4 两例自然复现替代；与无 MCP 横幅的 claude 正例合看，「MCP 签名既非充分也非必要」的证据增强，但触发机制仍未知。
- provider 不对称（波次4 claude fresh 4 派 2 例对同窗 codex 0 例；2026-08-13 当日 claude fresh 5/8 对 codex 1/10）来自自然运营小样本，无预注册对照；不能推出 codex 免疫、claude 固定发生率或派发路径因果。
- dispatch_liveness 的首个自然分歧样本（W250）为 n=1：保守分支在 fresh 终端可能把人工可恢复的 composer-pending 归为 `input-missing` 而不点火，原因未定位；不能推出工具自然误判率，也不构成改判据的充分依据，改进候选已登记待独立处理。
- `tools/dispatch_liveness` 的对抗证据只覆盖受控夹具与受控演示，未主动制造真实 composer 竞态；自然命中率、误判率与长期收益未知。
- `turn.started` 仍只在一次 Codex 0.147.0 非交互只读探针中直接验证；适配器实现与两份真实 rollout 验证只把既有事件可靠映射为精确 Dispatch 三态，不验证 Orca 派发改造、受监督所有权、取消／ask、自然竞态收益或跨 Provider 通用性。
- 六次配对样本中的 preamble 只覆盖 5,571–5,728 字节，未跨 16 KiB chunk 边界；它驳回当前区间内的单调长度解释，不能排除更大输入的长度效应。
- `retained (user_takeover)` 与手工补 Enter 在六次样本中 3/3 对 3/3 相关，但早期有反例，准确触发条件仍未知。
- 结论 1 不能推出低层 Dispatch 的交付失败；其 Task result、Dispatch 记录和 `worker_done` 可以持久化，缺口只在高层 agent-terminal 索引与生命周期动词。
- 结论 4 只证明一次低层 `dispatch --inject` 的错误回执与落盘不一致，不证明其他 mutation 动词或版本具有同样缺陷。
- 结论 5 中后台 PTY 仍可按精确 handle 收口，不能据此推出发生了不可恢复损失；视觉布局、PTY 生命周期和对象所有权是三个不同维度。
- dummy 夹具证明授权集合内可以安全处置，不改变预先存在、复用、用户接管或其他所有者资源所需的独立授权门。

## 失效条件

出现以下任一情况时，受影响结论停止直接复用并先做最少复核：

1. Orca 升级，或 stablyai/orca#13821 的输入提交路径、状态模型或释放耦合发生变化；
2. Orca 文档或 changelog 改变 `worker-*`／`dispatch` 的对象模型、低层 agent-terminal 索引或生命周期支持；
3. mutation 错误回执不再暴露 `effectsApplied`，或授权隔离样本证明错误返回与 `dispatch-show` 已保持一致；
4. terminal 的 tab／pane／PTY 回执或视觉布局模型发生变化；
5. Claude／Codex TUI 的输入提交机制变化；
6. Codex CLI 改变 `exec --json` 的 `thread.started`／`turn.started` 事件语义，或 `codex_apps` 的初始化、失败横幅与当前样本环境发生变化；
7. `tools/dispatch_liveness` 的三态判据、唯一领取域或点火前门禁语义变化。

## 下次最少复核步骤

1. 先运行 `orca status --json` 并读取 `orca skills get orchestration` 的当前动态指南；版本不再是 1.4.182，或高层／低层对象与收口语义变化时，让受影响结论先退出直接复用。
2. 下一次真实高层派发即作为复核样本：读取 `worker-start` 回执后，Claude 端优先运行 [`tools/dispatch_liveness`](../tools/dispatch_liveness/README.md) 的三态 observe；只有工具确认 `composer-pending` 才沿原身份经其单次点火路径补一次 Enter，并记录最终 `worker-release` 分支。工具不可用时按人工判读保守处理；工具判 `input-missing` 且回执显示走了保守分支（transcript 不可得／footer 未适配）时，先按 composer-pending 判据人工复核一次再决定是否沿原身份单次补交（W250 分歧先例）；真实 `input-missing` 停止在诊断与证据保留，不创建第二个 Task／Dispatch。
3. 查看 Orca 上游[关联 #13821（输入提交竞态报告）](https://github.com/stablyai/orca/issues/13821)当前状态；上游行为变化时，让结论 2 或 3 先退出直接复用，再按新版本重测。
4. 下一次自然 Codex 高层派发同时记录是否真正进入对话、是否补 Enter、`codex_apps` 启动签名是否出现、最终释放分支和残留资源；保留命中与未命中两侧，不为验证主动制造 MCP 故障或竞态。
5. Codex 派发验活先运行 `tools/codex_liveness` 并保存 CLI 版本、事件 schema、精确 Task／Dispatch／turn 映射与三态；只有调用者已经把 batch JSONL 文件排他绑定到该 Dispatch 时才使用 `events` 适配器。下一次自然样本继续比较 accepted-but-not-executed、人工判读、token 与时延；没有自然样本时只声称当前交付验证，不外推产品收益。
6. 只有在确有低层探测授权时，才创建一次性 dummy Task 与终端：调用 `dispatch --inject` 后无论回执成败都读取 `dispatch-show`；随后检查 `worker-show`／`worker-read`／`worker-release` 是否已获得索引。未获授权时不为复核制造低层派发。
7. 只有在确有一次性资源处置授权时，才建立同 tab 双 pane 夹具：分别记录 pane 处置、整 tab 处置、PTY 结果和最终终端清单。视觉布局与 PTY 状态任一语义变化时更新结论 5。

## 不适用范围

- 未经明确授权的低层派发、终端或 worktree 处置；
- Orca 长期依赖、自建适配层、Fork 或产品选型决定；
- 非 Windows 环境、远端 placement 与其他未核验 Provider；
- terminal 之外的进程管理、操作系统级资源回收与通用事务语义。
