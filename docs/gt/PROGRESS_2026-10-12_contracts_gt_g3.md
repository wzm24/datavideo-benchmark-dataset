# DataVideo Benchmark 进展：输入契约、GT 分层与 G3 判定问题

日期：2026-10-12
例子用的是 bar_27（家庭收入档位对应 SAT 平均分，7 档，890 到 1150）。

---

## 一、输入定成四种，都带 intent

没有 intent 的话模型不知道要往哪个方向讲，评测就没有意义。所以原来"只给数据表"那一档作废。

| 代号 | 输入 | 模型负责 |
|---|---|---|
| v1 | 数据表 + intent | 旁白、图表设计、动画 |
| v2 | 数据表 + intent + 旁白 | 图表设计、动画 |
| v3 | 数据表 + intent + 参考图 | 旁白、动画 |
| v4 | 数据表 + intent + 旁白 + 参考图 | 只做动画与时间同步 |

四档分开建 GT、分开报榜，不混在一起比较。

## 二、v1 的 GT 是五层

| 层 | 全称 | 管什么 |
|---|---|---|
| G0 | 数据事实基础 | 表、字段、单位、来源、容差，确认一句话有没有依据 |
| G1 | 必需语义单元 | 这张图必须讲哪几件事 |
| G2 | 视觉证据规范 | 每件事在图里要看到什么才算真的画出来了 |
| G3 | 时间关系规范 | 这些证据该和旁白哪句话对齐 |
| G4 | 人工验证集 | 真实输出的标注与裁决，用来校准自动判官 |

现状：只有 G1 真正落地，340 条 clip、1646 个语义单元（平均每条 4.8 个）。G2 和 G3 目前是 G1 单元里的两个字段（`visual_evidence_rule` 和 `temporal_anchor`），还没有独立文件；G4 没建。

## 三、生成流程（参考 DataReel）

两步走：

1. 用 intent 和数据表让模型写旁白，再用本地 TTS 逐句合成，量出每句真实的起止时间。
2. 把旁白和时间轴，连同 intent、数据表一起喂回去，让模型写单文件 HTML。

时间轴是真的量出来的，不是模型估的。

**和 DataReel 的差别**：他们也是一次生成 HTML，字幕由模型在 HTML 里自己写，没有音频，时长是作为输入给定的。我们是旁白先出、TTS 量出真实时间轴、再写 HTML。多出来的这一步让时间轴是真的，代价是时长没法预先控制——我们的视频多长由旁白多长决定，所以出现了 47 秒和 70 秒两种失控。

---

## 四、改动过程中的几个发现

### 4.1 不让念数据之后，同步就崩了

最初的提示词是"每句话必须给出判断、不许念数字、每句最多一个数"。加完之后复述率从 0.50 降到 0.00，看起来成功了，但同步坏了：说 1150 的那句是 0 到 7.6 秒，而那根柱到 11.2 秒才长完，晚了 3.65 秒。

原因是旁白和动画各自从 intent 生成，中间没有绑定。模型没有义务"说到哪就画到哪"，它只会按自己的节奏把柱子依次长出来。

### 4.2 加了逐句绑定之后，同步好了

在写 HTML 的提示词里加了要求：先声明一份逐句的动画计划（每句对应哪次画面变化、变化发生在第几秒），再按这份计划写代码。加上之后每句话都有对应的画面动作，不再出现"整句播放画面不动"。

### 4.3 但复述率和同步是反向的

bar_27 前后跑了六版：

| 跑法 | 句数 | 时长 | 复述率 | 同步表现 |
|---|---|---|---|---|
| 旧版（只要求数字有依据） | 4 | 35.9s | 0.50 | — |
| 加"每句必须是判断" | 3 | 22.9s | 0.00 | 1150 那句晚 3.65 秒 |
| 再加逐句绑定计划 | 4 | 29.6s | 0.25 | 每句各有一次画面动作 |
| 放宽数量限制，保留绑定 | 3 | 14.3s | 0.00 | 每句各有一次画面动作 |
| 把定量限制全删 | 7 | 47.0s | 0.43 | 退回念数据 |
| 加回 DataReel 的定性句 | 9 | 69.9s | 0.33 | 一句一根柱，最准 |

最后一版的完成度和同步是所有版本里最高的，但它是靠**把表念一遍**做到的：旁白一句报一个值，动画一句长一根柱，两边自然严丝合缝。

逐根量过，七根柱每一根都落在自己那句话的窗口里，一个不漏：

| 数值 | 柱子长完的时刻 | 念它那句话的窗口 |
|---|---|---|
| 890 | 8.2s | 0 – 8.58 |
| 946 | 15.4s | 8.88 – 15.69 |
| 994 | 22.0s | 15.99 – 22.11 |
| 1006 | 29.2s | 22.41 – 29.45 |
| 1054 | 36.4s | 29.75 – 36.63 |
| 1103 | 45.4s | 36.93 – 45.64 |
| 1150 | 54.2s | 45.94 – 54.40 |

结论：复述率和同步互为反向。只看完成度和同步，模型老老实实一句一个数地念就能拿满分。所以这几个指标必须同时报，不能只看完成度。

### 4.4 去掉所有定量限制，模型还是念数据

把时长、句数之类的限制全删掉之后，模型写 7 句、47 秒，仍然念数据。加回 DataReel 那句 "explain, highlight, compare, or summarize the data as needed" 之后，复述率只从 0.43 降到 0.33，句子反而涨到 9 句、70 秒。

所以这不像是提示词没写好，更像模型本身的限制，能不能讲好故事确实是模型之间的能力差异。DataReel 自己的评测里也把"只是把数据读出来"判 1 分（满分 5），说明他们的输出同样有这个问题。

### 4.5 顺带一个 G2 的例子

最后一版里，七根柱的"宽度除以（数值减 850）"全部等于 2.867，说明柱子是按"数值减 850"画的。最宽那根看起来比最窄的长 7.5 倍，实际数值只差 1.29 倍；而横轴刻度从 890 开始标，零点和刻度本身也不一致。文案对、标注对、刻度也对，只有比例在骗人，人工看很难发现。

---

## 五、指标怎么算

### 5.1 复述率

定义：复述率 = 复述句数 ÷ 总句数。

逐句判断，同时满足下面两条才算"复述"：

**第一条，这句话里的数字，至少有一个能在本 clip 的数据表里找到。**

数字池取自数据表的三列：`value`、`x_value`、`relative_value`。每一列同时收录原值、乘以 100、除以 100 三种写法，这样 0.3 和 30% 不会因为量纲不同被当成两个数。绝对值小于 0.001 的丢掉（避免把 0 当成命中）。

**第二条，这句话里没有任何"判断词"。**

判断词是一份约九十词的词表，分三类：

- 比较与方向：higher、lower、less、fewer、rises、climbs、increases、falls、drops、doubles、halves、top、highest、lowest、outpaces、surpasses、steeper、flatter
- 转折与限定：only、just、despite、although、while、whereas、but、however、nearly、almost、roughly、remains
- 结论与判断：reveals、confirms、suggests、dominates、outweighs、gap、exception、advantage、jump、yield

两条同时满足的句子记为复述。

**这个算法有四个已知的粗糙之处，用的时候要一起说明：**

1. 纯词表匹配。一句话明明是判断，但没有词表里的词，就会误报。bar_27 那句 "Even small income jumps yield noticeable advantages" 一开始被判成复述，把 advantage 加进词表才改对。
2. 反过来也会漏。带判断词但实质还是报数的句子会被放过，比如 "the average climbs to 946"，它就是念了一个数。
3. 数字写成英文单词就完全看不见。有一版模型写的是 "eight hundred ninety"，数字匹配直接失效，需要在检查器里加数字词归一化。
4. 分母是句子数，不是字数也不是秒数。一句五秒的报数和一句两秒的判断，权重一样，这个不太合理。

所以复述率只能当代理指标，要和人工的"信息量"五点量表做相关性校准之后才能正式用。

### 5.2 完成度

三个数分开报，不合成一个：

- 内容完成度：必需单元里，有几条被旁白讲到了
- 视觉完成度：必需单元里，有几条在图里画出来了
- 联合完成度：两个通道同时成立、并且时间对上的，有几条

权重是平均的，每条必需单元等权，所以完成度就是通过条数除以必需条数。

### 5.3 时序

判定动作三步：先确定这条单元的证据是什么（G2 给的），再量出证据"齐备"的最早时刻（用逐帧扫描，柱子看宽度、环图看扇区角、标签看可见性），最后拿这个时刻去比锚点句的时间窗。

---

## 六、G3 现在的问题

### 6.1 锚点会锚空

G1 里每条单元写着一个锚点，形式是"提到某个数的那句"。这条写法是在看过原视频旁白的情况下写的。旁白不再念数字之后，"提到 890 的那句"根本不存在，锚点就锚空了。

正确做法是锚点按命题来定：判分时先找哪一句在讲这条单元（这本来就是内容通道要干的活），找到的那句才是锚点。这样旁白念数据也好、讲判断也好，都能锚上。

### 6.2 同一份输出，两种锚法结论相反

bar_27 有一条单元是"最高档高于最低档，1150 对 890"，它的视觉证据是两根柱同时可见。

在最后一版里：说 890 的是第 1 句（0 到 8.58 秒），可那时屏幕上只有 890 一根柱，1150 还没画出来；真正下比较结论的是第 9 句（62.2 到 69.6 秒），那时七根柱都齐了。

锚在报数句判不过，锚在下结论句判过。所以 G3 现在不是测不准，是政策没定。

### 6.3 要定的四条

1. 锚点归哪一句：报数句还是命题句
2. 时序判"窗口内证据可见"还是"证据首次出现必须落在窗口内"
3. 比较类单元跨两句时，是两个端点都要满足，还是任一满足
4. 容差取多少（现在只有一条样例上写过 1.5 秒，其余 339 条没实例化）

这四条定完，G3 就能写成脚本。

---

## 七、下一步

1. 把 G3 的四条政策定下来，并实例化到全部 clip。
2. 把完成度、复述率、时长、布局、时序做成一条命令，输入一个输出目录就出分数单。
3. 把 G2 的证据规则从"可见、能比较"收紧到带比例或角度（比较与占比类单元），否则像 4.5 那种截断轴会判过。
4. G0 目前只在一条手写样例上有完整形态。实际上数据表本身就是数字来源，需要为每条 clip 单独补的只有两样：每个数是图里印的还是我们估读的，以及允许多大误差。

---

## 八、和 DataReel 的逐项对比

### 8.1 任务与输入

| 项 | DataReel | 我们 |
|---|---|---|
| 输入 | 数据表、intent、目标时长、参考图截图（另给图的数量和参考图数量） | v1 给 intent + 数据表；v2 加旁白；v3 加参考图；v4 旁白和参考图都给 |
| 图型怎么定 | 靠参考图。Director 那一步明确要求"复现参考图里的图型和布局" | 用文字 chart_spec 指定，细到堆叠还是分组、横向还是竖向（340 条已推完） |
| 时长 | 作为输入给定，提示词里强调 "THIS TIMING IS STRICTLY ENFORCED DURING RENDERING"，并要求用满时长、不要提前结束 | 没给。时长由旁白长度决定，所以失控过 47 秒和 70 秒两种 |
| 输出 | 单个自包含 HTML，D3 动画加字幕 | 一样，单文件 HTML 加字幕，另配本地 TTS 音频 |

### 8.2 运行契约

| 项 | DataReel | 我们 |
|---|---|---|
| 确定性做法 | 禁用 requestAnimationFrame，只允许 setTimeout，必须实现 resetChart() 和 scheduleNow()，每次调用完整重放 | 要求纯函数 renderAt(t)，播放时才用 requestAnimationFrame |
| 画布 | 固定 1280x720，单个 `<svg id="chart">` | 允许 SVG 或 canvas。实测模型在几次之间从 SVG 跳到了 canvas，测量要两套探针 |
| 字幕位置 | 必须在 SVG 内，不能是 HTML 覆盖层；不重叠、不裁切、位置统一、太长要换行 | 只要求有一个 id="subtitle" 的可见字幕元素 |
| 失败兜底 | "The animation MUST still produce a correct static visualization if motion fails" | 没有这条，值得抄 |

### 8.3 字幕内容的要求

| 项 | DataReel | 我们 |
|---|---|---|
| 有没有句数限制 | 没有 | v0 有"3 到 4 句"；v5 起删掉 |
| 有没有"每句最多几个数" | 没有 | 只有 v2、v3 有，v4 起删掉 |
| 定性引导 | "Subtitles should explain, highlight, compare, or summarize the data as needed"，以及 "Author a cohesive story"、"The story should unfold progressively over time, not all at once" | v2 到 v4 用的是我自己编的措辞；v6 才改成用他们的原话 |
| 数据保真 | "Do NOT invent, interpolate, or modify data values" | "use only the values in the table, exactly as given" |
| 同步 | "Subtitles must be synchronized with animation events" | v0 只写了"每个关键值在说到它的那句可见"；v3 起改成逐句绑定并要求写 PLAN |

### 8.4 评测

| 项 | DataReel | 我们 |
|---|---|---|
| 代码层 | 读 HTML 的 LLM 裁判，四维 0 到 5 分：叙事质量、信息量、字幕与原转写的相似度、代码正确性，另统计 JS 错误率 | 没有单独的代码层打分，代码只用来跑渲染契约 |
| 视频层 | 视觉模型做**成对比较**，判 A 还是 B 更好，三维：可视化质量、字幕动画一致性、风格一致性，允许判平手，且不告诉裁判哪个是哪个 | 我们是对每条输出打绝对分，按单元判，不出成对结论 |
| 同步怎么判 | 视觉模型看两段视频给整体印象 | 拆成可量的：量出证据"齐备"的时刻，再比锚点句的时间窗 |
| 信息量怎么判 | 人工或模型打 0 到 5 分，其中"只是把数据读出来"明确判 1 分 | 复述率，词表加数字匹配的自动代理指标，待与人工分做校准 |
| 他们自己承认的短板 | 论文原话：代码层裁判 "does not capture animation-related issues such as clipping or subtitle-animation incoherence"；成对比较里 "Subtitle-Animation Coherence improves less consistently across judges, indicating that temporal synchronization remains a challenging aspect of the task" | 我们正在填的就是这块 |

---

## 附录 A：几版用过的提示词

写 HTML 的那份提示词里，除了下面 A.2 列出的第 5 条以外，其他部分从 v0 到 v6 没有改过（音频元素、`renderAt` 契约、时间轴注入、只用表里的值、只输出 HTML 这些）。写旁白的那份改动比较大，逐版列在 A.1。

### A.1 写旁白的提示词

**v0（原样，也是旧版 deepseek 基线用的）**

```
Write the narration for a 15-20 second data video as 3-4 short English sentences.
Base every number on the table below; do not invent data.
Return ONLY JSON: {"sentences": ["...", "..."]}

Intent: __INTENT__
Table:
__TABLE__
```

**v2（加"每句必须是判断"，同时加了图型那一行）**

```
Write the narration for a 15-20 second data video as 3-4 short English sentences.

Rules for every sentence:
- It must assert something a viewer cannot simply read off the chart: a comparison, a trend,
  an exception, or a conclusion. Numbers are evidence inside the claim, not the claim itself.
- Do not spend a sentence listing values. At most one number per sentence.
- Prefer comparative and interpretive wording (higher than, roughly doubles, only, despite,
  the gap widens, the exception is) over labelling.
- Base every number on the table below; do not invent data.
- Keep each sentence under 22 words so it can be read while the chart animates.
Return ONLY JSON: {"sentences": ["...", "..."]}

Chart form (fixed, do not change it):
__SPEC__

Intent: __INTENT__
Table:
__TABLE__
```

**v3（在 v2 的规则里加一条"一句一个新东西"）**

```
- Each sentence should introduce ONE new thing to look at, so the animation has one distinct
  beat per sentence. Do not put two separate claims in one sentence.
```

**v4（删掉句数和一个数的限制，改成总词数预算，加禁止因果）**

```
Write the narration for a data video of about 15-20 seconds. Use as many
sentences as you need, but keep the whole narration BETWEEN 24 AND 32 WORDS so the finished
video lands in the target length. Shorter reads as rushed, longer overruns.

Rules for every sentence:
- It must assert something a viewer cannot simply read off the chart: a comparison, a trend,
  an exception, or a conclusion. Numbers are evidence inside the claim, not the claim itself.
- Do not spend a whole sentence listing values. A number is expected when it is the evidence for
  the point, and two numbers are expected when the point is a comparison between them.
- Do not claim that one thing causes another. The table compares groups, it does not run an
  experiment. Say what differs and by how much, never what makes it happen.
- Base every number on the table below; do not invent data, and do not introduce a threshold,
  average or label that is not in the table.
- Each sentence should introduce ONE new thing to look at, so the animation has one distinct
  beat per sentence. Do not put two separate claims in one sentence.
Return ONLY JSON: {"sentences": ["...", "..."]}

Chart form (fixed, do not change it):
__SPEC__

Intent: __INTENT__
Table:
__TABLE__
```

**v5（把我加的限制全删，只留任务）**

```
Write the narration for a data video that conveys the intent below, using ONLY
the data in the table. Do not invent data.

Return ONLY JSON: {"sentences": ["...", "..."]}

Chart form (fixed, do not change it):
__SPEC__

Intent: __INTENT__
Table:
__TABLE__
```

**v6（现在用的这一版，等于 v5 加回 DataReel 的定性句）**

```
Write the narration for a data video that fulfills the intent below, using ONLY
the data in the table. Do not invent data.

Author a cohesive story. The narration should explain, highlight, compare, or summarize the data
as needed. The story should unfold progressively over time, not all at once.

Return ONLY JSON: {"sentences": ["...", "..."]}

Chart form (fixed, do not change it):
__SPEC__

Intent: __INTENT__
Table:
__TABLE__
```

### A.2 写 HTML 的提示词里那条同步要求，三版对照

**v0（只绑数值）**

```
5. The narration sentences and their start/end seconds are given below; show the matching sentence in
   #subtitle during its window, and animate the chart so each key value becomes visible while its
   sentence is spoken.
```

这条的问题是只把"关键数值"绑到句子上。以前旁白就是念数字，能对上；改成讲判断之后，多数句子没有数值，绑定就落空了。

**v3 / v4（逐句绑定，要求先声明计划）**

```
5. NARRATION-ANIMATION BINDING (required, this is what the video is scored on):
   a. Declare the plan as a JS constant, one entry per narration sentence, in order:
      const PLAN = [
        {sentence: 0, window: [0.0, 7.5], beat: "<short name>",
         evidence: "<exactly what must be on screen while this sentence is spoken>",
         change: [<second the visual change starts>, <second it ends>]},
        ... one entry per sentence, no omissions ...
      ];
      Put the identical array on window.__PLAN__ so the harness can read it.
   b. Every sentence must own at least one visual change, and that change (its `change`
      interval) must happen INSIDE that sentence's own window. No sentence may play over an
      unchanged frame, and the animation must not finish early.
   c. While a sentence is on screen, the evidence it names must already be visible, and it must
      stay visible until that sentence ends. If a sentence compares two things, BOTH sides of
      the comparison must be on screen for the whole sentence.
   d. Drive the animation from PLAN (loop over it). Do not schedule anything outside it.
```

**v6（现在这一版，改成 DataReel 的口径）**

```
5. SUBTITLES AND SYNC (mandatory):
   - The narration sentences and their start/end seconds are given below. Show the matching
     sentence in #subtitle during its window.
   - Subtitles must be synchronized with the animation events they describe: what a sentence
     talks about must be on screen while that sentence is showing, and must not disappear before
     the sentence ends.
   - Use the whole duration meaningfully. Allow the story to unfold progressively; do not rush
     key moments and do not finish the animation early.
   - Declare the sentence-to-animation plan as a JS array named PLAN, one entry per sentence:
       const PLAN = [
         {sentence: 0, window: [<start>, <end>], shows: "<what is on screen>",
          change: [<second it starts changing>, <second it stops>]},
         ... one entry per sentence, no omissions ...
       ];
     Expose the same array on window.__PLAN__, and build the animation by looping over PLAN.
```

---

## 附录 B：bar_27 六版的旁白原文

**v0 旧版（原提示词），35.9 秒，4 句**

```
0.0-7.7    SAT scores increase steadily with family income, starting at 890 for less than $20,000.
8.0-19.0   The average is 946 at $40,000, 994 at $60,000, and 1,006 at $80,000.
19.3-28.2  At $100,000 it reaches 1,054, then 1,103 at $140,000.
28.5-35.6  For families earning more than $200,000, the average score is 1,150.
```

**v2 加判断要求，22.9 秒，3 句**

```
0.0-7.6    Test scores climb steadily alongside earnings, with top earners averaging 1150 points.
7.9-15.2   Even small income jumps yield noticeable advantages, lifting averages to 946 points.
15.5-22.6  The financial divide remains stark, as lower-income students score only 890 on average.
```

**v3 再加逐句绑定，29.6 秒，4 句**

```
0.0-6.7     The top earners reach 1150, leaving a clear advantage over the lowest bracket.
7.0-14.0    Each successive bracket consistently outperforms the previous group, crossing the 1006 mark.
14.3-20.5   Crossing the 100000 dollar threshold unlocks noticeably stronger academic performance.
20.8-29.3   This steady climb proves wealth directly fuels stronger test outcomes, reaching 1103 before the final jump.
```

最后一句是因果越界（"proves wealth directly fuels"），G1 的 `unsupported_to_avoid` 里明确禁止这种说法，所以我后来在提示词里加了禁止因果那条。

**v4 放宽数量、加反因果，14.3 秒，3 句**

```
0.0-3.5    Scores rise consistently with household earnings.
3.8-10.0   The bottom group averages eight hundred ninety points, versus eleven hundred fifty at the top.
10.3-14.0  This gap highlights a clear advantage for higher earners.
```

第二句把数字写成了英文单词，数字匹配器直接失效。这个应该在检查器里加数字词归一化，不该在提示词里禁。

**v5 只留任务，47.0 秒，7 句**

```
0.0-6.7    Students from households earning less than $20,000 record an SAT score of 890.
7.0-13.9   As family income rises to $40,000, the score increases to 946.
14.2-20.2  At the $60,000 income level, the score reaches 994.
20.5-25.4  Households earning $80,000 show a score of 1006.
25.7-32.0  When income reaches $100,000, the score climbs to 1054.
32.3-38.5  Families making $140,000 have scores of 1103.
38.8-46.6  Finally, households earning more than $200,000 achieve the highest score of 1150.
```

**v6 加回 DataReel 定性句，69.9 秒，9 句**

```
0.0-8.6    Starting at the lowest income bracket, families earning less than $20,000 see an average SAT score of 890.
8.9-15.7   As household earnings rise to $40,000, that average climbs to 946.
16.0-22.1  Crossing into the $60,000 range, scores reach 994.
22.4-29.5  At $80,000, the average breaks past the thousand mark, landing at 1006.
29.8-36.6  For households making $100,000, the typical score jumps to 1054.
36.9-45.6  Moving further up the economic ladder, families at $140,000 report an average of 1103.
45.9-54.4  Finally, students from households earning more than $200,000 achieve the top average of 1150.
54.7-61.9  This unbroken upward trajectory reveals a clear positive relationship between family income and SAT performance.
62.2-69.6  The data ultimately confirms that students from wealthier families consistently secure higher standardized test scores.
```

---

## 附录 C：V2 / V4 / V6 三版对照

这三版按修改顺序排：V2 是"加判断要求"那一版，V4 是"放宽数量限制、加逐句绑定"那一版，V6 是"改用 DataReel 措辞"的当前版本。三版的旁白提示词原文见 A.1，写 HTML 时的同步要求原文见 A.2。

### C.1 三版提示词的区别

| 提示词里的规则 | V2 | V4 | V6 |
|---|---|---|---|
| 句数限制"3 到 4 句" | 有 | 删掉 | 删掉 |
| 总词数预算 | 无 | 24 到 32 词 | 删掉 |
| "每句最多一个数字" | 有 | 删掉 | 删掉 |
| "每句必须给判断，不能只念数" | 有 | 有 | 删掉，换成 DataReel 的定性句 |
| "每句只引入一个新东西" | 无 | 有 | 删掉 |
| "不许说因果" | 无 | 有 | 删掉 |
| DataReel 的定性句 | 无 | 无 | 有 |
| 图型 chart_spec | 有 | 有 | 有 |
| 写 HTML 的同步要求 | 只绑数值（v0 原版） | 逐句绑定 + 要求写 PLAN | DataReel 口径 + 要求写 PLAN |

一句话概括三版的差别：V2 靠"规定说什么"来逼出叙事，V4 放松了说什么、改成靠流程绑定逼同步，V6 把"说什么"全部交还给模型，只在流程上要求同步。

### C.2 三份代码里最该看的三处

**第一处，柱子长度怎么算。三版都用了截断基线，但基线不同。**

| | V2 | V4 | V6 |
|---|---|---|---|
| 基线值 | 850 | 800 | 850 |
| 实际写法 | `VAL_MIN = 850; valToX(v) = left + (v-850)/350*W` | `SCORE_MIN = 800; ratio = (val-800)/400` | `MIN_VAL = 850; SCALE = W/(1150-850)` |
| 最高柱与最低柱的视觉长度比 | 7.5 倍 | 3.89 倍 | 7.5 倍 |

真实数值比是 1150 ÷ 890 = 1.29 倍。三版都把差距放大了，只是放大倍数不同。同一张图、同一张数据表，三次跑出三种视觉量级——这正是 G2 必须带比例判据的原因，只写"两根柱要可见"是拦不住的。

**第二处，动画怎么排期。**

| | V2 | V4 | V6 |
|---|---|---|---|
| 有没有 PLAN | 没有 | 有，3 条 | 有，9 条 |
| 排期来源 | 硬编码：`BAR_ENTRY_STARTS = [0.0, 1.2, 2.8, 4.5, 6.0, 8.5, 11.0]`，最后一根 11.0 秒起、12.0 秒画完 | 循环读 PLAN | 循环读 PLAN，第 i 句对应第 i 根柱 |
| 结果 | 七根柱 12 秒画完，那时旁白已经说到第三句，而最后一句（15.5 到 22.6 秒）画面完全不动 | 每句各有一次动作 | 七根柱逐根落在自己那句话的窗口里，一个不漏 |

这是三版差别最大的地方：V2 的动画节奏是模型自己拍的，跟旁白无关；V4 之后有了逐句计划，动画才开始跟着话走。

**第三处，渲染方式。** V2 和 V6 用 SVG，V4 自己换成了 canvas。同一份提示词允许两种，模型每次选哪个不确定，测量就得准备两套探针（SVG 查 DOM，canvas 要挂钩子拦 `fillRect` 和 `fillText`）。这一条值得在提示词里钉死。

### C.3 三版完整代码

下面是模型自己产出的 HTML 原文。评测用的两段注入脚本已经去掉（一段是 `window.__BENCHMARK__` 的时间轴注入，一段是末尾负责按 t 定位画面的钩子），其余一字未改。

顺带记一个流程上的小毛病：模型原始输出外面套了一层 markdown 围栏，我们的抽取正则从 `<!DOCTYPE html>` 一直取到字符串末尾，把收尾那行 ``` 也带进了 `entry.html`。渲染不受影响，但文件里多了一行垃圾。附录里这三份是清掉之后的样子。


#### V2（加判断要求） — `baseline_narr_v2/bar_27/entry_model_only.html`

````html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SAT Scores by Family Income</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: #1a1a2e;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    min-height: 100vh;
    font-family: 'Segoe UI', Arial, sans-serif;
    color: #e0e0e0;
  }
  #chart-container {
    width: 1280px;
    height: 720px;
    position: relative;
    background: #16213e;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  }
  svg#chart {
    width: 100%;
    height: 100%;
  }
  #subtitle {
    width: 1280px;
    min-height: 60px;
    margin-top: 16px;
    padding: 14px 24px;
    background: #0f3460;
    border-radius: 8px;
    font-size: 20px;
    text-align: center;
    color: #e8e8e8;
    line-height: 1.4;
    letter-spacing: 0.3px;
    transition: opacity 0.2s;
  }
  #controls {
    margin-top: 16px;
    display: flex;
    gap: 12px;
    align-items: center;
  }
  #play-btn {
    padding: 10px 28px;
    font-size: 16px;
    background: #4A96D6;
    color: white;
    border: none;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
  }
  #play-btn:hover { background: #5aaae6; }
  #time-display {
    font-size: 14px;
    color: #aaa;
    min-width: 100px;
    text-align: center;
  }
</style>
</head>
<body>

<div id="chart-container">
  <svg id="chart" viewBox="0 0 1280 720" xmlns="http://www.w3.org/2000/svg"></svg>
</div>
<div id="subtitle">Press Play to begin</div>
<div id="controls">
  <button id="play-btn">▶ Play</button>
  <span id="time-display">0.0 / 0.0 s</span>
</div>

<audio id="tts" src="audio/tts.wav"></audio>

<script>
(function() {
  // ── DATA ──────────────────────────────────────────────
  const BAR_DATA = [
    { label: "Less than $20,000", value: 890.0,  color: "#4A96D6" },
    { label: "$40,000",            value: 946.0,  color: "#4A96D6" },
    { label: "$60,000",            value: 994.0,  color: "#4A96D6" },
    { label: "$80,000",            value: 1006.0, color: "#4A96D6" },
    { label: "$100,000",           value: 1054.0, color: "#4A96D6" },
    { label: "$140,000",           value: 1103.0, color: "#4A96D6" },
    { label: "More than $200,000", value: 1150.0, color: "#4A96D6" }
  ];

  const NARRATION = [
    { start: 0.0,   end: 7.553,  text: "Test scores climb steadily alongside earnings, with top earners averaging 1150 points." },
    { start: 7.853, end: 15.186, text: "Even small income jumps yield noticeable advantages, lifting averages to 946 points." },
    { start: 15.486, end: 22.589, text: "The financial divide remains stark, as lower-income students score only 890 on average." }
  ];

  // ── TIMELINE ──────────────────────────────────────────
  let DURATION = 22.589;
  if (typeof window.__BENCHMARK__ !== "undefined") {
    DURATION = window.__BENCHMARK__.duration || DURATION;
    if (window.__BENCHMARK__.sentences && window.__BENCHMARK__.sentences.length > 0) {
      NARRATION.length = 0;
      window.__BENCHMARK__.sentences.forEach(s => {
        NARRATION.push({ start: s.start, end: s.end, text: s.text });
      });
    }
  }

  // ── CHART GEOMETRY ────────────────────────────────────
  const SVG_W = 1280, SVG_H = 720;
  const MARGIN = { top: 80, right: 80, bottom: 60, left: 260 };
  const CHART_W = SVG_W - MARGIN.left - MARGIN.right;
  const CHART_H = SVG_H - MARGIN.top - MARGIN.bottom;
  const BAR_HEIGHT = Math.min(52, (CHART_H - 20) / BAR_DATA.length - 6);
  const BAR_GAP = (CHART_H - BAR_HEIGHT * BAR_DATA.length) / (BAR_DATA.length + 1);
  const VAL_MIN = 850;
  const VAL_MAX = 1200;
  const VAL_RANGE = VAL_MAX - VAL_MIN;

  function valToX(v) {
    return MARGIN.left + ((v - VAL_MIN) / VAL_RANGE) * CHART_W;
  }

  // ── STAGGERED BAR ENTRY TIMES ─────────────────────────
  // Distribute 7 bars across the first ~14 seconds so they build up
  const BAR_ENTRY_STARTS = [0.0, 1.2, 2.8, 4.5, 6.0, 8.5, 11.0];
  const BAR_ENTRY_DURATIONS = [1.8, 1.6, 1.5, 1.4, 1.3, 1.2, 1.0];

  function easeOutCubic(t) {
    return 1 - Math.pow(1 - t, 3);
  }

  function getBarProgress(t, idx) {
    const start = BAR_ENTRY_STARTS[idx];
    const dur = BAR_ENTRY_DURATIONS[idx];
    if (t <= start) return 0;
    const p = (t - start) / dur;
    return Math.min(1, p);
  }

  // ── SUBTITLE ──────────────────────────────────────────
  function getSubtitleText(t) {
    for (let i = 0; i < NARRATION.length; i++) {
      if (t >= NARRATION[i].start && t < NARRATION[i].end) {
        return NARRATION[i].text;
      }
    }
    return "";
  }

  // ── RENDER AT TIME T ──────────────────────────────────
  function renderAt(t) {
    t = Math.max(0, Math.min(t, DURATION));
    const svg = document.getElementById("chart");
    const subEl = document.getElementById("subtitle");
    const timeDisp = document.getElementById("time-display");

    // Subtitle
    const subText = getSubtitleText(t);
    subEl.textContent = subText || "Press Play to begin";

    // Time display
    timeDisp.textContent = t.toFixed(1) + " / " + DURATION.toFixed(1) + " s";

    // Build SVG content
    let html = '';

    // Title
    html += `<text x="${SVG_W/2}" y="42" text-anchor="middle" fill="#e0e0e0" font-size="26" font-weight="bold" font-family="Segoe UI, Arial, sans-serif">Average SAT Score by Family Income Level</text>`;
    html += `<text x="${SVG_W/2}" y="66" text-anchor="middle" fill="#8899aa" font-size="15" font-family="Segoe UI, Arial, sans-serif">Positive relationship between family income and SAT scores</text>`;

    // X-axis label
    html += `<text x="${MARGIN.left + CHART_W/2}" y="${SVG_H - 12}" text-anchor="middle" fill="#8899aa" font-size="14" font-family="Segoe UI, Arial, sans-serif">Average SAT Score</text>`;

    // Grid lines and X-axis ticks
    const tickValues = [850, 900, 950, 1000, 1050, 1100, 1150, 1200];
    tickValues.forEach(v => {
      const x = valToX(v);
      html += `<line x1="${x}" y1="${MARGIN.top}" x2="${x}" y2="${MARGIN.top + CHART_H}" stroke="#2a3a5c" stroke-width="1" stroke-dasharray="4,4"/>`;
      html += `<text x="${x}" y="${MARGIN.top + CHART_H + 20}" text-anchor="middle" fill="#8899aa" font-size="12" font-family="Segoe UI, Arial, sans-serif">${v}</text>`;
    });

    // Axis line
    html += `<line x1="${MARGIN.left}" y1="${MARGIN.top + CHART_H}" x2="${MARGIN.left + CHART_W}" y2="${MARGIN.top + CHART_H}" stroke="#4a5a7c" stroke-width="1.5"/>`;

    // Bars
    BAR_DATA.forEach((bar, i) => {
      const y = MARGIN.top + BAR_GAP + i * (BAR_HEIGHT + BAR_GAP);
      const progress = getBarProgress(t, i);
      const easedProgress = easeOutCubic(progress);
      const currentVal = bar.value * easedProgress;
      const barX = valToX(currentVal);
      const barFullEnd = valToX(bar.value);
      const startX = valToX(VAL_MIN);

      // Bar shadow
      if (progress > 0) {
        html += `<rect x="${startX}" y="${y + 2}" width="${barFullEnd - startX}" height="${BAR_HEIGHT}" rx="4" fill="#00000022"/>`;
      }

      // Bar gradient-like effect using layered rects
      if (progress > 0) {
        // Main bar
        html += `<rect x="${startX}" y="${y}" width="${Math.max(0, barX - startX)}" height="${BAR_HEIGHT}" rx="4" fill="${bar.color}" opacity="${0.7 + 0.3 * easedProgress}"/>`;

        // Highlight overlay
        html += `<rect x="${startX}" y="${y}" width="${Math.max(0, barX - startX)}" height="${BAR_HEIGHT / 2}" rx="4" fill="#ffffff" opacity="${0.08 * easedProgress}"/>`;
      }

      // Value label at end of bar
      if (progress > 0.5) {
        const labelOpacity = Math.min(1, (progress - 0.5) * 2);
        html += `<text x="${barFullEnd + 8}" y="${y + BAR_HEIGHT / 2 + 5}" fill="#e0e0e0" font-size="14" font-weight="bold" font-family="Segoe UI, Arial, sans-serif" opacity="${labelOpacity}">${bar.value.toFixed(0)}</text>`;
      }

      // Category label
      html += `<text x="${MARGIN.left - 12}" y="${y + BAR_HEIGHT / 2 + 5}" text-anchor="end" fill="#c0c8d8" font-size="13" font-family="Segoe UI, Arial, sans-serif">${bar.label}</text>`;
    });

    // Source note
    html += `<text x="${SVG_W - MARGIN.right}" y="${SVG_H - 12}" text-anchor="right" fill="#556677" font-size="11" font-family="Segoe UI, Arial, sans-serif">Source: printed</text>`;

    svg.innerHTML = html;
  }

  // ── PLAYBACK LOOP ─────────────────────────────────────
  let playing = false;
  let rafId = null;
  const audio = document.getElementById("tts");
  const playBtn = document.getElementById("play-btn");

  function playbackLoop() {
    if (!playing) return;
    const t = audio.currentTime;
    renderAt(t);
    if (t >= DURATION || audio.paused) {
      playing = false;
      playBtn.textContent = "▶ Play";
      return;
    }
    rafId = requestAnimationFrame(playbackLoop);
  }

  function startPlayback() {
    if (playing) {
      audio.pause();
      playing = false;
      playBtn.textContent = "▶ Play";
      return;
    }
    audio.play().catch(() => {});
    playing = true;
    playBtn.textContent = "⏸ Pause";
    playbackLoop();
  }

  playBtn.addEventListener("click", startPlayback);

  // Also handle audio timeupdate as backup
  audio.addEventListener("timeupdate", () => {
    if (playing) renderAt(audio.currentTime);
  });

  // ── URL PARAM HANDLING ────────────────────────────────
  const urlParams = new URLSearchParams(location.search);
  const tParam = urlParams.get("t");
  if (tParam !== null) {
    const t = parseFloat(tParam);
    if (!isNaN(t)) {
      renderAt(t);
      // Don't auto-play, just show the frame
      return;
    }
  }

  // ── INITIAL RENDER ────────────────────────────────────
  renderAt(0);

  // Expose globally
  window.renderAt = renderAt;
})();
</script>


</body>
</html>
````

#### V4（放宽数量，加逐句绑定） — `baseline_narr_v4/bar_27/entry_model_only.html`

````html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SAT Scores by Family Income</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: #1a1a2e;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  font-family: 'Segoe UI', Arial, sans-serif;
  color: #e0e0e0;
}
#chart-container {
  position: relative;
  width: 1280px;
  height: 720px;
  background: #16213e;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
canvas {
  display: block;
  width: 1280px;
  height: 720px;
}
#subtitle {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0,0,0,0.75);
  color: #fff;
  padding: 10px 28px;
  border-radius: 8px;
  font-size: 22px;
  text-align: center;
  max-width: 1100px;
  min-height: 44px;
  line-height: 1.4;
  pointer-events: none;
  transition: opacity 0.2s;
}
#controls {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  align-items: center;
}
button {
  background: #4A96D6;
  color: white;
  border: none;
  padding: 10px 24px;
  border-radius: 6px;
  font-size: 16px;
  cursor: pointer;
}
button:hover { background: #3a86c6; }
#time-display { font-size: 14px; color: #aaa; }
</style>
</head>
<body>

<div id="chart-container">
  <canvas id="chart" width="1280" height="720"></canvas>
  <div id="subtitle"></div>
</div>

<div id="controls">
  <button id="play-btn">▶ Play</button>
  <span id="time-display">0.0 / 0.0 s</span>
</div>

<audio id="tts" src="audio/tts.wav"></audio>

<script>
// ── DATA ──────────────────────────────────────────────────────────────
const BARS = [
  { label: "Less than $20,000", value: 890.0,  color: "#4A96D6" },
  { label: "$40,000",           value: 946.0,  color: "#4A96D6" },
  { label: "$60,000",           value: 994.0,  color: "#4A96D6" },
  { label: "$80,000",           value: 1006.0, color: "#4A96D6" },
  { label: "$100,000",          value: 1054.0, color: "#4A96D6" },
  { label: "$140,000",          value: 1103.0, color: "#4A96D6" },
  { label: "More than $200,000",value: 1150.0, color: "#4A96D6" }
];

const SCORE_MIN = 800;
const SCORE_MAX = 1200;

// ── PLAN (narration-animation binding) ────────────────────────────────
const PLAN = [
  {
    sentence: 0,
    window: [0.0, 3.514],
    beat: "rising-trend",
    evidence: "all seven bars displayed with increasing heights",
    change: [0.0, 3.514]
  },
  {
    sentence: 1,
    window: [3.814, 9.967],
    beat: "bottom-vs-top",
    evidence: "bottom bar (890) and top bar (1150) highlighted",
    change: [3.814, 9.967]
  },
  {
    sentence: 2,
    window: [10.267, 14.026],
    beat: "gap-emphasis",
    evidence: "gap between bottom and top bars emphasized with annotation",
    change: [10.267, 14.026]
  }
];
window.__PLAN__ = PLAN;

// ── TIMELINE SETUP ────────────────────────────────────────────────────
let DURATION = 14.026;
let SENTENCES = [];

if (window.__BENCHMARK__) {
  DURATION = window.__BENCHMARK__.duration || DURATION;
  SENTENCES = window.__BENCHMARK__.sentences || [];
} else {
  // Fallback from PLAN
  PLAN.forEach(p => {
    const idx = p.sentence;
    if (!SENTENCES[idx]) {
      SENTENCES[idx] = { start: p.window[0], end: p.window[1], text: "" };
    }
  });
  // Fill in narration texts
  const FALLBACK_TEXTS = [
    "Scores rise consistently with household earnings.",
    "The bottom group averages eight hundred ninety points, versus eleven hundred fifty at the top.",
    "This gap highlights a clear advantage for higher earners."
  ];
  FALLBACK_TEXTS.forEach((t, i) => {
    if (SENTENCES[i]) SENTENCES[i].text = t;
  });
}

// ── CANVAS SETUP ──────────────────────────────────────────────────────
const canvas = document.getElementById("chart");
const ctx = canvas.getContext("2d");
const subtitleEl = document.getElementById("subtitle");
const playBtn = document.getElementById("play-btn");
const timeDisplay = document.getElementById("time-display");

// ── LAYOUT CONSTANTS ──────────────────────────────────────────────────
const MARGIN = { top: 70, right: 60, bottom: 80, left: 220 };
const CHART_W = 1280 - MARGIN.left - MARGIN.right;
const CHART_H = 720 - MARGIN.top - MARGIN.bottom;
const BAR_HEIGHT = 52;
const BAR_GAP = 14;
const TOTAL_BARS_H = BARS.length * (BAR_HEIGHT + BAR_GAP) - BAR_GAP;
const CHART_Y_START = MARGIN.top + (CHART_H - TOTAL_BARS_H) / 2;

function yForBar(i) {
  return CHART_Y_START + i * (BAR_HEIGHT + BAR_GAP);
}

function xForScore(val) {
  const ratio = (val - SCORE_MIN) / (SCORE_MAX - SCORE_MIN);
  return MARGIN.left + ratio * CHART_W;
}

// ── EASING ────────────────────────────────────────────────────────────
function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3);
}

function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }
function lerp(a, b, t) { return a + (b - a) * t; }

// ── RENDER AT TIME T ──────────────────────────────────────────────────
window.renderAt = function(t) {
  t = clamp(t, 0, DURATION);

  // Clear
  ctx.clearRect(0, 0, 1280, 720);

  // Background gradient
  const bgGrad = ctx.createLinearGradient(0, 0, 0, 720);
  bgGrad.addColorStop(0, "#16213e");
  bgGrad.addColorStop(1, "#1a1a2e");
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, 1280, 720);

  // ── TITLE ─────────────────────────────────────────────────────────
  ctx.fillStyle = "#ffffff";
  ctx.font = "bold 28px 'Segoe UI', Arial, sans-serif";
  ctx.textAlign = "center";
  ctx.fillText("Average SAT Score by Household Income Level", 640, 40);

  ctx.fillStyle = "#8899aa";
  ctx.font = "16px 'Segoe UI', Arial, sans-serif";
  ctx.fillText("Source: College Board — Printed Data", 640, 65);

  // ── X-AXIS ────────────────────────────────────────────────────────
  ctx.strokeStyle = "#3a4a5a";
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(MARGIN.left, MARGIN.top + CHART_H + 4);
  ctx.lineTo(MARGIN.left + CHART_W, MARGIN.top + CHART_H + 4);
  ctx.stroke();

  // X-axis ticks and labels
  ctx.fillStyle = "#8899aa";
  ctx.font = "13px 'Segoe UI', Arial, sans-serif";
  ctx.textAlign = "center";
  for (let s = 800; s <= 1200; s += 50) {
    const x = xForScore(s);
    ctx.beginPath();
    ctx.moveTo(x, MARGIN.top + CHART_H);
    ctx.lineTo(x, MARGIN.top + CHART_H + 6);
    ctx.strokeStyle = "#3a4a5a";
    ctx.stroke();
    ctx.fillText(s.toString(), x, MARGIN.top + CHART_H + 22);
  }

  ctx.fillStyle = "#8899aa";
  ctx.font = "14px 'Segoe UI', Arial, sans-serif";
  ctx.fillText("SAT Score", MARGIN.left + CHART_W / 2, MARGIN.top + CHART_H + 48);

  // ── Y-AXIS LABELS & BARS ──────────────────────────────────────────
  // Determine which bars should be visible based on PLAN timing
  // Sentence 0 (0-3.514): bars appear sequentially
  // Sentence 1 (3.814-9.967): all bars visible, bottom & top highlighted
  // Sentence 2 (10.267-14.026): all bars visible, gap emphasized

  const activeSentence = getActiveSentence(t);

  BARS.forEach((bar, i) => {
    const barY = yForBar(i);
    const barX = xForScore(bar.value);
    const barWidth = barX - MARGIN.left;

    // Determine visibility progress per bar
    let barProgress = 0;
    if (activeSentence === 0) {
      // Bars appear sequentially during sentence 0
      const barStartTime = i * 0.45;
      const barEndTime = barStartTime + 0.55;
      if (t >= barEndTime) {
        barProgress = 1;
      } else if (t >= barStartTime) {
        barProgress = easeOutCubic((t - barStartTime) / (barEndTime - barStartTime));
      }
    } else {
      // All bars fully visible after sentence 0
      barProgress = 1;
    }

    if (barProgress <= 0) return;

    const effectiveWidth = barWidth * barProgress;

    // Bar shadow
    ctx.fillStyle = "rgba(0,0,0,0.2)";
    ctx.fillRect(MARGIN.left + 3, barY + 3, effectiveWidth, BAR_HEIGHT);

    // Bar body
    const grad = ctx.createLinearGradient(MARGIN.left, barY, MARGIN.left + effectiveWidth, barY);
    grad.addColorStop(0, bar.color);
    grad.addColorStop(1, lightenColor(bar.color, 20));
    ctx.fillStyle = grad;

    // Rounded rect
    const r = 4;
    ctx.beginPath();
    ctx.moveTo(MARGIN.left + r, barY);
    ctx.lineTo(MARGIN.left + effectiveWidth - r, barY);
    ctx.quadraticCurveTo(MARGIN.left + effectiveWidth, barY, MARGIN.left + effectiveWidth, barY + r);
    ctx.lineTo(MARGIN.left + effectiveWidth, barY + BAR_HEIGHT - r);
    ctx.quadraticCurveTo(MARGIN.left + effectiveWidth, barY + BAR_HEIGHT, MARGIN.left + effectiveWidth - r, barY + BAR_HEIGHT);
    ctx.lineTo(MARGIN.left + r, barY + BAR_HEIGHT);
    ctx.quadraticCurveTo(MARGIN.left, barY + BAR_HEIGHT, MARGIN.left, barY + BAR_HEIGHT - r);
    ctx.lineTo(MARGIN.left, barY + r);
    ctx.quadraticCurveTo(MARGIN.left, barY, MARGIN.left + r, barY);
    ctx.fill();

    // Value label at end of bar
    if (barProgress > 0.5) {
      ctx.fillStyle = "#ffffff";
      ctx.font = "bold 15px 'Segoe UI', Arial, sans-serif";
      ctx.textAlign = "left";
      ctx.fillText(bar.value.toFixed(0), MARGIN.left + effectiveWidth + 8, barY + BAR_HEIGHT / 2 + 5);
    }

    // Category label on left
    ctx.fillStyle = "#c0d0e0";
    ctx.font = "14px 'Segoe UI', Arial, sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(bar.label, MARGIN.left - 12, barY + BAR_HEIGHT / 2 + 5);

    // ── HIGHLIGHTS for sentence 1 ───────────────────────────────────
    if (activeSentence === 1) {
      if (i === 0 || i === 6) {
        // Glow effect for bottom and top bars
        ctx.save();
        ctx.shadowColor = "#ffcc00";
        ctx.shadowBlur = 18;
        ctx.strokeStyle = "#ffcc00";
        ctx.lineWidth = 2.5;
        ctx.beginPath();
        ctx.moveTo(MARGIN.left + r, barY);
        ctx.lineTo(MARGIN.left + effectiveWidth - r, barY);
        ctx.quadraticCurveTo(MARGIN.left + effectiveWidth, barY, MARGIN.left + effectiveWidth, barY + r);
        ctx.lineTo(MARGIN.left + effectiveWidth, barY + BAR_HEIGHT - r);
        ctx.quadraticCurveTo(MARGIN.left + effectiveWidth, barY + BAR_HEIGHT, MARGIN.left + effectiveWidth - r, barY + BAR_HEIGHT);
        ctx.lineTo(MARGIN.left + r, barY + BAR_HEIGHT);
        ctx.quadraticCurveTo(MARGIN.left, barY + BAR_HEIGHT, MARGIN.left, barY + BAR_HEIGHT - r);
        ctx.lineTo(MARGIN.left, barY + r);
        ctx.quadraticCurveTo(MARGIN.left, barY, MARGIN.left + r, barY);
        ctx.closePath();
        ctx.stroke();
        ctx.restore();

        // Annotation label
        const annotText = i === 0 ? "Lowest: 890" : "Highest: 1150";
        ctx.fillStyle = "#ffcc00";
        ctx.font = "bold 13px 'Segoe UI', Arial, sans-serif";
        ctx.textAlign = "center";
        const annotX = MARGIN.left + effectiveWidth / 2;
        const annotY = i === 0 ? barY - 10 : barY + BAR_HEIGHT + 18;
        ctx.fillText(annotText, annotX, annotY);
      }
    }

    // ── GAP ANNOTATION for sentence 2 ───────────────────────────────
    if (activeSentence === 2) {
      // Draw gap bracket between bottom and top bars
      const bottomBarY = yForBar(0);
      const topBarY = yForBar(6);
      const gapMidX = MARGIN.left - 40;

      // Vertical bracket line
      ctx.strokeStyle = "#ff6b6b";
      ctx.lineWidth = 2;
      ctx.setLineDash([6, 4]);
      ctx.beginPath();
      ctx.moveTo(gapMidX, bottomBarY + BAR_HEIGHT / 2);
      ctx.lineTo(gapMidX, topBarY + BAR_HEIGHT / 2);
      ctx.stroke();
      ctx.setLineDash([]);

      // Arrow heads
      ctx.fillStyle = "#ff6b6b";
      ctx.beginPath();
      ctx.moveTo(gapMidX, bottomBarY + BAR_HEIGHT / 2);
      ctx.lineTo(gapMidX - 6, bottomBarY + BAR_HEIGHT / 2 - 8);
      ctx.lineTo(gapMidX + 6, bottomBarY + BAR_HEIGHT / 2 - 8);
      ctx.fill();
      ctx.beginPath();
      ctx.moveTo(gapMidX, topBarY + BAR_HEIGHT / 2);
      ctx.lineTo(gapMidX - 6, topBarY + BAR_HEIGHT / 2 + 8);
      ctx.lineTo(gapMidX + 6, topBarY + BAR_HEIGHT / 2 + 8);
      ctx.fill();

      // Gap value label
      const gapValue = 1150 - 890;
      ctx.fillStyle = "#ff6b6b";
      ctx.font = "bold 16px 'Segoe UI', Arial, sans-serif";
      ctx.textAlign = "right";
      ctx.fillText("Gap: " + gapValue + " pts", gapMidX - 8, (bottomBarY + topBarY + BAR_HEIGHT) / 2 + 5);
    }
  });

  // ── SUBTITLE ──────────────────────────────────────────────────────
  updateSubtitle(t);

  // ── TIME DISPLAY ──────────────────────────────────────────────────
  timeDisplay.textContent = t.toFixed(1) + " / " + DURATION.toFixed(1) + " s";
};

// ── HELPER: get active sentence index ─────────────────────────────────
function getActiveSentence(t) {
  for (let i = 0; i < SENTENCES.length; i++) {
    if (t >= SENTENCES[i].start && t < SENTENCES[i].end) return i;
  }
  // Check last sentence boundary
  if (SENTENCES.length > 0 && t >= SENTENCES[SENTENCES.length - 1].start) return SENTENCES.length - 1;
  return -1;
}

// ── HELPER: update subtitle ───────────────────────────────────────────
function updateSubtitle(t) {
  const activeIdx = getActiveSentence(t);
  if (activeIdx >= 0 && SENTENCES[activeIdx].text) {
    subtitleEl.textContent = SENTENCES[activeIdx].text;
    subtitleEl.style.opacity = "1";
  } else {
    subtitleEl.textContent = "";
    subtitleEl.style.opacity = "0";
  }
}

// ── HELPER: lighten color ─────────────────────────────────────────────
function lightenColor(hex, amount) {
  const num = parseInt(hex.slice(1), 16);
  const r = Math.min(255, (num >> 16) + amount);
  const g = Math.min(255, ((num >> 8) & 0xff) + amount);
  const b = Math.min(255, (num & 0xff) + amount);
  return "#" + ((r << 16) | (g << 8) | b).toString(16).padStart(6, "0");
}

// ── PLAYBACK LOOP ─────────────────────────────────────────────────────
let isPlaying = false;
let animFrameId = null;
let startTime = 0;
let pausedTime = 0;

function playbackLoop() {
  if (!isPlaying) return;
  const elapsed = (performance.now() - startTime) / 1000 + pausedTime;
  if (elapsed >= DURATION) {
    isPlaying = false;
    pausedTime = 0;
    renderAt(DURATION);
    playBtn.textContent = "▶ Play";
    return;
  }
  renderAt(elapsed);
  animFrameId = requestAnimationFrame(playbackLoop);
}

playBtn.addEventListener("click", () => {
  const audio = document.getElementById("tts");
  if (isPlaying) {
    isPlaying = false;
    pausedTime = parseFloat(timeDisplay.textContent.split(" / ")[0]);
    cancelAnimationFrame(animFrameId);
    playBtn.textContent = "▶ Play";
    audio.pause();
    return;
  }
  isPlaying = true;
  startTime = performance.now();
  playBtn.textContent = "⏸ Pause";
  audio.currentTime = 0;
  audio.play().catch(() => {});
  playbackLoop();
});

// ── URL PARAM: seek to specific time ──────────────────────────────────
const urlParams = new URLSearchParams(location.search);
const tParam = urlParams.get("t");
if (tParam !== null) {
  const seekT = parseFloat(tParam);
  renderAt(seekT);
  // Don't auto-play, just show the frame
} else {
  renderAt(0);
}
</script>

</body>
</html>
````

#### V6（DataReel 措辞，当前版本） — `baseline_narr_v6/bar_27/entry_model_only.html`

````html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Family Income &amp; SAT Scores</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  background: #1a1a2e;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  font-family: 'Segoe UI', Arial, sans-serif;
  color: #e0e0e0;
}
#chart-container {
  width: 1280px;
  height: 720px;
  position: relative;
  background: #16213e;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
}
svg { display: block; }
#subtitle {
  width: 1280px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: 22px;
  font-weight: 600;
  color: #ffffff;
  background: rgba(0,0,0,0.6);
  margin-top: 0;
  letter-spacing: 0.3px;
  transition: opacity 0.3s;
}
#controls {
  margin-top: 16px;
  display: flex;
  gap: 12px;
  align-items: center;
}
#controls button {
  padding: 10px 28px;
  font-size: 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  background: #4A96D6;
  color: white;
  font-weight: 600;
  transition: background 0.2s;
}
#controls button:hover { background: #3a7bc8; }
#progress-bar {
  width: 1280px;
  height: 6px;
  background: #0f3460;
  border-radius: 3px;
  margin-top: 8px;
  overflow: hidden;
}
#progress-fill {
  height: 100%;
  width: 0%;
  background: #4A96D6;
  border-radius: 3px;
  transition: width 0.1s linear;
}
</style>
</head>
<body>

<div id="chart-container">
  <svg id="chart" width="1280" height="720"></svg>
</div>
<div id="subtitle"></div>
<div id="progress-bar"><div id="progress-fill"></div></div>
<div id="controls">
  <button id="playBtn">▶ Play</button>
  <button id="pauseBtn">⏸ Pause</button>
  <span id="timeDisplay" style="font-size:14px;color:#aaa;">0.0 / 0.0 s</span>
</div>

<audio id="tts" src="audio/tts.wav"></audio>

<script>
// ── DATA ──────────────────────────────────────────────────────────────
const BARS = [
  { label: "Less than $20,000",  value: 890,  color: "#4A96D6" },
  { label: "$40,000",            value: 946,  color: "#4A96D6" },
  { label: "$60,000",            value: 994,  color: "#4A96D6" },
  { label: "$80,000",            value: 1006, color: "#4A96D6" },
  { label: "$100,000",           value: 1054, color: "#4A96D6" },
  { label: "$140,000",           value: 1103, color: "#4A96D6" },
  { label: "More than $200,000", value: 1150, color: "#4A96D6" }
];

const SENTENCES = [
  { start: 0.0,    end: 8.583,  text: "Starting at the lowest income bracket, families earning less than $20,000 see an average SAT score of 890." },
  { start: 8.883,  end: 15.691, text: "As household earnings rise to $40,000, that average climbs to 946." },
  { start: 15.991, end: 22.105, text: "Crossing into the $60,000 range, scores reach 994." },
  { start: 22.405, end: 29.453, text: "At $80,000, the average breaks past the thousand mark, landing at 1006." },
  { start: 29.753, end: 36.626, text: "For households making $100,000, the typical score jumps to 1054." },
  { start: 36.926, end: 45.644, text: "Moving further up the economic ladder, families at $140,000 report an average of 1103." },
  { start: 45.944, end: 54.402, text: "Finally, students from households earning more than $200,000 achieve the top average of 1150." },
  { start: 54.702, end: 61.905, text: "This unbroken upward trajectory reveals a clear positive relationship between family income and SAT performance." },
  { start: 62.205, end: 69.552, text: "The data ultimately confirms that students from wealthier families consistently secure higher standardized test scores." }
];

// ── PLAN ──────────────────────────────────────────────────────────────
const PLAN = [
  { sentence: 0, window: [0.0, 8.583],   shows: "Title + axis labels + Bar 0 animating in (value 890)", change: [0.0, 8.583] },
  { sentence: 1, window: [8.883, 15.691], shows: "Bar 0 fixed + Bar 1 animating in (value 946)", change: [8.883, 15.691] },
  { sentence: 2, window: [15.991, 22.105],shows: "Bars 0-1 fixed + Bar 2 animating in (value 994)", change: [15.991, 22.105] },
  { sentence: 3, window: [22.405, 29.453],shows: "Bars 0-2 fixed + Bar 3 animating in (value 1006)", change: [22.405, 29.453] },
  { sentence: 4, window: [29.753, 36.626],shows: "Bars 0-3 fixed + Bar 4 animating in (value 1054)", change: [29.753, 36.626] },
  { sentence: 5, window: [36.926, 45.644],shows: "Bars 0-4 fixed + Bar 5 animating in (value 1103)", change: [36.926, 45.644] },
  { sentence: 6, window: [45.944, 54.402],shows: "Bars 0-5 fixed + Bar 6 animating in (value 1150)", change: [45.944, 54.402] },
  { sentence: 7, window: [54.702, 61.905],shows: "All 7 bars visible + upward arrow annotation + highlight glow", change: [54.702, 61.905] },
  { sentence: 8, window: [62.205, 69.552],shows: "All 7 bars visible + conclusion text fade-in", change: [62.205, 69.552] }
];
window.__PLAN__ = PLAN;

// ── CHART GEOMETRY ────────────────────────────────────────────────────
const SVG_W = 1280, SVG_H = 720;
const MARGIN = { top: 80, bottom: 80, left: 260, right: 160 };
const CHART_W = SVG_W - MARGIN.left - MARGIN.right;
const CHART_H = SVG_H - MARGIN.top - MARGIN.bottom;
const BAR_COUNT = BARS.length;
const BAR_HEIGHT = Math.min(52, (CHART_H - (BAR_COUNT - 1) * 12) / BAR_COUNT);
const BAR_GAP = 12;
const MAX_VAL = 1150;
const MIN_VAL = 850;
const VAL_RANGE = MAX_VAL - MIN_VAL;
const SCALE = CHART_W / VAL_RANGE; // pixels per SAT point

function valToX(v) { return MARGIN.left + (v - MIN_VAL) * SCALE; }
function barY(i) { return MARGIN.top + i * (BAR_HEIGHT + BAR_GAP); }

// ── SVG HELPERS ───────────────────────────────────────────────────────
const NS = "http://www.w3.org/2000/svg";
function svgEl(tag, attrs) {
  const el = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs || {})) el.setAttribute(k, v);
  return el;
}

// ── BUILD STATIC SVG STRUCTURE ────────────────────────────────────────
const svg = document.getElementById("chart");

// Title
const title = svgEl("text", { x: SVG_W / 2, y: 42, "text-anchor": "middle", fill: "#ffffff", "font-size": "28", "font-weight": "bold", "font-family": "'Segoe UI', Arial, sans-serif" });
title.textContent = "Average SAT Score by Family Income Level";
svg.appendChild(title);

// Subtitle
const subtitleText = svgEl("text", { x: SVG_W / 2, y: 68, "text-anchor": "middle", fill: "#8899aa", "font-size": "15", "font-family": "'Segoe UI', Arial, sans-serif" });
subtitleText.textContent = "Source: Printed Data — Relationship Between Household Earnings and Standardized Test Performance";
svg.appendChild(subtitleText);

// Axis line (baseline)
const baseline = svgEl("line", { x1: MARGIN.left, y1: MARGIN.top + BAR_COUNT * (BAR_HEIGHT + BAR_GAP) - BAR_GAP + 4, x2: SVG_W - MARGIN.right, y2: MARGIN.top + BAR_COUNT * (BAR_HEIGHT + BAR_GAP) - BAR_GAP + 4, stroke: "#334466", "stroke-width": 1.5 });
svg.appendChild(baseline);

// Y-axis labels (income brackets)
const yLabels = [];
for (let i = 0; i < BAR_COUNT; i++) {
  const g = svgEl("g", {});
  const txt = svgEl("text", { x: MARGIN.left - 14, y: barY(i) + BAR_HEIGHT / 2 + 5, "text-anchor": "end", fill: "#c0d0e0", "font-size": "14", "font-family": "'Segoe UI', Arial, sans-serif" });
  txt.textContent = BARS[i].label;
  g.appendChild(txt);
  yLabels.push(g);
  svg.appendChild(g);
}

// X-axis tick marks and labels
const xTicks = [890, 950, 1000, 1050, 1100, 1150];
const xAxisGroup = svgEl("g", {});
for (const tv of xTicks) {
  const tx = valToX(tv);
  if (tx >= MARGIN.left && tx <= SVG_W - MARGIN.right) {
    const tick = svgEl("line", { x1: tx, y1: MARGIN.top + BAR_COUNT * (BAR_HEIGHT + BAR_GAP) - BAR_GAP + 4, x2: tx, y2: MARGIN.top + BAR_COUNT * (BAR_HEIGHT + BAR_GAP) - BAR_GAP + 10, stroke: "#334466", "stroke-width": 1 });
    xAxisGroup.appendChild(tick);
    const lbl = svgEl("text", { x: tx, y: MARGIN.top + BAR_COUNT * (BAR_HEIGHT + BAR_GAP) - BAR_GAP + 26, "text-anchor": "middle", fill: "#8899aa", "font-size": "12", "font-family": "'Segoe UI', Arial, sans-serif" });
    lbl.textContent = tv;
    xAxisGroup.appendChild(lbl);
  }
}
svg.appendChild(xAxisGroup);

// X-axis unit label
const xUnit = svgEl("text", { x: SVG_W / 2, y: SVG_H - 20, "text-anchor": "middle", fill: "#667788", "font-size": "13", "font-family": "'Segoe UI', Arial, sans-serif" });
xUnit.textContent = "Average SAT Score";
svg.appendChild(xUnit);

// Value labels group (populated dynamically)
const valueLabelsGroup = svgEl("g", { id: "value-labels" });
svg.appendChild(valueLabelsGroup);

// Annotation groups (hidden initially)
const arrowGroup = svgEl("g", { id: "arrow-group", opacity: "0" });
svg.appendChild(arrowGroup);
const conclusionGroup = svgEl("g", { id: "conclusion-group", opacity: "0" });
svg.appendChild(conclusionGroup);

// Build arrow annotation
const arrowPath = svgEl("path", { d: `M ${valToX(890)} ${barY(0) + BAR_HEIGHT/2} Q ${(valToX(890)+valToX(1150))/2} ${barY(0)-30} ${valToX(1150)} ${barY(6)+BAR_HEIGHT/2}`, fill: "none", stroke: "#ff6b6b", "stroke-width": 2.5, "stroke-dasharray": "8,4", "marker-end": "url(#arrowhead)" });
const defs = svgEl("defs", {});
const marker = svgEl("marker", { id: "arrowhead", markerWidth: "10", markerHeight: "7", refX: "9", refY: "3.5", orient: "auto" });
const poly = svgEl("polygon", { points: "0 0, 10 3.5, 0 7", fill: "#ff6b6b" });
marker.appendChild(poly);
defs.appendChild(marker);
svg.insertBefore(defs, svg.firstChild);
arrowGroup.appendChild(arrowPath);
const arrowLabel = svgEl("text", { x: (valToX(890)+valToX(1150))/2, y: barY(0) - 40, "text-anchor": "middle", fill: "#ff6b6b", "font-size": "16", "font-weight": "bold", "font-family": "'Segoe UI', Arial, sans-serif" });
arrowLabel.textContent = "↑ Positive Correlation";
arrowGroup.appendChild(arrowLabel);

// Build conclusion text
const conclText = svgEl("text", { x: SVG_W / 2, y: SVG_H - 40, "text-anchor": "middle", fill: "#4A96D6", "font-size": "18", "font-weight": "bold", "font-family": "'Segoe UI', Arial, sans-serif" });
conclText.textContent = "Students from wealthier families consistently secure higher standardized test scores.";
conclusionGroup.appendChild(conclText);

// ── BAR ELEMENTS ──────────────────────────────────────────────────────
const barRects = [];
const barGlowRects = [];
for (let i = 0; i < BAR_COUNT; i++) {
  // Glow behind bar
  const glow = svgEl("rect", {
    x: valToX(MIN_VAL), y: barY(i), width: 0, height: BAR_HEIGHT,
    rx: 4, ry: 4, fill: BARS[i].color, opacity: "0.25"
  });
  svg.appendChild(glow);
  barGlowRects.push(glow);

  // Main bar
  const rect = svgEl("rect", {
    x: valToX(MIN_VAL), y: barY(i), width: 0, height: BAR_HEIGHT,
    rx: 4, ry: 4, fill: BARS[i].color
  });
  svg.appendChild(rect);
  barRects.push(rect);

  // Value label
  const vlbl = svgEl("text", {
    x: valToX(MIN_VAL), y: barY(i) + BAR_HEIGHT / 2 + 5,
    "text-anchor": "start", fill: "#ffffff", "font-size": "15", "font-weight": "bold",
    "font-family": "'Segoe UI', Arial, sans-serif", opacity: "0"
  });
  vlbl.textContent = BARS[i].value.toString();
  valueLabelsGroup.appendChild(vlbl);
}

// ── RENDER AT TIME T ──────────────────────────────────────────────────
function easeOutCubic(t) { return 1 - Math.pow(1 - t, 3); }

function renderAt(t) {
  const duration = getDuration();
  const clampedT = Math.max(0, Math.min(t, duration));

  // Determine which bars should be visible
  for (let i = 0; i < BAR_COUNT; i++) {
    const barStart = PLAN[i] ? PLAN[i].change[0] : i * 8;
    const barEnd = PLAN[i] ? PLAN[i].change[1] : i * 8 + 7;
    let progress = 0;
    if (clampedT >= barEnd) {
      progress = 1;
    } else if (clampedT >= barStart) {
      progress = easeOutCubic((clampedT - barStart) / (barEnd - barStart));
    }

    const targetW = (BARS[i].value - MIN_VAL) * SCALE;
    const currentW = targetW * progress;

    barRects[i].setAttribute("width", Math.max(0, currentW));
    barGlowRects[i].setAttribute("width", Math.max(0, currentW));

    // Value label
    const vlbl = valueLabelsGroup.children[i];
    if (progress > 0.3) {
      vlbl.setAttribute("opacity", Math.min(1, (progress - 0.3) / 0.3));
      vlbl.setAttribute("x", valToX(MIN_VAL) + currentW + 8);
    } else {
      vlbl.setAttribute("opacity", "0");
    }
  }

  // Arrow annotation (sentence 7)
  const arrowVisible = clampedT >= PLAN[7].change[0];
  if (arrowVisible) {
    const arrowProgress = Math.min(1, (clampedT - PLAN[7].change[0]) / (PLAN[7].change[1] - PLAN[7].change[0]));
    arrowGroup.setAttribute("opacity", String(easeOutCubic(arrowProgress)));
  } else {
    arrowGroup.setAttribute("opacity", "0");
  }

  // Conclusion text (sentence 8)
  const conclVisible = clampedT >= PLAN[8].change[0];
  if (conclVisible) {
    const conclProgress = Math.min(1, (clampedT - PLAN[8].change[0]) / (PLAN[8].change[1] - PLAN[8].change[0]));
    conclusionGroup.setAttribute("opacity", String(easeOutCubic(conclProgress)));
  } else {
    conclusionGroup.setAttribute("opacity", "0");
  }

  // Subtitle sync
  updateSubtitle(clampedT);

  // Progress bar
  const pct = duration > 0 ? (clampedT / duration) * 100 : 0;
  document.getElementById("progress-fill").style.width = pct + "%";
  document.getElementById("timeDisplay").textContent = clampedT.toFixed(1) + " / " + duration.toFixed(1) + " s";
}

// ── SUBTITLE SYNC ─────────────────────────────────────────────────────
function updateSubtitle(t) {
  const el = document.getElementById("subtitle");
  let found = null;
  for (const s of SENTENCES) {
    if (t >= s.start && t <= s.end) { found = s; break; }
  }
  if (found) {
    el.textContent = found.text;
    el.style.opacity = "1";
  } else {
    el.textContent = "";
    el.style.opacity = "0";
  }
}

// ── DURATION ──────────────────────────────────────────────────────────
function getDuration() {
  if (window.__BENCHMARK__ && window.__BENCHMARK__.duration) {
    return window.__BENCHMARK__.duration;
  }
  // Fallback: last sentence end
  return SENTENCES[SENTENCES.length - 1].end;
}

// ── PLAYBACK ENGINE ───────────────────────────────────────────────────
let playing = false;
let rafId = null;
let startTime = 0;
let pausedAt = 0;

const audio = document.getElementById("tts");

function play() {
  if (playing) return;
  playing = true;
  document.getElementById("playBtn").disabled = true;
  document.getElementById("pauseBtn").disabled = false;

  audio.currentTime = pausedAt;
  audio.play().catch(() => {});

  startTime = performance.now() / 1000 - pausedAt;
  tick();
}

function pause() {
  if (!playing) return;
  playing = false;
  pausedAt = performance.now() / 1000 - startTime;
  audio.pause();
  if (rafId) cancelAnimationFrame(rafId);
  rafId = null;
  document.getElementById("playBtn").disabled = false;
  document.getElementById("pauseBtn").disabled = true;
  renderAt(pausedAt);
}

function tick() {
  if (!playing) return;
  const now = performance.now() / 1000;
  const t = now - startTime;
  const dur = getDuration();

  if (t >= dur) {
    pause();
    renderAt(dur);
    return;
  }

  renderAt(t);
  rafId = requestAnimationFrame(tick);
}

document.getElementById("playBtn").addEventListener("click", play);
document.getElementById("pauseBtn").addEventListener("click", pause);

// ── INIT ──────────────────────────────────────────────────────────────
(function init() {
  // Check URL param for time-addressable rendering
  const params = new URLSearchParams(location.search);
  const tParam = params.get("t");
  if (tParam !== null) {
    renderAt(parseFloat(tParam));
  } else {
    renderAt(0);
  }
})();

// Expose renderAt globally
window.renderAt = renderAt;
</script>

</body>
</html>
````
