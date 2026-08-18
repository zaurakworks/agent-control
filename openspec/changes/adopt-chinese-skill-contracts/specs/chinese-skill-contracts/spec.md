## Purpose

规定快速迭代阶段以中文运行时 Skill 作为唯一全文合同，从而减少双语同步成本和语义漂移，同时保持标准机器元数据和 profile 引用稳定。

## ADDED Requirements

### Requirement: 中文 SKILL 文件是唯一全文执行合同
项目 MUST 在 `.cap/capabilities/skills/<id>/SKILL.md` 中使用中文维护 `description` 和行为正文；稳定机器 id、目录名、配置键和命令保持其规范形式。

#### Scenario: 修改 Skill 行为
- **WHEN** 维护者新增或修改 Skill 的触发、流程、输出或完成条件
- **THEN** 只修改对应中文 `SKILL.md` 全文合同，不维护第二份逐字翻译

#### Scenario: 机器标识参与路由
- **WHEN** profile 或客户端按 Skill id 定位能力
- **THEN** `name`、目录 id 和 profile 引用保持小写连字符形式，不翻译为中文

### Requirement: 项目不得维护重复全文镜像
项目 MUST NOT 为运行时 Skill 维护需要逐项同步的另一语言全文副本；目录和说明文档只提供摘要并链接唯一运行时合同。

#### Scenario: 中文阅读者查找 Skill
- **WHEN** 维护者从 Skill 目录进入某项能力
- **THEN** 目录直接链接中文运行时 `SKILL.md`，无需在运行时合同和阅读镜像之间选择

### Requirement: 语言迁移必须单独验证
语言切换 MUST 分别验证标准元数据、项目闭包和目标客户端实际运行；任何一层成功都不能替代另一层。

#### Scenario: 元数据和 lock 均通过
- **WHEN** Skill 元数据验证与 profile lock/verify 成功
- **THEN** 项目只声明标准合规和配置态成功，在运行 smoke 前不声称客户端行为等价

#### Scenario: OMP 路由 smoke 通过
- **WHEN** OMP 真实运行能够看到并按中文合同执行目标 Skill
- **THEN** 只记录 OMP 生效态证据，Codex 和 Qoder 保持 unknown 直到分别观察
