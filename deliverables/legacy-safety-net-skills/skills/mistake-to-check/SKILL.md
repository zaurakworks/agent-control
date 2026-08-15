---
name: mistake-to-check
description: 刚修复一个错误时使用:把教训按测试、断言、结构规则、坑卡的顺序固化,防止同类错误复发。Use right after fixing a mistake: convert the lesson into an executable check or a pit card.
disable-model-invocation: true
---

# 犯错转检查:让每个错误只犯一次

**什么时候用我**:AI(或人)刚在仓里犯了一个错,已经修好。别让教训只活在聊天记录里——现在花 5 分钟(现场信息最全的时刻),把"下次别再犯"转成机器能执行的检查;实在写不成检查的,才降级成坑卡文档。判断依据:**知识压缩的正确介质是可执行物**——测试/断言/lint 自己会报警,文档只会安静地过时。

## 套路

### 第 1 步:先试可执行通道(按强到弱)

**能写成测试?** 加一条特征/例子测试,把正确行为钉死:

```java
@Test
void promoSceneUsesPromoRate_not_normalRate() {
    // 2026-08 曾错:PROMO 场景走了 NORMAL 费率。此测试钉住修复。
    BigDecimal actual = FreightCalculator.doCalc(Fixtures.template1001(),
        new FreightRequest("APP", "PROMO", "310000", new BigDecimal("1.5")));
    assertThat(actual).isEqualByComparingTo("9.00");
}
```

**能写成生产断言?** 在出错位置加前置/后置守卫,让同类错误在离病灶最近处爆炸:

```java
static BigDecimal doCalc(FreightSnapshot snap, FreightRequest req) {
    Objects.requireNonNull(snap.mainTemplate(), "快照缺主模板:templateId=" + snap.templateId());
    if (snap.rateRules().isEmpty()) {
        throw new IllegalStateException("模板无费率规则,拒绝按 0 计费:templateId=" + snap.templateId());
    }
    // ……
}
```

**能写成结构规则?** 用 ArchUnit 把架构约定变成测试(例:查算分离不被后来者腐蚀):

```xml
<dependency>
    <groupId>com.tngtech.archunit</groupId>
    <artifactId>archunit-junit5</artifactId>
    <version>1.3.0</version>
    <scope>test</scope>
</dependency>
```

```java
@AnalyzeClasses(packages = "com.example.freight")
class ArchitectureTest {
    @ArchTest
    static final ArchRule calcStaysPure = noClasses()
        .that().resideInAPackage("..calc..")
        .should().dependOnClassesThat().resideInAnyPackage("..mapper..", "..client..")
        .because("计算层必须保持纯函数,查询只发生在 load 层(查算分离)");
}
```

### 第 2 步:写不成可执行物的,落坑卡

历史原因、隐性约定、外部系统怪癖——这类写不成断言的知识落坑卡。四要素缺一不收:

```markdown
## 坑卡:免邮判断在主模板,不在子模板
- 触发条件:准备修改免邮/包邮相关逻辑时
- 症状词:免邮、包邮、freeThreshold、满额免运费
- 最短动作:先看 FreightCalculator#applyFreeRule 与 MainTemplateTest;子模板层没有免邮字段
- 失效条件:免邮逻辑迁往营销中心后本卡作废(关注 promotion-center 域)
```

四要素:触发条件/症状词/最短动作/失效条件,可加一行来源日期。没有失效条件的卡会永远赖在库里发霉。

### 第 3 步:坑卡三通道放置(按强到弱)

1. **贴代码・物理在场(最强)**:坑卡直接作为 `*.kb.md` 文件放在出错代码同目录(如 `calc/free-rule.kb.md`),改这段代码的人和 AI 打开目录就看得见,不依赖任何注入机制。真本放中央知识库,用软链物化到代码旁(kb 物化器,见安装说明);`*.kb.md` 不入库——`.git/info/exclude` 加单条 `**/*.kb.md`,再挂 pre-push 保险丝兜底。最热的那几个文件可以再加**文件内路牌**:方法签名上方一两行 `// [KB] 坑:免邮只看主模板 → 见同目录 free-rule.kb.md`——路牌只写十年不变的硬警告+指向卡片,细节全在卡片;`[KB]` 行由 clean 过滤器在提交时自动剥掉、由 `kb sync` 按签名锚点注回(双轨约定见安装说明)。
2. **显式问路(路由)**:把坑卡登记进你仓的显式路由入口目录(如「问安全网」的全目录表),按名问路时被指到。不做内容级自动注入——注入是强灌,在场是按需取用。
3. **召回库(兜底)**:坑卡进检索/向量库,靠症状词召回。召回不保证命中,前两条挂不上的才只靠这条。

约定:**一坑一卡**,一张卡只写一个坑。细粒度不是洁癖:多人/多 Agent 并发补卡时,一坑一卡把编辑冲突面缩到单文件,合集卡才是碰撞源。

### 第 4 步:同类错第二次出现=通道失效

上次的检查没建成,或放错了通道。重新走第 1 步;坑卡类的,检查症状词是否覆盖这次实际的搜索词/报错原文,补上。

## 坑位预警

- 别把坑卡写成事故报告:四要素之外的过程叙述全删,一卡 ≤15 行。
- 别跳过第 1 步直接写文档——写文档最顺手,恰恰是最弱介质。
- 生产断言要早抛、带上下文值(templateId 等),但别用断言承载业务逻辑。
- 修错当下就做,拖到"有空再整理"=永远不做。

## 完成自查

- [ ] 本次错误试过测试→断言→结构规则三个可执行通道
- [ ] 落坑卡的,四要素齐全且 ≤15 行
- [ ] 坑卡至少挂上了贴代码物理在场或显式问路通道之一,且一坑一卡
- [ ] 同类第二次犯错时回查了上次的检查为什么没拦住
