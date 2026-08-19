# Why

当前只有面向 Agent 装配工作的 `assembly-helper` profile，普通工作仍会落回未受管客户端，无法获得显式能力闭包。现在需要一个可恢复既有 OMP Session 的 `general` profile，并把 OpenSpec 工作流作为所有工作 profile 的基础能力。

# What Changes

- 新增显式 `general` profile，提供通用工程工作 prompt，不继承装配专用 Skills。
- 将 OpenSpec 1.9.0 对应的 Explore、Propose、Update、Apply、Sync、Archive 工作流作为中文 Skill 合同纳入 `.cap`。
- `general` 与现有 `assembly-helper` 都显式声明上述 OpenSpec Skills；不通过 `.agents`、`.claude`、`.qoder` 或 `.omp` 原生目录旁路加载。
- 记录 OMP 通过 `cap use general --cli omp -- --resume <id-or-path>` 恢复既有 Session 的入口；profile 变化在恢复后的新运行实例生效，不热改正在运行的能力快照。
- 更新 manifest、lock、Skill 目录和使用说明，并验证三端渲染闭包。

# Non-Goals

- 本变更不实现多 catalog、latest-at-start 或外部 Skill resolver。
- 本变更不新增 CAP `commands` 能力类型；显式调用先使用各客户端已有的 Skill 入口，客户端专属 `/opsx:*` 投影留给后续四端适配变更。
- 本变更不把 `general` 设为隐藏默认 profile，也不允许未显式选择 profile 的客户端冒充 `general`。
- 本变更不改变认证、Session 存储或客户端自身的 resume 格式。

# Capabilities

## New Capabilities

- `general-profile`: 定义显式通用 profile、所有工作 profile 的 OpenSpec 基础能力闭包，以及在新 profile 运行实例中恢复既有 OMP Session 的可观察合同。

## Modified Capabilities

无。

# Impact

- 受影响 profile：新增 `general`；修改 `assembly-helper` 的 Skill 闭包。
- 受影响能力：新增六个 `openspec-*` Skill；不新增 MCP、Hook 或 Plugin。
- 受影响文件：`.cap/manifest.toml`、`.cap/profiles/*`、`.cap/prompts/*`、`.cap/capabilities/skills/*`、`.cap/lock.json`、README 与 Skill 目录。
- 依赖基线：仓库固定 `@fission-ai/openspec` 1.9.0；本机 OMP 17.3.5 的官方 `--help` 声明 `--resume=<id|path>`、`--continue`，且 `tools/cap.py` 会原样透传 `--` 后客户端参数。
- 回滚边界：删除 `general` 声明与 prompt，移除两个 profile 对 OpenSpec Skills 的引用和对应 Skill 文件，再重建 lock；既有 OMP Session 数据不被修改。
