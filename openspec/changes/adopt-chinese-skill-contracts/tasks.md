## 1. 规则切换

- [x] 1.1 更新 `AGENTS.md`，将中文 `SKILL.md` 设为唯一执行合同并取消双语全文要求。
- [x] 1.2 更新 OpenSpec context，使后续运行时 Skill 和人读资产默认使用中文。

## 2. 运行时合同迁移

- [x] 2.1 将所有现有 Skill 的 frontmatter `description` 和正文迁移为中文，保持 `name` 和目录 id 不变。
- [x] 2.2 检查 Skill 路由边界、命令、路径和标准字段没有因翻译改变机器语义。

## 3. 删除重复文档

- [x] 3.1 删除 `docs/skills/*.zh-CN.md` 全文镜像。
- [x] 3.2 更新 Skill 目录、README 和维护指南，直接链接中文运行时合同并移除双语同步流程。

## 4. 验证与归档

- [x] 4.1 刷新 `.cap/lock.json`，运行 Skill 标准验证和 profile 闭包验证。
- [ ] 4.2 运行 OMP Skill inventory 和中文路由 smoke，记录 Codex/Qoder unknown。
- [ ] 4.3 运行 OpenSpec strict validation，完成任务证据并归档本 change。
- [x] 4.4 继续 `harden-assembly-helper-maintenance`，确保新增 Skill 直接使用中文。

### 当前证据

- `python3 tools/cap.py skills-validate`：7 个 Skill，`standard_conformance: ok`。
- `python3 tools/cap.py ... verify`：`status: ok`。
- `npx openspec validate adopt-chinese-skill-contracts --strict --json`：通过。
- OMP 运行基线已通过：隔离 `assembly-helper` profile 输出 `RUNTIME-OK`，对应收据为 `exit_code: 0`。Skill inventory 和中文路由 smoke 尚未执行，Codex、Qoder 生效态仍为 `unknown`，因此本 change 尚未归档。
