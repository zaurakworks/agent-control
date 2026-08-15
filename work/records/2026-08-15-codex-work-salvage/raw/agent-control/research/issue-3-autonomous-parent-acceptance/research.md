# Research Phase：自主父目标验收

## 范围

只核验 `agent-control#3` 已批准的行为补丁所依赖的当前权威、入口、Skill 源码、Plugin 包装和真实安装边界；不重新调研 Agent 平台，不复现旧失败，不提出新系统。

## 已读取的当前依据

- `agent-control` 的 `README.md`、`authority/00-map.md`、`work/current.md` 及当前任务列出的六份权威；
- `agent-control#2` 的 ROI 决定、`agent-control#3` 的正文与负责人授权评论；
- 版本化入口 `entrypoints/agent-system.md`、仓内 `AGENTS.md` 与 `CLAUDE.md`；
- `adaptive-problem-solving 0.1.0` 和 `orchestrated-collaboration 0.1.2` 的版本化源码、双端 manifest、Marketplace 清单与仓库 README；
- `agent-plugins/docs/conformance.md` 与相关 Git 历史；
- Orca `1.4.177` 当前完整 orchestration 指南及活动 Run 状态。

## 已确认事实

1. 当前入口会在长任务验收时加载 `adaptive-problem-solving`，但没有明确规定 Agent 系统 MVP、工作流替代或多 PR 父任务在宣称完成、进入自然观察或关闭前必须检查父目标、能力回退和负责人可见 ROI。
2. `adaptive-problem-solving 0.1.0` 的第八节只检查是否仍在解决原始问题、瓶颈、方法、替代方案和下一行动；没有显式区分实现完成、提交验收、样本有效、产品采用和长期依赖，也没有要求对照当前基线或明确引用的被替代方案。
3. `orchestrated-collaboration 0.1.2` 要求协调者独立验收执行者交付并区分执行、验收和产品决定，但没有规定：协调者参与拆分和设计时，高价值多 PR Agent 系统能力需由另一 Agent 做父目标级只读复核。
4. `agent-control#2` 已记录负责人批准的临时混合质量基线；`agent-control#3` 已记录负责人批准路线 C，并保留“合并绑定精确 PR head 和单独授权”的门。
5. 版本化入口同时投影到普通 Codex、Orca Codex 和 Claude 的真实入口；Plugin 源码同时投影到三端安装缓存。仓库源码修改不会自动更新用户级安装。
6. `agent-plugins` 当前 `main` 干净，`adaptive-problem-solving` 版本是 `0.1.0`，`orchestrated-collaboration` 版本是 `0.1.2`。行为变化需要同步双端 manifest 和 README 版本说明。
7. `agent-control` 与 `agent-plugins` 是两个独立 Git 仓，不能由一个 PR 原子交付；真实安装又是仓外共享状态，不能由 worktree 隔离。
8. 当前 Orca Run 的协调者仍是本 Session，Run 已存在且没有必要新建竞争 Run；Orca TUI 只是观察面。

## 约束

- 不新建 Skill、Hook、评测平台、强制锁、登记中心、自动调度器、资源监控或长期依赖决定；
- 普通单 PR、低风险、容易回退任务不强制父目标独立产品复核；
- 子 PR Review 不能冒充父目标复核；
- 不把静态一致性、安装成功、一次行为样本或一个产品决定互相替代；
- 未经精确 head 的合并授权，不合并 PR；未合并源码不写入三端真实安装。

## 未知与验证面

- 新措辞能否在新 Session 中被正确复述，只能在安装后通过受限只读场景观察；静态走读不能证明真实触发收益。
- 当前没有低成本可靠的 Token／费用观测；本次只记录墙钟、流程步骤、发现和人工决定次数。
- 两仓改动的组合语义需要独立父目标复核；单仓 PR Review 不能单独证明组合完整。

