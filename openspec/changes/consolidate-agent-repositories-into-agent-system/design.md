## Context

见 `proposal.md` 的 Why。当前远端产品族包含五个仓：public `agent-control`、`agent-contracts`、`agent-plugins`、`agent-assembly` 与 private `agent-state-lab`；`agent-assembly` 默认分支为 `master`，其余为 `main`。GitHub 仓只能整体设置可见性，Issue/PR 也不能原生并入另一仓，因此公开产品单仓和 private 原始研究证据必须在迁移后继续保持可见性边界，旧仓需要 archive 承载历史。

`agent-control` 已拥有公共政策、知识、`tools/profile/` 和一份 `tools/cap.py`；`agent-assembly` 拥有 `.cap` 声明、OpenSpec、另一份已经显著分叉的 `tools/cap.py` 及 OMP runtime/CAS/migration 策略。`agent-contracts` 是独立 Python Schema/CLI/测试项目；`agent-plugins` 是具有独立版本、双端 Marketplace 和 TypeScript 符合性检查的发布资产；`agent-state-lab` 明确是非权威 private 证据仓与原型载体。

本地同时存在当前代、旧 `Eridanus117` checkout、legacy `~/workspace` 主仓和 registered worktree。当前规划工件位于 `agent-assembly` task worktree；实施时每个 source/target 写入必须绑定自己的任务 worktree和写入所有权，不能把 repo-local OpenSpec 根解释为任意修改其他 checkout 的权限。

当前机器没有 Claude CLI。负责人已决定：在当前 Plugin/Skill 版本、双端 manifest、source conformance、contracts validation 和可用 Codex 隔离基线已保存后，内容迁移可以继续；Claude 及未安全取得认证的显式触发/负例保持 `unknown`，并硬阻塞 Plugin/source archive，直到真实 Claude 环境补证。

## Goals / Non-Goals

**Goals:**

- 以现有 `agent-control` 仓身份为目标并重命名为 `agent-system`，不创建新仓。
- 把四个公开产品面收敛为一个可原子修改、单一 Issue/PR 入口的 monorepo，同时保留政策、合同、Plugin 和 assembly 的逻辑边界。
- 收敛 CAP/profile 工具所有权，形成一个 uv 管理、可导入、可测试的 Python package 和稳定命令入口。
- 逐仓保全提交、Issue/PR、未跟踪资产、worktree 和回滚引用；源仓只在分层验证完成后 archive。
- 只毕业 private state-lab 的已确认、已脱敏、产品必要结论；原始证据继续 private。
- 最终把本地 canonical 主仓和新 worktree 入口收敛到 `~/work/agent-system` 与 `~/work/worktrees/agent-system/<slug>`。

**Non-Goals:**

- 不把五仓 Git 历史强接成一个 unrelated-history 提交图；旧历史由 archived source 保留。
- 不迁移 GitHub Issue/PR 到伪造的新编号，不删除或重写历史评论。
- 不把 monorepo 变成新的用户级全局能力源；运行时能力仍只来自目标项目显式 `.cap`。
- 不恢复退役能力，不借迁移改变 profile inventory、Plugin 行为、合同格式或公共政策。
- 不在迁移过程中直接移动 Git common dir、registered worktree 或 dirty checkout。
- 不建设新的调度器、状态数据库、合同权威或实验控制面。

## Decisions

### 1. 重命名现有目标仓，不建立第六仓

目标 GitHub 仓由 `zaurakworks/agent-control` 原位重命名为 `zaurakworks/agent-system`。Rename 前固定 remote head、开放 Issue/PR、默认分支、ruleset、Actions、Secrets/Variables 名称清单和回滚 ref；rename 后立即回读仓身份、默认分支、权限、Actions 与 redirect。新 remote 是唯一 canonical URL，旧 URL redirect 只覆盖迁移窗口。

选择现有 `agent-control` 而非新仓，保留其公共政策、Issue/PR 和产品入口历史，也避免产生第六个协调仓。备选方案是继续使用 `agent-control` 名称，但合并后职责已覆盖合同、Plugin 和 assembly；负责人已接受 `agent-system` 的长期名称。

### 2. 单仓内使用清晰目录，不把逻辑边界压平

目标布局采用：

```text
agent-system/
├── authority/                 # 公共政策，原 agent-control
├── knowledge/                 # 公共当前知识，原 agent-control
├── contracts/                 # Schema、examples、CLI、tests
├── plugins/                   # Plugin/Skill 源码及各自版本
├── .agents/                   # Codex Marketplace/发现入口
├── .claude-plugin/            # Claude Marketplace
├── .cap/                      # 当前 profile/prompt/capability 声明
├── src/agent_system/
│   ├── cap/                   # 唯一 CAP CLI 与项目协调
│   ├── profile/               # profile schema/render/lock/verify
│   └── omp/                   # OMP runtime/generation/migration/launch
├── tests/
├── openspec/
├── pyproject.toml
├── uv.lock
├── package.json
└── package-lock.json
```

`authority/`、`contracts/`、`plugins/` 与 `.cap/` 分别只有一个规范入口。目标根 README 提供单一导航，不复制子域全文。现有源目录按资产清单迁入；若实际构建或客户端发现要求略有不同，可以调整路径，但不得形成第二份可运行实现或第二份规范正文。

### 3. 采用当前树快照迁移，不 graft unrelated Git 历史

每个 source 在冻结 head 上生成机器清单与内容摘要，目标以一个或少量具名迁移提交导入当前树，并在提交、迁移 manifest 和 successor README 中记录 source URL、branch、head、验证结果与目标路径。源 Git 历史、Issue/PR 和发布记录由 archived source 永久保留。

选择快照迁移是因为五仓为独立 clean-slate 产品，强行 `--allow-unrelated-histories` 或 subtree graft 会把多套根目录与历史路径带入目标提交图，却仍不能迁移 Issue/PR。备选的完整历史 graft 只有在发现法律归属、许可证或逐行追责要求无法由 archive + provenance 满足时才启用。

### 4. CAP/profile 先按所有权拆分，再删除旧入口

`agent-control/tools/cap.py`、`agent-assembly/tools/cap.py` 与 `tools/profile/profile.py` 不做文本择一。先建立调用与行为清单，再按以下所有权迁移：

- profile schema、manifest/lock、layer merge、render、verify、通用客户端适配进入 `agent_system.profile`；
- CLI parser、show/use/run 协调和 Skill 元数据检查进入 `agent_system.cap`；
- OMP runtime root、generation/CAS、migration、launch、receipt 与安全门进入 `agent_system.omp`；
- profile/prompt/Skill 和项目策略输入继续位于 `.cap`，不写死进 package。

根 `pyproject.toml` 声明 Python 版本、PyYAML 依赖、测试配置和 `cap`/必要的 profile entry point，`uv.lock` 纳管；旧 `requirements.txt` 和两份脚本入口在所有调用方迁移后删除，不留 shim。项目根通过显式 `--project`、受控环境或已验证的 source context 选择，禁止用 `../agent-control` 或任意 sibling checkout 猜依赖。

### 5. 合同与 Plugin 保持独立版本语义

`contracts/` 迁入 Schema、有效/无效样例、捕获/回执 CLI 和原验证入口；合同格式在没有独立 delta spec 时保持兼容。开放合同 Issue 先分类为已完成历史、迁入目标 Issue 或继续阻塞项，不能因仓库 archive 自动视为验收。

`plugins/` 保留每个 Plugin 的版本、来源和双端差异；根 `.agents` 与 `.claude-plugin` 继续作为各客户端真实 Marketplace 入口。Monorepo 不强制 Plugin 共用一个版本，也不把源码迁入等同于用户端已安装。npm 只管理实际 Node/OpenSpec 依赖；不为目录对称引入额外 workspace 抽象。

### 6. State-lab 使用毕业清单，而不是目录迁移

对 `FINDINGS.md` 中每项候选资产建立毕业记录：负责人决定、产品 owner、公开必要性、脱敏检查、目标规范/测试、source commit 和负例。只有全部字段通过的最小资产可以进入 public 目标；目标内容必须自足，private URL 只作为可选 provenance，不是理解前提。

原始 `experiments/`、audit JSON、private `.omp`、handoff、运行记录和历史概念账本不复制。完成已确认结论毕业、关闭当前 work item、README 指向公开 successor 后，private source archive；未来核验证据仍可按明确授权读取，但它不再是活跃产品或运行依赖。

### 7. 逐源门禁，最后归档

迁移顺序固定为 baseline → target rename → contracts → plugins → assembly/CAP → state-lab graduation → 集成验证 → source archive → 本地物理收敛。每个 source 单独有完成清单和回滚点；后一个 source 失败不要求回滚已经独立验证的前一个导入，但 target 在全部产品入口切换前仍不宣称整体完成。

基线门区分“source 身份/资产未知”和“客户端环境不可用”：前者阻止首次写入；后者在静态、配置态和可用客户端基线已保存后不阻止内容迁移，但持续阻止对应 source archive。不得用历史候选试验或另一客户端结果替代缺失客户端证据。

归档前回读 source 默认分支、README successor、开放 Issue/PR 处置、release/Marketplace 链接和 GitHub archive 状态。Archive 是历史保留，不执行 delete。旧 private `Eridanus117` 仓按既有蒸馏/冻结计划单独处理，不与本次当前代迁移混为同一 source。

### 8. 多仓实施使用独立 worktree 与单一协调回执

每个 writable repo task 使用该 repo canonical 主仓创建具名 worktree，并明确 owned paths；源仓冻结清单、目标导入、入口改写和归档操作不由同一未分区工作树隐式完成。协调者在本 change tasks 中记录 immutable source head、目标提交、验证证据和状态，但聊天、CURRENT 文件或本地 handoff 不成为迁移状态权威。

远端 rename/archive 和本地 clone/worktree 迁移分开执行。当前 `agent-assembly-general` worktree 及其 dirty common dir 在交付本 change 规划和后续代码后，必须通过 owning main repo 的 worktree API 收口；不得因目标路径已创建而直接移动或删除。

### 9. 验证按声明态、配置态、生效态分层

- 声明态：政策、合同、Plugin、`.cap` inventory 和唯一入口清单与 source 基线一致；private 证据不在公开树。
- 标准合规：合同正负样例、Skill/Plugin metadata、Marketplace schema、Python/TypeScript 测试和 provenance 检查通过。
- 配置态：lock、portable/effective render、package entry point、Plugin manifest/version 与 CI 接线通过。
- 生效态：真实 Codex/Claude Plugin 安装/显式调用、Codex/Qoder/OMP profile show/render/use、共享 runtime/Session 和无 ambient 能力探针按原合同通过。

静态文件、GitHub rename、CI 或 lock 不能替代真实生效证据。生效探针没有适用环境时保持 `unknown`，并阻止对应 source archive。

## Risks / Trade-offs

- **Public 泄露 private state-lab**：默认拒绝目录迁移，毕业清单逐项要求确认与脱敏；无法证明即留在 private source。
- **单仓范围扩大导致入口再次过重**：根 README 只导航，子域保持唯一规范；CI 按受影响域选择但保留全局一致性门。
- **快照迁移降低目标内逐行历史可见性**：source archive、head digest 和 provenance 永久保留；只有出现强制追责需求才改用历史 graft。
- **GitHub Issue/PR 仍分散在 archived source**：目标建立迁移索引和 successor 链接，不伪造编号或复制评论冒充原记录。
- **CAP 重构同时改变行为**：先钉住 inventory/hash/CLI/安全门基线，模块化和 uv 只做等价迁移；新行为必须另建 delta spec。
- **源仓归档过早**：归档是最后门，任一 dirty/local-only/open contract/生效证据未知均阻止对应 archive。
- **物理迁移破坏 worktree**：先读取 common dir 与 registered worktree，所有收口通过 Git worktree API；目标 clone 存在不构成删除旧根授权。
- **Rename 影响外部链接和安装**：GitHub redirect 提供过渡，所有受管 remote、Marketplace、文档和自动化仍必须显式迁到新 canonical URL；保留 rename 回滚 ref。

## Migration Plan

1. 锁定五个当前代远端、所有已知本地 checkout/worktree、开放 Issue/PR、验证命令、内容摘要和 source→target 路径；source 身份、资产或工作树未知时进入 blocker。客户端环境不可用时记录 `unknown` 与 archive blocker，不自动缩减最终生效验收。
2. 在现有 `agent-control` 目标分支建立目标骨架与回滚 ref，重命名远端为 `agent-system`，回读身份、权限、默认分支和 Actions。
3. 迁入 contracts，保持 Schema/CLI 行为，运行全部正负样例和测试，建立 Issue 迁移索引。
4. 迁入 plugins、双端 Marketplace 和验证资产，保持独立版本；在隔离客户端根完成安装、发现、显式调用和负例。
5. 迁入 `.cap` 与 OpenSpec，按所有权合并 CAP/profile/OMP package，uv 化并迁移全部调用方；运行 profile inventory/render/runtime 基线。
6. 从 private state-lab 逐项毕业已确认资产，执行公开树 secret/private-path 扫描与产品消费测试；保留其余原始证据。
7. 运行目标仓全局静态、单元、集成与真实端探针，验证旧 URL 不再是受管长期入口并演练回滚。
8. 更新三个 public source 与 private state-lab 的 successor/历史入口，处置开放 Issue/PR 后逐仓 archive；不删除仓库。
9. 把本地 canonical 主仓收敛到 `~/work/agent-system`，为后续任务使用规范 worktree 分组；按 `_org` 计划处理旧 clone 和 common dir。
