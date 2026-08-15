---
name: property-invariants
description: 给计算类核心逻辑写测试但无人能给出精确期望值时使用:人给一句话领域性质,jqwik 机械化成随机测试。Use when no one can state exact expected outputs: encode domain invariants as jqwik property tests.
disable-model-invocation: true
---

# 性质不变量:不知道精确答案,也能抓住错

**什么时候用我**:想给算钱类核心逻辑加测试,但没人说得清任意输入下的精确期望值。不需要:领域里有些话永远成立——"更重不能更便宜""总运费=各段之和"。把这种一句话性质交给 jqwik,变成几千个随机用例。它无法被实现"自证":**性质由人给出,随机输入由框架生成,两头都不在实现者手里**。

## 套路

### 第 1 步:人给性质(一句话一条)

对照四个模式在你的域里找,先攒句子再机械化:

| 模式 | 运费域例句 |
| --- | --- |
| 单调性 | 同模板同地址,更重的包裹运费不变少 |
| 可分解性 | 多段计费时,总运费=各段费用之和 |
| 连续性 | 阶梯边界两侧不跳崖:重量 +0.01kg,费用增量不超过一档差价 |
| 局部性 | 只改模板的偏远地区加价字段,非偏远地址的运费一分不变 |

### 第 2 步:机械化成 jqwik property

```xml
<dependency>
    <groupId>net.jqwik</groupId>
    <artifactId>jqwik</artifactId>
    <version>1.9.2</version>
    <scope>test</scope>
</dependency>
```

```java
class FreightPropertyTest {

    static final FreightSnapshot SNAP = Fixtures.template1001();

    @Property
    void heavierIsNeverCheaper(
            @ForAll @BigRange(min = "0.01", max = "100") @Scale(2) BigDecimal weight,
            @ForAll @BigRange(min = "0.01", max = "50") @Scale(2) BigDecimal delta) {
        BigDecimal light = FreightCalculator.doCalc(SNAP, req(weight));
        BigDecimal heavy = FreightCalculator.doCalc(SNAP, req(weight.add(delta)));
        assertThat(heavy).isGreaterThanOrEqualTo(light);
    }

    @Property
    void tierBoundaryHasNoCliff(
            @ForAll @BigRange(min = "0.01", max = "99") @Scale(2) BigDecimal weight) {
        BigDecimal fee = FreightCalculator.doCalc(SNAP, req(weight));
        BigDecimal feeJustAbove = FreightCalculator.doCalc(
            SNAP, req(weight.add(new BigDecimal("0.01"))));
        assertThat(feeJustAbove.subtract(fee))
            .isLessThanOrEqualTo(SNAP.maxSingleTierDiff()); // 一档差价上限,由模板数据算出
    }

    private static FreightRequest req(BigDecimal weight) {
        return new FreightRequest("APP", "NORMAL", "310000", weight);
    }
}
```

### 第 3 步:反例走人裁决

失败时 jqwik 自动收缩(shrink)到最小反例并报告种子。拿最小反例走"例子先行"的裁决流程:是实现 bug,还是性质本身写错(域里有合法例外)?复现用 `@Property(seed = "...")` 固定种子。

### 第 4 步:例外写进前提,不删性质

真实域里单调性可能有合法例外(如满额免邮)。用 `Assume.that(...)` 把例外排除在前提外,或把性质改精确("未触发免邮时,更重不更便宜"),不要因为有例外就删掉整条性质。

```java
@Property
void heavierIsNeverCheaper_belowFreeThreshold(
        @ForAll @BigRange(min = "0.01", max = "100") @Scale(2) BigDecimal weight,
        @ForAll @BigRange(min = "0.01", max = "50") @Scale(2) BigDecimal delta) {
    // 前提:较重的那个也在免邮阈值以下,免邮分支不参与本性质
    Assume.that(weight.add(delta).compareTo(SNAP.freeWeightThreshold()) < 0);
    BigDecimal light = FreightCalculator.doCalc(SNAP, req(weight));
    BigDecimal heavy = FreightCalculator.doCalc(SNAP, req(weight.add(delta)));
    assertThat(heavy).isGreaterThanOrEqualTo(light);
}
```

`Assume.that` 只收窄前提,断言本身一行不少:仍然生成两个重量、仍然比较两次计算结果。只写 `Assume` 不写断言的"性质"是空转,一个反例也抓不到。

## 坑位预警

- **性质不能把实现抄一遍**:在测试里重算一遍运费再比相等=同脑自证换了个房间。性质必须弱于实现,只断言关系,不断言精确值。
- BigDecimal 随机生成必须限定范围和 scale(`@BigRange` + `@Scale`),否则极端值噪音淹没有效反例。
- 性质测试和特征测试**并存不互代**:特征测试钉具体点位,性质测试扫随机空间。
- doCalc 必须先是纯函数(查算分离完成),连库的代码跑不动几千个随机用例。

## 完成自查

- [ ] 每条性质都能还原成人说的一句领域话
- [ ] 四模式(单调/可分解/连续/局部)都对照找过
- [ ] 没有一条性质是在测试里重新实现计算
- [ ] 反例经人工裁决,例外进了 Assume 前提而不是删性质
- [ ] 失败种子已记录,可复现
