# Knowledge named-route query

This explicitly invoked tool returns the smallest current knowledge route for a named
action. It is intentionally narrower than general search: the supported entry point asks
for one identifier from [`routes.json`](./routes.json), and the result names the current
source package instead of copying or rewriting its conclusions. The historical directory,
script, schema, and Python class names are retained for compatibility.

Two blind spots are registered initially:

- Windows PowerShell plus GitHub multiline Markdown →
  `knowledge/windows-powershell-multiline-transfer.md`;
- Windows path-length or file-lock diagnosis → `knowledge/windows-agent-ops.md`.

The query only returns guidance. It does not monitor actions, run the proposed action,
mutate knowledge, grant permission, or continue from an invalidated source.

## Explicit named lookup

When the caller wants local guidance for one of these actions, it actively asks by name.
From this repository, run one of:

```text
python tools/knowledge_action_trigger/action_trigger.py --action github-multiline-markdown
python tools/knowledge_action_trigger/action_trigger.py --action windows-path-or-file-lock
```

The result names the exact source file to read and reminds the caller that the source's
invalidation conditions and the current task contract still apply. The tool never fires
automatically, injects context, or requires a Hook. A caller may also read either source
file directly when it already knows the name or the query tool is unavailable.

## Retained Hook adapter: not adopted

The previously merged `--hook` adapter remains in the codebase for compatibility and
historical traceability. **本系统不安装；原因是注入式投递已被负责人否决（见
[关联 #251（动作型知识触发）251-D1](https://github.com/Eridanus117/agent-control/issues/251#issuecomment-5288572032)）。**

There is no installation, configuration, or Hook-mounting path for this adapter in the
Agent system. The supported path is the explicit `--action <name>` query above: ask when
guidance is wanted, then choose whether to read the returned source.

## Verification

From the repository root:

```text
python -m unittest discover -s tools/knowledge_action_trigger/tests -v
```

Tests cover both registered blind spots, false-positive rejection, explicit action
queries, the retained adapter's compatibility and fail-open behavior, the README's
non-adoption contract, and source-path containment.
