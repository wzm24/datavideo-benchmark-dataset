from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(r"D:\dev\data_video_dataset_pipeline\data\generated\ok_5files_all")


def basis_item(row: dict) -> dict:
    item = {
        "field": "value",
        "value": row.get("value", ""),
        "unit": row.get("unit", ""),
    }
    for key in ("entity", "series", "x", "year", "metric", "label"):
        value = (row.get(key) or "").strip()
        if value:
            item[key] = value
    return item


def selected_rows(rows: list[dict]) -> tuple[list[dict], str]:
    if any("role" in row for row in rows):
        return [row for row in rows if row.get("role") == "bar"], "all role=bar rows"
    return rows, "all data rows (table has no role column)"


def completeness_unit(unit_id: str, state: str | None, rows: list[dict]) -> dict:
    count = len(rows)
    if state is None:
        claim = f"All {count} required bar marks or stacked segments appear in the final chart."
        state_phrase = "the final chart state"
    else:
        claim = f"All {count} required bar marks or stacked segments appear in state {state}."
        state_phrase = f"state {state}"
    return {
        "id": unit_id,
        "requirement_id": "R1",
        "unit_kind": "visual_completeness",
        "must_be_visualized": True,
        "claim": claim,
        "basis": [basis_item(row) for row in rows],
        "accept": [
            f"all {count} required data marks are visible in {state_phrase}",
            "every grouped bar and every stacked segment is present"
            if any(row.get("series") for row in rows)
            else "every required bar is present",
        ],
        "reject": [
            "omitting any required bar or stacked segment",
            "showing only selected endpoint bars",
            "replacing missing marks with a summary total or subtitle",
        ],
        "evidence": f"All G0-required marks for {state_phrase} are visible and identifiable.",
    }


def row_state(row: dict) -> str | None:
    for key in ("x", "year", "state"):
        value = (row.get(key) or "").strip()
        if value:
            return value
    return None


def renumber_semantic_units(
    requirements: list[dict],
    units: list[dict],
    completeness_count: int,
    hardcases: list[dict],
) -> tuple[list[dict], list[dict], list[dict]]:
    unit_id_map = {
        unit["id"]: f"U{index + completeness_count + 1}"
        for index, unit in enumerate(units)
    }
    requirement_id_map = {
        requirement["id"]: f"R{index + 2}"
        for index, requirement in enumerate(requirements)
    }
    new_units = []
    for unit in units:
        clone = dict(unit)
        clone["id"] = unit_id_map[unit["id"]]
        clone["requirement_id"] = requirement_id_map.get(
            unit.get("requirement_id"), unit.get("requirement_id")
        )
        new_units.append(clone)

    new_requirements = []
    for index, requirement in enumerate(requirements):
        clone = dict(requirement)
        clone["id"] = requirement_id_map[requirement["id"]]
        clone["unit_ids"] = [
            unit_id_map[unit_id] for unit_id in requirement.get("unit_ids", [])
        ]
        new_requirements.append(clone)

    new_hardcases = []
    for hardcase in hardcases:
        clone = dict(hardcase)
        old_id = clone.get("unit_id")
        if old_id in unit_id_map:
            clone["unit_id"] = unit_id_map[old_id]
        new_hardcases.append(clone)
    return new_requirements, new_units, new_hardcases


def add_completeness(clip: str) -> None:
    d = ROOT / clip
    path = d / "g1.json"
    g1 = json.loads(path.read_text(encoding="utf-8"))
    with (d / "data_table.csv").open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    required_rows, selection = selected_rows(rows)
    count = len(required_rows)
    g0 = dict(g1.get("g0_data_completeness", {}))
    mode = g0.get("mode", "static_all_at_once")
    states = g0.get("required_states", [])
    per_state = g0.get("required_marks_per_state", {})

    semantic_requirements = [
        requirement
        for requirement in g1.get("requirements", [])
        if not any(
            unit.get("id") in requirement.get("unit_ids", [])
            and unit.get("unit_kind") == "visual_completeness"
            for unit in g1.get("units", [])
        )
    ]
    semantic_units = [
        unit for unit in g1.get("units", []) if unit.get("unit_kind") != "visual_completeness"
    ]

    if mode == "state_sequence":
        grouped = {state: [] for state in states}
        for row in required_rows:
            state = row_state(row)
            if state in grouped:
                grouped[state].append(row)
        completeness_rows = [
            (f"U{index + 1}", state, grouped[state])
            for index, state in enumerate(states)
        ]
        if any(not rows_for_state for _, _, rows_for_state in completeness_rows):
            raise ValueError(f"{clip}: could not reconstruct all required states")
    else:
        completeness_rows = [("U1", None, required_rows)]

    completeness_units = [
        completeness_unit(unit_id, state, unit_rows)
        for unit_id, state, unit_rows in completeness_rows
    ]
    completeness_count = len(completeness_units)
    new_requirements, new_units, new_hardcases = renumber_semantic_units(
        semantic_requirements,
        semantic_units,
        completeness_count,
        g1.get("hardcases", []),
    )
    requirement = {
        "id": "R1",
        "question": "How does the video present the required bars in this chart?",
        "relation": "all_of" if len(completeness_units) > 1 else "single",
        "unit_ids": [unit["id"] for unit in completeness_units],
        "scope": {
            "selection": selection,
            "required_data_rows": count,
            "required_states": states,
            "required_marks_per_state": per_state,
        },
    }

    g1["requirements"] = [requirement] + new_requirements
    g1["units"] = completeness_units + new_units
    g1["weight_mode"] = "uniform_over_units"
    g1["unit_weights"] = {
        u["id"]: round(1 / len(g1["units"]), 10) for u in g1["units"]
    }
    g0.update({
        "required": True,
        "selection": selection,
        "required_data_rows": count,
        "evaluated_in": "G1_R1_completeness_units_and_G2_mark_presence",
        "g1_requirement_id": "R1",
        "g1_unit_ids": [unit["id"] for unit in completeness_units],
    })
    g1["g0_data_completeness"] = g0
    g1["hardcases"] = new_hardcases
    g1["version"] = "g1_r_u_v4"
    flags = list(g1.get("review_flags", []))
    flags = [flag for flag in flags if flag != "completeness_as_g1_unit_2026-10-22"]
    if "state_level_completeness_r1_2026-10-22" not in flags:
        flags.append("state_level_completeness_r1_2026-10-22")
    g1["review_flags"] = flags
    path.write_text(json.dumps(g1, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def main() -> None:
    clips = sorted(
        (d for d in ROOT.iterdir() if d.is_dir() and d.name.startswith("bar_")),
        key=lambda d: int(d.name.split("_")[1]),
    )
    for d in clips:
        add_completeness(d.name)
    print(f"added R1 completeness units to {len(clips)} bar clips")


if __name__ == "__main__":
    main()
