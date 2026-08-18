## Context

当前 CAP wrapper 为 OMP 保留持久 profile agent home，但把 `HOME` 改为该目录，并用手工 bridge 注入 Git 根上方的 `AGENTS.md`。公共 profile 工具原 schema 是扁平闭包，项目 lock 同时承担了本应属于机器和 workspace 的决定。

## Goals / Non-Goals

**Goals:**
- 让真实用户环境成为一个显式、可审批、可绑定的 `real-home` 基座。
- 让项目 profile 成为可移植增量层，并确定性支持 `add`、`mask`、`replace`。
- 保留 OMP profile 专属配置和 Session 状态。
- 以 digest 和运行证据区分声明态、配置态和生效态。

**Non-Goals:**
- 不复制或版本化整份 HOME。
- 不把认证、session、history、cache 纳入 profile lock。
- 不自动批准基座更新，也不级联刷新所有 derived profile。
- 不保留旧 schema 或 workspace bridge 兼容路径。

## Decisions

### 1. 三个独立锁定层

项目 `.cap/lock.json` 只锁可移植 layer；`$HOME/.cap-user-state/locks/real-home.manifest.json` 保存私有机器观察；`$HOME/work/_org/locks/agent-assembly-general/` 保存 workspace pin 和 derived bindings。这样项目层变化不迫使重新批准基座，基座变化也不会污染 Git 历史。

### 2. 单继承与显式集合操作

每个 profile 最多一个 `extends`，链无环且最多一个 `real-home`。每类能力按基座到叶子顺序应用 `add`、`mask`、`replace`；同名 add 和不存在的 mask/replace 失败。prompt 按继承顺序拼接，`real-home` 不把用户文件正文复制到 render。

### 3. 真实 HOME 与客户端状态分离

OMP 进程使用真实 `HOME`，但 `PI_CODING_AGENT_DIR`、`PI_CONFIG_DIR` 和 `PI_CONFIG_FILES` 指向 profile 专属 agent home。由此 Git、SSH、工具链和原生 context discovery 正常工作，Session 仍按 profile 隔离。旧 bridge 删除，避免重复注入。

### 4. 分级漂移

manifest 对 secret 值做固定替换后摘要；能力路径、结构、命令或非 secret 配置变化会改变 digest。batch 对 active drift fail closed；交互允许一次显式 continue，但不修改 pin。每次持久 OMP 退出后再次执行 binding verify，成功后才写 receipt。

## Risks / Trade-offs

- 客户端对真实 HOME 的原生能力发现不对称；不可可靠观测的维度保持 unknown，不以文件存在冒充生效。
- manifest 的候选路径目录需随客户端演进维护；未知路径不应静默视为已批准能力。
- workspace pin 是本机控制面资产，丢失后需要重新人工批准，但不会影响项目 lock 可复现性。

## Migration Plan

1. 公共 profile 工具升级 schema、base manifest、pin/binding 和 runtime gate。
2. 两个 assembly profile 迁移到 version 2，并更新项目 lock。
3. 生成一次私有 base manifest，人工批准 workspace pin，分别绑定两个 profile。
4. CAP wrapper 转发三类 binding 路径、保留真实 HOME、删除 bridge、保留 profile agent home。
5. 运行单元测试、strict spec validation、render/verify 和真实 OMP smoke。

## Rollback Plan

回退公共工具和本仓对应提交；删除外部 binding 即可阻止 layered profile 启动。不得恢复旧 bridge 与 HOME 替换的混合状态。