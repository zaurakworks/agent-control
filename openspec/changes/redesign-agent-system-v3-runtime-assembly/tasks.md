## 1. v3 源模型与路径

- [x] 1.1 定义 machine-context、asset-inventory、project-defaults、role profile、runtime policy 的 v3 数据模型
- [x] 1.2 将 `add`/`mask`/`replace` 替换为 `allow`/`deny`/`override`，定义冲突和优先级错误
- [x] 1.3 移除 `real-home`、`work`、`agent-home-root`、`base-*` 作为长期运行语义
- [x] 1.4 将用户级状态根迁移为 `$HOME/.agent-system-state`
- [x] 1.5 将持久 runtime 组织为 `runtimes/<client>/<runtime-id>/`
- [x] 1.6 定义 machine-context-pin、assembly-binding、asset-inventory manifest 和 runtime-manifest 的 schema

## 2. 资产观察与闭包验证

- [x] 2.1 实现无 secret 的 machine-context manifest、pin 和 active/passive drift 摘要
- [x] 2.2 实现 Agent-facing asset inventory，覆盖 capability plane 与 instruction plane
- [x] 2.3 实现 observed、allowed、stripped、blocked、unknown、reported_client_limited 状态
- [x] 2.4 实现默认拒绝和 active unknown fail-closed 校验
- [x] 2.5 实现 external import 的来源、digest、审批和 profile 绑定校验
- [x] 2.6 更新 lock、verify、show、agents 和 receipt，使声明态、配置态、生效态分层输出

## 3. OMP runtime policy

- [x] 3.1 定义 OMP 语义 runtime policy 与 OMP adapter allowlist
- [x] 3.2 实现按 `omp/<runtime-id>` 读取用户全局 preference 的受控入口
- [x] 3.3 实现系统门禁、项目 policy、role override、用户默认的固定合成顺序
- [ ] 3.4 将上下文压缩、advisor、预算等已验证字段投影到 OMP native config
- [x] 3.5 保持 OMP Session、history、agent.db、认证与 project capability closure 分离
- [x] 3.6 将 runtime policy digest、effective settings、generation 和 render hash 写入 OMP runtime-manifest/receipt
- [x] 3.7 保留未知或未验证 OMP 字段为未接入状态，不猜测 native 配置键

## 4. OMP render、启动与迁移

- [x] 4.1 让 OMP 临时 render 使用 v3 role、defaults、capability closure 和 runtime policy
- [x] 4.2 保留 OMP native `config.yml`、`mcp.json` 等文件名仅作为 adapter 输出
- [x] 4.3 更新 OMP launch/run 前的 lock、pin、binding、旁路和 generation 门禁
- [x] 4.4 实现旧状态到 v3 的 dry-run、apply、verify、quarantine 流程
- [x] 4.5 迁移旧状态根、pin、binding、OMP runtime 和旧配置，并报告丢弃项
- [x] 4.6 在冲突、权限、secret 或 digest 不明确时停止迁移并保持旧状态不变

## 5. 角色、文档与后续 adapter 合同

- [x] 5.1 将 `general`、`assembly-helper` 和未来 role 改为 v3 叶子 profile
- [x] 5.2 更新 `.cap` manifest、profile、prompt、能力索引和中文运行时合同
- [x] 5.3 更新 CLI 帮助、错误消息、维护指南和 CAP 中文入门中的 v3 名称与路径
- [x] 5.4 明确 Codex adapter 的 runtime policy projection、native 文件边界和 evidence ceiling
- [x] 5.5 明确 Claude adapter 的后续合同、未安装时的 unknown 边界和禁止的 OMP config 复用
- [x] 5.6 记录 OMP-only 当前实现范围，确保后续 Claude 实施者可仅凭变更包消费 v3 合同

## 6. 验证与交付

- [x] 6.1 更新 schema、profile、migration、runtime policy 和 lock 的单元测试
- [x] 6.2 验证未声明用户级 MCP/Skill/规则不会进入 OMP closure
- [x] 6.3 验证 external import 只对批准 profile 生效
- [x] 6.4 验证 machine-context active drift、runtime policy drift 和 render drift 的失败关闭行为
- [x] 6.5 验证 OMP 正常 run、跨项目共享 `omp/default`、不同 role override 和 receipt
- [x] 6.6 验证 migration dry-run/apply/quarantine/rollback 和冲突停止
- [x] 6.7 运行 `cap skills-validate`、OpenSpec strict validation、profile verify 和 OMP smoke/probe
- [x] 6.8 记录 OMP 实际生效态、Codex/Claude 未实施或 unknown 的证据边界
