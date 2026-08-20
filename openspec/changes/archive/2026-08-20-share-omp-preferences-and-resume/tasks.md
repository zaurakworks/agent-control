## 1. 共享 preference 与认证合同

- [x] 1.1 在 `.cap/runtime/omp.toml`、`src/agent_system/omp/runtime.py` 和中文运行时文档中定义并校验共享 preference source、字段 allowlist、固定安全门禁优先级与 source-state 摘要；验证未知／能力／路径字段不会进入 CAP native config。
- [x] 1.2 实现共享模型、`extendedContext`、thinking/tier、advisor、theme、statusLine、composer、显示和已批准 provider endpoint 的类型化投影，并把 redacted preference digest 与 allowlist version 纳入 generation/binding 失效判断；验证 preference 变化重建 generation，terra/luna 在 CAP 下保持 272K。
- [x] 1.3 实现普通 OMP 与 CAP 共用的私有认证 source adapter，明确 provider endpoint allowlist 与启动期 credential 注入；验证 API key/token/cookie/broker secret 不会出现在 render、lock、binding、generation、receipt、诊断或日志，且未批准来源 fail closed。

## 2. 跨 profile session resume

- [x] 2.1 固化同一 OMP runtime id 下 `general`、`agent-assembler` 和后续 CAP profile 的共享 session/history/models-cache/数据库根，并验证 profile 名或 generation hash 不会成为 session namespace；不为该目标引入 profile 专属 `--session-dir`.
- [x] 2.2 验证 OMP 原生 `/resume` 在同一工作目录发现另一 CAP profile 创建的 session，并以当前 profile 的 generation、模型、advisor、prompt 和能力闭包继续；不新增 profile metadata、picker 或 profile 专属 `--session-dir`。

## 3. 验证、证据与维护

- [x] 3.1 为 preference 合成、优先级、generation hash、redaction、provider/auth 拒绝路径、共享 runtime root、当前 profile 续接和 272K context cap 添加确定性单元与集成测试；运行受影响测试集。
- [x] 3.2 更新 `docs/profile.md`、`docs/maintenance.zh-CN.md` 和 `docs/cap-guide.zh-CN.md`，说明共享配置／认证／session 边界、跨 profile `/resume` 操作、占用处理、回滚与 secret 禁令；验证不再声称 advisor 等字段未接入。
- [x] 3.3 刷新 `.cap/lock.json` 与受影响 assembly binding，运行 `uv run cap verify`、OpenSpec strict validation，并在真实 OMP 中验证：普通 OMP preference 被两个 CAP profile 投影、`/resume` 选择另一 profile session 后按当前 profile 继续；分别报告声明态、配置态与实际生效态。