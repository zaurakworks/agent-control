## 1. 声明模型与解析

- [ ] 1.1 在 `.cap` 声明格式中增加显式 public source、private overlay、selected profile 和 private namespace 字段，并拒绝未声明的 source。
- [ ] 1.2 扩展 profile resolver，构造 `real-home -> work -> public profile -> private profile` 单一有序链，校验继承环、路径越界、source 缺失和同名能力冲突。
- [ ] 1.3 保持 `add`、`mask`、`replace` 的能力级语义，记录每个 effective capability 的来源层和操作关系。
- [ ] 1.4 增加公共 profile 无私有层时的兼容路径，确保 `general` 与 `assembly-helper` 的既有声明结果不读取 ambient Skill。

## 2. Lock、binding 与摘要门禁

- [ ] 2.1 为 public source、private source、profile layer 和 effective render 定义独立 lock 数据结构及稳定规范化序列化。
- [ ] 2.2 更新 workspace pin、base manifest、derived binding 的校验，记录有序层 digest、renderer/adapter 版本和 stale 原因。
- [ ] 2.3 实现 active drift、passive drift、缺失 private binding 和摘要不匹配的 fail-closed 行为；禁止静默刷新 pin、lock 或旧 render。
- [ ] 2.4 实现删除 private binding 后公共 profile 的独立重建和回滚路径。

## 3. Digest 物化证据

- [ ] 3.1 增加 evidence CAS 目录、`evidence.json` 和 `entries.jsonl` 的规范化格式，覆盖 source、closure、layer merge 与 effective render。
- [ ] 3.2 实现安全物化 tree、secret/session/history/cache 排除 marker、路径与 mode 记录，并确保公共证据不含私有正文和路径。
- [ ] 3.3 实现 evidence index、物化 tree、source digest 与 effective digest 的一致性校验，拒绝证据缺失、篡改或一摘要多内容。
- [ ] 3.4 增加按层、profile、能力名和相对路径输出新增/删除/替换/mode/content 变化的 evidence diff 入口。

## 4. Prompt、Skill 与客户端渲染

- [ ] 4.1 将公共和私有 prompt、Skill 合并结果交给统一 effective inventory，再分别接入 Codex、Qoder、OMP renderer。
- [ ] 4.2 让每个 renderer 生成隔离的 effective generation，并把 client adapter、fixed gates 和生成结果纳入 effective digest。
- [ ] 4.3 保持客户端 user/project Skill 自动发现关闭，阻止 ambient 同名 Skill、用户 cache 和未绑定私有 source 注入。
- [ ] 4.4 更新运行 receipt、preview 和失败诊断，只输出 digest、evidence 路径和非敏感摘要。

## 5. 中文运行时合同与文档

- [ ] 5.1 更新中文 `SKILL.md`，说明显式私有 overlay、来源边界、层顺序、冲突操作和回滚语义。
- [ ] 5.2 更新 `docs/profile.md`、维护文档和 assembly README，区分声明态、配置态、effective 闭包和实际客户端生效态。
- [ ] 5.3 更新 `.cap` 示例、公共 lock/binding 示例和证据目录说明，确保不包含公司 Skill 正文、认证材料或 secret。

## 6. 验证与真实运行

- [ ] 6.1 增加 profile layer、能力冲突、source 隔离、私有回滚和公共兼容性的单元测试。
- [ ] 6.2 增加 evidence 物化、secret 排除、digest 重算、diff 和篡改拒绝的单元测试。
- [ ] 6.3 增加 lock/pin/binding active drift 与 passive drift 门禁测试，以及三类客户端 renderer 的 effective digest 测试。
- [ ] 6.4 运行 `npx openspec validate --change layered-capability-overlays --strict`、仓库测试、`cap verify` 和 `cap skills-validate`。
- [ ] 6.5 用公共 profile 和一个本地非敏感 private overlay 分别执行 Codex、Qoder、OMP smoke check，回读运行 receipt、evidence 和实际加载结果。
