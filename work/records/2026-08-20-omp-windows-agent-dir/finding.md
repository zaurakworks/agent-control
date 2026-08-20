# cap 误用 `PI_CONFIG_DIR`：它是相对 home 的目录名，不是绝对根路径

> 非权威研发记录。结论只描述实测行为，不产生产品决定或授权。
> 相关规划：`openspec/changes/enable-windows-cap-assembly` 的任务 5.3。
> 上游 issue：[can1357/oh-my-pi#9067](https://github.com/can1357/oh-my-pi/issues/9067)（`wontfix`，理由见下）。

## 两次更正

本文件前两版的结论都是错的，按时间顺序保留更正链：

1. **首版**把根因记为 `PI_CODING_AGENT_DIR`。错在两组对照同时设置了两个变量，无法区分。
2. **第二版**逐变量隔离后改记为 `PI_CONFIG_DIR`，隔离本身是对的，但把它定性为"上游 bug、cap 侧无解、只能等修复"。**这个定性也是错的**——上游回复指出该行为是设计意图，问题在 cap 的用法。

## 上游裁定

[#9067](https://github.com/can1357/oh-my-pi/issues/9067) 被标为 `wontfix`，理由（原文摘要）：

- `getBaseConfigRoot()` 无条件把 `os.homedir()` 与 `getConfigDirName()` 拼接；
- `PI_CODING_AGENT_DIR` 单独经过 `path.resolve()`；
- 这个区分是**当前的设计意图**：同一模块把 `PI_CONFIG_DIR` 定义为**相对 home 的目录名**，native 崩溃日志解析也镜像了同样语义；
- 支持绝对值会改变 config-root 契约，而不是修复回归。

即：`PI_CONFIG_DIR` 传绝对路径本来就不在契约内，cap 用错了。

## 正确用法（已实测）

| 变量 | 契约 | cap 应传 |
| --- | --- | --- |
| `PI_CODING_AGENT_DIR` | 经 `path.resolve()`，接受绝对路径 | 托管运行时根的绝对路径 |
| `PI_CONFIG_DIR` | 与 `os.homedir()` 拼接的**目录名** | 同一目录相对真实 home 的名字 |

实测（omp v17.3.8，Windows 11）：`PI_CONFIG_DIR="cap-probe-config"` ＋ `PI_CODING_AGENT_DIR=<绝对路径>` → omp 正常启动，配置根落在 `~/cap-probe-config`，无翻倍。

cap 的托管运行时根按构造就在真实 home 之下（`$HOME/.agent-system-state/runtimes/omp/<id>`），因此总能表达为 home 相对名。运行时根若被显式配置到 home 之外，则该配置无法用 `PI_CONFIG_DIR` 表达，cap 显式失败而不是交出会被静默翻倍的绝对值。

## 修复后的实测结果

`uv run cap run agent-assembler` 在 Windows 上**成功拉起 omp**：不再有 `ENOENT`，omp 加载托管运行时（日志落在 `~/.agent-system-state/runtimes/omp/default/logs/`），进入模型调用。

## 仍未取得生效态证据的原因（与路径无关）

默认的共享运行时路径 `_agent_home_env` 会**主动删除** `OMP_AUTH_BROKER_URL` 与 `OMP_AUTH_BROKER_TOKEN` 并设 `PI_AUTH_NO_BORROW=1`，因此 `--auth-root` 提供的 broker 凭据在这条路径上不生效；omp 报 `No API key found for openai-codex`，并提示凭据应位于托管运行时自己的 `agent.db`。

`--auth-root` 的 broker 注入只发生在 profile engine 的一次性运行时路径（`_staged_auth`）。这两条路径的认证来源不同，是一个独立于本次修复的设计问题。

附带确认：负责人的 `openai-codex` OAuth 凭据**已在** broker vault 中（`migrate --dry-run` 报 `already on broker`），因此不需要迁移凭据；缺的是这条路径不读 broker。

## 对本仓的影响

- `cap render`／`cap show --cli omp`：Windows 正常。
- `cap run`／`cap use`：Windows 上**可以启动 omp**（本次修复），但默认路径拿不到 broker 凭据，因此 `agent-assembler` 的实际生效态仍为 `unknown`——原因从"上游阻塞"更正为"cap 内两条认证路径的来源不一致"。

## 同一次实测中发现的 cap 侧问题（已在 #98 修复）

`cap run` 拉起 omp 时未关闭 stdin，omp 停在 `readPipedInput` 等 EOF，实测干等 290 秒不返回。
