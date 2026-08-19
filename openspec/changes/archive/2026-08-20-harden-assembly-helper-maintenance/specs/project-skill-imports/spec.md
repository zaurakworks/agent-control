## Purpose

定义 CAP v3 如何显式复用同一项目中的唯一 Skill 正文，同时保持路径安全、默认拒绝、lock 漂移检测和客户端 render 自足。

## ADDED Requirements

### Requirement: 项目 Skill import 必须显式声明唯一来源

manifest MAY 指向项目内 Skill import 声明；每项 import MUST 包含 Skill id 与项目根相对 source，source MUST 是非 symlink 目录并包含同名 `SKILL.md`。

#### Scenario: agent-assembler 导入 Plugin Skill
- **WHEN** `.cap/skill-imports.toml` 声明 `grilling` 来自 `plugins/grilling/skills/grilling`
- **THEN** `agent-assembler` 可以在 role 中 allow `grilling`
- **AND** render 使用 Plugin 中的唯一正文，不在 `.cap` 复制文件

#### Scenario: import 逃逸项目或经过 symlink
- **WHEN** source 包含绝对路径、`..`、非规范分量或任一 symlink
- **THEN** 项目加载失败关闭
- **AND** 不读取项目外文件

### Requirement: import 必须参与闭包和冲突验证

每个 import MUST 被至少一个有效 role引用；import id 与 `.cap` 本地 Skill 同名，或声明重复 id，MUST 失败关闭。

#### Scenario: 声明未使用 import
- **WHEN** import 存在但没有 role 的有效闭包引用它
- **THEN** verify 报告未引用来源并失败

#### Scenario: 本地和 imported Skill 同名
- **WHEN** `.cap/capabilities/skills/grilling` 与项目 import 同时存在
- **THEN** loader 报告来源冲突
- **AND** 不按路径顺序静默选择实现

### Requirement: import 源必须被 lock 和标准验证覆盖

Skill import 声明、目录和全部文件 MUST 进入 lock inputs；`skills-validate` MUST 对 imported `SKILL.md` 使用与本地 Skill 相同的标准元数据检查。

#### Scenario: import 正文在 lock 后变化
- **WHEN** imported `SKILL.md` 内容改变
- **THEN** show、verify 或 run 检测 lock drift并停止

#### Scenario: imported Skill 元数据无效
- **WHEN** imported `SKILL.md` 缨少 name／description、id 与目录不一致或字段不是允许的简单字符串
- **THEN** 标准验证按本地 Skill 的相同规则失败
- **AND** 不把配置态报告为通过

### Requirement: project-defaults 与 import 必须真实进入 render

有效 profile inventory 中的每个 Skill MUST 从其已验证最终源路径 staged 到客户端 render；不得只列名而漏文件。

#### Scenario: Skill 来自 project-defaults
- **WHEN** role 继承 project-defaults 中的本地 Skill
- **THEN** render 包含该 Skill 的 `SKILL.md`

#### Scenario: Skill 来自项目 import
- **WHEN** role allow 已声明 imported Skill
- **THEN** render 包含 import 源树
- **AND** tree hash随源内容变化
