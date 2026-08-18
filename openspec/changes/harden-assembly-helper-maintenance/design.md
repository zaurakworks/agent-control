## Context

变更动机和基线见 `proposal.md`。当前仓库把 manifest、profile 和 lock 操作委托给相邻 `agent-control` 的 profile 工具，并把运行时能力限制在 `.cap`。OpenSpec 可以生成客户端专属 Skill 和 command，但这些目录会在选定 profile 之外形成第二条运行时能力路径。

## Goals / Non-Goals

**Goals：**

- 保持 `.cap` 为唯一运行时能力授权面。
- 让 Skill 发现元数据可移植、可确定性验证。
- 增加聚焦的调研、Skill 编写和行为评测流程，不扩大 MCP、Hook、Plugin 能力面。
- 让 OpenSpec 规划可以仅凭仓库复现。

**Non-Goals：**

- 不替代 `agent-control` 的 lock、render、probe 语义。
- 不生成 `.agents`、`.omp` 或 `.qoder` OpenSpec 运行时文件。
- 不建设通用评测平台，也不依赖托管服务。
- 当凭据或客户端可观察性不足时，不在本次变更中虚构三端行为证明。

## Decisions

### OpenSpec 采用仓库内 CLI

把 `@fission-ai/openspec` 固定为 `devDependencies`，提交 npm lock，通过 `npx openspec` 调用，并使用 `--tools none` 初始化。这样版本和规划资产可复现，同时避免全局安装和未声明客户端目录。

备选方案是官方推荐的全局安装。它对个人工作站更简单，但不满足本仓项目内自足和可复现要求。

### 每个 Skill 使用标准元数据

只加入可移植的必需字段 `name` 和 `description`。不使用实验性 `allowed-tools`；工具和能力授权仍由选定 profile 控制。

保留无 frontmatter 文件、继续依赖当前 renderer 的目录 inventory，会让闭包成功持续掩盖不可移植的发现元数据，因此不采用。

### 新增两个聚焦 Skill

新增 `agent-skill-design`，负责 Skill 格式、路由、渐进披露和验收设计；新增 `agent-behavior-evaluation`，负责基线和可比较运行证据。调研作为常驻 prompt 的显式阶段，并落实到既有 `capability-lifecycle`，不再新增一个职责重叠的调研 Skill。

不采用单个大型“自维护”Skill，因为 prompt 设计、Skill 设计、能力来源、闭包和评测具有不同触发条件和输出。

### Prompt 只承载不变量和路由

项目闭包、三态结论、无 secret、调研触发和评测义务保持常驻；过程细节进入对应 Skill。在路由 smoke test 证明新元数据可见并可用之前，不激进压缩 prompt。

### 本地确定性元数据验证

为 `tools/cap.py` 增加 `skills-validate` 命令，并让 `cap verify` 在委托闭包和 lock 验证前执行它。验证器检查 frontmatter 分隔符、必需标量 `name` 和 `description`、名称格式和目录一致性、长度限制，并把 `standard_conformance` 与闭包结果分开报告。

官方 `skills-ref` 自称演示性参考库，不适合作为未经固定的生产依赖。因此本仓实现当前使用的必需可移植子集，并把 frontmatter 限制为简单标量字段。

### 轻量行为证据

长期行为需求写入 OpenSpec specs；初始 smoke check 使用可复现的 OMP batch prompt。检查同时包含必须外部调研和不应外部调研的任务，以及三态结论边界。记录准确命令和观察结果；不能把模型自述的 Skill inventory 当成完整行为证明。

## Risks / Trade-offs

- **本地验证器只实现 YAML 子集** → 本仓 frontmatter 仅使用简单必需标量；遇到畸形或重复键时失败关闭。
- **Skill 数量增加可能加剧路由歧义** → 每个 description 明确正向触发和相邻职责边界，并运行正反 smoke 场景。
- **Prompt 与 Skill 可能漂移** → Prompt 只保留不变量和路由；中文 `SKILL.md` 是唯一全文合同，不维护逐字镜像。
- **一次 OMP 运行不能代表所有客户端和 trial** → 只声明 OMP 生效态证据；Codex 和 Qoder 保持 unknown，直到真实观察。
- **OpenSpec 增加 npm 维护面** → 固定版本、提交 lock，并保持客户端产物生成关闭。

## Migration Plan

1. 安装并初始化仓库内 OpenSpec。
2. 为既有 Skill 添加标准 frontmatter。
3. 新增两个中文 Skill，并在 profile 和摘要目录中声明。
4. 加强调研、prompt 设计、生命周期、闭包和总入口合同。
5. 增加本地元数据验证，在闭包验证前运行。
6. 更新维护文档和 lock。
7. 运行 OpenSpec 验证、元数据验证、profile 闭包验证、inventory smoke 和正反 OMP 行为 smoke。
8. 仅在实施任务和证据完整后归档。

回滚时移除两个新增 profile 引用和 Skill 文件，恢复之前的合同与验证器行为，刷新 `.cap/lock.json` 并重新运行闭包验证。即使之后退役 npm 依赖，OpenSpec 历史也可以保留为审计证据。
