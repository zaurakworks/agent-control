## Context

见 `proposal.md` 的 Why。前一轮实现已把 `general` 与 `assembly-helper` 从 profile 专属 home 迁移到 `<project>.agent-homes/shared/omp`，合并本地认证、settings 和 Session，并用项目级 immutable generations 注入 profile overlay。真实双 profile、并发、跨 profile resume 和 MCP active-empty 已验证。用户进一步确认这些状态与角色应跨 workdir／agent-assembly worktree复用，因此 runtime 和 render cache 应提升到用户级；但仓库规则要求 profile、prompt、capability 只能来自当前 Git 项目显式声明，用户目录不得成为业务能力真源。

OMP 17.3.7 的默认 Session 路径由全局 agentDir 与 encoded cwd 共同计算，显式 Session id/path 仍可跨 cwd；该目录组织不是授权边界。Resume 会重新解析当前启动的 system prompt/Skills。全局化可以复用这些原语，但必须把“用户级状态/CAS”与“当前项目权威声明”严格分离。

## Goals / Non-Goals

**Goals:**

- 用用户级 CAP runtime id `default` 跨 profile、workdir 和显式 CAP 项目共享 OMP auth/settings/Session/cache。
- 用用户级内容寻址 CAS 复用已验证 profile generations，避免每个 worktree复制相同 render。
- 保持当前 Git 项目的 `.cap` manifest/profile/prompt/capabilities/lock/binding 为每次启动的唯一授权来源。
- 允许删除整个 CAS 后从当前项目重建，拒绝 cache poisoning、其他项目隐式继承和未声明 profile。
- 把已验证项目级 shared runtime 安全迁移到全局 root，并完成跨 workdir真实验证后清理项目级状态。

**Non-Goals:**

- 不把 `$HOME/.cap-user-state` 变成 profile catalog、source repo、marketplace 或可编辑 prompt/Skill 存储。
- 不允许裸 OMP、其他项目或未绑定客户端仅凭全局 generation path 启动当前 profile。
- 不把 cwd Session 分目录声明为安全隔离；跨 cwd显式 resume 是用户选择的共享行为。
- 不在本 change 新增业务 MCP、Hook、Plugin、Rule 或 memory。
- 不修改当前项目 profile prompt、中文 Skill 正文、manifest inventory 或 `.cap/lock.json`。
- 不直接复用或删除真实 `~/.omp`、`.claude`、`.codex`、`.agents`、`.qoder`。

## Decisions

### 1. 当前 Git 项目始终是 profile 权威

每次 `cap use/run/show` 都从显式 `--project`（默认当前 agent-assembly Git 根）加载 `.cap/manifest.toml`，选择其列出的 profile，验证项目 lock、real-home pin 和 derived binding，再计算 portable/effective render。用户级目录不提供 profile列表、prompt、Skill或 capability lookup。

Profile “用户级”只表示同一项目声明的角色可从不同 workdir调用，并不改变权威顺序。其他项目若要复用同一 profile，必须显式把该 agent-assembly 项目作为 `--project`，或拥有自己的 `.cap` 声明并独立计算出相同 hash；目录位置和同名 cache 不产生继承。

### 2. 用户级 runtime id 与显式参数

默认状态根：

```text
$HOME/.cap-user-state/runtimes/omp/default/
```

增加： 

```text
--omp-runtime-id default
--omp-runtime-root <可选显式目录>
```

未传 root 时由批准的真实 HOME 和 runtime id 确定；id 必须使用稳定小写标识，不得含路径。`--agent-home-root` 继续只表示当前项目旧状态/迁移来源，不再决定持久 OMP runtime。不同账号或安全域将来使用不同 runtime id，不复用 CAP profile 名。

全局 runtime 只保存 OMP 自有 `agent.db`、settings、sessions、models/cache 和 MCP deny policy；`memory.backend` 固定 `off`，不保存 profile prompt/Skills/render。

### 3. 用户级 render CAS 是不受信任缓存

默认 CAS：

```text
$HOME/.cap-user-state/renders/omp/<effective-hash>/
```

Effective hash 输入：

- 当前项目已锁 portable OMP tree hash；
- 当前 profile 名、profile/layer digest；
- OMP adapter version；
- 规范化 effective config template；
- fixed launch flags 与 Skill allowlist；
- generation manifest schema version。

不把项目绝对路径或用户级 CAS 路径作为 profile权威输入；相同内容可跨 worktree复用。Generation manifest记录上述摘要与 content digest。每次使用前，CAP必须先验证当前项目，再重新计算期望 hash，最后核对 manifest/content；CAS中额外目录、同名 profile、篡改内容或错误来源摘要均失败。Generation不存在时从当前项目 materialize 到私有 stage后原子安装；存在时只读核对，不重写。

删除 CAS 不影响声明态；重新运行当前项目 render必须得到相同 generation。CAS本身不进入 `.cap/lock.json`，只在 effective preview/receipt中作为配置态证据。

### 4. 当前启动 overlay 与长期门禁

OMP进程保留真实 HOME，并设置全局 `PI_CODING_AGENT_DIR`／`PI_CONFIG_DIR` 与 `OMP_PROFILE=default`。每次启动固定传入当前项目验证 generation 的：

- `--config`；
- `--append-system-prompt`；
- `--extension`；
- `--skills` 精确 allowlist或 `--no-skills`；
- `--no-extensions`；
- `--no-rules`。

Effective config固定 `memory.backend=off`、Skill custom directory/include allowlist、关闭 Codex/Claude/Pi/Agents user/project Skill来源和 `mcp.enableProjectConfig`。Real-home manifest/pin继续阻断新 ambient能力；共享 runtime `mcp.json` denylist屏蔽已观察 server。真实 `/mcp reload` 以 connected server/tool为准，disabled配置不算 active capability；Hook/Plugin不可可靠观察时保持 unknown。

### 5. Session 全局共享但 cwd 不是权限边界

不传 `--session-dir`。OMP把默认 Session放在全局 runtime下按 encoded cwd组织；这只影响默认 picker/continue。显式 id/path可以跨 profile、worktree或项目恢复。恢复后保留 transcript/session identity，当前项目/profile的prompt、Skills和显式能力重新构建。

Receipt记录真实 workdir和可观察 Session id（若客户端提供）；不得把“当前 cwd只看到自己的默认 Session列表”报告为安全隔离。

### 6. 全局 runtime/CAS 并发与生命周期

多个 workdir/profile并发共享全局SQLite，使用OMP原生WAL/busy-timeout；CAP不复制或同步多个DB。Generations不可变，可被任意并发进程只读。CAS GC不在本change实施；旧generation可保留，未来GC必须依据内容和活动引用，不能按项目删除全局缓存。

全局 MCP denylist会影响同一runtime id的所有CAP项目，这是当前“默认runtime无active MCP”策略。未来项目需要不同MCP策略时，应使用另一runtime id或等待OMP提供per-launch MCP allowlist，不能从项目目录偷偷恢复被全局禁用的server。

### 7. 项目级 shared runtime 迁移到用户级

`cap migrate-omp-runtime`使用当前项目级 `<project>.agent-homes/shared/omp` 作为迁移来源，用户级runtime作为目标：

1. 默认dry-run验证当前项目lock/binding、源/目标owner/mode/no-follow、SQLite静止/schema、settings、credential identity、Session摘要和runtime id。
2. 目标不存在：私有backup源，SQLite backup与Session稳定复制到用户级stage，写global marker/MCP policy后原子安装。
3. 目标存在：比较schema/settings/credential identity；等价时只合并内容不冲突的Session，实质冲突在写入前失败。
4. 项目级 renders不迁移；它们由当前项目重新计算并写入全局CAS。
5. 全局双profile、跨workdirresume、并发、closure、MCP和无secret验证通过后，`--cleanup`只删除当前项目级shared runtime、项目renders和migration backup，不删除全局runtime/CAS、当前`.cap`或真实HOME客户端目录。

当前实现已清理更早的profile专属roots和broker；这次迁移只处理现存项目级shared runtime/renders。

### 8. Preview、receipt 与证据分层

Effective preview/receipt增加：

- `runtime_id`；
- global runtime root；
- 当前项目root/source digest；
- profile/layer digest；
- portable tree hash；
- global CAS generation与effective hash；
- fixed gates、workdir、退出状态。

不记录参数值、credential/config正文、token、环境值或Session transcript。

- 标准合规：当前项目 `SKILL.md`不变。
- 声明态：当前项目manifest/profile/prompt/capability/lock决定闭包，CAS存在与否无关。
- 配置态：global runtime marker、generation manifest/content、binding和preview通过。
- 生效态：同一登录跨profile/workdir请求；同一Session显式跨cwd恢复并切换当前overlay；并发generation不变；MCP active empty，Hook/Plugin unknown。

## Risks / Trade-offs

- [全局settings变化影响所有显式CAP项目] → runtime id就是用户状态域；需要隔离时使用新id，不用profile名模拟身份。
- [全局Session可跨项目访问] → 这是明确共享语义；cwd分组仅用于默认查找，receipt准确记录workdir。
- [用户级CAS被误当权威] → 每次先验证当前项目，再核对hash/manifest/content；缓存不能枚举或选择profile，删除后必须可重建。
- [同hash跨项目来源混淆] → hash包含profile/layer/adapter/config/flags摘要；manifest不依赖名称或目录猜测。
- [全局MCP denylist限制未来项目] → 当前默认runtime策略是无active MCP；不同策略使用新runtime id或后续显式MCP change。
- [用户级状态清理风险更高] → 本change cleanup不删除global runtime/CAS，只删除当前项目迁移源；global GC另行设计。
- [迁移后回退] → 清理前保留项目级backup；清理后全局runtime为唯一真源，只做前向修复。

## Migration Plan

1. 修订CLI路径语义，增加runtime id/root和global CAS root；保留当前项目source/lock校验。
2. 扩展generation hash/manifest，覆盖adapter、profile/layer、effective config与fixed gates，并测试cache poisoning和删除重建。
3. 扩展迁移命令，dry-run比较项目级source与global target，apply原子迁移runtime/Session，项目renders重新materialize到global CAS。
4. 更新preview/receipt和中文文档，明确global profile语义不等于用户目录权威。
5. 运行单元测试、Skill标准、CAP verify、portable/global effective preview和OpenSpec strict validation。
6. 从至少两个不同workdir使用同一runtime完成双profile请求；显式以同一Session path跨cwd恢复，准确报告共享而非隔离。
7. 并发启动不同workdir/profile，核对global SQLite和CAS generation不变；真实MCP active empty。
8. 验证后删除当前项目级shared runtime/renders/backup，再重复closure与行为验证；不自动Sync或Archive。
