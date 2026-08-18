# 1. 声明与运行时合同

- [x] 1.1 新增 `general` prompt、profile，并注册到 manifest
- [x] 1.2 新增六个中文 OpenSpec 1.9.0 Workflow Skills
- [x] 1.3 将六个 OpenSpec Skills 显式加入全部工作 profile

# 2. 摘要与锁

- [x] 2.1 更新 README 与中文 Skill 目录，写明 general 和 resume 入口
- [x] 2.2 重建 `.cap/lock.json` 并核对两个 profile 的三端闭包

# 3. 验证

- [x] 3.1 运行 Skill 标准验证与 OpenSpec strict validation
- [x] 3.2 运行 CAP verify，并分别渲染 general 的 Codex、Qoder 与 OMP 结果
- [x] 3.3 运行 general 的真实 OMP Skill 发现 smoke check
- [x] 3.4 验证 `--resume` 参数可由 CAP 透传；无法取得可用 Session 路径时仅报告到配置态
