"""Build all 340 masked narration-context packages with one ASR configuration."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import difflib
import html
import json
import os
import re
import shutil
import subprocess
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(r"D:\dev\data_video_dataset_pipeline")
CLIPS = ROOT / "data" / "generated" / "ok_5files_all"
SOURCE_MAP = ROOT / "data" / "processed" / "_full_video_transcripts" / "clip_source_map.csv"
FULL_VIDEOS = ROOT / "data" / "raw" / "videos" / "_full_720p"
FULL_AUDIO = ROOT / "data" / "raw" / "videos" / "_full_audio"
LEGACY_UNIFORM = ROOT / "data" / "processed" / "_bar_uniform_whisper_small_20261105"
TRANSCRIPTS = ROOT / "data" / "processed" / "_full_uniform_whisper_small_20261112"
OUT = ROOT / "benchmark_draft" / "full_narration_context_uniform_20261112"
CONTEXTS = OUT / "clips"
MODEL_DIR = ROOT.parent / "models" / "faster-whisper-small"
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
NODE = Path(r"D:\node.exe")
COOKIES = ROOT / "www.youtube.com_cookies.txt"
PROXY = os.environ.get("YTDLP_PROXY", "http://127.0.0.1:7897")
ASR_LABEL = "faster_whisper_small"
FAMILIES = ("bar", "line", "area", "donut", "pie")
MASK_PADDING_SECONDS = 1.5
SIMILARITY_THRESHOLD = 0.25


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def parse_clock(value: str) -> float:
    parts = [float(part) for part in str(value).strip().split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return float(value)


def norm(text: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        re.sub(r"[^a-z0-9%$ ]+", " ", text.lower()),
    ).strip()


def family_number(clip_id: str) -> tuple[int, int]:
    family, number = clip_id.rsplit("_", 1)
    return FAMILIES.index(family), int(number)


def clip_rows() -> list[dict[str, Any]]:
    clip_ids = {
        path.name
        for path in CLIPS.iterdir()
        if path.is_dir() and re.fullmatch(r"(?:bar|line|area|donut|pie)_\d+", path.name)
    }
    with SOURCE_MAP.open(encoding="utf-8-sig", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("clip_id") in clip_ids
        ]
    missing = clip_ids - {row["clip_id"] for row in rows}
    if missing:
        raise RuntimeError(f"clips missing from source map: {sorted(missing)}")
    for row in rows:
        row["start"] = parse_clock(row["Start"])
        row["end"] = parse_clock(row["End"])
        row["family"] = row["clip_id"].split("_", 1)[0]
    return sorted(rows, key=lambda row: family_number(row["clip_id"]))


def unique_sources(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values: dict[str, dict[str, Any]] = {}
    for row in rows:
        values.setdefault(
            row["video_id"],
            {
                "video_id": row["video_id"],
                "url": row.get("Link", ""),
                "title": row.get("Title", ""),
            },
        )
    return sorted(values.values(), key=lambda row: row["video_id"])


def local_media(video_id: str) -> Path | None:
    video = FULL_VIDEOS / f"{video_id}.mp4"
    if video.exists() and video.stat().st_size > 1024 * 1024:
        return video
    if FULL_AUDIO.exists():
        for path in sorted(FULL_AUDIO.glob(f"{video_id}.*")):
            if (
                path.suffix.lower() in {".m4a", ".webm", ".opus", ".mp3", ".wav"}
                and path.stat().st_size > 100_000
            ):
                return path
    return None


def seed_legacy_transcripts() -> dict[str, Any]:
    copied = []
    skipped = []
    if not LEGACY_UNIFORM.exists():
        return {"copied": copied, "skipped": skipped, "legacy_missing": True}
    for source in sorted(LEGACY_UNIFORM.glob("*/transcript.json")):
        payload = read_json(source)
        if payload.get("asr_model") != ASR_LABEL or not payload.get("cues"):
            skipped.append(source.parent.name)
            continue
        target = TRANSCRIPTS / source.parent.name / "transcript.json"
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(source.parent.name)
    return {
        "copied": copied,
        "skipped": skipped,
        "legacy_missing": False,
        "uniform_transcripts": len(list(TRANSCRIPTS.glob("*/transcript.json"))),
    }


def download_missing(sources: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [source for source in sources if not local_media(source["video_id"])]
    FULL_AUDIO.mkdir(parents=True, exist_ok=True)
    temp_dir = ROOT / "_work_tmp" / "runtime" / "yt-dlp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["TEMP"] = str(temp_dir)
    env["TMP"] = str(temp_dir)
    results = []
    for index, source in enumerate(missing, 1):
        command = [
            str(PYTHON),
            "-m",
            "yt_dlp",
            "--proxy",
            PROXY,
            "--socket-timeout",
            "30",
            "--retries",
            "3",
            "--js-runtimes",
            f"node:{NODE}",
            "-f",
            "bestaudio/best",
            "--no-playlist",
            "-o",
            str(FULL_AUDIO / "%(id)s.%(ext)s"),
        ]
        if COOKIES.exists():
            command.extend(["--cookies", str(COOKIES)])
        command.append(source["url"])
        started = time.time()
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=900,
            env=env,
        )
        media = local_media(source["video_id"])
        item = {
            **source,
            "status": "downloaded" if result.returncode == 0 and media else "failed",
            "returncode": result.returncode,
            "path": str(media) if media else "",
            "sec": round(time.time() - started, 1),
            "stderr_tail": (result.stderr or "")[-1200:],
        }
        results.append(item)
        print(
            json.dumps(
                {"download": f"{index}/{len(missing)}", **item},
                ensure_ascii=False,
            ),
            flush=True,
        )
    summary = {
        "missing_before": [source["video_id"] for source in missing],
        "status_counts": dict(Counter(row["status"] for row in results)),
        "results": results,
    }
    write_json(OUT / "download_summary.json", summary)
    if any(row["status"] == "failed" for row in results):
        raise RuntimeError("one or more source media downloads failed")
    return summary


def load_whisper():
    from faster_whisper import WhisperModel

    return WhisperModel(
        str(MODEL_DIR),
        device="cuda",
        compute_type="float16",
        num_workers=1,
    )


def transcribe_one(model, source: dict[str, Any]) -> dict[str, Any]:
    video_id = source["video_id"]
    target = TRANSCRIPTS / video_id / "transcript.json"
    if target.exists():
        payload = read_json(target)
        if payload.get("asr_model") == ASR_LABEL and payload.get("cues"):
            return {
                **source,
                "status": "cached",
                "path": str(target),
                "cues": len(payload["cues"]),
                "duration": payload.get("duration_seconds"),
            }
    media = local_media(video_id)
    if not media:
        raise FileNotFoundError(f"no local media for {video_id}")
    started = time.time()
    segments, info = model.transcribe(
        str(media),
        language="en",
        beam_size=5,
        vad_filter=True,
        condition_on_previous_text=True,
        word_timestamps=False,
    )
    cues = []
    for segment in segments:
        text = re.sub(r"\s+", " ", segment.text).strip()
        if not text:
            continue
        cues.append(
            {
                "index": len(cues),
                "start": round(float(segment.start), 3),
                "end": round(float(segment.end), 3),
                "text": text,
                "source": ASR_LABEL,
                "avg_logprob": (
                    round(float(segment.avg_logprob), 6)
                    if segment.avg_logprob is not None
                    else None
                ),
                "no_speech_prob": (
                    round(float(segment.no_speech_prob), 6)
                    if segment.no_speech_prob is not None
                    else None
                ),
            }
        )
    payload = {
        "video_id": video_id,
        "source_media": str(media),
        "asr_model": ASR_LABEL,
        "model_path": str(MODEL_DIR),
        "device": "cuda",
        "compute_type": "float16",
        "language": "en",
        "beam_size": 5,
        "vad_filter": True,
        "condition_on_previous_text": True,
        "duration_seconds": round(float(info.duration), 3),
        "duration_after_vad_seconds": round(float(info.duration_after_vad), 3),
        "cue_count": len(cues),
        "cues": cues,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    write_json(target, payload)
    return {
        **source,
        "status": "transcribed",
        "path": str(target),
        "cues": len(cues),
        "sec": round(time.time() - started, 1),
        "duration": payload["duration_seconds"],
    }


def transcribe_all(sources: list[dict[str, Any]]) -> dict[str, Any]:
    seed = seed_legacy_transcripts()
    missing_media = [
        source["video_id"] for source in sources if not local_media(source["video_id"])
    ]
    if missing_media:
        raise RuntimeError(f"missing local media before ASR: {missing_media}")
    model = load_whisper()
    results = []
    for index, source in enumerate(sources, 1):
        result = transcribe_one(model, source)
        results.append(result)
        progress = {
            "completed": index,
            "total": len(sources),
            "seed": seed,
            "status_counts": dict(Counter(row["status"] for row in results)),
            "last": result,
        }
        write_json(OUT / "transcription_progress.json", progress)
        print(
            json.dumps(
                {
                    "asr": f"{index}/{len(sources)}",
                    "video_id": source["video_id"],
                    "status": result["status"],
                    "cues": result.get("cues"),
                    "sec": result.get("sec"),
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    summary = {
        "asr_model": ASR_LABEL,
        "model_path": str(MODEL_DIR),
        "source_count": len(sources),
        "status_counts": dict(Counter(row["status"] for row in results)),
        "total_cues": sum(int(row.get("cues") or 0) for row in results),
        "seed": seed,
        "sources": results,
    }
    write_json(OUT / "asr_summary.json", summary)
    return summary


def overlap(cue: dict[str, Any], start: float, end: float) -> float:
    return max(
        0.0,
        min(float(cue["end"]), end) - max(float(cue["start"]), start),
    )


def verify_target(
    clip_id: str,
    target: list[dict[str, Any]],
) -> dict[str, Any]:
    path = CLIPS / clip_id / "narration.jsonl"
    sentences = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = []
    for sentence in sentences:
        start = float(sentence.get("start_source") or 0)
        end = float(sentence.get("end_source") or start)
        hits = [cue for cue in target if overlap(cue, start, end) > 0]
        target_text = norm(" ".join(cue["text"] for cue in hits))
        text = str(sentence.get("text") or "")
        similarity = (
            difflib.SequenceMatcher(None, norm(text), target_text).ratio()
            if target_text
            else 0.0
        )
        rows.append(
            {
                "sentence_id": sentence.get("sentence_id"),
                "text": text,
                "start_source": start,
                "end_source": end,
                "matching_cue_ids": [cue["index"] for cue in hits],
                "text_similarity": round(similarity, 4),
                "time_overlap": bool(hits),
                "passes": bool(hits) and similarity >= SIMILARITY_THRESHOLD,
            }
        )
    passed = bool(rows) and all(row["passes"] for row in rows)
    return {
        "status": "pass" if passed else "needs_review",
        "threshold": SIMILARITY_THRESHOLD,
        "existing_narration_sentences": len(rows),
        "sentences": rows,
    }


def build_all(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary_rows = []
    for index, row in enumerate(rows, 1):
        clip_id = row["clip_id"]
        transcript_path = TRANSCRIPTS / row["video_id"] / "transcript.json"
        if not transcript_path.exists():
            summary_rows.append({**row, "status": "missing_transcript"})
            continue
        transcript = read_json(transcript_path)
        if transcript.get("asr_model") != ASR_LABEL:
            summary_rows.append({**row, "status": "wrong_asr_model"})
            continue
        cues = transcript["cues"]
        start = float(row["start"])
        end = float(row["end"])
        mask_start = max(0.0, start - MASK_PADDING_SECONDS)
        mask_end = end + MASK_PADDING_SECONDS
        original_target = [
            cue for cue in cues if overlap(cue, start, end) > 0
        ]
        masked_cues = [
            cue for cue in cues if overlap(cue, mask_start, mask_end) > 0
        ]
        mask_ids = {int(cue["index"]) for cue in masked_cues}
        context_cues = [
            cue for cue in cues if int(cue["index"]) not in mask_ids
        ]
        before = [
            cue for cue in cues if float(cue["end"]) <= mask_start
        ]
        after = [
            cue for cue in cues if float(cue["start"]) >= mask_end
        ]
        verification = verify_target(clip_id, masked_cues)
        context_availability = "available" if context_cues else "empty"
        included_in_context_arms = True
        if not context_cues:
            verification["status"] = "pass_empty_context"
            verification["context_empty_reason"] = (
                "No non-target ASR cue remains after the padded mask interval; "
                "the public context is intentionally the empty string."
            )
        payload = {
            "clip_id": clip_id,
            "family": row["family"],
            "video_id": row["video_id"],
            "source_url": row["Link"],
            "source_title": row["Title"],
            "target_window_source": {"start": start, "end": end},
            "target_mask_interval": {
                "start": round(mask_start, 3),
                "end": round(mask_end, 3),
                "padding_seconds": MASK_PADDING_SECONDS,
            },
            "target_masked": True,
            "context_availability": context_availability,
            "included_in_context_arms": included_in_context_arms,
            "contract_eligibility": {
                "V1": True,
                "V2": True,
                "V3": True,
                "V4": True,
            },
            "original_target_cue_ids": [cue["index"] for cue in original_target],
            "masked_cue_ids": sorted(mask_ids),
            "context_cue_ids": [cue["index"] for cue in context_cues],
            "context_before": before,
            "context_after": after,
            "all_non_target_cues": context_cues,
            "context_text_chronological": " ".join(
                cue["text"] for cue in context_cues
            ),
            "target_text_for_audit": " ".join(
                cue["text"] for cue in original_target
            ),
            "verification": verification,
            "transcript": {
                "asr_model": transcript.get("asr_model"),
                "model_path": transcript.get("model_path"),
                "source_media": transcript.get("source_media"),
                "cue_count": len(cues),
            },
            "token_estimate_char_div_4": round(
                len(" ".join(cue["text"] for cue in context_cues)) / 4
            ),
        }
        write_json(CONTEXTS / clip_id / "context_input.json", payload)
        write_json(CLIPS / clip_id / "context_input.json", payload)
        summary_rows.append(
            {
                "clip_id": clip_id,
                "family": row["family"],
                "video_id": row["video_id"],
                "source_title": row["Title"],
                "start": start,
                "end": end,
                "mask_start": round(mask_start, 3),
                "mask_end": round(mask_end, 3),
                "status": verification["status"],
                "context_availability": context_availability,
                "included_in_context_arms": included_in_context_arms,
                "original_target_cues": len(original_target),
                "masked_cues_with_padding": len(masked_cues),
                "context_cues": len(context_cues),
                "context_tokens_estimate": payload["token_estimate_char_div_4"],
            }
        )
        print(
            json.dumps(
                {
                    "build": f"{index}/{len(rows)}",
                    "clip_id": clip_id,
                    "status": verification["status"],
                },
                ensure_ascii=False,
            ),
            flush=True,
        )
    write_csv(OUT / "clip_context_summary.csv", summary_rows)
    counts = Counter(row.get("status", "unknown") for row in summary_rows)
    by_family = {
        family: dict(
            Counter(
                row.get("status", "unknown")
                for row in summary_rows
                if row.get("family") == family
            )
        )
        for family in FAMILIES
    }
    result = {
        "clip_count": len(summary_rows),
        "unique_source_video_count": len({row["video_id"] for row in rows}),
        "asr_model": ASR_LABEL,
        "mask_padding_seconds": MASK_PADDING_SECONDS,
        "status_counts": dict(counts),
        "status_by_family": by_family,
        "needs_review_clips": [
            row["clip_id"]
            for row in summary_rows
            if row.get("status") == "needs_review"
        ],
        "excluded_from_context_arms": [
            row["clip_id"]
            for row in summary_rows
            if row.get("status") == "excluded_no_context"
        ],
        "empty_context_clips": [
            row["clip_id"]
            for row in summary_rows
            if row.get("context_availability") == "empty"
        ],
        "avg_context_tokens_estimate": round(
            sum(int(row.get("context_tokens_estimate") or 0) for row in summary_rows)
            / max(len(summary_rows), 1)
        ),
        "max_context_tokens_estimate": max(
            (int(row.get("context_tokens_estimate") or 0) for row in summary_rows),
            default=0,
        ),
    }
    write_json(OUT / "summary.json", result)
    return result


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0].keys()) if rows else []
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def audit(rows: list[dict[str, Any]]) -> dict[str, Any]:
    issues = []
    family_counts = Counter(row["family"] for row in rows)
    source_to_asr = {}
    transcript_models = Counter()
    for source in unique_sources(rows):
        path = TRANSCRIPTS / source["video_id"] / "transcript.json"
        if not path.exists():
            issues.append(
                {"clip": None, "video_id": source["video_id"], "issue": "missing transcript"}
            )
            continue
        transcript = read_json(path)
        transcript_models[transcript.get("asr_model")] += 1
        source_to_asr[source["video_id"]] = transcript

    statuses = Counter()
    leak_clips = []
    missing_packages = []
    context_mismatch = []
    for row in rows:
        clip_id = row["clip_id"]
        central = CONTEXTS / clip_id / "context_input.json"
        synced = CLIPS / clip_id / "context_input.json"
        if not central.exists() or not synced.exists():
            missing_packages.append(clip_id)
            continue
        payload = read_json(central)
        statuses[(payload.get("verification") or {}).get("status")] += 1
        transcript = source_to_asr.get(payload["video_id"])
        if not transcript:
            continue
        start = float(payload["target_mask_interval"]["start"])
        end = float(payload["target_mask_interval"]["end"])
        expected_mask = {
            int(cue["index"])
            for cue in transcript["cues"]
            if overlap(cue, start, end) > 0
        }
        actual_mask = {int(value) for value in payload.get("masked_cue_ids") or []}
        context_ids = {
            int(cue["index"]) for cue in payload.get("all_non_target_cues") or []
        }
        if expected_mask != actual_mask:
            context_mismatch.append(clip_id)
        if actual_mask & context_ids:
            leak_clips.append(clip_id)
        expected_context = [
            cue["text"]
            for cue in transcript["cues"]
            if int(cue["index"]) not in expected_mask
        ]
        if expected_context != [
            cue["text"] for cue in payload.get("all_non_target_cues") or []
        ]:
            context_mismatch.append(clip_id)

    result = {
        "clip_count": len(rows),
        "family_counts": dict(family_counts),
        "transcript_count": len(source_to_asr),
        "transcript_models": dict(transcript_models),
        "verification_status_counts": dict(statuses),
        "missing_packages": sorted(set(missing_packages)),
        "mask_leaks": sorted(set(leak_clips)),
        "context_mismatches": sorted(set(context_mismatch)),
        "asr_issues": issues,
        "passed": (
            len(rows) == 340
            and family_counts == Counter({"bar": 153, "line": 92, "area": 34, "donut": 41, "pie": 20})
            and len(source_to_asr) == 85
            and transcript_models == Counter({ASR_LABEL: 85})
            and not missing_packages
            and not leak_clips
            and not context_mismatch
            and not issues
        ),
    }
    write_json(OUT / "audit.json", result)
    write_review_page(rows)
    write_review_markdown(result)
    return result


def write_review_markdown(audit_result: dict[str, Any]) -> None:
    summary = read_json(OUT / "summary.json") if (OUT / "summary.json").exists() else {}
    text = f"""# Uniform narration context audit

- Clips: {audit_result['clip_count']}
- Families: {json.dumps(audit_result['family_counts'], ensure_ascii=False)}
- Source transcripts: {audit_result['transcript_count']}
- ASR models: {json.dumps(audit_result['transcript_models'], ensure_ascii=False)}
- Mask padding: ±{MASK_PADDING_SECONDS:.1f}s
- Verification statuses: {json.dumps(audit_result['verification_status_counts'], ensure_ascii=False)}
- Mask leaks: {len(audit_result['mask_leaks'])}
- Context mismatches: {len(audit_result['context_mismatches'])}
- Missing packages: {len(audit_result['missing_packages'])}
- Audit passed: {audit_result['passed']}

## Corpus summary

```json
{json.dumps(summary, ensure_ascii=False, indent=2)}
```

Each clip package is written to both `clips/<clip_id>/context_input.json` and
`ok_5files_all/<clip_id>/context_input.json`.

## No-context policy

A source with no non-target narration uses the empty string as its context.
Empty context is a valid input, not missing data. Clips remain eligible for all
V1-V4 contracts. The current case is `line_90`; see `LINE90_DECISION.md`.
"""
    (OUT / "AUDIT.md").write_text(text, encoding="utf-8")


def write_review_page(rows: list[dict[str, Any]]) -> None:
    cards = []
    for row in rows:
        path = CONTEXTS / row["clip_id"] / "context_input.json"
        if not path.exists():
            continue
        payload = read_json(path)
        verification = payload.get("verification") or {}
        sentences = verification.get("sentences") or []
        sentence_html = "".join(
            f"<li><span class='sim'>{item.get('text_similarity')}</span> "
            f"{html.escape(item.get('text', ''))}</li>"
            for item in sentences
        )
        cards.append(
            f"""
<section data-search="{html.escape(row['clip_id'] + ' ' + row['Title'])}">
  <h2>{html.escape(row['clip_id'])}
    <span class="pill {html.escape(str(verification.get('status')))}">{html.escape(str(verification.get('status')))}</span>
  </h2>
  <p class="muted">{html.escape(row['Title'])} · {html.escape(row['video_id'])}</p>
  <p><strong>Source window:</strong> {row['start']:.2f}–{row['end']:.2f}s ·
    <strong>Masked:</strong> {payload['target_mask_interval']['start']:.2f}–{payload['target_mask_interval']['end']:.2f}s</p>
  <p><strong>Masked ASR:</strong> {html.escape(payload.get('target_text_for_audit', ''))}</p>
  <p><strong>Existing narration:</strong></p><ol>{sentence_html}</ol>
  <details><summary>Masked full context · {payload.get('token_estimate_char_div_4')} token est.</summary>
    <p>{html.escape(payload.get('context_text_chronological', ''))}</p>
  </details>
</section>"""
        )
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>340 uniform masked narration contexts</title>
<style>
body{{font-family:Inter,"Segoe UI",Arial,sans-serif;background:#f4f6f3;color:#17251e;margin:0}}
header{{position:sticky;top:0;background:#173f32;color:white;padding:18px 28px;z-index:2}}
input{{width:min(720px,90vw);padding:10px;border-radius:8px;border:0;margin-top:10px}}
main{{max-width:1250px;margin:auto;padding:20px}}
section{{background:white;border:1px solid #d8e1db;border-radius:12px;padding:16px;margin:14px 0}}
.muted{{color:#66756c;font-size:13px}}
.pill{{padding:3px 9px;border-radius:999px;font-size:12px;background:#dceee5;color:#12503d}}
.pill.needs_review{{background:#fde7c7;color:#7c3e00}}
.sim{{display:inline-block;min-width:48px;color:#476357}}
details p{{white-space:pre-wrap;line-height:1.55}}
</style></head><body>
<header><h1>340 clips · uniform Faster-Whisper context</h1>
<p>Target cues are removed as whole cues with ±1.5s boundary padding.</p>
<input id="q" placeholder="Search clip, title, or video id">
</header><main id="list">{''.join(cards)}</main>
<script>
const q=document.querySelector('#q');
q.addEventListener('input',()=>{{
  const value=q.value.toLowerCase();
  document.querySelectorAll('#list section').forEach(el=>{{
    el.style.display=el.dataset.search.toLowerCase().includes(value)?'block':'none';
  }});
}});
</script></body></html>"""
    (OUT / "review.html").write_text(document, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("seed", "download", "transcribe", "build", "audit", "all"),
    )
    args = parser.parse_args()
    rows = clip_rows()
    sources = unique_sources(rows)
    OUT.mkdir(parents=True, exist_ok=True)
    TRANSCRIPTS.mkdir(parents=True, exist_ok=True)
    if args.command == "seed":
        print(json.dumps(seed_legacy_transcripts(), ensure_ascii=False, indent=2))
    elif args.command == "download":
        print(json.dumps(download_missing(sources), ensure_ascii=False, indent=2))
    elif args.command == "transcribe":
        print(json.dumps(transcribe_all(sources), ensure_ascii=False, indent=2))
    elif args.command == "build":
        print(json.dumps(build_all(rows), ensure_ascii=False, indent=2))
    elif args.command == "audit":
        print(json.dumps(audit(rows), ensure_ascii=False, indent=2))
    else:
        seed_legacy_transcripts()
        missing = [source for source in sources if not local_media(source["video_id"])]
        if missing:
            download_missing(missing)
        transcribe_all(sources)
        build_all(rows)
        print(json.dumps(audit(rows), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
