# plugin_release

回答一个问题：**这台机器上的三个运行端此刻装的，是不是 `agent-plugins` 源仓当前的内容。**

## 为什么需要它

Plugin 的版本声明分散在六处（两端 `plugin.json`、两份 Marketplace、符合性声明、README 版本总览）。这六处是否互相自洽，`agent-plugins` 仓的 CI 已经能判定——`tests/workflow-routing.test.ts` 全部断言过。

CI 判定不了的是**本机安装态**：它看不见这台电脑。而运行端读的是安装副本，不是源仓。于是存在一种沉默故障——源仓合并了新版本，没人执行安装，三个运行端继续按旧内容干活，而所有远端检查都是绿的。

最危险的一种是 `modified`：**版本号相同、内容不同**。任何按版本号做的核对都会放行它。本工具按整树 SHA-256 比较，因此看得见。

## 用法

```
python tools/plugin_release/plugin_release.py check              # 默认；一致返回 0，漂移返回 1
python tools/plugin_release/plugin_release.py check --json       # 机器可读
python tools/plugin_release/plugin_release.py check --quiet      # 一致时不输出，只给退出码

python tools/plugin_release/plugin_release.py release <插件> [--part patch|minor|major]
python tools/plugin_release/plugin_release.py release <插件> --apply    # 默认演练，加 --apply 才执行
```

`release` 五步，任一步失败即中止：

1. **前置检查**——源仓存在、是 git 仓库、工作树干净（`--allow-dirty` 可放行，但发布会与你的改动混在一起）。
2. **同步六处版本声明**——每一处都必须恰好匹配一处；不是恰好一处就硬失败，因为发布时改错地方和漏改地方都是静默事故。
3. **跑符合性测试**——`targets.json` 里列出的两份，任一不过即停。
4. **安装到三个运行端**。
5. **指纹验收**——装完重新比对整树摘要。安装命令报成功但内容对不上时，不相信安装回执。

`release` 不提交、不开 PR、不合并。它结束时源仓有六处未提交改动，后续归你。

## 判定档位

| 档位 | 含义 | 是否失败 |
| --- | --- | --- |
| `ok` | 声明版本已装且整树逐字节一致 | 否 |
| `modified` | 声明版本已装，但内容不同——版本号在骗人 | 是 |
| `stale` | 只装着别的版本 | 是 |
| `missing` | 该运行端完全没装这个插件 | 是 |

另外报告「非当前版本的缓存目录」：只占盘，不影响正确性，因此不判失败。运行端不会自动清理它们（曾累积到 76 个）。

## 一个必须知道的事实

三个运行端的 `agent-plugins` Marketplace 都注册为**本机目录源，直接指向工作树**：

```
Claude      {"source": "directory", "path": "C:\\Users\\Morni\\workspace\\agent-plugins"}
Codex       source_type = "local", source = '\\?\C:\Users\Morni\workspace\agent-plugins'
Orca Codex  同上
```

因此「源」是工作树的**当前检出**，不是 `origin/main`。在 `agent-plugins` 里切到特性分支，运行端下次安装到的就是那个分支的内容。`check` 因此总是先报分支、干净度和相对上游的位置；不在 `main` 或工作树不干净时会额外提醒。

## 配置

`targets.json`：源仓位置、六处声明的路径模板、三个运行端的缓存根与安装命令。运行端路径按 `home` 或 `environment`（环境变量）解析，因此不把绝对路径写死在代码里。

Orca 内的 Codex 用 `CODEX_HOME` 指向它自己的运行时 home——已实测该覆盖对 `codex plugin` 生效。

## 边界

- 只读本机文件与源仓；`check` 不写任何东西。
- 不判定版本化来源是否自洽，那是 `agent-plugins` 仓 CI 的事。
- 不提交、不推送、不合并、不改远端。
- 不是常驻进程，没有轮询和调度器；要么你运行它，要么由会话启动钩子运行它。
