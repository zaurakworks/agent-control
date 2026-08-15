# Plan Phase：自主父目标验收

## 目标与选择

实施已批准的路线 C：在 Agent 系统的高价值完成节点主动触发父目标级验收；由 `adaptive-problem-solving` 统一检查父目标贡献、能力回退、证据等级和负责人可见 ROI；由 `orchestrated-collaboration` 在高价值、多 PR、且协调者参与拆分或设计时要求另一 Agent 做只读父级复核。

## 交付结构

本 Issue 作为两仓交付的父目标和最终完成门，不把跨仓改动压成一个不可审查 PR。

### 切片 1：`agent-plugins`

1. 建立一个链接 `agent-control#3` 的交付 Issue；只拥有以下范围：
   - `adaptive-problem-solving` 正文、双端 manifest 与对应 README 版本说明；
   - `orchestrated-collaboration` 正文、双端 manifest 与对应 README 版本说明。
2. 将 `adaptive-problem-solving` 提升为 `0.1.1`：
   - 最终／阶段验收检查父目标实际贡献；
   - 对照当前基线、明确引用的参考能力和被替代方案，识别未经明确接受的能力回退；
   - 声明证据最多支持实现完成、当前交付验收、样本有效、产品采用或长期依赖中的哪一级；
   - 需要负责人决定时，确认 ROI、限制、替代方案和推荐已进入负责人可直接访问的审阅面；
   - 授权内的客观缺口直接进入 `revise`，产品取舍、风险偏好或扩大授权才升级给负责人。
3. 将 `orchestrated-collaboration` 提升为 `0.1.3`：仅在高价值、多 PR 的 Agent 系统能力或工作流替代中，且协调者参与拆分或方案设计时，派发另一 Agent 做父目标级只读复核；普通低风险任务明确豁免；子 PR Review 不替代父级复核。
4. 同步 Codex／Claude manifest 和 README；不复制 Orca 命令，不增加新 Skill。
5. 在专用分支／worktree 提交并创建 Draft PR。

### 切片 2：`agent-control`

1. 在版本化入口 `entrypoints/agent-system.md` 增加一个短触发与不变量：Agent 系统 MVP、工作流替代或高价值多 PR 父任务在宣称完成、进入自然观察或关闭前，必须加载 `adaptive-problem-solving` 做父目标、能力回退、证据等级和负责人可见 ROI 验收；未完成不得声称产品闭环。
2. 同步仓内 `AGENTS.md`；`CLAUDE.md` 继续导入同一入口，不复制正文。
3. 更新 `work/current.md` 与研发记录，只记录授权、交付状态、证据和 ROI，不提前把未合并／未安装行为写成权威事实。
4. 在专用分支／worktree 提交并创建 Draft PR，链接但不自动关闭 `agent-control#3`。

## 质量与整合门

1. 两个 PR 分别执行提交后 `pr-self-review`，检查范围、行为闭环、版本、双端包装和无越权扩张。
2. 由与实现者不同的 Agent 按当前 head 执行 `pr-review`；发现阻断后修正并重新绑定新 head。
3. 另派一个未参与拆分和实现的 Agent，对两个最终 head 做父目标级只读复核，检查：原始问题贡献、相对当前基线和 `issue-to-merge` 明确引用能力的回退、证据等级、普通任务成本边界、ROI 审阅面和完成声明。
4. 协调者使用 `pr-integration` 核验两个精确 head、关联 Issue、检查、未解决反馈、合并性和授权。没有明确合并授权时停止在可合并决定点。
5. 获得合并授权后按依赖顺序合并 `agent-plugins`、再合并 `agent-control`；随后安装或升级普通 Codex、Orca Codex 和 Claude 三端 Plugin，并同步三份真实入口。
6. 比较版本、文件清单、字节数和 SHA-256；运行一个受限的新 Session 只读复述场景。该场景只证明发现和合同理解，不证明长期 ROI。

## 验证

- JSON／YAML／frontmatter 与 Agent Skills 格式检查；
- 两端 manifest 名称、版本、描述和路径一致；
- `git diff --check`、owned-path 检查、未引入新自动化资产扫描；
- 从入口到 Skill、从协作路由到独立父级复核、从客观缺口到 `revise`／从产品取舍到负责人决定的静态走读；
- 两个 PR 的当前 head 自审与独立复审；
- 三端安装后逐文件一致性和受限新 Session 复述。

## 成本、停止与回退

- 不做外部大规模调研，不复现旧失败，不建设测试平台；
- 粗粒度记录本轮墙钟、流程步骤、真实发现、返工和负责人决定次数；
- 如果 Challenge／规划没有改变方案，只把它记为本次临时质量基线的成本证据，不再追加方法层；
- 如果两个 Skill 的职责产生重复或普通任务触发过宽，在 PR 阶段缩窄措辞；不增加第三个 Skill；
- 未合并时回退是关闭 PR；已合并但安装失败时恢复上一个 Plugin 版本和入口副本；
- 任一产品边界变化、明显扩大授权或长期依赖决定都停止并请求负责人。

## 完成定义

- 两仓精确 head 通过自审、独立 PR Review 和独立父目标复核；
- 负责人能从 GitHub 直接看到方案、审查、ROI、证据边界和下一决定；
- 获得合并授权后，两仓合并、三端入口与 Plugin 安装一致性通过；
- `agent-control#3` 的验收标准全部有证据，并且没有把一次样本升级成产品采用或永久依赖决定。

