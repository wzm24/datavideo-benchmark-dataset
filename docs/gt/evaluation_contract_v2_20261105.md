# 数据视频基准评测契约 v2

日期：2026-11-05  
适用范围：V1–V4 data-video generation 实验  
状态：本轮实验的有效契约。与旧版协议冲突处，以本文件为准；旧版保留为历史设计记录。

## 1. 任务定义

模型根据公开输入生成：

1. 目标时间段的 narration；
2. 可执行的 HTML/SVG 动画；
3. 最终可播放视频。

评测对象是最终运行结果，不是模型声称的计划、metadata 或代码注释。

公开任务只允许使用输入中给出的数据。除 `table` 明确提供的事实外，不得把原视频 narration、原视频字幕或外部知识当成事实真值。

## 2. 输入契约

四档共同包含：

- `intent`
- `data_table`
- `input_spec`

两档额外包含目标片段前后的源视频 narration context；该 context 中，目标时间段的原文必须完全遮住。

| 输入 | intent + table + spec | narrative context（目标遮罩） | reference SVG |
|---|---:|---:|---:|
| V1 | ✓ |  |  |
| V2 | ✓ | ✓ |  |
| V3 | ✓ |  | ✓ |
| V4 | ✓ | ✓ | ✓ |

### 2.1 Context 定义

上下文必须来自**同一个源视频**，而不是按 clip 名猜测的来源。

每个 clip 的 context 记录：

- `video_id`
- `source_url`
- `target_window`（源视频绝对时间）
- `target_cue_ids`（被遮罩的 transcript 单元）
- `context_before`
- `context_after`
- `verification`（目标窗口与现有 narration 的时间/文本核对）

目标遮罩规则：

1. 按完整句子/cue 边界遮罩；
2. 与目标窗口重叠的句段不得部分保留；
3. 目标遮罩向两侧最多扩 1.5 秒，防止边界泄露；
4. context 中可以出现与目标事实相关的背景，但不得直接提供目标句的完整文本。

全量 context 用于 `context_full` 实验臂；`context20` 实验臂从 153 条 bar clip 中按固定种子随机抽取 20 条，被抽中的每条仍使用完整且目标遮罩后的 context。两个臂均使用相同 target 遮罩。

源视频完整转写统一使用同一个 ASR 模型、版本、语言和 VAD 配置。不得把 YouTube 字幕、不同 Whisper 模型或其他转写来源混入同一实验结果。源视频公开且可能出现在模型训练语料中，因此上下文污染作为已知混杂因素报告，但目标时间段的转写必须遮罩。

## 3. GT 分层

| 层 | 内容 |
|---|---|
| G0 | 数据事实、单位、口径、允许推断、禁止推断 |
| G1 | 相对 intent 的必需语义单元；四档共同使用 intent + table 派生 |
| G2 | 每个 G1 unit 所需的可观察视觉证据 |
| G3 | 视觉证据与生成 narration 的时间关系 |
| G4 | 实际生成结果的人工验证、叙事质量和呈现质量评分 |
| S | 仅 V3/V4：对参考 SVG 的结构、编码和风格遵守度 |

G1 不从目标原 narration 派生。原 narration 仅用于：

- 构造 narrative context；
- 作为评测参考路径；
- 辅助发现目标窗口边界。

原 narration 不是叙事金标准，也不能覆盖 table 的事实约束。

## 4. 信

### 4.1 Claim 标签

分别抽取并去重：

- narration factual claims；
- visual factual assertions。

每个 claim 标为：

- `supported`
- `contradicted`
- `unsupported`
- `unresolved`

### 4.2 推断规则

允许：

- 同一实体、同一单位、同一口径内的加减、差值、比例；
- 明确整体时的补集；
- 轴/刻度可读时的估读，误差不超过声明容差；
- 明确标为约数、near、over、under 的近似表达。

不允许：

- 把多个分组统计量重新平均成总体平均；
- 从相关关系外推因果；
- 编造未提供的外部基准；
- 跨实体、跨时间或跨口径无依据推断；
- 为视觉效果改变数值、比例或坐标编码。

### 4.3 错误分级

| 等级 | 定义 | 处理 |
|---|---|---|
| Critical | 改变 intent 核心结论、实体、方向、数量级或关键数据；图表编码明显歪曲事实 | `Faithfulness=0` |
| Major | 新增未被输入支持的非核心事实、口径或因果 | 计入 unsupported/contradicted |
| Minor | 在公开容差内的舍入、估读、措辞近似 | 不扣事实通过，记录误差 |

### 4.4 Faithfulness

```text
NarrationFactuality = supported narration claims / all adjudicated narration claims
VisualFactuality = supported visual assertions / all adjudicated visual assertions
```

```text
if CriticalError:
    Faithfulness = 0
else:
    Faithfulness = harmonic_mean(NarrationFactuality, VisualFactuality)
```

`unresolved` 同时报告下界和上界，不直接删除样本。

## 5. 达

### 5.1 G1

沿用协议 §2.4：

- 一个 intent 槽对应一个 unit；
- unit 必须可由 table 判定；
- 删除该 unit 后 intent 无法完成，才进入 required；
- 同一槽的端点、差值、比值和排序视为同一条 unit 的不同 accepted routes。

### 5.2 G2

每个 unit 声明：

- 必需 marks；
- 实体和 series identity；
- 轴、图例和标签条件；
- 可接受证据路线；
- reject 条件。

### 5.3 G3

对每个 required visual unit：

- anchor 为实际完成的 narration sentence；
- 默认检查窗口：句末前 1.0 秒到后 1.5 秒；
- dwell 最小值是草稿，待 G4 校准；
- 比较和变化类必须看到完成状态，不能用半程动画代替。

### 5.4 完成度

```text
ContentCompletion = Σ(w_u × C_u) / Σw_u
VisualCompletion = Σ(w_u × V_u) / Σw_u
Adequacy = JointCompletion
         = Σ(w_u × C_u × V_u × T_u) / Σw_u
```

首版 unit 等权。渲染失败时 `Adequacy=0`。

## 6. 雅

`雅` 只有两个一级维度：

```text
Elegance = mean(NarrativeQuality, PresentationQuality)
```

### 6.1 NarrativeQuality

各主观项采用 1–5 分，并转换到 `[0,1]`：

```text
normalized(s) = (s - 1) / 4
```

| 维度 | 核心问题 |
|---|---|
| Framing | 观众是否知道问题、对象、范围和这一段为什么存在 |
| Information selection | 是否选取服务 intent 的关键事实，避免过度复述 |
| Insight | 是否形成有数据支持的比较、趋势、异常、阈值或结论 |
| Coherence / context | 句子和视觉状态是否连贯；V2/V4 是否合理承接前后文而非照抄 |
| Closure / handoff | 是否完成 intent 或为下一段留下自然入口 |
| Narration comprehension | 仅看生成 audio 或 transcript，回答预先冻结的问题 |

```text
NarrativeQuality = mean(
  Framing,
  InformationSelection,
  Insight,
  CoherenceContext,
  ClosureHandoff,
  NarrationComprehension
)
```

### 6.2 PresentationQuality

| 维度 | 核心问题 |
|---|---|
| Visual readability | 轴、图例、标签和 panel 是否清晰可读 |
| Animation effectiveness | 动画是否帮助理解变化、比较、顺序和重点 |
| Transition coherence | 场景转换是否保留对象身份、比较基准和叙事关系 |
| Pacing | 出现、停留和切换是否有足够阅读时间 |
| Aesthetic coherence | 色彩、字体、构图、层级和装饰是否统一 |
| Visual comprehension | 只看 muted video，回答预先冻结的图表问题 |

```text
PresentationQuality = mean(
  VisualReadability,
  AnimationEffectiveness,
  TransitionCoherence,
  Pacing,
  AestheticCoherence,
  VisualComprehension
)
```

Full-video comprehension 单独记录，用于诊断两种模态的结合效果。

### 6.3 Comprehension QA

每个 bar clip 至少生成三条四选一问题：

1. `main_takeaway`：视频想传达的主要判断；
2. `relation`：比较、趋势、排序、变化或占比；
3. `evidence_check`：哪项说法被数据支持/不受支持。

约束：

- 问题在模型输出前冻结；
- 不直接复制参考 narration；
- 每题只有一个正确答案；
- 干扰项必须合理，但不能与正确答案同时成立；
- 答案可由 table + G1 唯一确定；
- 保存所绑定的 `unit_ids` 和证据；
- 由独立于生成器的裁判模型在 `reasoning=enabled` 下出题并记录 usage；
- 在冻结题库前对选项使用固定种子随机化，报告正确答案位置分布，避免位置偏差；
- 四选一正确率进行 chance correction：

```text
Comprehension = max(0, (accuracy - 0.25) / 0.75)
```

## 7. V3/V4 的 SVG 约束 S

单独报告，不混入 `Elegance`：

```text
StructureAdherence ∈ {0, 1}
StyleSimilarity ∈ [0, 1]
```

硬结构包括：

- chart type / subtype；
- panel 和 series 数量；
- 实体、标签、图例；
- 轴方向与可见尺度；
- 必需 mark 是否存在。

软风格包括：

- 颜色角色映射；
- 字体层级；
- 间距、布局和装饰密度；
- 视觉层级与整体一致性。

`StructureAdherence=0` 时标记 contract failure，保留质量诊断分，但不进入正式排名。

## 8. 总分

```text
Overall = 100 × mean(Faithfulness, Adequacy, Elegance)
```

`Overall` 仅用于直观展示。主表必须同时报告：

- Faithfulness
- Adequacy
- Elegance
- NarrativeQuality
- PresentationQuality
- critical errors
- unresolved count
- RenderSuccess
- duration compliance
- StyleAdherence（V3/V4）

## 9. 评分者

- 生成模型不得给自己评分。
- Program 评测：运行、时长、音频、SVG 结构、G2/G3 和可读性几何。
- 独立 VLM/LLM 裁判：NarrativeQuality、PresentationQuality 和理解题。
- 人工评审：建立 20–30 条校准集，校准模型裁判，并裁决分差 ≥1 的样本。
- 所有候选使用相同裁判模型、版本、提示、reasoning 配置和预算。
- 叙事评分优先采用 blind pairwise；绝对 1–5 分只作为分解报告。

## 10. 本轮实验阶段

1. 统一上下文来源和 ASR。
2. 为全部 bar clip 生成 Ya comprehension questions。
3. 使用 V4 契约，以 Qwen3.8 Flash 在关闭 reasoning 下运行：
   - `context_full`：全部 153 条 bar clip，每条使用完整源视频 context；
   - `context20`：固定种子随机 20 条 bar clip，每条仍使用完整源视频 context。
4. 生成模型做一次 fresh narration call 和一次 fresh HTML call。
5. 使用独立 DeepSeek 视觉裁判开启 reasoning，对全部有效结果评分。
6. unresolved 和基础设施失败单独保留，不静默转为零分。
