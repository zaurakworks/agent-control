## Context

见 `proposal.md` 的 Why。CAP 已把所有 profile 指向同一个受管理的 OMP runtime id，但当前 runtime policy 只投影 memory 与 project MCP 门禁；`_agent_home_env()` 会清空 ambient credential 和 broker 环境，普通 OMP 的模型、advisor、显示、provider 与认证配置因此不会成为 CAP 生效配置。当前 OMP session 的默认目录按 runtime root 与 cwd 组织，不以 CAP profile 名隔离；跨 profile `/resume` 的可观察语义、来源标签和单写者状态尚未成为合同。

约束：`.cap` 仍是 prompt 与 Agent-facing capability 的唯一声明来源；共享 preference 绝不能成为发现或启用 MCP、Skill、Hook、Plugin、extension、tool approval 或 project capability 的渠道。所有持久状态仍按 OMP runtime id 归属，而非按 profile 归属。

## Goals / Non-Goals

**Goals:**

- 把普通 OMP 的用户偏好、provider 配置和认证来源以明确、可审计、无 secret 落盘的方式提供给 CAP OMP。
- 保留同一 CAP runtime id 下 profile 间的 session、history、models/cache 和 OMP 数据库共享，并将跨 profile `/resume` 固化为当前 profile 续接语义。
- 让 preference source 或 profile 变化可使 generation 正确失效，并分别证明声明态、配置态与实际 OMP 行为。

**Non-Goals:**

- 将 CAP profile 配置根或 capability runtime 目录与普通 OMP 配置根合并。
- 支持多进程并发写入同一 session，或恢复旧 profile 的运行中任务。
- 用 OMP native 配置替代 `.cap` 的 prompt、Skill 或能力声明。

## Decisions

### D1：采用显式、单向的共享 preference projection

普通 OMP 的用户 preference root 是共享偏好与非 secret provider 配置的唯一来源；CAP 不读取任意 ambient 配置，也不以目录扫描发现来源。CAP 读取该 root 后使用类型化 allowlist 生成当前 profile 的 effective OMP config，合成顺序保持：

```text
固定安全门禁 > 项目 runtime policy > role override > 共享用户 preference
```

初始 allowlist 覆盖用户已确认的模型角色、`extendedContext`、thinking/tier、advisor、theme、statusLine、composer、显示字段与已验证的 provider endpoint。未知字段、能力字段和路径字段忽略并产生可诊断的 source-state 摘要，不进入 native config。allowlist 由 CAP 源码维护；每个 OMP native key 必须有 schema 验证和正反行为测试。

备选方案是让 CAP 与普通 OMP 共用整个 runtime root。拒绝：该方案会把 CAP 的 prompt、render、能力闭包、运行状态和普通 OMP 的扩展配置混为同一写入面，无法保持固定门禁。

### D2：认证共享使用单一私有 source adapter，绝不复制 credential

认证与 provider endpoint 分开处理。endpoint 只能来自 D1 的 allowlist；API key、OAuth token、cookie 和 broker token 由一个被批准的私有 auth source adapter 在启动时解析，并只注入 CAP 启动的 OMP 子进程。该 adapter 必须支持普通 OMP 已使用的本地认证来源；无法安全识别、权限不足或 endpoint 未批准时 fail closed，不借用 ambient environment。

CAP generation、lock、binding 与 receipt 只记录 adapter identity、source digest、允许 provider id 和是否成功解析，不能包含 credential 值、完整 endpoint secret 或配置正文。为避免 provider 数据外流，endpoint source 变化必须参与 generation hash；CAP 的当前安全门禁仍可拒绝该 provider。

备选方案是把 credential 写入 generation `config.yml` 或恢复 ambient environment。拒绝：两者都会把 secret 扩散到 CAS、日志、子进程继承链或不受控工具调用。

### D3：以现有 runtime-id 保留 profile 间共享 state，不引入 profile session 目录

同一 CAP OMP runtime id 继续是 session、history、`agent.db`、models/cache 与 OMP 自有状态的唯一 root。profile 仅决定当前 generation 与启动 overlay；它不是 session namespace。CAP 不传 profile 专属 `--session-dir`，使 OMP 默认 session 路径继续只按 runtime root 与 cwd 解析，确保同一工作目录的任意 profile `/resume` 可发现相同 session。

选择 session 时只启动一个当前 profile 的 OMP 进程：保留 JSONL transcript 与 session identity，重建当前 profile generation、system prompt、模型、advisor、工具与能力闭包。session header/事件保存创建 profile 和最近恢复 profile 的 digest 级标签；它们仅供 picker 显示与诊断，不能反向恢复旧能力。

备选方案是将 session 文件复制到每个 profile root 或为跨 profile resume 建独立 session daemon。拒绝：复制会分叉 transcript；daemon 超出当前 OMP 原生 session 支持，增加锁与故障恢复面。

### D4：跨 profile resume 默认是当前 profile 续接

用户先选择 profile、再在 `/resume` 选择 session，这一选择本身表示采用当前 profile；不增加迁移向导。CAP/OMP 必须在恢复前确认 session 未被另一个活动实例占用。当前 profile 有更小 context window 时，使用当前 OMP 压缩规则；不得因旧 transcript 自动开启 long-context premium tier。

当前 profile 的安全门禁、新的 model/advisor 和 capability closure 总是优先。旧 session 中的历史说明不被重写，但运行时只消费当前启动附加的 prompt 与工具表。若 session 有未完成的 tool call、subagent 或 worktree，恢复将其视为历史记录，不继续绑定旧运行态。

### D5：generation 与诊断只保存可复核摘要

共享 preference 的 redacted canonical digest、allowlist version、auth adapter identity、provider selection、session root identity 与当前 profile resume 标签进入 effective generation hash 或 receipt 的相应无 secret 字段。偏好变动使下一次 launch 重建 generation；session 内容和 credential source 原文永不进入 hash 记录。

## Risks / Trade-offs

- provider endpoint 是数据出站边界；allowlist 与 fail-closed adapter 会增加首次配置成本，但避免把代码和 prompt 发送到未批准端点。
- 当前 profile resume 可能使旧 transcript 中的先前指令与新 profile 指令同时可见；当前 profile prompt 作为后续运行规则，来源标签帮助诊断，而不是尝试修改历史。
- OMP 原生 session 状态的活动占用可观察能力有限；实现必须在能可靠判定时拒绝双写，不能把不可判定误报为安全。
- session/history/cache 已经按 runtime id 共享；本变更必须验证该事实，不应为达到同一目标新增不兼容存储布局。

## Migration Plan

1. 只读盘点现有普通 OMP preference、CAP runtime preference、认证 source 和 session root，输出 redacted 差异与冲突；不自动复制 secret 或 session。
2. 写入显式 shared preference/auth binding，建立 allowlist 投影和 generation digest；先验证生成的 native config 与固定门禁。
3. 保留现有 CAP runtime-id 与 session 根，增加 profile 来源标签和跨 profile picker/恢复验证；活动 session 或无法判定占用时停止。
4. 将当前用户确认的 terra/luna、272K、advisor 和显示配置导入共享 source，验证普通 OMP 与两个 CAP profile 的配置态及实际 session resume。
5. 回滚只移除 binding/projection 并恢复上一个 CAP runtime generation；保留普通 OMP 配置、CAP session JSONL、认证 source 和缓存。