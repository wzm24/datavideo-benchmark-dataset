"""Validate the bundled synthetic ground-truth example, not generated videos.

Uses only Python's standard library. Does not execute model-generated code.
Run: python3 validate_example.py
"""

from decimal import Decimal, localcontext
from pathlib import Path
import json


ROOT = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_json(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"), parse_float=Decimal)


def decimal(value):
    require(not isinstance(value, bool), "Boolean cannot be used as numeric input")
    require(isinstance(value, (int, Decimal)), "Only JSON numbers are allowed")
    return Decimal(value)


def all_keys(value):
    if isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from all_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from all_keys(child)


def compute_facts(public, private):
    rows_list = public["table"]["rows"]
    rows = {row["row_id"]: row for row in rows_list}
    require(len(rows) == len(rows_list), "Duplicate row IDs")
    fact_list = private["facts"]
    facts = {fact["id"]: fact for fact in fact_list}
    require(len(facts) == len(fact_list), "Duplicate fact IDs")
    cache = {}
    active = set()

    def fact_value(fact_id):
        require(fact_id in facts, "Unknown fact reference: " + fact_id)
        if fact_id in cache:
            return cache[fact_id]
        require(fact_id not in active, "Cyclic fact dependency: " + fact_id)
        active.add(fact_id)
        result = evaluate(facts[fact_id]["expr"])
        active.remove(fact_id)
        cache[fact_id] = result
        return result

    def evaluate(expr):
        op = expr["op"]
        if op == "cell":
            require(expr["row_id"] in rows, "Unknown row")
            require(expr["field"] in public["table"]["schema"], "Unknown field")
            return decimal(rows[expr["row_id"]][expr["field"]])
        if op == "ref":
            return fact_value(expr["id"])
        if op == "const":
            return decimal(expr["value"])
        require(op in {"sub", "div", "mul", "gt"}, "Unsupported operation: " + op)
        require(len(expr["args"]) == 2, "Binary operation requires exactly two arguments")
        left, right = [evaluate(arg) for arg in expr["args"]]
        left, right = decimal(left), decimal(right)
        if op == "sub":
            return left - right
        if op == "mul":
            return left * right
        if op == "gt":
            return left > right
        require(right != 0, "Undefined division by zero")
        return left / right

    with localcontext() as ctx:
        ctx.prec = 40
        for fact_id, fact in facts.items():
            actual = fact_value(fact_id)
            expected = fact["expected"]
            if isinstance(expected, bool):
                require(isinstance(actual, bool) and actual == expected,
                        "Boolean fact mismatch: " + fact_id)
            else:
                require(not isinstance(actual, bool) and actual == decimal(expected),
                        "Numeric fact mismatch: " + fact_id)
    return cache


def completion_bounds(units, observations):
    """Toy helper for the documented fixed-denominator formula only."""
    total = sum(decimal(unit["weight"]) for unit in units if unit["must_be_visualized"])
    require(total > 0, "Visual denominator must be positive")
    lower = Decimal(0)
    upper = Decimal(0)
    for unit in units:
        if not unit["must_be_visualized"]:
            continue
        axes = observations[unit["id"]]
        require(len(axes) == 3, "C/V/T triplet required")
        require(all(value in (0, 1, None) for value in axes), "Invalid triplet")
        weight = decimal(unit["weight"])
        lower += weight * int(all(value == 1 for value in axes))
        upper += weight * int(all(value != 0 for value in axes))
    return lower / total, upper / total


def main():
    public = load_json("example_public_task.json")
    private = load_json("example_private_gt.json")
    require(public["sample_id"] == private["sample_id"], "Mismatched sample IDs")
    require(public["synthetic_example"] and private["synthetic_example"], "Demo must be labeled synthetic")
    forbidden_public_keys = {"facts", "expected", "required_units", "accepted_routes", "private_gt"}
    require(not (set(all_keys(public)) & forbidden_public_keys), "Answer annotations leaked into public input")
    require("分别量化" in public["intent"], "Quantification obligation must be public")
    require(public["constraints"]["pre_rendered_complete_video_as_asset"] is False,
            "Coding-only scope must exclude wrapped complete videos")
    duration = public["duration"]
    low, high = duration["acceptable_range_seconds"]
    require(low <= duration["target_seconds"] <= high, "Duration target outside public range")

    values = compute_facts(public, private)
    units = private["required_units"]
    require(len({unit["id"] for unit in units}) == len(units), "Duplicate unit IDs")
    policies = {policy["id"] for policy in private["temporal_policies"]}
    public_requirements = public["constraints"]["content_requirements"]
    for unit in units:
        require(decimal(unit["weight"]) > 0, "Unit weight must be positive")
        require(0 <= unit["public_requirement_index"] < len(public_requirements),
                "Unit has no valid public requirement")
        require(unit["temporal_policy_id"] in policies, "Unknown temporal policy")
        require(unit["routes_are_examples_not_exhaustive"], "Open-answer routes must not be exhaustive")
        for route in unit["accepted_routes"]:
            require(bool(route["semantic_condition"]), "Route needs semantic acceptance condition")
            require(all(fact_id in values for fact_id in route["fact_ids"]), "Unknown route fact")
    require(not private["fact_policy"]["catalog_is_exhaustive"], "Fact catalog cannot define closed world")

    all_pass = {unit["id"]: (1, 1, 1) for unit in units}
    all_fail = {unit["id"]: (0, 0, 0) for unit in units}
    require(completion_bounds(units, all_pass) == (1, 1), "All-pass score incorrect")
    require(completion_bounds(units, all_fail) == (0, 0), "Failure score incorrect")
    one_unknown = dict(all_pass)
    one_unknown["U3"] = (1, 1, None)
    lower, upper = completion_bounds(units, one_unknown)
    require(lower == Decimal(2) / Decimal(3) and upper == 1, "Unresolved bounds incorrect")
    delayed = dict(all_pass)
    delayed["U3"] = (1, 1, 0)
    require(completion_bounds(units, delayed) == (lower, lower), "Delayed evidence score incorrect")
    for fact_id, value in values.items():
        print(f"{fact_id}: {value}")
    print(f"PASS: {len(values)} facts, {len(units)} units, public/private structure and score examples")
    print("Scope: data-contract smoke checks only; no video parser, judge or empirical validation is implemented.")


if __name__ == "__main__":
    main()
