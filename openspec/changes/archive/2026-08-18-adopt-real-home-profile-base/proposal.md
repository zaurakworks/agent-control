## Why

现有 `general` 与 `assembly-helper` 通过替换 OMP `HOME` 获得隔离，导致真实用户环境不可见，并需要额外 workspace context bridge 修补父级 `AGENTS.md`。项目 profile 也仍是不可继承的扁平闭包，无法把机器基座与项目增量分别审查和锁定。

## What Changes

- 将 `work`、`general` 与 `assembly-helper` 升级到 version 2，形成显式 `real-home -> work -> derived` 链。
- 用 `add`、`mask`、`replace` 表达项目层能力变化；项目 lock 只纳入可移植层。
- 用私有 real-home manifest、workspace pin 和 derived binding 锁定机器基座与项目层组合。
- OMP 保留真实 `HOME`，同时把配置与 Session 状态隔离到 profile 专属 agent home。
- 删除手工 workspace context bridge；父级和仓库 `AGENTS.md` 交给真实 HOME 下的客户端原生发现，并以真实 OMP 输出验证替代机制。

## Capabilities

### New Capabilities

- `layered-agent-profile`: 定义真实 HOME 基座、项目层操作、外部 pin/binding、漂移门禁和运行时隔离。

### Modified Capabilities

- `workspace-context-bridge`: 删除手工注入合同，改由真实 HOME 下的客户端原生 context discovery 承担父级规则发现。

## Impact

影响 `.cap` schema、两个 profile/prompt、CAP wrapper、lock、维护文档、单元测试和 OMP smoke 证据。私有 manifest 位于 `$HOME/.cap-user-state/locks/`；workspace pin 与 binding 位于 `$HOME/work/_org/locks/agent-assembly-general/`，均不进入 Git。