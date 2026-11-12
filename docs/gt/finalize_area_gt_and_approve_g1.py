"""Approve all G1 files and materialize area G2/G3 from approved G1."""

from __future__ import annotations

import json
import re
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(r"D:\dev\data_video_dataset_pipeline")
DATASET = ROOT / "data" / "generated" / "ok_5files_all"
BACKUP = ROOT / "data" / "generated" / "_gt_backup" / "g1_approval_area_g2g3_20261112"
OUT = ROOT / "benchmark_draft" / "gt" / "finalization_20261112"
APPROVED_AT = "2026-11-12"
APPROVED_BY = "human_sampling_approval_2026-11-12"
AREA_INTENT_SCHEMA = "area_intent_v1_2026-11-12"
G1_SCHEMA = "g1_approved_2026-11-12"
G2_SCHEMA = "g2_area_visual_evidence_v1_2026-11-12"
G3_SCHEMA = "g3_area_temporal_policy_v1_2026-11-12"


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: Any, backup: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if backup and path.exists():
        relative = path.relative_to(DATASET)
        target = BACKUP / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(path, target)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )


def clip_dirs() -> list[Path]:
    return sorted(
        (
            path
            for path in DATASET.iterdir()
            if path.is_dir()
            and re.fullmatch(r"(?:bar|line|area|donut|pie)_\d+", path.name)
        ),
        key=lambda path: (
            ("bar", "line", "area", "donut", "pie").index(
                path.name.split("_", 1)[0]
            ),
            int(path.name.rsplit("_", 1)[1]),
        ),
    )


def approve_g1(clip: Path) -> dict[str, Any]:
    official = clip / "g1.json"
    candidate = clip / "g1_candidate.json"
    source = official if official.exists() else candidate
    if not source.exists():
        raise FileNotFoundError(f"{clip.name}: no G1 file")
    g1 = read_json(source)
    g1["status"] = "approved"
    g1["approved_by"] = APPROVED_BY
    g1["approved_at"] = APPROVED_AT
    g1["approval_basis"] = (
        "Human sampling review completed; remaining items approved as a batch."
    )
    g1["input_contract"] = g1.get("input_contract") or "V1"
    g1["input_materials"] = g1.get("input_materials") or [
        "intent_en",
        "data_table.csv",
        "chart_spec.json",
    ]
    flags = g1.setdefault("review_flags", [])
    if "g1_batch_approved_after_human_sampling_2026_11_12" not in flags:
        flags.append("g1_batch_approved_after_human_sampling_2026_11_12")
    for unit in g1.get("units") or []:
        unit["needs_review"] = False
        if isinstance(unit.get("review"), dict):
            unit["review"]["decision"] = unit["review"].get("decision") or "approved"
            unit["review"]["reviewer"] = (
                unit["review"].get("reviewer") or APPROVED_BY
            )
            unit["review"]["adjudicated"] = True
    write_json(official, g1, backup=True)
    if candidate.exists() and candidate != source:
        candidate_payload = read_json(candidate)
        candidate_payload["status"] = "approved"
        candidate_payload["approved_by"] = APPROVED_BY
        candidate_payload["approved_at"] = APPROVED_AT
        write_json(candidate, candidate_payload, backup=True)
    return g1


def approve_area_intent(clip: Path) -> dict[str, Any]:
    candidate_path = clip / "intent_candidate.json"
    if not candidate_path.exists():
        raise FileNotFoundError(f"{clip.name}: area intent_candidate.json missing")
    candidate = read_json(candidate_path)
    audit = candidate.get("protocol_audit") or {}
    mechanical = candidate.get("mechanical_checks") or {}
    narrative_goal = clean(candidate.get("narrative_goal"))
    intent = clean(candidate.get("proposed_intent"))
    if not narrative_goal or not intent:
        raise RuntimeError(f"{clip.name}: empty area goal/intent")
    payload = {
        "clip_id": clip.name,
        "narrative_goal": narrative_goal,
        "intent_en": intent,
        "intent_language": "en",
        "narrative_goal_role": "answer_bearing_internal_story_goal",
        "intent_role": "neutral_public_generation_input",
        "public_input_field": "intent_en",
        "narrative_goal_review_status": "approved",
        "intent_review_status": "approved",
        "protocol_intent_status": (
            "protocol_compliant"
            if audit.get("protocol_compliant")
            and audit.get("answer_leak") is False
            else "approved_after_sampling_review"
        ),
        "leak_check": {
            "contains_answer_values": not (
                audit.get("answer_leak") is False
            ),
            "non_year_numbers": mechanical.get("non_year_numbers") or [],
            "answer_pattern_matches": mechanical.get("answer_pattern_matches") or [],
            "scope_complete": audit.get("scope_complete"),
            "supported_by_inputs": audit.get("supported_by_inputs"),
        },
        "narrative_goal_evidence": [
            "narration",
            "semantic_svg",
            "data_table",
        ],
        "intent_source": [
            "narrative_goal",
            "data_table",
            "semantic_svg",
        ],
        "schema_version": AREA_INTENT_SCHEMA,
        "approved_by": APPROVED_BY,
        "approved_at": APPROVED_AT,
        "candidate_record": candidate,
    }
    write_json(clip / "intent.json", payload, backup=True)
    candidate["status"] = "approved"
    candidate["approved_by"] = APPROVED_BY
    candidate["approved_at"] = APPROVED_AT
    write_json(candidate_path, candidate, backup=True)
    return payload


ENCODING_BY_SUBTYPE = {
    "simple_area": "filled_area_boundary_height",
    "overlay_area": "independent_filled_area_boundaries",
    "two_panel_area": "filled_area_boundary_height_per_panel",
    "stacked_area": "stacked_band_thickness",
    "multi_area_overlay": "independent_filled_area_boundaries",
    "normalized_timeline_area": "normalized_curve_height",
    "mirrored_age_distribution_panels": "horizontal_profile_width_by_age",
    "proportional_circle_size": "circle_diameter",
    "proportional_circle_area": "circle_area",
    "proportional_square_area": "square_area",
    "proportional_sphere_volume": "sphere_volume",
    "historical_projection_area": "historical_area_and_projection_band",
    "distribution_area_with_highlight": "distribution_profile_and_highlighted_region",
    "single_value_callout": "printed_value_callout",
    "annual_area": "filled_area_boundary_height",
    "area_tile_map": "tile_count_share",
}


def mark_label(item: dict[str, Any]) -> str:
    parts = [
        clean(item.get("panel")),
        clean(item.get("entity")) or clean(item.get("series")),
    ]
    x = clean(item.get("x"))
    if x:
        parts.append(x)
    elif clean(item.get("point_order")):
        parts.append(f"#{clean(item.get('point_order'))}")
    return " | ".join(part for part in parts if part) or "unnamed area mark"


def evidence_routes(spec: dict[str, Any], role: str) -> list[str]:
    subtype = clean(spec.get("sub_type"))
    routes = ["readable_label", "explicit_annotation"]
    if role == "reference_line":
        return ["reference_line_geometry", *routes]
    if subtype == "area_tile_map":
        return ["tile_count", *routes]
    if subtype == "proportional_square_area":
        return ["square_area_geometry", *routes]
    if subtype == "proportional_circle_size":
        return ["circle_diameter_geometry", *routes]
    if subtype == "proportional_circle_area":
        return ["circle_area_geometry", *routes]
    if subtype == "proportional_sphere_volume":
        return ["sphere_volume_geometry", *routes]
    if subtype == "single_value_callout":
        return ["visible_printed_value", *routes]
    if subtype == "stacked_area":
        return ["stacked_band_geometry", *routes]
    return ["area_boundary_geometry", *routes]


def build_g2(
    clip: Path,
    spec: dict[str, Any],
    g1: dict[str, Any],
) -> dict[str, Any]:
    evidence = []
    for unit in g1.get("units") or []:
        basis = unit.get("basis") or []
        marks = list(
            dict.fromkeys(mark_label(item) for item in basis)
        )
        role = next(
            (
                clean(item.get("role"))
                for item in basis
                if clean(item.get("role"))
            ),
            "",
        )
        kind = clean(unit.get("unit_kind"))
        if kind == "visual_completeness":
            evidence_type = "complete_area_mark_set"
            assertion = {
                "all_required_marks_present": True,
                "required_mark_count": len(marks),
                "panel_scoped": any(clean(item.get("panel")) for item in basis),
                "required_marks": [
                    {
                        "mark": mark_label(item),
                        "panel": clean(item.get("panel")),
                        "entity": clean(item.get("entity")),
                        "series": clean(item.get("series")),
                        "role": clean(item.get("role")),
                    }
                    for item in basis
                ],
            }
        elif kind in {
            "comparison",
            "change",
            "trend",
            "extremum",
            "ranking",
            "threshold_or_crossing",
            "projection_or_range",
            "proportional_comparison",
            "share_or_composition",
        }:
            evidence_type = kind
            assertion = {
                "marks": [
                    {
                        "mark": mark_label(item),
                        "panel": clean(item.get("panel")),
                        "entity": clean(item.get("entity")),
                        "series": clean(item.get("series")),
                        "x": clean(item.get("x")),
                        "point_order": clean(item.get("point_order")),
                        "value": clean(item.get("value")),
                        "unit": clean(item.get("unit")),
                        "role": clean(item.get("role")),
                    }
                    for item in basis
                ],
                "expected_relation": clean(unit.get("claim")),
                "computation": clean(unit.get("computation")) or "none",
                "encoding": ENCODING_BY_SUBTYPE.get(
                    clean(spec.get("sub_type")),
                    "semantic_area_geometry",
                ),
                "axis_condition": {
                    "x_axis": clean(
                        next(
                            (
                                item.get("x_axis")
                                for item in basis
                                if clean(item.get("x_axis"))
                            ),
                            "",
                        )
                    ),
                    "y_axis": clean(
                        next(
                            (
                                item.get("y_axis")
                                for item in basis
                                if clean(item.get("y_axis"))
                            ),
                            "",
                        )
                    ),
                },
            }
            if clean(spec.get("sub_type")) == "area_tile_map":
                assertion["tile_counts"] = spec.get("tile_counts") or {}
                assertion["total_tiles"] = spec.get("total_tiles")
        elif kind == "identity":
            evidence_type = "semantic_identity"
            assertion = {
                "identities": [
                    {
                        "mark": mark_label(item),
                        "entity": clean(item.get("entity")),
                        "series": clean(item.get("series")),
                        "role": clean(item.get("role")),
                    }
                    for item in basis
                ],
                "label_must_be_readable": True,
            }
        else:
            evidence_type = kind or "semantic_area_evidence"
            assertion = {
                "marks": [
                    {
                        "mark": mark_label(item),
                        "value": clean(item.get("value")),
                        "unit": clean(item.get("unit")),
                    }
                    for item in basis
                ],
                "expected_relation": clean(unit.get("claim")),
            }
        evidence.append(
            {
                "unit_id": unit["id"],
                "unit_kind": kind,
                "must_be_visualized": bool(unit.get("must_be_visualized", True)),
                "evidence_type": evidence_type,
                "required_marks": marks,
                "assertion": assertion,
                "accepted_routes": evidence_routes(spec, role),
                "reject": unit.get("reject") or [],
                "tolerance": {
                    "printed_value_relative": 0.02,
                    "geometry_relative": 0.05,
                    "label_text": "normalized_exact_or_semantically_equivalent",
                },
                "completeness_ref": (
                    "G1_R1" if kind == "visual_completeness" else None
                ),
                "needs_review": False,
            }
        )
    return {
        "clip_id": clip.name,
        "family": "area",
        "version": G2_SCHEMA,
        "status": "approved",
        "source_g1": "g1.json",
        "chart_input": {
            "clip_id": clip.name,
            "family": "area",
            "sub_type": spec.get("sub_type"),
            "orientation": spec.get("orientation"),
            "panel_count": spec.get("panel_count"),
            "series_count": spec.get("series_count"),
            "time_behavior": spec.get("time_behavior"),
            "special_area_type": spec.get("special_area_type"),
        },
        "completeness": g1.get("g0_data_completeness") or {},
        "unit_evidence": evidence,
        "approved_by": APPROVED_BY,
        "approved_at": APPROVED_AT,
    }


def temporal_rule(kind: str) -> tuple[str, str, str, str]:
    if kind == "visual_completeness":
        return (
            "whole_video_completion",
            "last_required_area_mark_visible",
            "all required area marks are in completed, identifiable states",
            "all_required_marks_present_by_anchor",
        )
    if kind in {"comparison", "extremum", "ranking"}:
        return (
            "generated_narration",
            "sentence_that_completes_unit",
            "all compared marks are visible at their completed values and a common scale or readable labels support the relation",
            "evidence_complete_before_conclusion",
        )
    if kind in {"trend", "change"}:
        return (
            "generated_narration",
            "sentence_that_completes_unit",
            "the required path or endpoints are sufficiently drawn to support the claimed direction and change",
            "evidence_complete_before_conclusion",
        )
    if kind == "threshold_or_crossing":
        return (
            "generated_narration",
            "sentence_that_completes_unit",
            "the relevant series and threshold/crossing state are visible at a completed animation state",
            "evidence_complete_before_conclusion",
        )
    if kind == "projection_or_range":
        return (
            "generated_narration",
            "sentence_that_completes_unit",
            "historical and projected endpoints plus the uncertainty range or band are visible",
            "evidence_complete_before_conclusion",
        )
    if kind in {"proportional_comparison", "share_or_composition"}:
        return (
            "generated_narration",
            "sentence_that_completes_unit",
            "all proportional marks have reached their completed encoding and remain identifiable",
            "evidence_complete_before_conclusion",
        )
    return (
        "generated_narration",
        "sentence_that_completes_unit",
        "the required semantic identity and visual evidence are readable",
        "no_additional_order_requirement",
    )


def build_g3(g1: dict[str, Any]) -> dict[str, Any]:
    units = []
    for unit in g1.get("units") or []:
        kind = clean(unit.get("unit_kind"))
        anchor_mode, selector, ready, ordering = temporal_rule(kind)
        units.append(
            {
                "unit_id": unit["id"],
                "applies": bool(unit.get("must_be_visualized", True)),
                "anchor_mode": anchor_mode,
                "anchor_selector": selector,
                "ready_condition": ready,
                "window_before_s": 1.0,
                "window_after_s": 1.5,
                "dwell_min_s": 0.0
                if kind == "visual_completeness"
                else 0.8,
                "ordering": ordering,
                "identity": "entity_and_series_binding_must_remain_stable",
                "transition": (
                    "ignore_mid_animation_geometry; judge_completed_area_state"
                    if kind != "visual_completeness"
                    else "evaluate_required_mark_set_at_completion"
                ),
            }
        )
    return {
        "clip_id": g1["clip_id"],
        "family": "area",
        "version": G3_SCHEMA,
        "status": "approved",
        "narration_source": "model_generated",
        "policy_status": "approved_rule_pending_g4_calibration",
        "units": units,
        "calibration_note": (
            "Window and dwell values follow the current contract and still require "
            "G4 calibration; they are not evidence from the reference video."
        ),
        "approved_by": APPROVED_BY,
        "approved_at": APPROVED_AT,
    }


def validate_area(
    clip: Path,
    intent: dict[str, Any],
    g1: dict[str, Any],
    g2: dict[str, Any],
    g3: dict[str, Any],
) -> list[str]:
    issues = []
    if intent.get("intent_review_status") != "approved":
        issues.append("intent not approved")
    if not clean(intent.get("intent_en")):
        issues.append("empty intent_en")
    if g1.get("status") != "approved":
        issues.append("G1 not approved")
    unit_ids = [unit.get("id") for unit in g1.get("units") or []]
    if len(unit_ids) != len(set(unit_ids)):
        issues.append("duplicate G1 unit ids")
    g2_ids = [unit.get("unit_id") for unit in g2.get("unit_evidence") or []]
    g3_ids = [unit.get("unit_id") for unit in g3.get("units") or []]
    if set(g2_ids) != set(unit_ids):
        issues.append("G2 does not cover G1 units")
    if set(g3_ids) != set(unit_ids):
        issues.append("G3 does not cover G1 units")
    for evidence in g2.get("unit_evidence") or []:
        if not evidence.get("required_marks"):
            issues.append(f"{evidence.get('unit_id')}: empty required_marks")
        if not evidence.get("accepted_routes"):
            issues.append(f"{evidence.get('unit_id')}: empty accepted_routes")
    return issues


def main() -> None:
    BACKUP.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    clips = clip_dirs()
    approval_rows = []
    area_rows = []
    issues = []

    for clip in clips:
        g1 = approve_g1(clip)
        approval_rows.append(
            {
                "clip": clip.name,
                "family": clip.name.split("_", 1)[0],
                "status": g1.get("status"),
                "units": len(g1.get("units") or []),
            }
        )
        if not clip.name.startswith("area_"):
            continue
        intent = approve_area_intent(clip)
        spec = read_json(clip / "chart_spec.json")
        spec["needs_review"] = False
        spec["batch_status"] = "approved"
        write_json(clip / "chart_spec.json", spec, backup=True)
        g2 = build_g2(clip, spec, g1)
        g3 = build_g3(g1)
        write_json(clip / "g2.json", g2, backup=True)
        write_json(clip / "g3.json", g3, backup=True)
        clip_issues = validate_area(clip, intent, g1, g2, g3)
        if clip_issues:
            issues.append({"clip": clip.name, "issues": clip_issues})
        area_rows.append(
            {
                "clip": clip.name,
                "intent": "approved",
                "g1_units": len(g1.get("units") or []),
                "g2_units": len(g2.get("unit_evidence") or []),
                "g3_units": len(g3.get("units") or []),
                "status": "pass" if not clip_issues else "failed",
            }
        )
        print(
            json.dumps(
                {
                    "clip": clip.name,
                    "g1_units": len(g1.get("units") or []),
                    "status": "pass" if not clip_issues else "failed",
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    summary = {
        "approved_at": APPROVED_AT,
        "g1_approved_clips": len(approval_rows),
        "g1_status_counts": dict(Counter(row["status"] for row in approval_rows)),
        "area_clips": len(area_rows),
        "area_status_counts": dict(Counter(row["status"] for row in area_rows)),
        "area_g2_units": sum(row["g2_units"] for row in area_rows),
        "area_g3_units": sum(row["g3_units"] for row in area_rows),
        "issues": issues,
        "backup": str(BACKUP),
    }
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "g1_approval_audit.json", approval_rows)
    write_json(OUT / "area_g2_g3_audit.json", area_rows)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if issues:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
