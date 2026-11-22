"""Controller tests (R03, R05)."""
import csv
import json
from pathlib import Path

import pytest

from project11.controller import SessionContext, SessionController
from project11.event_logger import EventLogger
from project11.models import Condition, Outcome
from project11.procedure_loader import load_procedure
from project11.scheduler import Scheduler


FIXTURE = {
    "schema_version": 1, "procedure_id": "p", "content_version": "v",
    "image": "images/panel.png", "source": "t",
    "components": [
        {"id": "a", "label": "A", "bounds": [0.1, 0.1, 0.3, 0.3]},
        {"id": "b", "label": "B", "bounds": [0.5, 0.5, 0.8, 0.8]},
    ],
    "steps": [
        {"id": "s01", "instruction": "x", "expected_action": "select", "component_id": "a"},
        {"id": "s02", "instruction": "x", "expected_action": "select", "component_id": "b"},
        {"id": "s03", "instruction": "x", "expected_action": "select", "component_id": "a"},
        {"id": "s04", "instruction": "x", "expected_action": "select", "component_id": "b"},
        {"id": "s05", "instruction": "x", "expected_action": "select", "component_id": "a"},
        {"id": "s06", "instruction": "x", "expected_action": "select", "component_id": "b"},
    ],
    "hazard": {"message": "w", "correct_component_id": "b"},
}


@pytest.fixture
def ctrl(tmp_path):
    p = tmp_path / "proc.json"
    p.write_text(json.dumps(FIXTURE))
    proc = load_procedure(p)
    log = EventLogger(tmp_path / "log.csv", "att1")
    sched = Scheduler()
    ctx = SessionContext("P1", "S1", Condition.A_MANUAL, 1, True, "t1")
    c = SessionController(proc, ctx, log, sched)
    c.start(0)
    return c, log


def test_correct_action_advances(ctrl):
    c, _ = ctrl
    assert c.step_index == 0
    out = c.handle_click("a", 100, 0.2, 0.2)
    assert out == Outcome.ACCEPTED
    assert c.step_index == 1


def test_wrong_action_rejected(ctrl):
    c, _ = ctrl
    out = c.handle_click("b", 100, 0.6, 0.6)
    assert out == Outcome.REJECTED
    assert c.step_index == 0


def test_review_does_not_reverse_state(ctrl):
    c, _ = ctrl
    c.handle_click("a", 100, 0.2, 0.2)
    assert c.step_index == 1
    c.review_previous(200)
    assert c.step_index == 1


def test_double_click_tail_is_ignored_not_an_error(ctrl):
    c, _ = ctrl
    assert c.handle_click("a", 100, 0.2, 0.2) == Outcome.ACCEPTED
    assert c.step_index == 1
    # Rapid second click on the SAME component: the tail of a double-click.
    # Without the guard this would be scored as an error against step s02.
    assert c.handle_click("a", 200, 0.2, 0.2) == Outcome.IGNORED
    assert c.step_index == 1
    # After the guard window the same click IS evaluated (and now rejected,
    # because s02 expects component b).
    assert c.handle_click("a", 600, 0.2, 0.2) == Outcome.REJECTED
    assert c.step_index == 1


HAZARD_FIXTURE = dict(FIXTURE)
HAZARD_FIXTURE["hazard"] = {"message": "w", "correct_component_id": "b",
                            "trigger_after_step": "s02"}


def _hazard_ctrl(tmp_path):
    p = tmp_path / "proc.json"
    p.write_text(json.dumps(HAZARD_FIXTURE))
    proc = load_procedure(p)
    log = EventLogger(tmp_path / "log.csv", "att2")
    ctx = SessionContext("P1", "S1", Condition.A_MANUAL, 1, True, "t1")
    c = SessionController(proc, ctx, log, Scheduler())
    c.start(0)
    return c, log


def test_hazard_presents_after_trigger_step(tmp_path):
    c, _ = _hazard_ctrl(tmp_path)
    c.handle_click("a", 100, 0.2, 0.2)          # s01
    assert not c.hazard.state.active
    c.handle_click("b", 200, 0.6, 0.6)          # s02 = trigger
    assert c.hazard.state.active
    assert c.hazard.state.presented_at_ms == 200


def test_hazard_correct_response_logged_once(tmp_path):
    c, log = _hazard_ctrl(tmp_path)
    c.handle_click("a", 100, 0.2, 0.2)
    c.handle_click("b", 200, 0.6, 0.6)
    out = c.handle_click("b", 500, 0.6, 0.6)    # correct hazard response
    assert out == Outcome.ACCEPTED
    assert c.hazard.latency_ms() == 300
    # After resolution the double-click guard is back in force: a rapid
    # second click on the same component is the tail of a double-click...
    out2 = c.handle_click("b", 600, 0.6, 0.6)
    assert out2 == Outcome.IGNORED
    # ...and after the guard window it IS evaluated (and rejected, because
    # s03 expects component a).
    out3 = c.handle_click("b", 1000, 0.6, 0.6)
    assert out3 == Outcome.REJECTED
    rows = list(csv.DictReader((tmp_path / "log.csv").open()))
    presented = [r for r in rows if r["event_type"] == "HAZARD_PRESENTED"]
    responded = [r for r in rows if r["event_type"] == "HAZARD_RESPONSE"]
    assert len(presented) == 1 and len(responded) == 1


MERGE_FIXTURE = {
    "schema_version": 1, "procedure_id": "p", "content_version": "v",
    "image": "images/panel.png", "source": "t",
    "components": [
        {"id": "a", "label": "A", "bounds": [0.1, 0.1, 0.3, 0.3]},
        {"id": "b", "label": "B", "bounds": [0.5, 0.5, 0.8, 0.8]},
    ],
    "steps": [
        {"id": "s01", "instruction": "x", "expected_action": "select", "component_id": "a"},
        {"id": "s02", "instruction": "x", "expected_action": "select", "component_id": "a"},
        {"id": "s03", "instruction": "x", "expected_action": "select", "component_id": "b"},
        {"id": "s04", "instruction": "x", "expected_action": "select", "component_id": "a"},
        {"id": "s05", "instruction": "x", "expected_action": "select", "component_id": "b"},
        {"id": "s06", "instruction": "x", "expected_action": "select", "component_id": "a"},
    ],
    "hazard": {"message": "w", "correct_component_id": "a",
               "trigger_after_step": "s01"},
}


def test_hazard_response_on_current_step_component_advances(tmp_path):
    """One physical action, one advance: the correct hazard response on the
    part the current step asks for completes that step too."""
    p = tmp_path / "proc.json"
    p.write_text(json.dumps(MERGE_FIXTURE))
    proc = load_procedure(p)
    log = EventLogger(tmp_path / "log.csv", "att3")
    ctx = SessionContext("P1", "S1", Condition.A_MANUAL, 1, True, "t1")
    c = SessionController(proc, ctx, log, Scheduler())
    c.start(0)
    assert c.handle_click("a", 100, 0.2, 0.2) == Outcome.ACCEPTED   # s01 + hazard
    assert c.hazard.state.active
    assert c.current_step().id == "s02"        # s02 also expects component a
    assert c.handle_click("a", 400, 0.2, 0.2) == Outcome.ACCEPTED
    assert c.step_index == 2, "hazard response merged with the step action"
    rows = list(csv.DictReader((tmp_path / "log.csv").open()))
    accepted = [r for r in rows if r["event_type"] == "ACTION_ACCEPTED"]
    assert [r["step_id"] for r in accepted] == ["s01", "s02"]


def test_wrong_clicks_count_and_hint(tmp_path):
    p = tmp_path / "proc.json"
    p.write_text(json.dumps(FIXTURE))
    proc = load_procedure(p)
    log = EventLogger(tmp_path / "log.csv", "att4")
    ctx = SessionContext("P1", "S1", Condition.A_MANUAL, 1, True, "t1")
    c = SessionController(proc, ctx, log, Scheduler())
    c.start(0)
    assert not c.hint_ready
    assert c.handle_click("b", 100, 0.6, 0.6) == Outcome.REJECTED
    assert c.handle_click("b", 200, 0.6, 0.6) == Outcome.REJECTED
    assert c.wrong_on_step == 2 and c.hint_ready
    hint = c.take_hint(300)
    assert hint["step_id"] == "s01" and hint["target_component_id"] == "a"
    assert c.step_index == 0, "hint never changes state"
    # a correct click resets the counter for the new step
    assert c.handle_click("a", 400, 0.2, 0.2) == Outcome.ACCEPTED
    assert c.wrong_on_step == 0 and not c.hint_ready
    assert c.last_completed_step_id == "s01"
    rows = list(csv.DictReader((tmp_path / "log.csv").open()))
    assert len([r for r in rows if r["event_type"] == "HINT_SHOWN"]) == 1


def test_hazard_miss_after_window(tmp_path):
    c, _ = _hazard_ctrl(tmp_path)
    c.handle_click("a", 100, 0.2, 0.2)
    c.handle_click("b", 200, 0.6, 0.6)          # presents at 200
    missed = c.hazard.miss_if_expired(200 + 6000 + 1)
    assert missed
    assert c.hazard.state.correct is False
