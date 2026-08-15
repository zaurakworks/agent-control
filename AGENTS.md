# 仓库工作入口

## 持久实现语言

公共规则见 [`entrypoints/agent-system.md` 的同名章节](./entrypoints/agent-system.md#持久实现语言)。

## 仓库任务路由

- 开始任何工作前，先读取 `README.md` 并执行其中的“开始工作”。
- 以 `authority/00-map.md` 为权威根；有明确 GitHub Issue 时先恢复远端合同，只加载合同链接的权威。授权变化与共享写入所有权同样以远端 Issue 为准，`work/current.md` 只是恢复指针，用于定位主线入口、各来源 observedAt 水位与未解决冲突标志。
- 没有明确 Issue 且被要求选择下一项工作时，经经营总账从未满足／部分满足诉求返回 `adaptive-problem-solving`；不要把空的“就绪”队列解释为没有工作。
- Session 职责由 Issue 合同和写入所有权决定。父 Issue 与叶子 Issue 都路由到 `github-collaboration:issue-workflow`，详细状态机只在 Skill 内。
- 不把分析、提案、实验、历史记录或旧仓材料当成权威。
- 未经负责人明确确认，不扩大授权，不恢复暂停事项，也不修改权威结论。

## 知识按名问路

- 需要 Windows／PowerShell GitHub 多行 Markdown 或 Windows 长路径／文件锁知识时，主动按名运行 `python tools/knowledge_action_trigger/action_trigger.py --action github-multiline-markdown` 或 `--action windows-path-or-file-lock`，再按需读取返回的当前知识源。
- 这是可查询工具，不自动触发、注入或挂 Hook；也可直接按名读取 `knowledge/windows-powershell-multiline-transfer.md` 或 `knowledge/windows-agent-ops.md`。查询不扩大合同、权限或产品决定。

### 持有 Issue 时扩大并行波次

公共规则见 [`entrypoints/agent-system.md` 的同名章节](./entrypoints/agent-system.md#持有-issue-时扩大并行波次)。

## 在线续接与负责人事项

公共规则见 [`entrypoints/agent-system.md` 的同名章节](./entrypoints/agent-system.md#在线续接与负责人事项)。

## 父目标验收

公共规则见 [`entrypoints/agent-system.md` 的同名章节](./entrypoints/agent-system.md#父目标验收)。

## 经营总账维护

公共规则见 [`entrypoints/agent-system.md` 的同名章节](./entrypoints/agent-system.md#经营总账维护)。
