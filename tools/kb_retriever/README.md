# KB Retriever

这是 `knowledge/retrieval-cards.md` 的真实可运行检索器。它读取结构化卡片，先按 `stage`／`object` 精确硬筛，再在候选卡的 `operation` 与 `signals.aliases` 上执行轻量 BM25，输出一张最短动作卡及其 `source`、`evidence` 标注。

本工具只依赖 Python 标准库，不建设语义层、向量库或索引服务，也不修改现有 K 包。当前产品证据上限仍是**小样回放有效**：两项真实任务的三个决策点可以复现 top-1 命中，但主动问路的自然采用率、误命中成本、长期召回和实际采用仍未验证。

卡片正文记录的历史回放分数与本工具输出的分数不可直接横比：前者来自当时的回放实现，本工具使用仓内固定的纯 Python 分词和 BM25 参数。可复核承诺是三决策点的 top-1 顺序，不是复刻旧分值。

## 使用

在仓库的 `tools/kb_retriever` 目录运行：

```text
cd tools/kb_retriever
python -m kb_retriever "stage=post-dispatch; object=orca.supervised-worker-dispatch; signals=worker-start 返回 input_accepted 后查 dispatch-show"
```

也可以把同一个参数写成 JSON 对象，并用 `--json` 取得机器可读结果。默认从当前目录和包目录向上寻找 `knowledge/retrieval-cards.md`；`--cards <path>` 可以显式指定只读卡片文件。

命中输出包括卡片、BM25 得分、`one-line-action`、`source` 与 `evidence`。如果 `stage`／`object` 没有候选，工具不会跨对象猜测，而是提示转回 `knowledge/README.md` 人工选择当前 K 包。唯一硬筛候选即使没有词法重合也会以 `matched-by-structure` 返回；多个候选均无词法重合时仍安全回退。

## 回放演示

从仓库根目录运行：

```text
python tools/kb_retriever/demo.py
```

演示依次回放派发回执、三端指纹和快照新鲜度三个真实决策点，打印预期卡、实际命中与 BM25 得分，并明确标注证据边界。

## 工作流采用

真实工作流怎样产生 `stage`／`object`／`signals`、怎样读取机器返回、怎样处置命中与未命中，见 [`ADOPTION.md`](./ADOPTION.md)。从仓库根目录运行集成示例：

```text
python tools/kb_retriever/examples/workflow_checkpoints.py
```

该示例在装端指纹验收、Token 燃烧测量决策与 worktree 删除前置门三个模拟场景中主动构造查询；它用于验证“查询—返回候选—调用者选择”的接线形状，不把演示结果提升为自然采用或产品采用证据。

本次端到端运行的命中卡、得分与演示内排除分支记录在 [`examples/DEMO_OUTPUT.md`](./examples/DEMO_OUTPUT.md)。

扩卡后的固定现有场景回放与自然旁路采集口径见 [`ADOPTION.md`](./ADOPTION.md) 的「自然旁路样本怎样记录」及 [`examples/NATURAL_BYPASS_EVIDENCE.md`](./examples/NATURAL_BYPASS_EVIDENCE.md)。可从仓库根目录复跑前后对比：

```text
python tools/kb_retriever/examples/evaluate_natural_bypass.py --baseline-ref a041aa06177b85357cb893305bb5cc6e9abb3c1a
```

评估器与固定样本只属于验证资产，不修改检索器生产代码，也不建立常驻监控。

## 测试

从仓库根目录运行：

```text
python -m unittest discover -s tools/kb_retriever/tests -v
```

测试覆盖 A–W 卡片与分桶快照、除显式登记单卡桶外每个 `stage`／`object` 桶至少两卡、A–C 既有正例 top-1、结构化硬筛、无候选回退、CLI 的来源／证据输出，以及已登记改述「配额读数没变还能否加开工作者」命中新增卡 N。历史回放中该改述曾略微误排到卡 A，前态固定分词又对同一句产生零词法命中；本批只是以同一现有场景补齐词法投影并验证排序，不把差异解释为语义能力或独立自然准确率提升。

### 语料快照约束

`tests/test_kb_retriever.py` 同时固定卡片标识符序列、`stage`／`object` 桶计数和已知单卡桶。任何加入、移除或重新分桶检索卡的变更，都必须在同一批更新这些快照并运行上述测试；否则测试保持红灯。单卡桶必须逐项显式登记，不能通过放宽其他桶至少两卡的约束来绕过。
