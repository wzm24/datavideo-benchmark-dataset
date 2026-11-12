# Uniform narration context audit

- Clips: 340
- Families: {"bar": 153, "line": 92, "area": 34, "donut": 41, "pie": 20}
- Source transcripts: 85
- ASR models: {"faster_whisper_small": 85}
- Mask padding: ±1.5s
- Verification statuses: {"pass": 313, "needs_review": 26, "pass_empty_context": 1}
- Mask leaks: 0
- Context mismatches: 0
- Missing packages: 0
- Audit passed: True

## Corpus summary

```json
{
  "clip_count": 340,
  "unique_source_video_count": 85,
  "asr_model": "faster_whisper_small",
  "mask_padding_seconds": 1.5,
  "status_counts": {
    "pass": 313,
    "needs_review": 26,
    "pass_empty_context": 1
  },
  "status_by_family": {
    "bar": {
      "pass": 138,
      "needs_review": 15
    },
    "line": {
      "pass": 87,
      "needs_review": 4,
      "pass_empty_context": 1
    },
    "area": {
      "pass": 31,
      "needs_review": 3
    },
    "donut": {
      "pass": 38,
      "needs_review": 3
    },
    "pie": {
      "pass": 19,
      "needs_review": 1
    }
  },
  "needs_review_clips": [
    "bar_22",
    "bar_24",
    "bar_25",
    "bar_26",
    "bar_39",
    "bar_40",
    "bar_57",
    "bar_78",
    "bar_101",
    "bar_104",
    "bar_125",
    "bar_132",
    "bar_139",
    "bar_146",
    "bar_159",
    "line_27",
    "line_54",
    "line_68",
    "line_96",
    "area_6",
    "area_39",
    "area_44",
    "donut_5",
    "donut_13",
    "donut_19",
    "pie_20"
  ],
  "excluded_from_context_arms": [],
  "empty_context_clips": [
    "line_90"
  ],
  "avg_context_tokens_estimate": 1519,
  "max_context_tokens_estimate": 3335
}
```

Each clip package is written to both `clips/<clip_id>/context_input.json` and
`ok_5files_all/<clip_id>/context_input.json`.

## No-context policy

A source with no non-target narration uses the empty string as its context.
Empty context is a valid input, not missing data. Clips remain eligible for all
V1-V4 contracts. The current case is `line_90`; see `LINE90_DECISION.md`.
