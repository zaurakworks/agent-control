# Research：跨 Codex / Claude 的方法资产边界

## 研究标识

- Issue：[`Eridanus117/agent-plugins#1`](https://github.com/Eridanus117/agent-plugins/issues/1)
- 调研时间：2026-08-08（America/New_York）
- 当前阶段：只核对事实；不选择资产模型，不写实施步骤
- 样例资产：`grilling`
- 上游冻结提交：[`mattpocock/skills@84fdeffd12f2ee307994d1eb6feb48173b6e0502`](https://github.com/mattpocock/skills/commit/84fdeffd12f2ee307994d1eb6feb48173b6e0502)

## 范围与权威

当前产品输入来自：

- [`agent-system-foundry` 方法介入合同](https://github.com/Eridanus117/agent-system-foundry/blob/main/product/method-intervention.md)
- [`agent-system-foundry` 验收场景](https://github.com/Eridanus117/agent-system-foundry/blob/main/product/method-intervention-scenarios.md)
- [`agent-system-foundry#1`](https://github.com/Eridanus117/agent-system-foundry/issues/1)
- 本 Issue 当前 body 与 framing Challenge

本机和外部仓中的旧 Orrery、`agent-workbench`、旧 `codex-marketplace`、Claude job 临时文件只作为现状或失败样本，不拥有本仓架构权威。

## 仓库现状

- `agent-plugins` 的 `main` 当前为 `795700e`，只有 `README.md`。
- README 只有仓名和一句“Cross-provider plugin and skill marketplace for Codex and Claude”。
- 仓内没有 `AGENTS.md`、`CLAUDE.md`、贡献约定、语言、构建、Lint、测试、Manifest 或资产目录。
- 因此没有可继承的实现架构，也没有仓库原生验证命令。

## 已合并产品合同给出的边界

产品合同已经规定以下用户可见行为：

- 普通任务始终是完整出口；方法不是强制流程。
- 用户选择方法前不能自动展开方法问卷。用户直接请求该方法，或在 Agent 建议后明确接受，都构成可观察同意；任务复杂、命中关键词或 Agent 自己判断“适合”不构成同意。
- 中途升级需要新证据、影响、建议、成本和普通出口。
- 同一理由被拒绝后不能重复打扰。
- 方法开始后仍能降级、换方法或退出，并保留原任务和已确认内容。
- `grilling` 是当前唯一方法入口；`grill-me` 只是上游别名，不打包、不安装、不维护。
- 能自行查明的事实由 Agent 调查；价值、偏好和边界取舍由用户决定。
- 共同理解得到确认前，不能实施依赖该决定的内容。

产品合同没有规定 Skill 目录、Plugin manifest、Marketplace、安装脚本、Provider 配置或测试框架，也没有规定必须通过斜杠 / 美元命令进入。它约束的是问询开始前的用户授权，而不是某一种宿主调用机制。

## Agent Skills 公共格式

当前 [Agent Skills 规范](https://agentskills.io/specification) 的公共部分是：

- 一个 Skill 至少是一个包含 `SKILL.md` 的目录。
- `SKILL.md` 必须有 YAML frontmatter 和 Markdown 正文。
- `name` 与 `description` 是必需字段；`license`、`compatibility`、`metadata` 和实验性的 `allowed-tools` 是可选字段。
- `scripts/`、`references/`、`assets/` 是推荐约定，不是强制的完整目录清单。
- Skill 通过渐进式加载工作：先加载名称与描述，触发后加载完整 `SKILL.md`，其他资源按需加载。
- 规范建议 `SKILL.md` 少于 500 行、资源使用相对路径，并可用 `skills-ref validate` 校验公共格式。
- 公共规范不定义 Codex Plugin、Claude Plugin、Marketplace、调用命名空间或安装缓存。

这意味着 `SKILL.md` 和同目录资源具有跨端公共基础，但 Provider 包装与调用策略仍属于宿主扩展。

## Codex 当前官方合同

来源：

- [OpenAI Docs：Build skills](https://learn.chatgpt.com/docs/build-skills)
- [OpenAI Docs：Package your plugin](https://developers.openai.com/plugins/build/plugins)
- [OpenAI Docs：Plugins](https://learn.chatgpt.com/docs/plugins)

核对到的事实：

1. Codex 的 Skill 目录以 `SKILL.md` 为核心，可附带 `scripts/`、`references/`、`assets/` 和 `agents/openai.yaml`。
2. 本地 Skill 的发现位置包含仓内 `.agents/skills`、用户级 `$HOME/.agents/skills`、管理级目录和系统内置目录。
3. Codex 支持显式调用与按 `description` 隐式调用。`agents/openai.yaml` 的 `policy.allow_implicit_invocation: false` 可以关闭隐式调用而保留显式调用。
4. 官方把直接 Skill 目录定位为本地编写或仓内工作流，把 Plugin 定位为跨仓、可安装分发载体。
5. 当前 Codex Plugin 必须有 `.codex-plugin/plugin.json`；`skills/`、`hooks/`、`.mcp.json`、`.app.json` 和 `assets/` 位于 Plugin 根目录。
6. `.codex-plugin/plugin.json` 中的组件路径相对 Plugin 根目录，并以 `./` 开头。
7. 仓级 Marketplace 的当前路径是 `.agents/plugins/marketplace.json`；Codex 也读取 `.claude-plugin/marketplace.json` 作为 legacy-compatible Marketplace 位置。
8. Marketplace 可以指向同仓相对 Plugin 路径、Git 仓或子目录，并可用 ref 或 SHA 固定 Git-backed Plugin 来源。
9. Codex / ChatGPT Desktop 安装 Marketplace Plugin 后从 `~/.codex/plugins/cache/<marketplace>/<plugin>/<version>/` 的副本加载，而不是直接使用 Marketplace 工作目录。
10. 当前本机 `codex plugin` 提供安装、列出、移除和 Marketplace 管理命令，没有 `validate` 子命令。
11. 当前 OpenAI Docs 把 Plugin 描述为 ChatGPT 与 Codex 的通用目录，但它不覆盖 Claude Code。

## Claude Code 当前官方合同

来源：

- [Claude Code：Skills](https://code.claude.com/docs/en/skills)
- [Claude Code：Create plugins](https://code.claude.com/docs/en/plugins)
- [Claude Code：Plugins reference](https://code.claude.com/docs/en/plugins-reference)
- [Claude Code：Plugin marketplaces](https://code.claude.com/docs/en/plugin-marketplaces)

核对到的事实：

1. Claude Code 的个人、项目与 Plugin Skill 分别位于 `~/.claude/skills/<name>/SKILL.md`、`.claude/skills/<name>/SKILL.md` 和 `<plugin>/skills/<name>/SKILL.md`。
2. Claude Code 声明兼容 Agent Skills 公共格式，并增加调用控制、工具权限、子 Agent、动态上下文等扩展字段。
3. `disable-model-invocation: true` 会阻止 Claude 自动调用 Skill，同时保留用户通过 `/name` 显式调用。
4. Plugin Skill 使用 `plugin-name:skill-name` 命名空间；普通个人或项目 Skill 不带 Plugin 前缀。
5. Claude Plugin 可有 `.claude-plugin/plugin.json`；该 manifest 当前是可选的，因为默认目录可以自动发现，但它可明确身份、版本和组件。
6. Claude Plugin 的 `skills/`、`agents/`、`hooks/`、脚本和其他组件位于 Plugin 根目录，只有 `plugin.json` 位于 `.claude-plugin/`。
7. Claude Marketplace 使用仓根下的 `.claude-plugin/marketplace.json`，支持相对 Plugin 路径、GitHub、Git URL、git-subdir 和 npm 来源。
8. Claude 把安装后的 Plugin 复制到 `~/.claude/plugins/cache`。安装包不能通过 `../` 依赖 Plugin 根外的文件；外部 symlink 也会被限制或跳过。
9. Claude CLI 提供 `claude plugin validate <path>`，能校验 Marketplace、Plugin manifest、Skill frontmatter 和部分组件文件。
10. Claude CLI 还提供 `plugin details`、`list`、`install`、`uninstall`、`update` 和 `eval`；`eval` 能比较带 Plugin 与不带 Plugin 的结果。
11. Claude 文档把 Skill 触发和 Skill 输出质量分成两类验证，并要求用新 Session 避免编写上下文掩盖缺陷。

## 共同面与差异面

| 对象 | 共同事实 | Codex 差异 | Claude 差异 |
| --- | --- | --- | --- |
| 方法正文 | 都能读取 `skills/<name>/SKILL.md` 及其相对资源 | 可用 `$name` 显式调用；初始 Skill 列表有上下文预算 | 可用 `/name`；Plugin Skill 有命名空间 |
| 隐式调用控制 | 两端都能表达“只显式调用” | `agents/openai.yaml` 中 `allow_implicit_invocation: false` | `SKILL.md` frontmatter 中 `disable-model-invocation: true` |
| Plugin manifest | 都把 Provider manifest 放在各自点目录 | `.codex-plugin/plugin.json` 必需 | `.claude-plugin/plugin.json` 当前可选 |
| Skill 目录 | Plugin 根下 `skills/` 都是原生位置 | manifest 可用 `skills: "./skills/"` 指向 | 默认扫描 `skills/`，也可由 manifest 指向 |
| Marketplace | 都支持 Git 仓与同仓相对路径 | 当前首选 `.agents/plugins/marketplace.json` | `.claude-plugin/marketplace.json` |
| 安装结果 | 两端都把安装包复制到用户缓存 | `~/.codex/plugins/cache/...` | `~/.claude/plugins/cache/...` |
| 原生校验 | 公共 Skill 可用 `skills-ref` | 当前 CLI 无 `plugin validate` | `claude plugin validate` 与 `plugin eval` |

官方文档没有证明一个完全相同的 Marketplace JSON 能同时满足两端当前 Schema。OpenAI 能读取 `.claude-plugin/marketplace.json` 这个位置，并不等于两个 Marketplace Schema 的全部字段与语义相同。

## `grilling` 冻结上游事实

固定基线：

- 仓库：[`mattpocock/skills`](https://github.com/mattpocock/skills)
- 提交：`84fdeffd12f2ee307994d1eb6feb48173b6e0502`
- 提交时间：2026-08-06T19:49:51Z
- 根许可证：MIT，Copyright (c) 2026 Matt Pocock
- `grilling` 目录：[`skills/productivity/grilling`](https://github.com/mattpocock/skills/tree/84fdeffd12f2ee307994d1eb6feb48173b6e0502/skills/productivity/grilling)

冻结目录只包含：

| 文件 | Git blob | 字节 |
| --- | --- | ---: |
| `SKILL.md` | `95bd01ee9049a7e08120d54af9cd6ceeef282335` | 1872 |
| `agents/openai.yaml` | `ddbdb96139c0c1dfe6bca698f39d0465674b8a39` | 113 |

没有 `scripts/`、`references/`、`assets/` 或其他 Skill 依赖。`grill-me` 是另一个目录；其正文只有“Run a `/grilling` session”，并带 Claude 的 `disable-model-invocation: true`。当前产品范围排除了这个路由别名。

`grilling` 正文本身的行为事实：

- 用“设计树、前沿、分轮”组织问题。
- 每轮询问当前前置决定已经解决的全部问题，而不是固定一次一个问题。
- 要求 Agent 自己查事实、用户做决定。
- 要求共同理解确认前不执行。
- 对事实调查写死了“dispatch a sub-agent”。这依赖宿主是否提供子 Agent，并不只是公共 Agent Skills 语义。
- 没有普通路径、进入前成本提示、拒绝后抑制、降级、换方法或退出规则。
- `SKILL.md` 没有 `disable-model-invocation: true`；`agents/openai.yaml` 也没有 `allow_implicit_invocation: false`。按两个 Provider 的默认合同，它可以被模型隐式调用。

因此，冻结上游与本地产品合同有共同部分，也存在可逐项指出的行为差异；二者不是同一份权威。

## 本机当前状态

- 运行环境：原生 Windows。
- Codex CLI：`0.147.0`。
- Claude Code：`2.1.221`。
- `~/.agents/skills/grilling/SKILL.md` 不存在。
- `~/.claude/skills/grilling/SKILL.md` 与 `~/.claude/skills/grill-me/SKILL.md` 不存在。
- Codex 当前登记三个 Marketplace：`openai-primary-runtime`、`openai-bundled`、`codex-marketplace`。
- Claude 当前登记 `claude-plugins-official` 与 `compound-engineering-plugin`；已安装的两个 Plugin 中没有 `grilling`。
- `.claude/jobs/.../tmp/.../grill-me` 下存在一次旧 job 的临时测试文件，但它不是个人 Skill 路径或已安装 Plugin 缓存。
- 当前可调用 Skill 清单中没有 `grilling` 或 `grill-me`。

这表示后续可以从“未安装”状态验证安装和卸载，不需要先覆盖一个现有生产版本。

## 可验证表面

当前合同和工具暴露出以下可观察面：

- 公共格式：`SKILL.md` 名称、描述、相对引用和可选许可证 / 兼容性字段。
- 来源完整性：上游提交、树、blob、许可证文本和本地修改能够逐项比对。
- 包完整性：安装缓存中的 Skill、Provider manifest、许可证与来源记录能否在没有仓外文件时工作。
- 调用策略：分别验证“宿主硬性命令入口”与“模型可加载 Skill、但只能在可观察同意后开始问询”两种实现；Provider 开关是机制证据，不等于产品授权证据。
- 行为语义：直接请求、接受建议、普通复杂任务、拒绝建议、命令回退、进入前成本、事实 / 决定分工、依赖顺序、确认门槛、降级 / 换方法 / 退出是否可从各 Provider 的新 Session 观察。
- 生命周期：Marketplace 添加、Plugin 安装、版本识别、禁用 / 卸载、缓存清理和回滚。
- Provider 工具：Claude 有原生 validate / eval；Codex 当前只有安装与列表命令，因此静态 Schema 校验与安装烟雾验证是不同问题。

## 仍未知

1. 同一 Plugin 根同时包含两个 Provider manifest 时，当前 Codex 0.147.0 与 Claude 2.1.221 是否都能完整安装和卸载。
2. 两端是否应共享同一 Marketplace 文件，还是只共享 Plugin 目录；当前官方文档不足以证明 Schema 完全兼容。
3. `grilling` 的共同正文需要改到什么程度，才能满足产品合同而不把 Provider 特有能力写进公共方法。
4. Codex 缺少 `plugin validate` 时，最小可信替代验证由哪些静态检查和安装烟雾组成。
5. 固定版本使用显式版本号、Git commit、tag 或组合时，两端更新和回滚行为的实测差异。
6. 一次本机双 Provider 验证能否代表 WSL；父事项已经把 WSL 留作后续独立环境切片。
7. 真实任务中方法收益、Token、耗时和打断成本尚未产生数据，本阶段不能声称投入产出比成立。
8. 两个 Provider 的模型调用在真实新 Session 中，能否稳定区分“同意”与“只是任务复杂”；若不能，是否需要对该 Provider 回退到硬命令入口。

## Research 事实摘要

- 跨 Provider 的公共核心确实存在：`SKILL.md` 与同目录资源。
- 当前单一上游 `grilling` 的实际文件闭包只有两个文件，没有脚本或其他 Skill 依赖。
- 两端真正需要区别处理的是调用政策、Provider manifest、Marketplace、缓存和验证工具。
- 当前上游不是可直接声明合规的成品：它允许模型按描述触发却没有“问询前须有可观察同意”的守卫，写死子 Agent，并缺少产品合同中的普通出口与降级规则。允许模型加载本身不是违规，未经同意开始问询才是。
- 当前本机没有安装 `grilling`，后续生命周期验证有干净起点。
- Marketplace 是否共享、是否需要生成投影、版本模型和 Codex 校验替代仍需 Options 比较，Research 不作选择。
