## 1. OpenSpec 基础

- [x] 1.1 固定仓库内 OpenSpec 版本，并在禁用客户端产物生成的条件下初始化 `openspec/`。
- [x] 1.2 配置项目上下文、各类资产规则以及 apply/archive 指引。
- [x] 1.3 根据 CLI JSON 指令创建 proposal、delta specs、design 和实施任务。

## 2. Skill 标准合规

- [x] 2.1 为所有既有运行时 Skill 添加必需的 `name` 和面向触发条件的 `description` frontmatter。
- [x] 2.2 在 `tools/cap.py` 中增加确定性 Skill 元数据验证；元数据无效时，`verify` 必须在闭包验证前失败。
- [x] 2.3 分别使用当前有效仓库和临时畸形 Skill fixture 验证检查器。

## 3. 装配行为合同

- [x] 3.1 新增 `agent-skill-design` 和 `agent-behavior-evaluation` 中文运行时合同。
- [x] 3.2 加强 `assembly-helper`、`agent-prompt-design`、`capability-lifecycle` 和 `capability-profile-closure` 的调研优先和评测意识。
- [x] 3.3 更新常驻 prompt，加入调研触发、来源优先级、评测义务和简洁 Skill 路由。
- [x] 3.4 在 `assembly-helper` profile 中声明两个新增 Skill，不新增 MCP、Hook、Plugin 或 ambient 客户端路径。

## 4. 审查文档

- [x] 4.1 以中文 `SKILL.md` 作为唯一全文合同，不新增双语全文镜像。
- [x] 4.2 更新 Skill 目录、README 和维护指南，覆盖 OpenSpec、标准验证、调研和行为证据。
- [x] 4.3 记录仓库内 OpenSpec 命令，以及选择 `--tools none` 的明确边界。
- [x] 4.4 确保 OpenSpec 中供人阅读的正文均为中文，仅保留解析所需的英文结构关键字。

## 5. 验证与证据

- [x] 5.1 在声明变更后刷新 `.cap/lock.json`。
- [x] 5.2 运行 OpenSpec strict validation、Skill 元数据验证、`.cap` 闭包验证和最终 profile inventory。
- [ ] 5.3 运行 OMP smoke check，覆盖外部调研触发、纯仓库任务不触发网络调研、三态结论边界。
- [x] 5.4 记录观察输出和仍未知的 OMP/Codex/Qoder 状态，不把配置态证据泛化到实际运行。
- [ ] 5.5 归档已验证 change，使 delta requirements 成为长期规范。

### 当前证据

- OpenSpec 两个活动 change 均通过 strict validation。
- `skills-validate` 对 7 个当前 Skill 返回 `standard_conformance: ok`；缺少 frontmatter 的临时 fixture 返回 exit 2。
- `cap verify` 返回 `status: ok`，profile inventory 包含 7 个 Skill，MCP、Hook、Plugin 仍为空。
- OMP 运行基线已通过：隔离 `assembly-helper` profile 经全局 Auth Broker 调用模型并输出 `RUNTIME-OK`，运行收据记录 `exit_code: 0` 和渲染 tree hash `sha256:3ea37b145234862cb53dbed24b53cc74afede923557831dd5667c749aa07636f`。该结果只证明认证可达、模型可选和 profile 进程成功，不证明 5.3 所列调研路由与三态边界；Codex、Qoder 生效态仍为 `unknown`，因此 change 尚未归档。
