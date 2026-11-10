"""Logger tests (R08, R09)."""
import csv
from pathlib import Path

from project11.event_logger import EventLogger, FIELDS
from project11.models import Event


def _event(**kw):
    base = dict(
        schema_version=1, app_version="t", study_version="t",
        participant_code="P", session_id="S", attempt_id="a",
        task_id="t1", condition="A", condition_order=1, is_practice=True,
        event_number=0, elapsed_ms=0, event_type="STEP_PRESENTED",
    )
    base.update(kw)
    return Event(**base)


def test_writes_header_and_rows(tmp_path):
    p = tmp_path / "log.csv"
    log = EventLogger(p, "a1")
    log.log(_event(event_type="SESSION_STARTED"))
    log.log(_event(event_type="SESSION_ENDED"))
    log.close()
    rows = list(csv.DictReader(p.open(encoding="utf-8")))
    assert len(rows) == 2
    assert rows[0]["event_number"] == "1"
    assert rows[1]["event_number"] == "2"


def test_bad_destination_raises(tmp_path):
    bad_dir = tmp_path / "a_dir"
    bad_dir.mkdir()
    try:
        EventLogger(bad_dir, "a2")
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError")
