---
name: mutation-testing-gate
description: 刚收到一批测试(尤其 AI 写的)需要裁决可信度时使用:跑 PIT 突变测试,按击杀率(mutation score)门槛裁决打回或放行。Use after receiving a batch of tests: run PIT mutation testing and gate on mutation score.
disable-model-invocation: true
---

# 突变测试门:测试全绿不等于测试可信

**什么时候用我**:AI(或任何人)交付了一批测试,全绿。全绿只说明"没抓到问题",不说明"能抓问题"——断言弱到只查非空的测试也全绿。突变测试自动把生产代码改坏几百次(`>=`改`>`、常量±1、删掉一行),每个坏版本都应该让至少一个测试变红;没变红的"存活突变体"直接量化测试网的窟窿。先把两个一体两面的指标分清名字:**击杀率(mutation score)= 被杀死突变体 ÷ 全部突变体**,PIT 报告和 `<mutationThreshold>` 用的都是它,越高越好;**存活率(survivor rate)= 存活突变体 ÷ 全部突变体**,约等于 100% − 击杀率。存活率是"自己证明自己"问题的直接度量;工程门统一按击杀率方向设:测试交付后必跑,击杀率低于门槛(=存活率超标)就打回,不进人工 review。

## 套路

### 第 1 步:配 PIT,范围只圈热点

全仓跑既慢又没必要,只对着安全网覆盖的计算包:

```xml
<plugin>
    <groupId>org.pitest</groupId>
    <artifactId>pitest-maven</artifactId>
    <version>1.17.0</version>
    <dependencies>
        <dependency>
            <groupId>org.pitest</groupId>
            <artifactId>pitest-junit5-plugin</artifactId>
            <version>1.2.1</version>
        </dependency>
    </dependencies>
    <configuration>
        <targetClasses><param>com.example.freight.calc.*</param></targetClasses>
        <targetTests><param>com.example.freight.calc.*Test</param></targetTests>
        <!-- mutationThreshold = 击杀率(mutation score)下限:低于 60% 构建失败 -->
        <mutationThreshold>60</mutationThreshold>
        <timestampedReports>false</timestampedReports>
    </configuration>
</plugin>
```

### 第 2 步:测试交付后必跑

```
mvn org.pitest:pitest-maven:mutationCoverage -DwithHistory
```

报告在 `target/pit-reports/index.html`:逐行标出每个突变体被哪条测试杀死(KILLED)或存活(SURVIVED)。`-DwithHistory` 增量提速,日常复跑快得多。

### 第 3 步:按存活情况裁决(动作,不是感想)

| 观察 | 裁决 |
| --- | --- |
| 击杀率低于门槛(=存活率超标) | 打回:逐个看存活突变体,针对性补断言;不许泛泛加用例凑数 |
| 击杀率达标但存活集中在某个方法 | 该方法的测试是装饰品,重写该方法的断言 |
| 突变体改了语义但所有测试仍绿 | 缺的正是那条边界的断言,照着突变体补 |
| 等价突变体(改动不影响语义) | 标记忽略,不追求 100% 击杀率 |

### 第 4 步:门槛固化进构建门

`<mutationThreshold>` 是击杀率(mutation score)下限,低于它直接构建失败。起点定在当前实际击杀率(先跑一次看),**只升不降**;别一上来定 90 然后天天绕过。

## 坑位预警

- 前置:测试套件先全绿、离线、够快(先查算分离)。PIT 在红/慢/连库的套件上跑不动也没意义。
- JUnit 5 必须带 `pitest-junit5-plugin` 依赖,否则 PIT 静默找不到测试,报告显示 0 覆盖还不报错。
- 断言弱是存活主因:跑了代码只断言"不抛异常"/"非 null"的测试,突变门专治。
- 计时器/并发代码的突变可能超时误报;热点是纯函数时基本不遇到——又一个先做查算分离的理由。

## 完成自查

- [ ] PIT 只圈热点包,单次运行时间可接受
- [ ] 每批测试交付后都跑过,报告留档
- [ ] 存活突变体逐个处置(补断言/标等价),不是只看击杀率总分
- [ ] 击杀率下限已进构建配置,只升不降
- [ ] 打回时把存活突变体清单直接发给测试作者(AI),要求针对性补
