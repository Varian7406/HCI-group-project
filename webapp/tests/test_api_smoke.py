"""End-to-end smoke test: browser-less client plays a full web session.

Skipped automatically when fastapi is not installed (tkinter-only setups).
Run the whole suite with:  python -m pytest -q
"""
import csv
import sys
from pathlib import Path

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from webapp.server import app, ROOT  # noqa: E402

RAM_STEPS = ["psu_switch", "chassis_ground", "dimm_clip_top", "dimm_clip_bottom",
             "dimm_slot_2", "dimm_slot_2", "psu_switch"]


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _play(client, condition_order):
    r = client.post("/api/session", json={
        "participant_code": "TST", "condition_order": condition_order,
        "is_practice": True,
    })
    assert r.status_code == 201, r.text
    sid = r.json()["session_id"]

    # Wrong component first: must be rejected, state untouched.
    r = client.post(f"/api/session/{sid}/action",
                    json={"component_id": "gpu_card", "action_seq": 1})
    assert r.json()["outcome"] == "rejected"

    # Duplicate action_seq: replayed, never re-executed.
    r2 = client.post(f"/api/session/{sid}/action",
                     json={"component_id": "gpu_card", "action_seq": 1})
    assert r2.json()["outcome"] == "rejected"
    assert r.json()["state"]["seq"] == r2.json()["state"]["seq"]

    # Play the whole procedure. Pacing note: two consecutive steps may target
    # the same component (remove, then insert); the double-click guard
    # correctly swallows a same-component click within 350 ms, so the client
    # waits that out exactly as a human would.
    import time
    hazard_seen = False
    last_comp = None
    seq = 10
    for i, comp in enumerate(RAM_STEPS):
        if comp == last_comp:
            time.sleep(0.36)
        last_comp = comp
        state = client.get(f"/api/session/{sid}/state").json()
        if state["hazard"]:
            hazard_seen = True
            r = client.post(f"/api/session/{sid}/action",
                            json={"component_id": "chassis_ground",
                                  "action_seq": seq})
            assert r.json()["outcome"] == "accepted"
            seq += 1
        r = client.post(f"/api/session/{sid}/action",
                        json={"component_id": comp, "action_seq": seq})
        assert r.json()["outcome"] == "accepted", (comp, r.json())
        seq += 1
    assert hazard_seen, "hazard never presented"
    assert client.get(f"/api/session/{sid}/state").json()["completed"]
    return sid


def test_full_session_condition_b_logs_validate(client):
    sid = _play(client, "BCA")
    logs = sorted((ROOT / "data" / "raw-local" / sid).glob("attempt_*.csv"))
    assert len(logs) == 1
    sys.path.insert(0, str(ROOT))
    from analysis.validate_logs import validate
    errors = validate(logs[0])
    assert errors == [], errors
    with logs[0].open() as f:
        rows = list(csv.DictReader(f))
    types = {row["event_type"] for row in rows}
    assert {"SESSION_STARTED", "TASK_STARTED", "STEP_PRESENTED",
            "ACTION_ACCEPTED", "ACTION_REJECTED", "HAZARD_RESPONSE",
            "TASK_COMPLETED", "SESSION_ENDED"} <= types
    hazard_rows = [r for r in rows if r["event_type"] == "HAZARD_RESPONSE"]
    assert len(hazard_rows) == 1 and hazard_rows[0]["outcome"] == "accepted"


def test_condition_a_gets_no_target_or_explanation(client):
    r = client.post("/api/session", json={
        "participant_code": "TST", "condition_order": "ABC"})
    state = r.json()["state"]
    assert state["condition"] == "A"
    assert state["target_component"] == ""
    assert state["explanation"] == ""


def test_condition_c_gets_explanation(client):
    r = client.post("/api/session", json={
        "participant_code": "TST", "condition_order": "CAB"})
    state = r.json()["state"]
    assert state["condition"] == "C"
    assert state["explanation"]
    assert state["target_component"]  # C also highlights


def test_pause_freezes_elapsed(client):
    r = client.post("/api/session", json={
        "participant_code": "TST", "condition_order": "ABC"})
    sid = r.json()["session_id"]
    client.post(f"/api/session/{sid}/pause")
    e1 = client.get(f"/api/session/{sid}/state").json()["elapsed_ms"]
    e2 = client.get(f"/api/session/{sid}/state").json()["elapsed_ms"]
    assert e1 == e2
    client.post(f"/api/session/{sid}/resume")
    e3 = client.get(f"/api/session/{sid}/state").json()["elapsed_ms"]
    assert e3 >= e1


def test_review_does_not_change_pc_state(client):
    r = client.post("/api/session", json={
        "participant_code": "TST", "condition_order": "ABC"})
    sid = r.json()["session_id"]
    client.post(f"/api/session/{sid}/action",
                json={"component_id": "psu_switch", "action_seq": 1})
    s1 = client.get(f"/api/session/{sid}/state").json()
    d = client.post(f"/api/session/{sid}/review").json()
    assert d["reviewed_instruction"]
    s2 = client.get(f"/api/session/{sid}/state").json()
    assert s1["step_index"] == s2["step_index"]


def test_stale_action_seq_rejected(client):
    r = client.post("/api/session", json={
        "participant_code": "TST", "condition_order": "ABC"})
    sid = r.json()["session_id"]
    client.post(f"/api/session/{sid}/action",
                json={"component_id": "psu_switch", "action_seq": 5})
    r = client.post(f"/api/session/{sid}/action",
                    json={"component_id": "chassis_ground", "action_seq": 2})
    assert r.status_code == 409
