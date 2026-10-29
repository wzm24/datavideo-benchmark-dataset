# Donut and pie table schema

All 41 donut and 20 pie clips use the same public table schema.

## Main table

```text
panel,series,entity,metric,value,unit,relative_value,label,role,source_type
```

- `panel`: layout/state identity for multi-panel clips; empty for a single chart.
- `series`: ring/composition identity only when a panel contains multiple rings.
- `entity`: semantic data entity. Avoid color-only names such as `orange share`.
- `metric`: the measured quantity.
- `value`: numeric value parsed from `label` whenever a numeric label exists.
- `unit`: `%`, count, million, USD, and similar units.
- `relative_value`: share within one composition or gauge, normalized to `[0,1]`.
- `label`: exact printed text from the visual, if present.
- `role`: `slice`, `arc`, `gauge`, `center_label`, `remainder`, `annotation`, or `state`.
- `source_type`: `printed`, `narration_calibrated`, `estimated`,
  `estimated_ring_geometry`, or `derived_complement`.

`label` is the authoritative printed fact. If it contains a number, `value` must
equal that number. Narration or geometry may supply `value` only when the label is
absent or non-numeric.

`panel`, `series`, `entity`, and `metric` are not interchangeable:

- `panel` is layout identity, e.g. `Panel 1`.
- `series` is an inner/outer-ring identity where required.
- `entity` is the data category.
- `metric` is the measured quantity.

## Sidecar

```text
clip_id,entity_id,x_px,x_value,geometry_relative_value,color,note
```

The sidecar carries geometry, stable binding and provenance. It must not override
the main table's checked value.

## Composition rules

- Full pies and multi-pie panels are normalized within each `panel`/`series` group.
- Multi-ring donuts are normalized within each ring/composition.
- Partial rings and gauges use the represented value over a 100% scale.
- Percentage annotations retain `value/100`; center counts and monetary labels use
  `role=center_label` and leave `relative_value` empty.
- A visible complement may use `role=remainder` and `source_type=derived_complement`.
- Rounded printed values are used directly as the table `value`.

## Current validation

- Clips: 61
- Rows: 147
- Main-table schema variants: 1
- Sidecar schema variants: 1
- Table/sidecar row mismatches: 0
- Duplicate or generic `slice-N` entity IDs: 0
- G1 basis references missing from table: 0
- G2 required-mark references missing from table: 0
- Local `ok_5files_all` versus GitHub file differences: 0

## Deliberately preserved source inconsistencies

- `pie_1/3/4`: Drive alone is now `76` because the printed label is `76%`;
  the other estimated slices produce a 99.7 total.
- `pie_2`: all five `value` fields now match their printed labels and sum to 95%;
  no unshown remainder is invented.
- `pie_5`: printed source shares total 89%; the pie geometry allocates the listed
  categories across the full circle. Table keeps the printed values and stores
  normalized visual shares separately.
- `pie_16`: printed source shares total 103%. The table keeps those printed values;
  `relative_value` is normalized over the listed total rather than fabricated to 100%.
- `donut_2`: checked table values are 75/18/7 from the narration/table audit; earlier
  77.1/12.5/10.4 geometry estimates remain explicitly marked as non-table provenance.
