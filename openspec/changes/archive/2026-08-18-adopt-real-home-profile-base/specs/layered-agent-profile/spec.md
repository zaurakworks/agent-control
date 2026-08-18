## ADDED Requirements

### Requirement: 项目 profile 显式继承真实 HOME 基座

`work`、`general` 与 `assembly-helper` SHALL 使用 version 2 profile。`work` SHALL `extends = "real-home"`；两个可运行 profile SHALL 分别 `extends = "work"`，形成单一 `real-home -> work -> derived` 链。项目层能力 SHALL 只通过每类能力的 `add`、`mask`、`replace` 操作表达；继承环、多个基座、隐式同名覆盖和不存在的 mask/replace 目标 SHALL 失败。

#### Scenario: 项目层增加 Skill

- **WHEN** profile 以 `add` 声明项目内 Skill，且基座和上层不存在同名能力
- **THEN** 最终项目层 inventory SHALL 包含该 Skill

#### Scenario: Derived profile 继承 work 共享能力

- **WHEN** `work` 以 `add` 声明共享 OpenSpec Skills，且 `general` 的 Skill `add` 为空
- **THEN** `general` 最终 inventory SHALL 包含这些共享 Skills，并 SHALL 保留 `real-home -> work -> general` 链

#### Scenario: 同名能力未声明替换

- **WHEN** `add` 名称与已审批基座或上层能力重名
- **THEN** binding SHALL 失败，并要求显式 `replace` 或调整能力名称

### Requirement: 基座与项目层分别锁定

系统 SHALL 把项目 `.cap/lock.json`、私有 real-home manifest、workspace approval pin 和 derived binding 分开存储。manifest SHALL 只含候选路径、能力 id、状态和摘要，不得保存 token、cookie、secret、session、history 或 cache 正文。binding SHALL 同时记录 base digest、layer digest 与 effective digest。

#### Scenario: 项目层变化

- **WHEN** profile、prompt 或项目能力变化
- **THEN** 项目 lock 与 derived binding SHALL stale，但 base pin SHALL 保持不变

#### Scenario: 基座变化

- **WHEN** real-home active digest 与 workspace pin 不一致
- **THEN** batch 启动 SHALL 在创建客户端进程前失败，且 SHALL NOT 自动刷新 pin 或 binding

### Requirement: 真实 HOME 与客户端状态隔离并存

继承 `real-home` 的客户端进程 SHALL 保留真实 `HOME`，使 Git、SSH、语言工具链和原生父级 context discovery 可用；客户端配置和 Session 状态 SHALL 写入 profile 专属隔离根。CAP SHALL NOT 复制整份 HOME 或把用户配置正文写入项目 lock、binding 或 receipt。

#### Scenario: OMP 从项目 worktree 启动

- **WHEN** `general` 或 `assembly-helper` 从当前 Git worktree 启动 OMP
- **THEN** `HOME` SHALL 等于真实用户 HOME，`PI_CODING_AGENT_DIR` 与 `PI_CONFIG_DIR` SHALL 指向 profile 专属 agent home

#### Scenario: 运行收据

- **WHEN** OMP 运行完成且 post-run binding 校验通过
- **THEN** receipt SHALL 包含 base、layer、effective 和 render tree digest，且 SHALL NOT 包含参数值、环境值或 secret

### Requirement: 基座漂移采用分级门禁

系统 SHALL 把影响能力集合或执行行为的变化判为 active drift，把不影响能力面的设置变化判为 passive drift。batch 遇到 active drift SHALL 失败；交互启动 MAY 在展示变化路径并收到明确 `continue` 后继续，但 SHALL NOT 修改审批状态。passive drift SHALL 告警但 MAY 继续。

#### Scenario: secret-only 值轮换

- **WHEN** 已知 secret 字段只改变值而能力结构不变
- **THEN** real-home effective digest SHALL 保持不变，且 manifest SHALL 不含旧值或新值
