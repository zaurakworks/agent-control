## 1. 入口切换

- [x] 1.1 记录 `general` 与 `assembly-helper` 当前 inventory、lock 和 Codex/Qoder/OMP tree hash，作为能力闭包不变基线
- [x] 1.2 从 `tools/cap.py` 删除 `interactive` / `i` parser，令无子命令在 TTY 中依次选择 profile、CLI、客户端参数并直接 launch
- [x] 1.3 扩展 `cap show`：无 profile 时在 TTY 选择、显式 profile 时直接输出公共闭包、`--cli` 时直接展开该端装配
- [x] 1.4 实现临时 CLI 装配预览：组合 explain 与真实 render，稳定输出 inventory、目标相对文件树和 tree hash，并覆盖全部清理路径
- [x] 1.5 让使用与查看链路共用现有客户端注册表，不增加 Claude 占位项、空 adapter 或模拟输出
- [x] 1.6 为裸 `cap` 和无 profile 的 `cap show` 增加 stdin/stdout TTY 边界及可操作错误
- [x] 1.7 添加聚焦行为测试，覆盖高频启动、公共查看、CLI 展开、不展开、预览失败清理、非 TTY、`--help`、旧别名和显式低频子命令

## 2. 使用说明迁移

- [x] 2.1 更新 parser 帮助、README 与维护指南，明确 `cap` 是高频使用链路、`cap show` 是查看链路
- [x] 2.2 一次性迁移仓库内旧入口和旧默认调用，保留显式 `run` / `render` 自动化说明，并明确没有兼容层、Claude adapter 延期且未获支持声明

## 3. 验证

- [x] 3.1 运行 CAP 聚焦测试和 Python 编译检查
- [x] 3.2 对两个 profile 运行 CAP verify，并确认 inventory、lock 与 Codex/Qoder/OMP tree hash 和基线一致
- [x] 3.3 在实际 PTY 中执行裸 `cap`，确认没有动作菜单并到达原有客户端启动路径
- [x] 3.4 在实际 PTY 中执行 `cap show`，确认先显示公共闭包、再可选展开 CLI 文件树且不启动客户端
- [x] 3.5 比较 `cap show <profile> --cli <client>` 与显式 render 的 tree hash，并确认预览结束后没有临时目录残留
- [x] 3.6 在非 TTY 中验证不完整调用快速失败、参数完整的 `show` / `run` / `render` 仍可执行、旧入口失败且输出不宣称 Claude 支持
- [x] 3.7 运行 `openspec validate make-cap-default-interactive --type change --strict --json`
