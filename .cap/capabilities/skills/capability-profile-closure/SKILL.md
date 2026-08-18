---
name: capability-profile-closure
description: 审计项目内 Agent manifest、profile、prompt、Skill、MCP、Hook、Plugin、lock 状态和运行证据。创建或修改 `.cap` 声明，或需要区分闭包、Skill 标准合规、配置态和生效态时使用。
---

# capability-profile-closure

## 流程
1. 从任务定位活动项目根目录，并要求项目内存在 `AGENTS.md` 和 `.cap/manifest.toml`。缺少任一文件时发出警告，只在请求范围内继续；绝不从用户目录补全。
2. 检查声明闭包：
   - manifest 列出所有可选 profile，且只使用项目内 profile 路径；
   - 每个 profile 只有一个 prompt 路径，并显式声明 `skills`、`mcps`、`hooks`、`plugins` 数组；
   - 每个引用能力都存在于 `.cap/capabilities/<kind>/`；
   - 每个现有能力均被引用，或被明确报告为有意未使用。
3. 单独检查 Skill 标准合规：必需 frontmatter、与目录一致的有效小写连字符 `name`、说明触发条件的非空 `description`，以及有效项目内引用。
4. 检查路径卫生：使用 POSIX 相对 `.cap/...` 路径，不依赖 symlink、用户级 overlay、provider 原生全局根目录或 secret 文件。
5. 在所有结论中分开证据：
   - 标准合规：机器可读 Skill 元数据和结构；
   - 声明态：manifest、profile、prompt 和能力文件；
   - 配置态：lock、render tree 和 materialized client config；
   - 生效态：观察到的客户端运行、probe 或环境结果。
6. 优先运行只读检查：`cap skills-validate`、`cap agents`、`cap show <profile>` 和 `cap verify`。只有声明确实改变后才运行 `cap lock`。
7. 把 stale lock、无效元数据、未知效果、不透明 Hook 或 Plugin staging，以及客户端可观察性限制报告为风险，不转写为成功。

## 完成条件
只有当 Skill 元数据验证和选定 profile 的 lock/verify 均通过，所有声明能力位于项目内，且交付准确标明已检查的证据层时，闭包才算完成。
