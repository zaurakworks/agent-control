# Issue #4 Plan：纳入 `grilling` 并验证双 Provider Plugin

## 人话结论

本 PR 建一个真实但最小的 `grilling` Plugin：方法正文只写一份，Codex 与 Claude 各有自己的 manifest 和 Marketplace 入口。先在完全隔离的配置根中证明来源、结构、安装、卸载和恢复，再做两端新会话行为验证。

Claude 可以用 `--plugin-dir` 在不安装的情况下先测行为。Codex 的独立 `CODEX_HOME` 会同时失去现有登录；如果实施时仍找不到既保留认证又隔离 Plugin 的官方入口，流程必须停在真实 Codex 配置写入前，请求一次单独授权。没有这次授权或等价安全路径，就不把行为未知的自动调用资产合并。

## 目标与选定方向

选定 `innovate.md` 的 `A + III + V1 + R1`：

- 一个自包含 Plugin 根：`plugins/grilling/`；
- 一个可编辑的共同 `SKILL.md`；
- 两个薄 Provider manifest；
- 两个原生 Marketplace 文件，都指向同一个 Plugin 根；
- 首测两端都允许模型调用，同时保留手动入口；
- 某端守不住同意边界，只收紧该端；
- 首次版本的“回退”只证明恢复测试前状态并重新安装相同固定版本，不冒充旧版本降级测试；
- 双根被真实校验或安装否决时，停止并把“共同源 + 生成双包”带回同一 Issue 重新规划，不临时发明生成语言。

## 明确不做

- 不纳入 `grill-me`、上游其他 Skill、Hook、MCP、LSP、脚本或持久数据。
- 不添加全局 `AGENTS.md` / `CLAUDE.md` 投影，不迁移 WSL，不修改其他 Plugin。
- 不建设 Schema 平台、生成器、通用 Lint、注册服务、遥测或自动上游更新。
- 不用格式、安装、合成场景或一次模型结果宣称真实任务 ROI 成立。
- 不在没有新授权时修改真实 Codex / Claude 用户配置。

## 计划文件树

```text
.agents/
└── plugins/
    └── marketplace.json                 # Codex 原生仓级 Marketplace
.claude-plugin/
└── marketplace.json                     # Claude 原生 Marketplace
plugins/
└── grilling/
    ├── .codex-plugin/
    │   └── plugin.json                  # Codex manifest
    ├── .claude-plugin/
    │   └── plugin.json                  # Claude manifest
    ├── skills/
    │   └── grilling/
    │       ├── SKILL.md                 # 唯一可编辑方法正文
    │       └── agents/
    │           └── openai.yaml          # Codex 显示与调用政策
    ├── LICENSES/
    │   └── mattpocock-skills-MIT.txt
    └── UPSTREAM.md
README.md                                 # 安装状态、真实入口和验证边界
```

若实验支持当前候选，`docs/asset-model.md` 与 `docs/conformance.md` 不重复写结果；只有实验推翻其中的待验证候选或回退语义时才更新对应句子。

## 固定身份与最小字段

- Marketplace 名：`agent-plugins`。
- Plugin 名：`grilling`。
- 初始版本：`0.1.0`。
- 共同 Skill 目录与 name：`grilling`。
- 维护者显示名：`Eridanus117`；不新增个人邮箱。
- 仓库：`https://github.com/Eridanus117/agent-plugins`。
- 许可证标识：`MIT`；完整上游文本放在 Plugin 根 `LICENSES/`。

两个 Marketplace 都不重复声明版本，让安装版本来自各自 manifest。两个 manifest 只放当前运行端能解释且本包实际使用的身份、版本、描述、维护者、仓库、许可证和 `./skills/` 路径；不提前添加图标、Hook、MCP、默认提示或发布门户字段。

Codex Marketplace 使用 `.agents/plugins/marketplace.json` 的当前官方字段：本地 `source.path` 为 `./plugins/grilling`，`policy.installation` 为 `AVAILABLE`，`policy.authentication` 为 `ON_INSTALL`，类别为 `Productivity`。

Claude Marketplace 使用 `.claude-plugin/marketplace.json`，本地 `source` 为 `./plugins/grilling`。它不复制 Codex 的 `policy`，也不依赖 Codex 对 legacy Claude 路径的兼容读取。

## 共同 Skill 的派生合同

### 保留的上游语义

- design tree、依赖和当前可回答的 frontier；
- 相互独立的问题可以同轮出现，依赖未决问题的分支延后；
- 每个问题给 Agent 推荐答案；
- 事实由 Agent 调查，决定由用户作出；
- 未确认共同理解前不实施依赖决定的工作。

### 必须修改或新增

1. **description 进入条件**：只匹配用户直接要求压力测试 / `grilling`，或用户已经明确接受一次使用 `grilling` 的建议。复杂度、关键词或 Agent 觉得有用本身不构成进入许可。
2. **同意守卫**：Skill 被模型加载但当前对话没有直接请求或接受时，不开始问题树；最多给一次简短建议，说明新情况、影响、方法收益、额外成本和普通出口，然后等待选择。
3. **拒绝抑制**：用户选普通路径后停止本方法；同一方法和理由不换措辞重提。只有改变风险、成本、范围或结果的新证据才能重新建议，并说明差异。
4. **事实调查**：删除“必须派发子 Agent”。使用当前环境可用且成本合理的文件、工具、官方来源或子 Agent；只有依赖该事实的分支等待，其他 frontier 可继续。
5. **表达**：跟随用户语言，用普通词解释必要术语；问题编号清楚，不使用内部实验术语描述用户选择。
6. **降级与退出**：收益不足、成本过高、问题已清楚、方法不合适或用户要求停止时，输出已确认决定与未知项，让用户选择普通路径、其他方法或停止，不丢失原任务。
7. **完成与交接**：frontier 为空后先给人话共同理解并请求确认；确认前不实施。确认后把决定、未知、所选路径和原任务交回当前工作流。

`agents/openai.yaml` 保留上游显示元数据，并显式写 `policy.allow_implicit_invocation: true`，把批准的首次试验输入变成可审查配置。Claude 的首次模型调用通过“不写 `disable-model-invocation: true`”表达。

## `UPSTREAM.md` 必备内容

- 上游仓、固定提交、提交时间和原始路径；
- 两个上游文件及 LICENSE 的 Git blob、字节与 SHA-256；
- MIT Copyright 与完整许可证副本路径；
- 上游文件到本地文件的一对一映射；
- “保留 / 修改 / 新增”表，逐项记录上节七类正文改造及 `openai.yaml` 的显式调用政策；
- 本地新建的 manifest / Marketplace 不伪装成上游文件；
- 后续更新只比较已采用路径，人工判定上游变化怎样影响本地改造；不自动合并或覆盖。

## 有序实施任务

### 1. 建立分支与冻结前置状态

- 从已同步的 `main` 建立 Issue #4 独占分支。
- 记录当前提交、Codex / Claude 版本、真实配置中 Marketplace / Plugin 的只读清单，以及 `grilling` 不存在的起点；不读取或发布认证材料。
- 重新下载三个固定上游对象，在内存中复算 blob、字节和 SHA-256。任一不符立即停止，不从 `main` 或最新上游替代冻结输入。

### 2. 写入来源、许可证和唯一共同正文

- 先加入原样 MIT 文本与 `UPSTREAM.md`；再从固定上游生成本地 `SKILL.md` 和 `agents/openai.yaml`。
- 按“保留 / 修改 / 新增”合同改造正文，确保只有 `plugins/grilling/skills/grilling/SKILL.md` 是方法正文。
- 不创建 wrapper Skill、别名、第二份正文或仓外引用。

### 3. 加入两个 manifest 与两个 Marketplace

- 使用上面的固定身份和最小字段；所有路径相对相应根目录并以 `./` 开头。
- 两个 Marketplace 都指向同一 `plugins/grilling`；不得让一个 Marketplace 指向缓存或本机绝对路径。
- manifest 版本和身份必须一致，但不强求两个 JSON 的 Provider 特有字段相同。

### 4. 静态与来源验证

- `git diff --check`。
- 用 PowerShell JSON 解析两个 manifest 和两个 Marketplace；显式检查名称、版本、source、policy、相对路径和目标存在。
- 检查仓库内 `name: grilling` 的共同 `SKILL.md` 只有一份，目录名与 frontmatter 一致。
- 检查 Plugin 根没有绝对路径、`..` 跳出、脚本、Hook、MCP、LSP 或未记录文件。
- 复算许可证字节 / SHA；检查 `UPSTREAM.md` 的三个固定对象与本地映射完整。
- 运行 `claude plugin validate plugins/grilling --strict` 和 `claude plugin validate . --strict`。警告在严格模式下也视为失败，不用“运行时会忽略”放行。

### 5. 在独立配置根验证 Codex 生命周期

在 `codex-work/experiments/issue-4/` 下创建本轮唯一、预先存在且非符号链接的 Codex 根；用任务专用变量保存路径，再把 `CODEX_HOME` 指向它。

按顺序执行并保存结构化结果：

1. `codex plugin marketplace list` 与 `codex plugin list --json`，确认空起点；
2. `codex plugin marketplace add <repo-root> --json`；
3. `codex plugin list --available --json`，确认 `grilling@agent-plugins`、版本与来源；
4. `codex plugin add grilling@agent-plugins --json`；
5. 再次 list，解析实际缓存路径，并比对 manifest、共同 Skill、`openai.yaml`、LICENSE 与 `UPSTREAM.md`；
6. `codex plugin remove grilling@agent-plugins --json` 与 `marketplace remove agent-plugins --json`，确认回到空状态；
7. 重复一次添加、安装、文件比对和移除，证明同一固定版本可恢复；
8. Provider 命令完成清理后，只有在解析后的探针绝对路径仍位于本仓 `codex-work/experiments/issue-4/` 时才删除残留目录。

任何命令触及真实 `CODEX_HOME`、现有 Marketplace 或其他 Plugin 都立即停止并报告，不自动清理不明目标。

### 6. 在独立配置根验证 Claude 生命周期

为 Claude 建立另一个独立、非符号链接根，把 `CLAUDE_CONFIG_DIR` 指向它；`user` scope 在此只表示探针根的用户范围。

按顺序执行：空起点 → `plugin validate --strict` → `plugin marketplace add <repo-root>` → `plugin install grilling@agent-plugins --scope user` → `plugin list/details` 与缓存比对 → `plugin uninstall ... --scope user` → `marketplace remove agent-plugins` → 确认空状态 → 重复安装和清理一次。

缓存比对和残留删除使用与 Codex 相同的路径约束。Claude 旧版本目录约保留 14 天是正常产品行为，但在独立探针根中必须被记录并随整个已验证探针根清理；不能据此删除真实 `~/.claude/plugins`。

### 7. 运行两端五组新会话行为检查

使用合成任务，避免真实工作内容进入证据。每个 Provider 至少五个新会话；需要接受或拒绝的场景在同一会话内继续：

| 会话 | 输入路径 | 必须观察的结果 |
| --- | --- | --- |
| 直接请求 | 用户直接点名 `grilling` | 进入问题树，不重复要求同意；允许退出 |
| 建议后接受 | 有一个会改变产品方向的关键歧义；用户接受一次建议 | 建议先说明影响、收益、成本与普通出口；接受后不再要求命令；最终确认前不实施 |
| 普通 / 只有复杂度 | 清楚、低风险任务，以及一个只是很复杂但没有新证据的任务 | 不展开问卷；普通路径仍完整有效 |
| 建议后拒绝 | 用户拒绝，再用同一理由继续任务 | 继续普通任务，不换措辞重复建议；若提供新证据，重新建议时指出差异 |
| 手动入口与降级 | 使用运行端实际显示的显式入口，再中途要求降级或停止 | 命令可用；交接保留原任务、决定与未知，停止剩余问题 |

Claude 先用正常认证与 `--plugin-dir <plugin-root>`，从无项目规则的空白工作目录启动，并排除可排除的 project / local setting sources；记录仍存在的用户级干扰。旁加载通过不能代替第 6 步的安装证据。

Codex 先检查当前版本是否出现新的会话级 Plugin 入口或 repo Marketplace 的无安装加载证据。若没有，停在这里并向用户展示：拟新增的 Marketplace 名、Plugin 名、预计写入位置、只读事前快照、卸载命令和回退检查。只有获得单独授权后，才在真实已认证 Codex 配置中临时添加本地 Marketplace 与 `grilling`，运行 `codex exec --ephemeral` 新会话，并立即按快照恢复。不得禁用、更新或移除其他 Plugin 来制造隔离。

### 8. 按证据裁决失败，不扩大范围

- **双 manifest 同根失败**：不合并半兼容包；保存失败命令与最短错误，回到 Options B 重新 Plan / Challenge 后再选择生成语言和产物策略。
- **Codex 同意守卫失败**：把 `allow_implicit_invocation` 改为 `false`，记录多一步 `$...` 的成本，重跑 Codex 静态、生命周期和五组行为；Claude 不随之收紧。
- **Claude 同意守卫失败**：先用 `disable-model-invocation: true` 作为 Claude 显式回退并重跑两个 Provider 的公共格式 / 安装检查；若共同文件中的 Provider 扩展被 Codex 或维护边界否决，则触发生成双包重新规划。
- **接受后仍要求第二次命令**：自动调用策略判失败；只可作为该端显式回退，不把它记成自动调用成功。
- **行为结果不稳定**：最多做一次有明确原因的正文修订与完整重跑；仍不稳定则不合并自动调用配置，进入 Plan 修订而不是堆叠提示词。
- **无法取得安全授权**：保持 Issue 等待，不复制认证文件、不降低安全边界，也不以静态检查替代行为证据。

### 9. 更新入口文档并提交可读证据

- 只有实验完成后才更新 `README.md`：仓库从“没有可安装 Plugin”变为何种实际状态、两端真实安装入口、真实命名空间、已验证版本和已知限制。
- Issue / PR 使用两张人话表，不粘贴大段终端日志：
  - `检查对象｜运行端与版本｜操作｜预期｜实际｜结论｜证据位置`；
  - `场景｜用户看到什么｜通过 / 失败 / 未知｜原因与回退`。
- 记录命令数、网络调用、人工判断点、新会话数，以及 CLI 能低成本给出的模型用量；取不到的时间或 Token 写“未知”。
- PR 只关闭 #4，回链父 #1 与外部 `agent-system-foundry#1`，不关闭两个父事项。

## 验证预算与停止条件

预期新增 8 个资产文件，修改 1 个入口 README；不新增工具依赖。首轮最多 10 个行为会话（每端 5 个组合场景），失败修订后最多完整重跑 1 次。生命周期每端做 2 次安装 / 清理循环，用于首次撤销与相同固定版本恢复。

立即停止并返回规划或授权门禁的条件：

- 固定上游哈希不匹配；
- 严格校验或真实安装拒绝双根；
- 命令目标逃出已验证的探针根；
- 将要修改真实配置但没有本次专项授权；
- 清理会触碰其他 Marketplace、Plugin、Hook、设置或缓存；
- 一次有原因的行为修订后仍不能稳定守住同意边界；
- 需要引入生成器、第二份可编辑正文或新的运行环境才能继续。

## 风险与缓解

- **模型行为非确定**：用固定合成场景、新会话、明确通过信号和一次重跑上限，不用继续堆提示词掩盖不稳定。
- **真实配置污染**：生命周期默认独立根；Codex 认证行为测试另设授权停点；前后快照与 Provider 自带 remove 命令优先。
- **Provider Schema 漂移**：记录 CLI 版本和检查时间；两份 Marketplace 使用各自当前官方主路径，不推断交集。
- **上游归因丢失**：固定 commit / blob / SHA、完整 MIT 与逐项本地改造一起进入包。
- **报告难读**：用“普通路径 / 使用 grilling / 显式入口”等用户词汇，不使用“实验臂”、内部 phase 代号或未解释英文缩写。
- **首次回滚过度表述**：只声称恢复事前状态和重新安装同一固定版本；真正跨版本降级等第二个版本出现后验证。

## 完成定义

- 仓内只有一份可编辑 `grilling` 方法正文；来源、许可证和本地改造可逐项复查。
- 两个原生 Marketplace 与两个 manifest 都在各自当前 CLI 上通过严格 / 实际安装检查，并从缓存复核相同共同资产。
- 两端生命周期都从已记录起点安装、移除、恢复同一固定版本并回到清理状态；其他资产无变化。
- 两端五组新会话得到可读结论；自动调用失败的 Provider 已按批准规则单独回退并重新验证。
- Codex 若需要真实配置写入，已有针对本次具体目标的用户授权和完整恢复证据；否则 PR 不进入合并。
- README 只写实际观察到的入口、版本和限制；Issue / PR 不越权宣称 ROI、WSL 或完整“升级思考”成立。
- PR 通过当前头部自审、代码审查和检查门禁，只关闭 Issue #4。

## 实施授权边界

本 Plan 与后续 `plan:proceed` 只证明方案可实施，不自动授权实现。实施需要用户再次明确批准；真实 Codex 配置的临时安装若被触发，还需要在到达该停点时再次说明具体写入并取得专项授权。
