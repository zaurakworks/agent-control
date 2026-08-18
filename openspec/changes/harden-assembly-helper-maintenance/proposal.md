## Why

`assembly-helper` 已形成项目内闭包，但五个运行时 Skill 均缺少 Agent Skills 标准要求的 frontmatter；外部调研仍是建议而不是显式阶段；仓库也没有行为评测合同。因此，当前项目能够证明声明和 lock 一致，却不能证明 Skill 可移植发现，也不能证明 prompt 或 Skill 修改带来行为改善。

## What Changes

- 为每个运行时 Skill 增加符合标准的 `name` 和 `description` 元数据。
- 新增 `agent-skill-design`，负责触发设计、渐进披露、标准验证和 Skill 验收场景。
- 新增 `agent-behavior-evaluation`，负责基线、正反场景、可比较 trial、transcript 审查和结果证据。
- 当装配决定依赖外部标准、客户端行为、当前版本或候选资产时，将官方一手网络调研设为显式要求。
- 扩展闭包验证，分别报告本地闭包、Agent Skills 标准合规和实际运行证据。
- OpenSpec 保持仓库内安装，通过 `npx openspec` 调用；不生成未声明的客户端专属 OpenSpec Skill 或 command。

## Non-goals

- 不新增 MCP、Hook、Plugin、secret 管理、marketplace 或用户级配置。
- 不用 lock 或静态验证声称跨客户端行为改善。
- 不在 `.cap` 之外安装 OpenSpec 生成的运行时能力。
- 对完全可由仓库恢复的内部事实，不强制进行形式化网络调研。

## Capabilities

### New Capabilities

- `research-first-assembly`：规定何时必须外部调研、来源优先级、证据记录和纯仓库任务边界。
- `agent-skill-design`：规定可移植 Skill 元数据、路由边界、渐进披露和标准合规验证。
- `agent-behavior-evaluation`：规定基线、正反场景、可比较 trial、结果检查和证据结论。

### Modified Capabilities

无。当前 `openspec/specs/` 中没有既有能力规范。

## Impact

- Profile 与 prompt：`.cap/profiles/assembly-helper.toml`、`.cap/prompts/assembly-helper.md`。
- 运行时合同：既有 `.cap/capabilities/skills/*/SKILL.md` 以及两个新增 Skill 目录。
- 验证：`tools/cap.py`、`.cap/lock.json`、OpenSpec 验证和 OMP 运行 smoke check。
- 审查文档：`docs/skill-catalog.zh-CN.md`、`docs/maintenance.zh-CN.md`、`README.md`。
- 工具：仓库内 `@fission-ai/openspec` 依赖和 `openspec/` 规划资产。

## Baseline Evidence

- 五个既有 `SKILL.md` 均缺少 YAML frontmatter。
- `cap verify` 返回 `status: ok`，说明当前验证未覆盖 Agent Skills 元数据合规。
- 通过 `tools/cap.py` 启动的 OMP 能看到五个已声明 Skill，但仓库没有正反路由套件或可比较行为基线。
- `.cap` 和 `docs` 下没有行为 eval、golden scenario 或 regression 资产。

控制本次设计的一手来源：

- Agent Skills 规范：https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx
- Anthropic Skill 编写指南：https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Anthropic Agent 评测指南：https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- OpenSpec 安装与工作流：https://github.com/Fission-AI/OpenSpec/blob/main/docs/installation.md

## Rollback Boundary

移除两个新增 Skill 的 profile 引用和文件，恢复原 prompt、生命周期和闭包合同，按需移除仓库内 OpenSpec 依赖和项目工作流，刷新 lock 并重新运行闭包验证。任何回滚步骤均不得修改用户级 Agent 配置；如 OpenSpec 历史仍有审计价值，可保留其归档资产。
