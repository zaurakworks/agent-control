# Entry sync

`entrypoints/agent-system.md` is the only source for shared Agent-system entry text.
`targets.json` declares the three repository projections and three installed full-copy
targets. Repository-only text and shortest backreferences to the shared source are marked
`target_specific`; only installed targets receive the complete shared text.

Generate every target into a staging directory and print the source-to-destination map:

```text
python -m scripts.entry_sync generate
```

The command never writes `~/.claude`, `~/.codex`, or `%APPDATA%`. Pass
`--write-repository` only to update the three repository targets. Verify all current
targets with newline-normalized diffs, or limit CI to versioned files:

```text
python -m scripts.entry_sync check
python -m scripts.entry_sync check --scope repository
```
