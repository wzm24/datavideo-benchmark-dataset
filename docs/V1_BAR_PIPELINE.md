# V1 Bar Pipeline: Intent, G1, G2, G3

Status: 2026-10-28  
Scope: all 153 `bar_*` clips in this repository  
Public contract: V1 = one neutral intent + `data_table.csv` + chart subtype metadata

## 1. What the generator sees

The model-facing file is `input_spec.json`:

```json
{
  "clip_id": "bar_88",
  "family": "bar",
  "sub_type": "population_pyramid",
  "orientation": "horizontal",
  "time_behavior": "snapshot"
}
```

`sub_type` is public because knowing that a chart is stacked, grouped,
pictograph, overlay, or a population pyramid is part of the task definition.
The input does **not** contain row counts, series counts, category counts,
mark counts, or the answer to who is largest/highest.

Current bar subtypes are:

| subtype | clips |
|---|---:|
| simple | 108 |
| stacked | 16 |
| grouped | 10 |
| population_pyramid | 7 |
| pictograph | 4 |
| stacked_100 | 4 |
| overlay_bar | 3 |
| range_bar | 1 |

There are 45 complex-chart hardcases:

- 16 stacked
- 10 grouped
- 7 population pyramids
- 4 pictographs
- 4 stacked-100 charts
- 3 overlay bars
- 1 range bar

## 2. Source preparation

The source reference consists of `narration.jsonl`, `keyframe.png`,
`semantic.svg`, and the extracted table. It is used to build and audit the data
facts, not supplied as a hidden answer to the generator.

For each clip:

1. Verify that the selected keyframe contains the complete final chart.
2. Verify that `semantic.svg` preserves the source chart's labels, scales,
   series order, stacking order, and proportions.
3. Reconstruct `data_table.csv` from the verified SVG or the original chart
   data. The table is the only factual source exposed in V1.
4. Keep semantic data columns only. Do not include pixel positions, colors,
   typography, layout, or extraction metadata in the public table.
5. For state sequences, preserve every declared state and all marks in each
   state.

## 3. Intent generation

The public intent is generated in three stages.

### 3.1 Internal narrative goal

The original narration and verified reference chart may be summarized as an
internal `narrative_goal`. This is an answer-bearing annotation artifact and is
never the public generator input.

### 3.2 Neutral public intent

The writer sees:

- `narrative_goal`
- `data_table.csv`
- G1 requirement questions and scopes (not G1 answers)

It returns one imperative sentence:

- at most 32 words;
- no numeric data values;
- four-digit years and numbers that are intrinsic entity names are allowed;
- no directional answer in the task, such as "A is higher" or "the rate fell";
- no chart style, layout, or animation prescription;
- every required intent slot must be represented.

Example shape:

```text
Compare A and B from 2000 to 2010, report each change, and determine
which changed more.
```

Not:

```text
Show that A increased from 10 to 20 and grew faster than B.
```

### 3.3 Intent verification

Every generated intent passes:

1. A deterministic table-number leakage check.
2. A requirement/scope coverage check.
3. A blind round trip: another parser receives only the public intent and
   `data_table.csv`, derives what a correct video must establish, and the result
   is compared with the required semantic slots.

The final four intent fields must be identical:

```text
intent.json:intent_en
intent.json:current_model_input
g1.json:intent
public_intent_v1/<clip>.json:proposed_intent
```

## 4. G1 generation

G1 has one structural requirement plus zero or more semantic requirements.

### 4.1 R1 completeness

Every bar clip starts with:

```text
R1: How does the video present the required bars in this chart?
```

For a snapshot chart, R1 has one completeness unit listing every required bar
or stacked segment. For a state sequence, each state receives its own
completeness unit and all units are joined by `all_of`.

Completeness applies to every category × series mark. A missing value that is
near the baseline still fails; endpoint-only display is not accepted.

### 4.2 Semantic slots

The remaining units are derived from the public intent:

1. Split the intent into obligation slots: comparison, change, trend,
   share/composition, ranking, extreme, threshold, or identity.
2. For every slot, select the minimum table cells that determine the claim.
3. Apply the protocol tests:
   - C1: the claim is decidable and true from the table.
   - C2: it is not a single-cell restatement, except for the one-row-table
     exception.
   - C3: deleting the claim means the public intent was not fulfilled.
   - C4: units serving one slot and one proposition are merged.
4. Add `accepted_routes`, concrete `reject` cases, and a visual evidence rule.
5. Assign equal weights `1/n` over all required units.

No fixed 3–5 unit target is used. The number of semantic units must equal the
number of independent intent slots.

### 4.3 Optional and unsupported material

Facts found only in the original narration or SVG but not derivable from the V1
table are not required units. They are removed or recorded as unsupported.
They may become V2/V3/V4 requirements later, but they are not hidden V1
obligations.

## 5. G2 generation

G2 is generated deterministically from:

- finalized G1 units and their basis;
- verified `data_table.csv`;
- canonical chart subtype metadata.

Each required unit receives one evidence record:

```json
{
  "unit_id": "U2",
  "unit_kind": "trend",
  "must_be_visualized": true,
  "evidence_type": "trend",
  "required_marks": ["..."],
  "assertion": {"..."},
  "accepted_routes": ["geometry", "readable_label"],
  "completeness_ref": "g0_data_completeness",
  "needs_review": false
}
```

Typical assertions:

- comparison: shared-scale ordering, ratio, or visible labels;
- change/trend: endpoint values, direction, deltas, or key turning points;
- share/composition: within-category segment sums and proportions;
- ranking: the full expected order;
- extreme: the maximum/minimum mark;
- threshold: the relevant intervals or crossing points;
- identity: the required label/value mapping.

Negative and positive values do not receive an invented multiplicative ratio.
Stacked segments are checked within the same category. Multi-panel clips keep
panel identity in every mark.

## 6. G3 generation

G3 binds each unit to the generated narration, not to the original video:

- completeness: `structural_completion`;
- semantic units: `generated_narration`;
- anchor: the sentence that completes the unit;
- provisional pre/post windows: `1.0s / 1.5s`;
- provisional minimum dwell: `0.8s`;
- identity binding: entity and series must remain stable;
- transition policy: ignore intermediate animation geometry and judge completed
  marks.

G3 thresholds remain `draft_requires_g4_calibration`; they are not claimed as
validated constants.

## 7. Validation gates

The publication gate for all 153 bar clips checks:

- 153/153 intent protocol checks pass;
- 153/153 blind V1 round trips close;
- all four public-intent fields are synchronized;
- no table-value leakage in public intents;
- every G1/G2/G3 unit ID is consistent;
- every unit type is in the protocol enum;
- every weight set sums to 1;
- no required unit has an empty basis;
- no duplicate-basis unit remains;
- every complex chart is marked as a hardcase;
- every complex chart's R1 basis covers all table-defined bar or segment marks.

Current result:

```text
clips: 153
semantic units: 187
required units including completeness: 352
intent protocol passes: 153
blind round-trip passes: 153
complex-chart hardcases: 45
complex-chart completeness failures: 0
```

## 8. Reproduction order

The migration and audit utilities live in the source pipeline repository:

```text
generate_protocol_intents.py
audit_intent_roundtrip.py
normalize_and_repair_all_bar_g1.py
sync_bar_chart_metadata.py
finalize_slot_units.py
finalize_remaining_slots.py
audit_required_units.py
build_intent_review.py
```

Recommended execution order:

```text
1. prepare and verify data tables / semantic SVG
2. generate or normalize public intents
3. build protocol-compliant G1
4. sync chart metadata
5. derive G2 from G1 + table + chart metadata
6. derive G3 timing policy
7. run intent/round-trip checks
8. run full unit audit and complex-chart coverage audit
9. build the review page and export the archive
```

## 9. Related artifacts

- `audits/bar_v1_20261027/SUMMARY.md`
- `audits/bar_v1_20261027/audit.csv`
- `audits/bar_v1_20261027/complex_hardcases.md`
- `audits/bar_v1_20261027/SCORE_FORECAST.md`
- `reviews/2026-10-28/bar_1_163_full_review.html`
