# 自有侧代码审查：PR #47（S3 入口单一真源生成器）

- 审查者：Claude 端自有能力（#49 影子对照·自有侧 A）
- 对象：已合并 PR #47 的全量 diff（8 个文件，约 1540 行；`gh pr diff 47`，远端只读）
- 方法注明：按合同先调用自有 code-review Skill，该调用进入后台分支、时限内未返回；本产物为直接审查（同一自有端能力的回退方式），如实注明。
- 现场验证：`tests.test_entry_sync` 12/12 通过；`scripts/test_federated_entry.py` 退出码 0；build/ 未跟踪状态与目标文件无代码围栏均已现场核验。

## 发现（按严重度）

### P0（阻断性缺陷）：无

### P1（应尽快面对的真实风险）：1 条

1. **合同极性守卫能力回退（设计取舍，但属真实回退）** — `scripts/test_federated_entry.py`（本 PR 删除段）
   本 PR 删除了校验器里的常量级内容锚点（`continuation_contracts`、`GLOBAL_WAVE_EXPECTED_SECTION`、三方镜像义务断言等），改为「repository-* 的声明式投影与单一真源一致」。此前校验器独立钉住已批准正文的极性（「不加载」「不是等价入口」等反转会被拦截）；现在只要 `entrypoints/agent-system.md` 本身被改写并重新生成投影，全部检查依然通过。`tests/test_federated_entry_validator.py` 同步把断言从 `assertTrue(checks[mirror_description])` 改为 `assertFalse(...)`，说明是有意设计，但保护层从「独立校验器常量」退到「对单一真源的人工审查」。
   失败场景：一次提交同时修改 `agent-system.md`（把某条规则反转极性）并再生成三个仓内投影——校验器与全部测试仍然全绿。
   建议：不必恢复旧常量，但应在验收面（Issue／PR 记录）明示该守卫层已移除，或对少量高危句保留一层独立极性抽查。

### P2（质量与潜在缺陷）：5 条

2. **build/ 输出目录未加入 .gitignore** — `scripts/entry_sync/__main__.py:98`（默认 `build/entry-sync`）
   `.gitignore` 只有 `__pycache__/`、`*.pyc`；首次实际运行 `generate` 后仓库已出现未跟踪 `build/`（本次审查现场可见 `?? build/`）。失败场景：一次 `git add -A` 把生成产物提交进仓。建议将 `build/` 加入 `.gitignore`。

3. **代码围栏内的 `#` 行会被误认为标题（潜在）** — `scripts/entry_sync/core.py:222-225`
   `HEADING_PATTERN` 以 MULTILINE 在全文匹配 ATX 标题，不识别 ``` 围栏。当前三个目标文件没有围栏（现场核验，暂无触发），但未来任何被镜像章节加入含 `# ` 行的代码块，会导致章节切分错误或「章节不唯一」误报。

4. **标题尾部 `#` 被剥离** — `scripts/entry_sync/core.py:223`
   title 组的 `[ \t]*#*[ \t]*$` 会把「C#」类标题剥成「C」，`find_markdown_section` 将找不到原标题。当前无此类标题，属边缘输入。

5. **`--scope installed` 与 `--write-repository` 组合静默无效** — `scripts/entry_sync/__main__.py:144-147`
   写回循环只处理 `repository` scope；该组合下无提示、无报错、无效果。建议 argparse 层直接拒绝或给出警告。

6. **mirror 声明的源节被重复解析** — `scripts/entry_sync/core.py:410-414` 与 `384-388`
   `apply_sections` 先对源节做 `_selector`＋`find_markdown_section`，`_render_source_section` 内再做一遍完全相同的解析与查找；可把已解析的源节传入以简化并减少一次全文扫描。

附注（不计入分级）：`scripts/test_federated_entry.py` 以 `from entry_sync import ...`（脚本目录路径）导入，`tests/` 以 `from scripts.entry_sync import ...`（命名空间包）导入；同进程混用会产生两个模块实例。当前用法互不相交，无实际冲突。

## 覆盖范围说明

- 覆盖：全部 8 个文件的全部改动（新增模块 `core.py`／`__main__.py`／`__init__.py`／`targets.json`／README、两个测试文件的改写、校验器的删改段）。
- 验证：单元测试与校验器实际运行；两个疑点（build/ 未忽略、围栏触发条件）现场核验。
- 未覆盖：未在干净环境重放 `generate --write-repository` 的写回路径（避免触碰仓内受跟踪文件）；未评估 targets.json 中 installed 三目标在缺失文件机器上的 check 行为（README 已声明用 `--scope repository` 规避）。
