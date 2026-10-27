# Required semantic unit audit

Scope: 153 bar clips under the V1 public contract (`intent + data_table`).
R1 completeness is excluded from the semantic-unit type denominator.
The sufficiency labels are model-assisted and require human validation.

## Summary

- Semantic units: 187 across 153 clips; mean 1.2222.
- Count distribution: `{1: 127, 2: 20, 3: 5, 5: 1}`.
- Canonical type counts: `{'comparison': 99, 'share_or_composition': 22, 'trend': 16, 'change': 15, 'ranking': 15, 'identity': 12, 'extreme': 6, 'threshold': 2}`.
- Type status counts: `{'exact': 187}`.
- Raw model sufficiency counts: `{'sufficient': 141, 'undercovered': 8, 'overdecomposed': 4}`.
- Final adjudicated sufficiency counts: `{'sufficient': 153}`.

## Deterministic flags

- non_protocol_type: 0 clip(s)
- legacy_alias: 0 clip(s)
- ambiguous_type: 0 clip(s)
- empty_basis: 0 clip(s)
- non_visual_required: 0 clip(s)
- duplicate_basis: 0 clip(s)
- generic_question: 26 clip(s) — bar_104, bar_105, bar_107, bar_110, bar_111, bar_114, bar_115, bar_116, bar_117, bar_118, bar_119, bar_121, bar_122, bar_128, bar_132, bar_137, bar_139, bar_140, bar_141, bar_146, bar_147, bar_149, bar_150, bar_151, bar_153, bar_160
- undercovered: 0 clip(s)
- overdecomposed: 0 clip(s)
- candidate_not_pass: 0 clip(s)
- intent_sync_mismatch: 0 clip(s)
- intent_numeric_leak: 0 clip(s)
- roundtrip_not_pass: 0 clip(s)

## Outputs

- `audit.json`: full per-clip records.
- `audit.csv`: reviewer-friendly flat table.
- `summary.json`: aggregate machine-readable summary.
