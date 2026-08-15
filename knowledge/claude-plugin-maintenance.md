# K4：Claude Code 与 Codex Plugin 维护、验收的已验证陷阱

> 状态：正式当前公共知识。
> 最近核验：2026-08-11。
> 适用对象：Claude Code 与 Codex 的 plugin 安装、版本化缓存与 Skill description 加载；directory 型 marketplace（本机 agent-plugins 仓）。
> 环境：Windows 11 本机；核验时 Claude Code CLI 为 2.1.227、Codex CLI 为 0.147.0（2026-08-11）。
> 版本边界：任一端 CLI、缓存布局或 marketplace 类型变化即为失效信号；Orca 专用 `CODEX_HOME` 的 Junction 消失或改指向时，单份存储结论失效。

## 回答的问题与价值门

升级一个已安装的 Claude Code plugin，直接 `plugin install` 有效吗？Skill 的 description 有没有长度约束？三端指纹验收应如何从按版本分目录的 Claude／Codex 缓存中选中正确副本？Codex 对 directory 型 marketplace 的安装与升级语义是什么？

本系统所有 Skill 改动都要经 agent-plugins 三端安装才真正生效。Claude 端升级假阳性与 description 截断各造成过一次真实故障；Claude 缓存跨版本通配又在本次验收中造成一次假不一致警报。结论会在后续每次 Skill 发布与三端指纹验收时复用，并补全既有知识未覆盖的 Codex 端安装语义，通过价值门。

## 可直接复用的结论

### 1. plugin install 对已安装项是无操作（升级假阳性）

Claude 端 `plugin install` 对已安装的 plugin 不报错也不更新——得到「安装成功」但运行端内容未变。真正升级必须先 `plugin uninstall` 再 `plugin install`。验收不能相信安装命令的输出，要对运行端实际加载的缓存副本做内容指纹核验（换行规范化后 SHA-256 与版本化来源比对，方法见 K6），而不是相信 marketplace 清单的自述版本号。

### 2. Skill description 超过 1536 字符被无声截断

运行端对 Skill description 存在 1536 字符上限，超出部分无声截断、不报错。真实事故：issue-workflow 的 description 长 1999 字符，结尾整批「不要用它做什么」边界条款被截掉，构成静默故障；修复为压缩至 1515 字符，并把该上限写成 agent-plugins 仓会失败的符合性断言。编写 description 时把最重要的触发与边界条款放在前部，长度留出余量。

### 3. 两端缓存按版本分目录，但历史版本保留语义不同

Claude 与 Codex 的 plugin 缓存均采用 `cache/<marketplace>/<plugin>/<version>/` 布局，但历史版本保留语义不同：Claude 经 uninstall／install 升级后仍保留旧版本目录，实测为多版本并存；Codex 经 remove／add 升级后会清除旧版本目录，只保留当前版本，两次实测结果一致。

三端指纹验收在任何一端都必须先确定本批目标版本，再分别锁定 Claude 与 Codex 的该版本目录；不得以跨版本通配得到的任一命中项代表当前安装副本。Claude 端尤其会因多版本并存而命中旧副本，产生内容已经正确却被报为不一致的假警报。本次 Skill 批次四验收即先出现这类假警报；锁定目标版本目录后，再对仓库源、Claude 缓存与 Codex 缓存做 LF 规范化 SHA-256 比对，四个改动 Skill 全部一致。换行规范化仍按 [K6](./newline-normalized-acceptance.md) 的方法执行；本结论补充的是指纹计算之前的版本选择前提。

### 4. Codex 的 directory 型 marketplace 安装语义

Codex 端移除与安装 plugin 时，`codex plugin remove` 和 `codex plugin add` 都使用 `<plugin>@<marketplace>` 形式。directory 型 marketplace 不支持 `codex marketplace upgrade`，命令报告「not configured as a Git marketplace」属于预期行为；这不能据以判断安装失败，应按移除、重新安装和目标版本目录指纹验收完成升级。

本机普通 Codex 与 Orca 专用 `CODEX_HOME` 的 `plugins`、`skills` 已经由 Junction 桥接为单份存储；因此从 Orca 环境执行安装仍写入同一份 plugin 缓存。该结论只描述当前落点，不表示两套 `CODEX_HOME` 的配置文件或用户级入口也已合并。

## 第一方来源

- 关联 [#44](https://github.com/Eridanus117/agent-control/issues/44)：Claude 端 `plugin install` 对已安装项无操作，需先 uninstall 再 install，及其三端 LF 规范化 SHA-256 指纹核验记录；
- 关联 [#44](https://github.com/Eridanus117/agent-control/issues/44)：「Skill 维护批次二交付」记录了 1999 字符被 1536 上限无声截断的实例与 1515 字符修复；
- 关联 [#44](https://github.com/Eridanus117/agent-control/issues/44)：2026-08-11「安装验收记录：Skill 批次四三端指纹核验」及后续勘误记录了两端按版本分目录、Claude 保留历史版本而 Codex remove／add 清除旧版本、Claude 跨版本通配先触发假不一致、锁定目标版本后复核通过，以及 Codex 的安装参数与 directory 型 marketplace 升级语义；
- [`authority/00-map.md`](../authority/00-map.md) 中 44-Dc 事实句：普通 Codex 与 Orca 专用 `CODEX_HOME` 的 `plugins`、`skills` 经 Junction 桥接为单份存储；
- Eridanus117/agent-plugins[#34](https://github.com/Eridanus117/agent-plugins/issues/34)、[#35](https://github.com/Eridanus117/agent-plugins/issues/35)：修复与符合性断言所在 PR。

## 例外、未知和不能推出的结论

- 只核验 directory 型 marketplace；registry 型或其他安装源未测。
- 1536 上限来自运行端观察，未见官方文档承诺该数值；不能推出其他字段（如 SKILL.md 正文）有同样上限。
- Codex 结论只覆盖本机 2026-08-11 的 `remove`／`add` 与 directory 型 marketplace 行为；registry 型 marketplace、其他操作系统和其他安装命令未测。
- Claude 多版本并存不表示运行端一定加载目录中版本号最大或修改时间最新的副本；当前加载版本仍须由本批发布目标与安装结果共同确定。
- Codex 清除旧版本的结论限于 remove／add 路径；不能推出其他安装或迁移路径也会清除历史目录。
- Junction 只合并 `plugins`、`skills` 的存储落点；不能推出两套 `CODEX_HOME` 的配置文件和用户级 `AGENTS.md` 相同。

## 失效条件

1. Claude Code 更新 plugin 安装语义（例如提供真正的 upgrade／reinstall 动词）；
2. description 上限数值或截断行为变化；
3. Claude 或 Codex 的缓存不再采用 `cache/<marketplace>/<plugin>/<version>/`，Claude 升级开始清除历史版本，或 Codex remove／add 不再清除旧版本；
4. Codex 改变 `<plugin>@<marketplace>` 参数形式，或 directory 型 marketplace 开始支持 `marketplace upgrade`；
5. marketplace 类型改变；
6. Orca 专用 `CODEX_HOME` 的 `plugins`／`skills` Junction 消失或改指向。

## 下次最少复核步骤

1. 下次 plugin 升级时先不 uninstall 直接 install 一次，对运行端副本做规范化指纹对比：指纹变了则结论 1 失效，照旧未变则结论继续成立（随后按正确流程完成升级）；
2. 确认 agent-plugins 的 description 长度符合性断言仍存在且通过；怀疑上限变化时，用一个超长 description 的探测 Skill 观察截断点；
3. 每批三端指纹验收先写下目标 plugin 版本，列出 Claude 缓存中的现存版本，再分别确认 Claude 与 Codex 的 `cache/<marketplace>/<plugin>/<version>/` 精确目标目录存在；只对这两个目标版本目录与仓库源执行 K6 的 LF 规范化 SHA-256 比对，出现不一致时先列出实际命中的完整路径和版本，再判断内容差异；
4. 下次 Codex plugin 升级时，以 `<plugin>@<marketplace>` 分别执行 remove／add，并确认旧版本目录消失、目标版本目录出现；directory 型 marketplace 仍报告「not configured as a Git marketplace」时维持当前结论，若旧目录仍在或 upgrade 成功则重审；
5. Orca 宿主或 `CODEX_HOME` 配置变化后首次安装前，确认 Orca 专用 `CODEX_HOME` 的 `plugins`、`skills` 仍为指向普通 `.codex` 同名目录的 Junction；任一项不成立即停止复用单份存储结论。
