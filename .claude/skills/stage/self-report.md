# 运行面自述

**这是量具，不是产品规则。**只在核验配置漂移时注入，普通运行不带它——否则每次交付都会拖一段运维输出。

由 `tools/profile` 在 manifest 里显式打开（`[prompt] self_report = true`）。

---

产出末尾必须有这四行，逐字照抄标记名（格式是给机器读的）：

``SKILLS-AVAILABLE: 逗号分隔的全部可用 skill 名``
``SKILLS-LOADED: 逗号分隔的本次实际加载的``
``MCP-AVAILABLE: 逗号分隔的全部可用 MCP server／连接器名``
``CONTEXT-FILES: 逗号分隔的被自动加载为指令的文件绝对路径（CLAUDE.md、AGENTS.md 之类）``

- 确实为空写 `none`；看不到、判断不了写 `unknown`。**这两个不是同义词**——`none` 是观察结果，`unknown` 是观测失败。
- `CONTEXT-FILES` 只算运行时**自动**加载为指令的，本次任务自己去读的普通文件不算。
- 只报实际看得见的。为了填满而推断出来的清单比空清单更有害：它会让漂移检测报无漂移。
