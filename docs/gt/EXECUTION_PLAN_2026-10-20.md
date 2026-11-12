# 执行方案：intent 只要不出错，G1 按文档定义

日期：2026-10-20
适用范围：V1（intent + data table + chart_spec）

## 0. 一句话

本轮公开输入只放 **intent + data table + chart_spec**。narration 和 semantic.svg 只用于**离线生成 intent**，不进入生成输入；G1 只从 **intent + data table** 生成，并按学长文档的定义写成"可独立判定的内容要求 + 接受路径"。

## 1. 现状 vs 目标

| 项 | 现状 | 目标 |
|---|---|---|
| intent 生成输入 | narration + **关键帧** | narration + data table + **semantic.svg** |
| intent 形式 | "To demonstrate that X" 叙事目标 | 协议式任务句（A/B 增长那种），一句话 |
| intent 质量目标 | 六维质量（忠实/覆盖/具体/泄露/可用/对齐） | **只要求不出错**：实体、方向、范围、指标、可答 |
| intent 与 G1 的关系 | G1 提示词里仍带 narration | G1 只用 intent + data table |
| G1 定义 | 固定命题 P + 最小依据 B + 证据 E；C1–C4 | 文档定义：**内容要求 + 接受路径**（all_of / any_of） |
| 生成输入是否带旁白 | 带（作为 reference） | **不带**；旁白只是生成 intent 的原料 |
| 关键帧 | 作为 intent 的视觉输入 | 不再输入；视觉侧用 semantic.svg |

## 2. 产物结构

```json
{
  "clip_id": "bar_34",
  "intent": "比较表中各国因费用跳过服药的占比，指出美国两组的位置，并量化两组差距。",
  "intent_provenance": {
    "sources": ["narration", "data_table", "semantic_svg"],
    "error_check": {
      "entity": "pass",
      "direction": "not_applicable",
      "scope": "pass",
      "measure": "pass",
      "answerable": "pass"
    }
  },
  "g1": {
    "requirements": [
      {
        "id": "R1",
        "question": "美国两组在表内所有国家中处于什么位置",
        "answers": "any_of",
        "routes": ["排名表", "两端点比较", "差距标注"],
        "scope": {"entities": ["..."], "measure": "...", "time": "..."},
        "reject": ["只说'美国很高'不给数据", "把有保险说成最高"],
        "evidence": "要看到哪些图元/标注才算讲到了"
      }
    ]
  }
}
```

公开给生成器的只有 `intent` + data table + chart_spec；`intent_provenance` 和 `g1` 留在评测端。

## 3. 执行步骤

### Step 0：先定"什么叫 intent 出错"

只查五类，不评文采、不评信息量：

| 错误类型 | 例子 | 检查方式 |
|---|---|---|
| 实体错 | 把美国写成英国 | intent 中的实体是否在表中出现，且与 narration/svg 指代一致 |
| 方向错 | "美国最高"写成"美国最低" | 若 intent 含方向断言，和表算出的方向比对 |
| 范围错 | 把"表中六国"说成"全球"；时间窗写错 | 实体集合、时间窗与表/svg 一致 |
| 指标错 | 把比例说成人数；单位错 | 指标名、单位与表头一致 |
| 不可答 | 要求比较表里没有的实体（bar_78 的 Regus） | 要求的每个实体/指标都能在表中查到 |

只要这五项过，intent 就接受；不追求"写得好"。

### Step 1：生成 intent（离线，一次性）

- 输入：`narration.jsonl` + `data_table.csv` + `semantic.svg`
- 模型：qwen3.7-flash（读 SVG 时可用 vision，或直接把 SVG 文本喂给文本模型）
- 输出：一句任务句，2–3 个分句，按 A/B 增长的样子：
  > 比较 A、B 在 2022 到 2023 年的用户增长，分别量化两者各自的变化，并说明哪个增长更快。
- 硬约束：一句话；≤32 词；无数字（年份除外）；无"最高/最低/上升/下降"等方向词；实体与指标必须在表里。
- 纠错：生成后跑 Step 0 的五类检查；有错就改，不通过就人工介入。

### Step 2：生成 G1（intent + data table，不带 narration）

- 输入：`intent` + `data_table.csv` + chart_spec
- 输出：1–3 条 requirement，每条含 `question / answers(all_of|any_of) / routes / scope / reject`
- 规则（来自文档）：
  - 单元是一项可独立判定的内容要求，不是固定命题；
  - 同一要求内不同表达是 `any_of`，并列要求是 `all_of`；
  - 每条 route 必须**足以证明**该要求（bar_27 的端点不能证明单调）；
  - 不按动词数或句子数决定条数；
  - 任务要求表里没有的数据 → 标 `off_table`，不硬造。

### Step 3：校验（机器 + 人）

机器检查：

- intent：一句话、无数字/方向词、实体/指标在表、五类错误清单
- G1：每条 requirement 的实体/指标/时间都在表里；`all_of` 的每个子项齐全；`any_of` 至少两条 route；`reject` 非空
- 交叉检查：G1 的每条 requirement 都能从 intent 推出（intent 不能少问，也不能多问）

人工抽检（50 条）：

- 接受路径是否充分（bar_27 端点 vs 单调）
- 有没有漏掉 intent 要求的子问题
- 有没有把"表里没有的东西"写成要求
- 最终裁决：pass / revise / drop / off_table

### Step 4：批量与冻结

20 条试点 → 修提示词 → 340 条批量 → 50 条人工抽检 → 冻结版本号。

## 4. 需要你拍板的四件事

1. **错误清单**是否就这五类（实体 / 方向 / 范围 / 指标 / 可答）？还要不要加"因果/立场"（例如 bar_109 的政策主张）？
2. **intent 是否允许说"比较/量化"这类动词**（A/B 式），但不出现答案和方向词？
3. **G1 结构**是否允许 `all_of` 里再嵌套 `any_of`（例如"四个类别都要报告，每类可用值/份额/排名任一"）？
4. **340 条是否全部重做 intent**？我建议全部重做（形式要从叙事目标改成任务句），但 narration/table/svg 可以直接复用。

## 5. 脚本映射与工作量

| 用途 | 现有 | 新方案 |
|---|---|---|
| intent | `regen_intent_dual.py`（narration+keyframe） | 新脚本 `intent_task_spec.py`（narration+table+svg） |
| G1 | `g1_draft.py`（intent+table+narration） | 新脚本 `g1_requirements.py`（intent+table） |
| 校验 | 无 | `check_intent_errors.py`、`check_g1_requirements.py` |
| 试点 | `intent_pilot2.py`（20 条） | 复用，改成"requirements → 一句话"的顺序 |

预计：20 条试点 20–30 分钟；340 条批量 1.5–2 小时；50 条人工抽检 1.5–2 小时。

## 6. 已知风险

- **SVG 读法**：直接喂 SVG 文本比截图稳定，但要确认模型能理解 `<path>/<rect>/<text>` 的结构语义。
- **intent 不出错 ≠ G1 稳定**：intent 只保证范围正确，G1 的 all_of/any_of 仍可能拆错；所以 Step 3 的人工抽检重点看接受路径。
- **bar_78 类型**：intent 要求表里没有的实体时，必须在 Step 0 判"不可答"，不能进入 G1。
- **V2/V4**：本轮不启用；等 V1 冻结后再用 narration 作为输入单独建 G1。
