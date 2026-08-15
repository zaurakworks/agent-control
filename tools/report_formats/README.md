# 运营文件层结构化视图

这个小模块定义运营台消费的两份版本化 JSON 视图：Worker 当前态与运营日报当前态。生产工具仍生成原有 Markdown 明细；运营台只从 JSON 视图读取字段，避免从展示文案反向重建结构化事实。

两份视图都使用 `schema_version: 1`，并用 `kind` 防止文件接错。`WorkerView` 保存观察时刻、在跑数、派发数和上游算出的当前活异常数；`MetricsView` 保存快照时刻与当日异常数。加载器拒绝未知版本、错误类型、负数和无时区时间戳。

验证：

```text
python -m unittest discover -s tools/report_formats/tests -v
```
