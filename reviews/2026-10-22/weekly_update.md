# DataVideo Benchmark 周报：2026-10-22

## 一句话结论

本周把 bar 家族从“局部样例 + 旧版 G1”推进到统一的全量评测结构：
153 条 bar 均有 G1/G2/G3，完整性成为固定 R1 下的状态级 U；
同时保留此前 340 条数据视频四件套和 B2 baseline 工作作为基础。

## 上周工作的起点

- 340 条 clip 已形成关键帧、SVG、数据表、narration、intent。
- 输入契约从历史 B1–B5 收敛为四种输入组合。
- 已有 bar/line/area/donut/pie 的模板化渲染经验。
- 已跑过多组 B2 baseline，暴露了 G1 过少、时长失控、字幕只念数据、
  G2 只做完整性无法检查比例、G3 时间窗未定等问题。

## 本周新增

### 1. bar 全量审核与统一格式

- 现有 153 条 bar：100 条 approved，53 条待人工复核。
- G1 共 380 个 U：
  - 366 个 visual U；
  - 14 个 narration-only U；
  - 164 个 R1 完整性 U。
- 每条 bar 的第一要求固定为：
  - R1：这个视频是怎么展现这些 bar 的？
  - 静态图：一个完整性 U；
  - 状态序列图：每个状态各一个完整性 U，R1 使用 all_of。
- `bar_1–34` 已保留人工确认的 claim、accept/reject 和语义，仅补齐当前格式。
- G2 和 G3 已为全部 153 条 bar 自动生成。
- 31 个复杂 G2 单元仍标为 `needs_review=true`，集中在金字塔、大堆叠图、
  多系列趋势和混合单位阈值图。

### 2. 输入契约

- V1：intent + data table。
- V2：intent + data table + narration。
- V3：intent + data table + SVG。
- V4：intent + data table + narration + SVG。

当前主 GT 以 V1 为基准。V2/V4 要额外评价固定 narration 是否被正确视觉化、
字幕与画面是否符合原句时间；V3/V4 要额外评价参考图风格义务，但不能把参考图
当作数据真值。

### 3. G1/G2/G3

- G1：必需语义单元。现在包含 R1 图元呈现要求、主题比较/变化/排序等语义要求。
- G2：每个 U 的可观察视觉证据，定义实体、标记、比例、标签和图形完整性。
- G3：绑定生成旁白的时间政策，检查 availability、ordering、identity、dwell、
  transition。
- 当前 R1 完整性 U 进入 G1 固定分母；G2 检查对应标记是否实际出现。

### 4. bar_22 hardcase baseline

- 模型：`deepseek-flash`。
- 输入：intent、data table、chart spec；运行脚本刻意不读取原 narration、
  keyframe、SVG 或 G1。
- 输出：8 句 narration、58.09 秒音频、HTML 动画、字幕和四个检查帧。
- 当前 GT 四个 U：
  - U1/R1 完整性：六根职业柱全部出现；
  - U2/R2 普通职业比较；
  - U3/R2 ultra-rich 离轴尾部；
  - U4/R3 wealth-tax policy conclusion（narration-only hardcase）。
- 当前评分：ContentCompletion=1.0，VisualCompletion=1.0，
  JointCompletion=1.0。
- 主要质量问题不是事实错误，而是叙事信息密度：3/8 句是纯读表，
  算上图型说明则有 4/8 句低信息量；视频时长远超 15–20 秒目标。

## bar_22 baseline 使用的 prompt

### Narration prompt

```text
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

### HTML prompt

```text
Write ONE self-contained HTML file (no external files except the audio file "audio/tts.wav")
that renders an animated chart (SVG or canvas) at 1280x720 with subtitles.

1. Include <audio id="tts" src="audio/tts.wav"></audio> and #subtitle.
2. Use injected window.__BENCHMARK__ timeline.
3. Implement deterministic window.renderAt(t).
4. Preserve playable audio and visible initial chart.
5. Synchronize subtitles and animation.
6. Declare a PLAN with one entry per sentence.
7. Use only values in the table.

Intent: __INTENT__
Table:
__TABLE__
Narration (index, start, end, text):
__LINES__
```

## 下一步

1. 完成 line、area、donut、pie 的当前格式迁移与 G2/G3 覆盖。
2. 针对 V2/V4 固定 narration，增加“是否视觉化”和“是否按时出现”的派生 GT。
3. 针对 V3/V4 参考 SVG，增加风格义务，但与数据事实、视觉证据分开。
4. 从“信”推进到“达/雅”：
   - 达：读者是否能快速读懂关系、发现重点、形成判断；
   - 雅：构图、节奏、动效、颜色、音画是否服务信息，而非单纯好看。

## VisJudgeBench 阅读后的简短意见

- 它的 Fidelity / Expressiveness / Aesthetics 六维框架很适合作为我们 G4
  人评层的参考。
- 它的核心短板是静态图、无原始数据，因此不能直接覆盖生成任务中的
  数据真值、动画时序和旁白一致性。
- 我们已有 G0–G3，可以把它放在后面的呈现质量层，而不是替代现有 GT。
- 它发现的模型“分数膨胀”和“过度保守”提醒我们：主观评分必须做盲评、
  多人一致性和校准，不能只依赖单个 MLLM judge。
