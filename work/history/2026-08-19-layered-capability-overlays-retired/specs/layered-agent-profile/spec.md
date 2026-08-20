## MODIFIED Requirements

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

## ADDED Requirements

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
