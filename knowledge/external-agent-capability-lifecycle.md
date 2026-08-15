# K10：外部 Agent Skill 与 Plugin 需要逐端验收和可恢复退场

> 状态：正式当前公共知识。
> 最近核验：2026-08-11。
> 适用对象：从外部 Git 仓库引入、评估、替换或退出的 Agent Skill／Plugin；Codex 与 Claude Code 多 Provider 环境。
> 环境：Windows 11；实证主样本为固定 revision `9add1cfab0eb71d48be76882df10e919782257a3` 的 codex-marketplace 三件 Plugin，以及当日 Agent Skills 规范与多个第一方项目说明。
> 版本边界：Provider 的 plugin、fork context、Hook、symlink／cache 或 Skill frontmatter 语义变化时，相关结论需逐端重新验收。

## 回答的问题与价值门

一份外部 Skill／Plugin 能被多个 Agent 发现或安装，是否就能证明它在各 Provider 中行为等价？如何在不丢失已需要能力的前提下评估、吸收和退出外部依赖？

外部能力会持续用于系统冷启动和能力替换。本机已完成过一批真实的三件 Plugin 固定版本盘点、影子核对、独立吸收和双运行面退出；过程中证明了安装与行为等价、功能与来源链、禁用与移除都不是同一件事。这些结论能直接降低后续外部能力替换的回退风险，通过价值门。

## 可直接复用的结论

### 1. 共享 `SKILL.md` 文件形状不等于跨 Provider 行为等价

Agent Skills 共享的文件与 frontmatter 形状只能降低搬运成本。核验时，`context: fork` 只在 Claude Code 中受支持，Hook 的支持面因 Agent 而异，`allowed-tools` 仍是实验字段，Codex 的 plugin manifest 路径选择和 cache copy 还使一个 symlink 方案在项目自身验证中落空。

因此，每个“Provider＋安装方式＋版本”都是独立验收对象。发现成功、安装命令成功或目录中存在 `SKILL.md` 都不能单独证明：触发条件等价、工具权限等价、上下文隔离等价，或运行端已加载目标内容。

### 2. 评估先固定来源和实际运行副本

进入影子核对前，至少记录：来源仓库、固定 revision、Plugin／Skill 清单、实际安装副本路径、版本、内容树指纹、端别启用面、主要调用边和已知回退方法。对 directory 型 marketplace，只读清单的 git revision 不足以证明安装内容；应对实际 cache、本地源树和固定 revision 的 Git 树逐路径核对。

来源、功能和文本复用是三个问题。某个 Plugin 能运行，不能推出其完整来源与许可链已可定位；本批实例中，Plugin manifest 虽有 MIT 字段，但源仓没有仓级 LICENSE／COPYING，NOTICE 还有浮动链接失效。对本系统的来源准入，这只足以采用“可用但不复制文本”的保守路径，不足以支持把外部正文复制、翻译或改写到自有资产。这是内部来源准入边界，不是对许可法律效力的通用判断。

### 3. 替换与退场按单项能力走完可恢复链

对每个 capability 分别执行，不以整个 Plugin 的“已安装”代替验收：

1. 写明当前实现、候选实现、固定来源、行为样例、通过证据与回退实现；
2. 先影子核对，再把主路切到候选实现，且保留已验证的旧实现作为可恢复退路；
3. 主路切换、禁用和移除是三个不同判断；能否同批处理由当次合同决定，不由前一阶段自动推得后一阶段；
4. 移除前固定回退快照，内含精确 revision、内容指纹、安装元数据与恢复命令；快照只证明恢复输入可定位，实际回退仍需单独演练；
5. 移除后同时检查配置、marketplace 注册、cache 和新 Session 可发现面。已打开的 Session 可能仍保留启动时加载的文本，不作为退场失败的单独依据。

本批三件外部 Plugin 的最终样本按固定 revision 逐文件核对，把需要的三组能力独立写成自有中文行为合同，再从普通 Codex 与 Orca Codex 两个运行面移除三件 Plugin；实际 cache、两面配置和 marketplace 清单均完成回读。

## 第一方来源与证据映射

1. [#43 的平台、Windows 与生态复用调研回执](https://github.com/Eridanus117/agent-control/issues/43#issuecomment-5253478669)：核对 Agent Skills 规范、多 Agent 兼容表、Codex plugin／symlink 失败样本和外部仓来源链；支持结论 1 与来源边界。
2. [#44 的三件 Plugin 盘点回执](https://github.com/Eridanus117/agent-control/issues/44#issuecomment-5254541385)：记录实际 cache、源树、固定 revision、调用边、文件级指纹与来源／NOTICE 链；支持结论 2。
3. [#44 的吸收核对终稿](https://github.com/Eridanus117/agent-control/issues/44#issuecomment-5256023899)：逐项说明值得吸收的能力、自有落点、不吸收部分和“独立重写、不复制外部正文”的来源边界。
4. [#44 的卸载终局回执](https://github.com/Eridanus117/agent-control/issues/44#issuecomment-5256071707)：记录固定回退快照、双运行面执行、配置／marketplace／cache 回读与新老 Session 可发现边界；支持结论 3。

## 两道准入门逐项判定

| 准入项 | 判定 | 依据 |
| --- | --- | --- |
| 价值门 | 通过 | 外部能力冷启动、影子对照、能力替换与退出会重复使用。 |
| 1. 明确回答的问题 | 通过 | 问题限定为跨 Provider 等价判断、固定来源与可恢复退场。 |
| 2. 可直接使用的结论和必要解释 | 通过 | 给出逐端验收原则、八类盘点信息和五步替换／退场链。 |
| 3. 第一方来源或可重复验证过程 | 通过 | 调研回执保存第一方规范与项目说明，三条实施回执保存可重复的真实样本。 |
| 4. 对象、版本、环境和核验时间 | 通过 | 页首列明外部样本的 revision、Provider 范围、Windows 环境与日期。 |
| 5. 例外、仍未知内容和不能推出的结论 | 通过 | 下节排除法律结论、未验新 Provider、活 Session 和其他 marketplace 的直接泛化。 |
| 6. 明确的失效条件 | 通过 | 下节列出 Agent Skills 规范、Provider 语义、来源链与安装布局变化。 |
| 7. 下次最少复核步骤 | 通过 | 只重读三类变化面，不重做完整盘点；只在变化后重跑目标端样本。 |
| 8. 人容易理解、Agent 足以复用的表达 | 通过 | 中文自足正文用三段结论和五步链给出直接执行方式。 |

## 例外、未知和不能推出的结论

- 本包不给出外部文本许可的通用法律结论；“不复制”是当次来源链不完整时的内部保守准入。
- 外部功能被独立重写成自有 Skill，不能推出两份文本或所有行为等价；应只验收明确写入的能力合同。
- 已打开的 Session 可能保留启动时文本；退出后的运行端判定以新 Session 与配置／cache 回读为准。
- 本批记录了可定位的回退输入和恢复命令，但没有实际重装该固定 revision；不能把快照完整误当成回退已通过。
- codex-marketplace 三件样本只覆盖 directory 型 marketplace、Codex 0.147.0 和两个本机运行面；不能直接泛化到 registry、云端或其他 Agent。
- 本包没有证明任一固定的外部能力切换状态数在所有任务中都是最优；核心要求是逐能力、有证据、可恢复。

## 失效条件

1. Agent Skills 规范或目标 Provider 改变 `context`、Hook、`allowed-tools`、manifest、symlink 或 cache copy 语义；
2. 新的逐端实测证明发现、权限、上下文隔离和工具行为在目标 Provider 中已等价；
3. 外部源的 revision、内容指纹、LICENSE／NOTICE 或主要调用边变化；
4. marketplace 类型、安装布局、cache 共享关系或 Provider 的新老 Session 加载语义变化；
5. 当前系统替换外部来源准入或能力退场的明确要求。

## 下次最少复核步骤

1. 只检查目标 Agent Skills 规范与 Provider 兼容说明中 `context`、Hook、`allowed-tools`、manifest 和 symlink／cache 语义；无变化时保留结论 1。
2. 对具体外部能力，仅回读它的固定 revision、内容树指纹、LICENSE／NOTICE 链、调用边和当前安装副本；任一项改变时再重跑影子样本。
3. 只在实际替换或退出前重做目标 Provider 的发现、触发、工具权限、输出形状和回退演练；完成后只更新变化的结论。

## 不适用范围

- 外部资产的通用法律意见；
- Plugin 选型排名或外部生态盘点；
- 未验证 Provider、云端环境或其他 marketplace 类型；
- 当前权威、授权或能力取舍本身。
