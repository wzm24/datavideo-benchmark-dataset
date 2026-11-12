# 论文用记忆文件：GT 设计与数据表验证

更新：2026-09-28

> 阶段性总结（2026-09-28，可直接给学长看）：`benchmark_draft/WEEKLY_SUMMARY_2026-09-28.md`

## 1. 我们的任务与输入契约（B1–B5）

| 档 | 输入 | 模型负责 | 用途 |
|---|---|---|---|
| B1 | table | 选题+旁白+视觉设计+动画 | 最难，开放发现子集 |
| **B2** | **table + intent** | 旁白+视觉设计+动画 | **主榜**（协议默认） |
| B3 | + narration 文本（不给时间戳） | 视觉设计+动画 | 隔离动画能力，须分榜 |
| B4 | + narration + 视觉设计 | 仅动画与同步 | 测"把静态图动画化" |
| B5 | 只有图 | 反推数据+旁白+动画 | 理解+生成复合任务 |

原则：**输入只含"条件"，不含"表达"**。条件 = 表/schema/intent/受众/时长预算/（可选）脱敏风格参考；表达 = 几何、图表类型与朝向、轴与刻度、标签图例、配色字体、时序。

**Chart spec 边界（2026-10-27）：** 完整 `chart_spec.json` 只用于内部 GT、G2/G3 和审计；
模型只能读取 `input_spec.json`。模型可见 spec 仅包含 `family`、`sub_type`、`orientation`
以及必要时的 `time_behavior=frame`，不暴露 `series_count`、`category_count`、`slice_count`、
`panel_count`、`row_count` 或 `marks_per_frame`。柱数、折线数、扇区数和面板内结构由模型
根据数据表与 intent 自行推断。

**Intent 分层（2026-10-27）：** 按协议 §1.1 与 §4.2，intent 是“希望回答的问题与传播目标”，
必须明确范围且不泄露计算答案。当前已人工/半人工修订的 `intent_en` 包含结论，适合作为
内部 `narrative_goal`；不能直接视为最终 public intent。最终 public intent 应由 narrative
goal 和现有 requirements 改写为中性问题句，再去掉答案。G1 中保存的是答案和接受条件；
只要中性 intent 保留相同槽位，G1 的命题与答案可以继续使用，但必须检查 intent-G1 映射。
旧 `previous_intent` 仅作历史候选，不能直接进入模型。

**Intent 候选审计（2026-10-27）：** 已从 153 条 bar 的 narrative goal 生成中性
public intent 候选，写入 `benchmark_draft/bar_intent/public_intent_v1/`，尚未覆盖正式
`intent_en`。候选生成只读取 narrative goal、data table 和 G1 的问题/scope，不读取
G1 答案。153/153 通过单句、长度、无答案泄露、scope 与 G1 requirement 覆盖检查；
独立盲解析往返检查为 127 closed、26 需复核。26 条中一部分是 intent 仍需收紧，
另一部分是原 narrative goal/G1 依赖表外信息或数据冲突，不能通过改 intent 掩盖。

**V1 闭合性复审（2026-10-27）：** `bar_1` 的完整三档排序因 CAR 只有定性标签
`a lot of time`，在 V1 中降为 `optional_valid`；`bar_22` 的财富税政策结论 U4、
`bar_51` 的 payroll-tax cap 因果解释 U3、`bar_66` 的 supporters/reinvestment 预测
U3 也因表中无依据而降为 optional。`bar_38` 去掉主观 `small` 判断，只要求比较
3.6B 人口和 0.4B reduction 的数量关系；`bar_54` 在 intent 中明确比较
income-tax-only 与五税合并后的总负担。上述 5 条更新后的 public intent 均通过
无泄露检查、requirement 覆盖和 blind round-trip。

## 2. GT 五层结构

| 层 | 内容 | 产出方 |
|---|---|---|
| G0 答案键 | facts：expr / expected / unit / basis(printed\|estimated\|computed) / model_tolerance / dataset_uncertainty + claim catalog | 程序自动 |
| G1 必需单元 | unit_kind / weight（类型模板 ±0.1）/ meaning / must_be_visualized / accepted_routes / derived_from_intent / visual_evidence_rule / temporal_policy_id | agent 起草 + 人定稿；**按输入契约分开建**（`g1_draft_b2.json` = B2） |
| G2 视觉证据 | 每个单元"要看到什么"的可判定条件（图元数量/类型/比例/标签/轴），多路径可接受 | 同上 |
| G3 时间政策 | 锚在**模型自己的旁白**句上的出现窗口与容差 | 同上 |
| G4 人工验证集 | 分层抽样的输出标注 + 裁决，用于校准 judge | 人（后建） |

自检四条：G1 每条可追溯到 intent 的某个槽（协议 §2.4）；每条有 G0 事实支撑；G2 可被程序/VLM 判定；G1 条数 = 槽数（不设配额，V1 实测 1–4）且权重和 = 1。

## 3. 容差政策（两类，不混）

| 容差 | 含义 | 大小 | 是否扣模型分 |
|---|---|---|---|
| `model_tolerance` | 判"是否与给定表一致"，只吸收测量误差（DOM ±1px / 像素 ±2px / 显示取整） | bar_27 ≈ ±3（DOM）/±5（像素） | ✅ |
| `dataset_uncertainty` | 判"我们的 GT 与原视频是否一致"，含估读误差 | printed ±0；estimated ±15 | ❌ 只进数据质量报告 |

## 4. 三篇对照论文的评测方式

| | Text2Vis (2507.19969) | DataNarrative (2408.05346) | DataReel (2604.25220) |
|---|---|---|---|
| 任务 | 表+问题 → 答案文本+可视化代码 | 表 → 数据故事（大纲+叙述+图表） | 表+intent+时长+风格参考图 → HTML/D3+字幕 |
| 逐条答案键 | ✅ gold answer + gold code + annotated chart | ❌（黄金参考故事） | 部分：数据表是事实真值，表达无答案键 |
| 输入 | 表+查询 | 表（用户意图=原标题） | 表+intent+时长+**本图截图作风格参考** |
| 评测手法 | 4 分量：Code Exec Success / Answer Match / Visual Clarity / Readability / Chart Correctness → Final Pass Rate；236 条人工验证（差异 <15%）；$2 / 1985 条；McNemar 检验 | LLM-judge pairwise（5 标准）+ 人工 1–5（100 条、2 标注者） | HTML 层 LLM judge（0–5 四标准）+ 视频 pairwise（人类 111/150、108/150；VLM 138/150；κ=0.58） |
| 局限 | pass rate 是全条件与（粗）；可读性/图表正确性是整体分；无时序 | 只有相对胜负 | 自认抓不到动画问题；字幕代替旁白；给本图截图=泄漏 |

**我们保留的差异**：逐单元视觉证据（G2）｜时间政策 + SyncOffset（G3）｜程序化几何核验 + 两类容差｜事实 precision（含额外断言）｜输入责任分层 B1–B5｜340 条人工精修的中间态数据（关键帧 + structure-aware SVG + 表 + narration + intent）。

## 5. 数据表验证现状（2026-09-23 实测）

**表的来源分层（`table_provenance.csv`）**：54 条来自生成脚本自带的 `table()`（与图同源，最高可信）；其余从 SVG 反推；2 条（bar_85/128）手工补写。

**schema 统一**：`clip_id, entity, entity_id, x_px, x_value, value, relative_value, unit, color, source_type`（340/340）；空表与非法行 0。

**程序检查 ①（内部一致性，`table_internal_check.csv`）**：39 张表报异常，类型为
- `relative_out_of_range`（5 张，如 bar_124/125/89/93/96 —— 相对值 >1，需按"同系列最大"重新归一或改口径）
- `mixed_units`（少数，如 line_51 同时出现 B/M/k）
- `share_sum ≠ 100`（donut_13/14/15/17 等 —— **多为"部分圆环只标已知部分"的正常情形**，不是错误）

**程序检查 ②（旁白数字 vs 表值，`narration_crosscheck.csv`）**：69/377 命中（18.3%）。**该数字目前不能作为表准确率**，原因：旁白里的年份/序数/泛指数量不在表里；70 张 relative_only 表没有绝对值可对；需要过滤后再统计（下一步修正）。

**几何回放（③）**：尝试 5 版（序号比对 → x 排序 → 轴标定 → 家族分流 → 按 entity 分组）**均未得到可信结论**。根因：SVG 里没有声明"元素 ↔ 表行"的对应关系，事后推断不可靠；且 187/279 张 SVG 无 y 轴刻度，无法标定。
**解法**：渲染时在 SVG 元素上写入 `data-row-id` / `data-value`（structure-aware SVG），使"表↔图"成为**可声明、可逐条验证**的关系。

**表忠实度指标（2026-09-23 定稿口径）**

> **Table faithfulness = 在旁白与关键帧中都出现的"数据值类"数字里，能在 data_table 中找到的比例。**

三类数字的判定：
1. **数据值类**（进分子/分母）：贴在柱顶/点/扇区上的印刷数值
2. **图的注释/背景统计**（排除）：带单位词的说明文字，如 donut_24 的 "419 billion kWh"
3. **仅出现在旁白**（排除）：年份（1900–2100）、专有名词里的数字（BOEING 747、COVID-19）、序数
补充规则：区间表达（"5–10%"）任一端点命中即算命中；数值容差 ±2%（上限 ±0.5）；只统计**有绝对值的表**（`relative_only` 表不计入分母）。

**实测结果（最终）：24 / 24 = 100.0%**（涉及 20 条 clip；donut_28 拆分后最后一条也命中）。

未命中的 6 条经逐条裁决，**5 条是口径问题、不是表错**：

| clip | 现象 | 裁决 |
|---|---|---|
| donut_33 / donut_35 / pie_10 | 旁白说 "top 1%"，其中 "1" 被误当数值 | 标签数字（实体名里的 1%）→ 已排除 |
| donut_28 | "5–10%" 区间 与 图例 "$10,000 BONUS" | 区间任一端点命中即可；金额属于图例名 → 已排除 |
| donut_31 | 旁白 "vegans make up 2.5%" 不在该环数据里 | 图的背景统计（非该环数据）→ 判为注释 |
| bar_104 | "400 richest" / 年份 与 25%、18.1% 混在一起 | 标签与年份 → 已排除；表值 25/18.1 均命中 |

剩余未命中：无。

**通用规则（由 donut_28 得出）**：当同一图例既含**金额/数量**又对应**占比**时，表的 `value` 必须明确是哪一个量——应拆成两行（金额行 `unit=usd`、占比行 `unit=%`），否则旁白里的两个数字都无法正确核验。donut_28 已按此拆分：`$10,000 BONUS = 10000 usd`（flat bonus amount）与 `bonus share = 10 %`（ring share）。

**结构问题待办：多子图（41 条，典型 line_51 三张独立折线图）**
GT 需按子图拆分：每个子图各自一组 G1/G2/G3（自己的必需单元、坐标轴与比例），SVG 在同一画布内保留多组 x/y 轴；`mixed_units` 在多子图情形下是**正常**，应按"每子图独立单位"记录而不是报错。

**已修的真错误**：`area_44` 原本只剩 1 行且值为 0，已用 SVG 上边缘重建为 200 行；`pie_1/3/4`（以及全部 20 张 pie）的 `relative_value` 改为 `value/100`；`bar_124/125/89/93/96` 的相对值按同系列最大值重新归一。

**待补的验证证据（写论文用）**
1. 修正 ②：过滤年份/序数，只在"有绝对值的表"上统计旁白一致率
2. 人工审计 50 张（双标注）：报完全一致率、偏差分布、κ（对齐 DataReel：44/50 完全一致、6 张 1–5% 偏差）
3. 外部权威数据抽样比对 30–50 条（World Bank / BTS / Gallup / JHU 等）
4. 渲染器加 `data-row-id` 后，③可全量自动执行

## 6. 论文写作要点（本节可直接改写）

### 6.1 Runtime 契约（2026-09-27 由 baseline 实测得出）

评测必须能在无人工交互的环境下复现，因此契约要求（三条，缺一条则该提交不可评）：
1. **按时间寻址渲染**：必须实现 `window.renderAt(t)`，对任意 `t ∈ [0, duration]` 画出确定性一帧，
   且在音频暂停时同样有效；页面加载时若 URL 带 `?t=<秒>`，必须直接渲染该帧、不要求点击。
2. **时间轴由 harness 注入**：`window.__BENCHMARK__ = {duration, sentences:[{start,end,text}]}`
   在提交代码之前注入，页面用它作为主时钟；`<audio>` 仅负责播放，不得依赖其元数据。
3. **评测路径无全屏遮挡**：允许播放按钮，但图表在点击前就必须可见，不得用全屏遮罩盖住画面。

实测对照（B2 基线，三条 clip）：

| 版本 | 结果 |
|---|---|
| 契约前 | bar_27 与 area_2 在 headless 下画面恒为空、字幕不更新（进度按"播放开始后 elapsed"计算，且音频元数据不可用） |
| 契约后 | 三条全部 `renderAt✓ / __BENCHMARK__✓ / 无遮挡✓`；**area_2 字幕 4/4、动画检出；donut_1 字幕 4/4、动画检出**；bar_27 仍只有 2/3 字幕、动画未检出（canvas 重绘仍依赖播放状态，作为失败样例保留） |

同批 B2 数字：事实命中 bar_27 3/3、area_2 2/2（donut_1 旁白无数字）；三条音频时长 26.8 / 30.4 / 26.8 s，**均超 15–20 s 时长预算**。


- **Data quality and verification**：分层来源 + 程序检查 + 人工审计 + 外部比对，报分层结果而非单一准确率
- **Scope of the tables**：明确指出无刻度图只保证形状与相对关系（`relative_only`），不隐含绝对值
- **Two tolerances**：测量误差计模型分，数据集不确定不计模型分
- **对照三篇**：Text2Vis（答案键 + pass rate + 人工验证）｜DataNarrative（pairwise + 1–5）｜DataReel（LLM judge + pairwise，且把本图截图当输入）
- **我们的增量**：分层答案键（G0–G4）+ 输入责任分层 + 逐单元证据与时序 + 两类容差 + 340 条精修中间态数据

### 6.2 更正（2026-09-27 晚）：bar_27 "不可评"是 harness 的 bug，不是模型的问题

上一节把 bar_27 记为"动画未检出/不可评"，实测证明是**评测脚本自己破坏了画面**：

- 旧 harness 会点击页面上 id/class 匹配 `/play/` 的元素 → 点到 bar_27 的 `#play-btn` →
  启动它自己的 `requestAnimationFrame` 播放循环 → 循环用"播放开始后的 elapsed"重画，
  把 `?t=` 请求的那一帧覆盖掉。两次截图（t=0.5 与 t=25）于是**字节完全相同**
  （MD5 均为 `ae825322e620`），评测据此判"没动"。
- 直接渲染同一份 entry.html 则完全正常：t=3 时 ink=0.012，t=25 时 ink=0.150（柱子按句子时长生长）。

修正后的 harness 规则（已实现于 `eval_baselines_v2.py`）：**不点播放键**、把音频 `pause()` 后
seek 到 t、反复调用 `window.renderAt(t)` 直到截图；只有页面没有 `renderAt` 时才尝试点开启动遮罩。
同时把可评性拆成硬检查：`has_renderAt` + 同一 t 两次渲染的像素抖动 <0.1%（容忍抗锯齿）。

修正后结果：bar_27 可评且 animated=True（ink 0.011→0.150，字幕 3/3）；三条 clip 全部 `evaluable=True`。
→ 论文里"不可评"必须是**独立的一列**（缺 `renderAt` / 同 t 渲染不确定 / 全屏遮挡），
不能把"两帧像素相同"直接当成"动画缺失"。

### 6.3 事实核验必须同时读旁白与**图内文字**

donut_1 暴露的漏洞：B2 生成的环图上明明写了 `Physical 28% / Digital 72% / Physical 58% / Digital 42%`，
但旧评测只从**旁白**里抽数字，于是记成"无数字"、事实一栏空着——把一次凭空造数判成了通过。

而且 donut_1 的 GT 表是 `illustrative`（physical/digital 两项、无值），源片段旁白只说
"66 % of US music sales were digital"，关键帧上没有印任何数字——**这类"无数值示意图"正是模型最容易
编造数字的地方，也是我们 GT 目前最弱的地方**。后续规则：
1. 事实层的 claim 来源 = 旁白 ∪ 图内文字（SVG `<text>`；canvas 需要 OCR 或契约要求导出 `window.__CHART_DATA__`）；
2. 出现在图上、表里没有、且该单元本应有值的数字 → 记 hallucination，而不是忽略；
3. 表里 `source_type=illustrative` 的单元要么补上源视频给出的值（donut_1 应补 66 %），
   要么在 GT 里显式声明"该单元无数值证据"，避免模型造数无法判分。

### 6.4 TTS 用错语音导致数字读成中文（已修）

`baseline_audio.py` 只 `New-Object SpeechSynthesizer` 而**没有 `SelectVoice`**，
SAPI 于是用系统默认语音 `Microsoft Huihui Desktop (zh-CN)`：英文句子按中文口音读，
数字按中文数字语法读（"20,000" → 两万）。

证据：现存的 `bar_27/audio/s0.wav` 时长 7.662 s，与"不选语音（默认）"和 Huihui 的渲染完全一致；
指定 Zira 或给 Huihui 加 `xml:lang="en-US"` 的 SSML 都是 7.178 s。

修正：`SelectVoice('Microsoft Zira Desktop')` + `SpeakSsml(..., xml:lang="en-US")`
（双保险，以后换机器也不会退回中文数字），已在 `baseline_audio.py` / `retone_audio.py` 落地。
重录后三条总时长：bar_27 26.75→25.63 s、area_2 30.39→25.46 s、donut_1 26.84→21.70 s
（换语音会改变时长，因此**必须重录后把新时间轴重新注入 HTML**；area_2 还把硬编码的
`const SENTENCES` 一起同步，否则字幕会掉到 3/4）。

### 6.5 动画"动态感"可否量化：可以

对渲染结果按 0.5 s 采样、统计"相邻帧有可见变化的帧对比例"与"最长静止段"：

| clip | 运动帧对占比 | 最长静止段 | ink 形态 |
|---|---|---|---|
| bar_27 | 19/53 (36%) | 10.5 s（开头，柱子还没出场） | 逐句连续生长 10.5→16 s |
| area_2 | 6/60 (10%) | 9.0 s | 只在句子边界**跳变**（0.014→0.016→0.010→0.025→0.036），且 t=10 s 有一次内容回退 |

→ "没有动态感"是可测量的：B2 基线里 area_2 的面积是**分步弹出来**的，不是连续绘制。
建议把它作为 G3 时间政策的子维度，但用客观指标而非观感打分：
`motion_coverage`（有变化的帧对比例）、`longest_static_gap`、逐句"该句窗口内是否有变化"、
`monotone`（生长型图不得回退）、`step_ratio`（变化是否集中在单帧）。
DataReel 的 4 个 judge 维度里没有动画维度，这是我们可以主张的差异点。

### 6.6 超框/遮挡怎么进分（2026-09-28 实测）

自动测量：把 `getBBox()` 探针注入页面、渲染末帧、读出每个 `<text>` 在视口里的框
（`layout_audit.py`）。bar_27 实测：7 个 y 轴档位标签全部越出画布左边界，
`More than $200,000`（128 px 宽）约 98 px、`Less than $20,000` 约 73% 落在画布外，
截图左侧 20 px 内只剩 980 个墨点（标签尾巴）。

它对分数的影响分三条路径，**不进事实分，但进视觉分和人评分**：
1. 事实 precision 不受影响——数值来自柱子右侧的数值标注（bar_27 20/20 命中）。
2. **G2 的"实体可辨认"会被打掉**：U1/U2 的证据规则要求"最高/最低收入档的柱可见"，
   而档位名不可读 → V1=V2=0 → VisualCompletion 从 1.00 掉到 0.30（严格读法）。
3. per-type bar rubric 里的 `axis_ticks/labels`（0.15）全扣；
   人评 Visual readability 落进"关键信息不可读"档（1–2 分）。

必须在公开评分细则里给出阈值（例如"标签可见字符 <50%，或无法唯一确定实体即判不可辨认"），
否则就是隐形审美扣分。另外布局检查要能识别**阴影/重影**（bar_27 的 `890`/`890` 同位置重复），
否则会把一个设计当成七处 overlap 重复扣分。

**已接进评测**（`layout_audit.py` 作为模块被 `eval_baselines_v2.py` 调用，末帧测量一次），
每条 clip 新增这些列：

| 列 | 含义 |
|---|---|
| `layout_mode` | `svg` / `canvas` / `unavailable` |
| `layout_flag` | `ok` / `minor`（最严重标签出框 ≥10%）/ `severe`（≥50%）/ `canvas_unmeasured` |
| `layout_texts` | 去重后可见文本数（同字符串同坐标的阴影层已合并） |
| `layout_shadow_dupes` | 被识别为阴影/重复层的数量 |
| `layout_clipped` | 出框文本数（按最严重的一侧计） |
| `layout_worst_label` / `layout_worst_hidden` / `layout_worst_side` | 最严重的那个标签、隐藏比例、出框方向 |
| `layout_overlaps` | 去重后互相重叠的文本对数量 |
| `edge_ink_l/r/t/b` | 四边 24 px 条带内的非背景像素占比（canvas 页的兜底信号；播放器 chrome 能测到时已屏蔽） |

实现要点：几何一律换算回**设计画布坐标**（SVG viewBox，通常 1280×720），因此与 headless
窗口大小无关（`--dump-dom` 实际不遵守 `--window-size`，用屏幕坐标会算错）；
出框判定用 `getBBox` 经 `getScreenCTM` 变换再逆变换回根用户坐标，能正确处理嵌套 `<g transform>`。
`canvas` 页没有文本节点，只能标 `canvas_unmeasured`，要数值级证据只能靠 OCR 或契约要求导出数据。

三条基线实测：bar_27 `severe`（7 个 y 轴档位标签出框，最严重 76% 隐藏在左侧，阴影重影 7 个已去重，
overlap 0，`edge_ink_l=0.070` 与 DOM 判定互相印证）；donut_1 `ok`；area_2 `canvas_unmeasured`。

局限：目前只在**末帧**测量；如果某页只在动画中途出框/重叠，需要改成多时点采样
（每多一个时点约 +10 s/条）。

### 6.9 更正：canvas 页必须按 `ctx.getTransform()` 换算，否则会误报超框

第一版 canvas 探针直接记录 `fillText(text, x, y)` 的原始参数，忽略了页面常用的
`ctx.translate/rotate/scale`。bar_6 的 y 轴标题正是
`ctx.translate(22, …) + ctx.rotate(-Math.PI/2) + fillText("% of trips", 0, 0)`
——真实位置是竖排文字、中心在 x=22（完全在画布内），却被误报成"50% 出框"。

修法：把文字框的四个角用 `ctx.getTransform()` 映射到设备坐标再取包围盒；
同时 canvas 页的画布尺寸改用 `<canvas width/height>` 而不是 SVG 的 viewBox。
修完重测：bar_6 两臂、area_2、line_52、area_46、donut_32 **全部 0 出框**，
只有两种情况是真的出框——qwen 的 bar_27 基线（SVG，7 个标签，最严重 76%）
和 qwen 的 pie_2 加约束臂（SVG，8 个文本，最严重 100%，另有 5 处重叠）。

**教训**：探针自身的坐标换算错误会把"看起来没问题的图"判成 severe，
任何布局类指标上线前都要先拿人眼能确认的样本做一次正负例校验。

### 6.10 一句话布局约束的消融（qwen，k=1，已用修正后的探针重测）

| clip | 原提示词 | +一句布局约束 | 结论 |
|---|---|---|---|
| bar_27 | severe（7 个标签，76%） | ok | 修好 |
| bar_6 | ok | ok | 无变化 |
| line_52 | ok（3 处重叠） | ok（1 处重叠） | 无变化 |
| area_46 | ok（1 处重叠） | ok | 无变化 |
| donut_32 | ok | ok | 无变化 |
| pie_2 | ok | severe（8 个文本，100%） | 变坏 |

修正探针后是 **修好 1 / 弄坏 1 / 无变化 4**。两点结论：
1. B2 生成结果**很少真的出框**（qwen 1/6，DeepSeek 0/6），所以"加一句话"这条实验
   几乎没有可提升空间；要检验它，必须预先筛出真的会出框的 clip（bar_27、pie_2 是种子），
   或者把采样次数提到 k≥3。
2. 重叠（overlap）比出框更常见，值得单独作为呈现质量指标。

### 6.11 DeepSeek 作为第二个 baseline 模型（2026-09-28 实测）

**多模态**：`GET /models` → `deepseek-flash`、`deepseek-v4-pro`。给 `image_url`
时只有 `deepseek-flash` 吃图（`deepseek-v4-pro` 返回 `{"error":"Unsupported image"}`）。
用 bar_27 关键帧实测：标题正确、7 个 y 轴档位标签逐字全对、数值只报图上真正印出来的
890/1150——和 GT 一致。所以它可作为视觉臂的 baseline，而 `deepseek-v4-pro` 只能跑纯文本臂。

**B2 六条（table+intent → 旁白 → HTML）token 与时长**（全部 deepseek-flash）：

| clip | 时长 s | 词数 | 旁白 tok | HTML 输入 | HTML 输出 | 其中 reasoning | 合计 tok | HTML 秒 | 布局 |
|---|---|---|---|---|---|---|---|---|---|
| bar_27 | 35.9 | 50 | 0（复用） | 893 | 20082 | 15388 | 20975 | 72.5 | ok |
| bar_6 | 21.0 | 43 | 0（复用） | 886 | 26919 | 21287 | 27805 | 96.2 | ok |
| line_52 | 42.0 | 70 | 0（复用） | 1424 | 20894 | 15880 | 22318 | 75.7 | ok（3 重叠） |
| area_46 | 16.6 | 35 | 0（复用） | 612 | 24827 | 19474 | 25439 | 92.6 | ok |
| donut_32 | 14.4 | 30 | 848 | 599 | 27305 | 22219 | 28752 | 99.9 | ok（2 重叠） |
| pie_2 | 23.0 | 36 | 699 | 725 | 27121 | 21694 | 28545 | 98.5 | ok |

合计 **153,834 tokens / 6 条 ≈ 25.6k tokens/条**；单页 HTML **20–27k 输出 token，其中
15–22k 是 reasoning**，耗时 72–100 s——**max_tokens 必须 ≥32k**，给 24k 会把页面截断。
另外它会在 `</html>` 之后追加说明文字，后处理要截到最后那个 `</html>`。

**时长**：6 条里 5 条超出 15–20 s（bar_27 35.9 s、line_52 42.0 s），旁白词数 30–70。
DeepSeek 写的旁白明显比 qwen 长（同 clip 25.6 s → 35.9 s），所以时长合规是**模型间的
真实差异**，必须在主表按模型分开报。

**DeepSeek B2 六条的完整评测**（`baseline_ds_b2/baseline_eval_v2.csv`）：

| clip | 时长 s | 可评 | 动画 | 字幕 | 旁白数字命中 | 图内数字命中 | 布局 | 重叠 |
|---|---|---|---|---|---|---|---|---|
| bar_27 | 35.9 | ✓ | ✓ | 4/4 | 7/7 | 10/11（ghost=1200 是刻度） | ok | 0 |
| bar_6 | 21.0 | ✓ | ✓ | 4/4 | 4/4 | 9/9 | ok | 0 |
| line_52 | 42.0 | ✓ | ✓ | 4/4 | 0 | 25/27（ghost=−69%/−33%） | ok | 3 |
| area_46 | 16.6 | ✓ | ✓ | 3/3 | 2/2 | 5/5 | ok | 0 |
| donut_32 | 14.5 | ✓ | ✓ | 3/3 | 0 | 0 | ok | 2 |
| pie_2 | 23.0 | ✓ | ✓ | 3/3 | 5/5 | 10/10 | ok | 0 |

两条要记住的结论：
1. **DeepSeek 六条全部满足 runtime 契约**（renderAt ✓、同 t 确定性 ✓、动画可检出、字幕全同步），
   比 qwen 稳；布局 6/6 无出框。当前最普遍的问题是**时长**（5/6 越界）和**文本重叠**（2 条）。
2. `line_52` 的 ghost `−69% / −33%` 不是编造：它由表内数值算出
   （(2.5−8.0)/8.0 = −68.75%，(0.8−1.2)/1.2 = −33.3%）。说明 **GT 必须支持派生事实**
   （G0 的表达式语言就是干这个的），否则"正确的额外推断"会被误判成 unsupported。
   评估时对"未在表中、但可由表内数据推出且结果正确"的 claim 应记 supported。

### 6.7 bar_27 的真正短板是时序，不是超框

用 `bar27_timing.py` 以 0.05 s 步长扫过整片，记录每根柱子的"数值标注 opacity=1 且柱宽到位"：

| 单元 | 旁白锚点 | 证据完全呈现 | 滞后 | 结论（容差 1.5 s） |
|---|---|---|---|---|
| U2（890） | 0.00 s | 3.60 s | 3.60 s | FAIL |
| U1（1150） | 17.20 s | 21.45 s | 4.25 s | FAIL |
| U3（trend） | 全片 | — | — | PASS |

原因：模型把每根柱子的出场绑在**整句话的中点**（`progress>0.5` 才显示数值），
而不是绑在"旁白念到这个数的时候"。因此 JointCompletion = 0.30（只有 U3 通过）。
这是 B2 基线可复现的弱点，也是"字幕–动画一致性"这一维度的直接证据。

### 6.8 时长预算要给字数，不要给秒数

三条 B2 基线都超 15–20 s：25.63 / 25.46 / 21.70 s。提示词写的是"15-20 seconds"，
但决定时长的是词数：Zira 语速实测 1.7–2.1 词/秒 → 15–20 s 只允许 **28–38 词**，
而三条写了 44–49 词。建议提示词直接给字数预算（≤35 词）或把秒数预算与 TTS 语速绑定，
否则整个 B2 榜都会被时长扣分、掩盖真正的系统差异。
