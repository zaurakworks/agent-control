# K24：Windows Agent 运维先按需实测，再隔离路径、句柄、PTY 与高权动作

> 状态：正式当前公共知识。
> 最近核验：2026-08-12（America/New_York）。
> 适用对象：本机 Windows 11 上，Agent 处理 PowerShell 脚本、深路径／临时目录、文件发布与回收、Orca PTY 生命周期或管理员动作的自然任务。
> 环境：Windows 11 Pro 10.0.26200；PowerShell 7.6.3；Git for Windows 2.55.0.windows.3；Orca 1.4.181 packaged；Microsoft Defender Antivirus。
> 证据上限：五条惯例由本机只读探针、Microsoft 一手合同和既有当前知识共同支持；它们不证明固定事故率、Defender 导致某次文件锁、所有 Windows／文件系统／PTY 宿主行为相同，也不产生配置修改、清理或提升权限的授权。

## 回答的问题与价值门

Windows Agent 在什么检查点应先停一下，才能避免把宿主策略、路径／临时目录、文件句柄、PTY 视觉状态或应用沙箱误当成目标系统的真实状态？

这些检查点会在后续 Windows Agent 文件、终端和高权任务中反复出现；误判可能造成脚本未执行、路径写入失败、覆盖／清理失败、活 PTY 被误收口或长驻高权进程扩大影响面。五条惯例都能用低副作用探针守住高返工边界，因此通过价值门。本次把关联 [#220（Windows 运维陷阱面）](https://github.com/Eridanus117/agent-control/issues/220)的 WIN-5 拆成可独立复核的“PTY 五事实”与“高权分段”，与 WIN-1／3／4 合成五条；WIN-2 已由 [K17（Windows 下 PowerShell／GitHub CLI 多行 Markdown 传输边界）](./windows-powershell-multiline-transfer.md)和 [K6（跨端文件一致性验收必须先规范化换行）](./newline-normalized-acceptance.md)承载，本包不复制。

## 可直接复用的五条惯例

### 1. 命中风险时做按需快照，不自动修机

**触发条件**：任务准备执行 `.ps1`，创建可能接近消费者路径上限的文件，依赖 Git 路径／换行设置，诊断安全产品干预，或请求管理员能力。普通、无关的 Windows 命令不为形式完整运行全套快照。

**最短动作**：只读取会改变本次动作的事实，并把结果写成“实测值”或“未知”。脚本面读取五个 execution-policy scope、有效策略及目标文件的 `Zone.Identifier`／签名；路径面读取 `LongPathsEnabled` 与 `git config --show-origin`；高权或杀软面读取当前 Windows token 与相关保护状态。探针失败就保持未知并走可回退路径，不调用 `Set-ExecutionPolicy`、`Unblock-File`，不改注册表、Git 配置、Defender 排除项或权限。

**一手探针依据**：2026-08-12 本机只读复核得到五个 scope 中仅 `LocalMachine=RemoteSigned`、有效策略 `RemoteSigned`；`LongPathsEnabled=0`、`core.longpaths` 未设置、系统级 `core.autocrlf=true`；当前 token 不是管理员，UAC 与 Defender 实时保护启用。Microsoft 说明 execution policy 有五个优先级 scope、是防误执行而非安全边界，并可由 Group Policy 覆盖；这支持“先读真实值，不把改策略当默认修复”。

**失效条件**：主机、PowerShell、Git、目标文件来源、当前 token、组织策略或安全产品变化；探针命令不再返回相同语义；任务移到 WSL、远程 placement 或非 Windows 宿主。命中后只重读相关事实，不重跑无关探针。

### 2. 先预算短根，再使用任务自有临时目录

**触发条件**：创建 worktree、依赖树、构建输出、解压目录、随机名或临时文件；清理任务残留。

**最短动作**：创建前用解析后的绝对路径计算“根＋最深输出＋工具保留后缀”，并按本次最弱消费者守门；消费者能力不明时缩短根与标识，不自动开启机器长路径策略。每个任务只在短、私有、带稳定任务身份的子目录中产生临时文件；使用前验证候选目录存在、可访问，解析后的目标仍位于该私有根内。清理只针对自己拥有的精确路径，先停止子进程并释放句柄；失败就登记残留，不按年龄或通配符扫描共享 `%TEMP%`。

**一手探针依据**：本 worktree 根的绝对路径为 58 字符，当前最长已跟踪文件绝对路径为 154 字符；`[IO.Path]::GetTempPath()` 返回当前用户 Temp 且目录存在。Microsoft 说明部分 Win32 路径仍受 `MAX_PATH` 约束，解除约束同时依赖系统位与应用 `longPathAware`，相对路径仍受限制；`GetTempPath2` 只按环境与 token 返回候选字符串，不验证目录存在、访问权，且会保留符号链接形状。

**失效条件**：消费者集合、文件系统、网络盘／UNC、容器或路径 API 变化；全部消费者已经用直接证据证明支持所需长度；临时目录来源、ACL 或 reparse-point 行为变化。变化后重算当前最深绝对路径，并重新验证私有根的存在、权限与边界。

### 3. 发布与回收必须感知句柄；sharing violation 只做有界诊断

**触发条件**：覆盖、重命名或删除可能正在被 Agent、子进程、编辑器、索引器、安装器或安全产品使用的文件。

**最短动作**：先写唯一新文件，完成落盘并关闭句柄，停止相关子进程并释放全部自有句柄；只有目标工具或 API 明确保证时，才用其同卷替换原语完成提交，并在目标端回读。遇到 sharing violation 时记录精确目标、错误码、时间与已知进程，采用有次数上限且带退避的重试；上限后保留原文件与残留证据，不强删。只有自然复现、测量把问题缩到安全产品且另有明确授权时，才把最窄排除项列为候选。

**一手探针依据**：2026-08-12 的两次只读复核对 `%TEMP%\\vscode-stable-user-x64\\CodeSetup-*.exe` 做独占打开时均返回 `0x80070020`，未重命名或删除目标；同期 Defender 实时、行为与 IOAV 保护均为启用。Microsoft 的 `CreateFileW` 合同明确说明共享模式在句柄关闭前持续生效，冲突返回 `ERROR_SHARING_VIOLATION`；Defender 文档说明排除以提升性能换取保护降低。两项事实不能合并成“Defender 导致这次锁”。

**失效条件**：目标迁移到不同卷、网络文件系统或另一个替换 API；工具明确改变原子替换／重试合同；错误不再是 sharing violation；安全产品或策略变化。下一次自然锁只复核精确错误、持有者候选、耗时与最终后态，不为验证主动制造破坏性锁或排除项。

### 4. PTY 收口分别验收五个事实

**触发条件**：派发输入、判断 Provider 是否开始、移动／关闭视觉 tab、终止进程树或宣称任务／终端已收口。

**最短动作**：分别记录并用稳定身份核验：① mutation／输入受理；②正文进入 Provider 会话及实际开始事件；③视觉 tab／pane 布局；④精确 PTY 与进程树存活；⑤任务终态、释放回执与最终终端清单。任何一项都不能替代另一项；继续处置前重新读取当前工具指南和精确对象状态。

**一手探针依据**：本次 `orca status --json` 返回 1.4.181 runtime ready，精确 Dispatch 的 `worker-show` 同时返回 `stage=input_accepted`、connected／writable terminal 与 `ptyId`；探针子进程的三路标准流均 redirected，`TERM=xterm-256color`、`TERM_PROGRAM=Orca`。这些只证明当前宿主形状与输入受理，不证明 Provider 已开始。K2 已用自然样本证明 `input_accepted` 不等于提交、视觉 tab 消失不等于 PTY 退出；Microsoft 的 Pseudoconsole 合同另说明输入／输出通道、resize、最终帧排空与附着进程树终止有独立生命周期。

**失效条件**：Orca 或 Provider 升级；Dispatch、开始事件、tab／pane／PTY、释放回执或终端清单语义变化；任务换用非 Orca PTY。命中时让本条退出直接复用，先执行 K2 的最少复核并动态读取当前 orchestration 指南。

### 5. 管理员动作分段执行，不提升整个 Agent

**触发条件**：动作需要 HKLM、机器级执行策略、Defender 排除、受保护目录或其他管理员 token；应用层显示无沙箱、自动批准或 `bypassPermissions` 不能降低触发门。

**最短动作**：默认让协调与 Agent Session 保持普通 token。把每个管理员动作视为新的外部写入：先取得覆盖精确对象与副作用的当前合同，只在单独、短生命周期进程中执行一个可审计步骤，随后用普通权限回读目标状态并结束高权进程。不自动 `RunAs`、不自提权、不让完整长驻 Agent 继承管理员 token。

**一手探针依据**：本机当前进程 `IsAdministrator=false`，同时 `EnableLUA=1`、管理员提示策略为 consent prompt、secure desktop 启用；当前权威又明确 Codex 使用 `danger-full-access/never`、Claude 使用 `bypassPermissions`。这直接证明“Agent 应用权限宽”与“Windows 管理员 token”是两层事实。Microsoft 说明子进程继承父进程 token，需要管理员 token 的应用必须经 UAC consent／credential 流程。

**失效条件**：用户、token、UAC／组织策略、宿主 placement、服务账户或目标资源权限变化；任务采用新的隔离提权代理。变化后先读取当前 token、UAC 与精确目标 ACL／权限合同，再决定是否仍能分段；本条自身不授权高权动作。

## 第一方来源与证据映射

1. [关联 #220（Windows 运维陷阱面）调研交付](https://github.com/Eridanus117/agent-control/issues/220#issuecomment-5275058574)：保存 2026-08-12 的完整只读探针、既有事故对照、未运行项、五条候选及不能外推的边界；本次又最少复核版本、策略、路径、Temp、锁、token、UAC、Defender 与 PTY 状态。
2. [Microsoft：PowerShell execution policies](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies?view=powershell-7.6)：支持五 scope、优先级、Zone 与“不是安全边界”；不支持自动放宽策略。
3. [Microsoft：Maximum Path Length Limitation](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation)与 [GetTempPath2](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-gettemppath2a)：支持应用 opt-in、相对路径边界、临时路径搜索顺序及存在／权限／符号链接未知。
4. [Microsoft：CreateFileW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew)与 [Defender exclusions](https://learn.microsoft.com/en-us/defender-endpoint/microsoft-defender-antivirus-exclusions-overview#contextual-exclusions)：支持共享模式、`ERROR_SHARING_VIOLATION` 与排除项保护取舍；不支持把当前锁归因于 Defender。
5. [K2（Orca 受监督派发）](./orca-supervised-dispatch.md)与 [Microsoft：Creating a Pseudoconsole session](https://learn.microsoft.com/en-us/windows/console/creating-a-pseudoconsole-session)：支持输入、Provider 开始、视觉布局、PTY／进程树与终态分离。
6. [`authority/08` 的 Windows 默认执行权限与授权边界](../authority/08-mvp-implementation-direction.md#windows-默认执行权限)和 [Microsoft：How UAC works](https://learn.microsoft.com/en-us/windows/security/application-security/application-control/user-account-control/how-it-works)：支持应用权限与 Windows token 分层、UAC consent 与 secure desktop；不产生任何新增高权授权。

## 两道准入门逐条判定

| 惯例 | 价值门 | 可信门 | 判定依据 |
| --- | --- | --- | --- |
| WIN-1｜按需快照、不自动修机 | 通过 | 通过 | 脚本／路径／高权任务反复需要；当前五类只读值与 Microsoft 策略合同可重复取得，并明确未知与不修改边界。 |
| WIN-3｜短根＋任务自有临时目录 | 通过 | 通过 | 每个 worktree／构建／清理任务可复用；当前路径长度、Temp 实测与 Win32 一手边界共同支持，未伪造统一安全阈值。 |
| WIN-4｜句柄感知发布与回收 | 通过 | 通过 | 发布／清理失败代价高；活锁、精确错误码与 CreateFileW 共享合同相互印证，并把 Defender 因果保留为未知。 |
| WIN-5a｜PTY 五事实验收 | 通过 | 通过 | 每次派发／收口都可能命中；本次精确 Dispatch／PTY 探针、K2 自然样本与 Pseudoconsole 合同形成边界清楚的证据链。 |
| WIN-5b｜高权分段 | 通过 | 通过 | 高权误用影响面大且自然任务会重复；当前 token／UAC 实测、现行权限权威与 Microsoft token 合同一致。 |

五条都明确回答窄问题，给出可执行动作、第一方来源或可重复探针、对象／版本／环境／时间、未知与不能外推内容、失效条件及下次最少复核步骤；表达可让 Agent 在自然检查点直接使用，满足八项可信门。

## 例外、未知和不能推出的结论

- 本包不是每次 Windows Session 的固定 preflight；只在触发条件命中时读相关子集。
- 本包不取代 K17／K6 的多行文本与换行验收，也不复制 K2 的完整 Orca 派发／收口程序。
- 一次活锁与 Defender 同时启用不构成因果；没有自然复现、测量和独立授权时，不得添加排除项。
- “短根”没有统一字符阈值；预算由当前最弱消费者、相对／绝对路径形状和保留后缀共同决定。
- “任务自有”必须来自当前合同或可核验所有权；目录名、年龄、位置或由本进程可访问都不能单独证明可删。
- `danger-full-access`／`bypassPermissions` 不等于管理员 token，也不等于获得宿主配置、删除、提权或其他外部写入授权。
- 当前直接样本不覆盖 Windows PowerShell 5.1、网络盘／UNC、WSL、远程 placement、其他杀软、其他 PTY 宿主或已提升的 Agent Session。

## 下次最少复核步骤

1. 先确认 Windows build、PowerShell、Git、Orca、当前 token 与相关安全产品是否仍在页首边界；只对命中的失效条件补查。
2. 脚本失败时读取五个 execution-policy scope、有效策略、目标文件 Zone／签名；没有目标脚本就不制造夹具。
3. 路径任务计算当前根与预期最深输出的绝对长度，读取本次最弱消费者的长路径能力；临时写入前只验证任务私有根的存在、访问权与解析后边界。
4. 下一次自然 sharing violation 保存精确错误、目标、持有者候选、退避次数与最终后态；不改排除项，不为复核删除或重命名活文件。
5. Orca 自然派发先动态读取当前指南并执行 K2 最少复核；用精确 Task／Dispatch／terminal／PTY 身份记录五个事实，不为复核制造低层 Dispatch 或终端夹具。
6. 管理员动作前读取当前 token、UAC 与精确目标权限；没有覆盖该外部写入的合同就停止，不用探针结果补出授权。
7. 只有新证据改变五条结论之一时才增量更新对应段；否则直接复用，不重做关联 [#220（Windows 运维陷阱面）](https://github.com/Eridanus117/agent-control/issues/220)的全量调研。
