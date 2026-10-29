# G0 fact-base archive status

- Schema: `g0_fact_base_v1_2026-10-29`
- Total OK clips: 340
- bar: 153
- line: 92
- donut: 41
- area: 34
- pie: 20

Every clip contains an independent `g0.json`.

## Contents

Each G0 record binds the evaluator-side fact base to the reviewed
`data_table.csv` and records:

- SHA-256 of the data table and optional sidecar
- row and column inventory
- chart family, subtype, orientation, panel structure, and time behavior
- x/y or category semantics and explicit x anchors where available
- entity/series inventory with row counts, units, metrics, source types,
  observed numeric ranges, and missing-value counts
- provenance counts for estimated, projected, or relative values
- the completeness requirement used by G1/G2

## Family-specific details

- bar uses the existing structured G0 completeness definition from G1.
- line preserves panel-scoped series and axis semantics, including explicit
  x anchors and incomplete-x cases.
- area uses table or sidecar x coordinates when present.
- donut and pie use table-level `relative_value` and `source_type`, plus sidecar
  geometry, stable entity identifiers, and notes when rows align one-to-one.

The machine-readable generation audit is stored in the source pipeline at
`benchmark_draft/g0_backups/all_ok_20261029/summary.json`.
