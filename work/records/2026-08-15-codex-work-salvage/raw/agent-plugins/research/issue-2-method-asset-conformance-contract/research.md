# Research：B1 最小方法资产与 conformance 合同

## 研究标识

- Issue：[`Eridanus117/agent-plugins#2`](https://github.com/Eridanus117/agent-plugins/issues/2)
- 父事项：[`Eridanus117/agent-plugins#1`](https://github.com/Eridanus117/agent-plugins/issues/1)
- 时间：2026-08-08（America/New_York）
- 范围：只核对 B1 三份文档需要承载的事实、决定与未知，不设计或实现 Plugin

## 已读取的仓库指导与输入

- 当前仓 `main`：`795700e`，只有 `README.md`。
- 仓内没有 `AGENTS.md`、`CLAUDE.md`、`CONTRIBUTING.md`、构建、Lint、测试或既有 docs 结构。
- 当前 README 只有仓名和一句 “Cross-provider plugin and skill marketplace for Codex and Claude.”
- [`agent-system-foundry/product/method-intervention.md`](https://github.com/Eridanus117/agent-system-foundry/blob/main/product/method-intervention.md)
- [`agent-system-foundry/product/method-intervention-scenarios.md`](https://github.com/Eridanus117/agent-system-foundry/blob/main/product/method-intervention-scenarios.md)
- 父事项 #1 当前 body、修订后的 Research / Options / Plan 与 `plan:proceed` Challenge
- Issue #2 当前 body 与 `framing:proceed` Challenge

旧 Orrery、旧 Marketplace、`agent-workbench` 与本 Issue 之前的旧设计不拥有本仓架构权威。

## 已批准的产品输入

方法介入合同已经确定：

- 普通任务是一条完整、长期有效的路径，不是临时跳过正确流程。
- 新任务只做一次轻量路径选择；用户选择前不能展开方法问卷。
- 用户直接点名方法，或在 Agent 建议后明确接受，都构成进入方法的同意。
- 任务复杂、命中关键词或 Agent 判断方法有帮助，不构成同意。
- 普通路径中只有出现会实质改变风险、成本、范围或结果的新证据时，才可提出一次升级建议。
- 升级建议需要包含新情况、影响、建议、成本和普通出口；拒绝后同一理由不能重复建议。
- 方法开始后仍可降级、换方法或退出，并保留原任务和已确认内容。
- 能由 Agent 查明的事实不转嫁给用户；依赖用户决定的实现要等共同理解确认。

本轮对话新增并批准的调用输入：

- 首次试验允许 Agent 自动调用 / 加载 `grilling`。
- 自动调用不等于自动进入问询；问询仍受上述同意门禁约束。
- 手动 `/grilling`、`$grilling` 入口保留。
- `grilling` 与负责人期待的完整“升级思考”存在差距；它是第一个试验样本，不是最终方法产品或唯一未来方法。

## Provider 调用事实

- OpenAI Docs 当前说明 Codex 支持显式与隐式调用；`policy.allow_implicit_invocation` 默认是 `true`，设置为 `false` 才禁止根据描述隐式调用。
- Claude Code 当前默认允许用户和 Claude 调用 Skill；`disable-model-invocation: true` 会把 Skill 从 Claude 的可调用范围隐藏，只保留用户命令入口。
- 两端都保留用户直接调用能力。
- Provider 配置只证明宿主是否允许模型加载 Skill，不能证明模型是否遵守产品层的同意、拒绝抑制、降级或退出合同。
- 父事项把真实 Provider 配置、安装与新 Session 行为试验留给 C1；B1 不修改配置。

## B1 必须表达的对象

父事项已经区分九类对象：

| 对象 | 已确认责任边界 |
| --- | --- |
| 产品合同 | 规定用户可见行为和路径切换，不规定包目录 |
| 共同 Skill | 承载方法步骤和行为语义，不拥有 Provider 安装状态 |
| Provider 元数据 | 表达调用、显示、依赖和宿主差异，不判断用户是否已经同意 |
| Plugin manifest | 表达安装单元身份、版本和组件入口，不成为产品合同 |
| Marketplace | 负责发现、来源定位和安装政策，不拥有 Plugin 内容 |
| 来源记录 | 保存上游坐标、许可证和本地修改，不自动证明改造正确 |
| Conformance | 保存分层证据，不自动证明方法收益 |
| 安装缓存 / 用户配置 | 是派生运行状态，不是可编辑或跨 Host 权威 |
| GitHub Issue | 保存目标、决定、依赖与证据链接，不是可执行资产或可信知识本体 |

共同方法正文只保存一次是父事项已经选择的逻辑不变量。同一 Plugin 根、双 manifest、Marketplace 共享 / 分离和 Provider frontmatter 兼容性仍是 C1 的物理实验项。

## 证据层级事实

B1 需要防止以下证据越权：

- 来源 commit、blob 与许可证匹配，只证明来源完整性。
- `SKILL.md` 公共格式通过，只证明公共格式。
- Provider manifest / validator / 安装通过，只证明对应宿主能够解析或安装。
- 缓存哈希匹配，只证明安装副本与所选包一致。
- 新 Session 场景通过，才支持直接请求、接受建议、普通路径、拒绝抑制、命令回退、降级和退出等行为结论。
- 真实任务中的收益、打断成本、时间与 Token 数据，才可能支持 ROI 判断。

低层证据不能替代更高层证据。`grilling` 的三个合同验收场景通过也只证明行为表述完整、可观察，不证明它优于普通路径或等于完整“升级思考”。

## 当前物理候选与未证明项

父事项当前候选为一个自包含目录，包含一个共同 `skills/grilling/SKILL.md`、Codex / Claude 的薄 manifest、Codex 元数据、来源记录和许可证。

下列内容尚未证明：

1. 同一 Plugin 根能否被当前 Codex 与 Claude 完整安装、卸载和回滚。
2. Claude 扩展 frontmatter 是否被 Codex 安全接受。
3. Marketplace 应共享还是分开，以及两个发现位置是否产生重复。
4. 允许模型自动调用后，两端能否稳定做到“先建议、有同意才问询”。
5. Codex 缺少原生 Plugin validator 时，哪些静态与安装证据足够。
6. `grilling` 的真实收益、打断成本和与完整“升级思考”的差距有多大。
7. 原生 Windows 的结果能否代表 WSL 或其他 Host。

## B1 文件与可验证表面

Issue #2 把交付面固定为：

- `README.md`：仓库定位、当前阶段、文档入口和后续切片；
- `docs/asset-model.md`：逻辑 ownership、单正文不变量、已确认 / 待实验边界和升级条件；
- `docs/conformance.md`：证据层级、C1 最小场景、失败回退与验证权限。

当前仓没有 Markdown Lint 或链接检查器。可直接使用的低成本检查只有：

- `git diff --check`；
- `git diff --name-only` 验证精确三文件范围；
- 对三个 Markdown 文件中的相对链接做存在性核对；
- 人工检查术语、ownership、已确认 / 未证明状态和证据权限是否一致；
- 用一个不读取旧仓的 Session 只读三份文件，复述 C1 未知、场景和回退。

## 约束与非目标

- B1 不创建 Skill、Plugin manifest、Marketplace、Schema、脚本、语言、Lint、Hook、MCP 或用户配置。
- B1 不安装或运行 `grilling`，不修改 Codex / Claude 调用设置。
- B1 不把 `grilling` 命名为最终“升级思考”，也不决定最终方法集合。
- B1 不建立知识格式、知识图谱、通用 Plugin 平台、遥测或上游自动同步。
- B1 不把候选目录、配置默认值、安装行为或 ROI 写成已经验证。

## Research 事实摘要

- 当前仓没有可继承的文档或实现体系，B1 的三文件合同将成为 C1 的第一个仓内边界。
- 自动调用已被批准为首次试验输入，但自动进入问询仍被产品合同禁止；两者必须在文档中分开。
- `grilling` 只是首个试验样本，与期待的完整“升级思考”有已知差距。
- 逻辑 ownership 与单正文不变量已确定；物理 Plugin、Marketplace、调用可靠性和 ROI 尚未证明。
- B1 的验证只能证明文档边界完整、一致、可交接，不能证明 Provider 行为或方法价值。
