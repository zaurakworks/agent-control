# Plan：用 `grilling` 建立最小跨 Provider 资产闭环

## 目标

在 `agent-plugins` 中建立一条可撤销的最小交付链：先冻结资产责任与验证合同，再纳入并改造 `grilling`，最后基于一次手工上游回顾决定是否值得自动化。

本 Plan 选择“一个自包含双 Provider Plugin、共同正文只存一次”作为当前方向。它不把未验证的目录兼容性写成既成事实；双 manifest 与 Marketplace 的物理可行性是首个实现门禁，失败时退到生成两个完整 Provider 包。

## 选择理由

- 当前只有一个 1872 字节的共同正文，没有事实支持先建设生成平台。
- Codex 与 Claude 都原生读取 Plugin 根下的 `skills/<name>/SKILL.md`，共同正文只存一次具有直接合同依据。
- Provider 差异集中在 manifest、调用机制、Marketplace 和验证命令，可以保持很薄且可观察；“用户明确同意”与“必须输入命令”不再混为一谈。
- 一个自包含目录可以被 Git 固定、复制到 Provider 缓存并按版本回滚。
- 与整仓 Fork 相比，只纳入获批的两个上游文件能显著减少无关上游噪声。
- 如果未来第二个真实资产暴露稳定重复，再升级到生成模型仍然可逆；现在提前生成会增加语言、产物和 Agent 判断成本。

## 逻辑资产模型

无论最终物理目录实验结果如何，以下角色固定：

| 对象 | 权威责任 | 不能取得的责任 |
| --- | --- | --- |
| 共同 Skill | 方法步骤、事实 / 决定分工、确认与退出语义 | Provider 安装、Marketplace 和用户启用状态 |
| Provider 元数据 | 调用机制、宿主显示、Provider 依赖与真实差异 | 决定用户是否已经同意，或复制共同正文 |
| Plugin manifest | 安装单元身份、版本、组件入口与许可展示 | 成为方法产品合同 |
| Marketplace | 发现、来源定位和安装政策 | 成为 Plugin 内容权威 |
| 来源记录 | 上游仓、提交、路径、blob、许可证、作者和本地修改 | 自动证明本地改造正确 |
| Conformance | 静态格式、包完整性、调用与生命周期证据 | 自动证明方法 ROI |
| 安装缓存 | 某个 Provider 的派生运行副本 | 成为可编辑来源或跨 Host 权威 |
| 用户配置 | Marketplace 登记和启用状态 | 存放唯一资产正文 |
| GitHub Issue | 当前目标、决定、依赖和证据链接 | 成为可执行包或可信知识 |

## 候选安装单元

当前物理候选为：

```text
plugins/grilling/
├── .codex-plugin/
│   └── plugin.json
├── .claude-plugin/
│   └── plugin.json
├── skills/
│   └── grilling/
│       ├── SKILL.md
│       └── agents/
│           └── openai.yaml
├── LICENSES/
│   └── mattpocock-skills-MIT.txt
└── UPSTREAM.md
```

规则：

- `skills/grilling/SKILL.md` 是唯一共同正文。
- 产品不变量是：用户直接请求，或在 Agent 建议后明确接受，才允许开始问询；复杂度、关键词和 Agent 判断都不算同意。
- `/grilling` 与 `$grilling` 是可靠入口和回退，不是共同合同强制的唯一入口。
- Claude 的 `disable-model-invocation` 与 Codex 的 `allow_implicit_invocation` 是 C1 要比较的 Provider 机制；若同意感知的模型调用不能稳定通过场景，才对失败的 Provider 回退到硬命令入口。
- 两个 Plugin manifest 只表达 Provider 包装，不复制方法正文。
- `UPSTREAM.md` 记录冻结提交、纳入路径与 blob、本地修改和回顾时间；完整 MIT 文本随包保存。
- 安装单元不能通过 `..`、绝对路径或宿主缓存引用仓外文件。
- `.agents/plugins/marketplace.json` 与 `.claude-plugin/marketplace.json` 是待验证的发现投影，不先宣布必须共享或必须分开。

## 交付切片

本 Issue 是规划父事项，不能由一个 PR 实施。依赖顺序为 `B1 → C1 → D1`。

### B1 — 资产合同与 conformance 边界（下一个 PR）

目的：把本 Plan 中已经有证据的逻辑边界变成仓内可审查合同，不纳入或安装 `grilling`。

预计变更：

1. `README.md`
   - 用人话说明本仓负责来源、包装、安装、验证和回滚。
   - 链接产品合同与本仓两个资产文档。
   - 明确旧 Marketplace 和旧仓没有默认权威。
2. `docs/asset-model.md`
   - 写清上表中的对象、ownership、单正文不变量、Provider 差异与候选目录。
   - 区分用户授权语义与 Provider 调用机制：自然语言直接请求 / 接受建议可构成同意，硬命令只是可靠入口与回退。
   - 区分已确认逻辑合同和仍需实验的物理目录。
   - 写清何时才需要生成器、第二个仓或整仓 Fork。
3. `docs/conformance.md`
   - 定义来源、公共 Skill、Codex、Claude、安装缓存、卸载 / 回滚六类证据。
   - 区分静态格式通过、Provider 安装通过、产品场景通过和 ROI 通过，禁止低层结果越权。
   - 定义实验失败后的降级：双根失败则比较生成双包；Marketplace 共享失败则保留 Provider 投影。

验证：Markdown 相对链接、合同所需角色与六类证据检查、精确三文件范围、`git diff --check`。不增加 Schema、语言、Lint、生成器或 Provider 配置。

完成门槛：一个新 Session 不读取旧仓也能说明什么只存一次、什么必须分开、什么还没有被证明，以及 C1 需要验证哪些门禁。

### C1 — `grilling` 自有派生与双 Provider 包

前置：B1 合并，并为 C1 建立独立 Issue、Research、Options、Plan、Plan Challenge 和实施批准。

职责：

1. 以固定提交 `84fdeffd...` 为来源，只纳入 `grilling/SKILL.md`、`agents/openai.yaml` 和适用 MIT 许可证。
2. 按 `agent-system-foundry` 产品合同改造共同正文；逐项记录上游与本地差异，不把改造伪装为上游原文。
3. 建立两个薄 Provider manifest；先验证同意感知的模型调用，不把两端关闭模型调用预设为共同答案。
4. 用最小临时实验先验证：
   - 双 manifest 同根；
   - Claude 扩展 frontmatter 是否被 Codex 安全接受；
   - 单 Marketplace 交集能否同时通过；
   - 若不能，两个 Marketplace 投影是否会在 Codex 中重复发现。
5. 只有实验通过后才冻结 Marketplace 物理结构与各 Provider 的调用机制；若某端不能可靠守住同意边界，则该端回退到硬命令入口并记录额外用户步骤，不修改共同 ownership。
6. 提供版本识别、安装、禁用 / 卸载和回滚说明；所有运行文件在安装单元内自包含。
7. 在不永久改变用户生产配置的隔离范围验证 Codex 与 Claude；若当前 CLI 无法隔离，停止并向负责人请求一次明确的可恢复配置试验授权。

验证门槛：

- 上游 commit / blob / license 精确匹配。
- Agent Skills 公共格式通过。
- `claude plugin validate` 通过。
- Codex 从目标 Marketplace 发现并安装，缓存文件与来源包一致。
- 两端在用户直接请求时进入；Agent 建议且用户明确接受后进入。
- 两端在普通任务或仅仅复杂 / 命中关键词时不开始问询；用户拒绝后不按同一理由重复建议。
- `/grilling` 与 `$grilling` 可作为确定性回退入口；是否关闭模型调用由各 Provider 场景结果决定。
- 两端都跑通关键歧义场景，以及降级 / 退出交接。
- 卸载后不残留启用状态；回滚到前一固定版本可复查。

### D1 — 手工上游回顾与自动化裁决

前置：C1 合并且至少存在一个已验证本地版本。

职责：

1. 手工比较一次上游 `grilling` 路径、相关 Provider 元数据、许可证和本地 patch。
2. 记录实际检查时间、命令 / 网络调用数、需要人判断的差异和是否产生行动。
3. 只在真实数据支持时选择月度自动化；无行动价值时保留手工、降频或停止。
4. 自动化即使建立，也只能创建或更新回顾 Issue，不能自动合并、发布或修改已安装版本。

## 与外部父事项的集成

- B1、C1、D1 的状态分别回链 [`agent-system-foundry#1`](https://github.com/Eridanus117/agent-system-foundry/issues/1)。
- C1 产生的固定版本是后续 Windows / WSL × Codex / Claude 环境验证的输入；C1 本身不决定全局 WSL 迁移。
- 真实任务 ROI 和跨 Session 恢复仍由 `agent-system-foundry` 后续切片验证。
- 任何研究结论在 `knowledge-foundry` 门槛前只能是待晋升候选，不能因本仓保存而成为可信知识。

## 兼容、安装和回滚

- 不覆盖或手工改写用户现有配置文件；优先使用 Provider 原生命令登记、安装、禁用和移除。
- 每次可变试验前记录目标 Marketplace、Plugin、scope、当前版本和配置状态，只触碰本 Issue 明确命名的对象。
- 回滚顺序是：禁用 / 卸载当前 Plugin、移除本 Marketplace 登记、确认缓存与启用状态、重新安装前一固定版本。
- 不删除其他 Marketplace、Plugin、Skill、Hook 或配置。
- Provider 文档或 CLI 与 Plan 不一致时，以当前官方合同和实际只读帮助输出为事实，回到 C1 的 Options，而不是硬套目录。

## 成本与观测边界

首轮只记录能够改变决定的低成本数据：

- 新增并维护的权威文件数；
- 每次上游回顾的相关变更数、所需命令 / 网络调用和人工判断点；
- 安装、验证、卸载是否需要额外手工步骤；
- 两端行为场景是否通过；
- 能取得时记录运行时间与 Token，取得成本过高时保持未知。

不为补齐未知建设遥测服务、数据库或跨 Provider 任务系统。第二个资产出现前，不以“未来可扩展”为由升级生成平台。

## 主要风险与处理

- **双 manifest 同根不兼容**：C1 最先验证；失败后保留共同源，生成两个完整安装包。
- **Marketplace 重复发现或 Schema 冲突**：先测一个交集目录，再测明确分离；任何方案都不得引入两个共同正文。
- **上游改造失去归属**：包内保存完整 MIT、来源 commit / blob 和本地修改说明。
- **Codex 校验能力不足**：公共格式、JSON / 路径静态检查与真实安装缓存比对分开记录，不把 Claude validator 结果冒充 Codex 结果。
- **Skill 误触发或多一步命令成本过高**：把“可观察同意”和“硬命令入口”分开验证；普通复杂任务不得直接问询，接受建议不应无证据地强迫用户再输命令。无法稳定守界的 Provider 才回退到硬命令入口；ROI 留给真实任务验证。
- **文档重新变重**：B1 只提交两个短合同文件；详细日志保留在忽略附件或 Issue 证据链接。

## 当前阻塞与开放问题

- Plan 没有需要负责人现在选择的架构分岔；方案一的失败回退已经定义。
- B1 已获负责人原则批准，尚需建立 PR 级子 Issue并完成该子 Issue 的 Plan Challenge；实现仍需按子 Issue 门禁确认。
- C1 对用户配置的隔离能力尚未验证；若 Provider CLI 不能隔离，必须在执行前单独请求配置试验授权。
- Marketplace 最终物理结构保持为 C1 的实验结论，不在 B1 文档中伪装为事实。

## Definition of Done

本父事项完成需要：

- B1 的资产与 conformance 合同已合并；
- C1 的 `grilling` 包有固定来源、许可、本地差异、两端同意边界与命令回退、安装、卸载和回滚证据；
- D1 至少完成一次手工上游回顾，并用实际成本决定自动化、降频或停止；
- 外部产品父事项获得版本与证据链接，但未被错误关闭；
- 未迁移其他 Plugin、未安装 `grill-me`、未建设通用生成平台，也未越权晋升知识。
