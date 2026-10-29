340 条 OK 五件套的合并副本，每条一个文件夹，名字自带类别前缀（bar_ / line_ / area_ / donut_ / pie_），按名字排序即按类别分组。

bar 与 line 目录核心文件：
  keyframe.png        原视频关键帧
  semantic.svg        我们确认过的语义图（风格的唯一真值）
  data_table.csv      V1 公开数据表
  narration.jsonl     原视频旁白
  intent.json         公开 intent 与内部叙事目标溯源
  input_spec.json     公开图表类型 / 方向 / 时间行为，不含数量提示
  chart_spec.json     完整图表元数据，供评测端使用
  g1.json             R/U、basis、权重与完整性要求
  g2.json             逐 U 的视觉证据规范
  g3.json             逐 U 的时间政策草稿

当前 bar V1 流水线与审计说明见 docs/V1_BAR_PIPELINE.md。
line 的归档与闭合说明见 LINE_G2_G3_STATUS.md 和 audits/line_gt_20261029/。
原始位置仍是 data/generated/ok_5files_all/。
