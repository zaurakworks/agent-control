## 1. 重新装配合同

- [x] 1.1 clean cutover 将 profile、prompt 与总 Skill 从 `assembly-helper` 重命名为 `agent-assembler`。
- [x] 1.2 重写常驻 prompt 与总 Skill，定义完整装配执行、人工决定、派生状态和证据边界。
- [x] 1.3 从零声明完整能力闭包；`grilling` 常驻但保留明示同意门；MCP、Hook、Plugin 为空。

## 2. 项目 Skill source-path

- [x] 2.1 为 manifest 增加可选 `skill_imports` 声明和严格项目内路径校验。
- [x] 2.2 让 capability origin 指向最终源路径，正确 render project-defaults 与 imported Skills。
- [x] 2.3 把 project-defaults、runtime policy、import 声明与源树纳入 lock inputs。
- [x] 2.4 让 Skill 标准验证覆盖 imported `grilling`。

## 3. clean cutover 调用方

- [x] 3.1 更新 CAP role 常量、CLI 标签／示例、OMP migration 和单元测试，不保留旧 id。
- [x] 3.2 更新 README、CAP 指南、profile、maintenance、assembly 和 Skill 目录中的命名与合同。
- [x] 3.3 删除刚才误加的动态 role 设计，不修改 CAP 发现模型。

## 4. 装配声明与派生状态

- [x] 4.1 新增 `.cap/skill-imports.toml`，唯一引用 Plugin 中的 `grilling` 正文。
- [x] 4.2 刷新 `.cap/lock.json`，生成并批准当前 machine-context，重建 `general` 与 `agent-assembler` bindings。

## 5. 验证与证据

- [x] 5.1 运行 project Skill import、project-defaults render、lock drift 和重命名回归测试。
- [x] 5.2 运行 `cap skills-validate`、`cap agents`、`cap show agent-assembler`、`cap verify` 与 OpenSpec strict validation。
- [x] 5.3 实际打开 CAP TUI，确认 `general` 与 `agent-assembler`；render 并确认 `grilling` 与 inherited Skills 均存在。
- [x] 5.4 运行 OMP CLI smoke；没有可用认证时把模型行为生效态保持为 `unknown`。
