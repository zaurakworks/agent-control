## 1. 基线与认证门禁

- [x] 1.1 记录 `general`、`assembly-helper` 的公共 inventory 与 Codex/Qoder/OMP render tree hash，确认本变更不需要修改 `.cap` 声明、中文 `SKILL.md` 运行时合同或 `.cap/lock.json`
- [x] 1.2 在 `tools/cap.py` 实现持久 OMP 专用 auth-root 读取器：校验项目外私有目录、owner/mode、非 symlink、单一硬链接、受限大小稳定读取、broker metadata URL 与 token 格式，错误不输出 secret 或私有路径
- [x] 1.3 让持久 OMP `use`／`launch`／`run` 在 render 和创建客户端进程前加载同一 `<auth-root>/omp`，无效输入失败关闭且不读取 profile 本地认证

## 2. 运行环境与状态隔离

- [x] 2.1 扩展持久 OMP 环境构造：清除 ambient 客户端根与 provider/API/OAuth/cloud credential 变量，保留真实 `HOME`，设置禁止借用与 metadata 探测的防护值
- [x] 2.2 最后写入已验证的 `OMP_AUTH_BROKER_URL`／`OMP_AUTH_BROKER_TOKEN`，同时保持 `PI_CODING_AGENT_DIR`、`PI_CONFIG_DIR`、`PI_CONFIG_FILES` 按 profile 指向不同持久 agent home
- [x] 2.3 保持 render、`.cap-rendered`、binding、lock 与 receipt schema 不变，确保认证路径、URL、token、环境值和认证正文不落盘或进入错误输出

## 3. 聚焦行为测试

- [x] 3.1 扩展 `tests/test_cap.py`，用同一测试 auth root 覆盖两个 runnable profile 获得相同 broker 绑定、不同 agent home，并覆盖 ambient override 无效和 receipt 无 secret
- [x] 3.2 覆盖认证目录和文件缺失、权限过宽、非 owner、symlink、硬链接、大小越界、读取时替换、metadata 字段/URL 无效及 token 非法，断言均在 OMP runner 调用前失败
- [x] 3.3 覆盖 broker 环境优先级、真实 `HOME`、profile 配置/Session 根和现有 OMP 命令 allowlist 不回归，运行 `python3 -m unittest tests.test_cap`

## 4. 中文摘要文档

- [x] 4.1 更新 `README.md`，说明认证按 client 共享、配置和 Session 按 profile 隔离，以及 `<auth-root>/omp/{broker.json,token}` 的私有权限和无 secret 边界
- [x] 4.2 更新 `docs/maintenance.zh-CN.md`，记录 OMP 17.3.7 与公共 profile 工具的合同来源、broker host 上 `login`／`serve`／`status` 的预置流程、失败关闭行为及升级复核点
- [x] 4.3 明确 CAP 不托管 broker、不在 profile 内执行远端登录、不复制或删除旧 profile credential store，并且本变更不修改 prompt、Skill 或能力闭包

## 5. 配置态与生效态验证

- [x] 5.1 运行 `python3 tools/cap.py skills-validate` 与 `python3 tools/cap.py verify`，确认 Skill 标准合规、base binding 和现有 `.cap/lock.json` 通过；不得以这些结果代替共享认证生效证据
- [x] 5.2 重新采集两个 profile 的公共 inventory 与三客户端 render tree hash，逐项等于 1.1 基线；任何 `.cap` 声明、中文运行时合同或 lock/hash 变化均作为越界回归修复
- [x] 5.3 运行 `npx openspec validate share-omp-auth-across-profiles --type change --strict --json`
- [x] 5.4 在私有测试 broker 上仅登录一次 provider，先执行 `omp auth-broker status`，再分别用 `general` 与 `assembly-helper` 运行真实持久 OMP 请求，确认第二个 profile 不要求登录且两个 receipt 指向不同 agent home
- [x] 5.5 检查两次真实运行产生的 Session 仅出现在各自 profile 根，且输出、receipt、render 与诊断未出现认证路径、broker token 或环境值；据结果分别报告配置态与实际生效态
