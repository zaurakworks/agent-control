# layered-agent-profile Specification

## Purpose
定义 `real-home -> work -> general | assembly-helper` 的分层能力、外部审批与真实 HOME 运行合同。

## Requirements

### Requirement: 项目 profile 显式继承真实 HOME 基座

公共 profile SHALL 继续使用 version 2 profile 和显式 `add`、`mask`、`replace` 操作。系统 MAY 在已验证公共 profile 之后接入一个显式私有 capability layer，形成 `real-home -> work -> public profile -> private profile` 的有序有效链；`real-home` SHALL 最多出现一次。继承环、未声明 source、多个未排序基座、隐式同名覆盖和不存在的 mask/replace 目标 SHALL 失败。

#### Scenario: 项目层增加 Skill

- **WHEN** 公共或私有 profile 以 `add` 声明对应 source 内存在的 Skill，且所有已继承层不存在同名能力
- **THEN** 最终 effective inventory SHALL 包含该 Skill，并记录其来源层

#### Scenario: Derived profile 继承 work 共享能力

- **WHEN** `work` 以 `add` 声明共享 OpenSpec Skills，且 `general` 的 Skill `add` 为空
- **THEN** `general` 最终 inventory SHALL 包含这些共享 Skills，并 SHALL 保留 `real-home -> work -> general` 公共链

#### Scenario: 私有 profile 继承公共 profile

- **WHEN** 私有 profile 显式指定公共 `general` 为 base，并增加私有 Skill
- **THEN** effective inventory SHALL 按固定顺序包含公共和私有能力
- **THEN** 私有 profile SHALL NOT 改写公共 profile 的声明源或公共 lock

#### Scenario: 同名能力未声明替换

- **WHEN** `add` 名称与已审批基座、公共层或上层能力重名
- **THEN** binding SHALL 失败，并要求显式 `replace` 或调整能力名称

### Requirement: 基座与项目层分别锁定

系统 SHALL 把项目公共 `.cap/lock.json`、私有 overlay lock、私有 real-home manifest、workspace approval pin、derived binding 和 effective evidence 分开存储。每层 lock SHALL 记录 source、profile、能力闭包、输入摘要和 renderer/adapter 版本；effective binding SHALL 同时记录有序层 digest、effective digest 与 evidence index。manifest、lock、binding 和 evidence SHALL 不得保存 token、cookie、secret、session、history 或 cache 正文。

#### Scenario: 项目层变化

- **WHEN** 公共 profile、prompt 或公共能力变化
- **THEN** 公共 lock、依赖该层的私有 lock 与 effective binding SHALL stale
- **THEN** private source、base pin 和其他不受影响的公共 profile SHALL 保持独立

#### Scenario: 私有层变化

- **WHEN** 私有 profile、私有 prompt 或私有能力变化
- **THEN** 私有 lock 与 effective binding SHALL stale
- **THEN** 公共 lock SHALL 不被改写，公共 profile SHALL 能单独验证和运行

#### Scenario: 基座变化

- **WHEN** real-home active digest 与 workspace pin 不一致
- **THEN** batch 启动 SHALL 在创建客户端进程前失败，且 SHALL NOT 自动刷新 pin、任一层 lock 或 binding

### Requirement: 真实 HOME 与客户端状态隔离并存

继承 `real-home` 的客户端进程 SHALL 保留真实 `HOME`，使 Git、SSH、语言工具链和原生父级 context discovery 可用。持久 OMP SHALL 使用当前用户、当前机器、显式 runtime id 对应的 CAP 全局 runtime，共享认证、用户 settings、Session、history、models/cache 与 `agent.db`；memory SHALL 显式保持关闭。CAP profile MAY 跨 workdir 使用，但 profile 的存在、选择、prompt、Skills、MCP、Hook 和 Plugin SHALL 只由当前 Git 项目的 `.cap/manifest.toml`、profile files、capabilities、lock、base pin 和 binding 授权。用户级 runtime 与 render CAS SHALL 只是私有状态/缓存，MUST NOT 成为 profile catalog、source 或 ambient 能力来源。CAP SHALL NOT 复制整份 HOME，或把用户配置正文、认证正文、token 与环境值写入项目 lock、binding、receipt 或诊断输出。

#### Scenario: OMP 从项目 worktree 启动

- **WHEN** 当前 Git 项目显式选择 `general` 或 `assembly-helper`，并从任一受支持 workdir 启动持久 OMP
- **THEN** `HOME` SHALL 等于真实用户 HOME
- **THEN** `PI_CODING_AGENT_DIR` 与 `PI_CONFIG_DIR` SHALL 指向 `$HOME/.cap-user-state/runtimes/omp/<runtime-id>`，不随 profile、workdir、项目副本或 worktree 改变
- **THEN** 当前进程的 system prompt、Skills 和显式能力 SHALL 来自当前 Git 项目验证后的 profile render，不得从用户级 cache 自主选择 profile

#### Scenario: 一次登录后切换 profile

- **WHEN** 用户在全局 runtime id `default` 中完成一次 provider 登录或修改一个 OMP 用户 setting
- **THEN** 当前项目的 `general`、`assembly-helper` 以及其他显式绑定同一 runtime id 的 CAP 项目 SHALL 使用同一登录状态和 setting
- **THEN** 切换 profile、workdir 或 agent-assembly worktree SHALL NOT 要求再次登录

#### Scenario: 共享认证输入无效

- **WHEN** 全局 runtime 缺失、权限不安全、迁移未完成、本地 credential store 无法读取，或 runtime id 未获当前项目策略允许
- **THEN** CAP SHALL 在创建 OMP 进程前失败并给出不含 secret 的可操作错误
- **THEN** CAP SHALL NOT 回落项目级旧 runtime、真实 `~/.omp`、ambient provider凭据、auth broker 或另一 runtime id

#### Scenario: 共享 broker 不可达

- **WHEN** 旧 auth broker 已停止、删除或不可达，但全局本地 runtime 已成功迁移
- **THEN** OMP SHALL 继续使用全局本地 credential store，不得连接、探测或要求恢复旧 broker

#### Scenario: 当前 Git 项目是 profile 唯一权威

- **WHEN** 用户级 render CAS 中存在某个 profile 名称或 generation，但当前 Git 项目的 manifest 未声明该 profile，或当前 lock/binding 无法验证其输入
- **THEN** CAP SHALL 拒绝启动该 cache entry，不得从 `$HOME/.cap-user-state`、其他 Git 项目、模板或 provider ambient配置补齐声明
- **THEN** 删除整个 render CAS 后，当前项目 SHALL 能仅凭自身 `.cap` 声明、lock 与已审批 base binding 重建相同 effective generation

#### Scenario: 全局 CAS 复用

- **WHEN** 两个显式 CAP 启动从各自当前项目计算出相同的 portable tree、adapter version、profile/layer digest、effective config template 和固定门禁
- **THEN** 它们 MAY 复用同一个 `$HOME/.cap-user-state/renders/omp/<effective-hash>` generation
- **THEN** 每次复用 SHALL 核对 generation manifest 与内容摘要；缺失、篡改、来源摘要不匹配或同 hash 内容冲突 SHALL 失败，不得重写正在使用的 generation

#### Scenario: Session 跨 profile 和 workdir 恢复

- **WHEN** 用户以一个当前项目 profile 创建 Session，再通过显式 Session id/path 从另一 profile、worktree 或 workdir 恢复
- **THEN** OMP SHALL 保留同一 transcript 和 Session identity，并重新应用恢复进程的当前项目/profile prompt、Skill allowlist 和显式能力
- **THEN** 默认 Session 目录 MAY 按 encoded cwd 组织和筛选，但该分组 SHALL NOT 被报告为授权或隔离边界

#### Scenario: 并发 profile 与 workdir 启动

- **WHEN** 多个当前项目/profile/workdir 并发使用同一全局 runtime 与不同 effective generations
- **THEN** OMP SHALL 使用原生共享 SQLite 并发模型，每个进程 SHALL 只读其已验证 generation
- **THEN** 任一启动 SHALL NOT 删除、替换或重写另一进程的 generation，也不得把 profile 能力文件写入全局 runtime

#### Scenario: Skills 只来自当前项目 profile

- **WHEN** OMP 启动当前项目显式声明的 CAP profile
- **THEN** Skill 文件 SHALL 来自该项目验证后 generation 的 custom directory，并受 config include list 与 CLI allowlist 约束
- **THEN** Codex、Claude、Pi 与 Agents 的 user/project Skill 自动来源 SHALL 被关闭，ambient 同名 Skill SHALL NOT 替换当前项目 Skill
- **THEN** `--no-extensions` 与 `--no-rules` SHALL 保持启用，但当前项目 generation 中明确传入的 extension root SHALL 仍可加载

#### Scenario: 当前 profile 不声明 MCP、Hook 或 Plugin

- **WHEN** 当前项目所选 profile 的声明 inventory 中 MCP、Hook 与 Plugin 均为空
- **THEN** project MCP 自动发现 SHALL 被关闭，全局 runtime policy SHALL 阻断已观察到的 ambient MCP connection/tool
- **THEN** 真实 `/mcp reload` SHALL 没有 connected ambient server/tool；被 denylist 的 source MAY 作为 disabled 配置显示。Hook/Plugin 无法可靠观察时 SHALL 报告 unknown

#### Scenario: Memory 保持关闭

- **WHEN** 任一当前项目/profile 从全局 runtime 启动
- **THEN** 全局用户 setting 与 effective overlay 的 `memory.backend` SHALL 均为 `off`
- **THEN** OMP SHALL NOT 从共享 `agent.db` 或 memory 文件向当前上下文注入记忆

#### Scenario: 迁移已有 profile runtime

- **WHEN** 当前项目级 shared runtime 已存在而全局 runtime id 目标不存在或已有状态
- **THEN** 迁移 SHALL 在不输出 secret 的前提下比较 schema、settings、credential identity 和 Session 摘要；目标不存在时原子安装，目标等价时合并 Session，实质冲突时在覆盖/删除前失败
- **THEN** profile renders SHALL NOT 作为 runtime 状态迁移；它们必须由当前项目重新计算后写入全局 CAS

#### Scenario: 清理 CAP 管理的旧状态

- **WHEN** 全局 runtime/CAS、跨 profile/workdir resume、并发启动、closure 和无 secret 验证全部通过
- **THEN** CAP MAY 按用户授权删除当前项目管理的项目级 shared runtime、project render cache 和 migration backup
- **THEN** 清理 SHALL NOT 删除当前 Git 项目的 `.cap` 声明、真实 `~/.omp`、其他客户端配置或其他 runtime id

#### Scenario: 声明态与配置态闭包

- **WHEN** 全局 runtime 与 CAS 被实现但当前项目 profile、prompt、Skill、MCP、Hook 和 Plugin 声明未改变
- **THEN** 当前项目的能力 inventory 和 `.cap/lock.json` SHALL 保持不变
- **THEN** effective preview SHALL 显示 runtime id/global root、当前项目 source/layer digest、CAS generation、固定门禁和 effective hash，且 SHALL NOT 把 cache存在报告为声明态成功

#### Scenario: Skill 标准合规证据

- **WHEN** 本变更未修改任何当前项目 `SKILL.md`
- **THEN** Skill 元数据验证结果 SHALL 保持不变，且该结果 SHALL NOT 被报告为全局 runtime/CAS 或跨 workdir resume 已生效的证据

#### Scenario: 共享认证生效态证据

- **WHEN** 只完成单元测试、迁移 dry-run、lock、render 或 `cap verify`，但未执行真实跨 profile/workdir请求和同一 Session恢复
- **THEN** 结果 SHALL 只报告声明态或配置态，不得声称登录、settings、Session、当前 overlay 或 CAS复用已实际生效

#### Scenario: 运行收据

- **WHEN** OMP 运行完成且 post-run binding 校验通过
- **THEN** receipt SHALL 包含 `runtime_id`、全局 runtime root、当前项目/profile/layer digest、portable/effective render hash、workdir 和退出状态
- **THEN** receipt SHALL NOT 包含参数值、认证路径、环境值、用户配置正文或 secret

### Requirement: 基座漂移采用分级门禁

系统 SHALL 把影响能力集合或执行行为的变化判为 active drift，把不影响能力面的设置变化判为 passive drift。batch 遇到 active drift SHALL 失败；交互启动 MAY 在展示变化路径并收到明确 `continue` 后继续，但 SHALL NOT 修改审批状态。passive drift SHALL 告警但 MAY 继续。

#### Scenario: secret-only 值轮换

- **WHEN** 已知 secret 字段只改变值而能力结构不变
- **THEN** real-home effective digest SHALL 保持不变，且 manifest SHALL 不含旧值或新值

### Requirement: Skills 只来自当前验证后的有效 profile 闭包

WHEN OMP 启动一个显式 CAP profile，Skill 文件 SHALL 来自该 profile 所引用的公共 source 和经 private binding 验证的私有 source 生成的 effective generation，并受 config include list 与 CLI allowlist 约束。Codex、Claude、Pi 与 Agents 的 user/project Skill 自动来源 SHALL 被关闭；ambient 同名 Skill、用户级 cache 和未绑定私有 source SHALL NOT 替换 effective generation。

#### Scenario: 公共和私有 Skill 进入 effective generation

- **WHEN** 当前 profile 显式引用公共 `general` 和私有 `company-order-skill`，且两层 lock、binding、evidence 均通过
- **THEN** effective generation SHALL 包含两者的物化文件
- **THEN** 客户端 SHALL 只从该 generation 加载 Skills

#### Scenario: 未声明私有 Skill 不得注入

- **WHEN** 私有 source 中存在未被当前 profile 引用的 Skill，或只存在于用户级 Skill 目录
- **THEN** 当前 effective generation SHALL NOT 包含该 Skill
- **THEN** 客户端 SHALL NOT 通过 ambient discovery、cache 或同名替换加载它

#### Scenario: 私有证据失败

- **WHEN** 私有 source、lock、binding 或 evidence index 不能通过一致性校验
- **THEN** CAP SHALL 拒绝创建客户端进程
- **THEN** CAP SHALL NOT 使用上一次 effective generation 作为静默回退
