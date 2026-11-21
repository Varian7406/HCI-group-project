"""Thin FastAPI adapter: web frontend <-> project11 experiment engine.

The engine (project11.controller + event_logger) stays the SINGLE
authoritative copy of the experiment logic. This server never re-implements
task rules; it creates one SessionController per browser session and calls
it, exactly the way the tkinter MainWindow does.

Run from the repo root:
    python -m pip install -r requirements-web.txt
    python -m uvicorn webapp.server:app --port 8000
Then open http://127.0.0.1:8000 in Firefox.

Timing: the server's pause-aware Scheduler (perf_counter) is the only
authoritative clock. Browser timestamps are never mixed with server times.
The secondary task and hazard expiry advance on every state poll, so the
browser polls every 250 ms; event times are server-side to the millisecond.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from project11.controller import SessionContext, SessionController
from project11.event_logger import EventLogger
from project11.models import Condition
from project11.procedure_loader import load_procedure
from project11.scheduler import Scheduler, now_ms

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
STATIC = ROOT / "webapp" / "static"

app = FastAPI(title="Project 11 web adapter")

_PROCEDURES: Dict[str, object] = {}


def _procedure(pid: str):
    if pid not in _PROCEDURES:
        path = ASSETS / "procedures" / f"{pid}.json"
        if not path.exists():
            raise HTTPException(400, f"unknown procedure '{pid}'")
        try:
            _PROCEDURES[pid] = load_procedure(path)
        except ValueError as e:
            raise HTTPException(500, f"procedure '{pid}' is invalid: {e}")
    return _PROCEDURES[pid]


# --------------------------------------------------------------------------
# Request bodies
# --------------------------------------------------------------------------
class SessionStart(BaseModel):
    participant_code: str = Field(min_length=2, max_length=16)
    condition_order: str = Field(pattern=r"^[ABC]{3}$")
    procedure_id: str = "pc_ram"
    task_id: str = "task_01"
    is_practice: bool = False


class ActionReq(BaseModel):
    component_id: str
    action_seq: int = Field(ge=0)
    x_source: float = Field(0.5, ge=0.0, le=1.0)
    y_source: float = Field(0.5, ge=0.0, le=1.0)


# --------------------------------------------------------------------------
# One browser session = one controller + one logger (mirrors MainWindow)
# --------------------------------------------------------------------------
class WebSession:
    def __init__(self, req: SessionStart, sid: str):
        proc = _procedure(req.procedure_id)
        self.procedure = proc
        self.condition = Condition(req.condition_order[0])
        self.attempt_id = uuid.uuid4().hex[:8]
        log_dir = ROOT / "data" / "raw-local" / sid
        self.logger = EventLogger(
            log_dir / f"attempt_{self.condition.value}_{self.attempt_id}.csv",
            self.attempt_id,
        )
        ctx = SessionContext(
            participant_code=req.participant_code,
            session_id=sid,
            condition=self.condition,
            condition_order=req.condition_order.index(self.condition.value) + 1,
            is_practice=req.is_practice,
            task_id=req.task_id,
        )
        self.ctrl = SessionController(proc, ctx, self.logger, Scheduler())
        self.ctrl.start(now_ms())
        self.seq = self.logger._n          # events written so far
        self.action_seq = 0                # last action_seq accepted
        self.last_reply: Optional[dict] = None
        self.finished = False

    # -- helpers ------------------------------------------------------------
    def _tick(self) -> None:
        """Advance secondary drift and hazard expiry to 'now' (poll-driven)."""
        if self.finished:
            return
        t = now_ms()
        self.ctrl.secondary.tick(t)
        self.ctrl.hazard.miss_if_expired(t)

    def _after_change(self) -> None:
        self.seq = self.logger._n
        if (self.ctrl.completed or self.ctrl.aborted) and not self.finished:
            self.finished = True
            self.logger.close()

    def state(self) -> dict:
        self._tick()
        c = self.ctrl
        step = c.current_step()
        show_target = c.ctx.condition != Condition.A_MANUAL
        hazard = None
        if c.hazard.state.active and not c.hazard.state.responded:
            remaining = max(
                0,
                c.hazard.cfg.response_window_ms
                - (now_ms() - c.hazard.state.presented_at_ms),
            )
            hazard = {"message": c.hazard.cfg.message, "remaining_ms": remaining}
        s = c.secondary.state
        lo, hi = c.secondary.target_band
        return {
            "seq": self.seq,
            "session_id": c.ctx.session_id,
            "condition": c.ctx.condition.value,
            "condition_order": c.ctx.condition_order,
            "is_practice": c.ctx.is_practice,
            "step_index": c.step_index,
            "total_steps": len(self.procedure.steps),
            "instruction": step.instruction,
            # Condition C only: the explanation is the manipulation.
            "explanation": (step.explanation or "") if c.ctx.condition == Condition.C_EXPLANATORY else "",
            # Conditions B and C highlight the target; A never does.
            "target_component": step.component_id if show_target else "",
            "hazard": hazard,
            "secondary": {
                "value": round(s.value, 3),
                "in_band": lo <= s.value <= hi,
                "corrections": s.corrections,
                "opportunities": s.opportunities,
            },
            "elapsed_ms": c.sched.elapsed_ms(),
            "completed": c.completed,
            "aborted": c.aborted,
            "paused": c.sched._paused_at is not None,
        }

    def _reply(self, extra: dict) -> dict:
        return {"state": self.state(), **extra}


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------
_SESSIONS: Dict[str, WebSession] = {}


def _get(sid: str) -> WebSession:
    sess = _SESSIONS.get(sid)
    if sess is None:
        raise HTTPException(404, "unknown session")
    return sess


@app.post("/api/session", status_code=201)
def start_session(req: SessionStart):
    sid = uuid.uuid4().hex[:12]
    try:
        sess = WebSession(req, sid)
    except ValueError as e:
        raise HTTPException(400, f"cannot start session: {e}")
    _SESSIONS[sid] = sess
    return {"session_id": sid, "state": sess.state()}


@app.get("/api/session/{sid}/state")
def get_state(sid: str):
    return _get(sid).state()


@app.post("/api/session/{sid}/action")
def submit_action(sid: str, req: ActionReq):
    sess = _get(sid)
    if sess.finished:
        raise HTTPException(409, "session already ended")
    if req.action_seq < sess.action_seq:
        raise HTTPException(409, "stale action_seq; refetch state")
    if req.action_seq == sess.action_seq and sess.last_reply is not None:
        return sess.last_reply          # idempotent replay, never re-executes

    sess.action_seq = req.action_seq
    sess._tick()
    outcome = sess.ctrl.handle_click(
        req.component_id, now_ms(), req.x_source, req.y_source
    ).value
    sess._after_change()
    sess.last_reply = sess._reply({"outcome": outcome})
    return sess.last_reply


@app.post("/api/session/{sid}/pause")
def pause(sid: str):
    sess = _get(sid)
    sess.ctrl.pause(now_ms())
    sess._after_change()
    return sess._reply({"paused": True})


@app.post("/api/session/{sid}/resume")
def resume(sid: str):
    sess = _get(sid)
    sess.ctrl.resume(now_ms())
    sess._after_change()
    return sess._reply({"paused": False})


@app.post("/api/session/{sid}/review")
def review(sid: str):
    sess = _get(sid)
    sess._tick()
    prev_id = sess.ctrl.review_previous(now_ms())
    sess._after_change()
    instruction = ""
    if prev_id:
        instruction = next(
            s.instruction for s in sess.procedure.steps if s.id == prev_id
        )
    # Reviewing shows the previous instruction but never changes PC state.
    return sess._reply({"reviewed_step_id": prev_id, "reviewed_instruction": instruction})


@app.post("/api/session/{sid}/secondary")
def secondary(sid: str):
    sess = _get(sid)
    sess._tick()
    corrected = sess.ctrl.secondary.correct(now_ms())
    sess._after_change()
    return sess._reply({"corrected": corrected})


@app.post("/api/session/{sid}/abort")
def abort(sid: str):
    sess = _get(sid)
    if not sess.finished:
        sess.ctrl.abort(now_ms())
        sess._after_change()
    return sess._reply({"aborted": True})


# Static frontend last, so /api routes keep priority.
app.mount("/", StaticFiles(directory=str(STATIC), html=True), name="static")
