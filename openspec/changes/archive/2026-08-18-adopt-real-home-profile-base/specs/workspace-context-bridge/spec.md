## REMOVED Requirements

### Requirement: 隔离启动恢复父级工作区 context

**Reason**: OMP 不再替换真实 `HOME`；手工读取并拼接父级 `AGENTS.md` 会与客户端原生 context discovery 重复。

**Migration**: 保留真实 `HOME`，隔离 `PI_CODING_AGENT_DIR`／`PI_CONFIG_DIR`，并通过真实 OMP smoke 验证父级和仓库 context 路径。

### Requirement: 父级 bridge 保持最小可见面

**Reason**: 手工 bridge 整体删除，不再维护第二套文件选择和顺序算法。

**Migration**: 工作目录仍固定为当前 Git worktree；context 文件选择交给 OMP 原生发现。

### Requirement: bridge 证据分层

**Reason**: 不再存在 bridge 实现或 bridge 单元测试。

**Migration**: 配置态验证真实 HOME 与隔离状态根；生效态要求真实 OMP 输出实际 context file 路径。

## ADDED Requirements

### Requirement: 真实 HOME 下使用客户端原生 context discovery

CAP SHALL 保留真实 `HOME`，不得手工读取、复制或拼接父级 `AGENTS.md` 到 profile prompt。OMP SHALL 从显式 workdir 原生发现适用的父级与仓库 context；只有真实 OMP 输出的 context 路径可作为该机制的生效态证据。

#### Scenario: worktree 位于工作区内

- **WHEN** OMP 从 `~/work` 下的当前 Git worktree 启动
- **THEN** 真实运行 SHALL 能报告适用的 `~/work/AGENTS.md` 与仓库 `AGENTS.md`，且 render 的 `system-prompt.md` SHALL 不复制这些正文

#### Scenario: profile prompt 保持项目层

- **WHEN** 调用方 render `general` 或 `assembly-helper`
- **THEN** `system-prompt.md` SHALL 只包含 profile 层 prompt，不得包含手工 workspace context bridge 标记
