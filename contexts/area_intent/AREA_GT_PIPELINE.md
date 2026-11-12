# Area narrative goal / intent / G1 pipeline

Date: 2026-11-12

## Scope

This pipeline generates candidates for all 34 `area_*` clips after their data
tables and chart specifications were frozen.

It follows the current evaluation contract:

- narrative goal: internal, answer-bearing GT derived from narration, corrected
  table, chart specification, and confirmed visible labels;
- public intent: one answer-neutral imperative sentence derived from the goal;
- G1: V1 units derived only from public intent + data table + chart specification;
- G2/G3: deliberately not generated in this pass.

## Stages

1. `narrative_goal_candidate.json`

   The model receives narration, a compact table view, visible SVG labels, chart
   specification, and the stale old intent as non-authoritative context. A second
   call audits the goal against the table and visible labels without narration.
   Unsupported narration-only claims are removed.

2. `intent_candidate.json`

   The answer-bearing goal is converted into one imperative English sentence.
   The intent must preserve the public entity/scope comparison but may not reveal
   direction, ranking, extrema, threshold, complement, or causal conclusions.
   Mechanical checks reject non-year data numerals and presentation terms. A
   semantic checker audits leakage, scope, and answerability, followed by up to
   three repairs.

3. `g1_candidate.json`

   G1 uses only `intent_en + data_table.csv + chart_spec.json`. Each intent slot is
   assigned one semantic unit under protocol C1-C4. Units with an identical basis
   set are merged deterministically. `R1` is a separate visual-completeness
   requirement for all required area marks, with one unit per panel.

   An independent closure-audit prompt checks missing slots, duplicate units,
   unsupported claims, unnecessary units, and whether completeness was substituted
   for semantic interpretation.

## Public schema

Every G1 unit records:

- `id`, `requirement_id`, `unit_kind`;
- a non-trivial `claim` (P);
- resolved table `basis` rows (B);
- `computation`, `accept`, `reject`;
- `must_be_visualized` and `needs_review`.

Area unit kinds are:

`comparison`, `change`, `trend`, `extremum`, `ranking`,
`threshold_or_crossing`, `share_or_composition`, `proportional_comparison`,
`projection_or_range`, `identity`, plus `visual_completeness`.

## Run

```powershell
python benchmark_draft/area_intent/generate_area_gt.py --phase all --workers 4
python benchmark_draft/area_intent/generate_area_gt.py --phase render
```

Use selected clip names after `--phase` to rerun only those clips.

## Outputs

- `goals/`: internal narrative goal candidates;
- `intents/`: public intent candidates and audit records;
- `g1/`: V1 G1 candidates, closure audits, usage, and local checks;
- `review/review.html`: visual review page;
- `area_goal_intent_g1.csv`: flat review index;
- `summary.json`: full output status.

Each clip also receives `narrative_goal_candidate.json`,
`intent_candidate.json`, and `g1_candidate.json`. Existing `intent.json`,
`g1_draft_b2.json`, and other source files are not overwritten.
