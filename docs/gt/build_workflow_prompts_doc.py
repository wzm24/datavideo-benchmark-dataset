from __future__ import annotations

import ast
from pathlib import Path


WORK = Path(r"D:\dev\he-m-work\work")


OUT = Path(
    r"D:\dev\data_video_dataset_pipeline\benchmark_draft\gt"
    r"\WORKFLOW_INTENT_G1_G2_G3_2026-10-22.md"
)


def load_constant(path: Path, name: str) -> str:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise KeyError(f"{name} not found in {path}")


INTENT_REQS = load_constant(WORK / "intent_pilot2.py", "REQS")
INTENT_SENTENCE = load_constant(WORK / "intent_pilot2.py", "SENTENCE")
INTENT_PARSER = load_constant(WORK / "intent_pilot2.py", "PARSER")
INTENT_COVERAGE = load_constant(WORK / "intent_pilot2.py", "COVERAGE")
INTENT_CONTENT = load_constant(WORK / "intent_pilot2.py", "CONTENT")
G1_PROMPT = load_constant(WORK / "g1_draft.py", "PROMPT")
SVG_ADAPTER = """Chart semantics from semantic.svg:
__SVG__"""


def fence(text: str, language: str = "text") -> str:
    return f"```{language}\n{text.rstrip()}\n```"


G2_G3_RULES = """Given one finalized G1 unit and its exact table basis:
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
5. For state_sequence, check every declared state separately."""


def main() -> None:
    doc = f"""# DataVideo Benchmark：intent / G1 / G2 / G3 工作流与提示词

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

{fence(INTENT_REQS)}

**现行 SVG 输入适配。** 上面是已经落盘的 `intent_pilot2` 基础模板，末尾仍然写着
`Chart type: __SPEC__`。新流程执行时，把这一行替换为：

{fence(SVG_ADAPTER)}

其中 `__SVG__` 应包含原图中的 title、legend、轴标签、印刷数值和可见数据图元结构；
chart_spec 只保留为图型分类辅助，不能替代 SVG 中的真实标签和关系。

### 3.2 Intent：一句话生成

{fence(INTENT_SENTENCE)}

### 3.3 Intent：盲解析

{fence(INTENT_PARSER)}

### 3.4 Intent：requirement 覆盖检查

{fence(INTENT_COVERAGE)}

### 3.5 Intent：内容往返检查

{fence(INTENT_CONTENT)}

### 3.6 G1：LLM 起草提示词

说明：下面是当前 `g1_draft.py` 的原文。`bar_1–34` 及后续统一格式时，脚本还会在 LLM 输出之后程序化加入当前固定 R1 完整性 U；因此不要把提示词末尾旧的
“完整性作为 G0/G2 门槛”视为当前最终 JSON 结构。

{fence(G1_PROMPT)}

### 3.7 G2/G3：没有 LLM prompt，使用以下确定性指令

如果必须用“提示词式”方式记录，它们应写成下面这种不可自由改写的规范：

{fence(G2_G3_RULES)}

---

## 4. 当前局限

- 现有 bar 中 100 条 intent 已经人工 approved；但很多文件的 `intent_source` 仍保留最初的
  `narration + keyframe` 溯源，尚未回写为最终人工确认时的
  `narration + data_table + semantic.svg`。这是元数据迁移问题，不是内容未 review。
- G2/G3 已覆盖 bar，但仍属于自动草稿；复杂图与 31 个 G2 单元需要人工复判。
- G3 的 `1.0 / 1.5 / 0.8` 秒阈值尚未用受控变体校准。
- Review 页只负责组织证据和状态，不会自动把自动判断升级为人工 approved。

## 5. 实现位置

- Intent 试点：`D:\\dev\\he-m-work\\work\\intent_pilot2.py`
- G1 起草：`D:\\dev\\he-m-work\\work\\g1_draft.py`
- bar R1 完整性规范化：`D:\\dev\\data_video_dataset_pipeline\\benchmark_draft\\gt\\add_bar_completeness_unit.py`
- bar G2/G3 规则生成：`D:\\dev\\data_video_dataset_pipeline\\benchmark_draft\\gt\\normalize_bar_1_34_and_build_g2_g3.py`
- 合并 review 页：`D:\\dev\\data_video_dataset_pipeline\\benchmark_draft\\bar1_163_full_review\\make_review.py`
"""
    OUT.write_text(doc, encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
