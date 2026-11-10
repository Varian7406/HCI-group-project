"""Controller tests (R03, R05)."""
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
