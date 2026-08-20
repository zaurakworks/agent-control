> 已提交：[can1357/oh-my-pi#9067](https://github.com/can1357/oh-my-pi/issues/9067)（2026-08-20，以 zaurakworks 身份）。
> **结果：`wontfix`。** 上游指出 `PI_CONFIG_DIR` 按设计就是相对 home 的目录名，`PI_CODING_AGENT_DIR` 才走 `path.resolve()`；
> 支持绝对值会改变 config-root 契约而非修复回归。诊断与隔离被确认准确，但定性有误——问题在 cap 的用法，已按契约修正。
> 详见同目录 [finding.md](./finding.md)。以下保留提交正文以便追溯。

---

**Title:** `PI_CONFIG_DIR` is joined onto the home directory on Windows, producing a doubled path

### Summary

On Windows, an absolute `PI_CONFIG_DIR` is concatenated onto the user's home directory instead of being used as-is, so omp tries to create a directory at `<home>\<absolute path>` and fails. `PI_CODING_AGENT_DIR` is handled correctly, which makes the two easy to confuse.

### Environment

| | |
| --- | --- |
| omp | `17.3.8` (also reproduced on `17.3.5`) |
| OS | Windows 11 Pro 10.0.26200 |
| Install | `bun` global — `C:\Users\<user>\.bun\bin\omp.exe` |

### Steps to reproduce

Run from any directory outside your home:

```bash
mkdir f
PI_CONFIG_DIR="C:/full/path/to/f" omp -p "hi" --no-session
```

### Expected

omp uses `C:\full\path\to\f` as its config directory.

### Actual

```
ENOENT: no such file or directory, mkdir 'C:\Users\<user>\C:\full\path\to\f\agent'
```

The home directory is prepended to a path that is already absolute.

### Isolation

Each row changes exactly one variable; the command is `omp -p "hi" --no-session` in a directory outside the home.

| Variables set | Result |
| --- | --- |
| `PI_CODING_AGENT_DIR` only (absolute) | **works** — directory created at the given location, run proceeds to the model call |
| `PI_CONFIG_DIR` only (absolute) | **fails** — `mkdir 'C:\Users\<user>\C:\...\f\agent'` |
| both, plus `OMP_PROFILE=default` and `PI_PROFILE=default` | fails |
| both, without the profile variables | fails |

The last two rows are identical, so the profile variables are not involved. On `17.3.5` the failure was also independent of whether `HOME` was set.

So the defect is specific to `PI_CONFIG_DIR`.

### Impact

Any tool that isolates omp's configuration by pointing `PI_CONFIG_DIR` at a managed directory cannot launch omp on Windows. Dropping the variable is not a workaround: without it omp reads `~/.omp/config.yml`, which defeats the isolation the variable exists for. Passing a relative value avoids the doubling but resolves against the current working directory rather than the home, which puts runtime state wherever the caller happens to be.

### Likely fix

Resolve `PI_CONFIG_DIR` (for example `path.resolve`) rather than joining it onto the home directory, matching how `PI_CODING_AGENT_DIR` is already handled.
