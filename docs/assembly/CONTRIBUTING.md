# Contributing to Agent System assembly

本目录说明根 `.cap` 的项目内 Agent 装配声明；它不是全局能力安装器。

## Scope

- Keep runtime capabilities under `.cap/capabilities/`.
- Reference every runtime capability from an explicit profile.
- Keep the Chinese `SKILL.md` as the only full execution contract.
- Do not add secrets, credentials, personal runtime state, or user-level configuration.
- Do not introduce MCP, hooks, plugins, or external repositories as implicit dependencies.

## Change shape

For a non-trivial behavior change, include:

1. purpose and non-goals;
2. observable behavior delta;
3. prompt/skill/profile design;
4. verification and remaining unknowns.

Use the repository-root `openspec/` workflow for non-trivial behavior changes.

## Checks

From the repository root:

```bash
uv run cap verify

git diff --check
```

If the selected profile changed, refresh the lock first:

```bash
uv run cap lock
```

Runtime claims require a focused client run or probe. A passing lock only proves the configured declaration is internally consistent.
