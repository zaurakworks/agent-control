# omp 在 Windows 上把绝对 `PI_CONFIG_DIR` 拼成双份路径

> 非权威研发记录。结论只描述实测行为，不产生产品决定或授权。
> 相关规划：`openspec/changes/enable-windows-cap-assembly` 的任务 5.3。
> 待提交上游的报告正文见同目录 [`upstream-issue.md`](./upstream-issue.md)。

## 更正说明

本文件 2026-08-20 首版把原因记为 `PI_CODING_AGENT_DIR`。**该结论是错的**：当时的两组对照同时设置了 `PI_CODING_AGENT_DIR` 与 `PI_CONFIG_DIR`，因此无法区分二者。逐个变量隔离后确认触发者是 `PI_CONFIG_DIR`。同时首版记录的版本 `v17.3.5` 在会话期间已自更新到 `v17.3.8`，问题在新版本上依然存在。

## 现象

`uv run cap run agent-assembler --cli omp` 在 Windows 上无法启动客户端：

```
ENOENT: no such file or directory, mkdir
  'C:\Users\Morni\C:\Users\Morni\.agent-system-state\runtimes\omp\default\run\daemons\...\clients'
```

用户主目录被拼在了一个已经是绝对路径的值前面。

## 逐变量隔离（omp v17.3.8，Windows 11 Pro 10.0.26200）

每组只改一个变量，命令固定为 `omp -p "hi" --no-session`，cwd 为一个项目外的临时目录。

| 组 | 设置的变量 | 结果 |
| --- | --- | --- |
| E | 仅 `PI_CODING_AGENT_DIR`（绝对） | **正常**：目录建在给定位置，进入模型调用 |
| F | 仅 `PI_CONFIG_DIR`（绝对） | **翻倍**：`mkdir 'C:\Users\Morni\C:\Users\Morni\...\f\agent'` |
| A2 | 两者 + `OMP_PROFILE=default` + `PI_PROFILE=default` | 翻倍 |
| A3 | 两者，不设 profile 变量 | 翻倍 |

A2 与 A3 相同，说明 profile 变量不是触发条件。E 与 F 的对比把触发者定在 `PI_CONFIG_DIR`。

补充：在旧版 v17.3.5 上，设与不设 `HOME` 的两组行为一致，因此主目录变量也不是触发条件。

## 结论

1. omp 对 `PI_CONFIG_DIR` 做的是拼接而不是解析，绝对 Windows 路径因此变成 `<home> + <绝对路径>`。
2. `PI_CODING_AGENT_DIR` 在 v17.3.8 上处理正确，不是原因。
3. 与 `HOME`、`OMP_PROFILE`、`PI_PROFILE` 均无关。

## 为什么 cap 侧不做绕过

`PI_CONFIG_DIR` 是 cap 隔离客户端配置的手段。实测组 E（不设 `PI_CONFIG_DIR`）中，omp 读取了用户目录下的 `~/.omp` 配置并据此选择模型——这正是本仓"业务能力不得从用户目录隐式补齐"这条边界要防的事。因此不能靠去掉 `PI_CONFIG_DIR` 绕过；`--config` 是叠加式覆盖，也不提供隔离。

另一种绕法是改传相对路径：它避开翻倍，但相对 **cwd** 解析，而 cap 把 cwd 设为项目根，会把运行时状态写进项目。实测确认过并已回退。

结论是等待上游修复。

## 对本仓的影响

- `cap render`／`cap show --cli omp` 不受影响，Windows 上正常。
- `cap run`／`cap use` 的 omp 客户端在 Windows 上无法启动，因此 `agent-assembler` 的**实际生效态保持 `unknown`**，属于被上游阻塞而非验证未做完。

## 同一次实测中发现的 cap 侧问题（已在 #98 修复）

`cap run` 拉起 omp 时未关闭 stdin，omp 停在 `readPipedInput` 等 EOF，实测干等 290 秒不返回。`run` 是批处理入口，应传 `stdin=DEVNULL`；`use` 是交互入口，必须保留真实 stdin。

## 未验证项

broker vault 为空（只跑了 `omp auth-broker serve`，未执行 `migrate --include-oauth` 上传凭据），因此即使启动成功也拿不到模型回答。上传 OAuth 凭据是对负责人认证配置的持久改动，未经具体确认不执行。
