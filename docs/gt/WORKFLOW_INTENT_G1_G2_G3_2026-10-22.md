# DataVideo Benchmark：intent / G1 / G2 / G3 工作流与提示词

日期：2026-10-22  
适用范围：当前 `ok_5files_all` 数据包，尤其是已经完成统一化的 `bar_*` 家族

## 1. 先说明两个容易混淆的点

1. **G2、G3 目前没有自由文本生成提示词。**
   - G2 是确定性的规则生成器：读取 `g1.json + data_table.csv + input_spec.json`，为每个 U 生成一个 `evidence_type + required_marks + assertion`。
   - G3 同样由规则生成：读取 G1/G2 和 `g0_data_completeness`，为每个 U 写入锚点、可用性、顺序、停留和状态检查政策。
   - 因此不能把 G2/G3 描述成“让模型自由写一段评分标准”；这样会重新引入不可复现性。

2. **intent 的“当前内容状态”和 `intent_source` 旧溯源字段必须分开看。**
   - `intent_source` 记录的是最初起草时读过什么，例如大部分历史草稿仍写
     `narration + keyframe`。
   - 人工 review 可能已经改写了句子，但批量脚本没有同步回写这个 provenance 字段。
   - 因此，`intent_source=narration + keyframe` 不等于“当前 intent 仍是旧稿”。
   - 当前 `ok_5files_all` 有 153 条 bar；`review.html` 中 100 条已人工
     approved，53 条仍 pending。approved 的 intent 应按人工确认后的当前内容使用。
   - 仍需补做的是 provenance 迁移：把最终人工版本的实际依据统一写成
     `narration + data_table + semantic.svg`。

---

## 2. 端到端工作流

### 2.1 单条 clip 的输入产物

每条 clip 至少包含：

- `keyframe.png`：仅用于视觉核对和后续渲染，不作为新 intent 的主要生成输入。
- `semantic.svg`：风格、图元、标签、轴和比例的参考。
- `data_table.csv`：可计算的数据事实。
- `narration.jsonl`：原视频旁白句子及时间戳。
- `intent.json`：公开的一句话任务说明。
- `g1.json`：R + U + 权重。
- `g2.json`：逐 U 的视觉证据。
- `g3.json`：逐 U 的时间政策。

### 2.2 Intent 生成与 review 状态

当前采用两层状态：

- **内容状态**：人工是否看过并标为 `approved`。`review.html` 中的绿色条目属于这一层。
- **原始生成溯源**：`intent_source / draft_by`。它描述最初草稿从哪里来，不自动代表人工改稿后的最终来源。

目前 bar 范围的实际状态是：

- `ok_5files_all` 中现有 153 条 bar。
- 100 条 intent/G1 已由人工批准。
- 53 条仍在 `review.html` 中等待复核。
- 7 个编号不在当前 OK 包中，不应算作已处理。

现行流程按四步执行：

1. **理解原片**
   - 读 narration，提炼 1–3 条主干 claim。
   - 读 data table，确认每条 claim 能否由表计算。
   - 读 semantic SVG，确认原图真正编码了哪些实体、时间、标签和关系。
   - 不接受“旁白说了但表和图都没有”的内容作为必须单元。

2. **先写 task requirements，不先写最终句子**
   - requirement 是“视频必须回答的问题”，不是答案。
   - 覆盖实体/人群、指标、时间窗、对比集合和口径。
   - 标注 `all_of` 或 `any_of`，并列出合法接受路径与错误路径。

3. **压成一个公开 intent**
   - 一句话，2–3 个分句，最多约 32 个英文词。
   - 使用祈使或明确任务表述，如 `Compare...`、`Show how...`。
   - 不出现除年份外的数值。
   - 不出现 `highest / lower / increase / decline / exceed / dominant` 等方向或结论词。
   - 不描述图表，不写颜色、布局和元素坐标。

4. **独立检查**
   - 形式检查：句数、词数、数字、方向词、clip id。
   - 覆盖检查：最终 intent 是否覆盖每个 requirement。
   - 往返检查：另一个 agent 只看 intent + table，是否能推出原片主干。
   - 内容检查：把原片主干与推导 claim 对齐，判 `closed / partial / open / off_table`。

### 2.3 G1 生成

G1 分为“LLM 起草”与“确定性规范化”两段。

#### 第一段：LLM 起草语义单元

输入：

- 公开 intent
- data table
- narration（只作为候选来源）

要求：

- 先把 intent 拆成槽：比较、变化、趋势、占比、极值、阈值、身份。
- 一个槽对应一个 U，不按固定 3–5 条凑数。
- 每个 U 包含：
  - `claim / meaning`
  - `unit_kind`
  - 最小 `basis`
  - 可执行计算
  - `accept`
  - `reject`
  - 视觉证据说明
  - 人工复核问题
- 两个独立观测才构成非平凡单元；只是复述一个表格格子的事实不能当单元。
- 一个事实的以下写法只能保留一条：A>B、B<A、差 260、1.29 倍。
- 只依赖当前输入契约可推出的内容；参考 narration 不能偷偷增加隐藏义务。

#### 第二段：程序化规范化为当前 R/U schema

当前 `bar_*` 家族额外执行：

- 每条 bar 的第一个 requirement 固定为 `R1`：
  - 问题：`How does the video present the required bars in this chart?`
- 单状态图：R1 下一个完整性 U，列出所有 `role=bar` 行。
- `state_sequence`：每个状态一个完整性 U，R1 用 `all_of` 绑定。
- 完整性 U 的 `unit_kind = visual_completeness`，`must_be_visualized=true`。
- 所有 U（含完整性 U）默认等权，权重为 `1/n`。
- 其他语义 requirement/unit 顺序后移，但 claim、accept/reject 和语义内容保持不变。

### 2.4 G2 生成

G2 不调用 LLM。输入是：

- `g1.json` 中的每个 U 及其 basis
- `data_table.csv`
- `input_spec.json`

输出每条 U 对应一个 evidence record：

- `evidence_type`
- `required_marks`
- `assertion`
- `accepted_routes`
- `completeness_ref`
- `needs_review`

当前支持的主要规则：

| G1 类型 | G2 证据类型 |
|---|---|
| `visual_completeness` | `complete_mark_set` |
| `comparison` | `pair_comparison` / `ranked_comparison` |
| `key_value_endpoint` | `mark_value` |
| `key_value_extreme` | `extremum_mark` |
| `trend_or_order` | `monotonic_order` |
| `change_or_rate` / `trend_or_change` | `endpoint_change` |
| `share_or_composition` | `complete_composition` |
| `range_or_span` | `range_endpoints` |
| `threshold_or_crossing` | `threshold_marks` |
| `narrative_claim` 且无视觉义务 | `not_required` |
| 无数值但有可读文本 | `value_or_readable_label` |

生成原则：

- 两个值共享零基线才能用柱长比较比例。
- 负值与正值之间不计算无意义的除法比例，改用顺序和差值。
- 堆叠图按“同一类别内各段合计”检查。
- 状态序列图必须逐状态检查，不只看末帧。
- 复杂图形、多系列聚合和混合单位会标 `needs_review=true`。

### 2.5 G3 生成

G3 同样是规则派生，输入是：

- G1 的语义与完整性状态
- G2 的 required marks
- V1/V3 或 V2/V4 对应的旁白来源

每个 U 写入：

- `anchor_mode`：普通语义 U 为 `generated_narration`；完整性 U 为 `structural_completion`。
- `anchor_selector`：普通 U 为 `sentence_that_completes_unit`；静态完整性 U 为 `project_end`，状态序列为 `last_required_state_or_project_end`。
- `window_before_s = 1.0`
- `window_after_s = 1.5`
- `dwell_min_s = 0.8`；完整性 U 暂为 0
- `ordering`
- `identity`
- `transition`

这些阈值目前是草稿值，状态为 `draft_requires_g4_calibration`。

### 2.6 Review

审核页由 `bar1_163_full_review/make_review.py` 生成，顺序固定：

1. 数据表与 SVG/关键帧
2. Intent 与 narration
3. G1 的 Requirements + Units
4. G2 的视觉证据表
5. G3 的时间政策表

颜色含义：

- 绿色 `approved`：人工确认
- 黄色 `agent_draft_pending_human_review`：待人工复核
- 浅黄色 `Hardcase` 面板：该 clip 或某个 U 依赖旁白或缺少直接图元

人工 review 重点：

- 表里的实体、时间、数值是否和图一致。
- intent 是否说清任务但没有泄露答案。
- 每个 U 是否真的必要，是否存在重复槽。
- G2 的 required marks 是否足以证明 U。
- G3 的锚点是否是“完成该语义的句子”，不是随便一个提到数字的句子。
- 缺失标记、错标签、错比例和明显出框应记录为具体问题，而不是笼统写“质量不好”。

审核状态只在用户明确确认后改为 `approved`。自动生成、自动迁移或 `needs_review` 都不能自行视为人工通过。

---

## 3. Prompt 附录

### 3.1 Intent：requirements

```text
You are designing the public task for ONE clip of a data-video benchmark.
The generator will receive the table and ONE public sentence; the evaluator will score the work
against the requirements you write here. The current narrative goal is only a source.

Write 1-3 requirements. A requirement is a question the video must answer, not the answer itself.
Rules:
1. Every requirement must be answerable from the given data table. If the clip's point needs data
   that the table does not contain, do not invent it: put it in "off_table".
2. answers = "all_of" when every listed sub-answer is required; "any_of" when one sufficient route
   is enough. Do not use all_of to pad.
3. For any_of, routes must be alternatives of comparable evidential strength. A route that only
   proves a weaker claim is invalid: if the question is "does the score rise at every step", an
   endpoint pair does NOT count.
4. Give each requirement its scope: entities/population, measure, time window, comparison set.
5. Never add a requirement the goal does not ask for.
6. Keep reject lists concrete: what a video must not do to count as answering.

Return ONLY JSON:
{"narrative_goal":"one sentence",
 "requirements":[
   {"id":"R1","question":"...","answers":"any_of",
    "routes":["route 1","route 2"],"scope":{"entities":["..."],"measure":"...","time":"..."},
    "reject":["..."],"why_required":"max 15 words"}
 ],
 "off_table":["claims the clip makes that the table cannot answer"]}

Narration: __NARR__
Data table: __TABLE__
Chart type: __SPEC__
Current goal: __GOAL__
```

**现行 SVG 输入适配。** 上面是已经落盘的 `intent_pilot2` 基础模板，末尾仍然写着
`Chart type: __SPEC__`。新流程执行时，把这一行替换为：

```text
Chart semantics from semantic.svg:
__SVG__
```

其中 `__SVG__` 应包含原图中的 title、legend、轴标签、印刷数值和可见数据图元结构；
chart_spec 只保留为图型分类辅助，不能替代 SVG 中的真实标签和关系。

### 3.2 Intent：一句话生成

```text
Turn the requirements into ONE public intent sentence for the generator.
Rules:
1. Exactly one sentence, imperative, 2-3 clauses, at most 32 words. Start with a verb.
2. No numbers except years. No direction or conclusion words (highest, more, increase, decline,
   exceed, dominant ...). Ask for the result; never state it.
3. Name the scope from the requirement's scope field (entities/population, measure, time).
   If there are more than four entities, name the set instead of listing every member.
4. Do not describe the chart and do not mention colours or layout.
5. Every requirement must be reflected by one clause; do not merge two unrelated requirements and
   do not add a clause for something that is not a requirement.

Return ONLY JSON:
{"intent":"...", "clause_map":[{"clause":"...","requirements":["R1","R2"]}]}

Requirements: __REQS__
Scope: __SCOPE__
```

### 3.3 Intent：盲解析

```text
You receive a one-sentence intent and the data table a generator would receive.
Parse the sentence into what the generator is being asked to establish.

IMPORTANT: derived_claims must be what a CORRECT video would assert after doing the work, not a
restatement of the task. Compute it from the table: compare, rank, give gaps, state directions.

Return ONLY JSON:
{"tasks":[{"type":"...","subject":"...","measure":"...","comparison_set":"..."}],
 "scope":{"entities":["..."],"time":"...","measure":"..."},
 "derived_claims":["..."],
 "ambiguous":["..."]}

Intent: __INTENT__
Data table: __TABLE__
Chart type: __SPEC__
```

### 3.4 Intent：requirement 覆盖检查

```text
Check whether a one-sentence intent covers every requirement.
The sentence may be phrased as a task (Compare / Quantify / Show how) or as a narrative goal
(Show that X is ...). Both are valid. A narrative conclusion is part of the goal, not a leak,
as long as the sentence does not add unsupported numbers or facts.

Judge only whether the sentence asks the same question over the same scope:
  covered = the sentence asks for the claim OR asserts the same claim, with the same scope
  partial = the claim is present but the scope is incomplete (missing entity set, measure or time)
  missing = the claim is neither asked nor asserted
A comparison requirement is covered as soon as the sentence asks to compare the named subjects;
it does not need to spell out every endpoint, year or direction.

Return ONLY JSON:
{"requirements":[{"id":"R1","status":"covered|partial|missing","why":"max 15 words"}],
 "overall":"all_covered|partial|missing"}

Requirements: __REQS__
Sentence: __SENTENCE__
```

### 3.5 Intent：内容往返检查

```text
Check whether a one-sentence intent carries the content of the original clip.
(A) are the narration claims. (B) are the claims a reader derives from the intent plus the table.

Step 1: classify every narration claim: main (does it carry the point?) and in_table (can it be
checked against the table?).
Step 2: the verdict uses only main=true AND in_table=true. Off-table claims are reported but never
counted as missing.
Step 3: covered = same fact (entities, direction/order); wording and rounding do not matter.
partial = a real difference in direction, order, entities or magnitude, not just less detail.
If no counted claim exists, set overall to "off_table".

Return ONLY JSON:
{"counted":["S1"],
 "claims":[{"id":"S1","status":"covered|partial|missing","main":true,"in_table":true,
            "why":"max 15 words"}],
 "overall":"closed|partial|open|off_table","missing":["..."]}

Claims: __CLAIMS__
Derived claims: __DERIVED__
```

### 3.6 G1：LLM 起草提示词

说明：下面是当前 `g1_draft.py` 的原文。`bar_1–34` 及后续统一格式时，脚本还会在 LLM 输出之后程序化加入当前固定 R1 完整性 U；因此不要把提示词末尾旧的
“完整性作为 G0/G2 门槛”视为当前最终 JSON 结构。

```text
You are drafting the G1 layer for ONE clip of a data-video benchmark: the small set of
things a correct data video MUST convey, given the intent and the data table. The original
narration is included as a candidate source, but a unit still has to be derivable from the intent
and the table, because that is all the video generator will see. A human reviewer decides which
are required, so make the trade-offs visible.

==================================================
THE ONLY TEST THAT MATTERS: one cell or several
==================================================
The video generator receives the intent and the table, nothing else. Sort every candidate unit by
how many table cells it needs:

- ONE cell, restated -> NOT a unit. Do not write it. This covers a value copied out of a cell, the
  unit of measure, how many rows or series exist, that only one row exists, that a number is an
  average rather than a total, that the measure is taken at a particular moment.
- TWO OR MORE cells combined -> a unit. A gap, a ratio, a ranking, a crossing, a share of a whole,
  a direction over time, which of two groups is ahead, the size of a change. The viewer can read
  any single cell, but NOT what two cells say together, so these carry information.

So "the relative value is 0.125" is not a unit, while "the purchased share is seven times the
unpurchased one" is; "Black adults are at 0.32" is not a unit, while "Black adults are more than
twice the next-highest group" is. A unit that only re-describes one cell MUST NOT be proposed,
even though it is true.

EXCEPTION - a table with exactly one row and one data column: there is nothing to combine, and the
intent is usually just that one claim. Then that claim IS the one unit. Write exactly one unit for
it and set its basis to that cell. Covering nothing at all is worse than restating a single cell,
because the clip would then have no required content at all. Do not use this exception to split a
one-row table into several units.

==================================================
WORKED EXAMPLE (taken from our own protocol)
==================================================
Intent: Make a short data video for a general audience comparing A and B's user growth from 2022
to 2023. Quantify each one's change, and use quantitative evidence to show which grew faster.
Use only the provided data; do not speculate about causes or future trends.

Table (unit: millions):
row_id,region,year,users_million
a_2022,A,2022,100
a_2023,A,2023,160
b_2022,B,2022,100
b_2023,B,2023,120

Good G1: three units, each leaning on a different set of rows, each with a reject list.

U1 "A's change" - basis: A/2022=100, A/2023=160
   accepted_routes: both endpoints; or the +60 million gain; or the +60% growth
   reject: giving only the end value 160 without saying what changed; saying "A grew" with no quantity
U2 "B's change" - basis: B/2022=100, B/2023=120
   accepted_routes: both endpoints; or the +20 million gain; or the +20% growth
   reject: talking only about A; quoting B's growth as 60%
U3 "A grew faster than B, and the comparison is stated" - basis: all four rows
   accepted_routes: A 60% against B 20%; or 40 percentage points apart; or 3x the rate
   reject: merely asserting "A grew faster" with no quantity; comparing different denominators;
           explaining why it happened

Notice what is absent: no unit says "the table has four rows", "the values are in millions",
"this is a growth rate and not an absolute", or "the data covers two regions". All of those are
readable straight off the table, so they carry no information.

==================================================
WHAT MAKES A UNIT REQUIRED
==================================================
A proposition P is REQUIRED when a video that never conveys P has NOT done the intent. That is the
only definition of required; the four tests below are how you write such a P down correctly.
C1 decidable and true: P is a closed proposition about the data and the table makes it true.
C2 non-trivial: B needs at least two INDEPENDENT observations (different row, entity or time point).
   Two fields of the same row are one observation, so "0.125 and its complement 0.875" fails.
   Exception: a one-row table has one observation, and that claim is then the unit.
C3 the definition above, operationalised: delete P from the video - would a reader who has only the
   intent say the task was not done? If the intent still holds without P, it is optional_valid.
C4 independent: no other unit may share B, and the two propositions must not imply each other under
   the table - 1150 > 890, a gap of 260, and 1.29x are the SAME fact and must become one unit.

QUALIFIERS: each unit carries its scope inside the proposition - population/entity, time window,
unit, aggregation (e.g. "Americans" when the table only covers the US). Coverage checks the scope
together with the claim, so never write a separate unit saying what the chart is about; that is a
table header, not a finding.

How to count: split the intent into slots (compare / change / trend / share / extreme / threshold /
identity). One unit per slot, whatever the number of slots turns out to be. Never add a slot the
intent does not ask for, and never split one slot into several units because it has several kinds of
evidence - put the alternatives into accepted_routes instead. Report the slots you found in the
`slots` field, and give every unit exactly one `slot_id`; a slot with two units is a split, and a
slot with no unit means part of the intent was dropped.

==================================================
HARD RULES
==================================================
1. No meta units: nothing about how many rows or series exist, what cannot be derived, or what the
   clip should not show.
2. No unit or measure declarations: "the unit is usd", "this is an average, not a total", "the
   measure is taken at graduation".
3. No restating a table cell as a claim: "the only entity is 2021", "the relative value is 0.125".
4. ONE unit per distinct set of basis rows, and one unit per underlying fact. Two units must never
   share the same basis set, and you must not split a single fact into several units: a share and
   its complement, a ratio and its inverse, a difference and the two endpoints it came from, an
   ordering and the values that establish it - these are the SAME fact. Keep only the single most
   informative one of them.
5. Every number MUST come from the table or be an explicit arithmetic combination of cells (state
   the formula). No invented values.
5b. Do not enumerate pairwise comparisons. If several units all say which of two items is larger,
   replace them with the single ordering fact, or with the one comparison the intent asks for.
6. Never propose units about layout, colours, ticks, chart type or rendering.
7. A `relative_value` is a 0-1 NORMALISATION of size or order, NOT a percentage. Only write a
   percentage when the table's unit column says "%" (or the clip is a pie/donut share).
8. If the table has no absolute `value` (only `relative_value`), the units must be relative:
   ordering, comparison, direction, which is largest, share of the whole, trend shape. Set the
   basis field to "relative_value" and never state %, $ or counts.
9. `accepted_routes` = 2-4 DIFFERENT acceptable ways to convey the unit, of different evidence
   strength (an endpoint pair, a difference, a ratio, a ranking). These are not paraphrases.
10. `reject` = what must NOT count as conveying this unit. One or two concrete items.
11. unit_kind is one of: key_value_endpoint, key_value_extreme, trend_or_order, comparison,
    change_or_rate, share_or_composition, threshold_or_crossing, identity_or_series.
    identity_or_series is the weakest kind: use it only when the intent depends on identifying a
    series or its measure and the table cannot convey it otherwise, and keep it rare.
12. required_candidate = true when the intent cannot be honoured without this unit.
13. For every bar-family clip, include a top-level `g0_data_completeness` object with
    `required=true`, `mode`, `selection="all bar-role data rows; all data rows when role is absent"`,
    the exact `required_data_rows`, `evaluated_in="G2_visual_completeness"`, and
    `missing_any_fails_visual_completeness=true`. Every bar, grouped bar, stacked
    segment, and range endpoint present in the source table is mandatory as a visual
    data mark. If `time_behavior=frame`, set `mode="state_sequence"`, list every
    required state, and record the required mark count per state; G2 must inspect the
    full timeline and cannot accept a complete final frame alone. This is a G0-to-G2
    completeness gate, not a weighted G1 unit.

The `slots` list is REQUIRED, even when the intent has only one slot.
Reply with the JSON object only - no markdown fences, no analysis, no commentary:
{
 "slots": [
   {"slot_id":"S1","obligation":"the one thing the intent asks the viewer to take away",
    "unit_ids":["U1"]}
 ],
 "units": [
   {"id":"U1","slot_id":"S1","meaning":"...","unit_kind":"...","required_candidate":true,
    "basis":[{"entity":"...","x":"...","field":"value","value":0.0,"note":"..."}],
    "computation":"none | formula",
    "accepted_routes":["...","..."],
    "reject":["..."],
    "visual_evidence_rule":"what must be visible in the chart",
    "temporal_anchor":"which narration clause should carry it",
    "reviewer_question":"the single decision the human should make"}
 ],
 "optional_valid":["..."],
 "unsupported_to_avoid":["..."],
 "g0_data_completeness":{"required":true,"mode":"static_all_at_once | state_sequence","selection":"all bar-role data rows; all data rows when role is absent","required_data_rows":0,"required_states":[],"required_marks_per_state":{},"evaluated_in":"G2_visual_completeness","check_full_timeline":false,"final_frame_only_sufficient":true,"missing_any_fails_visual_completeness":true},
 "notes":"max 2 sentences"
}

Intent: __INTENT__

Table (clip_id,entity,entity_id,x_px,value,relative_value,unit,source_type):
__TABLE__

Original narration (reference only, do not copy blindly):
__NARR__
```

### 3.7 G2/G3：没有 LLM prompt，使用以下确定性指令

如果必须用“提示词式”方式记录，它们应写成下面这种不可自由改写的规范：

```text
Given one finalized G1 unit and its exact table basis:
1. Read only the unit kind, basis rows, data table, and chart input spec.
2. Emit exactly one G2 record.
3. Required marks are the basis rows, with entity/series/x/metric/value/unit.
4. Emit a machine-checkable assertion:
   - complete set for visual_completeness;
   - common-baseline length ratio or explicit label for comparison;
   - monotonic sequence for trend_or_order;
   - endpoint delta/ratio for change;
   - within-category segment sum for composition;
   - endpoints and span for range;
   - threshold candidates for crossing.
5. Do not invent values or marks absent from basis.
6. For negative values, do not compute a multiplicative ratio across zero.
7. If the rule cannot be stated without ambiguity, set needs_review=true.

Then emit exactly one G3 record for the same unit:
1. Anchor generated-narration units at the sentence that completes the claim.
2. Anchor completeness units at project end or the last required state.
3. Require completed marks, entity identity, and the declared ordering.
4. Use provisional before/after/dwell values from the current G3 policy until G4 calibration.
5. For state_sequence, check every declared state separately.
```

---

## 4. 当前局限

- 现有 bar 中 100 条 intent 已经人工 approved；但很多文件的 `intent_source` 仍保留最初的
  `narration + keyframe` 溯源，尚未回写为最终人工确认时的
  `narration + data_table + semantic.svg`。这是元数据迁移问题，不是内容未 review。
- G2/G3 已覆盖 bar，但仍属于自动草稿；复杂图与 31 个 G2 单元需要人工复判。
- G3 的 `1.0 / 1.5 / 0.8` 秒阈值尚未用受控变体校准。
- Review 页只负责组织证据和状态，不会自动把自动判断升级为人工 approved。

## 5. 实现位置

- Intent 试点：`D:\dev\he-m-work\work\intent_pilot2.py`
- G1 起草：`D:\dev\he-m-work\work\g1_draft.py`
- bar R1 完整性规范化：`D:\dev\data_video_dataset_pipeline\benchmark_draft\gt\add_bar_completeness_unit.py`
- bar G2/G3 规则生成：`D:\dev\data_video_dataset_pipeline\benchmark_draft\gt\normalize_bar_1_34_and_build_g2_g3.py`
- 合并 review 页：`D:\dev\data_video_dataset_pipeline\benchmark_draft\bar1_163_full_review\make_review.py`
