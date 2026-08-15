# K1：Codex 与 Claude Code 的项目指令加载规则

> 状态：正式当前公共知识。
> 最近核验：2026-08-11。
> 适用对象：当前官方文档所描述的 Codex 和 Claude Code；项目／仓库级持久指令加载。
> 环境：通用项目目录；Windows 差异仅限文中明确标出的符号链接选择。
> 版本边界：本包所列规则在两份官方页面中均未绑定到单一产品版本，因此产品升级或文档变化是失效信号。

## 回答的问题与价值门

Codex 和 Claude Code 分别读取什么项目指令文件？一个同时支持两者的仓库，怎样以最低重复成本共享入口规则？

这些结论会在维护仓库入口、诊断指令未加载和评估入口上下文成本时重复使用；它们也解释 `agent-control` 当前入口设计，因此通过价值门。自然复用是否比重新调研更省成本仍待真实任务观察，不能由正式收录本身推出。

## 可直接复用的结论

### Codex

1. Codex 在每次运行开始时建立一条项目指令链。在 Codex home 目录（默认 `~/.codex`；设置 `CODEX_HOME` 时改用其指向的目录）中优先选择 `AGENTS.override.md`，否则选择 `AGENTS.md`；项目范围通常从 Git 根目录走到当前工作目录。
2. 在项目路径的每一层目录中，Codex 依次检查 `AGENTS.override.md`、`AGENTS.md` 和已配置的备用文件名，最多采用一个非空文件。文件从根到当前目录合并；更近当前目录的文件后置，并覆盖先前指导。
3. 合并后的项目指令默认受 `project_doc_max_bytes` 的 32 KiB 上限约束。达到上限时应精简入口、使用更具体的嵌套文件，或有意调整配置；不能假设所有长说明都会进入上下文。

### Claude Code

1. Claude Code 在每个会话开始时读取持久指令。团队共享的项目文件可以位于 `./CLAUDE.md` 或 `./.claude/CLAUDE.md`；这项结论只适用于 Claude Code，不泛化到其他 Claude 产品。
2. Claude Code 读取 `CLAUDE.md`，不会直接把 `AGENTS.md` 当作项目指令。`CLAUDE.md` 可以用 `@path/to/import` 导入其他文件；已有 `AGENTS.md` 的仓库可以用 `@AGENTS.md` 共享同一组规则而不复制正文。
3. 在 Windows 上，如果只是要共享 `AGENTS.md`，优先用 `@AGENTS.md` 导入；符号链接可能要求管理员权限或开发者模式。
4. `CLAUDE.md` 及其导入会进入会话上下文，而不是形成强制配置或安全边界。需要无条件阻止某项操作时，改用权限设置（例如 `permissions.deny`）或 `PreToolUse` Hook 等由产品执行的强制机制。官方建议每个 `CLAUDE.md` 以少于 200 行为目标；拆成导入文件有助于组织，但导入内容仍在启动时进入上下文。

### 对同时支持两者的仓库

- 用 `AGENTS.md` 保存两者共享的仓库规则，用很短的 `CLAUDE.md` 通过 `@AGENTS.md` 导入；只有确有 Claude Code 专属内容时才在导入后追加。
- 把入口保持具体、简短；更长或只与子目录相关的规则放在产品支持的更窄作用域中：Codex 使用目标子目录中的嵌套 `AGENTS.md`（需要其他文件名时将其加入 `project_doc_fallback_filenames`），Claude Code 使用 `.claude/rules/` 中带 `paths` frontmatter 的路径限定规则。
- 把这些文件当作行为指导和上下文，不当作权限控制、强制安全策略或“Agent 必然遵守”的保证。

## 第一方来源与结论映射

1. OpenAI，[Custom instructions with AGENTS.md](https://learn.chatgpt.com/docs/agent-configuration/agents-md)：支持 Codex 的运行时指令链、默认 home 与 `CODEX_HOME` 例外、全局与项目查找顺序、每目录单文件、根到当前目录的覆盖顺序、嵌套文件、`project_doc_fallback_filenames`，以及默认 32 KiB 上限。核验日期：2026-08-11。
2. Anthropic，[Claude 如何记住你的项目](https://code.claude.com/docs/zh-CN/memory)：支持 Claude Code 的项目文件位置和会话加载、`@` 导入、`@AGENTS.md` 共享方式、Windows 符号链接差异、`.claude/rules/` 与 `paths` frontmatter、少于 200 行建议、上下文成本、非强制性质，以及权限／`PreToolUse` Hook 的强制补救。核验日期：2026-08-11。

这两份页面是本包行为结论的唯一来源。旧试用文件和 GitHub 讨论只解释本包的形成过程，不作为当前事实来源。

## 例外、未知和不能推出的结论

- Codex home（全局）层的上述文件选择顺序已经核验；除此之外，用户级、组织级和托管策略的其他行为不在本包核验范围，遇到这些范围时补查相应官方章节。
- 本包只核验 `project_doc_fallback_filenames` 备用文件名机制的存在；未核验具体自定义值，也未核验父目录规则与项目规则发生冲突时的全部行为。遇到这些情况只复用无冲突部分，并补查相应官方章节。
- 未在本包中验证某一具体仓库实际加载成功，也未验证 Claude Code 以外的 Claude 产品、Codex 以外的执行环境或其他编码 Agent。
- 官方文档描述支持的加载机制，不保证模型在每次会话中严格遵守全部指令。
- 这里没有证明自然复用的长期 ROI、知识平台的需要、产品采用或长期依赖。

## 失效条件

出现以下任一情况时，相关结论立即停止直接复用，重新核验前只作为历史证据：

1. Codex 或 Claude Code 升级后，入口文件没有按上述方式加载；
2. 任一官方页面修改了文件名、查找／合并顺序、导入语法、大小限制或上下文／强制边界；
3. 任务开始依赖未逐项核验的嵌套目录行为、`project_doc_fallback_filenames` 具体自定义值、用户级、组织级、托管策略或外部目录导入；
4. 任务需要把项目指令作为强制权限或安全边界；
5. 任务对象扩展到 Claude Code 和 Codex 以外的产品或环境。

## 下次最少复核步骤

1. 只打开上面两份官方页面。
2. 在 OpenAI 页面检查“`How Codex discovers guidance`”和“`Customize fallback filenames`”中的默认 home、`CODEX_HOME` 例外、文件优先级、根到当前目录的覆盖、`project_doc_fallback_filenames` 和 `project_doc_max_bytes` 默认值。
3. 在 Anthropic 页面检查“`CLAUDE.md 与自动记忆`”“`选择 CLAUDE.md 文件的位置`”“`导入其他文件`”“`AGENTS.md`”“`编写有效的指令`”和“`使用 .claude/rules/ 组织规则`”中的项目位置、`@AGENTS.md`、Windows 差异、`.claude/rules/` 与 `paths` frontmatter、上下文与非强制边界，以及权限／`PreToolUse` Hook 的强制补救。
4. 没有变化时继续复用；有变化时只更新受影响结论。若页面无法访问或无法确认某条结论，该结论先退出当前知识，不以旧文本兜底。

## 不适用范围

- 全局 Agent 配置优化；
- Skill、Hook、MCP 或 Plugin 的选型；
- 多 Agent 调度和协作后端；
- 私域知识保存；
- 其他产品的指令文件；
- 强制权限与安全策略。
