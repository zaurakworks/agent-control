## Context

当前规则把英文 `SKILL.md` 作为执行合同，并在 `docs/skills` 下维护中文全文。正在进行的 assembly-helper 行为改造会同时触及多个 Skill，双语逐字同步成为主要维护成本。Agent Skills 标准不限制正文语言，但不同客户端对中文 description 的路由效果仍需真实验证。

## Goals / Non-Goals

**Goals：**

- 以中文运行时 `SKILL.md` 作为唯一全文 truth source。
- 删除需要同步的中文全文镜像，保留中文摘要目录。
- 保持机器 id、路径和 profile 引用稳定。
- 将语言切换的证据限制在实际验证覆盖的状态层和客户端。

**Non-Goals：**

- 不翻译命令、配置键、路径、标准字段和 OpenSpec 解析关键字。
- 不把中文单语策略永久化；跨语言发布阶段另行评估。
- 不改变 MCP、Hook、Plugin 或客户端安装面。

## Decisions

### 先切换项目规则，再迁移合同

同一个 change 同时更新 `AGENTS.md`、维护指南、运行时 Skill 和目录，避免出现“规则要求英文但文件已中文”或反向不一致。迁移采用 clean cutover，不保留双语 alias。

### 删除全文镜像，保留摘要目录

`docs/skill-catalog.zh-CN.md` 保留导航、触发摘要和能力关系，直接链接 `.cap/capabilities/skills/*/SKILL.md`。删除 `docs/skills/*.zh-CN.md`，因为它们不再提供独立价值且会恢复同步成本。

### Frontmatter description 同样使用中文

`name` 必须维持标准机器 id；`description` 是路由信号，也属于唯一合同的一部分，使用中文并通过 OMP 正反触发 smoke 验证。不采用“英文 description + 中文正文”的半双语方案。

### 当前 hardening change 依赖本迁移

先完成并归档 `adopt-chinese-skill-contracts`，再继续 `harden-assembly-helper-maintenance`。后者新增和修改的所有 runtime Skill 直接使用中文，避免先写英文再翻译。

## Risks / Trade-offs

- **某些客户端对中文路由较弱** → 分客户端保留 unknown，先验证 OMP；发现可重复回归时通过独立 change 回滚语言策略。
- **删除镜像减少英文可读性** → 早期迭代阶段接受该取舍；稳定发布前重新评估英文发行资产，而不是恢复逐字双写。
- **活跃 change 的上下文仍描述旧规则** → 本迁移归档后更新 OpenSpec context，并刷新后续 change 的设计和任务。

## Migration Plan

1. 更新项目规则和维护文档，声明中文 `SKILL.md` 为唯一全文合同。
2. 将现有 Skill 的 frontmatter description 和正文一次性迁移为中文。
3. 更新目录链接并删除 `docs/skills` 全文镜像。
4. 更新 OpenSpec context，使后续 change 默认生成中文人读资产和中文 runtime Skill。
5. 刷新 lock，运行标准验证、闭包验证和 OMP 路由 smoke。
6. 归档本 change，再继续 assembly-helper hardening change。
