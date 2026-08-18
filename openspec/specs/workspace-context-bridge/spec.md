# workspace-context-bridge Specification

## Purpose

让 CAP 隔离 OMP 在不扩大 workspace、不读取无关目录且不复制规则正文的前提下，恢复真实 home 边界内、当前 Git 仓库上方的工作区 `AGENTS.md` 上下文。

## Requirements

### Requirement: 真实 HOME 下使用客户端原生 context discovery

CAP SHALL 保留真实 `HOME`，不得手工读取、复制或拼接父级 `AGENTS.md` 到 profile prompt。OMP SHALL 从显式 workdir 原生发现适用的父级与仓库 context；只有真实 OMP 输出的 context 路径可作为该机制的生效态证据。

#### Scenario: worktree 位于工作区内

- **WHEN** OMP 从 `~/work` 下的当前 Git worktree 启动
- **THEN** 真实运行 SHALL 能报告适用的 `~/work/AGENTS.md` 与仓库 `AGENTS.md`，且 render 的 `system-prompt.md` SHALL 不复制这些正文

#### Scenario: profile prompt 保持项目层

- **WHEN** 调用方 render `general` 或 `assembly-helper`
- **THEN** `system-prompt.md` SHALL 只包含 profile 层 prompt，不得包含手工 workspace context bridge 标记
