# 仓库工作入口

本仓的项目级 Agent 规则正文在 [`entrypoints/agent-system.md`](./entrypoints/agent-system.md)，开始工作前读取。它只在工作目录落在本仓时加载，不进入用户级全局常驻面。

## 仓库任务路由

- 开始任何工作前，先读取 `README.md` 并执行其中的“开始工作”。
- 以 `authority/00-map.md` 为产品政策根；有明确 GitHub Issue 时先读取远端当前合同，只加载合同链接的最窄政策与证据。
- 带 `迁移索引/待分诊` 标签的 Issue 默认只允许分诊和只读核验；旧正文、私有评论与开放状态都不恢复实施授权。
- 没有明确 Issue 时保持自由对话或当前请求的最小范围；可以提出有界候选，不能自行激活、派发或恢复旧事项。
- 可用 Plugin 只有在实际安装、合同明确调用和能力核验通过时才参与执行；源码存在不等于生效。
- 不把分析、提案、实验、历史记录或私有旧仓材料当成当前授权。
- 未经负责人明确确认，不扩大授权，不恢复暂停事项，也不修改产品政策。

## 知识按名问路

- 需要 Windows／PowerShell GitHub 多行 Markdown 或 Windows 长路径／文件锁知识时，主动按名运行 `python tools/knowledge_action_trigger/action_trigger.py --action github-multiline-markdown` 或 `--action windows-path-or-file-lock`，再按需读取返回的当前知识源。
- 这是可查询工具，不自动触发、注入或挂 Hook；也可直接按名读取 `knowledge/windows-powershell-multiline-transfer.md` 或 `knowledge/windows-agent-ops.md`。查询不扩大合同、权限或产品决定。
