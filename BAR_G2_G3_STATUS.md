# Bar G2/G3 generation status

- Clips: 153
- G1 units: 380
- Completeness units under fixed `R1`: 164 (one per static clip; one per declared
  state for state-sequence clips)
- Visual units: 366
- Narrative-only units: 14
- G2 files generated: 153
- G3 files generated: 153
- G2 units marked `needs_review=true`: 31
- G2 units directly machine-checkable: 349

## Format normalization

`bar_1`–`bar_34` contain 34 human-approved clips and 50 G1 units. Their claims,
accepted routes, reject conditions and weights were preserved. The migration
only filled structural fields required by current G1/G2:

- `unit_kind`
- `must_be_visualized`
- `basis`
- normalized `g0_data_completeness`

They now use `g1_r_u_v2` and remain `approved`.

## G2

G2 is generated from the human-confirmed G1 basis, `data_table.csv` and
`input_spec.json`. Evidence types include pair/ranked comparisons, endpoint
changes, monotonic ordering, complete compositions, threshold marks, ranges
and readable-label fallbacks.

The 31 `needs_review` units are concentrated in large compositions,
multi-series trend comparisons, population pyramids and mixed-unit
threshold/ranking charts. They are generated as drafts and must not be treated
as finalized ground truth before geometric-rule review.

## G3

Every visual unit receives a generated-narration anchor policy:

- `anchor_selector=sentence_that_completes_unit`
- provisional `window_before_s=1.0`
- provisional `window_after_s=1.5`
- provisional `dwell_min_s=0.8`
- completed-mark geometry is required
- all declared states are checked for `state_sequence` clips

These thresholds remain `draft_requires_g4_calibration` and must be frozen
using controlled early, late and shortened-dwell variants before headline
evaluation.
