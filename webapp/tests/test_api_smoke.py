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

RAM_STEPS = ["psu_switch", "side_screw", "side_panel", "chassis_ground",
             "dimm_clip_top", "dimm_clip_bottom", "dimm_slot_2", "dimm_slot_2",
             "side_panel", "psu_switch"]


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
    # waits that out exactly as a human would.  The hazard fires right before
    # the grounding step, and a correct hazard response on the component that
    # step asks for completes the step too, so the loop resyncs its pointer
    # from the server after every hazard response.
    import time
    hazard_seen = False
    seq = 10
    i = 0
    while i < len(RAM_STEPS):
        state = client.get(f"/api/session/{sid}/state").json()
        if state["completed"]:
            break
        if state["hazard"]:
            hazard_seen = True
            r = client.post(f"/api/session/{sid}/action",
                            json={"component_id": "chassis_ground",
                                  "action_seq": seq})
            assert r.json()["outcome"] == "accepted"
            seq += 1
            i = client.get(f"/api/session/{sid}/state").json()["step_index"]
            continue
        comp = RAM_STEPS[i]
        if i > 0 and comp == RAM_STEPS[i - 1]:
            time.sleep(0.36)
        r = client.post(f"/api/session/{sid}/action",
                        json={"component_id": comp, "action_seq": seq})
        assert r.json()["outcome"] == "accepted", (comp, r.json())
        seq += 1
        i += 1
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


def test_starting_state_is_on_and_closed(client):
    s = client.post("/api/session", json={
        "participant_code": "TST", "condition_order": "ABC"}).json()["state"]
    assert s["step_index"] == 0
    assert s["step_id"] == "s01"
    assert s["instruction"].startswith("Flip the PSU")
    assert s["last_completed_step_id"] is None
    assert s["wrong_count"] == 0 and not s["hint_ready"]


def test_wrong_clicks_then_hint_is_logged_not_state_changing(client):
    r = client.post("/api/session", json={
        "participant_code": "TST", "condition_order": "BCA"})
    sid = r.json()["session_id"]
    # two wrong clicks on the same step -> hint offered
    for seq in (1, 2):
        out = client.post(f"/api/session/{sid}/action",
                          json={"component_id": "hdd", "action_seq": seq})
        assert out.json()["outcome"] == "rejected"
    s = client.get(f"/api/session/{sid}/state").json()
    assert s["wrong_count"] == 2 and s["hint_ready"]
    assert s["step_index"] == 0, "wrong clicks never advance or undo"

    d = client.post(f"/api/session/{sid}/hint").json()
    assert d["hint"]["step_id"] == "s01"
    assert d["hint"]["target_component"] == "psu_switch"  # B sees the target
    s2 = client.get(f"/api/session/{sid}/state").json()
    assert s2["step_index"] == 0, "hint never changes state"

    # condition A: hint re-presents the instruction but names no target
    r = client.post("/api/session", json={
        "participant_code": "TST", "condition_order": "ABC"})
    sid_a = r.json()["session_id"]
    for seq in (1, 2):
        client.post(f"/api/session/{sid_a}/action",
                    json={"component_id": "hdd", "action_seq": seq})
    d = client.post(f"/api/session/{sid_a}/hint").json()
    assert d["hint"]["target_component"] == ""
    assert d["hint"]["instruction"]

    # hint use is part of the data
    logs = sorted((ROOT / "data" / "raw-local" / sid_a).glob("attempt_*.csv"))
    with logs[0].open() as f:
        types = {row["event_type"] for row in csv.DictReader(f)}
    assert "HINT_SHOWN" in types

    # a correct click resets the wrong-click counter for the new step
    client.post(f"/api/session/{sid_a}/action",
                json={"component_id": "psu_switch", "action_seq": 3})
    s3 = client.get(f"/api/session/{sid_a}/state").json()
    assert s3["wrong_count"] == 0 and not s3["hint_ready"]
    assert s3["last_completed_step_id"] == "s01"
