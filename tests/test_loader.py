"""Procedure loader tests (R01)."""
import json
import pytest
from pathlib import Path

from project11.procedure_loader import load_procedure


def _write(tmp_path, data):
    p = tmp_path / "proc.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


GOOD = {
    "schema_version": 1,
    "procedure_id": "p1",
    "content_version": "v1",
    "image": "images/panel.png",
    "source": "test",
    "components": [
        {"id": "a", "label": "A", "bounds": [0.1, 0.1, 0.3, 0.3]},
        {"id": "b", "label": "B", "bounds": [0.5, 0.5, 0.8, 0.8]},
    ],
    "steps": [
        {"id": f"s{i:02d}", "instruction": f"do {i}",
         "expected_action": "select", "component_id": "a"}
        for i in range(1, 7)
    ],
    "hazard": {"message": "warn", "correct_component_id": "b"},
}


def test_loads_valid(tmp_path):
    p = _write(tmp_path, GOOD)
    proc = load_procedure(p)
    assert proc.procedure_id == "p1"
    assert len(proc.steps) == 6


def test_missing_field_raises(tmp_path):
    bad = dict(GOOD); bad.pop("procedure_id")
    with pytest.raises(ValueError):
        load_procedure(_write(tmp_path, bad))


def test_unknown_component_in_step_raises(tmp_path):
    bad = dict(GOOD)
    bad["steps"] = [dict(GOOD["steps"][0]), *GOOD["steps"][1:]]
    bad["steps"][0]["component_id"] = "zzz"
    with pytest.raises(ValueError):
        load_procedure(_write(tmp_path, bad))


def test_bounds_out_of_range_raises(tmp_path):
    bad = dict(GOOD)
    bad["components"] = [dict(GOOD["components"][0]), GOOD["components"][1]]
    bad["components"][0]["bounds"] = [0.5, 0.1, 0.3, 0.3]
    with pytest.raises(ValueError):
        load_procedure(_write(tmp_path, bad))


def test_pc_procedures_load():
    """The three web procedures (RAM, GPU, case fan) all pass validation."""
    root = Path(__file__).resolve().parents[1]
    for pid in ("pc_ram", "pc_gpu", "pc_fan"):
        proc = load_procedure(root / "assets" / "procedures" / f"{pid}.json")
        assert proc.procedure_id == pid
        assert 13 <= len(proc.steps) <= 21
        # every procedure starts with the PC powered on and closed:
        # PSU off, ground, four separate thumbscrew steps, then the panel
        assert proc.steps[0].component_id == "psu_switch"
        assert proc.steps[1].component_id == "chassis_ground"
        assert [s.component_id for s in proc.steps[2:6]] == [
            "side_screw_1", "side_screw_2", "side_screw_3", "side_screw_4"]
        assert proc.steps[6].component_id == "side_panel"
