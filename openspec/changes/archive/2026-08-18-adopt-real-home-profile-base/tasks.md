## 1. 公共 profile 合同

- [x] 1.1 将 manifest/profile schema 升级为 version 2 单继承层
- [x] 1.2 实现 `add`、`mask`、`replace` 合成与冲突门禁
- [x] 1.3 实现无 secret real-home manifest、workspace pin 和 derived binding
- [x] 1.4 实现 active/passive drift 与交互/批处理门禁
- [x] 1.5 让 materialize、probe、diff、launch、run 统一校验 base binding

## 2. Assembly 采用

- [x] 2.1 将 `general` 与 `assembly-helper` 改为继承 `real-home`
- [x] 2.2 更新两个 prompt 的分层能力合同
- [x] 2.3 让 CAP wrapper 转发 manifest、pin、binding 路径
- [x] 2.4 保留真实 HOME 与 profile 专属 OMP 配置/Session 根
- [x] 2.5 删除 workspace context bridge 和兼容分支
- [x] 2.6 更新 lock、维护说明和运行收据

## 3. 验证

- [x] 3.1 公共 profile 单元测试覆盖继承、冲突、漂移和真实 HOME
- [x] 3.2 Assembly 单元测试覆盖 binding 参数与 OMP 环境
- [x] 3.3 CAP verify、render 与 Skill 元数据检查通过
- [x] 3.4 OpenSpec strict validation 通过
- [x] 3.5 真实 OMP 输出真实 HOME、父级工作区和仓库 context 路径
