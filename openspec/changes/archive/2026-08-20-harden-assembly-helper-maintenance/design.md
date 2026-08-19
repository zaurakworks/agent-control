## Context

CAP v3 已把 machine-context、asset-inventory、project-defaults、叶子 role 和 runtime policy 分开。本次只重新装配原 `assembly-helper`：clean cutover 为 `agent-assembler`，从目标重新选择能力，并增加让唯一 `grilling` 正文进入 render 所需的最窄 project Skill source-path。

现有 `harden-assembly-helper-maintenance` change 尚未归档。本次更新同一变更包，因为意图仍是装配角色的行为与维护合同；不并列创建第二个 helper change。

## Goals / Non-Goals

**Goals：**

- 让 `agent-assembler` 交付完整 Agent 合同、项目内源声明、派生状态和相称证据。
- 角色 id、prompt、总 Skill 和 CLI 入口一致使用执行者命名。
- `grilling` 常驻可发现，但严格保留明示同意门。
- Plugin Skill 只有一份正文，CAP render 能直接 staged 该项目源。
- project-defaults 与 role Skills 都从正确的最终源路径进入 render。

**Non-Goals：**

- 不改变 v3 的默认拒绝、machine-context 审批、external import 或 runtime policy 优先级。
- 不增加通用文件挂载、动态 role 发现或旧 id 兼容。
- 不自动批准 machine-context，不管理认证，不读取 secret。
- 不证明 OMP 之外客户端的实际生效。

## Decisions

### 1. clean cutover 到 agent-assembler

manifest 只声明 `general` 与 `agent-assembler`。原 profile、prompt 和总 Skill 文件／目录改名，所有代码常量、CLI 标签、命令示例、测试和文档同步迁移。旧 `assembly-helper` 不保留 alias、redirect 或 fallback。

`RUNNABLE_PROFILES` 仍是当前两个正式 role 的显式列表；本次只更新成员，不重设计发现机制。OMP 旧状态迁移也使用新 id；当前环境没有旧状态需要恢复。

### 2. 从目标重选完整能力闭包

role-specific Skills：

- `agent-assembler`：端到端控制器；
- `grilling`：仅在直接要求或明确接受后进行结构化问询；
- `agent-prompt-design`、`agent-skill-design`：设计持久行为；
- `capability-lifecycle`：调研、引入、升级和退役能力；
- `capability-profile-closure`：声明、lock、render 和证据分层；
- `agent-behavior-evaluation`：正反场景与可比较观察；
- `spec-change-pack`：值得审计的行为变更。

项目 OpenSpec workflow 继续由 project-defaults 继承。MCP、Hook、Plugin 为空。总 Skill 只编排，不复制各子 Skill 正文。

### 3. prompt 与总 Skill 分层

常驻 prompt 保存角色、硬边界、阶段、人工决定和证据义务。总 Skill执行：恢复合同、查明事实、取得决定、选择能力来源、修改源文件、刷新派生状态、验证与交付。

`grilling` 的决定树、退出和实施前确认只存在于其唯一 Skill；总 Skill 只写触发与返回关系。

### 4. 项目 Skill source-path 使用独立声明

manifest 可选声明：

```toml
skill_imports = ".cap/skill-imports.toml"
```

声明文件格式：

```toml
version = 1

[[imports]]
name = "grilling"
source = "plugins/grilling/skills/grilling"
```

约束：

- `source` 是项目根下规范 POSIX 相对目录，任何分量不得为 symlink；
- 目录名与 Skill id 一致并包含 `SKILL.md`；
- import 源不得位于 `.cap/capabilities/skills`；
- import 必须被至少一个有效 profile引用，未引用声明失败关闭；
- 同名本地 Skill 与 import 冲突失败关闭；
- import 声明、源目录和全部文件逐项进入 lock input；
- 机器／用户目录能力仍使用 external import 与 asset inventory，不走本声明。

不采用复制，因为会产生第二真源。不复用 external import，因为它不负责 staged render。

### 5. capability origin 保存最终源路径

当前 renderer 把 origin 保存为“根”再拼固定目录，无法正确表示 project-defaults 和 import。改为保存每项能力的已验证最终路径：本地 Skill 指向 `.cap/capabilities/skills/<id>`，import 指向声明目录，Hook／Plugin 指向各自能力目录。renderer 不再二次猜路径。

### 6. lock 覆盖完整项目源

`Project` 保存 manifest、project-defaults、runtime policy、可选 Skill import 声明和 import 源。`_input_records` 对这些路径及 capability 树计算 mode 与 SHA-256。任何变化使 lock drift；刷新 lock 后两个正式 role 的 binding 重建。

### 7. 机器审批仍是独立人工门

装配者可以生成 machine-context manifest、说明差异并重建 binding，但不得把“生成摘要”当成“批准摘要”。首次 pin 或 active drift 需要负责人明确批准。普通 role 源修改不自动刷新 pin。

## Risks / Trade-offs

- **manifest 增量**：`skill_imports` 为可选字段，未使用的 v3 项目保持现状；存在时严格校验。
- **role rename**：旧命令立即失效；clean cutover 不提供兼容别名。当前无持久 state，迁移风险低。
- **import 源漂移**：lock 覆盖全部文件；启动前失败关闭。
- **行为证据受认证限制**：无认证时只证明标准、声明、配置和 CLI 启动面；实际模型行为保持 unknown。

## Migration Plan

1. 更新变更包与正反行为合同。
2. 实现可选项目 Skill source-path、最终 origin 和完整 lock input。
3. clean cutover 重命名 profile、prompt、总 Skill与所有调用方。
4. 重写装配合同，声明并 allow `grilling`。
5. 更新文档、刷新 lock、生成并批准当前 machine-context、重建 bindings。
6. 运行单元测试、OpenSpec strict、Skill 标准验证、show/render/verify 和 OMP CLI smoke。

## Rollback Strategy

恢复旧 id、manifest、profile、prompt、总 Skill和调用方；移除 Skill import 声明与实现；刷新 lock／bindings。import 不复制源文件，因此回滚不会留下双份 `grilling`。
