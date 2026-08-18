## Why

`general` 与 `assembly-helper` 是当前 Git 项目显式声明的用户角色，不是目标业务仓的身份或状态边界。项目级共享 runtime 已解决 profile 间重复登录，但仍会让每个 agent-assembly worktree／项目副本维护另一份认证、settings 和 Session；用户明确希望这些 OMP 状态跨 profile、workdir 和项目复用。需要把 runtime 与 immutable render cache 提升为用户级 CAP 状态，同时保持 `.cap/manifest.toml`、profile、prompt、capabilities 和 lock 始终由当前 Git 项目授权，绝不从用户目录缓存反向发现或继承业务能力。

## What Changes

- **BREAKING**：持久 OMP 的默认 runtime 从 `<project>.agent-homes/shared/omp` 移到用户级 `$HOME/.cap-user-state/runtimes/omp/default`；认证、settings、Session、history、models/cache 和关闭状态的 memory 跨当前项目的 profile、workdir 与其他显式使用同一 runtime id 的 CAP 项目共享。
- 增加显式 OMP runtime id/root 概念；当前默认 id 为 `default`。runtime id 表示用户状态/身份域，不与 CAP profile 名称绑定，未来需要不同账号或安全域时使用不同 id。
- Profile 的语义可以跨 workdir 使用，但其**权威来源与选择仍是当前 Git 项目**：只有当前项目 `.cap/manifest.toml` 列出的 profile、当前 `.cap/lock.json`、base pin 和 derived binding 可以生成启动 overlay。`$HOME/.cap-user-state` 不保存可编辑 profile catalog，也不能补齐 prompt、Skill、MCP、Hook 或 Plugin。
- OMP effective render 改为用户级内容寻址 CAS：`$HOME/.cap-user-state/renders/omp/<effective-hash>`。CAS 只是可丢弃缓存；每次使用必须由当前项目重新计算 portable tree、adapter version、profile/layer digest、effective config template 和固定门禁，核对 generation manifest/content 后才能复用。
- 当前项目继续提供 `general`、`assembly-helper` 的 system prompt、Skill allowlist 和显式 extension；目标 workdir 只提供原生父级/仓库 context 与源码，不会因全局 runtime/cache 自动获得业务能力。
- Session 继续使用 OMP 全局默认目录并按 cwd 组织；cwd 分组只是默认查找与展示约定，不是授权边界。显式 Session id/path 可以跨 profile、worktree 或项目恢复，并在恢复时重新应用当前项目当前 profile 的 prompt/Skills。
- 保留 `--no-extensions`、`--no-rules`、ambient Skill source关闭、project MCP discovery关闭和共享 runtime MCP denylist；真实 `/mcp reload` 必须没有 connected ambient server/tool。Hook/Plugin 无可靠观察时保持 unknown。
- `memory.backend` 在全局 runtime 与每个有效 overlay 中显式固定为 `off`。
- `migrate-omp-runtime` 增加“项目级 shared runtime -> 用户级 runtime”迁移：目标不存在时原子迁移；目标已存在时无 secret 比较 schema、settings、credential identity 和 Session，冲突时在覆盖/删除前停止。
- 验证用户级 runtime/CAS 后，按已授权边界删除当前 CAP 项目管理的项目级 shared runtime、项目 render generations 和 migration staging；不删除当前 Git 项目的 `.cap` 声明，不删除真实 `~/.omp` 或其他客户端配置。
- receipt 记录 `runtime_id`、全局 runtime root、当前项目 profile/layer digest、portable/effective render hash、workdir 和退出状态；不得保存参数值、认证正文、token、配置正文或环境值。
- 非目标：不把 `$HOME/.cap-user-state` 变成 profile source、catalog 或 marketplace；不允许未带当前项目 manifest/lock/binding 的客户端从全局 CAS 启动；不在本 change 新增业务 MCP、Hooks、Plugin、Rules 或 memory；不修改 profile prompt 和中文 Skill 正文；不把 cwd 分目录宣称为安全隔离。
- 回滚边界：全局迁移前备份当前项目 shared runtime；跨 workdir/profile 真实验证通过后再删除项目级状态。清理前可回滚；清理后保留全局 runtime，只做前向修复，不恢复 broker 或 profile/project 专属认证副本。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `layered-agent-profile`: 把持久 OMP 从项目级共享 runtime/render 提升为用户级 CAP runtime 与全局 CAS，同时规定当前 Git 项目 `.cap` 仍是 profile/prompt/capability 的唯一权威，定义跨 workdir Session、缓存校验、迁移、ambient 门禁和证据边界。

## Impact

- 受影响实现：`tools/cap.py` 的 runtime root/id、global render CAS、generation manifest校验、迁移、preview、receipt 和 cleanup；`tests/test_cap.py` 的多项目/多 workdir、cache poisoning、global migration 与 resume 覆盖。
- 受影响文档：`README.md`、`docs/maintenance.zh-CN.md`；明确“profile 语义全局可选”和“profile 权威仍由当前项目显式声明”的区别。
- 受影响私有状态：当前 `<project>.agent-homes/shared/omp`、项目 renders 与 `$HOME/.cap-user-state/runtimes|renders`；均不进入 Git。真实 `~/.omp`、其他客户端配置和 `.cap` 声明不作为迁移目标。
- 受影响 profile：当前项目显式列出的 `general`、`assembly-helper` 的持久 OMP；Codex、Qoder、`--fresh`、prompt/Skill inventory 和项目 `.cap/lock.json` 不应变化。
- 已完成基线：项目级 shared runtime 已迁移本地认证/settings 和 Session，双 profile共享/并发/resume、MCP active empty、28 项单元测试与 CAP closure 均通过；这部分证据保留，但不能替代全局 root/CAS 和跨 workdir验证。
- 控制设计的一手来源：OMP 17.3.7 默认 Session 目录由全局 agentDir 与 encoded cwd 共同计算，显式 resume仍可跨 cwd；resume重新构建 system prompt/Skills。仓库规则要求 profile、prompt、capability 只从当前 Git 项目显式声明，因此用户级目录只允许保存 runtime/CAS，不得成为业务能力权威。
- 兼容性：profile 名和高频启动接口保持不变；新增 runtime root/id 参数。尚未完成全局迁移、当前项目校验或 CAS content核对时持久启动必须失败，不得静默回落项目 runtime、真实 `~/.omp` 或未验证缓存。
