---
name: characterization-tests
description: 准备修改缺少测试保护的遗留 Java 代码时使用:查算分离、导出配置快照、把现状锁成特征测试再动手。Use when modifying legacy Java code without tests: lock current behavior with characterization tests first.
disable-model-invocation: true
---

# 特征测试:先锁现状,再动手

**什么时候用我**:你即将修改一段没有测试保护的老 Java 代码——典型是一个几百行、来源×场景×模板十几个分支的计算方法。先按本套路给它拍一张"行为快照",让之后任何改动引起的行为变化立刻变红。特征测试**锁现状,不判对错**:按"应该是什么"写测试是遗留代码测试的第一死因——那会把从没人验证过的猜想固化成断言,把"锁行为"变成"边锁边改"。

## 套路(按序执行)

### 第 1 步:圈热点,不求覆盖率

只钉你这次要动的方法及其直接调用链。全仓补测试是另一个项目,不是本次的前置条件。

### 第 2 步:查算分离(剪切粘贴级提取)

把"查"(数据库/RPC/配置中心/时间)与"算"(纯逻辑)拆开。这不是重构设计,是物理搬运:原语句原样剪切粘贴,不改一行逻辑、不改变量名、不顺手优化。

```java
// 改造前:查询与计算缠绕,测试必须连库
public BigDecimal calcFreight(Long templateId, FreightRequest req) {
    FreightTemplate main = templateMapper.selectById(templateId);
    List<SubTemplate> subs = subTemplateMapper.listByMainId(templateId);
    List<RateRule> rules = rateRuleMapper.listBySubIds(ids(subs));
    // ……下面 300 行 if/else 计算……
}
```

```java
// 改造后:同一个类里拆成两个方法,调用方无感知
public BigDecimal calcFreight(Long templateId, FreightRequest req) {
    FreightSnapshot snap = loadSnapshot(templateId); // 查:所有 I/O 收拢在这里
    return doCalc(snap, req);                        // 算:纯函数,可离线测试
}

FreightSnapshot loadSnapshot(Long templateId) {
    // 原查询语句原样剪切进来,组装成快照对象
    FreightTemplate main = templateMapper.selectById(templateId);
    List<SubTemplate> subs = subTemplateMapper.listByMainId(templateId);
    List<RateRule> rules = rateRuleMapper.listBySubIds(ids(subs));
    return new FreightSnapshot(main, subs, rules);
}

static BigDecimal doCalc(FreightSnapshot snap, FreightRequest req) {
    // 原 300 行计算原样剪切进来,只把数据读取改为从 snap 取
}
```

`FreightSnapshot` 是纯数据类(record 或 POJO),把主模板/子模板/费率规则整棵装进去。

### 第 3 步:配置数据全量导出为快照 fixture

模板这类配置数据从测试库/预发库读一次,整棵序列化进 `src/test/resources/fixtures/`。此后测试不连库——基线钉在"快照+代码"上,运营后来改了配置也不影响测试可重复。

```java
@Test
@Disabled("一次性导出工具:连测试库跑一遍,导完恢复 Disabled")
void exportSnapshot() throws Exception {
    FreightSnapshot snap = calculator.loadSnapshot(1001L);
    new ObjectMapper().writerWithDefaultPrettyPrinter()
        .writeValue(new File("src/test/resources/fixtures/template-1001.json"), snap);
}
```

### 第 4 步:录现状为期望值

第一次跑,把实际输出记下来当期望值;它从此就是基线。

```java
class FreightCalcCharacterizationTest {

    static FreightSnapshot snap;

    @BeforeAll
    static void load() throws Exception {
        snap = new ObjectMapper().readValue(
            FreightCalcCharacterizationTest.class.getResource("/fixtures/template-1001.json"),
            FreightSnapshot.class);
    }

    @Test
    void app_normal_district310000_2kg() {
        BigDecimal actual = FreightCalculator.doCalc(
            snap, new FreightRequest("APP", "NORMAL", "310000", new BigDecimal("2.0")));
        // 期望值 = 第一次运行的实际输出,不是"应该多少"
        assertThat(actual).isEqualByComparingTo("12.50");
    }
}
```

用例按分支维度组合挑选(来源×场景×模板类型各覆盖到),十几个分支通常 20-40 个用例足以钉住热点;有生产日志时用"日志重放"套路系统化选用例。

### 第 5 步:绿了才改,红了先裁决

特征测试全绿后开始真正的修改。改完变红=行为变化被捕获,人工裁决:

- 变化在本次意图内→更新期望值,提交说明写明哪几个用例为何变;
- 变化在意图外→这就是网抓住的事故,修代码。

## 坑位预警

- **BigDecimal**:`equals` 连 scale 一起比,`new BigDecimal("12.5").equals(new BigDecimal("12.50"))` 是 `false`。断言一律 AssertJ 的 `isEqualByComparingTo`(底层 `compareTo`);JUnit 原生则用 `assertEquals(0, expected.compareTo(actual))`。快照/用例文件里统一 `setScale(2, RoundingMode.HALF_UP)` 再存。
- **时间**:代码里的 `LocalDateTime.now()` 让结果随运行时刻漂移(节假日/活动期分支)。把 `java.time.Clock` 注入被测类:字段 `private final Clock clock`,生产装配给 `Clock.systemDefaultZone()`,所有 `now()` 改成 `LocalDateTime.now(clock)`;测试给 `Clock.fixed(Instant.parse("2026-01-15T02:00:00Z"), ZoneId.of("Asia/Shanghai"))`。这也是剪切粘贴级改造。
- **随机数/UUID/自增主键**:会混进快照或输出的,进快照前剥离或固定,否则快照每次导出都变。
- **别顺手改逻辑**:查算分离过程中发现可疑写法(比如 double 算钱)→记到待办,网建好之后再动。

## 完成自查

- [ ] 热点方法已查算分离,doCalc 不再触碰 Mapper/RPC/`now()`
- [ ] 配置快照已入 `src/test/resources/fixtures/`,测试不连库
- [ ] 期望值全部来自实际运行输出,没有一个是"我觉得应该"
- [ ] 分支维度组合已覆盖(来源×场景×模板类型)
- [ ] 全绿提交过一次,之后才开始功能修改
