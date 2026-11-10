"""Simulated participant: plays sessions against the REAL controller.

This drives the same SessionController, EventLogger and Scheduler the GUI
uses, so the CSV logs it produces are exactly what a human session would
produce.  Use it to test the analysis pipeline and to demo the study
without a person in front of the screen.

    python tools/simulated_participant.py          # one demo attempt
"""
from __future__ import annotations

import random
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from project11.controller import SessionContext, SessionController
from project11.event_logger import EventLogger
from project11.models import Condition, Procedure
from project11.scheduler import Scheduler


@dataclass
class BotProfile:
    """One row of 'how a person behaves'.  Tune these, not the loop."""
    step_seconds: float = 3.5      # mean time between clicks
    step_sd: float = 0.8
    error_prob: float = 0.05       # chance a click lands on the wrong component
    hazard_respond_prob: float = 0.9
    hazard_latency_s: float = 2.5
    hazard_latency_sd: float = 0.8
    gauge_react_s: float = 1.8     # how fast the bot corrects the gauge
    gauge_react_sd: float = 0.6
    tick_ms: int = 50


class FakeClock:
    """A controllable clock, so a 5-minute session simulates instantly."""

    def __init__(self) -> None:
        self._ms = 0

    def __call__(self) -> int:
        return self._ms

    def advance(self, ms: int) -> None:
        self._ms += ms


def _gauss_ms(rng: random.Random, mean_s: float, sd_s: float,
              min_s: float = 0.4) -> int:
    return int(max(min_s, rng.gauss(mean_s, sd_s)) * 1000)


def simulate_attempt(procedure: Procedure, out_dir: Path,
                     participant_code: str, session_id: str,
                     condition: Condition, condition_order: int,
                     profile: BotProfile, rng: random.Random,
                     is_practice: bool = False,
                     task_id: str = "task_01") -> Path:
    """Play one attempt to the end and return the CSV path it wrote."""
    clock = FakeClock()
    attempt_id = f"{condition.value}_{rng.randrange(16**6):06x}"
    log_path = out_dir / f"attempt_{attempt_id}.csv"
    log = EventLogger(log_path, attempt_id)
    ctx = SessionContext(participant_code, session_id, condition,
                         condition_order, is_practice, task_id)
    # after_fn/cancel_fn do nothing: the sim loop polls the controller
    # itself instead of relying on scheduled callbacks.
    sched = Scheduler(clock=clock, after_fn=lambda d, c: None,
                      cancel_fn=lambda t: None)
    ctrl = SessionController(procedure, ctx, log, sched)
    ctrl.start(clock())

    component_ids = [c.id for c in procedure.components]
    next_click = clock() + _gauss_ms(rng, profile.step_seconds, profile.step_sd)
    gauge_next = clock() + _gauss_ms(rng, profile.gauge_react_s,
                                     profile.gauge_react_sd)
    hazard_respond_at = None

    while not (ctrl.completed or ctrl.aborted):
        clock.advance(profile.tick_ms)
        now = clock()
        ctrl.secondary.tick(now)
        ctrl.hazard.miss_if_expired(now)

        # Gauge: correct it whenever it is out of band and the bot "notices".
        if now >= gauge_next:
            lo, hi = ctrl.secondary.target_band
            if not lo <= ctrl.secondary.state.value <= hi:
                ctrl.secondary.correct(now)
            gauge_next = now + _gauss_ms(rng, profile.gauge_react_s,
                                         profile.gauge_react_sd)

        # Hazard: decide once whether/how to respond, then wait out the latency.
        if ctrl.hazard.state.active and not ctrl.hazard.state.responded:
            if hazard_respond_at is None:
                if rng.random() < profile.hazard_respond_prob:
                    hazard_respond_at = now + _gauss_ms(
                        rng, profile.hazard_latency_s,
                        profile.hazard_latency_sd, min_s=0.5)
                else:
                    hazard_respond_at = now + 10**9   # never: it will miss
            if now >= hazard_respond_at:
                ctrl.handle_click(ctrl.hazard.cfg.correct_component_id,
                                  now, 0.5, 0.5)
            continue    # a person deals with the alarm before the next step

        # Normal stepping.
        if now >= next_click:
            step = ctrl.current_step()
            if (rng.random() < profile.error_prob
                    and len(component_ids) > 1):
                wrong = rng.choice([c for c in component_ids
                                    if c != step.component_id])
                ctrl.handle_click(wrong, now, 0.5, 0.5)
            else:
                ctrl.handle_click(step.component_id, now, 0.5, 0.5)
            next_click = now + _gauss_ms(rng, profile.step_seconds,
                                         profile.step_sd)

    log.close()
    return log_path


def main() -> None:
    from project11.procedure_loader import load_procedure

    proc = load_procedure(Path("assets/procedures/example_procedure.json"))
    out = Path("data/demo")
    rng = random.Random(42)
    for i, cond in enumerate([Condition.A_MANUAL, Condition.B_OVERLAY,
                              Condition.C_EXPLANATORY], start=1):
        path = simulate_attempt(proc, out, "DEMO", "demo_session", cond, i,
                                BotProfile(), rng)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
