# -*- coding: utf-8 -*-
"""Generate area narrative goals, public intents, and V1 G1 candidates."""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import html
import json
import re
import sys
import threading
import time
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import requests


ROOT = Path(r"D:\dev\data_video_dataset_pipeline")
DATASET = ROOT / "data" / "generated" / "ok_5files_all"
BASE = ROOT / "benchmark_draft" / "area_intent"
GOALS = BASE / "goals"
INTENTS = BASE / "intents"
G1_OUT = BASE / "g1"
REVIEW = BASE / "review"
WORK = Path(r"D:\dev\he-m-work\work")
sys.path.insert(0, str(WORK))
import llm  # noqa: E402


LOCK = threading.Lock()
PROMPT_VERSION = "area_goal_intent_g1_v1_2026-11-12"
ACTION_VERB = re.compile(
    r"(?i)^(compare|contrast|trace|quantify|explain|identify|examine|describe|"
    r"analyze|analyse|present|show|determine|evaluate|assess|explore|summarize|"
    r"summarise|report|state|calculate|compute|rank|combine|estimate|relate|map|measure)\b"
)
YEAR = re.compile(r"^(?:1[5-9]\d\d|20\d\d|21\d\d)$")
ANSWER_PATTERNS = [
    re.compile(r"\bshow(?:s|ed)?\s+that\b", re.I),
    re.compile(
        r"\b(?:is|are|was|were|has|have|had)\s+(?:the\s+)?"
        r"(?:highest|lowest|largest|smallest|greatest|least|most|only)\b",
        re.I,
    ),
    re.compile(
        r"\b(?:is|are|was|were)\s+"
        r"(?:more|less|higher|lower|greater|fewer|faster|slower|bigger|smaller)\s+than\b",
        re.I,
    ),
    re.compile(
        r"\b(?:increased|decreased|rose|fell|declined|dropped|surged|doubled|"
        r"tripled|exceeded|outpaced|surpassed|accelerated)\b",
        re.I,
    ),
    re.compile(r"\b(?:outpaces?|exceeds?|surpasses?|dominates?)\b", re.I),
]
UNIT_KINDS = {
    "comparison",
    "change",
    "trend",
    "extremum",
    "ranking",
    "threshold_or_crossing",
    "share_or_composition",
    "proportional_comparison",
    "projection_or_range",
    "identity",
}
MANUAL_INTENTS = {
    "area_4": (
        "Trace the democracy share from 1900 to 2000 and quantify its overall change."
    ),
    "area_27": (
        "Compare where the income-distribution density is concentrated relative to "
        "the average and identify the labeled lower-income segment."
    ),
    "area_29": (
        "Compare the perceived risk associated with death by car and death by plane."
    ),
    "area_32": (
        "Trace the relative change in the scale of the universe from the Big Bang "
        "to the present."
    ),
    "area_33": (
        "Compare how coal-plant-equivalent capacity changes for the USA and China "
        "from 2000 to 2040."
    ),
    "area_43": (
        "Compare annual CO2 emissions for all listed entities across the period "
        "and trace how each changes over time."
    ),
}


def clean(value: Any) -> str:
    return "" if value is None else str(value).strip()


def parse_number(value: Any) -> float | None:
    text = clean(value).replace(",", "").replace("%", "").replace("$", "")
    try:
        return float(text)
    except ValueError:
        return None


def clip_number(path: Path) -> int:
    return int(path.name.rsplit("_", 1)[1])


def clip_dirs() -> list[Path]:
    return sorted(
        (
            path
            for path in DATASET.iterdir()
            if path.is_dir() and re.fullmatch(r"area_\d+", path.name)
        ),
        key=clip_number,
    )


def read_narration(clip: Path) -> str:
    values = []
    for line in (clip / "narration.jsonl").read_text(encoding="utf-8-sig").splitlines():
        if line.strip():
            values.append(clean(json.loads(line).get("text")))
    return " ".join(value for value in values if value)


def read_table(clip: Path) -> list[dict[str, str]]:
    with (clip / "data_table.csv").open(
        encoding="utf-8-sig", newline=""
    ) as handle:
        rows = list(csv.DictReader(handle))
    for index, row in enumerate(rows, 1):
        row["_row_id"] = f"r{index}"
    return rows


def read_svg_text(clip: Path) -> list[str]:
    path = clip / "semantic.svg"
    root = ElementTree.parse(path).getroot()
    values = []
    for element in root.iter():
        if element.tag.rsplit("}", 1)[-1] != "text":
            continue
        parts = []
        for node in element.iter():
            if node.text and node.text.strip():
                parts.append(node.text.strip())
        value = " ".join(" ".join(parts).split())
        if value and value not in values:
            values.append(value)
    return values


def load_spec(clip: Path) -> dict[str, Any]:
    return json.loads((clip / "chart_spec.json").read_text(encoding="utf-8-sig"))


def public_spec(clip: Path, spec: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "family",
        "sub_type",
        "orientation",
        "panel_count",
        "series_count",
        "time_behavior",
        "stacked",
        "fill_under",
        "special_area_type",
        "total_tiles",
    )
    result = {"clip_id": clip.name}
    for field in fields:
        if spec.get(field) is not None:
            result[field] = spec[field]
    axis_ranges = spec.get("axis_ranges")
    if axis_ranges:
        result["axis_ranges"] = axis_ranges
    return result


def old_intent(clip: Path) -> str:
    path = clip / "intent.json"
    if not path.exists():
        return ""
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return clean(data.get("intent_en") or data.get("intent"))


def mark_identity(row: dict[str, str]) -> str:
    return (
        clean(row.get("entity"))
        or clean(row.get("series"))
        or clean(row.get("label"))
        or clean(row.get("panel"))
        or "unnamed area mark"
    )


def selected_indices(rows: list[dict[str, str]], limit: int = 36) -> list[int]:
    if len(rows) <= limit:
        return list(range(len(rows)))
    indices = {0, len(rows) - 1}
    printable_x = [
        index for index, row in enumerate(rows) if clean(row.get("x"))
    ]
    indices.update(printable_x)
    numeric = [
        (index, parse_number(row.get("value")))
        for index, row in enumerate(rows)
        if parse_number(row.get("value")) is not None
    ]
    if numeric:
        values = [value for _, value in numeric if value is not None]
        indices.add(min(numeric, key=lambda pair: pair[1])[0])
        indices.add(max(numeric, key=lambda pair: pair[1])[0])
        if len(values) >= 4:
            for index in range(1, len(numeric) - 1):
                left = numeric[index - 1][1]
                current = numeric[index][1]
                right = numeric[index + 1][1]
                if current is None or left is None or right is None:
                    continue
                if (current - left) * (right - current) < 0:
                    indices.add(numeric[index][0])
    if len(indices) > limit:
        ordered = sorted(indices)
        indices = {
            ordered[round(position * (len(ordered) - 1) / (limit - 1))]
            for position in range(limit)
        }
    else:
        remaining = limit - len(indices)
        for position in range(remaining):
            indices.add(round(position * (len(rows) - 1) / max(remaining - 1, 1)))
    return sorted(index for index in indices if 0 <= index < len(rows))[:limit]


def row_payload(row: dict[str, str]) -> dict[str, str]:
    fields = (
        "_row_id",
        "panel",
        "x_axis",
        "y_axis",
        "entity",
        "series",
        "x",
        "point_order",
        "value",
        "unit",
        "label",
        "role",
    )
    return {field: clean(row.get(field)) for field in fields}


def compact_table(rows: list[dict[str, str]]) -> dict[str, Any]:
    groups: OrderedDict[tuple[str, str, str, str], list[dict[str, str]]] = OrderedDict()
    for row in rows:
        key = (
            clean(row.get("panel")),
            clean(row.get("entity")),
            clean(row.get("series")),
            clean(row.get("role")),
        )
        groups.setdefault(key, []).append(row)

    summaries = []
    sampled = []
    seen_rows = set()
    for (panel, entity, series, role), group in groups.items():
        group = sorted(group, key=lambda row: int(clean(row.get("point_order")) or 0))
        values = [
            value
            for row in group
            if (value := parse_number(row.get("value"))) is not None
        ]
        x_values = [clean(row.get("x")) for row in group if clean(row.get("x"))]
        indices = selected_indices(group)
        selected = [group[index] for index in indices]
        summaries.append(
            {
                "panel": panel,
                "entity": entity,
                "series": series,
                "role": role,
                "row_count": len(group),
                "unit": next(
                    (clean(row.get("unit")) for row in group if clean(row.get("unit"))),
                    "",
                ),
                "printed_x": x_values[:20],
                "value_min": min(values) if values else None,
                "value_max": max(values) if values else None,
                "first": row_payload(group[0]),
                "last": row_payload(group[-1]),
                "sampled_row_ids": [row["_row_id"] for row in selected],
            }
        )
        for row in selected:
            if row["_row_id"] not in seen_rows:
                sampled.append(row_payload(row))
                seen_rows.add(row["_row_id"])
    return {
        "row_count": len(rows),
        "columns": list(rows[0].keys()) if rows else [],
        "groups": summaries,
        "sampled_rows": sampled,
        "instruction": (
            "The sampled rows preserve endpoints, printed x anchors, extrema, bends, "
            "and evenly spaced coverage. Use only a listed _row_id as G1 basis."
        ),
    }


def parse_json(text: str) -> dict[str, Any] | None:
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", text or ""):
        try:
            value, _ = decoder.raw_decode(text[match.start() :])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def call_json(prompt: str, max_tokens: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    token, base, model = llm._cfg()
    session = requests.Session()
    session.trust_env = False
    last: dict[str, Any] = {}
    for attempt in range(3):
        started = time.time()
        response = session.post(
            base + "/chat/completions",
            headers={"Authorization": "Bearer " + token},
            json={
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                        + (
                            "\nReturn only the JSON object."
                            if attempt == 0
                            else "\nReturn valid JSON only; do not use Markdown fences."
                        ),
                    }
                ],
                "temperature": 0,
                "max_tokens": max_tokens,
                "thinking": {"type": "disabled"},
            },
            timeout=300,
            proxies={"http": None, "https": None},
        )
        last = {
            "model": model,
            "sec": round(time.time() - started, 1),
            "status": response.status_code,
            "attempt": attempt + 1,
            "usage": {},
        }
        if response.status_code != 200:
            last["error"] = response.text[:500]
            continue
        payload = response.json()
        choice = payload["choices"][0]
        text = choice.get("message", {}).get("content", "")
        last.update(
            {
                "model": payload.get("model", model),
                "finish_reason": choice.get("finish_reason"),
                "usage": payload.get("usage", {}),
                "raw": text,
            }
        )
        parsed = parse_json(text)
        if parsed:
            return parsed, last
    return None, last


def goal_prompt(
    clip: Path,
    narration: str,
    table: dict[str, Any],
    svg_text: list[str],
    spec: dict[str, Any],
    prior: str,
) -> str:
    return f"""Write the internal, answer-bearing narrative goal for one area chart clip.

The goal is hidden GT and may contain the conclusion and key values. It should
state what the original narration, corrected table, and confirmed chart jointly
ask a viewer to understand.

Rules:
- return exactly one concise English sentence, at most 45 words;
- start with Show, Compare, Trace, Quantify, Explain, Identify, or Demonstrate;
- capture the narrative takeaway, not a chart inventory or a list of every row;
- preserve the population/entity, metric, time or category scope, panel identity,
  and comparison set that are supported by the inputs;
- narration supplies the intended framing; the corrected table and visible labels
  are the factual authority;
- every entity and relation in the final goal must be answerable from the compact
  table or visible labels; do not import an adjacent narration-only claim;
- values may appear only when supported by the table or visible labels;
- for a noisy or incomplete narration, use the table/chart to recover the actual
  comparison without inventing causes or external context;
- do not mention chart type, colors, layout, animation, SVG, code, or file format;
- a proportional mark may describe the visible relationship without inventing
  exact values that are absent;
- if a conclusion in narration cannot be supported, omit it and record the issue.

Return only JSON:
{{
 "narrative_goal": "...",
 "core_claim": "...",
 "chart_role": "one short phrase",
 "source_consistency": "consistent|corrected_from_old_intent|partial|conflict",
 "issues": ["..."],
 "confidence": 0.0
}}

Clip: {clip.name}
Narration:
{narration}

Public chart specification:
{json.dumps(spec, ensure_ascii=False, indent=1)}

Compact corrected-table view:
{json.dumps(table, ensure_ascii=False, indent=1)}

Visible chart text and labels:
{json.dumps(svg_text[:120], ensure_ascii=False, indent=1)}

Old intent draft (non-authoritative context only):
{prior}
"""


def goal_check_prompt(
    goal: str,
    core_claim: str,
    table: dict[str, Any],
    svg_text: list[str],
    spec: dict[str, Any],
) -> str:
    return f"""Audit an area narrative goal against the public data and visible labels.

Narration is not included in this audit. Only the compact corrected table,
visible chart labels, chart specification, and directly supported calculations
are evidence.

Check:
- every entity/population, metric, direction, comparison, and value in the goal
  is supported by the table or visible labels;
- no adjacent narration-only claim was imported;
- the goal is one concise answer-bearing sentence and captures a nontrivial
  takeaway rather than a chart inventory;
- no cause or external fact is asserted unless the supplied evidence contains it.

Return only JSON:
{{
 "supported": true,
 "unsupported_claims": [],
 "issues": [],
 "corrected_goal": "",
 "corrected_core_claim": ""
}}

Proposed narrative goal:
{goal}

Proposed core claim:
{core_claim}

Chart specification:
{json.dumps(spec, ensure_ascii=False, indent=1)}

Compact corrected table:
{json.dumps(table, ensure_ascii=False, indent=1)}

Visible chart text and labels:
{json.dumps(svg_text[:120], ensure_ascii=False, indent=1)}
"""


def writer_prompt(
    goal: str,
    table: dict[str, Any],
    svg_text: list[str],
    spec: dict[str, Any],
) -> str:
    return f"""Write one answer-neutral public V1 intent for an area chart task.

The narrative goal below is hidden GT and contains the answer. Convert it into
a task the generator can complete from the public intent, data table, and chart
specification.

Rules:
- exactly one imperative English sentence, preferably 12-28 words, maximum 32;
- start with an action verb;
- preserve the entity/population set, metric, time window, panel/category scope,
  and comparison set;
- make the requested analytical operation explicit: compare, trace, quantify,
  determine, rank, identify, or report;
- never state the result, direction, largest/smallest, increase/decrease,
  complement, threshold, or causal conclusion;
- no numerals except four-digit years, year ranges, and numbers that are literal
  parts of an entity/category name in the table;
- do not mention area, line, chart, axis, color, layout, animation, SVG, or code;
- do not add a comparison or entity that is absent from the public table/spec;
- remain answerable from the table and chart scope.

Return only JSON:
{{
 "intent": "...",
 "entities": ["..."],
 "measure": "...",
 "scope": "...",
 "comparison": "...",
 "withheld_answer": "..."
}}

Hidden narrative goal:
{goal}

Chart specification:
{json.dumps(spec, ensure_ascii=False, indent=1)}

Compact data-table view:
{json.dumps(table, ensure_ascii=False, indent=1)}

Visible labels available while authoring:
{json.dumps(svg_text[:120], ensure_ascii=False, indent=1)}
"""


def checker_prompt(
    goal: str,
    table: dict[str, Any],
    svg_text: list[str],
    spec: dict[str, Any],
    intent: str,
) -> str:
    return f"""Audit whether this public area-chart intent is neutral, complete, and answerable.

Required:
- one imperative sentence, at most 32 words, starting with an action verb;
- same entities/population, metric, time scope, panel set, and comparison set as
  the hidden goal;
- no answer, direction, ranking, extreme, threshold, complement, or cause;
- no non-year numeral except literal numbers in table entity/category names;
- no chart type, visual style, layout, axis, animation, or code instruction;
- answerable from the public table and chart specification.

Return only JSON:
{{
 "protocol_compliant": true,
 "answer_leak": false,
 "leaked_phrases": [],
 "scope_complete": true,
 "scope_issues": [],
 "supported_by_inputs": true,
 "natural_request": true,
 "issues": []
}}

Hidden narrative goal:
{goal}

Chart specification:
{json.dumps(spec, ensure_ascii=False, indent=1)}

Compact data-table view:
{json.dumps(table, ensure_ascii=False, indent=1)}

Visible chart labels:
{json.dumps(svg_text[:120], ensure_ascii=False, indent=1)}

Proposed intent:
{intent}
"""


def repair_intent_prompt(
    goal: str,
    table: dict[str, Any],
    svg_text: list[str],
    spec: dict[str, Any],
    intent: str,
    audit: dict[str, Any],
    mechanical: dict[str, Any],
) -> str:
    return writer_prompt(goal, table, svg_text, spec) + f"""

Repair the rejected intent. Keep its valid scope, remove every leaked answer and
presentation detail, and obey the mechanical audit.

Mechanical audit:
{json.dumps(mechanical, ensure_ascii=False, indent=1)}

Semantic audit:
{json.dumps(audit, ensure_ascii=False, indent=1)}

Rejected intent:
{intent}
"""


def mechanical_intent_checks(intent: str, rows: list[dict[str, str]]) -> dict[str, Any]:
    words = intent.split()
    sentence_text = re.sub(
        r"(?i)\b(U\.S|U\.K|e\.g|i\.e|vs|No|Mr|Ms|Dr)\.", r"\1", intent.strip()
    )
    sentence_text = re.sub(r"(?<=\d)\.(?=\d)", "", sentence_text)
    sentence_count = len(
        [part for part in re.split(r"(?<=[.!?])\s+", sentence_text) if part.strip()]
    )
    normalized = re.sub(
        r"(?i)\b(CO2|CH4|NO2|SO2|PM2\.5)\b",
        "CHEMTOKEN",
        intent,
    )
    normalized = re.sub(
        r"\b(?:1[5-9]\d\d|20\d\d|21\d\d)\s*[-/]\s*(?:\d{2}|\d{4})\b",
        "YEARRANGE",
        normalized,
    )
    normalized = re.sub(r"\b[A-Za-z]+-\d+\b", "NAMETOKEN", normalized)
    numbers = [
        token.rstrip(".,;:()[]")
        for token in re.findall(r"\d[\d,.]*", normalized)
    ]
    allowed = set()
    for row in rows:
        for field in ("panel", "entity", "series", "label"):
            for token in re.findall(r"\d[\d,.]*", row.get(field, "")):
                allowed.add(token.rstrip(".,;:()[]"))
    bad_numbers = [
        token
        for token in numbers
        if not YEAR.fullmatch(token) and token not in allowed
    ]
    answer_matches = [
        match.group(0)
        for pattern in ANSWER_PATTERNS
        for match in pattern.finditer(intent)
    ]
    return {
        "word_count": len(words),
        "sentence_count": sentence_count,
        "starts_with_action_verb": bool(ACTION_VERB.search(intent.strip())),
        "non_year_numbers": bad_numbers,
        "allowed_name_numbers": sorted(allowed),
        "answer_pattern_matches": answer_matches,
        "mentions_chart_style": bool(
            re.search(
                r"(?i)\b(area|line|chart|graph|color|colour|layout|axis|"
                r"animation|svg|tile|bubble|circle|square)\b",
                intent,
            )
        ),
    }


def intent_needs_repair(audit: dict[str, Any], mechanical: dict[str, Any]) -> bool:
    return bool(
        not audit.get("protocol_compliant")
        or audit.get("answer_leak")
        or audit.get("scope_complete") is False
        or audit.get("supported_by_inputs") is False
        or audit.get("natural_request") is False
        or mechanical["sentence_count"] != 1
        or mechanical["word_count"] > 32
        or not mechanical["starts_with_action_verb"]
        or mechanical["non_year_numbers"]
        or mechanical["answer_pattern_matches"]
        or mechanical["mentions_chart_style"]
    )


def completeness_units(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    panel_groups: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
    for row in rows:
        panel_groups.setdefault(clean(row.get("panel")), []).append(row)
    units = []
    for index, (panel, group) in enumerate(panel_groups.items(), 1):
        identities: OrderedDict[tuple[str, str, str], dict[str, str]] = OrderedDict()
        for row in group:
            key = (
                clean(row.get("entity")),
                clean(row.get("series")),
                clean(row.get("role")),
            )
            identities.setdefault(key, row)
        names = [
            mark_identity(row)
            for row in identities.values()
        ]
        scope = panel or "the chart"
        units.append(
            {
                "id": f"U{index}",
                "requirement_id": "R1",
                "unit_kind": "visual_completeness",
                "must_be_visualized": True,
                "claim": (
                    f"All {len(identities)} required area marks are present in "
                    f"{scope}: {', '.join(names)}."
                ),
                "basis": [
                    {
                        "row_id": row["_row_id"],
                        "panel": clean(row.get("panel")),
                        "entity": clean(row.get("entity")),
                        "series": clean(row.get("series")),
                        "role": clean(row.get("role")),
                        "field": "series_presence",
                    }
                    for row in identities.values()
                ],
                "accept": [
                    "every listed area, reference mark, segment, or category is visible",
                    "each mark is correctly bound to its entity or series identity",
                ],
                "reject": [
                    "missing any required area, reference mark, segment, or category",
                    "assigning a mark to the wrong entity, panel, or series",
                    "replacing a required mark with narration text alone",
                ],
            }
        )
    requirement = {
        "id": "R1",
        "question": "How does the video present the required area marks in this chart?",
        "relation": "all_of" if len(units) > 1 else "single",
        "unit_ids": [unit["id"] for unit in units],
        "scope": {"panels": list(panel_groups.keys())},
    }
    return [requirement], units


def g1_prompt(
    intent: str,
    spec: dict[str, Any],
    table: dict[str, Any],
) -> str:
    return f"""Draft semantic G1 slots and units for one area-chart V1 clip.

Use only the neutral intent, chart specification, and public table below. Do not
use reference narration, target narration, or the reference visual as evidence.

Requiredness test:
A unit is required if omitting it means the video has not completed the intent.
Create one unit per analytical slot. Keep 1-4 semantic units. Do not enumerate
every row merely because it exists in the table. R1 completeness is added later.

Allowed unit kinds:
- comparison: compare values, entities, panels, or groups
- change: compare start and end or two named states
- trend: monotonic increase/decrease, reversal, or sustained movement
- extremum: maximum/minimum/lowest/highest relation
- ranking: order among three or more required entities
- threshold_or_crossing: one series crosses or exceeds a reference threshold
- share_or_composition: a part-versus-whole or stacked contribution relation
- proportional_comparison: compare proportional areas, diameters, volumes, or sizes
- projection_or_range: history versus projection or uncertainty interval
- identity: bind a semantic role when the intent explicitly requires it

Rules:
- one slot produces one unit; do not split endpoints, difference, ratio, and
  ranking when they express the same fact;
- if the intent asks only how two series relate over time, use one relation,
  crossing, or comparison unit instead of separate units for each series;
- one unit should normally need at least two independent table observations;
- preserve population, entity, unit, time/category scope, and panel identity;
- stacked series are bands in a shared whole; do not add unrelated panels;
- proportional marks must state the encoding relation only when the intent asks;
- do not create units for colors, layout, chart type, decoration, or code;
- every basis item must use a listed _row_id and an actual field;
- place relevant but non-required facts in optional_valid;
- list easy false claims and unsupported inferences in unsupported_to_avoid;
- return only semantic slots and units; R1 completeness is separate.

Return only JSON:
{{
 "slots": [
   {{"slot_id":"S1","obligation":"one obligation in the intent",
     "unit_ids":["U1"]}}
 ],
 "semantic_units": [
   {{"id":"U1","slot_id":"S1","unit_kind":"comparison",
     "claim":"one nontrivial proposition",
     "basis_rows":[{{"row_id":"r1","field":"value"}}],
     "computation":"none | formula",
     "accept":["..."],
     "reject":["..."],
     "must_be_visualized":true,
     "needs_review":false}}
 ],
 "optional_valid":["..."],
 "unsupported_to_avoid":["..."],
 "review_notes":["..."]
}}

Public intent:
{intent}

Chart specification:
{json.dumps(spec, ensure_ascii=False, indent=1)}

Public compact data table:
{json.dumps(table, ensure_ascii=False, indent=1)}
"""


def closure_prompt(
    intent: str,
    requirements: list[dict[str, Any]],
    units: list[dict[str, Any]],
    table: dict[str, Any],
) -> str:
    return f"""Independently audit G1 closure for an area-chart V1 example.

Check:
1. every obligation in the public intent maps to at least one semantic unit;
2. every semantic unit is necessary under the deletion test;
3. no two units share the same analytical slot or merely restate one another;
4. each claim is nontrivial and supported by its listed basis;
5. completeness R1 is present and does not replace semantic interpretation;
6. no narration-derived or hidden-answer requirement was added.

Return only JSON:
{{
 "closed": true,
 "missing_slots": [],
 "duplicate_units": [],
 "unsupported_units": [],
 "unnecessary_units": [],
 "issues": [],
 "recommended_fix": ""
}}

Public intent:
{intent}

Requirements:
{json.dumps(requirements, ensure_ascii=False, indent=1)}

Units:
{json.dumps(units, ensure_ascii=False, indent=1)}

Public compact table:
{json.dumps(table, ensure_ascii=False, indent=1)}
"""


def resolve_basis(items: list[dict[str, Any]], rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    by_id = {row["_row_id"]: row for row in rows}
    resolved = []
    for item in items:
        row_id = clean(item.get("row_id"))
        row = by_id.get(row_id)
        if row is None:
            raise RuntimeError(f"unknown basis row_id {row_id!r}")
        field = clean(item.get("field")) or "value"
        if field not in row:
            raise RuntimeError(f"basis field {field!r} not in {row_id}")
        resolved.append(
            {
                "row_id": row_id,
                "panel": clean(row.get("panel")),
                "x_axis": clean(row.get("x_axis")),
                "y_axis": clean(row.get("y_axis")),
                "entity": clean(row.get("entity")),
                "series": clean(row.get("series")),
                "x": clean(row.get("x")),
                "point_order": clean(row.get("point_order")),
                "field": field,
                "value": clean(row.get(field)),
                "unit": clean(row.get("unit")),
                "role": clean(row.get("role")),
            }
        )
    if not resolved:
        raise RuntimeError("empty semantic basis")
    return resolved


def normalize_g1(
    response: dict[str, Any],
    rows: list[dict[str, str]],
    completeness_count: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    slots = response.get("slots") or []
    semantic = response.get("semantic_units") or []
    if not 1 <= len(semantic) <= 4:
        raise RuntimeError(f"expected 1-4 semantic units, got {len(semantic)}")
    id_map = {
        clean(unit.get("id")): f"U{completeness_count + index}"
        for index, unit in enumerate(semantic, 1)
    }
    slot_units = {}
    for slot in slots:
        mapped = [id_map[uid] for uid in slot.get("unit_ids", []) if uid in id_map]
        if mapped:
            slot_units[clean(slot.get("slot_id"))] = (slot, mapped)

    requirements = []
    unit_to_requirement = {}
    assigned_units = set()
    for slot_id, (slot, mapped) in slot_units.items():
        unique_mapped = [unit_id for unit_id in mapped if unit_id not in assigned_units]
        if not unique_mapped:
            continue
        requirement_id = f"R{len(requirements) + 2}"
        requirements.append(
            {
                "id": requirement_id,
                "question": clean(slot.get("obligation")) or "Complete this intent obligation.",
                "relation": "all_of" if len(unique_mapped) > 1 else "single",
                "unit_ids": unique_mapped,
                "scope": {},
            }
        )
        for unit_id in unique_mapped:
            assigned_units.add(unit_id)
            unit_to_requirement[unit_id] = requirement_id
    claim_by_id = {
        id_map[clean(unit.get("id"))]: clean(unit.get("claim"))
        for unit in semantic
    }
    for unit_id, claim in claim_by_id.items():
        if unit_id in assigned_units:
            continue
        requirement_id = f"R{len(requirements) + 2}"
        requirements.append(
            {
                "id": requirement_id,
                "question": claim,
                "relation": "single",
                "unit_ids": [unit_id],
                "scope": {},
            }
        )
        assigned_units.add(unit_id)
        unit_to_requirement[unit_id] = requirement_id

    normalized = []
    for unit in semantic:
        source_id = clean(unit.get("id"))
        unit_id = id_map[source_id]
        kind = clean(unit.get("unit_kind"))
        if kind not in UNIT_KINDS:
            raise RuntimeError(f"unsupported unit kind {kind!r}")
        normalized.append(
            {
                "id": unit_id,
                "requirement_id": unit_to_requirement.get(unit_id),
                "unit_kind": kind,
                "claim": clean(unit.get("claim")),
                "basis": resolve_basis(unit.get("basis_rows") or [], rows),
                "computation": clean(unit.get("computation")) or "none",
                "accept": unit.get("accept") or [],
                "reject": unit.get("reject") or [],
                "must_be_visualized": bool(unit.get("must_be_visualized", True)),
                "needs_review": bool(unit.get("needs_review")),
            }
        )
    return requirements, normalized


def merge_same_basis_units(
    requirements: list[dict[str, Any]],
    units: list[dict[str, Any]],
    start_index: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Apply protocol C4 deterministically when two units use the same basis set."""
    requirement_by_id = {requirement["id"]: requirement for requirement in requirements}
    grouped: OrderedDict[tuple[str, ...], list[dict[str, Any]]] = OrderedDict()
    for unit in units:
        key = tuple(sorted(item["row_id"] for item in unit["basis"]))
        grouped.setdefault(key, []).append(unit)

    merged_units = []
    merged_requirements = []
    for index, group in enumerate(grouped.values(), start_index):
        first = group[0]
        unit_id = f"U{index}"
        requirement_id = f"R{index - start_index + 2}"
        kind = (
            first["unit_kind"]
            if all(unit["unit_kind"] == first["unit_kind"] for unit in group)
            else "comparison"
        )
        claims = []
        for unit in group:
            claim = clean(unit.get("claim"))
            if claim and claim not in claims:
                claims.append(claim)
        accept = list(
            OrderedDict.fromkeys(
                value
                for unit in group
                for value in (unit.get("accept") or [])
                if clean(value)
            )
        )
        reject = list(
            OrderedDict.fromkeys(
                value
                for unit in group
                for value in (unit.get("reject") or [])
                if clean(value)
            )
        )
        computations = list(
            OrderedDict.fromkeys(
                clean(unit.get("computation"))
                for unit in group
                if clean(unit.get("computation")) not in {"", "none"}
            )
        )
        question_values = []
        for unit in group:
            requirement = requirement_by_id.get(clean(unit.get("requirement_id")))
            if requirement and clean(requirement.get("question")):
                question_values.append(clean(requirement["question"]))
        question = " and ".join(OrderedDict.fromkeys(question_values))
        merged_units.append(
            {
                "id": unit_id,
                "requirement_id": requirement_id,
                "unit_kind": kind,
                "claim": "; ".join(claims),
                "basis": first["basis"],
                "computation": "; ".join(computations) or "none",
                "accept": accept,
                "reject": reject,
                "must_be_visualized": all(
                    bool(unit.get("must_be_visualized", True)) for unit in group
                ),
                "needs_review": any(bool(unit.get("needs_review")) for unit in group),
            }
        )
        merged_requirements.append(
            {
                "id": requirement_id,
                "question": question or merged_units[-1]["claim"],
                "relation": "single",
                "unit_ids": [unit_id],
                "scope": {},
            }
        )
    return merged_requirements, merged_units


def two_pass_table(clip: Path) -> dict[str, Any]:
    return compact_table(read_table(clip))


def process_goal(clip: Path) -> dict[str, Any]:
    started = time.time()
    rows = read_table(clip)
    spec_full = load_spec(clip)
    narration = read_narration(clip)
    texts = read_svg_text(clip)
    prior = old_intent(clip)
    table = compact_table(rows)
    response, call = call_json(
        goal_prompt(clip, narration, table, texts, public_spec(clip, spec_full), prior),
        1800,
    )
    if not response:
        raise RuntimeError(call.get("error") or "goal model returned no JSON")
    goal = " ".join(clean(response.get("narrative_goal") or response.get("narration_goal")).split())
    if not goal:
        raise RuntimeError("empty narrative goal")
    issues = response.get("issues") or []
    if not isinstance(issues, list):
        issues = [str(issues)]
    core_claim = clean(response.get("core_claim"))
    goal_audit, goal_audit_call = call_json(
        goal_check_prompt(
            goal,
            core_claim,
            table,
            texts,
            public_spec(clip, spec_full),
        ),
        1800,
    )
    if not goal_audit:
        raise RuntimeError(goal_audit_call.get("error") or "goal audit failed")
    if (
        not goal_audit.get("supported")
        or goal_audit.get("unsupported_claims")
    ):
        corrected_goal = clean(goal_audit.get("corrected_goal"))
        if corrected_goal:
            corrected, corrected_call = call_json(
                goal_prompt(
                    clip,
                    narration,
                    table,
                    texts,
                    public_spec(clip, spec_full),
                    prior,
                )
                + "\nThe previous goal imported unsupported claims. Rewrite it using "
                "only the table and visible labels.\nAudit:\n"
                + json.dumps(goal_audit, ensure_ascii=False, indent=1),
                1800,
            )
            if corrected and clean(corrected.get("narrative_goal")):
                response = corrected
                goal = " ".join(clean(corrected.get("narrative_goal")).split())
                core_claim = clean(corrected.get("core_claim")) or corrected_goal
            else:
                goal = " ".join(corrected_goal.split())
                core_claim = clean(goal_audit.get("corrected_core_claim")) or goal
            issues.extend(goal_audit.get("issues") or [])
        else:
            issues.extend(goal_audit.get("issues") or [])
    elif not core_claim:
        core_claim = goal
    if len(goal.split()) > 45:
        issues.append("Narrative goal is longer than 45 words.")
    result = {
        "clip": clip.name,
        "family": "area",
        "status": "candidate_needs_review",
        "narrative_goal": goal,
        "core_claim": core_claim or goal,
        "chart_role": clean(response.get("chart_role")),
        "source_consistency": clean(response.get("source_consistency")),
        "issues": issues,
        "confidence": response.get("confidence"),
        "old_intent": prior,
        "narration": narration,
        "svg_text": texts,
        "chart_spec": public_spec(clip, spec_full),
        "table_summary": table,
        "source": ["narration", "data_table", "semantic_svg", "chart_spec", "old_intent_context"],
        "prompt_version": PROMPT_VERSION,
        "model": call.get("model"),
        "goal_audit": goal_audit,
        "usage": {
            "goal": call.get("usage", {}),
            "audit": goal_audit_call.get("usage", {}),
        },
        "sec": round(time.time() - started, 1),
    }
    (GOALS / f"{clip.name}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return result


def process_intent(clip: Path) -> dict[str, Any]:
    started = time.time()
    goal_doc = json.loads((GOALS / f"{clip.name}.json").read_text(encoding="utf-8"))
    goal = goal_doc["narrative_goal"]
    rows = read_table(clip)
    spec_full = load_spec(clip)
    spec = public_spec(clip, spec_full)
    table = compact_table(rows)
    texts = read_svg_text(clip)
    manual = MANUAL_INTENTS.get(clip.name)
    if manual:
        draft = {"intent": manual, "manual_override": True}
        writer_call = {"model": "manual", "usage": {}}
        intent = manual
    else:
        draft, writer_call = call_json(writer_prompt(goal, table, texts, spec), 1800)
        if not draft or not clean(draft.get("intent")):
            raise RuntimeError(writer_call.get("error") or "intent writer returned no intent")
        intent = " ".join(clean(draft["intent"]).split())
    calls = [writer_call]
    repairs = []
    for repair_index in range(3):
        mechanical = mechanical_intent_checks(intent, rows)
        audit, checker_call = call_json(
            checker_prompt(goal, table, texts, spec, intent), 1800
        )
        calls.append(checker_call)
        if not audit:
            raise RuntimeError(checker_call.get("error") or "intent checker failed")
        if not intent_needs_repair(audit, mechanical):
            break
        repaired, repair_call = call_json(
            repair_intent_prompt(goal, table, texts, spec, intent, audit, mechanical),
            1800,
        )
        calls.append(repair_call)
        repairs.append(
            {
                "attempt": repair_index + 1,
                "rejected_intent": intent,
                "audit": audit,
                "mechanical": mechanical,
            }
        )
        if not repaired or not clean(repaired.get("intent")):
            break
        draft = repaired
        intent = " ".join(clean(repaired["intent"]).split())
    mechanical = mechanical_intent_checks(intent, rows)
    passed = not intent_needs_repair(audit, mechanical)
    result = {
        "clip": clip.name,
        "family": "area",
        "status": "pass" if passed else "revise",
        "narrative_goal": goal,
        "proposed_intent": intent,
        "writer": draft,
        "protocol_audit": audit,
        "mechanical_checks": mechanical,
        "repairs": repairs,
        "repair_attempts": len(repairs),
        "source": ["narrative_goal", "data_table", "semantic_svg", "chart_spec"],
        "prompt_version": PROMPT_VERSION,
        "usage": [call.get("usage", {}) for call in calls],
        "sec": round(time.time() - started, 1),
    }
    (INTENTS / f"{clip.name}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return result


def process_g1(clip: Path) -> dict[str, Any]:
    started = time.time()
    intent_doc = json.loads((INTENTS / f"{clip.name}.json").read_text(encoding="utf-8"))
    intent = intent_doc["proposed_intent"]
    rows = read_table(clip)
    spec_full = load_spec(clip)
    spec = public_spec(clip, spec_full)
    table = compact_table(rows)
    completeness_requirements, completeness = completeness_units(rows)
    response = None
    semantic_requirements = None
    semantic_units = None
    calls = []
    errors = []
    current_prompt = g1_prompt(intent, spec, table)
    for attempt in range(3):
        response, call = call_json(current_prompt, 7000)
        calls.append(call)
        if not response:
            errors.append(call.get("error") or "no JSON")
            continue
        try:
            semantic_requirements, semantic_units = normalize_g1(
                response, rows, len(completeness)
            )
            semantic_requirements, semantic_units = merge_same_basis_units(
                semantic_requirements, semantic_units, len(completeness) + 1
            )
            break
        except Exception as error:
            errors.append(f"{type(error).__name__}: {error}")
            current_prompt = (
                g1_prompt(intent, spec, table)
                + "\nPrevious response failed normalization. Return 1-4 valid semantic "
                "units with listed _row_id values and supported unit kinds."
            )
    if not semantic_units:
        raise RuntimeError("G1 generation failed: " + " | ".join(errors))

    requirements = completeness_requirements + semantic_requirements
    units = completeness + semantic_units
    audit = None
    for repair_attempt in range(3):
        audit, audit_call = call_json(
            closure_prompt(intent, requirements, units, table), 3000
        )
        calls.append(audit_call)
        if not audit:
            raise RuntimeError(audit_call.get("error") or "G1 closure audit failed")
        basis_sets = [
            tuple(sorted(item["row_id"] for item in unit["basis"]))
            for unit in semantic_units
        ]
        warnings = []
        if len(basis_sets) != len(set(basis_sets)):
            warnings.append("Two semantic units share an identical basis set.")
        if any(len(unit["basis"]) < 2 for unit in semantic_units):
            warnings.append("At least one semantic unit uses fewer than two basis rows.")
        if audit.get("closed") and not warnings:
            break
        if repair_attempt >= 2:
            break
        repair, repair_call = call_json(
            g1_prompt(intent, spec, table)
            + "\nThe independent closure audit or local check rejected the previous G1:\n"
            + json.dumps(audit, ensure_ascii=False, indent=1)
            + "\nLocal warnings:\n"
            + json.dumps(warnings, ensure_ascii=False, indent=1)
            + "\nRewrite a closed G1. Merge units that share the same basis and "
            "analytical slot; use consistent rows when duplicate x values exist.",
            7000,
        )
        calls.append(repair_call)
        if not repair:
            break
        semantic_requirements, semantic_units = normalize_g1(
            repair, rows, len(completeness)
        )
        semantic_requirements, semantic_units = merge_same_basis_units(
            semantic_requirements, semantic_units, len(completeness) + 1
        )
        requirements = completeness_requirements + semantic_requirements
        units = completeness + semantic_units

    weights = {unit["id"]: round(1.0 / len(units), 10) for unit in units}
    basis_sets = [
        tuple(sorted(item["row_id"] for item in unit["basis"]))
        for unit in semantic_units
    ]
    warnings = []
    if len(basis_sets) != len(set(basis_sets)):
        warnings.append("Two semantic units share an identical basis set.")
    if any(len(unit["basis"]) < 2 for unit in semantic_units):
        warnings.append("At least one semantic unit uses fewer than two basis rows.")
    result = {
        "clip_id": clip.name,
        "version": "g1_area_r_u_v1_2026-11-12",
        "input_contract": "V1",
        "input_materials": ["intent_en", "data_table.csv", "chart_spec.json"],
        "intent": intent,
        "chart_structure": spec,
        "requirements": requirements,
        "units": units,
        "weight_mode": "uniform_over_units",
        "unit_weights": weights,
        "optional_valid": response.get("optional_valid") or [],
        "unsupported_to_avoid": response.get("unsupported_to_avoid") or [],
        "review_notes": response.get("review_notes") or [],
        "closure_review": audit,
        "local_checks": {"warnings": warnings},
        "g0_data_completeness": {
            "required": True,
            "mode": "area_mark_set_per_panel",
            "required_units": [unit["id"] for unit in completeness],
            "row_count": len(rows),
            "table_sha256": hashlib.sha256(
                (clip / "data_table.csv").read_bytes()
            ).hexdigest(),
        },
        "status": (
            "candidate_pending_review"
            if audit.get("closed") and not warnings
            else "candidate_needs_attention"
        ),
        "prompt_version": PROMPT_VERSION,
        "usage": [call.get("usage", {}) for call in calls],
        "sec": round(time.time() - started, 1),
    }
    (G1_OUT / f"{clip.name}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    return {
        "clip": clip.name,
        "status": result["status"],
        "units": len(units),
        "semantic_units": len(semantic_units),
        "requirements": len(requirements),
        "closed": bool(audit.get("closed")),
        "warnings": warnings,
        "sec": result["sec"],
        "usage": result["usage"],
    }


def run_parallel(clips: list[Path], workers: int, function) -> list[dict[str, Any]]:
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(function, clip): clip for clip in clips}
        for index, future in enumerate(concurrent.futures.as_completed(futures), 1):
            clip = futures[future]
            try:
                result = future.result()
            except Exception as error:
                result = {
                    "clip": clip.name,
                    "status": "error",
                    "error": f"{type(error).__name__}: {error}",
                }
            with LOCK:
                results.append(result)
            print(
                json.dumps(
                    {
                        "clip": clip.name,
                        "status": result.get("status"),
                        "completed": index,
                        "total": len(clips),
                        "error": result.get("error", ""),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    results.sort(key=lambda row: clip_number(Path(row["clip"])))
    return results


def write_review(selected: list[Path]) -> None:
    REVIEW.mkdir(parents=True, exist_ok=True)
    cards = []
    for clip_path in selected:
        clip = clip_path.name
        goal_doc = json.loads((GOALS / f"{clip}.json").read_text(encoding="utf-8"))
        intent_doc = json.loads((INTENTS / f"{clip}.json").read_text(encoding="utf-8"))
        g1_doc = json.loads((G1_OUT / f"{clip}.json").read_text(encoding="utf-8"))
        units = "".join(
            f"<li><strong>{html.escape(unit['id'])} · "
            f"{html.escape(unit.get('unit_kind', ''))}</strong> "
            f"{html.escape(unit.get('claim', ''))}"
            f"<div class='muted'>basis rows: "
            f"{html.escape(', '.join(item['row_id'] for item in unit.get('basis', [])))}"
            "</div></li>"
            for unit in g1_doc.get("units", [])
        )
        cards.append(
            f"""
<section id="{html.escape(clip)}">
  <h2>{html.escape(clip)} <span class="pill">{html.escape(g1_doc.get('status', ''))}</span></h2>
  <div class="media">
    <img src="../../data/generated/ok_5files_all/{html.escape(clip)}/keyframe.png">
    <img src="../../data/generated/ok_5files_all/{html.escape(clip)}/semantic.svg">
  </div>
  <p><strong>Narrative goal:</strong> {html.escape(goal_doc.get('narrative_goal', ''))}</p>
  <p><strong>Public intent:</strong> {html.escape(intent_doc.get('proposed_intent', ''))}</p>
  <p class="muted">Intent audit: answer_leak={html.escape(str(intent_doc.get('protocol_audit', {}).get('answer_leak')))} ·
    scope_complete={html.escape(str(intent_doc.get('protocol_audit', {}).get('scope_complete')))} ·
    G1 closed={html.escape(str(g1_doc.get('closure_review', {}).get('closed')))}</p>
  <ol>{units}</ol>
</section>"""
        )
    document = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>Area narrative goal · intent · G1 review</title>
<style>
body{{font-family:Inter,"Segoe UI",Arial,sans-serif;margin:0;background:#f3f5f2;color:#17231d}}
header{{position:sticky;top:0;background:#173f32;color:white;padding:20px 32px;z-index:2}}
main{{max-width:1320px;margin:auto;padding:24px}}
section{{background:white;border:1px solid #d2ddd5;border-radius:14px;padding:20px;margin:18px 0;box-shadow:0 3px 12px #173f3210}}
.media{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.media img{{width:100%;height:330px;object-fit:contain;background:#fafcf9;border:1px solid #dce5df;border-radius:8px}}
.muted{{color:#607067;font-size:13px}}
.pill{{font-size:12px;padding:3px 9px;border-radius:999px;background:#dcefe6;color:#174f42}}
li{{margin:10px 0}}
</style></head><body><header>
<h1>Area · narrative goal → intent → G1</h1>
<p>{len(selected)} clips · V1 public intent · hidden goal is answer-bearing · G1 uses intent + table + chart_spec only</p>
</header><main>{''.join(cards)}</main></body></html>"""
    (REVIEW / "review.html").write_text(document, encoding="utf-8")


def sync_candidates(selected: list[Path]) -> None:
    for clip in selected:
        goal = json.loads((GOALS / f"{clip.name}.json").read_text(encoding="utf-8"))
        intent = json.loads((INTENTS / f"{clip.name}.json").read_text(encoding="utf-8"))
        g1 = json.loads((G1_OUT / f"{clip.name}.json").read_text(encoding="utf-8"))
        for filename, payload in (
            ("narrative_goal_candidate.json", goal),
            ("intent_candidate.json", intent),
            ("g1_candidate.json", g1),
        ):
            (clip / filename).write_text(
                json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                encoding="utf-8",
            )


def write_index(selected: list[Path]) -> None:
    rows = []
    for clip in selected:
        goal = json.loads((GOALS / f"{clip.name}.json").read_text(encoding="utf-8"))
        intent = json.loads((INTENTS / f"{clip.name}.json").read_text(encoding="utf-8"))
        g1 = json.loads((G1_OUT / f"{clip.name}.json").read_text(encoding="utf-8"))
        semantic_units = [
            unit
            for unit in g1.get("units", [])
            if unit.get("unit_kind") != "visual_completeness"
        ]
        rows.append(
            {
                "clip": clip.name,
                "goal_status": goal.get("status"),
                "narrative_goal": goal.get("narrative_goal"),
                "intent_status": intent.get("status"),
                "intent": intent.get("proposed_intent"),
                "g1_status": g1.get("status"),
                "closed": (g1.get("closure_review") or {}).get("closed"),
                "semantic_units": len(semantic_units),
                "total_units": len(g1.get("units", [])),
                "unit_kinds": "|".join(
                    unit.get("unit_kind", "") for unit in semantic_units
                ),
                "claims": " || ".join(
                    unit.get("claim", "") for unit in semantic_units
                ),
                "goal_issues": " | ".join(goal.get("issues") or []),
                "intent_issues": " | ".join(
                    (intent.get("protocol_audit") or {}).get("issues", [])
                ),
                "g1_issues": " | ".join(
                    (g1.get("closure_review") or {}).get("issues", [])
                ),
            }
        )
    with (BASE / "area_goal_intent_g1.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase",
        choices=("goals", "intents", "g1", "all", "render"),
        required=True,
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("clips", nargs="*")
    args = parser.parse_args()
    selected = clip_dirs()
    if args.clips:
        wanted = set(args.clips)
        selected = [clip for clip in selected if clip.name in wanted]
        missing = wanted - {clip.name for clip in selected}
        if missing:
            raise SystemExit(f"unknown clips: {sorted(missing)}")
    GOALS.mkdir(parents=True, exist_ok=True)
    INTENTS.mkdir(parents=True, exist_ok=True)
    G1_OUT.mkdir(parents=True, exist_ok=True)

    goal_results = []
    intent_results = []
    g1_results = []
    if args.phase in {"goals", "all"}:
        goal_results = run_parallel(selected, args.workers, process_goal)
        errors = [row for row in goal_results if row["status"] == "error"]
        if errors:
            raise SystemExit("goal errors: " + json.dumps(errors, ensure_ascii=False))
    if args.phase in {"intents", "all"}:
        intent_results = run_parallel(selected, args.workers, process_intent)
        errors = [row for row in intent_results if row["status"] in {"error", "revise"}]
        if errors:
            print(json.dumps({"intent_incomplete": errors}, ensure_ascii=False, indent=2))
    if args.phase in {"g1", "all"}:
        g1_results = run_parallel(selected, args.workers, process_g1)
        errors = [row for row in g1_results if row["status"] == "error"]
        if errors:
            print(json.dumps({"g1_errors": errors}, ensure_ascii=False, indent=2))

    all_results = []
    goal_docs = []
    intent_docs = []
    g1_docs = []
    for clip in selected:
        entry = {"clip": clip.name}
        for name, path in (
            ("goal", GOALS / f"{clip.name}.json"),
            ("intent", INTENTS / f"{clip.name}.json"),
            ("g1", G1_OUT / f"{clip.name}.json"),
        ):
            if path.exists():
                document = json.loads(path.read_text(encoding="utf-8"))
                entry[name] = document.get("status")
                if name == "goal":
                    goal_docs.append(document)
                elif name == "intent":
                    intent_docs.append(document)
                else:
                    g1_docs.append(document)
        all_results.append(entry)
    summary = {
        "prompt_version": PROMPT_VERSION,
        "clips": len(selected),
        "goal_status": dict(Counter(row.get("status") for row in goal_docs)),
        "intent_status": dict(Counter(row.get("status") for row in intent_docs)),
        "g1_status": dict(Counter(row.get("status") for row in g1_docs)),
        "g1_closure": dict(
            Counter(
                str((row.get("closure_review") or {}).get("closed"))
                for row in g1_docs
            )
        ),
        "unit_counts": dict(
            Counter(len(row.get("units") or []) for row in g1_docs)
        ),
        "semantic_unit_counts": dict(
            Counter(
                sum(
                    unit.get("unit_kind") != "visual_completeness"
                    for unit in (row.get("units") or [])
                )
                for row in g1_docs
            )
        ),
        "needs_attention": [
            row.get("clip_id")
            for row in g1_docs
            if row.get("status") != "candidate_pending_review"
        ],
        "errors": {
            "goals": [row for row in goal_results if row.get("status") == "error"],
            "intents": [
                row for row in intent_results if row.get("status") in {"error", "revise"}
            ],
            "g1": [row for row in g1_results if row.get("status") == "error"],
        },
        "outputs": {
            "goals": str(GOALS),
            "intents": str(INTENTS),
            "g1": str(G1_OUT),
            "review": str(REVIEW / "review.html"),
        },
        "candidate_files_written_to_dataset": all(
            (clip / "narrative_goal_candidate.json").exists()
            and (clip / "intent_candidate.json").exists()
            and (clip / "g1_candidate.json").exists()
            for clip in selected
        ),
        "existing_dataset_files_overwritten": False,
    }
    (BASE / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if all((GOALS / f"{clip.name}.json").exists() and (INTENTS / f"{clip.name}.json").exists() and (G1_OUT / f"{clip.name}.json").exists() for clip in selected):
        write_review(selected)
        sync_candidates(selected)
        write_index(selected)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
