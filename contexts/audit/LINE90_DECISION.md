# line_90 context decision

Date: 2026-11-12

## Finding

- Source: `3WSQI7aVIgo`
- Video duration: 190.427 seconds
- Target window: 16.0–28.0 seconds
- Padded mask: 14.5–29.5 seconds
- Unified VAD ASR: one cue, 17.78–27.78 seconds
- Remaining non-target context: empty

A diagnostic rerun with `vad_filter=false` and otherwise identical
Faster-Whisper-small settings produced seven segments, but all seven repeated
the same target sentence. The six non-target repeats had `no_speech_prob`
between 0.9399 and 0.9780, indicating hallucinated repetition rather than
additional speech.

## Decision

- Keep `line_90` in all V1-V4 contracts.
- Use the empty string as its V2/V4 narration context.
- Do not substitute YouTube captions, another source video, or no-VAD repeated
  text.
- Record `context_availability=empty`,
  `included_in_context_arms=true`, empty `context_text_chronological`, and
  `status=pass_empty_context`.

This is a valid empty-context input, not a masking failure.
