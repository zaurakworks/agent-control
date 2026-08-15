---
name: log-replay-baseline
description: 遗留代码没有测试但有生产日志时使用:抽取、去重分桶、录现跑基线、JaCoCo 补漏,把百万行日志蒸馏成几百个回归用例。Use when distilling production logs into a regression baseline for legacy code.
disable-model-invocation: true
---

# 日志重放:把生产日志蒸馏成回归基线

**什么时候用我**:要给一段老逻辑建回归网,手头没有测试,但生产日志里躺着百万行真实调用。用本套路把日志蒸馏成几百个代表性用例并录成基线。关键认知:**日志只提供输入分布,不提供期望值**。历史输出是"当时代码+当时配置"算出来的,配置早被运营改过了——拿历史输出当期望值,就是把自己锁死在一个已经不存在的世界里(配置变更死结)。基线=**现在的代码跑出来的输出**;历史输出只作交叉参考。

## 套路

### 第 1 步:抽取

写一次性抽取器,从日志解析完整调用输入,参数不全的行直接丢弃,输出结构化 JSONL。日志格式各家不同,以下是形状示意(Python,一次性工具):

```python
import json, re, sys

# 假设日志行形如: ... calcFreight req={"source":"APP","scene":"NORMAL","templateId":1001,...}
PATTERN = re.compile(r'calcFreight req=(\{.*\})')

for line in sys.stdin:
    m = PATTERN.search(line)
    if not m:
        continue
    req = json.loads(m.group(1))
    if not all(k in req for k in ("source", "scene", "templateId", "weight", "districtCode")):
        continue  # 参数不全的行不要
    print(json.dumps(req, ensure_ascii=False))
```

### 第 2 步:去重分桶

分桶键=你的真实分支维度组合。运费例:(来源 × 场景 × 模板类型 × 重量分桶)。每桶保留 1-3 条,百万行进,几百条出。分桶键就是"这段代码眼里有多少种不同世界"的显式化——键选错,几百条就代表不了百万行。

```python
def bucket_key(req, template_type_of):
    w = float(req["weight"])
    weight_bucket = "0-1" if w <= 1 else "1-3" if w <= 3 else "3-10" if w <= 10 else "10+"
    return (req["source"], req["scene"], template_type_of(req["templateId"]), weight_bucket)
```

### 第 3 步:录基线

用例文件里 expected 先留空。参数化测试第一遍跑:expected 为空→把实际输出写回用例文件;之后 expected 非空→纯断言。

```java
class FreightReplayTest {

    static final Path CASES = Path.of("src/test/resources/cases/replay-cases.jsonl");

    @ParameterizedTest(name = "[{index}] {0}")
    @MethodSource("cases")
    void replay(ReplayCase c) throws Exception {
        FreightSnapshot snap = Fixtures.load(c.templateId());
        BigDecimal actual = FreightCalculator.doCalc(snap, c.toRequest());

        if (c.expected() == null) {
            BaselineRecorder.record(CASES, c.id(), actual); // 第一遍:录基线,写回文件
        } else {
            assertThat(actual).isEqualByComparingTo(c.expected()); // 之后:回归断言
        }
    }

    static Stream<ReplayCase> cases() throws Exception {
        return Files.lines(CASES).map(ReplayCase::fromJson);
    }
}
```

`BaselineRecorder.record` 只在 expected 为空时写回;录完基线后这条分支不再触发,防止误覆盖已录基线。

### 第 4 步:JaCoCo 补漏

日志只反映线上打到过的分支。跑分支覆盖,看热点类哪些分支没被重放用例打到,手工构造输入补上。

```xml
<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>0.8.12</version>
    <executions>
        <execution><goals><goal>prepare-agent</goal></goals></execution>
        <execution><id>report</id><phase>test</phase><goals><goal>report</goal></goals></execution>
    </executions>
</plugin>
```

`mvn test` 后打开 `target/site/jacoco/index.html`,看热点类的**分支覆盖**(missed branches),不是行覆盖。怎么构造输入都打不到的分支→怀疑是死代码:单独记录上报,**不要顺手删**(删代码要等网建好之后按正常流程走)。

### 第 5 步:历史输出交叉参考

日志里若有当时的计算结果,与现跑基线对比一遍:不一致的用例打标注(可能是配置变更/已修 bug/未发现 bug),供人工抽查,**不阻塞**基线录制。

## 坑位预警

- 前置:先完成查算分离(见"特征测试"),否则重放要连库,离线跑不动。
- 抽取器是一次性工具,别过度工程;但分桶键必须和真实分支维度对齐。
- 桶数爆炸(维度太多)→先合并对计算无影响的维度,或加大连续值的桶粒度。
- 录基线那次运行的环境要和之后回归完全一致(同快照、同 Clock),否则基线本身不可重复。
- 日志里的重量/金额是字符串时注意精度:直接转 BigDecimal,别过 double。

## 完成自查

- [ ] 抽取只保留参数完整的行,字段齐全
- [ ] 分桶键=真实分支维度,桶数在几百量级
- [ ] expected 全部由第一遍运行写回,无手填猜测值
- [ ] JaCoCo 分支覆盖已看过,漏的分支已补用例或已标注死代码嫌疑
- [ ] 历史输出不一致的用例已标注,未拿历史输出当期望值
