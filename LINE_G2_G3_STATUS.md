# Line G0-G3 archive status

- Clips: 92
- G1 units: 327
- Semantic units: 221
- Panel-level completeness units under fixed `R1`: 106
- G0 files archived: 92
- G1 files archived: 92
- G2 files archived: 92
- G3 files archived: 92
- G1 closure status: 92 / 92 pass
- Structural closure failures: 0

## Input contract

V1 exposes only:

- public `intent_en`
- `data_table.csv`
- count-free `input_spec.json`

The public input spec records chart family, subtype, orientation, panel count,
panel identities, and time behavior. It does not reveal series counts, extrema,
answer values, G1/G2/G3 content, narration, SVG, keyframes, or the source video.

## G1 closure adjudication

All remaining parser disagreements were reviewed against `data_table.csv`.

- 12 clips were confirmed as parser misreads and manually closed while retaining
  the original parser result under `manual_adjudication`.
- 4 clips have an intent relation that cannot be judged from V1 inputs and were
  downgraded to `optional_valid`: `line_4`, `line_46`, `line_59`, `line_69`.
- Numeric, range, direction, and arithmetic corrections are recorded in
  `audits/line_gt_20261029/truth_fixes.json`.

## G2

Each G1 unit has a machine-facing visual evidence record. Required marks,
accepted evidence routes, expected order, direction, extrema, or crossing
conditions are listed per unit. Multi-panel clips retain panel-scoped evidence.

## G3

Every unit has a temporal policy linked to generated narration:

- `anchor_selector=sentence_that_completes_unit`
- provisional `window_before_s=1.0`
- provisional `window_after_s=1.5`
- provisional `dwell_min_s=0.8`
- completed trajectory evidence is required before a trend conclusion
- crossing, comparison, and extrema policies require the corresponding marks
  before and after the narration anchor

These thresholds remain `draft_requires_g4_calibration`.
