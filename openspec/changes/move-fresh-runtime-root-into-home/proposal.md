> 方案审阅载体：[#109](https://github.com/zaurakworks/agent-system/issues/109)。上游裁定见 [can1357/oh-my-pi#9067](https://github.com/can1357/oh-my-pi/issues/9067)（`wontfix`）。

## Why

`cap run --fresh` 与 `cap use --fresh` 在 omp 客户端下无法启动，因此 `agent-assembler` 的**实际生效态**至今没有真实客户端证据，只能按 `portable-assembly-host` 的既有需求记为 `unknown`。

`--fresh` 是 CAP 唯一使用 `--auth-root` 显式认证的路径——默认持久 runtime 把认证保存在自己的 `agent.db` 中。因此这条路径不通，等于「显式认证的一次性运行」整体不可用。

失败点（实测，Windows 11 + omp v17.3.8）：

```
ENOENT: no such file or directory, mkdir
  'C:\Users\<user>\C:\Users\<user>\AppData\Local\Temp\profile-omp-agent-assembler-xxxx\run\daemons\...'
```

`build_launch` 把一次性临时根当绝对路径传给 `PI_CONFIG_DIR`，而 omp 的契约是该变量为**相对 home 的目录名**（`getBaseConfigRoot()` 无条件拼接 `os.homedir()`）；只有 `PI_CODING_AGENT_DIR` 经过 `path.resolve()`。路径被拼了两次。

持久 runtime 已在 #104 按该契约修正——它的根按构造就在 `$HOME/.agent-system-state/runtimes/omp/<id>` 之下，总能表达为 home 相对名。**一次性根位于系统临时目录，不在 home 之下，因此同样的修法不适用。**

## What Changes

- 一次性 runtime 根从系统临时目录移到真实 home 之下的 CAP 自有位置，使它总能表达为 `PI_CONFIG_DIR` 要求的 home 相对名。
- `PI_CODING_AGENT_DIR` 保持绝对路径不变（其契约本就是 `resolve()`）。
- 三个客户端共用该位置，因此 codex 与 qoder 的一次性根一并移动。

## Capabilities

### Modified Capabilities

- `portable-assembly-host`：新增一条需求，要求一次性 runtime 根必须落在两端都能表达为客户端所需形式的位置，并要求该位置的选择不得引入平台分支。

## 推荐方案

把一次性根改到 `$HOME/.agent-system-state/` 之下的 CAP 自有目录。

两端同一实现：macOS 的 `/tmp` 与 Windows 的 `%LOCALAPPDATA%\Temp` **都不在 home 之下**，只有移进 home 才能让两端走同一条路径，而不是只给 Windows 打补丁。

现有边界无需放宽：`_require_external_directory` 只拒绝「与 home 相同」和「在项目内」，不拒绝 home 之下——该行为已有测试固定（`PortableDirectoryTests.test_directory_below_the_user_home_is_accepted`）。

## 可信替代方案与不选的理由

| 方案 | 不选的理由 |
| --- | --- |
| 只在 Windows 上把临时根转成 home 相对名 | Windows 临时目录确实在 home 之下，可行；但 macOS 的 `/tmp` 不在，`--fresh` 在 macOS 上依然坏，且引入平台分支，与已归档 change 的 D3（平台判断收敛在一处）相反 |
| 不设 `PI_CONFIG_DIR`，只用 `PI_CODING_AGENT_DIR` | 实测该配置下 omp 会读取 `~/.omp/config.yml` 并据此选模型，直接违反本仓「业务能力不得从用户目录隐式补齐」的边界 |
| 放弃 `--fresh`，只保留持久 runtime | 等于放弃 `--auth-root` 显式认证这条路径，与 `docs/cap-guide.zh-CN.md` §1 声明的边界冲突 |
| 等上游支持绝对 `PI_CONFIG_DIR` | 已被上游明确 `wontfix`，不是可等待项 |

## Scope

### In scope

- 一次性 runtime 根的位置与 `PI_CONFIG_DIR` 取值。
- 三个客户端共用该位置带来的影响复核（凭据暂存、`_require_external_directory` 判定）。
- 对应测试与两端 CI 的 `--fresh` smoke 覆盖。

### Out of scope

- 不改默认持久 runtime 路径（#104 已按契约修正，工作正常）。
- 不改能力闭包、prompt、Skill 正文或任一客户端 adapter 输出。
- 不改 `cap` 命令面。
- 不为 Windows 放宽 POSIX 侧任何既有检查。
- 不处理 codex／qoder 在 Windows 上的凭据 symlink 暂存（需要额外权限，属独立取舍）。

## Baseline Evidence

- `src/agent_system/profile/cli.py` 的 `run_client` 与 probe 路径各自用 `tempfile.TemporaryDirectory(prefix="profile-…")` 建立一次性根。
- `build_launch` 的 omp 分支把该根作为 `PI_CONFIG_DIR` 的取值。
- `PortableDirectoryTests.test_directory_below_the_user_home_is_accepted` 固定了「home 之下被接受」的既有行为。
- 已通过的路径与失败点见 #109 正文的实测记录。

## Rollback Boundary

单个提交可 revert；不涉及 `.cap/lock.json` 或任何声明面变更，也不改变已提交的 `tree_hash`。

回滚后 `--fresh` 回到当前的不可用状态，其余路径不受影响。

## Risks

- **残留位置改变**：清理失败时残留从系统临时目录变成用户 home 下的 CAP 目录。需确认清理路径在成功与异常下都不留内容。
- **三客户端共用**：codex 与 qoder 的一次性根一并移动，需复核其凭据暂存与目录安全判定不受影响。
