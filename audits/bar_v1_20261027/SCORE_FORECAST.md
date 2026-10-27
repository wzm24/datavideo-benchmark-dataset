# Score-direction forecast after the bar G1 revisions

## Evidence boundary

- The only full-bar score history (`bar_v1_all`) is legacy: it used the
  count-hint chart specification that was later removed.
- The corrected no-count contract currently has only four pilot scores.
- Therefore the legacy means are useful for locating affected clips and
  regression risk, not for predicting the final absolute leaderboard.

Legacy full-set means:

- ContentCompletion: 0.9352
- VisualCompletion: 0.9357
- JointCompletion: 0.8761

## Current GT state

- 153/153 public intents pass protocol and blind round-trip checks.
- 187 semantic units use only protocol type names; no legacy alias,
  `narrative_claim`, empty basis, duplicate basis group, or non-visual required
  unit remains.
- 45 complex-chart clips are explicitly marked as `complex_chart` hardcases.
- Every complex chart's R1 basis covers all table-defined bars, segments,
  symbols, paired marks, or states.
- 352 required units in total, including completeness units.

## Directional estimate

Holding the corrected input contract and judge fixed, the expected direction is
upward.

- The affected clips with historically poor scores should gain most:
  `bar_120`, `bar_125`, `bar_129`, `bar_131`, `bar_134`, `bar_159`.
- Some clips already scored 1.0 in the legacy run and now have stricter,
  corrected units. Local regressions are possible, especially:
  `bar_109`, `bar_130`, `bar_142`, `bar_154`, `bar_155`, `bar_156`,
  `bar_158`, `bar_163`.
- A reasonable central forecast is a modest increase in the corrected-contract
  JointCompletion: roughly **+0.5 to +2.0 percentage points** relative to the
  same system run with the pre-normalization GT.

This is not a claim that the final no-count score will exceed the legacy
0.8761 JointCompletion. Removing count hints can lower model scores even when
the evaluation is fairer:

- a model may omit bars, stacked segments, or complex-chart subcomponents when
  it must infer their number from the table;
- corrected table values now expose errors that the old ambiguous/incorrect
  table could hide;
- stronger merged units can turn several easy partial passes into one failed
  joint unit.

## Expected behavior on complex charts

Complex-chart scores should become less inflated, not uniformly higher:

- stacked and stacked-100 charts: completeness depends on every
  category × series segment;
- grouped/pyramid charts: every paired or category-series mark is required;
- pictographs: the complete visible symbol/count encoding is required;
- range/overlay charts: both endpoints and the comparison overlay are checked.

The likely result is a lower ceiling on complex charts and a higher ceiling on
the previously mis-specified simple charts. Overall ranking should be more
discriminative even if the absolute mean moves by only a few points.
