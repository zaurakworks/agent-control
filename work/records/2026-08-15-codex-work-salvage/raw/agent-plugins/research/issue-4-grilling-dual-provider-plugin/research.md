# Issue #4 Research：`grilling` 双运行端 Plugin

检查时间：2026-08-08（America/New_York）

## 范围

本阶段只核验 Issue #4 的仓库现状、固定上游、公共 Skill 合同、Codex / Claude 当前 Plugin 合同、本机命令面、状态写入和验证边界。不选择资产布局，不写实施步骤，不修改仓库来源文件或用户配置。

## 已读仓库与产品合同

- 仓库默认分支当前只有 `README.md`、`docs/asset-model.md`、`docs/conformance.md`；没有 Plugin、Marketplace、Schema、生成器、Lint、测试框架或仓库级 `AGENTS.md` / `CLAUDE.md`。
- `docs/asset-model.md` 已确定：共同方法正文只有一个可编辑来源；Provider 包装、安装和验证差异必须分开；物理目录只是待验证候选。
- `docs/conformance.md` 已把来源、公共格式、Codex、Claude、生命周期、行为和投入产出证据分层；本 Issue 不能用低层通过证明方法 ROI。
- `agent-system-foundry/product/method-intervention.md` 规定：直接请求或明确接受建议才允许进入方法；复杂度、关键词和 Agent 判断本身不是同意；拒绝后同一理由不能重提；方法可以降级、替换或退出；实施前要用人话确认共同理解。
- Issue #4 是父 Issue #1 的开放子项；前置 #2 已关闭。当前 framing Challenge 为受信任的 `proceed`。

## 固定上游事实

固定提交：[`mattpocock/skills@84fdeffd12f2ee307994d1eb6feb48173b6e0502`](https://github.com/mattpocock/skills/commit/84fdeffd12f2ee307994d1eb6feb48173b6e0502)，提交时间 `2026-08-06T19:49:51Z`。

| 文件 | Git blob | 字节 | SHA-256 |
| --- | --- | ---: | --- |
| `skills/productivity/grilling/SKILL.md` | `95bd01ee9049a7e08120d54af9cd6ceeef282335` | 1872 | `FA5C1E5EE76B1C8F1AE56101F52C9E239DE75D5C578ADC61227B92D10B7E52EF` |
| `skills/productivity/grilling/agents/openai.yaml` | `ddbdb96139c0c1dfe6bca698f39d0465674b8a39` | 113 | `1411D7DF7D99B7E621A1FF8283C8133CC2464BE63D064E52D8CE169C6800EE9B` |
| `LICENSE` | `f1dd2c09108dde1a5f56097cee8461b3ea834499` | 1068 | `0E7AC423BF2C6E223B7C5B156F8CF72DA49D748E56A1641402C31F22AD07DBB5` |

上游许可证是 MIT，Copyright 2026 Matt Pocock。许可证要求分发副本或实质部分时保留版权和许可声明。

上游 `SKILL.md` 的可观察语义：

- `name` 为 `grilling`；description 以用户要求压力测试或使用 grill 触发词为主要匹配条件。
- 以 design tree、frontier 和 rounds 组织问题；同一轮可以询问前置决定已经完成的多个独立问题。
- 每题给 Agent 推荐答案，并等待用户回答后再扩展依赖分支。
- 把事实查找交给 Agent，但写死“派发子 Agent”且要求不阻塞其他独立问题。
- 在用户确认共同理解前不得开始行动。
- 没有规定问询前的可观察同意、普通出口、建议成本、拒绝后抑制、降级 / 换方法 / 退出和人话交接。

上游 `agents/openai.yaml` 只有 `interface.display_name` 与 `interface.short_description`，没有 `policy`。因此它没有显式锁定 Codex 调用策略。

## Agent Skills 公共合同

[Agent Skills Specification](https://agentskills.io/specification) 当前要求每个 Skill 至少有 `SKILL.md`，并要求 `name` 与 `description`；`name` 必须与父目录一致。公共 frontmatter 还定义可选 `license`、`compatibility`、`metadata` 和实验性 `allowed-tools`。其他文件目录允许存在，但 Provider 支持程度不由公共规范保证。

规范链接的 `skills-ref` 是演示用 Python 参考实现，当前本机未安装；其 README 明确说不用于生产。`uvx`、Python、Node 和 `npx` 可用，但仓库当前没有批准任何新验证依赖。

## Codex 当前合同与本机命令面

官方 OpenAI 文档：

- [Package your plugin](https://developers.openai.com/plugins/build/plugins)
- [Build plugins](https://learn.chatgpt.com/docs/build-plugins)
- [Build skills：Optional metadata](https://learn.chatgpt.com/docs/build-skills#optional-metadata)

已核验事实：

- Plugin 必须在根目录包含 `.codex-plugin/plugin.json`；Skill 放在根目录 `skills/<name>/SKILL.md`。
- `.codex-plugin/plugin.json` 的组件路径从 Plugin 根解析、以 `./` 开头且不能逃出根目录。
- 仓级 Marketplace 的当前主路径是 `.agents/plugins/marketplace.json`；OpenAI 运行端也兼容读取仓级 `.claude-plugin/marketplace.json`，但这只是读取位置兼容，不证明两个 Marketplace Schema 相同。
- Marketplace `source.path` 相对 Marketplace 根解析。安装后由缓存副本运行，而不是直接运行来源目录；启用状态写入 Codex 配置。
- `agents/openai.yaml` 的 `policy.allow_implicit_invocation` 默认是 `true`；设为 `false` 时，Codex 不会按用户提示隐式调用，但显式 `$skill` 仍可用。
- 当前官方构建文档要求在新会话中用代表性请求测试 Plugin。

本机 Codex CLI 是 `0.147.0`：

- `codex plugin` 提供 `add`、`list`、`remove` 与 `marketplace add/list/upgrade/remove`。
- `codex plugin add` 和 `remove` 支持 JSON 输出；`marketplace add` 支持本地路径、Git 来源、固定 `--ref` 和稀疏路径。
- 当前 CLI 没有 `plugin validate` 子命令。
- 当前真实配置有三个 Marketplace 与多个已启用 Plugin；没有 `grilling`。
- 预先建立一个空的独立 `CODEX_HOME` 后，`plugin marketplace list` 和 `plugin list` 都能在空状态运行且不读取现有 Plugin；该独立根没有现有登录。
- `codex exec --ignore-user-config` 仍从 `CODEX_HOME` 取得认证；当前环境没有 `OPENAI_API_KEY`。因此“独立 Plugin 根 + 现有认证”的 Codex 行为测试路径尚未得到证据。

## Claude 当前合同与本机命令面

Anthropic 官方文档：

- [Create plugins](https://code.claude.com/docs/en/plugins)
- [Plugins reference](https://code.claude.com/docs/en/plugins-reference)
- [Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [Create a plugin marketplace](https://code.claude.com/docs/en/plugin-marketplaces)
- [Environment variables](https://code.claude.com/docs/en/env-vars)

已核验事实：

- Claude Plugin 的 manifest 位于 `.claude-plugin/plugin.json`；如果存在 manifest，只有 `name` 必填。Skill 位于 Plugin 根的 `skills/<name>/SKILL.md`。
- Plugin Skill 始终带 Plugin 命名空间；名为 `grilling` 的 Plugin 中名为 `grilling` 的 Skill，其官方示例规则对应 `/grilling:grilling`，不能把 `/grilling` 记录成既成事实。
- Claude 默认允许用户和模型调用 Skill。`disable-model-invocation: true` 才把 Skill 隐藏到只能由用户显式调用；本地产品已经批准首次实验保留模型调用能力。
- `claude --plugin-dir <path>` 可以只在当前会话旁加载一个未安装 Plugin；Marketplace 安装则复制到缓存。
- Claude Marketplace 主文件是仓根 `.claude-plugin/marketplace.json`。安装后按 Marketplace、Plugin 和版本保存独立缓存目录；旧版本在更新后约保留 14 天再清理。
- `claude plugin validate <path> --strict` 能校验 manifest、Skill frontmatter 与相关组件；严格模式把未知字段警告升级为失败。
- `claude plugin install` 支持 `user`、`project`、`local` 三种 scope；卸载默认删除最后 scope 对应的持久数据，可用 `--keep-data` 保留。
- `CLAUDE_CONFIG_DIR` 能整体替换配置、会话与 Plugin 根；`CLAUDE_CODE_PLUGIN_CACHE_DIR` 能单独替换 Plugin 根。

本机 Claude Code 是 `2.1.221`：

- CLI 提供 `plugin validate`、`install`、`list`、`update`、`uninstall`、`marketplace`、`details`、`eval` 和 `--plugin-dir`。
- 真实用户配置当前有两个 Marketplace、两个已安装 Plugin；没有 `grilling`。
- 空的独立 `CLAUDE_CONFIG_DIR` 能得到空 Marketplace 与空 Plugin 状态，但没有现有登录；当前环境没有 `ANTHROPIC_API_KEY`。
- 用正常认证配合 `--plugin-dir` 可以避免安装状态写入，但会继续处在真实用户配置边界内；怎样排除其他用户级规则和 Skill 的干扰仍需运行验证。

## 两端不能互相代替的证据

| 问题 | Codex | Claude |
| --- | --- | --- |
| Plugin manifest | `.codex-plugin/plugin.json` | `.claude-plugin/plugin.json` |
| Marketplace 主路径 | `.agents/plugins/marketplace.json` | `.claude-plugin/marketplace.json` |
| 模型调用控制 | `agents/openai.yaml` | `SKILL.md` frontmatter |
| 显式调用 | 官方合同为 `$skill`；Plugin 后的实际显示仍需观察 | Plugin Skill 必然是 `/plugin:skill` |
| 静态原生校验 | 当前无 `plugin validate` | `claude plugin validate --strict` |
| 未安装旁加载 | 当前 CLI 未提供等价入口 | `--plugin-dir` |
| 独立完整配置根 | `CODEX_HOME`，同时隔离认证 | `CLAUDE_CONFIG_DIR`，同时隔离认证 |

因此：一个 Provider 的格式、安装或行为通过，不能作为另一个 Provider 的证据；目录名相似也不能证明 Schema 相同。

## 状态写入与安全边界

- 两个 Provider 的 Marketplace 安装都会写配置和缓存。空独立根可隔离这些写入，但也同时隔离当前登录。
- Claude 的 `--plugin-dir` 是当前已知的无安装行为测试入口；Codex 当前没有对应命令证据。
- 本 Plugin 预期只有说明性 Skill，不需要脚本、Hook、MCP、LSP 或持久数据。加入这些能力会扩大信任与清理范围，但当前需求没有提供依据。
- Issue #4 的规划授权不是修改真实用户配置的授权。若 Codex 行为测试不能在保留认证的同时隔离 Plugin 状态，实施必须在该写入前停止并单独请求授权。

## 可验证表面

1. 来源：提交、路径、Git blob、字节、SHA-256、许可证和本地差异。
2. 公共 Skill：目录名、必填 frontmatter、正文与相对资源。
3. Codex：manifest 与 Marketplace JSON、路径、独立根安装 / 列表 / 移除、缓存比对、显式与隐式行为。
4. Claude：`validate --strict`、Marketplace 与安装 / 列表 / 卸载、缓存比对、`--plugin-dir` 与安装版本行为。
5. 生命周期：安装前、安装后、移除后和恢复目标；首次正式版本没有天然的“前一正式版本”。
6. 产品行为：直接请求、建议后接受、普通或仅复杂任务、拒绝建议、手动入口、降级 / 退出和实施前确认。
7. ROI：本 Issue 只能记录低成本运行数据，不能得出真实任务收益结论。

## 仍未知

- 同一个 Plugin 根同时包含两个 manifest 时，当前两个 CLI 是否都完整接受，严格校验是否出现 Provider 文件警告。
- 两个 Marketplace 文件指向同一 Plugin 根时，各自的真实发现、版本和缓存身份。
- Codex 安装后的显式 Skill 名称与用户界面显示；是否出现 Plugin 命名空间。
- Codex 在不复制认证材料、不修改现有配置的前提下能否运行已隔离安装的 Plugin 行为会话。
- Claude 用正常认证与 `--plugin-dir` 时，怎样低成本排除其他用户级规则和 Skill 对行为结果的影响。
- 允许模型调用后，两端能否稳定做到“加载不等于开始问询”，以及拒绝后是否在同一会话中保持抑制。
- 共同 `SKILL.md` 的本地改造边界和首次发布的具体回滚目标。
