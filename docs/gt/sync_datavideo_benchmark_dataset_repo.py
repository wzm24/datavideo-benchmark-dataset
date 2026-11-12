"""Sync finalized text/GT/context assets to the dedicated GitHub dataset clone."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from pathlib import Path


ROOT = Path(r"D:\dev\data_video_dataset_pipeline")
SOURCE = ROOT / "data" / "generated" / "ok_5files_all"
TARGET = Path(r"D:\dev\datavideo-benchmark-dataset")
CONTEXTS = ROOT / "benchmark_draft" / "full_narration_context_uniform_20261112"
TRANSCRIPTS = ROOT / "data" / "processed" / "_full_uniform_whisper_small_20261112"
AREA_INTENT = ROOT / "benchmark_draft" / "area_intent"
GT_FINAL = ROOT / "benchmark_draft" / "gt" / "finalization_20261112"
PROTOCOL_DIR = ROOT / "benchmark_draft" / "gt"

PER_CLIP_FILES = (
    "clip.mp4",
    "keyframe.png",
    "semantic.svg",
    "data_table.csv",
    "data_table.sidecar.csv",
    "narration.jsonl",
    "chart_spec.json",
    "input_spec.json",
    "g0.json",
    "g1.json",
    "g2.json",
    "g3.json",
    "intent.json",
    "context_input.json",
)
OBSOLETE_PER_CLIP_FILES = (
    "g1_draft_b2.json",
    "g2_evidence.json",
    "intent_candidate.json",
    "g1_candidate.json",
    "narrative_goal_candidate.json",
)
FAMILIES = ("bar", "line", "area", "donut", "pie")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_if_changed(source: Path, target: Path) -> bool:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if source.stat().st_size == target.stat().st_size:
            if sha256(source) == sha256(target):
                return False
    shutil.copy2(source, target)
    return True


def copy_tree(source: Path, target: Path) -> int:
    changed = 0
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if copy_if_changed(path, target / relative):
            changed += 1
    return changed


def clip_dirs() -> list[Path]:
    return sorted(
        (
            path
            for path in SOURCE.iterdir()
            if path.is_dir()
            and re.fullmatch(r"(?:bar|line|area|donut|pie)_\d+", path.name)
        ),
        key=lambda path: (
            FAMILIES.index(path.name.split("_", 1)[0]),
            int(path.name.rsplit("_", 1)[1]),
        ),
    )


def main() -> None:
    if not (TARGET / ".git").exists():
        raise RuntimeError(f"dataset clone not found: {TARGET}")
    changed = []
    removed = []
    manifest = []
    clip_rows = []

    for clip in clip_dirs():
        target_dir = TARGET / clip.name
        target_dir.mkdir(parents=True, exist_ok=True)
        present = []
        for filename in PER_CLIP_FILES:
            source = clip / filename
            if not source.exists():
                continue
            target = target_dir / filename
            if copy_if_changed(source, target):
                changed.append(str(target.relative_to(TARGET)))
            present.append(filename)
            manifest.append(
                {
                    "clip": clip.name,
                    "family": clip.name.split("_", 1)[0],
                    "file": filename,
                    "bytes": source.stat().st_size,
                    "sha256": sha256(source),
                }
            )
        for filename in OBSOLETE_PER_CLIP_FILES:
            obsolete = target_dir / filename
            if obsolete.exists():
                obsolete.unlink()
                removed.append(str(obsolete.relative_to(TARGET)))
        clip_rows.append(
            {
                "clip": clip.name,
                "family": clip.name.split("_", 1)[0],
                "files": len(present),
                "has_context": int("context_input.json" in present),
                "has_g1": int("g1.json" in present),
                "has_g2": int("g2.json" in present),
                "has_g3": int("g3.json" in present),
            }
        )

    docs = TARGET / "docs"
    audits = TARGET / "audits"
    pipeline = TARGET / "pipeline"
    contexts = TARGET / "contexts"
    for path in (
        docs,
        audits,
        pipeline,
        contexts / "audit",
        contexts / "transcripts",
        contexts / "area_intent",
    ):
        path.mkdir(parents=True, exist_ok=True)

    copied_extra = {}
    copied_extra["protocol"] = copy_tree(
        PROTOCOL_DIR,
        docs / "gt",
    )
    # Keep the finalization code and reports but not all historical gt scripts.
    for name in (
        "evaluation_protocol.md",
        "evaluation_contract_v2_20261105.md",
        "INPUT_CONTRACTS_V2.md",
        "finalize_area_gt_and_approve_g1.py",
    ):
        source = PROTOCOL_DIR / name
        if source.exists():
            copy_if_changed(source, docs / "gt" / name)

    for name in (
        "summary.json",
        "asr_summary.json",
        "audit.json",
        "summary.json",
        "clip_context_summary.csv",
        "AUDIT.md",
        "LINE90_DECISION.md",
        "build_uniform_context.py",
        "review.html",
    ):
        source = CONTEXTS / name
        if source.exists():
            copy_if_changed(source, contexts / "audit" / name)

    copied_extra["transcripts"] = copy_tree(
        TRANSCRIPTS,
        contexts / "transcripts",
    )
    copied_extra["area_intent"] = copy_tree(
        AREA_INTENT,
        contexts / "area_intent",
    )
    for name in ("summary.json", "g1_approval_audit.json", "area_g2_g3_audit.json"):
        source = GT_FINAL / name
        if source.exists():
            copy_if_changed(source, audits / "gt_finalization" / name)

    release_note = f"""# Dataset release 2026-11-12

This release contains 340 clips:

| Family | Clips |
|---|---:|
| bar | 153 |
| line | 92 |
| area | 34 |
| donut | 41 |
| pie | 20 |

Every clip includes the finalized public `intent.json`, `g0.json`, `g1.json`,
`g2.json`, `g3.json`, and `context_input.json`, together with clip media,
keyframe, confirmed SVG, narration, data table, and chart specification.

- G1: 340/340 approved after human sampling review.
- G2/G3: 340/340, with each unit ID matching its corresponding G1 unit.
- Area: 34/34 formal G2/G3 generated from the approved G1.
- Context: 340/340 masked with a uniform Faster-Whisper-small transcript.
- Source videos: 85.
- Target mask: whole overlapping cues removed with 1.5-second boundary padding.
- `line_90`: valid empty context; all remaining target cues are masked.

The repository stores original clip videos and text assets. Full minute-level
source videos/audio are not committed; their uniform ASR transcripts and masked
context packages are included under `contexts/`.

See:

- `audits/gt_finalization/summary.json`
- `contexts/audit/summary.json`
- `contexts/audit/audit.json`
- `contexts/area_intent/AREA_GT_PIPELINE.md`
- `docs/gt/evaluation_contract_v2_20261105.md`
"""
    (TARGET / "RELEASE_20261112.md").write_text(release_note, encoding="utf-8")

    with (TARGET / "DATASET_MANIFEST.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("clip", "family", "file", "bytes", "sha256"),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(manifest)

    with (TARGET / "CLIP_INDEX.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "clip",
                "family",
                "files",
                "has_context",
                "has_g1",
                "has_g2",
                "has_g3",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(clip_rows)

    summary = {
        "clips": len(clip_rows),
        "families": {
            family: sum(row["family"] == family for row in clip_rows)
            for family in FAMILIES
        },
        "changed_files": len(changed),
        "removed_obsolete_files": len(removed),
        "extra_tree_copies": copied_extra,
        "cross_family_checks": {
            "context_340": sum(row["has_context"] for row in clip_rows) == 340,
            "g1_340": sum(row["has_g1"] for row in clip_rows) == 340,
            "g2_340": sum(row["has_g2"] for row in clip_rows) == 340,
            "g3_340": sum(row["has_g3"] for row in clip_rows) == 340,
        },
        "manifest_rows": len(manifest),
    }
    (TARGET / "SYNC_SUMMARY.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
