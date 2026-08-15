---
name: example-first-oracle
description: 实现新需求前使用:先向需求方索取 5-10 个人工计算的期望值例子,保持预言机与实现分离,AI 不得自出期望值。Use when implementing new requirements: obtain human-computed expected values before writing code or tests.
disable-model-invocation: true
---

# 例子先行:期望值必须来自实现者之外

**什么时候用我**:要在老仓里实现一个新需求(新计费玩法、新分支逻辑),而且大概率是 AI 动手写代码。先停一下:**AI 给自己的实现写测试是同脑自证**——需求理解错在上游时,代码和测试一起错,测试永远绿。本套路把期望值(预言机)的来源从实现者身上剥离:人先给例子,实现方做到全过。

## 套路

### 第 1 步:要例子,不要形容

动手前由需求方给出 5-10 个具体例子:完整输入+**人脑算出的**期望输出。"首重 8 元、续重每公斤 2 元"是规则描述;"0.5kg→8.00,1.5kg→10.00,3.0kg→12.00"才是例子。例子必须带全输入维度(来源/场景/模板/重量/地址),缺维度的例子会被实现方自由脑补。

### 第 2 步:例子先落成验收测试

一字不改写进参数化测试,例子编号保留,来源写明:

```java
class NewFreightRuleAcceptanceTest {

    // 期望值由需求方人工计算给出(2026-08-13 评审记录),实现方不得修改。
    // 觉得某个期望值可疑→停下来提出质疑,由需求方裁决。
    @ParameterizedTest(name = "例{0}")
    @CsvSource({
        // 例号, 来源, 场景,   区码,   重量, 期望运费
        "1,     APP,  NORMAL, 310000, 0.5,  8.00",
        "2,     APP,  NORMAL, 310000, 1.5,  10.00",
        "3,     APP,  PROMO,  310000, 1.5,  9.00",
        "4,     PC,   NORMAL, 440300, 3.0,  12.00",
        "5,     APP,  NORMAL, 440300, 10.0, 26.00",
    })
    void acceptance(int caseNo, String source, String scene, String district,
                    BigDecimal weight, BigDecimal expected) {
        BigDecimal actual = FreightCalculator.doCalc(
            Fixtures.newRuleSnapshot(), new FreightRequest(source, scene, district, weight));
        assertThat(actual).isEqualByComparingTo(expected);
    }
}
```

### 第 3 步:实现到全过,矛盾就上抛

实现过程中发现例子与需求文字矛盾→**这是收获,不是障碍**:不一致暴露的是双方理解差异,拿去问人。**例子算错了也有价值**——它逼出一次需求澄清。纪律:实现方(尤其 AI)不得为了变绿而修改期望值。

### 第 4 步:扩测试面时保持预言机分离

例子只有 5-10 个,不够覆盖分支。实现方可以增加输入,但新期望值仍须外部来源:人工补算,或第 5 步的独立对算。不允许"我的实现算出多少就填多少"。

### 第 5 步:独立对算(高价值逻辑用)

开一个**全新会话**(干净上下文,只给需求文本,不给实现代码),让 AI 写一个笨慢直白版:逐段累加、不查表、不优化、不复用主实现的任何代码。两版对拍随机输入,分歧点人工裁决。

```java
// 笨慢版:只为对拍存在,可读性压倒一切
static BigDecimal naiveFreight(FreightSnapshot snap, FreightRequest req) {
    BigDecimal fee = snap.firstWeightPrice();
    BigDecimal w = req.weight().subtract(snap.firstWeight());
    while (w.compareTo(BigDecimal.ZERO) > 0) {          // 逐续重单位累加,不用乘法捷径
        fee = fee.add(snap.additionalPrice());
        w = w.subtract(snap.additionalWeight());
    }
    return fee.setScale(2, RoundingMode.HALF_UP);
}
```

对拍可以用 jqwik(见"性质不变量")把"两版结果相等"本身作为性质跑随机输入。

## 坑位预警

- 别接受"已按需求自测通过"式汇报。验收=人给的例子全绿+突变门通过(见"突变测试门")。
- 独立对算的会话必须干净:同一会话里出现过主实现代码,笨慢版就被污染,对拍失去意义。
- 例子表就是需求文档的可执行部分,评审需求时直接评审例子表。

## 完成自查

- [ ] 动手前拿到 ≥5 个人工计算的完整例子
- [ ] 例子原样进参数化测试,注释写明来源与"不得修改"
- [ ] 出现矛盾走了需求澄清,没有静默改期望值
- [ ] 新增用例的期望值全部来自外部(人工/独立对算)
- [ ] 高价值逻辑做了独立对算,或写明为何不需要
