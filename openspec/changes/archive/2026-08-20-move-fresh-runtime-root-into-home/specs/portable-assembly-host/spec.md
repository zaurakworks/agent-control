## ADDED Requirements

### Requirement: 一次性 runtime 根必须落在两端都能表达的位置

CAP 为 `--fresh` 建立的一次性 runtime 根 SHALL 位于两个受支持宿主都能把它表达成客户端所要求形式的位置。当某客户端要求某个配置目录以「相对用户 home 的名字」给出时，一次性根 SHALL 位于该 home 之下，使同一份实现在两端都成立。

位置的选择 MUST NOT 依赖平台分支；系统 MUST NOT 为其中一端单独选择一个另一端不成立的位置。

#### Scenario: 客户端要求 home 相对的配置目录名

- **WHEN** 客户端把某个配置目录环境变量定义为相对 home 的名字，并在内部与 home 拼接
- **THEN** CAP 传入的取值 SHALL 是该一次性根相对 home 的名字
- **AND** 拼接结果 SHALL 指向该一次性根本身，而不是一个被拼了两次的路径

#### Scenario: 两端的系统临时目录都不在 home 之下

- **WHEN** 某宿主的系统临时目录不在用户 home 之下
- **THEN** 一次性根 SHALL NOT 使用该系统临时目录
- **AND** 系统 MUST NOT 通过为该宿主单独增加平台分支来绕过该约束

#### Scenario: 一次性运行结束或中止

- **WHEN** 一次性运行正常结束，或在中途因失败中止
- **THEN** 该一次性根 SHALL NOT 留下任何内容
- **AND** 残留检查 SHALL 覆盖新位置，而不仅覆盖旧的系统临时目录
