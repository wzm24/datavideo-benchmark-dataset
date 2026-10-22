# bar_22 V1 baseline prompts

## Narration

```text
Write the narration for a data video that fulfills the intent below, using ONLY
the data in the table. Do not invent data.

Author a cohesive story. The narration should explain, highlight, compare, or summarize the data
as needed. The story should unfold progressively over time, not all at once.

Return ONLY JSON: {"sentences": ["...", "..."]}

Chart form (fixed, do not change it):
__SPEC__

Intent: __INTENT__
Table:
__TABLE__
```

## HTML

```text
Write ONE self-contained HTML file (no external files except the audio file "audio/tts.wav")
that renders an animated chart (SVG or canvas) at 1280x720 with subtitles.

REQUIREMENTS (strict):
1. Include <audio id="tts" src="audio/tts.wav"></audio> and a visible subtitle element with id="subtitle".
1b. CHART FORM (fixed, do not substitute another form): __SPEC__
2. TIMELINE: the harness injects `window.__BENCHMARK__ = {duration: <seconds>,
   sentences: [{start: <s>, end: <s>, text: "..."}]}` BEFORE your script runs. Use it as the master
   timeline for subtitles and animation. If it is missing, fall back to the audio element.
3. TIME-ADDRESSABLE RENDER (required): implement a pure function
   `window.renderAt(t)` that draws the frame for time t (subtitles + chart state) without depending on
   playback. On load, if `new URLSearchParams(location.search).get("t")` is present, call
   `renderAt(parseFloat(t))` and do NOT require a click. The chart must be visible and correctly drawn
   for any t in [0, duration] even when the audio is paused.
4. Playback: still start the audio (and drive `renderAt`) via requestAnimationFrame/​timeupdate when
   the user presses play; a click-to-play button is allowed but the chart must already be visible before
   the click (no full-screen blocking overlay covering the chart).
5. SUBTITLES AND SYNC (mandatory):
   - The narration sentences and their start/end seconds are given below. Show the matching
     sentence in #subtitle during its window.
   - Subtitles must be synchronized with the animation events they describe: what a sentence
     talks about must be on screen while that sentence is showing, and must not disappear before
     the sentence ends.
   - Use the whole duration meaningfully. Allow the story to unfold progressively; do not rush
     key moments and do not finish the animation early.
   - Declare the sentence-to-animation plan as a JS array named PLAN, one entry per sentence:
       const PLAN = [
         {sentence: 0, window: [<start>, <end>], shows: "<what is on screen>",
          change: [<second it starts changing>, <second it stops>]},
         ... one entry per sentence, no omissions ...
       ];
     Expose the same array on window.__PLAN__, and build the animation by looping
     over PLAN.
6. Use only the values in the table, exactly as given.
Return ONLY the HTML, starting with <!DOCTYPE html>.

Intent: __INTENT__
Table:
__TABLE__
Narration (index, start, end, text):
__LINES__
```
