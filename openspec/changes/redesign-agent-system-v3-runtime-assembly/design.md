## Context

现状和动机见 `proposal.md`。当前 `.cap` profile 使用 `extends` 与 `add`/`mask`/`replace`，机器基座、项目共享 Skill 和角色 profile 形成 `real-home -> work -> role` 链。OMP 已有用户级 runtime 迁移和临时隔离 render，但 OMP render 当前生成空 `config.yml`，用户级 native settings 不是受控 CAP runtime policy 的输入。当前仓库支持并验证 OMP、Codex、Qoder adapter；本变更只实现 OMP，Codex 和 Claude 只消费本设计规定的未来合同。

约束：`.cap` 是项目能力声明唯一权威；用户级目录不能作为业务能力 discovery 或隐式继承来源；machine-context 可保留宿主运行底座但不能授权 Agent-facing asset；所有结论必须区分声明态、配置态和生效态；禁止写入 secret。

## Goals / Non-Goals

**Goals:**

- 建立 `machine-context`、`asset-inventory`、`project-defaults`、`role profile` 和 `runtime policy` 五个可区分的输入面。
- 用默认拒绝、显式 `allow`/`deny`/`override` 和 external import provenance 替代旧的混合继承语义。
- 将用户级状态根和 runtime 路径改为 v3 命名，并提供显式、可回滚的一次性迁移。
- 让 OMP 的全局 runtime-id、项目 policy、role override、临时 render、generation、receipt 和 probe 形成闭环。
- 给 Codex、Claude 后续 adapter 留下稳定的语义 policy 和 native projection 边界。
- 使 Claude 后续实施者可以只依据变更包实现 adapter，不依赖本次会话上下文。

**Non-Goals:**

- 本变更不实现 Codex 或 Claude adapter 的 runtime policy projection。
- 本变更不在没有真实 Claude CLI 的环境中验证 Claude 生效态。
- 不把任意用户 native config、provider config、认证、Git/SSH 或语言工具链复制成 Agent-facing capability。
- 不长期兼容 v2 的 `real-home`、`work`、`agent-home-root`、`base-*` 或 `add`/`mask`/`replace` 运行语义。
- 不引入未被真实需求证明的多 defaults bundle 或跨客户端 native passthrough。

## Decisions

### 1. 采用显式组合，不保留混合继承链

v3 的有效装配由以下输入合成：

```text
machine-context
+ project-defaults
+ role profile
+ runtime policy
+ explicitly approved external imports
```

`machine-context` 和 `asset-inventory` 不是 role profile；用户命令只展示和选择叶子 role。保留一个独立的 `project-defaults` 文件，避免让共享能力再次伪装成 profile。

备选是继续 `extends`，但它无法表达“宿主上下文”“观察候选”“项目能力”和“角色增量”的正交关系；不采用。

### 2. machine-context 与 asset-inventory 分开

`machine-context` 只保存经批准的宿主底座摘要、pin 和 drift 输入；`asset-inventory` 只保存发现的 Agent-facing 候选摘要。两者都使用无 secret manifest，但只有 machine-context 参与宿主运行绑定，inventory 不参与授权。

Agent-facing asset 分成两个子平面：

```text
capability plane：Skill / MCP / Hook / Plugin
instruction plane：Prompt / Rule / Agent / Marketplace / client settings
```

未声明候选不进入任一有效平面。active 且无法证明隔离的候选导致 blocked；passive 或不影响能力面的观察不足保留 warning/unknown。

### 3. 用 allow/deny/override 替代 add/mask/replace

v2 `mask` 依赖“先继承再遮蔽”，与 v3 默认拒绝冲突。v3 语义为：

- `allow`：把项目能力或经审批的 external import 放进闭包；
- `deny`：明确拒绝已知候选或上层公共能力，并作为审阅记录；
- `override`：用项目已声明来源替换已批准同名实现。

系统安全固定门禁不可被 role 或 runtime policy 覆盖。旧操作名称只由迁移器识别并映射，不作为长期运行 API。

### 4. external import 单独保留 provenance

普通项目能力和外部导入不共用无来源的名称列表。external import 至少保存来源标识、digest、审批状态和适用 role；不保存 endpoint secret、token 或配置正文。机器拥有权不等于项目使用权，项目批准也不等于所有 role 自动批准。

### 5. runtime policy 使用 client/runtime-id 隔离

用户级状态根迁移为：

```text
$HOME/.agent-system-state/
```

持久 runtime 迁移为：

```text
runtimes/<client>/<runtime-id>/
```

当前实现只创建和验证 `runtimes/omp/default/`。Codex 未来使用独立 namespace；Claude 只有在真实 CLI 和 adapter 存在后创建。

runtime policy 不属于 Agent capability。它由受控的语义 preference 组成，再由 client adapter 投影到 native config。OMP native `config.yml`、Codex native config 等只能是隔离 render 的输出或客户端状态，不能成为跨客户端的 CAP source schema。

### 6. runtime policy 合成优先级固定

最终策略按以下顺序处理：

```text
system fixed safety gates
    > project runtime policy
    > role override
    > user global preference
```

全局 preference 按 client/runtime-id 隔离；项目 lock 锁项目 policy；assembly-binding 和 receipt 记录全局 preference digest 与最终 effective settings。这样个人偏好不进入 Git，但实际运行仍可解释和复现。

### 7. OMP 先实现，其他客户端只实现合同

OMP 端到端实现包括：

```text
v3 source model
-> machine-context/inventory verification
-> project/role/policy lock
-> OMP policy projection
-> isolated config.yml/mcp.json/system prompt
-> OMP launch/run
-> generation/render hash/receipt/probe
```

Codex 和 Claude 的后续实现必须消费同一套语义 policy，且自行生成 native projection；不得读取 OMP native files。Claude 当前没有生效态证据，不在本变更中声称支持。

### 8. 路径迁移与原生文件名分层

CAP 自己的路径和命名一次性迁移：`.agent-system-state`、`machine-context`、`asset-inventory`、`project-defaults`、`runtime-policy`、`machine-context-pin`、`assembly-binding`。客户端原生文件名只在隔离 render 中保留，例如 OMP `config.yml` 和 `mcp.json`。

迁移采用 `dry-run -> apply -> verify -> quarantine`，不在普通启动中隐式迁移。旧状态在成功后只作为隔离备份和报告来源，不再被 v3 runtime 读取。

### 9. lock、binding、render 和 receipt 的输入边界

- project lock：项目 manifest、defaults、role、prompt、项目能力、runtime policy source 和 adapter version；
- machine-context pin：批准的宿主上下文 digest；
- assembly-binding：项目、role、client、runtime-id 与 machine-context 的关联；
- render generation/hash：能力闭包、effective runtime policy、adapter version 和固定门禁；
- receipt：本次实际运行的 source/profile/policy/runtime/generation/effective settings 和观察结果。

所有记录都使用摘要；不写入 secret、Session 正文或 history。

### 10. OMP runtime 与项目 render 的关系

持久 OMP runtime 保存 settings、Session、history、cache 和 agent.db 等用户状态；每次项目启动仍创建独立 ephemeral render。全局 runtime 不得绕过项目 lock、machine-context pin、assembly-binding 或能力闭包；项目 render 不得反向修改持久 runtime 的认证和历史来源。

## Risks / Trade-offs

- **命名和路径一次性迁移风险**：旧调用、文档、测试和私有状态可能遗漏。迁移器必须先 dry-run，且严格校验后才 quarantine；不做普通启动自动兼容。
- **OMP native 配置差异**：当前仓库没有统一的 advisor 或压缩字段合同。先定义受控语义字段和 OMP adapter allowlist；未知字段保持未接入，不把 guessed key 写入实现。
- **全局 preference 影响可重复性**：项目 policy 必须能够覆盖用户默认，receipt 必须记录 global digest 和 effective settings；项目 lock 不保存个人 preference 正文。
- **客户端观察不完整**：OMP 的 MCP/context/Hook/Plugin 观察可能是 `unknown` 或 `reported_client_limited`。配置态通过不能升级为生效态通过。
- **未来 adapter 漂移**：Codex/Claude 不能共享 OMP native config。每个 adapter 必须声明版本、支持字段、投影结果和真实 probe 上限。
- **配置与能力边界混淆**：runtime policy 不能授予工具；所有工具仍须通过 project-defaults、role 和 external import 显式闭包授权。

## Migration Plan

1. 为 v3 source schema、state paths、runtime policy 和 OMP adapter 建立类型和验证边界。
2. 实现只读 inventory 与 machine-context 拆分，并生成无 secret 摘要。
3. 将旧 profile inheritance 转换为 project-defaults + role，生成 allow/deny/override 审阅报告。
4. 将旧状态根、pin、binding 和 OMP runtime 迁移到 `.agent-system-state`，支持 dry-run/apply/verify/quarantine。
5. 先实现 OMP runtime policy、隔离 render、generation、receipt 和 probe。
6. 验证 OMP 正向、越权、unknown/block、drift、迁移冲突和跨项目 runtime-id 场景。
7. 将 Codex/Claude adapter contract、非目标和 evidence ceiling 交给后续实现者；不在本变更中生成未验证 adapter。

## Rollback Strategy

任何迁移或 OMP runtime policy apply 在冲突、权限、secret 或 digest 不一致时停止并保持旧状态不变。v3 验证后旧状态进入 quarantine backup；显式 rollback 可从备份恢复，但恢复后的旧状态不能成为 v3 的隐式 discovery 或能力来源。