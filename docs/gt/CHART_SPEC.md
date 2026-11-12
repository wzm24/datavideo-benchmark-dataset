# chart_spec：把图型写进输入（2026-10-12）

学长的意见：**要告诉模型用什么图型，而且要细到小类型**（堆叠柱、分组柱、横向还是竖向），
否则同一个 clip 上 A 模型画堆叠柱、B 模型画分组柱，两边的完成度没有可比性。

这条与早期"不告诉模型用哪种图"的口径相反，现在按新口径执行：图型从"模型的自由选择"变成**输入的一部分**。

`chart_spec.json` 是数据集内部完整规格，供 GT、G2/G3 和审计使用。模型侧只接收
`input_spec.json`；两者不能混用。

## 1. 受控词表

| 字段 | 取值 | 说明 |
|---|---|---|
| `family` | bar / line / area / donut / pie | 大类，等于数据集目录 |
| `sub_type` | 见下表 | 小类型，跨模型必须一致 |
| `orientation` | horizontal / vertical / cartesian / radial | 柱状图的横竖，折线区域坐标系，环图极坐标 |
| `series_count` | 整数 | 同一类目下的系列数（堆叠段数 / 折线条数） |
| `category_count` | 整数 | 柱状图的类目数 |
| `panel_count` | 整数 | 子图数量，多子图必须一致 |
| `time_encoding` | none / frame / x_axis | 时间怎么编码：逐帧动画、x 轴、或不编码时间 |
| `frames` | 数组 | 逐帧动画的帧值，例如 [1990, 2017] |
| `marks_per_frame` | 整数 | 每一帧画几根柱/几个图元 |
| `time_behavior` | snapshot / frame | 数据值是同一快照，还是随时间帧变化；**入场生长动画不属于这个字段** |
| `motion` | none / bar_race / single_bar_race | 仅 GT/审计：多柱随帧、单柱随帧 |
| `unit_mark` | bar / square / flag | 图形单元，用于点阵、国旗、小方块这类计数图 |

小类型词表：

| family | sub_type | 含义 |
|---|---|---|
| bar | `simple` | 单系列普通柱 |
| bar | `grouped` | 分组柱（同类目下多柱并排） |
| bar | `stacked` | 堆叠柱 |
| bar | `stacked_100` | 百分比堆叠柱（每类目合计 100） |
| bar | `overlay_bar` | 同柱叠加（两个时间点重叠画在一根柱上） |
| bar | `pyramid` | 人口金字塔（男女分列） |
| bar | `pictograph` | 点阵 / 图案计数柱 |

**Bar 完整性硬规则：** 哪些数据柱必须出现由 G0 表的 `role=bar` 行定义，
实际是否画出属于 G2 视觉完整性检查，不构成额外 G1 单元。普通/分组/堆叠柱
必须出现输入表中的全部数据柱；堆叠柱还要求每个堆叠段完整。缺失任意一个柱或
段时，视觉完整性直接失败。Annotation 不是数据柱，但仍按它所属的语义单元判断。具体见
`evaluation_protocol.md` §2.4.7.1。

对于 `time_behavior=frame` 的柱图，完整性必须沿整段时间线检查：每个声明状态
都要出现，且每帧的全部必需柱/堆叠段齐全。末帧完整不能证明前面状态没有遗漏。
| bar | `range_bar` | 范围条：从 min 到 max 的横向条，可带参考点（如 0°C） |
| line | `single_line` | 单折线 |
| line | `multi_line` | 多折线（同一坐标系） |
| line | `multi_panel` | 多子图折线 |
| area | `simple_area` | 单条区域（曲线加填充） |
| area | `overlay_area` | 多条区域重叠（快慢、上下界、参考线） |
| area | `stacked_area` | 堆叠面积（构成随时间变化） |
| area | `two_panel_area` | 左右两块独立区域 |
| area | `bubble` | 圆的大小表示数值 |
| area | `pictograph_blocks` | 方块大小表示数值 |
| donut | `full_ring` | 完整环 |
| donut | `partial_ring` | 不完整环 / 仪表盘 |
| donut | `multi_ring` | 同心多层环 |
| pie | `full_pie` | 普通饼 |
| pie | `multi_pie` | 两个饼并排 |

### 1.1 时间编码：静态多类目 vs 逐帧动画

长表（同一 entity 在不同年份各一行）**不等于**并排多柱。必须看 `time_encoding`：

| 情况 | 表的样子 | spec | 正确画法 |
|---|---|---|---|
| 静态多类目 | entity 各一行，没有 x | sub_type=simple, time_behavior=snapshot | 所有柱并排（仍可长出来） |
| 多柱随帧变 | entity × 年份，同一 entity 多行 | sub_type=simple, time_behavior=frame，motion=bar_race，marks_per_frame=N | 每帧只画 N 根柱，值随帧动画 |
| 单柱随帧变 | 只有一个 entity，多行年份 | sub_type=simple, time_behavior=frame，motion=single_bar_race，marks_per_frame=1 | 同一根柱，值随帧变 |

**sub_type 只描述形态，永远不编码动画。** 数据是否随时间变化看 `time_behavior`；具体动画类型看 `motion`。`marks_per_frame`、`frames`、`time_encoding` 只留在完整 spec（GT/审计），不进 `input_spec`。

例：

- `bar_2`：4 个地区 × 2 个年份，是 `bar_race`，每帧 4 根柱。
- `bar_4`：同一根柱跨 5 个年份，是 `single_bar_race`，每帧 1 根柱。

## 2. 340 条的实际分布

| family | 分布 |
|---|---|
| bar（153） | simple 115、grouped 23、stacked 8、stacked_100 3、pictograph 2、pyramid 1、overlay_bar 1 |
| line（92） | single_line 49、multi_line 38、multi_panel 5 |
| area（34） | simple_area 11、overlay_area 8、bubble 6、two_panel_area 5、pictograph_blocks 2、stacked_area 2 |
| donut（41） | partial_ring 26、full_ring 13、multi_ring 2 |
| pie（20） | full_pie 17、multi_pie 3 |

横向 103 条、竖向 50 条（柱状图）。

## 3. 怎么推出来的

脚本：`D:\dev\he-m-work\work\make_chart_spec.py`，产物：

| 文件 | 内容 |
|---|---|
| `data/generated/chart_spec/<clip>.json` | 逐条 spec |
| `data/generated/chart_spec/chart_spec.csv` | 340 行汇总，便于复核 |

规则主要来自两张表：

1. **系列结构来自数据表**：`series` 列有几个取值就是几系列；同类目下系列是否共用同一个 `x_px`——
   共用就是堆叠，分开就是分组；每类目合计等于 100 就是百分比堆叠；
   `units` 里出现 squares / flags / people 就判为计数图。
2. **横竖与子图来自 SVG**：柱子的宽高比决定横竖；填充多边形的 x 区间不重叠就是左右两块（两面板、双子图）；
   环图的弧段总扫过角度小于 300 度判为不完整环，半径不止一种判为多层环。
3. **少数靠人工定**：写在脚本的 `OVERRIDES` 里并标注来源为 `manual_review`。
   目前两条：`bar_104`（两个时间点叠在同一根柱上，表面看不出来）、`area_29`（两个实心方块）。

**需要你过一眼的 59 条**（罕见形态或推断置信度中等）：28 条 donut 的不完整环、20 条 area、
5 条多子图 line、3 条 bar（bar_128 / bar_132 / bar_163）、3 条 pie。

## 4. 进入输入的方式

四档契约只向模型暴露图型和必要的动画语义。固定的模型侧输入措辞是：

> Draw this as a **{family}** chart, sub-type **{sub_type}**, orientation **{orientation}**,
> Do not substitute another chart form.

`series_count`、`category_count`、`slice_count`、`panel_count`、`row_count` 和
`marks_per_frame` 都是可从数据表推导或用于内部评测的元数据，**不能进入模型输入**。
模型需要自己从表和 intent 判断柱数、折线数、扇区数和面板内结构。

逐帧动画只额外给 `time_behavior=frame`：

> This chart is **animated over time**: draw one frame at a time; do not place all frames
> side by side. The number of marks per frame follows the subjects named in the intent.

## 5. 对 GT 的影响

| 影响 | 说明 |
|---|---|
| 图型不再是模型义务 | V1 到 V4 全部给定图型，因此"选错图型"不再扣完成度，改为**违反给定约束**，单独记一条 spec compliance 错误 |
| `identity_or_series` 单元 | 系列数不再由 spec 泄漏，模型必须根据数据表判断系列和 mark 数量 |
| G2 更容易自动化 | 证据类型已知（柱、扇区、折线点、圆半径），判定器可以按 sub_type 写，不必猜模型画了什么 |
| 跨模型可比性 | 同一 clip 所有系统画同一种图，完成度差异才能归因到"讲没讲清楚"而不是"画法不同" |
| 输入边界 | `input_spec` 只给图型；完整 `chart_spec` 保留用于内部 GT，不进入模型上下文 |
