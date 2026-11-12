# 字幕"只在念数据"的量化与修法

学长的观察：现在的 baseline 字幕只是在读数据，没意义也不好打分。这条现在有数了。

## 1. 度量口径

脚本：`D:\dev\he-m-work\work\check_restatement_rate.py`

一句话被判为**复述**，要同时满足两条：

1. 句子里出现至少一个与本 clip 数据表完全一致的数（表里的 `value` / `x_value` / `relative_value`，
   以及它们的 ×100、÷100）；
2. 句子里没有任何表示比较、趋势、异常或结论的词（higher than、roughly doubles、only、
   despite、the gap widens、top、surpass 等约 90 个词）。

复述率 = 复述句 / 总句数。这条判据对应 DataReel 裁判标准里的 `Informativeness`：
它把"基本只是把数据念出来"明确判为 5 分里的 1 分。

## 2. 实测结果（2026-10-12）

| 来源 | 句数 | 复述句 | 复述率 |
|---|---|---|---|
| 原视频自己的旁白（340 条全量，作为参照） | 848 | 25 | **0.03** |
| baseline_audio（qwen，3 条） | 11 | 0 | 0.00 |
| baseline_ds_b2（deepseek，6 条） | 21 | 10 | **0.48** |
| ablation_layout（qwen 布局消融，6 条 × 2 臂） | 20 | 5 | **0.25** |

结论：原视频的解说只有 3% 的句子在念数据；我们的 baseline 是 25% 到 48%。
也就是说模型不是不会讲故事，是我们**没有要求它讲故事**。

## 3. 根因

`baseline_audio.py` 的 `NARR_PROMPT` 原文只有两句要求：

> Write the narration for a 15-20 second data video as 3-4 short English sentences.
> Base every number on the table below; do not invent data.

"每个数字都要有依据"这条被模型读成了"把表里的数字说出来"，
而"要讲什么"完全没有约束。给出的 intent 是唯一的内容来源，但提示词没让它变成判断。

## 4. 已做的修改

`NARR_PROMPT` 已改为（`baseline_audio.py`，`b2_deepseek.py` 复用同一个常量）：

- 每句必须给出**观众无法直接从图上读到**的判断：比较、趋势、异常或结论；
- 数字只能作为判断里的证据出现，**每句最多一个数字**；
- 给出倾向的措辞示例（higher than / roughly doubles / only / despite / the gap widens）；
- 每句不超过 22 词，保证动画期间读得完。

## 5. 还差的三件事

1. **GT 侧**：新增 `narrative_claim` 单元类型，把"有没有洞见"变成可判定的义务；
   单元内容按 P3 的比较类型（1:1 / 2:2 / All / 1:M）分类，人工复核时直接选类型。
2. **指标侧**：复述率进自动指标（不需要人评），并与 DataReel 的 `Informativeness`
   五点量表做相关性校准；两个都报，避免只用代理指标。
3. **重跑**：改完提示词后，现有的 6 条 B2 输出与新跑的输出不能混榜，
   要么标版本号 `narration_prompt_v2`，要么整批重跑。

## 6. 顺带发现

同一批脚本里，`run_baseline.py` 用的是另一条更早的提示词，也要求"write your own narration
subtitles"但同样没有洞见约束。如果后续要用它跑对照，需要一起改，否则两条 baseline 的口径不一致。
