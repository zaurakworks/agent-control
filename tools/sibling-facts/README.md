# 兄弟 Session 事实查询

这个工具只回答一个瞬时问题：**本机现在还有谁在跑、各自可能写哪里、怎么核实？** 它把直接观察和未知分开，不产生所有权、不处置冲突，也不自动触发其他动作。

## 使用

```powershell
python tools/sibling-facts/sibling_facts.py
python tools/sibling-facts/sibling_facts.py --json
```

默认读取：

- `orca orchestration run-list --json` 与 `worker-list --json`；
- `orca terminal list --json`；
- `%LOCALAPPDATA%\agent-system\scheduler-lease.json` 中的 D9 持有者与 session；
- `agent-system` 当前 checkout 和 `~/workspace/work-skills` 的 `git worktree list --porcelain`；
- `zaurakworks/agent-system`、`Eridanus117/work-skills`、`Eridanus117/agent-plugins` 的开放 PR。

每条事实都带「谁／写哪儿／怎么核实」。如果一个来源缺失、命令失败、JSON 无法解析或返回截断标志，报告会明确写「未观察到」或「只观察到部分」，不会用其他来源推断补齐。

## 只读边界

工具没有写入或处置选项，也不写输出文件。它只执行固定的查询命令并读取租约文件：

- Orca：`run-list`、`worker-list`、`terminal list`；
- Git：`worktree list --porcelain`；
- GitHub：`pr list --state open`。

worktree 只证明登记存在，开放 PR 只证明远端分支存在；两者都不单独证明对应 Session 仍在跑。D9 租约只暴露当前调度持有者和 session，不提供完整写入范围，因此工具明确保留该范围为「未观察到」。

## 自检

```powershell
python -m unittest discover tools/sibling-facts/tests -v
python tools/sibling-facts/sibling_facts.py
python tools/sibling-facts/sibling_facts.py --json
```

本次交付的真实运行记录见 [VERIFICATION.md](./VERIFICATION.md)。建议的入口调用文本见 [ENTRYPOINT-PROPOSAL.md](./ENTRYPOINT-PROPOSAL.md)。
