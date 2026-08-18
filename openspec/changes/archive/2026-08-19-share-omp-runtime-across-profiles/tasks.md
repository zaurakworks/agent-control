## 1. 基线与迁移门禁

- [x] 1.1 记录两个 profile 的公共 inventory、portable 三端 render hash、`.cap/lock.json`、旧 OMP roots、无 secret settings/auth 摘要和 Session 清单，确认 profile 声明与中文 `SKILL.md` 不需要修改
- [x] 1.2 在 `tools/cap.py` 定义共享 runtime、profile generation 和 migration backup 的固定 CAP 管理路径，并新增显式 `migrate-omp-runtime` dry-run／`--apply` 接口
- [x] 1.3 让普通持久 OMP 启动在旧 roots 尚未迁移或 staged/shared 状态不完整时失败并提示迁移命令，不在高频路径隐式复制、选择或删除状态
- [x] 1.4 实现无 secret migration preflight：验证 no-follow/owner/mode、状态静止、SQLite schema、规范化 settings、`memory.backend`、credential provider/type/identity 摘要和 Session 内容摘要
- [x] 1.5 实现私有 backup、canonical 选择、SQLite 状态复制、Session 去重合并、冲突即停、staged 校验和共享 root 原子安装；不迁移 WAL/SHM、terminal breadcrumb 或临时文件
- [x] 1.6 实现仅针对固定 CAP 管理 roots 的清理门禁；保留 `<project>.auth/codex`、`qoder`，拒绝真实 HOME 客户端目录、symlink ancestor、路径别名和越界删除

## 2. 共享 runtime 与 profile overlay

- [x] 2.1 把持久 OMP home 固定为 `<agent-home-root>/shared/omp`，让两个 profile 使用相同 `PI_CODING_AGENT_DIR`、`PI_CONFIG_DIR`、本地 `agent.db` 和默认共享 Session 目录
- [x] 2.2 把 profile tool 的已锁 OMP render 物化为 `<agent-home-root>/renders/<profile>/omp/<effective-hash>` 内容寻址 generation；generation 已存在时核对内容，不重写或使用可变 current symlink
- [x] 2.3 生成 effective `config.yml`：固定 `memory.backend=off`、profile Skill custom directory/include allowlist、关闭 Codex/Claude/Pi/Agents user/project Skill 来源和 `mcp.enableProjectConfig`
- [x] 2.4 更新 OMP 命令：引用当前 generation 的 config/system prompt/显式 extension，保留 `--no-extensions`、`--no-rules` 和精确 `--skills`／`--no-skills`，不传 profile 专属 `--session-dir`
- [x] 2.5 更新持久环境：保留真实 `HOME`、ambient credential 清理、`PI_AUTH_NO_BORROW` 和 metadata 防护；删除 broker URL/token 注入并让 OMP 使用共享本地 credential store
- [x] 2.6 更新 preview 与 receipt，分别报告 portable profile hash、共享 runtime root、profile generation/effective hash、active profile 和现有 digest，且不记录参数值、配置正文或认证材料
- [x] 2.7 删除 `_OmpAuthBinding`、auth-root validator、持久 OMP broker错误路径和只服务该路径的常量；保留 Codex、Qoder、`--fresh` 使用的全局 `--auth-root` 参数

## 3. 聚焦行为测试

- [x] 3.1 扩展 `tests/test_cap.py`，覆盖两个 profile 共享 OMP home、认证/settings/Session 路径且环境无 broker变量，Codex/Qoder/`--fresh` 参数合同不回归
- [x] 3.2 覆盖 effective config、system prompt、Skill custom directory/allowlist/source toggles、memory off、project MCP off、显式 extension 与 `--no-extensions`／`--no-rules` 固定命令
- [x] 3.3 覆盖不同 profile 和不同 hash 的 immutable generations、同 hash 复用、篡改拒绝，以及两个 profile 并发 materialize/launch 不删除或替换对方文件
- [x] 3.4 覆盖 migration 的零/单/双旧根、等价 canonical、settings/auth冲突、Session去重/冲突、活动写入、失败回滚、幂等 dry-run/apply 和 staged 原子安装
- [x] 3.5 覆盖清理只删除 CAP 管理的旧 profile roots、backup 与 `<project>.auth/omp`，拒绝真实 HOME、Codex/Qoder auth、symlink、hardlink/路径别名和未完成验证状态
- [x] 3.6 覆盖同一 Session 跨 `general -> assembly-helper -> general` 时使用同一 Session identity 并切换当前 profile generation/prompt/Skill roster，运行 `python3 -m unittest tests.test_cap`

## 4. 中文摘要文档

- [x] 4.1 更新 `README.md`，把持久 OMP 说明改为共享 runtime、共享登录/settings/Session 与 profile 启动 overlay，删除每 profile 登录和 broker bootstrap 指引
- [x] 4.2 更新 `docs/maintenance.zh-CN.md`，记录 migration dry-run/apply、冲突即停、immutable generation、跨 profile resume、并发验证和只清理 CAP 管理状态的流程
- [x] 4.3 明确 `--no-extensions`／`--no-rules` 是长期门禁，磁盘清理只属于 migration；当前 MCP/Hook/Plugin 为空且实际不可可靠观察时保持 unknown
- [x] 4.4 明确本变更不修改 `.cap` profile、prompt、中文 `SKILL.md`、能力 inventory 或 lock，不删除真实 HOME 客户端配置，也不改变 Codex/Qoder/`--fresh` auth-root

## 5. 状态迁移与配置态验证

- [x] 5.1 运行真实 `migrate-omp-runtime` dry-run，确认旧 runtime 无活动写入并审查无 secret canonical/settings/auth/Session plan；发现实质冲突时在任何写入前停止
- [x] 5.2 执行 migration apply，核对私有 backup、共享 `agent.db`、settings/auth 真源和两个旧根的 Session 合并结果，保留旧 roots 与 backup 直到行为验证完成
- [x] 5.3 运行 `python3 tools/cap.py skills-validate`、`python3 tools/cap.py verify` 与两个 profile 的 portable/effective preview，确认标准合规、binding、inventory 和 `.cap/lock.json` 不变且 generation/hash/门禁正确
- [x] 5.4 运行 `npx openspec validate share-omp-runtime-across-profiles --type change --strict --json`

## 6. 生效态与清理验证

- [x] 6.1 使用共享本地登录先由 `general` 创建真实 Session，再以同一 Session id 由 `assembly-helper` 和 `general` 恢复，观察 transcript连续、当前 profile marker 和 Skill roster随启动 profile切换且不再次登录
- [x] 6.2 并发启动 `general` 与 `assembly-helper` 真实 OMP，请求分别输出 profile/Skill marker，确认共享 SQLite 正常且两边 generation 内容和 effective hash 未被改写
- [x] 6.3 通过真实 OMP `/mcp` 或等价可重复观察核对没有 ambient MCP；Hook/Plugin 无可靠观察时报告 unknown，不用文件缺失或模型自述冒充 observed empty
- [x] 6.4 检查输出、receipt、preview、migration plan/backup metadata 和诊断不含参数值、真实用户配置正文、认证路径、token、环境值或 secret
- [x] 6.5 在 6.1–6.4 全部通过后按用户授权删除旧 profile roots、migration backup 和 `<project>.auth/omp`，保留 Codex/Qoder auth 与真实 HOME 数据
- [x] 6.6 清理后重新运行单元测试、CAP closure/preview、OpenSpec strict validation、双 profile请求和同一 Session跨 profile resume，分别报告标准合规、声明态、配置态与生效态结果

## 7. 用户级 runtime 与全局 CAS 修订

- [x] 7.1 记录当前项目级 shared runtime/render、用户级 runtime/CAS 目标、全局 settings/auth/Session 摘要和现有 closure/hash，确认用户目录不含可编辑 profile catalog
- [x] 7.2 在 `tools/cap.py` 新增稳定 `--omp-runtime-id` 与可选 `--omp-runtime-root`，默认解析为批准真实 HOME 下 `$HOME/.cap-user-state/runtimes/omp/default`；`--agent-home-root` 只保留为项目迁移源
- [x] 7.3 把 immutable generation 移到 `$HOME/.cap-user-state/renders/omp/<effective-hash>`，hash/manifest 纳入当前项目 portable tree、profile/layer digest、adapter version、effective config 与 fixed gates；每次先验证当前项目再复用 CAS
- [x] 7.4 覆盖全局 CAS 缺失重建、篡改/额外文件/错误来源摘要拒绝、同内容跨 worktree复用，以及 manifest 未声明 profile 时即使 cache 存在也拒绝启动
- [x] 7.5 扩展 `migrate-omp-runtime`，以当前项目 `<project>.agent-homes/shared/omp` 为源、用户级 runtime id 为目标，支持目标缺失原子安装、等价目标 Session 合并、冲突即停和只清理项目级迁移源
- [x] 7.6 更新 preview/receipt，记录 runtime id/global root、当前项目 source/profile/layer digest、global CAS generation/effective hash、workdir 和 fixed gates；不把 cache 存在报告为声明态成功
- [x] 7.7 扩展单元测试覆盖多 workdir/显式项目、全局 SQLite、runtime id隔离、CAS poisoning/重建/并发、global migration/cleanup和跨 cwd Session resume，运行 `python3 -m unittest tests.test_cap`
- [x] 7.8 更新 `README.md` 与 `docs/maintenance.zh-CN.md`，明确 profile语义可跨workdir但权威来源仍是当前Git项目 `.cap`，用户级runtime/CAS只保存状态和经验证缓存

## 8. 全局化迁移与验证

- [x] 8.1 运行用户级 migration dry-run，核对项目级源与global目标的无secret schema/settings/auth/Session plan；发现runtime id或状态冲突时在写入前停止
- [x] 8.2 执行global migration apply，核对用户级runtime marker、共享本地认证/settings/Session、MCP policy和global CAS，保留项目级源/backup直到行为验证完成
- [x] 8.3 运行 Skill标准、CAP verify、两个profile的portable/global effective preview和OpenSpec strict validation，确认当前项目manifest/inventory/lock不变且CAS可删除重建
- [x] 8.4 从至少两个不同workdir使用同一runtime完成 `general`、`assembly-helper` 请求；显式用同一Session path跨cwd/profile恢复并观察当前overlay切换，不把cwd分组报告为隔离
- [x] 8.5 并发启动不同workdir/profile，确认global SQLite与CAS generation稳定；真实 `/mcp reload` 无connected ambient server/tool，Hook/Plugin保持准确unknown
- [x] 8.6 检查global migration/preview/receipt/output不含参数值、用户配置正文、认证路径、token、环境值或secret
- [x] 8.7 在8.1–8.6通过后按授权删除当前项目级shared runtime/renders/migration backup，保留global runtime/CAS、当前 `.cap`、真实 `~/.omp` 和其他客户端数据
- [x] 8.8 清理后重跑单元测试、closure、global preview、strict validation、跨workdir双profile请求和跨cwd Session resume，分别报告标准合规、声明态、配置态与生效态
