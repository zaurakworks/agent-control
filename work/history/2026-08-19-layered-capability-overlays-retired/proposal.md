## Why

当前 CAP 把 `.cap` 视为单一项目的唯一能力来源，无法在不把公司 Skill 名称、正文或依赖私有 Skill 的 profile 推入公共 `agent-system` 的前提下，形成可验证的本地私有能力闭包。与此同时，现有 digest 主要证明摘要相等；发生差异时缺少可回读、可比较的物化内容证据，排查只能从路径和摘要反推。

现在需要把公共声明源与本地私有声明源分层，并把每层及最终闭包物化为可读证据；这保留公共仓边界，也使私有 profile 的审批、回滚和差异排查可重复。

## What Changes

- 增加显式的公共 base + 一个私有 capability overlay 装配模型；私有 overlay 不通过 ambient discovery、symlink 或用户目录自动扫描进入。
- 允许私有 profile 显式引用公共 profile，并只在本地增加公司 Skill、MCP 或私有 prompt；依赖私有能力的 profile 不进入公共仓。
- 为公共层、私有层和 effective profile 分别生成 lock/digest；effective digest 必须包含有序层来源、profile、能力闭包、渲染器和客户端适配器输入。
- 为 digest 对应的源树、解析后的能力 inventory、合并结果和最终 render tree 提供受控物化目录或归档，以及机器摘要到物化证据的索引；差异时可直接读取前后内容和来源边界。
- 评估 OCI/ORAS、Nix flakes/store、CUE modules 等开源项目：优先复用内容寻址、锁定和 artifact 存储思想；不把完整容器运行时或 Nix/CUE 语言引入 CAP，除非验证显示直接依赖能降低复杂度。
- 保持私有源、lock、pin、binding、runtime、认证和 session 分离；私有源可以本机保存于 `~/.cap-user-state/overlays/`，但不与运行态目录混用。

## Capabilities

### New Capabilities

- `private-capability-overlay`: 显式装配公共 profile 与本地私有 capability/profile layer，隔离公开性、来源、冲突规则和回滚边界。
- `digest-materialization-evidence`: 将摘要输入、解析闭包、层合并结果和最终渲染树物化为可读、可比较且不含 secret 的证据。

### Modified Capabilities

- `layered-agent-profile`: 修改单一项目能力来源、用户级目录不得作为 source、Skills 只能来自当前项目 profile 的要求，使其支持经显式 lock/binding 授权的私有 overlay，同时保留禁止 ambient discovery 和未声明能力注入的要求。

## Impact

- 主要影响 `src/agent_system/profile/`、`src/agent_system/cap/`、`.cap/` lock/binding 语义、render CAS 与 receipt/preview 证据；不改变现有公共 profile 的默认行为。
- 需要新增私有 overlay 的 source、lock、binding 和物化证据路径规范；公共仓不得保存私有 Skill 名称、正文、prompt 或私有 profile。
- 需要新增跨层冲突验证：`add` 同名拒绝，`mask`/`replace` 必须显式且只能作用于已继承能力；层顺序和来源摘要进入 effective digest。
- 运行时仍只加载当前验证后的 effective render tree；用户级 runtime、cache、manifest、pin、binding 和 auth store 不能反向成为 profile catalog。
- 回滚边界：删除或禁用私有 overlay binding 后，公共 profile 和公共 render 必须仍可独立重建；删除物化证据不得影响声明源、lock 或运行态。

## Baseline Evidence and Open-Source References

当前 `openspec/specs/layered-agent-profile/spec.md` 已定义 `real-home -> work -> derived` 的单基座链、`add/mask/replace`、base/layer/effective digest 分离，以及“Skills 只来自当前项目 profile”的约束；本变更只提议增加显式私有 source layer，不恢复 ambient 能力来源。

开源调研基线：

- [OCI Descriptor](https://github.com/opencontainers/image-spec/blob/main/descriptor.md) 定义以算法、大小和 digest 标识原始字节，并要求消费方校验 digest/size。
- [OCI Image Manifest](https://github.com/opencontainers/image-spec/blob/main/manifest.md) 定义配置、layers、artifact type 与 descriptor 引用，可借鉴层清单和内容寻址模型。
- [ORAS Artifacts Specification](https://github.com/oras-project/artifacts-spec) 将 OCI 扩展为通用 artifact 及引用关系，可作为可选证据/分发存储，而不是 CAP 的 profile resolver。
- [Nix flakes](https://releases.nixos.org/nix/nix-2.25.5/manual/command-ref/new-cli/nix3-flake.html) 与 [Nix content-addressed store](https://releases.nixos.org/nix/nix-2.24.2/manual/store/store-object/content-address.html) 提供锁定输入和内容寻址闭包的参考，但其求值与构建模型超出本变更范围。
- [CUE modules](https://cuelang.org/docs/concept/modules-packages-instances/) 展示可复现模块依赖和声明组合的做法；本变更不引入 CUE 作为运行时语言。
