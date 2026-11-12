# G1 Hardcases

## Definition

A required semantic unit is a **hardcase** when both of the following hold:

1. The proposition is necessary to complete the public intent and is supported
   by the public V1 inputs (`intent_en`, `data_table.csv`, `chart_spec.json`).
2. The source chart has no obvious direct data mark, axis, label, or other
   visual encoding for that proposition.

This is different from an unsupported narration claim. If a claim is only in
the source narration and is not supported by the table or intent, it remains
`optional_valid` or unsupported; it does not become a hardcase G1 unit.

## Default handling

- Keep the hardcase in G1 if deleting it would make the intent incomplete.
- Set `must_be_visualized=false` by default.
- Its `C_u` score still enters `ContentCompletion`.
- It is excluded from `VisualCompletion` and `JointCompletion` denominators
  unless the task explicitly asks every required unit to be visualized.
- Accept flexible generated visualizations when present, such as a readable
  annotation or callout tied to the relevant evidence. Do not prescribe one
  fixed icon or layout.
- Record a `hardcase` flag and a short `hardcase_reason` in the G1 unit.

## Examples

### bar_22 / U3

- Claim: extreme ultra-rich wealth concentration is the rationale for a wealth
  tax that could fund programs benefiting millions.
- Public support: intent plus the contrast between named occupations and the
  off-scale ultra-rich tail.
- Source visual: no direct tax mark.
- Handling: `unit_kind=narrative_claim`, `must_be_visualized=false`.
- The independent V1 output additionally drew an off-scale ultra-rich arrow and
  a wealth-tax callout. This is accepted as a valid optional visual route, not
  as a requirement inherited from the source video.

### bar_28 / whole clip

- Type: `threshold_diagram_with_narration_only_claims`.
- The source visual is a wealth-threshold schematic, not a standard category bar
  chart. One illustrative wealth column crosses `$60M` and `$1B`; `2%` and `3%`
  are rate annotations attached to those thresholds.
- U1 (threshold-to-rate relationship) requires visual evidence.
- U2 (`0.05%` tax base) and U3 (`$200B` potential revenue) exist only in
  narration and use `must_be_visualized=false`.

## Batch migration flags (2026-10-22)

For `bar_35` onward, hardcases were flagged conservatively during migration:

- `legacy_units_without_visual_basis`: a required legacy unit has no basis, or its
  basis is explicitly narration-only. It defaults to `must_be_visualized=false`.
- `no_explicit_bar_mark_in_reference_svg`: the reference SVG contains no recognizable
  `data-role="bar"` mark. These clips remain pending human visual inspection.
- `legacy_unit_count_above_4`: the migrated G1 still has more than four required
  units and should be checked for C4 duplication.

The authoritative per-clip status and flags are in `BAR_REVIEW_INDEX.csv`.

## Line input-side hardcases

### line_17 / implicit top decile

- Type: `implicit_top_decile`.
- The public table gives an `Income percentile` axis and continues beyond the
  printed 90th-percentile tick, but it does not explicitly name that final
  segment as `Richest 10%`.
- The source SVG contains that label; the public V1 input intentionally omits
  it so the model has to infer the top decile from the percentile structure.
- During intent/G1 authoring, decide explicitly whether identifying the top
  decile is `required`, `optional_valid`, or not supported by V1.
- For G2, verify whether the generated chart visibly shows the final
  high-participation segment in the top-decile region.

### line_6 / staggered series start

- Type: `staggered_series_start`.
- The Bank of England base rate begins in 1991, while the mortgage-rate series
  first becomes visible later; the public table marks its first point as 1993.
- The two lines do not share a full-period starting year. A generated chart
  should not pad the mortgage series back to 1991 or imply values before its
  first observed point.
- During intent/G1 authoring, define the comparison period using the shared
  overlap unless the intent explicitly asks about the base-rate series alone.
- For G2/G3, verify the visible start of the mortgage line and the time window
  of any comparison between the two rates.

### line_44 / staggered series start and 2008 drop

- Type: `staggered_series_start`.
- The white base-rate line begins in 1991; the red mortgage-rate line first
  becomes visible in 1995.
- The public table marks the white line's sharp drop at 2008.
- A generated chart must not connect the red line back to 1991 or imply
  mortgage observations before 1995.
- During intent/G1 authoring, separate claims about the full base-rate period
  from claims about the shared 1995-2016 overlap.
- For G2/G3, verify both the delayed red-line start and the binding of the
  white-line drop to 2008.
