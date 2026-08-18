# Context

`agent-assembly` 当前只有 `assembly-helper`，其 prompt 和七个 Skills 都针对 Agent 装配。`tools/cap.py` 支持显式 profile、隔离且持久的客户端 home，并把 `--` 后参数透传给客户端；OMP 17.3.5 支持 `--resume=<id|path>` 和 `--continue`。仓库固定 OpenSpec 1.9.0，但现有 `spec-change-pack` 只是装配维护方法，不是完整 OpenSpec 工作流入口。

本变更是项目内 bootstrap：`general` 仍属于 `agent-assembly` 的 `.cap` 闭包，不是跨任意仓库自动继承业务规则的全局 profile。

# Goals / Non-Goals

## Goals

- 提供与装配角色解耦的显式 `general` profile。
- 让仓库内所有工作 profile 都能通过自然语言或客户端已有的 Skill 调用进入完整 OpenSpec 工作流。
- 支持保留 Session 历史、以新 profile 能力快照恢复 OMP。
- 保持 `.cap` 为唯一运行时能力来源，并生成可核验 lock。

## Non-Goals

- 不新增 profile 继承、隐藏 baseline 或默认 profile 推断。
- 不实现客户端专属 `/opsx:*` command 文件渲染。
- 不实现外部 catalog resolution 或自动联网升级 OpenSpec。
- 不修改 OMP Session 文件格式。

# Decisions

## 1. general 使用独立最小 prompt

新增 `.cap/prompts/general.md`，只声明通用工程角色、显式身份、项目内权威、OpenSpec 路由和交付证据。它不复用 `assembly-helper.md`，避免普通工作继承装配输出格式和专用流程。

备选方案是让 `general` 继承 assembly-helper 后关闭部分 Skills；这会引入负向覆盖和难以审查的隐式语义，拒绝采用。

## 2. OpenSpec 工作流作为六个中文 Skill 合同 vendoring

新增六个 `.cap/capabilities/skills/openspec-*/SKILL.md`。每个 Skill 保持单一阶段边界，并在 `compatibility` 声明 OpenSpec CLI 1.9.0。正文使用中文，稳定命令和工件名保持原样；工作流以本地 CLI 的 `list`、`status`、`instructions`、`validate`、`apply` 与 `archive` 能力为准。

这些文件是运行时合同，不从 OpenSpec 初始化产生的 provider 目录加载。升级 CLI 时必须同时审查并更新六个 Skill 合同和 lock。

备选方案是只保留 `spec-change-pack`。它无法提供 Explore、Proposal、Apply、Sync 和 Archive 的明确阶段入口，因此拒绝采用。

## 3. 每个 profile 显式列出 OpenSpec Skills

`general.toml` 与 `assembly-helper.toml` 都直接列出六个名字。第一版不加入 manifest 级 baseline 或 profile 继承：显式重复比隐藏注入更容易审查，且 profile 数量当前只有两个。

validator 和 lock 负责发现缺失、拼写错误或内容漂移。未来 profile 数量显著增加后，才评估显式的 baseline schema。

## 4. 显式调用复用客户端 Skill 机制

自然语言是正确性入口。显式入口先采用客户端对已加载 Skill 的原生调用方式，例如 OMP 的 `/skill:openspec-explore` 或 Codex 的 `$openspec-explore`。本变更不伪造独立 command 文件。

四端原生 `/opsx:*` 入口需要 CAP 新增 `commands` 能力类型，属于后续四端适配变更；不能把 command 文件塞进 opaque Plugin 目录。

## 5. Resume 是重启运行实例，不是热更新

推荐入口：

```bash
python3 tools/cap.py use general --cli omp -- --resume <id-or-path>
```

`cap.py` 先用 `general` 渲染持久 agent home，再把 `--resume` 原样交给 OMP。Session 历史由 OMP 恢复；Skill 和 prompt 来自这次启动的渲染快照。运行中的进程不观察 `.cap` 文件变化。

用 ID 恢复依赖 OMP 能在当前 Session 存储范围找到该 ID；跨隔离 home 时使用 Session 文件路径是确定性入口。

# Risks / Trade-offs

- [显式 Skill 列表存在重复] → 由 lock 和 verify 检查，暂不引入继承复杂度。
- [OpenSpec Skill 合同可能落后于 CLI] → 固定兼容版本；CLI 升级必须同时更新合同和 lock。
- [跨隔离 home 的 Session ID 不可见] → 使用 OMP 支持的 Session 文件路径恢复，并在文档中明确。
- [当前没有独立 `/opsx:*` command 投影] → 保留自然语言和原生 Skill 显式入口；在后续 `commands` 能力变更中补齐。
- [render 通过不能证明模型使用 Skill] → 分开报告声明态、配置态和真实 OMP smoke check。

# Migration Plan

1. 添加六个 OpenSpec Skill 合同和 `general` prompt/profile。
2. 将 `general` 注册到 manifest，并把六个 Skills 加入 `assembly-helper`。
3. 更新 README、Skill 目录和 `.cap/lock.json`。
4. 运行 Skill 标准验证、OpenSpec strict validation、CAP verify 和三端 render。
5. 用 OMP 启动 `general` smoke session；若已有可访问的 Session 路径，再验证 resume。
6. 回滚时逆序删除声明与能力并重建 lock，不修改 Session 数据。
