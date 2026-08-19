# digest-materialization-evidence Specification

## Purpose
为每个 source、profile 闭包和最终 render digest 提供可回读的物化证据，使摘要变化能够定位到具体来源、路径、内容和层合并结果，同时不把 secret 写入证据。

## Requirements

### Requirement: 每个 digest 必须可定位到物化证据

系统 SHALL 为 public source、private source、resolved inventory、layer merge result 和 effective render 分别生成稳定的 evidence index。每个 index SHALL 记录对象类型、层顺序、相邻父摘要、相对路径、文件 mode、字节数和内容摘要，并指向本地受控物化目录或归档。

#### Scenario: digest 与物化内容一致

- **WHEN** 系统生成一个 source 或 render digest
- **THEN** 对应 evidence index SHALL 能定位所有参与摘要的非 secret 文件和目录
- **THEN** 重新读取物化内容并按记录的规范化规则计算 SHALL 得到相同 digest

#### Scenario: digest 发生变化

- **WHEN** 前后两次 digest 不同
- **THEN** 系统 SHALL 提供按层、profile、能力名和相对路径排序的差异结果
- **THEN** 差异结果 SHALL 指出新增、删除、替换、mode 变化或内容变化的具体证据

### Requirement: 物化证据必须不含 secret

物化 evidence SHALL 遵守与 manifest、binding、receipt 相同的 secret 边界。Secret、token、cookie、认证正文、session、history 和 cache SHALL NOT 被写入 evidence index、物化文件、差异输出或失败诊断；被排除的输入 SHALL 以稳定的非敏感占位信息记录其排除原因。

#### Scenario: 普通能力文件物化

- **WHEN** Skill、prompt、profile 声明或渲染配置不含 secret
- **THEN** 系统 SHALL 物化其可读正文并记录 mode、size 和 digest
- **THEN** 用户 SHALL 能从 digest 反查到该文件的来源层和相对路径

#### Scenario: 敏感输入参与运行但不出证据

- **WHEN** 某输入包含 secret 或属于认证、session、cache 状态
- **THEN** 系统 SHALL 从物化正文和差异输出中排除该输入
- **THEN** 系统 SHALL 保留不泄露值的 exclusion marker 和影响摘要的规则结果

### Requirement: 证据必须与 effective digest 一起校验

系统复用或启动一个已有 effective render 前 SHALL 校验证据 index、物化内容、source/layer digest、client adapter 和 effective digest 的一致性。证据缺失、篡改、来源不匹配或同一摘要指向不同内容时 SHALL 失败关闭，不得使用旧缓存。

#### Scenario: 缓存命中且证据完整

- **WHEN** effective render 的 manifest、evidence index 和物化树均与当前输入匹配
- **THEN** 系统 MAY 复用该 render
- **THEN** preview SHALL 显示可读 evidence 路径和对应 effective digest

#### Scenario: 证据被删除或篡改

- **WHEN** render 仍存在但 evidence index、物化文件或来源摘要缺失或不一致
- **THEN** 系统 SHALL 拒绝复用该 render
- **THEN** 系统 SHALL 报告缺失或不一致的证据对象，并允许从当前声明源重建
