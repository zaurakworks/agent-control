# 遗留代码安全网 skill 包:安装说明

8 件套,把"在几乎没有测试的老 Java/Spring 仓上安全干活"的方法论打包成 AI 助手可用的资产:1 个显式路由入口+6 个方法技能+1 个 kb 物化器工具。内容纯方法论,示例统一用通用运费计算域,不含任何公司私有信息,可直接带走使用。

| 资产 | 一句话 |
| --- | --- |
| `ask-safety-net`(问安全网) | 显式路由入口:掌握全目录,分诊并给出下一步 |
| `characterization-tests` | 特征测试:改老代码前先锁现状 |
| `log-replay-baseline` | 日志重放:把生产日志蒸馏成回归基线 |
| `example-first-oracle` | 例子先行:期望值来自实现者之外 |
| `property-invariants` | 性质不变量:不知精确答案也能抓错 |
| `mutation-testing-gate` | 突变测试门:用击杀率门槛裁决测试可信度 |
| `mistake-to-check` | 犯错转检查:每个错误只犯一次 |
| `tools/kb/` | kb 物化器(Mac 软链版,双轨):`*.kb.md` 软链物化+`[KB]` 注释收割/注回+中央库快照 |

目录结构(全部资产):

```
README.md            本安装说明
skills/              7 个技能目录(路由入口+6 方法),每个一份 SKILL.md=唯一正文真本
tools/kb/            kb.py 物化器 + kb_selftest.py 可重复自验
hooks/               pre-commit / pre-push / post-checkout 三个 hook 样例
```

## 设计形态:显式问路,不指望自动路由

环境自动路由(指望模型干活时自发匹配到对的规则/技能)实测不可靠。本包用 ask 式显式路由:**一个好记的入口名背下全部记忆负担**——你只要记住「问安全网」,入口掌握全目录、替你分诊、给出下一步。正文一律以文件形式物理在场、按需读取;**不做任何内容级条件注入**(注入是强灌,在场是按需取用)。

要养成的唯一习惯:动手前问一句。「问安全网:我要改运费计算里一段没测试的老代码」——入口会告诉你先建哪张网、第一步做什么、去读哪份正文。

正文单一真本在 `skills/<技能名>/SKILL.md`;两种安装格式只是"入口怎么挂"不同,读的是同一批文件。

## 格式 A:qodercli(Qoder CLI / Qoder IDE)

1. 把整个包目录拷到你顺手的位置(**建议放在目标仓外**,如 `~/work-skills/legacy-safety-net/`;放仓内则把包目录加进 `.git/info/exclude`——包内文档含 `[KB]` 示例字样,直接 commit 进挂了安检钩子的仓会被拦下)。
2. 把下面三行**粘贴到 qodercli 规则**(新建 `<项目根>/.qoder/rules/safety-net-router.md`,或贴进你现有的常驻规则文件),路径按实际安装位置改:

   ```
   遗留代码/测试/回归安全网相关的活,先「问安全网」:读 ~/work-skills/legacy-safety-net/skills/ask-safety-net/SKILL.md,由它分诊并给出下一步,再动手。
   本仓 **/*.kb.md 与上述 skills/ 下各 SKILL.md 是物理在场的知识文件,按需读取;不做内容级自动注入。
   代码内 [KB] 注释是路牌:一两行硬警告+指向同目录 *.kb.md 卡片;细节读卡片,不展开在代码里。
   ```

   这三行路标就是全部常驻内容:不给任何正文文件加 `trigger:` 条件注入,正文靠入口指路+按需读取。
3. 验证:`/memory` 里应只看到这一条常驻路由;对助手说「问安全网:……」应得到分诊+明确下一步。
4. 版本门:`.qoder/rules` 需 CLI ≥1.0.31,以本机 `/memory` 实测为准;项目级规则依赖 Trusted Workspace(未信任目录会被忽略)。

## 格式 B:标准 SKILL.md(Claude Code 及兼容 agent)

1. 把 `skills/` 下 7 个目录拷到 `<项目根>/.claude/skills/`(项目级)或 `~/.claude/skills/`(用户级,所有项目可用)。
2. 分层设计:只有入口 `ask-safety-net` 可被模型自动触发,也可 `/ask-safety-net` 显式调用(推荐养成显式习惯);6 个子技能 `disable-model-invocation: true`——零常驻上下文、不参与自动触发,由入口按名指路(`/技能名` 或直接读对应 `SKILL.md`)。
3. 机制坑:`.claude/skills/` 顶层目录若是会话中途新建的,当前会话看不见新技能(调用报 Unknown skill);重启会话,或 v2.1.152+ 用 `/reload-skills`。
4. 其他支持 SKILL.md 约定的 agent 同样直接复制目录,放进各自文档规定的 skills 目录。

## 贴代码知识资产:双轨约定

坑卡等贴代码知识走「物理在场」,不走注入,分两轨:

- **旁车轨(主力)——`*.kb.md` 卡片文件**:放在它描述的代码同目录,打开目录就看见。适用于一切贴代码知识,默认永远先用这轨。
- **嵌入轨(只给最热文件)——代码内 `[KB]` 注释路牌**:方法签名上方一两行、每行都带 `[KB]` 标记的注释。只有"打开这个文件的人必须当场看见"的少数硬警告才值得上这轨。
- 两轨**共用同一个中央库**(真本都在中央库,经 `kb snapshot` 版本化)和**同一套保险丝**(`.git/info/exclude`+pre-commit/pre-push,见下)。
- **嵌入轨的持有成本,如实说**:注释嵌在代码里,会随编辑上下漂移——所以锚点用**方法签名邻近**而不用行号;但方法改名/重构签名后,`kb sync` 注回会报"找不到锚点",需要人工搬一次。这是嵌入轨比旁车轨贵的地方,也是"只给最热文件"的原因。

## 双层同步纪律:注释=路牌,卡片=内容

嵌入注释做不到软链级同步(物理限制:它是文件内容的一部分,不是一个可链接的文件)。所以分层:

- **代码内 `[KB]` 注释=路牌**:一两行、十年不变的硬警告+指向卡片。例:`// [KB] 坑:免邮只看主模板 → 见同目录 free-rule.kb.md`。
- **`*.kb.md` 卡片=内容**:常变的细节、失效条件、案例——全放卡片;卡片在软链层,天然完美同步。
- 原则一句话:**把需要频繁同步的内容,放在能完美同步的层**。路牌基本不用同步(它不变),真正常变的内容走软链。
- 路牌层靠**两个自动同步点**达成最终一致:pre-commit 钩子自动 `kb harvest`(提交时收割进中央库),post-checkout 钩子/`kb sync` 检出时刷新注回。

## worktree 流程:贴膜→干活→撕膜→安检

主线(master/main)**永远干净**——仓库历史里永远没有 `[KB]` 注释和 `*.kb.md`:

1. `git worktree add`(或 clone/checkout)得到干净工作区;
2. `kb sync` **贴膜**:补建 `*.kb.md` 软链+把 `[KB]` 路牌按签名锚点注回热点文件;
3. 正常干活,注释在场可见;
4. `git commit` **自动撕膜**:clean 过滤器把 `[KB]` 行剥掉才入暂存(git 对注释失明,`git status`/`diff` 都看不见它);
5. `git push` **安检**:pre-push 钩子查将推历史,任何 `[KB]`/被跟踪的 `*.kb.md` 都拒绝。

**明确禁止**任何「带注释的本地分支」方案(在本地分支上 commit 含 `[KB]` 的历史,推前再洗)——历史污染即泄漏:分支一旦被合并、cherry-pick、reflog 恢复或误推,注释就进了共享历史。注释只允许活在工作区,永不进任何 git 历史。

## kb 物化器:tools/kb/kb.py(Mac 软链版,双轨完整版)

前提:macOS(或任何原生支持 symlink 的系统)+ Python 3.9+,零第三方依赖。中央库 = 一个本地 git 仓(建议 `~/kb-central`,`git init` 一次):

```
~/kb-central/
├── manifest.json     # 旁车轨清单:哪张卡物化到哪个仓的哪个路径
├── cards/…           # *.kb.md 真本,目录组织随意
└── notes.json        # 嵌入轨清单:哪条 [KB] 路牌锚在哪个文件的哪个方法签名(kb harvest 自动维护)
```

manifest.json 形如:

```json
{
  "version": 1,
  "links": [
    {
      "repo": "freight-service",
      "path": "src/main/java/com/example/freight/calc/free-rule.kb.md",
      "card": "cards/freight-service/free-rule.kb.md"
    }
  ]
}
```

子命令(**没有 collect**:软链之下,在代码旁编辑就是直接写中央库真本,无需回收):

- `kb sync`——在 worktree 里跑,幂等可重跑,一次做两轨:
  - 旁车轨:读 manifest,补建 `*.kb.md` symlink。已有正确链接跳过;实体文件占位或链接指向别处只报告不覆盖;代码目录不存在只警告。
  - 嵌入轨:读 notes,把 `[KB]` 路牌**显式注回**热点文件——锚点=方法签名邻近(不用行号),注在签名上一行、保持缩进;已在场跳过;**找不到锚点/锚点不唯一即报错不乱插**(方法改名后人工搬一次再收割)。
- `kb snapshot`——把中央库当前状态自动 `git commit` 一次(卡片和 notes 一起)。并发写坏可从历史恢复:`git -C ~/kb-central log --oneline -- cards/…` 再 `checkout <提交> -- <路径>`。
- `kb filter-install <热点文件>...`——装配并校验 clean/smudge 过滤器:写 `.git/config`(`filter.kb.clean/smudge/required`)+`.git/info/attributes`(`/<路径> filter=kb`),两处都是本地配置、linked worktree 天然共享,不污染共享文件。**只对显式指定的热点文件生效,不全仓开**。clean 只做一件机械事:剥掉所有含 `[KB]` 的行;smudge 是**显式 no-op**——检出注入静默难调试,注入一律走 `kb sync` 显式执行。装完自动校验(`git check-attr`+剥离逻辑)。
- `kb harvest [文件...]`——收割热点文件里的 `[KB]` 注释进中央库 `notes.json`(缺省收割 attributes 里登记的全部热点文件;按文件整体替换,删除也是变更,经 snapshot 版本化可恢复)。收割时记录锚点=紧随注释块之后的第一个非空代码行(通常是方法签名)。

```
python3 tools/kb/kb.py sync            [--central ~/kb-central] [--repo freight-service]
python3 tools/kb/kb.py snapshot        [--central ~/kb-central] [-m "说明"]
python3 tools/kb/kb.py filter-install  src/main/java/com/example/freight/calc/FreightCalculator.java
python3 tools/kb/kb.py harvest         [文件...] [--central ~/kb-central] [--repo freight-service]
```

`--central` 缺省读环境变量 `KB_CENTRAL`,再缺省 `~/kb-central`;`--repo` 缺省取 origin URL 末段或仓目录名。`filter-clean`/`filter-smudge` 是给 git 调的内部子命令,不用手工跑。

**自验**:`python3 tools/kb/kb_selftest.py` 在临时目录搭一套中央库+假 worktree,21 项覆盖两轨:幂等建链、冲突不覆盖、编辑落真本、快照可恢复、collect 缺席、clean 剥离/smudge 透传、filter-install 装配校验幂等、git 对注释失明、harvest 收割与整体替换、注入幂等与锚点报错;macOS 上应全部 PASS(无 symlink 权限的 Windows 上软链 4 项如实标 SKIP)。

## 保险丝:exclude+hooks(过滤器失效时的兜底)

- **第一道**:`.git/info/exclude` 加**单条** `**/*.kb.md`(本地忽略,不污染共享 `.gitignore`,不需要说服全团队)。
- **hooks/ 三个样例**(拷到 `<目标仓>/.git/hooks/<去掉 .sample>` 并 `chmod +x`,文件里的 kb.py 路径按实际位置改):
  - `pre-commit.sample`:自动 `kb harvest`(提交时收割,双层同步点之一)+**兜底 grep**——暂存内容仍含 `[KB]` 即拒绝提交(clean 过滤器未装/失效的最后防线);
  - `pre-push.sample`:任何 `*.kb.md` 已被跟踪即拒绝+将推的每个提交树里含 `[KB]` 即拒绝(历史污染即泄漏);
  - `post-checkout.sample`:切分支/新建 worktree 后自动 `kb sync`(贴膜,双层同步点之二)。
- **一坑一卡**:一张卡只写一个坑(≤15 行)。细粒度把多人/多 Agent 并发补卡的编辑冲突面缩到单文件,合集卡才是碰撞源。
- **kb 不做分支版本化**:中央库不管分支,所有 worktree/分支共享同一真本。卡与路牌只描述"当前有效的知识+失效条件";随分支不同而不同的行为,钉进该分支的测试/断言,不进 kb。

## 定制指引

- 示例统一用通用运费计算域(`FreightCalculator`/主模板/子模板/费率规则)。落到你的仓时,把示例类名与字段换成你的域,套路与红线不变。
- 入口名「问安全网」/`ask-safety-net` 可改成你团队顺口的名字,但要同步改粘贴片段、入口正文和使用习惯;名字的全部价值在"每个人都记得住"。
- 示例版本号(jqwik 1.9.2 / PIT 1.17.0 / JaCoCo 0.8.12 / ArchUnit 1.3.0)是当前常见稳定版,以你仓库的依赖管理为准。
