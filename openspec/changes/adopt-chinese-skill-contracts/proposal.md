## Why

快速迭代早期同时维护英文运行时 Skill 和中文全文镜像，会让每次行为调整产生双份编辑、审查和漂移风险。项目面向中文维护者，且 Agent Skills 标准不限制正文语言，因此改为中文单一运行时合同，用一个 truth source 降低迭代成本。

## What Changes

- 将 `.cap/capabilities/skills/*/SKILL.md` 的 `description` 和正文统一改为中文；机器 id、路径和 OpenSpec 结构关键字保持英文。
- 将中文 `SKILL.md` 设为唯一执行合同和唯一全文维护源。
- 移除 `docs/skills/*.zh-CN.md` 全文镜像，避免双语同步义务。
- 更新 `AGENTS.md`、README、Skill 目录、维护指南和 OpenSpec context，使语言策略一致。
- 对语言切换执行 Skill 元数据验证、闭包验证和 OMP 路由 smoke check，不凭语言相同推断跨客户端等价。

## Non-goals

- 不翻译稳定机器 id、目录名、命令、配置键或 OpenSpec 解析关键字。
- 不承诺长期永远只用中文；进入跨语言发布阶段时再通过独立 change 评估英文发行版。
- 不改变 profile 的 MCP、Hook、Plugin 能力面。

## Capabilities

### New Capabilities

- `chinese-skill-contracts`：规定快速迭代阶段以中文运行时 Skill 作为唯一全文合同，并禁止维护第二份逐字镜像。

### Modified Capabilities

无。当前长期 specs 中尚无语言维护能力。

## Impact

- 项目规则：`AGENTS.md`。
- 运行时合同：`.cap/capabilities/skills/*/SKILL.md`。
- 审查文档：`README.md`、`docs/skill-catalog.zh-CN.md`、`docs/maintenance.zh-CN.md`，并删除 `docs/skills/*.zh-CN.md`。
- OpenSpec：`openspec/config.yaml` 及后续 change 资产。
- 验证：Skill 元数据、profile lock/verify、OMP 运行 smoke。

## Baseline Evidence

当前仓库明确要求英文 `SKILL.md` 为执行合同，同时为每个 Skill 维护中文全文镜像；维护指南要求英文语义变化时同步检查并更新中文全文。当前正进行多项 Skill 行为调整，这会使双份全文维护成本立即扩大。

控制事实：Agent Skills 规范只约束 `name`、`description` 和目录格式，没有规定正文必须使用英文：https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx

## Rollback Boundary

若中文运行时合同在目标客户端出现可重复的发现或执行回归，则通过独立 change 恢复英文运行时正文；在回滚发生前，不重新建立逐字双语镜像。任何语言迁移都保持机器 id 和 profile 引用稳定。
