"""Load and validate a procedure JSON file.

Raises ValueError with a clear message on any problem (R01).
"""
import json
from pathlib import Path
from typing import List

from project11.models import (
    Component, HazardConfig, Procedure, SecondaryConfig, Step,
)


def _require(d: dict, key: str, ctx: str):
    if key not in d or d[key] is None or d[key] == "":
        raise ValueError(f"{ctx}: missing required field '{key}'")
    return d[key]


def _parse_component(d: dict) -> Component:
    cid = _require(d, "id", "component")
    label = _require(d, "label", f"component {cid}")
    bounds = _require(d, "bounds", f"component {cid}")
    if not (isinstance(bounds, list) and len(bounds) == 4):
        raise ValueError(f"component {cid}: bounds must be [l,t,r,b]")
    l, t, r, b = map(float, bounds)
    if not (0 <= l < r <= 1 and 0 <= t < b <= 1):
        raise ValueError(f"component {cid}: bounds out of 0..1 or inverted")
    return Component(id=cid, label=label, bounds=(l, t, r, b))


def _parse_step(d: dict) -> Step:
    sid = _require(d, "id", "step")
    return Step(
        id=sid,
        instruction=_require(d, "instruction", f"step {sid}"),
        expected_action=_require(d, "expected_action", f"step {sid}"),
        component_id=_require(d, "component_id", f"step {sid}"),
        explanation=d.get("explanation", ""),
    )


def load_procedure(path: Path) -> Procedure:
    if not path.exists():
        raise ValueError(f"Procedure file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    _require(data, "schema_version", "procedure")
    pid = _require(data, "procedure_id", "procedure")
    image = _require(data, "image", "procedure")

    raw_comps = data.get("components", [])
    if not raw_comps:
        raise ValueError("procedure: at least one component required")
    components: List[Component] = [_parse_component(c) for c in raw_comps]
    comp_ids = {c.id for c in components}
    if len(comp_ids) != len(components):
        raise ValueError("procedure: duplicate component ids")

    raw_steps = data.get("steps", [])
    if not (6 <= len(raw_steps) <= 10):
        raise ValueError(f"procedure: expected 6-10 steps, got {len(raw_steps)}")
    steps: List[Step] = [_parse_step(s) for s in raw_steps]
    for s in steps:
        if s.component_id not in comp_ids:
            raise ValueError(f"step {s.id}: unknown component_id {s.component_id!r}")

    hazard_raw = _require(data, "hazard", "procedure")
    hazard = HazardConfig(
        trigger_after_step=hazard_raw.get("trigger_after_step"),
        message=_require(hazard_raw, "message", "hazard"),
        correct_component_id=_require(hazard_raw, "correct_component_id", "hazard"),
        response_window_ms=int(hazard_raw.get("response_window_ms", 6000)),
    )
    if hazard.correct_component_id not in comp_ids:
        raise ValueError("hazard: unknown correct_component_id")

    return Procedure(
        schema_version=int(data["schema_version"]),
        procedure_id=pid,
        content_version=_require(data, "content_version", "procedure"),
        image_rel_path=image,
        source=data.get("source", "unknown"),
        components=components,
        steps=steps,
        hazard=hazard,
    )
