from __future__ import annotations

import copy
import csv
import json
from pathlib import Path


ROOT = Path(r"D:\dev\data_video_dataset_pipeline\data\generated\ok_5files_all")


# Row indices refer to the current, human-approved data_table.csv.  Only
# structural G1 fields are added; claims, accept/reject text and weights remain
# unchanged.
BAR_1_34_LAYOUT = {
    1: {
        "U1": ("key_value_endpoint", True, [0]),
        "U2": ("key_value_endpoint", True, [1]),
        "U3": ("key_value_endpoint", True, [2]),
        "U4": ("trend_or_order", True, [0, 1, 2]),
    },
    2: {
        "U1": ("trend_or_change", True, list(range(8))),
        "U2": ("trend_or_order", True, list(range(8))),
    },
    3: {"U1": ("comparison", True, [0, 1])},
    4: {"U1": ("trend_or_change", True, list(range(5)))},
    5: {
        "U1": ("comparison", True, [0, 1]),
        "U2": ("key_value_endpoint", True, [2]),
    },
    6: {
        "U1": ("comparison", True, [0, 1]),
        "U2": ("comparison", True, list(range(2, 8))),
    },
    7: {"U1": ("change_or_rate", True, [0, 1])},
    8: {"U1": ("comparison", True, [0, 1])},
    9: {"U1": ("comparison", True, [0, 1, 2])},
    10: {"U1": ("comparison", True, [0, 1, 2])},
    11: {
        "U1": ("comparison", True, [1, 2]),
        "U2": ("comparison", True, [0, 2]),
    },
    12: {"U1": ("change_or_rate", True, [0, 1, 2])},
    13: {"U1": ("comparison", True, [0, 1])},
    14: {
        "U1": ("change_or_rate", True, [0, 4]),
        "U2": ("comparison", True, [4, 5, 6, 7]),
    },
    15: {"U1": ("change_or_rate", True, [0, 1])},
    16: {"U1": ("change_or_rate", True, [0, 1])},
    17: {"U1": ("comparison", True, [0, 1])},
    18: {"U1": ("change_or_rate", True, [0, 1])},
    19: {"U1": ("range_or_span", True, [0, 1])},
    20: {"U1": ("change_or_rate", True, [0, 1])},
    21: {
        "U1": ("comparison", True, [0, 3, 4]),
        "U2": ("comparison", True, [1, 3, 5]),
        "U3": ("comparison", True, [2, 3]),
        "U4": ("trend_or_order", True, [0, 1, 2]),
    },
    22: {
        "U1": ("comparison", True, list(range(6))),
        "U2": ("key_value_extreme", True, [6]),
        "U3": ("narrative_claim", False, [6]),
    },
    23: {"U1": ("share_or_composition", True, list(range(150)))},
    24: {"U1": ("trend_or_change", True, list(range(5)))},
    25: {"U1": ("comparison", True, [0, 1])},
    26: {"U1": ("change_or_rate", True, [0, 1])},
    27: {"U1": ("trend_or_order", True, list(range(7)))},
    28: {
        "U1": ("threshold_or_crossing", True, [0, 1, 2, 3]),
        "U2": ("narrative_claim", False, [4]),
        "U3": ("narrative_claim", False, [5]),
    },
    29: {"U1": ("comparison", True, list(range(7)))},
    30: {"U1": ("comparison", True, list(range(6)))},
    31: {"U1": ("comparison", True, list(range(7)))},
    32: {"U1": ("comparison", True, list(range(7)))},
    33: {"U1": ("comparison", True, list(range(10)))},
    34: {
        "U1": ("comparison", True, list(range(8))),
        "U2": ("comparison", True, list(range(8))),
    },
}


def read_rows(clip: str) -> list[dict]:
    with (ROOT / clip / "data_table.csv").open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


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


def normalize_g1(clip: str) -> None:
    n = int(clip.split("_")[1])
    if n not in BAR_1_34_LAYOUT:
        return
    path = ROOT / clip / "g1.json"
    g1 = json.loads(path.read_text(encoding="utf-8"))
    if any(unit.get("unit_kind") == "visual_completeness" for unit in g1.get("units", [])):
        return
    rows = read_rows(clip)
    layout = BAR_1_34_LAYOUT[n]
    if set(layout) != {u["id"] for u in g1["units"] if u.get("id") != "U_COMPLETE"}:
        raise ValueError(f"{clip}: unit ids differ from migration map")

    for unit in g1["units"]:
        if unit.get("id") == "U_COMPLETE":
            continue
        kind, visual, indices = layout[unit["id"]]
        unit["unit_kind"] = kind
        unit["must_be_visualized"] = visual
        unit["basis"] = [basis_item(rows[i]) for i in indices]

    flags = list(g1.get("review_flags", []))
    if "human_confirmed_semantics_auto_format_backfill_2026-10-22" not in flags:
        flags.append("human_confirmed_semantics_auto_format_backfill_2026-10-22")
    g1["review_flags"] = flags
    g1["version"] = "g1_r_u_v3"
    path.write_text(json.dumps(g1, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def fnum(value) -> float | None:
    try:
        return float(str(value).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def mark_id(item: dict) -> str:
    entity = item.get("entity", "")
    x = item.get("x") or item.get("year") or ""
    series = item.get("series", "")
    metric = item.get("metric") or item.get("field", "")
    parts = [part for part in (entity, series, x, metric) if part]
    return " | ".join(parts) if parts else "mark"


def unique_mark_ids(basis: list[dict]) -> list[str]:
    raw = [mark_id(item) for item in basis]
    counts = {value: raw.count(value) for value in set(raw)}
    seen = {}
    result = []
    for item, value in zip(basis, raw):
        if counts[value] == 1:
            result.append(value)
            continue
        seen[value] = seen.get(value, 0) + 1
        row = item.get("table_row")
        suffix = f" @ row {row}" if row is not None else f" #{seen[value]}"
        result.append(value + suffix)
    return result


def hydrate_basis(basis: list[dict], rows: list[dict]) -> list[dict]:
    """Attach table fields omitted by older basis records.

    Matching uses every field present in the basis item and consumes rows once,
    so repeated values keep their original table order.
    """
    used = set()
    hydrated = []
    for item in basis:
        source = copy.deepcopy(item)
        candidates = []
        for index, row in enumerate(rows):
            if index in used:
                continue
            ok = True
            for key in ("entity", "series", "x", "year", "metric", "field", "value", "unit", "label"):
                if key not in source or source[key] in (None, ""):
                    continue
                row_value = row.get(key, "")
                if key == "field":
                    row_value = row.get("metric", "")
                if str(row_value) != str(source[key]):
                    ok = False
                    break
            if ok:
                candidates.append(index)
        if candidates:
            index = candidates[0]
            used.add(index)
            row = rows[index]
            for key in ("entity", "series", "x", "year", "metric", "unit", "label"):
                if row.get(key):
                    source.setdefault(key, row[key])
            source["table_row"] = index
        hydrated.append(source)
    return hydrated


def ordered_basis(basis: list[dict]) -> list[dict]:
    if not basis:
        return []
    xvals = [fnum(item.get("x") or item.get("year")) for item in basis]
    if all(value is not None for value in xvals):
        return [item for _, item in sorted(zip(xvals, basis), key=lambda pair: pair[0])]
    return basis


def manual_g2(clip: str, unit_id: str, basis: list[dict]) -> dict | None:
    if clip == "bar_1" and unit_id == "U4":
        return {
            "evidence_type": "ordered_marks_with_readable_label",
            "assertion": {
                "expected_order": [mark_id(item) for item in basis],
                "qualitative_label": {
                    "mark": mark_id(basis[0]),
                    "expected_label": "a lot of time",
                },
                "tolerance": 0,
            },
            "routes": ["geometry", "readable_label"],
            "needs_review": False,
        }
    if clip == "bar_2" and unit_id in {"U1", "U2"}:
        by_entity = {}
        for item in basis:
            by_entity.setdefault(item["entity"], {})[str(item["x"])] = fnum(item["value"])
        changes = []
        for entity, points in by_entity.items():
            start, end = points["1990"], points["2017"]
            changes.append({
                "entity": entity,
                "start_value": start,
                "end_value": end,
                "absolute_decline": round(start - end, 6),
                "relative_decline": round((start - end) / start, 6) if start else None,
            })
        if unit_id == "U2":
            ranking = sorted(changes, key=lambda item: item["relative_decline"], reverse=True)
            return {
                "evidence_type": "relative_decline_ranking",
                "assertion": {
                    "ranking": [item["entity"] for item in ranking],
                    "lowest_relative_decline": ranking[-1]["entity"],
                    "changes": changes,
                    "tolerance": 0.02,
                },
                "routes": ["geometry", "readable_label"],
                "needs_review": False,
            }
        return {
            "evidence_type": "four_series_endpoint_changes",
            "assertion": {"changes": changes, "tolerance": 0.02},
            "routes": ["geometry", "readable_label"],
            "needs_review": False,
        }
    if clip == "bar_12" and unit_id == "U1":
        return {
            "evidence_type": "one_month_change_with_annotation",
            "assertion": {
                "july_index": 1.0,
                "august_index": 1.15,
                "relative_increase": 0.15,
                "added_members": 3200,
                "tolerance": 0.02,
            },
            "routes": ["geometry", "readable_label"],
            "needs_review": False,
        }
    if clip == "bar_21" and unit_id in {"U1", "U2", "U3", "U4"}:
        cost_rows = [item for item in basis if item.get("metric") == "spending_cost_relative_to_college"]
        revenue_rows = [item for item in basis if item.get("metric") == "available_revenue"]
        multiple_rows = [item for item in basis if item.get("metric") == "coverage_multiple"]
        assertion = {
            "relative_costs": [
                {"entity": item["entity"], "value": fnum(item["value"])}
                for item in cost_rows
            ],
            "available_revenue_billion_usd": fnum(revenue_rows[0]["value"]) if revenue_rows else None,
            "coverage_multiple": fnum(multiple_rows[0]["value"]) if multiple_rows else None,
            "tolerance": {"value": 0.02, "ratio": 0.05},
        }
        return {
            "evidence_type": "ranked_spending_comparison" if unit_id == "U4" else "cost_coverage_comparison",
            "assertion": assertion,
            "routes": ["geometry", "readable_label"],
            "needs_review": unit_id == "U3",
        }
    if clip == "bar_28" and unit_id == "U1":
        levels = [item for item in basis if item.get("metric") == "wealth_level"]
        rates = [item for item in basis if item.get("metric") == "wealth_tax_rate"]
        return {
            "evidence_type": "threshold_marks",
            "assertion": {
                "wealth_levels": [
                    {"label": item.get("label", ""), "value": fnum(item.get("value"))}
                    for item in levels
                ],
                "tax_rates": [
                    {"label": item.get("label", ""), "value": fnum(item.get("value"))}
                    for item in rates
                ],
                "expected_threshold_rates": {"$60 million": 2, "$1 billion": 3},
                "tolerance": 0.02,
            },
            "routes": ["geometry", "readable_label"],
            "needs_review": False,
        }
    return None


def build_g2(clip: str) -> dict:
    d = ROOT / clip
    g1 = json.loads((d / "g1.json").read_text(encoding="utf-8"))
    rows = read_rows(clip)
    spec = json.loads((d / "input_spec.json").read_text(encoding="utf-8"))
    numeric_pool = [v for v in (fnum(row.get("value")) for row in rows) if v is not None]
    evidence = []
    semantic_index = 0

    for unit in g1.get("units", []):
        basis = ordered_basis(hydrate_basis(unit.get("basis", []), rows))
        required = unique_mark_ids(basis)
        values = [fnum(item.get("value")) for item in basis]
        labels = [item.get("label", "") for item in basis if item.get("label")]
        visual = bool(unit.get("must_be_visualized"))
        kind = unit.get("unit_kind", "")
        assertion = {}
        routes = ["geometry", "readable_label"]
        needs_review = False
        if kind != "visual_completeness":
            semantic_index += 1
        manual = (
            manual_g2(clip, f"U{semantic_index}", basis)
            if visual and kind != "visual_completeness"
            else None
        )

        if not visual:
            evidence_type = "not_required"
            routes = ["narration"]
            assertion = {"required": False, "reason": "narrative-only unit"}
        elif kind == "visual_completeness":
            evidence_type = "complete_mark_set"
            routes = ["geometry"]
            assertion = {
                "required_data_rows": g1.get("g0_data_completeness", {}).get("required_data_rows"),
                "mode": g1.get("g0_data_completeness", {}).get("mode"),
                "required_states": g1.get("g0_data_completeness", {}).get("required_states", []),
                "required_marks_per_state": g1.get("g0_data_completeness", {}).get(
                    "required_marks_per_state", {}
                ),
                "all_required_marks_must_be_present": True,
            }
        elif manual is not None:
            evidence_type = manual["evidence_type"]
            assertion = manual["assertion"]
            routes = manual["routes"]
            needs_review = manual["needs_review"]
        elif any(value is None for value in values):
            evidence_type = "value_or_readable_label"
            routes = ["readable_label"]
            assertion = {
                "marks": required,
                "expected": [
                    {"mark": mark_id(item), "label": item.get("label", ""), "value": item.get("value", "")}
                    for item in basis
                ],
            }
            needs_review = not any(item.get("label") for item in basis)
        elif kind == "comparison":
            ranked = sorted(basis, key=lambda item: fnum(item.get("value")) or 0, reverse=True)
            high, low = ranked[0], ranked[-1]
            high_value = fnum(high.get("value"))
            low_value = fnum(low.get("value"))
            evidence_type = "pair_comparison" if len(basis) == 2 else "ranked_comparison"
            assertion = {
                "greater": mark_id(high),
                "greater_value": high_value,
                "lesser": mark_id(low),
                "lesser_value": low_value,
                "delta": round(high_value - low_value, 6),
                "ratio": round(high_value / low_value, 6) if low_value else None,
                "expected_order": [mark_id(item) for item in ranked],
                "tolerance": {"value": 0.02, "ratio": 0.05},
            }
            if low_value in (None, 0) or low_value < 0 < high_value:
                assertion["ratio"] = None
            entities = {item.get("entity") for item in basis if item.get("entity")}
            x_values = {item.get("x") or item.get("year") for item in basis if item.get("x") or item.get("year")}
            if len(basis) > 8 and (len(entities) > 1 or len(x_values) > 1):
                needs_review = True
        elif kind == "key_value_extreme":
            values_found = [(item, fnum(item.get("value"))) for item in basis if fnum(item.get("value")) is not None]
            item, value = values_found[0] if values_found else (None, None)
            extreme = "max" if value is not None and numeric_pool and value == max(numeric_pool) else "min"
            evidence_type = "extremum_mark"
            assertion = {
                "mark": mark_id(item) if item else None,
                "extreme": extreme,
                "expected": value,
                "compared_set": "all numeric data rows",
                "tolerance": 0.02,
            }
        elif kind == "key_value_endpoint":
            evidence_type = "mark_value"
            assertion = {
                "marks": [
                    {"mark": mark_id(item), "expected": fnum(item.get("value"))}
                    for item in basis
                ],
                "tolerance": 0.02,
            }
        elif kind in ("trend_or_order", "trend_or_change", "change_or_rate"):
            sequence = [(item, fnum(item.get("value"))) for item in basis]
            numeric_values = [value for _, value in sequence if value is not None]
            direction = "flat"
            if len(numeric_values) >= 2:
                direction = "increasing" if numeric_values[-1] > numeric_values[0] else (
                    "decreasing" if numeric_values[-1] < numeric_values[0] else "flat"
                )
            evidence_type = "monotonic_order" if kind == "trend_or_order" else "endpoint_change"
            assertion = {
                "sequence": [{"mark": mark_id(item), "value": value} for item, value in sequence],
                "direction": direction,
                "start_value": numeric_values[0] if numeric_values else None,
                "end_value": numeric_values[-1] if numeric_values else None,
                "delta": round(numeric_values[-1] - numeric_values[0], 6)
                if len(numeric_values) >= 2 else None,
                "ratio": round(numeric_values[-1] / numeric_values[0], 6)
                if len(numeric_values) >= 2 and numeric_values[0] else None,
                "tolerance": 0.02,
            }
        elif kind == "share_or_composition":
            groups: dict[str, list[dict]] = {}
            for item in basis:
                groups.setdefault(item.get("entity", ""), []).append(item)
            composition = []
            for entity, items in groups.items():
                total = sum(value for value in (fnum(item.get("value")) for item in items) if value is not None)
                composition.append({
                    "entity": entity,
                    "segments": [
                        {"mark": mark_id(item), "value": fnum(item.get("value"))}
                        for item in items
                    ],
                    "total": round(total, 6),
                })
            evidence_type = "complete_composition"
            assertion = {
                "compositions": composition,
                "expected_total": 100 if all(item.get("unit") == "%" for item in basis) else None,
                "tolerance": 0.05,
            }
            if len(basis) > 20:
                needs_review = True
        elif kind == "range_or_span":
            numeric_values = [value for value in values if value is not None]
            evidence_type = "range_endpoints"
            assertion = {
                "minimum": min(numeric_values),
                "maximum": max(numeric_values),
                "span": round(max(numeric_values) - min(numeric_values), 6),
                "tolerance": 0.02,
            }
        elif kind == "threshold_or_crossing":
            evidence_type = "threshold_marks"
            assertion = {
                "marks": [
                    {"mark": mark_id(item), "value": fnum(item.get("value")), "label": item.get("label", "")}
                    for item in basis
                ],
                "relation": "distinguish values on opposite sides of the stated thresholds",
                "tolerance": 0.02,
            }
            needs_review = True
        else:
            evidence_type = "unmapped"
            assertion = {"marks": required, "values": values}
            routes = ["readable_label"]
            needs_review = True

        evidence.append({
            "unit_id": unit.get("id"),
            "unit_kind": kind,
            "must_be_visualized": visual,
            "evidence_type": evidence_type,
            "required_marks": required,
            "assertion": assertion,
            "accepted_routes": routes,
            "completeness_ref": "g0_data_completeness",
            "needs_review": needs_review,
        })

    return {
        "clip_id": clip,
        "family": "bar",
        "version": "g2_visual_evidence_v1",
        "source": "auto-derived from human-confirmed g1.json + data_table.csv",
        "chart_input": spec,
        "completeness": g1.get("g0_data_completeness", {}),
        "unit_evidence": evidence,
    }


def build_g3(clip: str, g2: dict) -> dict:
    g1 = json.loads((ROOT / clip / "g1.json").read_text(encoding="utf-8"))
    units = []
    for evidence in g2["unit_evidence"]:
        visual = evidence["must_be_visualized"]
        unit_policy = {
            "unit_id": evidence["unit_id"],
            "applies": visual,
            "anchor_mode": "generated_narration",
            "anchor_selector": "sentence_that_completes_unit",
            "ready_condition": (
                "all required marks are at their completed state and identifiable"
                if visual else "not applicable to the visual denominator"
            ),
            "window_before_s": 1.0,
            "window_after_s": 1.5,
            "dwell_min_s": 0.8,
            "ordering": (
                "evidence_complete_before_conclusion"
                if evidence["unit_kind"] in {
                    "comparison", "trend_or_order", "threshold_or_crossing"
                } else "no_additional_order_requirement"
            ),
            "identity": "entity_and_series_binding_must_remain_stable",
            "transition": (
                "check_each_required_state"
                if g1.get("g0_data_completeness", {}).get("mode") == "state_sequence"
                else "ignore_mid_animation_geometry; judge_completed_marks"
            ),
        }
        if evidence["unit_kind"] == "visual_completeness":
            unit_policy.update({
                "anchor_mode": "structural_completion",
                "anchor_selector": (
                    "last_required_state_or_project_end"
                    if g1.get("g0_data_completeness", {}).get("mode") == "state_sequence"
                    else "project_end"
                ),
                "dwell_min_s": 0.0,
                "ordering": "all_required_marks_present_by_anchor",
                "transition": "check_required_mark_set_in_each_declared_state",
            })
        units.append(unit_policy)
    return {
        "clip_id": clip,
        "version": "g3_temporal_policy_v1",
        "narration_source": "model_generated",
        "policy_status": "draft_requires_g4_calibration",
        "units": units,
    }


def main() -> None:
    for n in range(1, 35):
        normalize_g1(f"bar_{n}")
    for n in range(1, 164):
        clip = f"bar_{n}"
        d = ROOT / clip
        if not d.is_dir():
            continue
        g2 = build_g2(clip)
        g3 = build_g3(clip, g2)
        (d / "g2.json").write_text(
            json.dumps(g2, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
        (d / "g3.json").write_text(
            json.dumps(g3, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )
    print("normalized bar_1-34 and generated G2/G3 for existing bar clips")


if __name__ == "__main__":
    main()
