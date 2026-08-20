> 第 1、2 组与 4.6 已由上游 #84／#85 落地，实现细节与本文件描述不完全一致（见 `proposal.md` 的《与已落地上游工作的关系》）。保留条目以维持任务编号与验收记录的连续性。

## 1. 提交一：平台中立的资产权限位（已由上游 #84 落地）

- [x] 1.1 在 `src/agent_system/profile/cli.py` 增加统一的资产权限位来源，供 `_input_records` 与 `_render_tree` 共用，普通文件取规范值 `0644`
- [x] 1.2 在能表达 POSIX 权限语义的宿主上校验实际权限位，拒绝携带可执行位或 group／other 写位的锁定输入与渲染源，错误信息指明具体资产路径
- [x] 1.3 补单元测试：同一份资产在两种权限位报告下产出相同 `inputs` 记录与相同 `tree_hash`；POSIX 上可执行资产与 group／other 可写资产被拒绝
- [x] 1.4 确认 `.cap/lock.json` 内容不变：运行 `uv run cap lock` 后 `git diff --exit-code .cap/lock.json` 为空

## 2. 提交一的验证与门禁（跨宿主 CI 由本 change 交付）

- [x] 2.1 在 Windows 宿主运行 `uv run cap agents`、`uv run cap profiles`、`uv run cap show agent-assembler`，确认返回声明态闭包且不再报 lock drift
- [x] 2.2 在 Windows 宿主运行 `uv run cap assembly-bind general`、`uv run cap assembly-bind agent-assembler`、`uv run cap verify`，确认 `verify` 返回 `{"status": "ok"}`
- [x] 2.3 在新增的 workflow 文件中补一个 `ubuntu-latest` job，跑与 Windows job 相同的 lock 复现检查（`uv run cap lock` 后 `git diff --exit-code .cap/lock.json`），使"同一提交在两端产出相同 digest"由两侧门禁共同证明，而不是靠单机手工核对；现有三个 `ubuntu-latest` job 仍不改动；该 workflow 文件随之改名为中性名
- [x] 2.4 新增 `windows-latest` CI job，覆盖平台中立权限位用例、`cap lock` 复现检查与 `cap show`，并保持现有三个 `ubuntu-latest` job 不变
- [x] 2.5 运行 `uv run cap skills-validate` 与仓库既有检查，确认无回归

## 3. 提交二：按簇迁移目录安全校验

簇的划分与函数清单见 `design.md` 的 D2。每完成一簇都要求 POSIX 回归全绿再进入下一簇。

- [x] 3.1 A 簇：把 `_open_stable_directory` 改为逐分量 `os.lstat` 校验（macOS 用 `stat.S_ISLNK`，Windows 用 `st_file_attributes` 判 `FILE_ATTRIBUTE_REPARSE_POINT`，检查集合两端相同），`StableDirectory` 改为承载路径与 `st_dev`／`st_ino` 身份而不再持有描述符，`_validate_stable_directory`／`_close_stable_directory`／`_stable_directory_is_within`／`_stable_directory_is_same` 随之改写
- [x] 3.2 调整 `_normalize_root_alias`：保留 macOS 根别名归一化，去掉对非 `/` anchor 的一律拒绝
- [x] 3.3 A 簇测试：普通目录通过；路径分量为符号链接、junction 或其他重解析点被拒；取得引用后目录被替换时操作失败；跨卷路径行为明确
- [x] 3.4 B 簇：`materialize_profile` 的空目录判定、`_state_root` 的空目录判定、`_strict_json_from_directory` 的私有读取改为按路径操作，保留原有拒绝条件
- [x] 3.5 E 簇：按 design D7 把 `_materialize_tree` 改为先在 cap 独占创建的私有暂存目录中写完整棵树，校验通过后紧邻一次身份复核再一次性移入目标；`fsync` 时序与目录创建顺序原样保留，不得因移植而放宽
- [x] 3.5a 用例：渲染中途把目标目录改名并替换为指向他处的符号链接，断言该次渲染失败**且替换后的对象保持为空**（当前实现会在检出前把子目录写进去，这是必须修掉的回归）
- [x] 3.6 F 簇：`_reserve_receipt`、`_validate_receipt_reservation`、`_commit_receipt`、`_unlink_reserved_receipt`、`_release_receipt` 改为按路径操作，`O_EXCL` 独占创建语义与预留身份复核原样保留
- [x] 3.6a 按 design D8 更新 `test_reserved_receipt_parent_cannot_be_redirected` 与 `test_observed_state_swap_cannot_redirect_evidence`：保留全部安全断言（错误抛出、替换后的目录保持为空），把"占位文件已被回收"改写为"占位文件保持为空"，并在用例名或注释中标明这是已知边界而非疏漏
- [x] 3.7 固定临时根位于用户主目录之下仍被接受的行为（`%LOCALAPPDATA%\Temp`），并补一条测试防止日后收紧规则时静默破坏 Windows；同时固定"用户主目录本身仍被拒绝"
- [x] 3.8 覆盖长路径场景，按 `knowledge/windows-agent-ops.md` 处理：该知识的口径是"按最弱消费者守门、不自动开启机器长路径策略"，因此不追求长路径可用，只固定"超限以 `could not materialize tree` 报错而非裸 OSError"，并在使用指南写明约束
- [x] 3.9 每簇完成后在 POSIX 宿主跑完整 `tests/profile` 与 `tests/cap`，确认保持全绿；任一簇掉绿按移植回归处理，不以平台差异解释

## 4. 提交二：C／D 簇——认证检查按可表达性分类

- [x] 4.1 C 簇：把 `_validate_private_directory`、`_read_private_file` 与 `_validate_private_tree` 中的属主判定与 `0o077` 私有性判定改为条件检查：能表达的宿主保持为门，不能表达的宿主产出显式的未知结论
- [x] 4.2 保持 `st_nlink` 硬链接数检查在两端均为门（实测 Windows 原生可用）
- [x] 4.3 把未知结论接入三层证据报告与 `cap verify` 输出，确保它不会被读成通过
- [x] 4.4 补单元测试：POSIX 上对 group／other 开放的认证目录被拒；无法表达的宿主上产出未知而非通过、且不阻断启动；两端硬链接数大于一均被拒
- [x] 4.6 第 7 簇（由上游 #85 落地，实现比本文件描述更强）：按 D4 同一条规则处理 `src/agent_system/omp/runtime.py` 的 `_validate_private_runtime`（`os.geteuid()`），使 `cap show <profile> --cli omp` 在 Windows 上不再崩溃
- [x] 4.5 D 簇：确认 codex 与 qoder 的 `_create_auth_symlink` 路径在 Windows 上给出明确的"该客户端在本宿主暂不支持"错误，而不是含糊的失败

## 5. 提交二的验证与 smoke check

- [x] 5.1 在 Windows 宿主运行 `uv run cap render agent-assembler --cli omp --output <项目外空目录>`，确认产出完整装配树
- [x] 5.2 在 Windows 宿主运行 `uv run cap show agent-assembler --cli omp`，确认返回该客户端的目标装配与渲染 hash
- [~] 5.3 **部分完成**：Windows 上 `cap run agent-assembler` 已能成功拉起 omp 并进入模型调用——原判定的"上游阻塞"经上游裁定（[oh-my-pi#9067](https://github.com/can1357/oh-my-pi/issues/9067) `wontfix`）更正为 cap 误用 `PI_CONFIG_DIR`，已按契约修正。**生效态自述标记仍未取得**，因为默认共享运行时路径主动删除 `OMP_AUTH_BROKER_*`，`--auth-root` 的 broker 凭据不在该路径生效；这是独立的设计问题，见 `work/records/2026-08-20-omp-windows-agent-dir/finding.md`
- [x] 5.4 按三层证据记录结论：声明态与配置态由两端 CI 门禁给出通过依据；实际生效态保持 `unknown`，原因是上游阻塞而非验证缺失
- [x] 5.5 扩展 `windows-latest` CI job 覆盖 render smoke，使 Windows 结论不依赖单机手工执行

## 6. 文档与合同同步

- [x] 6.1 更新 `docs/cap-guide.zh-CN.md`：补充 Windows 宿主的可用命令范围、渲染输出目录的 Windows 示例（当前只给了 POSIX 路径）、认证私有性结论为未知的含义与故障排查条目
- [x] 6.2 复核 `docs/profile.md` 与 `docs/maintenance.zh-CN.md`：两份文档均未描述权限位记录方式或目录句柄保证，没有因本变更失真的表述，因此不改；保证边界写入使用指南的《宿主之间的差异》
- [x] 6.3 复核 `.cap/capabilities/skills/*` 与 `.cap/skill-imports.toml`：无变更；`.cap/lock.json` 全程未产生差异，`cap verify` 通过，可证闭包未动
- [x] 6.4 运行 `npx openspec validate enable-windows-cap-assembly --strict` 并通过
- [~] 6.5 归档前确认 OpenSpec 校验与 `cap verify` 在两端均通过；Windows 侧已由 `cross-host-checks` 的 `windows-assembly` job 覆盖（含 render smoke），POSIX 侧由 `posix-assembly` 与 `checks` 覆盖。实际生效态的归档结论待上游解除阻塞
