## Context

动机见 `proposal.md` 的《Why》，需求见 `specs/portable-assembly-host/spec.md`，实测基线见 `proposal.md` 的《基线证据》。这里只记录塑造技术路线的现状约束：

- 装配执行层集中在 `src/agent_system/profile/cli.py` 单文件（约 5.2k 行）。`src/agent_system/cap/cli.py` 只是用户入口，通过 `sys.executable <profile-tool>` 子进程调用执行层，因此平台适配全部落在执行层，命令面无需改动。
- 现有安全模型由一个内部抽象承载：`StableDirectory` = 逐分量 no-follow 打开的**目录句柄链** + 操作前后的对象身份复核。句柄链直接使用 `os.open(dir_fd=...)`、`O_DIRECTORY`、`O_NOFOLLOW`、`os.geteuid()`，Windows CPython 四者皆无。
- 现有实现已经是 macOS 形状：`_normalize_root_alias` 专为 macOS 的 `/var` → `/private/var` 根别名而写，使用指南里的渲染示例也是 `/private/tmp`。
- 本变更位于 prompt 与 Skill 之下：prompt 正文、`.cap/capabilities/skills/*`、`.cap/skill-imports.toml` 与三个客户端 adapter 的输出（codex 的 `config.toml`／`AGENTS.md`，qoder 的 `settings.json`／`mcp.json`／`system-prompt.md`，omp 的 `config.yml`／`mcp.json`／`system-prompt.md`）全部不改。三端共用同一条渲染与启动路径，因此适配必须落在这条共用路径上，不得引入任何客户端专属分支。
- 三端在**认证**上并不共用一条路径：codex 与 qoder 用 `os.symlink` 把凭据暂存进一次性运行时根，omp 只读取 `broker.json` 与 `token` 的值并经环境变量传入。这个差异决定了本变更的范围。
- README《持久实现语言》要求持久实现只用 Go／Python／TypeScript／Rust，且不新增 PowerShell／Batch 产品脚本。

## Goals / Non-Goals

**Goals:**

- 让 digest 只由仓内资产内容决定，使两端共用同一份已提交 lock。
- 用一份可移植实现替换目录句柄链，两端跑同一条分支。
- 把宿主无法表达的安全结论变成显式的"未知"，而不是伪装通过、也不是阻断启动。
- 让两端结论都由自动门禁产生。

**Non-Goals（设计层边界，范围边界见 `proposal.md` 的《非目标》）:**

- 不重构 `cli.py` 的文件组织，不拆包。
- 不引入跨平台文件系统抽象库，不引入 `ctypes`，不引入新的第三方运行时依赖。
- 不为任何宿主增加客户端专属渲染或启动分支。
- 不改变 `.cap/lock.json` 的 schema 版本与字段名。

## Decisions

### D1：权限位钉规范值（已由上游 #84 落地，本节保留为记录）

> **本决定已被上游取代。** #84 的 `_canonical_mode` 直接返回常量，不做 POSIX 侧校验。原文打算在 POSIX 侧拒绝可执行位与 group／other 写位——该规则在 WSL 经 DrvFs 访问时会把每个文件都判为可执行（DrvFs 对所有文件报 `0o777`），从而拒绝全部锁定输入。上游结论正确，以下原文仅作决策记录保留。

#### 原文

锁定输入与渲染树记录的资产权限位取常量规范值（普通文件 `0644`），并在 POSIX 宿主上校验实际权限位，拒绝可执行位与 group／other 写位。

- **为什么不选"Windows 上把 `0666` 映射回 `0644`"**：映射是静默近似。仓内一旦出现 `100755` 资产，POSIX 记 `0755`、Windows 记 `0644`，drift 会在跨平台时重现，而且失败点离原因很远。钉常量则把"锁定输入不得可执行"变成一条可以在 POSIX 上直接执行的显式规则。
- **为什么不选"从 git index 读取 mode"**：会让声明层依赖 VCS 状态，与"声明必须自足"的边界冲突，且 export／打包场景下不可用。
- **为什么不选"直接删除 `mode` 字段"**：会丢掉 POSIX 上现有的"资产不得对 group／other 可写"检测，是净损失；也会改变 `.cap/lock.json` 内容，需要重新 lock。
- **成立条件已核实**：`.cap`、`plugins`、`.agents` 下 138 个文件全部为 `100644`，仓内唯一的 `100755` 位于 `tools/`，不在锁定输入与渲染源集合内。本决定在当前仓库内容下产出与已提交 lock 逐位相同的结果。

### D2：放弃目录句柄锚定，改用两端共用的 `os.lstat` 分量校验

`StableDirectory` 保留"路径 + 对象身份 + 前后复核"的语义契约，去掉"持有句柄链"的实现手段：

- 逐分量用 `os.lstat` 检查，拒绝符号链接与重解析点。实测在 Windows 上 `os.lstat` 原生不跟随 junction，`st_file_attributes` 可判出重解析点（junction 得 `attrs=0x410`、`st_reparse_tag=0xa0000003`，真实目录得 `attrs=0x10`）；macOS 侧沿用 `stat.S_ISLNK`。
- 对象身份用 `st_dev` + `st_ino`。两端均有值且能区分对象，`_same_file_identity` 的判定形状完全不变。
- 操作前后各复核一次身份，`_validate_stable_directory` 的语义与时机不变。
- **改写面（原设计误判，已修正）**：去掉描述符链不只是替换入口实现。`StableDirectory.descriptor` 被 18 个函数直接消费，分 6 簇：

  | 簇 | 函数 | 现有用法 |
  | --- | --- | --- |
  | A 句柄链核心 | `_open_stable_directory`、`_validate_stable_directory`、`_close_stable_directory`、`_stable_directory_is_within`、`_stable_directory_is_same`、`StableDirectory.descriptor` | 链本身 |
  | B 目录内容与空目录判定 | `materialize_profile`、`_state_root`、`_strict_json_from_directory` | `os.listdir(fd)`、`os.open(dir_fd=)`、`os.stat(dir_fd=)` |
  | C 认证私有性 | `_validate_private_directory`、`_read_private_file`、`_validate_private_tree` | `os.fstat`、`os.geteuid`、`dir_fd=` |
  | D 认证暂存 | `_create_auth_symlink` | `os.symlink(dir_fd=)` |
  | E 渲染物化 | `_materialize_tree` | `os.mkdir(dir_fd=)`、`os.fsync(fd)`，整个函数按描述符组织 |
  | F 回执预留与提交 | `_reserve_receipt`、`_validate_receipt_reservation`、`_commit_receipt`、`_unlink_reserved_receipt`、`_release_receipt` | `os.dup`、`O_EXCL`、`lseek`／`ftruncate`／`fsync` |

- **POSIX 侧既有保证不得因移植丢失**：按路径操作只替换"如何定位对象"，不得替换"操作本身的语义"。`_reserve_receipt` 的 `O_EXCL` 独占创建、`_materialize_tree` 的 `fsync` 时序、私有文件读取的重试与身份复核都必须原样保留；任何一簇改完若使 POSIX 回归掉绿，即为移植引入的回归，不接受以"平台差异"解释。
- **为什么不选"给 Windows 写一套 Win32 句柄实现"（`CreateFileW` + `FILE_FLAG_OPEN_REPARSE_POINT` + `GetFileInformationByHandle`）**：那是把一个 POSIX 机制在第二个平台上重新实现一遍，得到两套需要各自维护、各自测试、语义只能靠人工论证等价的代码，与"cap 是 Win + Mac 两端产品"的定位相反。它换来的唯一额外保证见下条权衡。
- **代价，实测修正**：原文写过这是从"不可能"退到"很小且可检出"。**该表述不准确，已作废**。实测（POSIX，渲染中途把输出目录改名并替换为指向他处的符号链接）表明：句柄链能让某个分量在持有期间**根本无法**被改名或删除，写入始终锚定在对象上；`lstat` 方案每次操作都按名字重新解析，因此在检出不符之前**已经产生的中间写入会真的落进替换后的对象**——实测有三个子目录被建到了攻击者目录里。仅靠前后身份复核只能让操作失败，不能阻止这些中间写入。应对见 D7。在两端均为单用户个人机器的当前使用场景下，这个窗口不构成现实威胁；若日后目标宿主变成多用户共享主机，应重新评估本决定。
- `_normalize_root_alias` 保留 macOS 根别名归一化，去掉对非 `/` anchor 的一律拒绝。

### D3：平台判断收敛在 A 簇一处，其余各簇改写后不含平台分支

`_open_stable_directory`／`_validate_stable_directory` 保持唯一入口；内部只在"如何判断一个分量是符号链接／重解析点"这一处存在平台差异，检查集合本身两端相同。B–F 簇的描述符消费点必须改写为按路径操作，改写完成后这些函数内部**不含任何平台分支**——它们只是不再依赖 `dir_fd`，而不是各自处理平台。理由：平台判断一旦散进这些函数，就无法再断言"两个宿主走同一条装配路径"，spec 的《能力闭包与命令面不随宿主平台变化》也就失去可验证性。

原设计在此处写过"调用点一行不改"，这是对代码结构的误判：描述符不只在入口出现，B–F 簇共 13 个函数直接使用它。该表述已作废，改写面见 D2 的表。

### D4：认证检查按"该宿主能否表达"分类处理，omp 不需要暂存

`_staged_auth` 的四项 POSIX 检查逐条处理：

| 检查 | POSIX | Windows | 处置 |
| --- | --- | --- | --- |
| 属主为当前用户（`st_uid == geteuid()`） | 可表达 | 不可表达（`st_uid` 恒为 0） | POSIX 保持为门；Windows 报未知 |
| 不授予 group／other 权限（`mode & 0o077`） | 可表达 | 不可表达（`st_mode` 只反映只读属性） | POSIX 保持为门；Windows 报未知 |
| 硬链接数为一（`st_nlink`） | 可表达 | **可表达**（实测硬链接后两名字均报 `nlink=2`） | 两端保持为门 |
| 凭据暂存 | `os.symlink` | 需要 `SeCreateSymbolicLinkPrivilege` 或开发者模式 | **omp 不使用暂存**，见下 |

- **omp 不产生凭据副本**：`_staged_auth` 的 omp 分支只读取 `broker.json` 与 `token` 的值，经 `OMP_AUTH_BROKER_URL`／`OMP_AUTH_BROKER_TOKEN` 传给客户端，磁盘上不出现第二份凭据。因此本变更完全不涉及"复制还是链接"的取舍——该取舍只存在于 codex 与 qoder，已列为非目标。
- **为什么私有性检查在 Windows 上报未知而不是用 `ctypes` 读 DACL**：该检查防的是同一机器上的另一个本地账户读取 token，或认证目录被放在广泛可读的位置；它不防任何以当前用户身份运行的代码，而后者是个人机器上唯一现实的威胁。在当前使用场景下其对抗价值接近零，残余价值是防意外配置。为它引入一处 Win32 平台分支与配套测试，与 D2 的方向相反且不成比例。
- **为什么不是在 Windows 上直接拒绝启动**：那等于 cap 在 Windows 上永远无法启动客户端，与本变更目的相反。
- **为什么不是在两端都删掉这项检查**：会削弱 macOS 侧现有保证，属于为跨宿主一致而放宽，被 spec 明确禁止。
- 该结论进入现有三层证据报告，与 lock、binding 结论并列；日后若目标宿主改变，可在不修改 spec 的前提下把它升级为真实的 ACL 检查。

### D5：两个提交独立可交付，各自带门禁

权限位（D1）与目录校验（D2–D4）分别为独立提交与独立 PR。D1 落地后 Windows 上即可用 `cap agents`／`show`（不带 `--cli`）／`lock`／`machine-context-*`／`assembly-bind`／`verify`；D2–D4 落地后才可用 `render`／`use`／`run`。理由：D1 已实测可让 `cap verify` 在 Windows 返回 `{"status": "ok"}` 且不改动已提交 lock，风险量级与后者完全不同，不应被后者的审阅周期挟持。

### D6：否决 WSL 路线

WSL Ubuntu 在本机存在且有 uv 与 CPython 3.12，但没有安装 `omp`；走 WSL 需要在第二套环境重装客户端与认证，Windows 原生 `omp.exe` 用不上，工作目录跨 `/mnt/c` 还会引入路径与文件锁问题。它能绕过问题但不解决 `authority/08` 已确立的 Windows 稳定入口，因此只作为应急手段记录，不作为方案。

### D7：写入先落私有暂存目录，再一次性移入目标

为满足 spec《操作期间目录被替换》"不得把任何内容写入替换后的对象"，渲染与物化不再直接在用户给定的目标目录中逐个创建子目录和文件：先把完整装配树写进 cap 自己创建的私有暂存目录，全部校验通过后再整体移入目标位置。
- 暴露窗口从"每一次 `mkdir`／`open`"缩成"最后一次移入"，且该次移入前紧邻一次身份复核。
- 暂存目录由 cap 独占创建，名字不可预测，攻击者无法预先占位。
- **为什么不选"每次写入前都复核一次身份"**：窗口只缩短不消除，且把复核次数放大到与文件数同阶，代价高而保证仍不满足 spec 的强表述。
- **为什么不选"POSIX 保留句柄链、Windows 走路径"**：那是回到两套实现，与本 change 的方向相反。
- **残留边界**：见 D8。

### D8：预留占位文件的回收在并发改名下会失败，这是按名字寻址的固有边界

receipt 采用"先 `O_EXCL` 预留占位、运行结束再提交"。旧实现持有父目录句柄，父目录被改名后仍能通过句柄回收占位文件；按名字寻址做不到——改名之后那个名字已经指向别处。

- 实测确认：安全性质保持（错误正确抛出，替换后的目录保持为空、不产生 receipt），失去的是卫生性质（被改名走的目录里留下一个**空**占位文件）。
- 该残留不含装配内容也不含凭据，且后续运行不会把空占位当作有效产物。因此接受这一边界，并在 spec 中显式表达，而不是假装它不存在或悄悄放宽测试。
- 对应的两个既有用例保留其安全断言，只把"占位文件已被回收"的断言改写为"占位文件保持为空"。

## Risks / Trade-offs

- **[去掉句柄锚定后存在 TOCTOU 时间窗]** → 见 D2 的代价记录：保留操作前后身份复核使替换可检出；在设计文档与使用指南中明确写出该保证的边界，不声称等同于句柄链；若目标宿主变成多用户共享主机则重新评估。
- **[Windows 上私有性结论为未知，可能被误读为"检查通过"]** → 结论必须出现在三层证据报告中并显式标为未知；`cap verify` 输出与文档同步说明，不得只在代码注释里交代。
- **[临时根位于用户主目录之下]** → Windows 的 `TemporaryDirectory` 落在 `%LOCALAPPDATA%\Temp`，在 `C:\Users\<user>` 之下。现有 `_require_external_directory` 只拒绝"与 HOME 相同"和"在项目内"，不拒绝 HOME 之下，因此不冲突；需加一条测试固定这一行为，避免日后收紧规则时静默破坏 Windows。
- **[长路径与文件锁]** → 按 `knowledge/windows-agent-ops.md` 处理；渲染与临时根路径需在测试中覆盖较长路径。
- **[改写面比原计划更大：实测还有第 7 簇]** → `src/agent_system/omp/runtime.py` 的 `_validate_private_runtime` 另有一处 `os.geteuid()` 判定，原 Impact 写的"全部位于 `profile/cli.py`"不成立。该处按 D4 同一条规则处理，不引入第二套判定逻辑。
- **[改写面达 6 簇 18 个函数，且含安全相关时序]** → 按簇分小步推进，每簇一条任务、一组测试；POSIX 侧回归必须全程保持全绿（Linux 当前为全绿基线），任一簇改完掉绿即视为移植引入的回归而非平台差异；回执预留与证据物化两簇单独复核 `O_EXCL` 与 `fsync` 语义是否原样保留。
- **[Windows CI 时长与不稳定]** → 只跑与平台相关的最小集合（单元测试 + `lock`／`verify` + render smoke），不整体复制现有 job。

## Migration Plan

1. 提交一：改 `_input_records` 与 `_render_tree` 的权限位来源，加 POSIX 侧校验与单元测试；`.cap/lock.json` 内容不变，无需重新 lock。
2. 增加新的 workflow 文件，内含 `windows-latest` 与 `ubuntu-latest` 两个 job，跑同一条 lock 复现检查；两侧共同证明 digest 与宿主无关。
3. 提交二：按 A→B→E→F→C／D 的簇序把 `StableDirectory` 换成 `os.lstat` 分量校验实现，调整 `_normalize_root_alias`，按 D4 分类处理认证检查，扩展 Windows CI 覆盖 render smoke。每簇完成后都要求 POSIX 回归全绿再进入下一簇。
4. 回滚：两个提交各自可单独 revert；POSIX 侧回到当前 `main` 行为。本机 `$HOME/.agent-system-state/` 不由本变更迁移；binding 失配时按既有 `cap assembly-bind` 重建。

## 已解答的问题

原文在此挂了一个待定问题：Windows 上的 omp 读 `HOME` 还是 `USERPROFILE`。实测**否掉了这个问题的前提**，且经历两次更正才收敛。完整更正链见 [`work/records/2026-08-20-omp-windows-agent-dir/finding.md`](../../../work/records/2026-08-20-omp-windows-agent-dir/finding.md)。

结论：与主目录变量、profile 变量都无关。**是 cap 误用了 `PI_CONFIG_DIR`。**

上游 [can1357/oh-my-pi#9067](https://github.com/can1357/oh-my-pi/issues/9067) 裁定 `wontfix` 并给出理由：`getBaseConfigRoot()` 无条件把 `os.homedir()` 与 `getConfigDirName()` 拼接，而 `PI_CODING_AGENT_DIR` 单独经过 `path.resolve()`；这个区分是设计意图，`PI_CONFIG_DIR` 被定义为**相对 home 的目录名**，支持绝对值会改变契约而不是修复回归。

因此两个变量的契约不同，cap 分别按契约传值：

| 变量 | 契约 | cap 传什么 |
| --- | --- | --- |
| `PI_CODING_AGENT_DIR` | 经 `path.resolve()`，接受绝对路径 | 托管运行时根的绝对路径 |
| `PI_CONFIG_DIR` | 与 `os.homedir()` 拼接的目录名 | 同一目录相对真实 home 的名字 |

cap 的托管运行时根按构造就在真实 home 之下，因此总能表达为 home 相对名；运行时根被显式配置到 home 之外时该配置无法用 `PI_CONFIG_DIR` 表达，cap 显式失败而不是交出会被静默翻倍的绝对值。

**修复后实测**：`cap run agent-assembler` 在 Windows 上成功拉起 omp，进入模型调用。

**生效态仍为 `unknown`，原因已更正**：不再是上游阻塞，而是 cap 内两条认证路径来源不一致——默认的共享运行时路径主动删除 `OMP_AUTH_BROKER_*` 并设 `PI_AUTH_NO_BORROW=1`，`--auth-root` 的 broker 凭据只在 profile engine 的一次性运行时路径生效。这是一个独立于本 change 的设计问题。
