# 实施任务

## 1. 一次性根的位置

- [x] 1.1 把一次性 runtime 根改到真实 home 之下的 CAP 自有目录 —— **已完成**

**描述**：`run_client` 与 probe 路径各自用 `tempfile.TemporaryDirectory(prefix="profile-…")` 建立一次性根，落在系统临时目录。改为落在 `$HOME/.agent-system-state/` 之下的 CAP 自有目录，两端同一实现，不引入平台分支。

**依赖**：无
**验收**：

- 一次性根位于真实 home 之下；两端行为一致，代码中无平台判断。
- `_require_external_directory` 接受新位置（既有测试 `test_directory_below_the_user_home_is_accepted` 已固定该行为）。
- 正常结束与异常中止两条路径都不留残留。

- [x] 1.2 `PI_CONFIG_DIR` 取一次性根相对 home 的名字 —— **已完成**

**描述**：`build_launch` 的 omp 分支当前把根作为绝对路径传入。omp 契约是该变量为相对 home 的名字，只有 `PI_CODING_AGENT_DIR` 经过 `resolve()`。

**依赖**：1.1
**验收**：

- `PI_CONFIG_DIR` 为 home 相对名，`PI_CODING_AGENT_DIR` 仍为绝对路径。
- 与 home 拼接后指向一次性根本身，不出现路径被拼两次。

## 2. 复核共用影响

- [x] 2.1 复核 codex 与 qoder 的一次性根移动后不受影响 —— **已完成：三客户端既有测试全部通过，未新增平台分支（有测试直接断言位置选择中无 `os.name` / `sys.platform` / `platform.system`）**

**描述**：三个客户端共用一次性根位置。需确认凭据暂存与目录安全判定在新位置下不变。

**依赖**：1.1
**验收**：三个客户端的既有测试全部通过，且无新增平台分支。

## 3. 测试与证据

- [x] 3.1 补测试 —— **已完成：7 个 unittest，其中「home 之外不可命名」一条在 Windows 上跳过、在 Linux 上真正执行——正是本变更要说明的两端差异**

**依赖**：1.2
**验收**：

- 新位置被 `_require_external_directory` 接受。
- `PI_CONFIG_DIR` 取值为 home 相对名，且拼接结果正确。
- 清理在成功与异常路径下都不留内容。

- [x] 3.2 在真实客户端上取得 `--fresh` 的生效态证据 —— **已完成：见 `evidence/fresh-run-check.json`。`SKILLS-AVAILABLE:14` 与 `CAP-FRESH-OK`；生效态等级记为 self-reported，不是逐项 probe**

**描述**：按 #109 的实施说明起 broker 并实跑。

**依赖**：3.1
**验收**：

- `cap run agent-assembler --fresh --auth-root <vault>` 成功拉起 omp 并进入模型调用。
- 取得自述标记与 receipt。
- 只有拿到真实客户端证据才把实际生效态从 `unknown` 改写；拿不到就保持 `unknown` 并说明原因。

- [x] 3.3 两端 CI 覆盖 `--fresh` smoke

**依赖**：3.2
**验收**：`cross-host-checks` 在两端执行 `--fresh` 路径的 smoke，使结论由自动门禁产生而非单机手工记录。

**实施说明（2026-08-20）**：`EphemeralRuntimeRootTests` 已加入 `windows-assembly`、`posix-assembly` 与新增的 `macos-assembly` 三个 job。该组用例真实构造并销毁一次性根，断言它落在真实 home 之下、可表达为 client 需要的 home 相对名、通过目录门禁、且位置选择中不含平台分支。

**门禁覆盖不到的部分**：真实拉起 omp 进程的 `--fresh` 启动不在 CI 内 —— runner 上既没有 omp 二进制，也不应放置认证凭据。因此「`--fresh` 能真正启动客户端」这一条仍只有单机手工证据（Windows，见 #109 的验收记录），生效态维持 `self-reported`，不因本 CI 升级为 `observed`。
