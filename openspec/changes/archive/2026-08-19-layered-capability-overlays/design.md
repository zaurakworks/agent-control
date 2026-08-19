## Context

当前 profile resolver 只加载一个项目 `.cap`，并把 profile 的 Skills、prompt 和客户端目标树锁入项目 lock；`real-home`、workspace pin、binding 与 OMP runtime 是独立控制面。参见 proposal.md 与本变更的三份 spec。新的私有层必须在验证后进入同一份 effective generation，但不能成为用户目录的 ambient source。

用户需要 Docker 式的装配体验：公共层可复用，私有层只在本机显式附加，层间按能力名合并；发生 digest 变化时，需要能读取对应的实际内容，而不是只看到不可解释的摘要。

## Goals / Non-Goals

**Goals:**

- 支持 `public base + one private overlay + selected profile` 的有序声明层。
- 保留现有 `extends`、`add`、`mask`、`replace` 的能力级语义和 fail-closed 门禁。
- 为每一层、解析闭包和客户端 effective render 生成可回读的物化证据。
- 公共、私有、配置态、运行态和证据态保持分离；Codex、Qoder、OMP 继续使用各自 renderer。
- 支持公共 profile 独立运行，私有 overlay 删除后不影响公共 profile。

**Non-Goals:**

- 不引入 UnionFS、容器运行时、whiteout 文件或任意路径覆盖。
- 不把 Nix/CUE 语言或完整构建系统引入 CAP。
- 第一版不支持任意数量 layer；只支持一个显式 private overlay。
- 不把 secret、认证、session、history、cache 或 provider 配置纳入 source/evidence。
- 不让私有 overlay 自动成为所有项目的隐式全局能力。

## Decisions

### 1. 采用逻辑声明层，不采用文件系统层

每个 layer 是一个受控 source root、manifest、profile 集合和 lock。resolver 先构造逻辑 capability map，再由现有 client adapter 渲染 effective tree。source 文件不直接覆盖另一个 source 的路径；只有 `add`、`mask`、`replace` 可以改变能力 map。

选择理由：能力已经有稳定名称和现有冲突规则；文件系统 union 会把“同名 Skill”“prompt 继承”和“客户端差异”混成路径覆盖，难以审计和回滚。

备选方案：OCI filesystem layer。OCI 的 descriptor/manifest/layer 适合保存字节和层 DAG，但 whiteout、tar 顺序和压缩字节不是 CAP 的能力语义；只作为后续可选的 artifact 封装，不作为 resolver。

### 2. 使用一个公共层和一个显式私有层

公共 source 默认是 `~/work/agent-system`，私有 source 默认放在 `~/.cap-user-state/overlays/agent-system-private`。CLI 或显式 profile descriptor 提供 private source；没有该输入时，公共 profile 的解析路径完全不读取私有目录。

私有 profile 通过稳定的跨层引用选择公共 profile，例如 `public:general`，然后执行私有层的 `add/mask/replace`。私有 profile 使用独立命名空间（例如 `company-general`），避免公共和私有 profile id 冲突。

选择理由：第一版只增加一个安全边界，易于理解和回滚；将来若确实需要多层，可把当前两层模型推广为有序 layer list，而不改变能力操作语义。

备选方案：把私有 Skill 同步进 `real-home` 的 native Skill 目录。该方案会重新引入 ambient discovery，且与当前“生成树关闭 user/project Skill 自动来源”的门禁冲突，不采用。

### 3. 分层 lock 与 effective binding 分离

每个 source layer 生成自己的 lock，包含 source identity、规范化输入清单、profile/layer digest、renderer version 和 adapter version。effective binding 记录有序的 public digest、private digest、base digest、selected profile 和 effective digest。

计算顺序固定为：

```text
real-home base
→ public source/profile
→ private source/profile
→ client renderer/fixed gates
→ effective render
```

任何层发生变化都会使其后继 lock/binding stale；不自动批准、不静默刷新、不使用旧 generation。

### 4. Digest 对应可回读的 evidence tree

新增独立 evidence 根，不放入 runtime 或 public source：

```text
$HOME/.cap-user-state/evidence/
  sources/<source-digest>/
  closures/<closure-digest>/
  renders/<effective-digest>/
```

每个目录包含：

- `evidence.json`：对象类型、source/layer 顺序、父 digest、profile、client adapter、规范化规则和内容排除记录；
- `entries.jsonl`：相对路径、mode、size、content digest、来源层和 capability id；
- `tree/`：去除 secret 后的可读物化文件树；
- 可选 `diff.json` 或由 CLI 即时计算的前后差异。

物化使用规范化路径排序、稳定 mode/size 记录和稳定 JSON 编码。secret 输入不写正文，只记录不泄露值的 exclusion marker。evidence index 和 tree 共同参与复用校验；缺一不可。

选择理由：digest 保持机器验证效率，tree 提供人类排查入口；两者不再要求用户从单个 hash 反推内容。

### 5. 开源项目只复用边界，不直接替换 CAP resolver

- OCI Descriptor/Manifest/ORAS：可选用于把 source/evidence tree 打包为可分发 artifact；第一版先采用本地 evidence CAS，避免 registry、tar 压缩和远端认证扩大范围。
- Nix flakes/store：参考其锁定输入和内容寻址闭包，但不引入 Nix 求值、daemon 或 store path 语义。
- CUE modules：参考其可复现模块依赖，但不引入第二套配置语言。

因此第一版新增少量 Python 证据/锁逻辑，后续可将 evidence bundle 导出为 OCI artifact，而不改变 effective profile 合同。

### 6. 客户端 renderer 共享 resolver，分别渲染

公共/私有层合并在客户端无关的 effective inventory 中完成。之后沿用现有 Codex、Qoder、OMP renderer：

- Codex：生成隔离 `CODEX_HOME`、`AGENTS.md` 和允许的 Skills；
- Qoder：生成隔离 config/MCP/prompt；
- OMP：生成隔离 config、custom Skill directory、extension policy 和 prompt。

source/evidence digest 不作为客户端可编辑配置注入；receipt/preview 只输出 digest、evidence path 和不含 secret 的摘要。

## Risks / Trade-offs

- [私有 source 路径或 Skill 名称泄露] → 公共 lock/preview/receipt 只保存公共层数据；私有 evidence 只在显式 private preview 输出。
- [私有层误覆盖公共能力] → `add` 重名拒绝，`replace`/`mask` 必须显式指向已继承 id，并把操作写入 private lock。
- [evidence 占用磁盘] → evidence 使用内容寻址、按 digest 复用；清理只删除用户授权的旧 evidence，不删除 source/lock/runtime。
- [同语义文件因规范化差异产生不同 digest] → 固定路径排序、JSON 编码、mode/size 规则；保留 raw content digest 与 semantic digest 的字段区分。
- [多客户端生成结果不同] → effective digest 纳入 client adapter 和 fixed gates；各 renderer 分别物化和验证，不共享客户端文件树。
- [开源工具引入过重] → 第一版不增加 Nix/CUE/OCI runtime 依赖；OCI/ORAS 只在需要跨机器分发 evidence 时作为后续实现。
- [私有层失效导致公共能力不可用] → 公共 profile 的解析、lock、render 和启动路径不依赖 private overlay；private profile 失败只阻断该 private profile。

## Migration Plan

1. 保持现有单项目 CAP 行为不变，先增加 source/layer/evidence 数据模型和只读 preview。
2. 为公共 `general` 和 `assembly-helper` 生成等价的 public layer lock/evidence，验证 effective digest 与现有 render 一致。
3. 创建本地 private overlay 示例，仅增加一个非敏感测试 Skill，验证显式绑定、冲突、回滚和公共 profile 独立运行。
4. 为 Codex、Qoder、OMP 分别执行 render、evidence 校验和真实 smoke check；确认 receipt 不含私有正文和 secret。
5. 默认仍不启用 private overlay；删除 private binding、private evidence 和 private source 后，公共 profile 使用原 public lock 可重建。

回滚方式：停用 private overlay 功能开关或删除 private binding，保留公共 `.cap`、public lock、real-home pin/binding 和现有 runtime；公共启动不读取 private source。

## Open Questions

无。第一版边界、单私有层、证据位置、开源项目采用范围和回滚路径已经确定；OCI/ORAS 的远端分发仅作为后续扩展，不影响本次规格。
