## 1. 冻结远端与本地基线

- [x] 1.1 记录五个 `zaurakworks` 当前代仓的 visibility、canonical remote、default branch、remote head、开放 Issue/PR、release、ruleset、Actions 和 rename/archive 权限，并为每个 source/target 固定回滚 ref
- [x] 1.2 从 `_org` 与具名 Git 根记录全部当前代、旧 `Eridanus117`、legacy `~/workspace` checkout 和 registered worktree 的 common dir、HEAD、branch、dirty、untracked、local-only commit 与 ownership；任何未知对象标为 blocker
- [x] 1.3 为 `agent-control`、`agent-contracts`、`agent-plugins`、`agent-assembly` 分别采集当前文件清单、内容摘要、入口、测试命令、CI、公开 URL 和 source→target 路径映射
- [x] 1.4 采集 `general`、`assembly-helper`、`work` inventory、Codex/Qoder/OMP portable render hash、有效 OMP generation、安全门、CLI 帮助与既有单元测试基线，不读取或记录 secret
- [x] 1.5 采集全部 Plugin/Skill 版本、双端 Marketplace、符合性结果、contracts Schema 正负样例和捕获/回执验证，以及当前环境可安全执行的隔离安装/发现/触发/负例；缺失客户端或认证时记录 `unknown` 并建立对应 archive blocker
- [x] 1.6 建立 state-lab 毕业清单，逐项记录负责人决定、产品 owner、公开必要性、脱敏结论、目标规范/测试、source commit 和拒绝理由；未确认资产默认不迁移

## 2. 建立并改名目标仓

- [x] 2.1 从现有 `agent-control` canonical 主仓创建目标任务 worktree，冻结 owned paths 和迁移协调回执，不复用 dirty/legacy checkout
- [x] 2.2 在目标 worktree 建立单仓目录、根导航和 provenance manifest 结构，保持现有 `authority/`、`knowledge/`、入口和验证在导入前仍可运行
- [x] 2.3 将现有 GitHub `zaurakworks/agent-control` 原位重命名为 `zaurakworks/agent-system`，回读仓身份、默认分支、权限、ruleset、Actions、Issues/PR 和旧 URL redirect
- [x] 2.4 更新目标 worktree remote、项目名称、根 README、AGENTS/CLAUDE 入口和受管自动化为 `agent-system`；旧 URL 只标记为迁移来源，不作为长期 canonical
- [x] 2.5 验证 rename 前的 agent-control 政策、知识、profile 工具和测试在新仓名下行为不变，并演练使用固定 ref 回退 rename/入口的步骤

## 3. 迁入 contracts

- [x] 3.1 在独立 source worktree 冻结 `agent-contracts` head 与内容摘要，把 Schema、examples、工具、测试和必要文档以具名快照迁入目标 `contracts/`，记录 provenance
- [x] 3.2 调整 contracts 内部相对路径、CI 和目标仓导航，保持合同字段、正负样例、捕获、父 Issue 校验、freshness、回执 render/post 和退出码不变
- [x] 3.3 分类 `agent-contracts` 开放 Issue/PR 为历史完成、目标仓 successor 或迁移 blocker，在目标建立可追溯索引，不伪造原 Issue/PR 编号或验收
- [x] 3.4 在目标仓运行 contracts 全部静态检查、正负样例和单元测试，并确认目标实现无需读取 source checkout

## 4. 迁入 plugins

- [x] 4.1 在独立 source worktree 冻结 `agent-plugins` head、版本和清单，把当前 Plugin/Skill、来源、docs、scripts、tests 与双端 Marketplace 以具名快照迁入目标，记录 provenance
- [x] 4.2 重写 repository URL、文档、manifest、Marketplace 和符合性调用方为 `agent-system`，保持每个 Plugin 独立版本、Codex/Claude 格式差异和退役负例
- [x] 4.3 运行全部 Plugin/Skill 元数据、版本、来源、双端 Marketplace、路由场景和复杂度门，证明迁移没有恢复已退役能力或增加第二清单
- [ ] 4.4 在隔离 Codex/Claude 根安装目标 Marketplace，验证发现、显式触发、无显式调用负例和卸载清理；源码/CI 通过不得替代该生效态证据
- [x] 4.5 分类 `agent-plugins` 开放 Issue/PR、release 和外部安装链接，建立 successor 索引并阻断仍指向 source canonical 的受管调用方

## 5. 迁入 assembly 并收敛 CAP

- [x] 5.1 在当前 `agent-assembly` task worktree 完成并验证本 OpenSpec 规划后，冻结 source head、dirty/untracked、`.cap`、OpenSpec、docs、CAP/OMP 实现、测试和运行时迁移状态；不得从 legacy main 猜测缺失内容
- [x] 5.2 把 `.cap/manifest.toml`、profiles、prompts、中文 `SKILL.md`、lock、OpenSpec specs/changes 和必要文档迁入目标唯一声明面，保持 `real-home -> work -> general | assembly-helper` 组合语义
- [x] 5.3 建立 `src/agent_system` Python package 和根 `pyproject.toml`/`uv.lock`，声明 Python/依赖/entry point；保留 npm 对 OpenSpec/实际 TypeScript 依赖的固定 lock，不为目录对称新增工具
- [x] 5.4 把 profile schema、manifest/lock、layer merge、render、verify 和通用客户端适配迁入 `agent_system.profile`，迁移测试并删除目标内被替代实现
- [x] 5.5 把 CAP parser、show/use/run、Skill 元数据和调用协调迁入 `agent_system.cap`，把 OMP runtime/generation/CAS/migration/launch/receipt 与安全门迁入 `agent_system.omp`
- [x] 5.6 迁移全部 README、维护指南、CI、测试和自动化调用方到正式 `cap`/profile entry point，删除 `requirements.txt`、两份旧 `tools/cap.py` 与 sibling `profile.py` 猜测，不保留 shim 或别名
- [x] 5.7 更新 `.cap/lock.json` 及必要 binding，只接受由路径/打包变化引起且可解释的摘要；公共 inventory、Skill 中文合同和无关能力 hash 不得漂移
- [x] 5.8 运行 uv locked sync、Python 单元测试、Skill 标准、CAP verify、三 profile/三客户端 show/render、OMP migration/generation/CAS 安全负例和 CLI smoke，修复所有等价迁移回归

## 6. 毕业 state-lab 结论

- [x] 6.1 只选择毕业清单中具有负责人确认、公开 owner、必要消费方和脱敏通过的结论，为每项建立目标政策、spec、测试或 fixture 与 source commit 映射
- [x] 6.2 把批准的最小自足资产迁入目标对应 owner，删除对 private 仓才能理解的硬依赖；原始实验、audit JSON、private `.omp`、handoff、Session/路径和未采纳候选保持不迁移
- [x] 6.3 对 public 目标树执行 secret、private path、Session、credential、未采纳候选和历史运行状态检查，并用故意失败 fixture 证明门禁能拒绝泄露
- [x] 6.4 回读 `agent-state-lab/FINDINGS.md`、当前 Issue 和目标消费方，确认每项当前结论只有一个产品入口，实验事实没有被报告为普遍生效能力

## 7. 单仓集成与真实生效验证

- [x] 7.1 运行目标仓所有原 agent-control、contracts、plugins、assembly 静态检查、单元测试和 OpenSpec strict validation，确认根入口和按域检查均可从干净 clone 执行
- [x] 7.2 对照 1.4 基线验证 profile inventory、portable/effective render hash、lock/binding、OMP runtime/Session、无 ambient MCP/Hook/Plugin 门和共享状态语义
- [ ] 7.3 对照 1.5 基线验证合同机械行为、Plugin/Skill 版本与双端 Marketplace，并重复隔离真实 Codex/Claude 安装/显式调用/负例
- [x] 7.4 从至少两个非目标仓 workdir 使用 `agent-system` canonical entry point 运行 Codex、Qoder 和 OMP smoke，证明不需要 sibling checkout 且 receipt 不含 secret
- [x] 7.5 检查 public 树、文档、CI、Marketplace、package metadata 和本地配置没有当前调用方继续依赖四个 source canonical URL、重复 CAP 实现或 profile 外 ambient 能力源
- [x] 7.6 以固定 target/source ref 演练一个未完成 source 导入的回滚，证明可恢复原 canonical 入口且不删除 source 历史、Issue/PR、private 证据或未跟踪资产

## 8. 切换入口并归档源仓

- [x] 8.1 为 `agent-contracts`、`agent-plugins`、`agent-assembly` 更新 README 首屏、Issue 模板、开放 Issue/PR 和 release/安装入口，明确 successor 路径、source head 与 archive 后只读语义
- [ ] 8.2 在逐源资产、调用方、验证、生效和回滚门全部通过后，将 `agent-contracts`、`agent-plugins`、`agent-assembly` 依次设为 GitHub archive；任一未知结果只阻止对应 source，不批量越过
- [ ] 8.3 在全部批准结论毕业、private 当前工作入口关闭且 successor 可自足后，更新 `agent-state-lab` private README 并设为 private archive；不删除仓或公开原始证据
- [ ] 8.4 回读四个 source 的 archive/visibility/README、目标仓 canonical URL、默认分支、Actions、Issues/PR、Marketplace 和 redirect，生成不含 secret 的最终迁移回执

## 9. 本地物理收敛与最终验收

- [x] 9.1 更新 `_org` remote/local/family inventory、searched roots、证据时间、duplicate/legacy/dirty 分类和 move plan，明确 `~/work/agent-system` 为唯一 canonical 主仓
- [x] 9.2 在不移动 active common dir 的前提下建立或迁入 `~/work/agent-system`，验证 origin/head/branch/工作树后为新任务统一使用 `~/work/worktrees/agent-system/<slug>`
- [ ] 9.3 逐个处理旧 `agent-control`、`agent-plugins`、`agent-assembly` clone 和 worktree：先保全 dirty/untracked/local-only commit，再仅通过 owning main repo 的 Git worktree API remove/prune；未获删除授权的普通 clone 保留并标记
- [ ] 9.4 更新 `WORKSPACE.md` 和维护入口，明确一个公开活跃 `agent-system`、private archived state-lab、archived source 历史和外部 `work-skills`/private-kb/ticket-decision-core 的独立边界
- [ ] 9.5 从干净 canonical clone 重跑全局检查、真实 smoke、OpenSpec strict validation 和远端 archive 回读，分别报告声明态、标准合规、配置态、生效态与仍为 `unknown` 的端
