"""Align the three G1/G2 visual-flag conflicts before the corrected V1 run."""

from __future__ import annotations

import json
import shutil
from pathlib import Path


ROOT = Path(r"D:\dev\data_video_dataset_pipeline")
DATASET = ROOT / "data" / "generated" / "ok_5files_all"
BACKUP = ROOT / "data" / "generated" / "_gt_backup" / "flag_conflicts_20261029"
TARGETS = {
    "bar_28": {"U4", "U5"},
    "bar_69": {"U3"},
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    for clip, unit_ids in TARGETS.items():
        clip_dir = DATASET / clip
        backup_dir = BACKUP / clip
        backup_dir.mkdir(parents=True, exist_ok=True)
        for name in ("g1.json", "g2.json", "g3.json"):
            source = clip_dir / name
            target = backup_dir / name
            if not target.exists():
                shutil.copy2(source, target)

        g2 = load(clip_dir / "g2.json")
        g2_by_id = {
            item.get("unit_id"): item for item in g2.get("unit_evidence") or []
        }
        for unit_id in unit_ids:
            if (g2_by_id.get(unit_id) or {}).get("must_be_visualized") is not False:
                raise RuntimeError(f"{clip}/{unit_id}: G2 is not narration-only")

        g1 = load(clip_dir / "g1.json")
        for unit in g1.get("units") or []:
            if unit.get("id") in unit_ids:
                unit["must_be_visualized"] = False
                unit["visual_obligation_source"] = "g2_narration_only_hardcase"
        flags = g1.setdefault("review_flags", [])
        if "visual_flags_aligned_to_g2_20261029" not in flags:
            flags.append("visual_flags_aligned_to_g2_20261029")
        write(clip_dir / "g1.json", g1)

        g3 = load(clip_dir / "g3.json")
        for unit in g3.get("units") or []:
            if unit.get("unit_id") in unit_ids:
                unit["applies"] = False
                unit["not_applicable_reason"] = (
                    "G2 marks this hardcase as narration-only; visual timing is not required."
                )
        write(clip_dir / "g3.json", g3)
        print(f"{clip}: aligned {', '.join(sorted(unit_ids))}")


if __name__ == "__main__":
    main()
