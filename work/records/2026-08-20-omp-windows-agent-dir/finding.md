# omp v17.3.5 在 Windows 上把绝对 `PI_CODING_AGENT_DIR` 拼成双份路径

> 非权威研发记录。结论只描述实测行为，不产生产品决定或授权。
> 相关规划：`openspec/changes/enable-windows-cap-assembly` 的任务 5.3。

## 现象

`uv run cap run agent-assembler --cli omp` 在 Windows 上无法启动客户端：

```
ENOENT: no such file or directory, mkdir
  'C:\Users\Morni\C:\Users\Morni\.agent-system-state\runtimes\omp\default\run\daemons\c47e5b440f203f8f\clients'
```

用户主目录被拼在了一个已经是绝对路径的值前面。

## 最小复现（不经过 cap）

环境：Windows 11 Pro 10.0.26200，omp v17.3.5（`C:\Users\Morni\.bun\bin\omp.exe`）。

```bash
mkdir ompdir

# A. 绝对 PI_CODING_AGENT_DIR，设 HOME
HOME="C:/Users/Morni" \
PI_CODING_AGENT_DIR="<abs>/ompdir" \
omp -p "say ok" --no-session
# -> ENOENT ... mkdir 'C:\Users\Morni\<abs>\ompdir\run\daemons\...\clients'

# B. 绝对 PI_CODING_AGENT_DIR，不设 HOME
env -u HOME PI_CODING_AGENT_DIR="<abs>/ompdir" omp -p "say ok" --no-session
# -> 同样的 ENOENT，路径同样翻倍

# C. 不设 PI_CODING_AGENT_DIR
omp -p "reply with exactly: OK" --no-session
# -> OK

# D. 相对 PI_CODING_AGENT_DIR
PI_CODING_AGENT_DIR="some/relative/dir" omp -p "say ok" --no-session
# -> 不翻倍，但相对 **cwd** 解析，不是相对 home
```

## 结论

1. omp 对 `PI_CODING_AGENT_DIR` 做的是拼接而不是解析，绝对 Windows 路径因此翻倍。
2. **与 `HOME` 是否设置无关**：A 与 B 行为相同。这一点否掉了"Windows 客户端读 `USERPROFILE` 而 cap 只设了 `HOME`"这个此前的猜测。
3. 相对值可以避开翻倍，但它相对 cwd 解析。cap 把 cwd 设为项目根，因此相对值会把运行时状态写进项目——不是可用的绕过方式，实测确认过并已回退。
4. C 证明 omp 本身在本机工作正常，问题只在被传入绝对 `PI_CODING_AGENT_DIR` 时出现。

## 对本仓的影响

- `cap render`／`cap show --cli omp` 不受影响，Windows 上正常。
- `cap run`／`cap use` 的 omp 客户端在 Windows 上无法启动，因此 `agent-assembler` 的**实际生效态保持 `unknown`**，不是"验证未做完"而是"被上游阻塞"。
- cap 侧不做绕过：唯一可行的绕过会改变路径解析基准并污染项目，代价高于收益。

## 同一次实测中发现的 cap 侧问题（已修）

`cap run` 拉起 omp 时未关闭 stdin，omp 停在 `readPipedInput` 等 EOF，实测干等 290 秒不返回。`run` 是批处理入口，应传 `stdin=DEVNULL`；`use` 是交互入口，必须保留真实 stdin。修复后 omp 立即越过启动阶段进入模型调用。

该修复的端到端效果在 Windows 上被上述上游 bug 遮挡，因此以 `_client_stdin` 的单元测试固定契约。

## 未验证项

broker vault 为空（只跑了 `omp auth-broker serve`，未执行 `migrate --include-oauth` 上传凭据），因此即使启动成功也拿不到模型回答。上传 OAuth 凭据是对负责人认证配置的持久改动，未经具体确认不执行。
