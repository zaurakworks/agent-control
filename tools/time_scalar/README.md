# 时间标量守卫

这个窄工具从序列化 JSON 直接读取带 `Z` 或 offset 的 RFC 3339 字符串，并按原始标量逐字比较陈旧快照。它拒绝已经解析成宿主时间对象的输入、无时区值和缺少来源的值，避免把“同一时刻的不同格式”误判为原始标量一致。

## 使用

直接读取 GitHub 响应中的原始标量：

```text
gh api repos/Eridanus117/agent-control/issues/28 | python tools/time_scalar/time_scalar.py extract --key updated_at --source "GitHub Issue 28 updated_at"
```

写入前将当前响应与先前保存的原始标量逐字比较：

```text
gh api repos/Eridanus117/agent-control/issues/28 | python tools/time_scalar/time_scalar.py compare --key updated_at --source "GitHub Issue 28 updated_at" --expected "2026-08-12T17:00:07Z"
```

嵌套对象可重复传入 `--key`，例如 `--key result --key dispatch --key last_heartbeat_at`。`compare` 返回 `0` 表示逐字相同，`1` 表示两个有效标量不同，`2` 表示输入、路径、类型或时区语义不安全；输出的成功值保持输入标量，不做 UTC、本地时区或文化格式转换。

验证：

```text
python -m unittest discover -s tools/time_scalar/tests -v
```

## 边界

本工具只处理 JSON 对象中的带时区 RFC 3339 字符串，不提供日期运算、自然语言解析或通用时间转换。无 offset／`Z` 的值应继续按“原始值 + 来源”记录，并在工具合同明确时区前留在本工具之外。
