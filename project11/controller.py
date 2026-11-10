"""SessionController: single task engine used by every condition (R03)."""
from dataclasses import dataclass
from typing import Optional, Tuple

from project11 import __version__, __study_version__
from project11.event_logger import EventLogger
from project11.hazard import HazardManager
from project11.models import Condition, Event, Outcome, Procedure
from project11.scheduler import Scheduler
from project11.secondary_task import SecondaryTask

#: A second click on the SAME component this soon after an accepted action is
#: treated as the tail of a double-click: logged, but not an error and not a
#: step action.  Deliberately narrow: clicks on OTHER components are never
#: discarded, they are real mistakes and belong in the data.
DOUBLE_CLICK_GUARD_MS = 350


@dataclass
class SessionContext:
    participant_code: str
    session_id: str
    condition: Condition
    condition_order: int
    is_practice: bool
    task_id: str


class SessionController:
    def __init__(self, procedure: Procedure, ctx: SessionContext,
                 logger: EventLogger, scheduler: Scheduler):
        self.proc = procedure
        self.ctx = ctx
        self.log = logger
        self.sched = scheduler
        self.hazard = HazardManager(procedure)
        self.secondary = SecondaryTask(
            target_band=procedure.secondary.target_band,
            drift_per_second=procedure.secondary.drift_per_second,
            correct_key=procedure.secondary.correct_key,
        )
        self.step_index: int = 0
        self.started_at: Optional[int] = None
        self.completed: bool = False
        self.aborted: bool = False
        self._last_accepted: Tuple[Optional[str], int] = (None, -(10**9))

    def start(self, now_ms: int) -> None:
        self.started_at = now_ms
        self._emit("SESSION_STARTED")
        self._emit("TASK_STARTED")
        self._emit("STEP_PRESENTED", step_id=self.current_step().id)
        self.secondary.start(now_ms)

    def current_step(self):
        return self.proc.steps[self.step_index]

    def handle_click(self, component_id: str, now_ms: int,
                     x_norm: float, y_norm: float) -> Outcome:
        if self.completed or self.aborted:
            return Outcome.IGNORED

        last_cid, last_t = self._last_accepted
        if component_id == last_cid and now_ms - last_t < DOUBLE_CLICK_GUARD_MS:
            self._emit("DOUBLE_CLICK_IGNORED", component_id=component_id,
                       x_source=x_norm, y_source=y_norm)
            return Outcome.IGNORED

        if self.hazard.state.active and not self.hazard.state.responded:
            self.hazard.respond(component_id, now_ms)
            outcome = Outcome.ACCEPTED if self.hazard.state.correct else Outcome.REJECTED
            if outcome == Outcome.ACCEPTED:
                self._last_accepted = (component_id, now_ms)
            self._emit("HAZARD_RESPONSE",
                       component_id=component_id,
                       outcome=outcome.value,
                       x_source=x_norm, y_source=y_norm)
            return outcome

        step = self.current_step()
        if component_id == step.component_id:
            self._emit("ACTION_ACCEPTED",
                       step_id=step.id, component_id=component_id,
                       outcome=Outcome.ACCEPTED.value,
                       x_source=x_norm, y_source=y_norm)
            self._last_accepted = (component_id, now_ms)
            self.hazard.maybe_arm_after_step(step.id)
            self._advance(now_ms)
            return Outcome.ACCEPTED
        else:
            self._emit("ACTION_REJECTED",
                       step_id=step.id, component_id=component_id,
                       outcome=Outcome.REJECTED.value,
                       x_source=x_norm, y_source=y_norm)
            return Outcome.REJECTED

    def _advance(self, now_ms: int) -> None:
        if self.step_index + 1 >= len(self.proc.steps):
            self.completed = True
            self._emit("TASK_COMPLETED")
            self._emit("SESSION_ENDED")
            return
        self.step_index += 1
        self._emit("STEP_PRESENTED", step_id=self.current_step().id)

    def review_previous(self, now_ms: int) -> Optional[str]:
        if self.step_index == 0:
            return None
        prev = self.proc.steps[self.step_index - 1].id
        self._emit("INSTRUCTION_REVIEWED", step_id=prev)
        return prev

    def pause(self, now_ms: int) -> None:
        self._emit("PAUSE_STARTED")
        self.sched.pause()

    def resume(self, now_ms: int) -> None:
        self.sched.resume()
        self._emit("PAUSE_ENDED")

    def abort(self, now_ms: int) -> None:
        self.aborted = True
        self._emit("SESSION_ABORTED")
        self._emit("SESSION_ENDED")

    def _emit(self, event_type: str, **kw) -> None:
        e = Event(
            schema_version=1,
            app_version=__version__,
            study_version=__study_version__,
            participant_code=self.ctx.participant_code,
            session_id=self.ctx.session_id,
            attempt_id=self.log.attempt_id,
            task_id=self.ctx.task_id,
            condition=self.ctx.condition.value,
            condition_order=self.ctx.condition_order,
            is_practice=self.ctx.is_practice,
            event_number=0,
            elapsed_ms=self.sched.elapsed_ms(),
            event_type=event_type,
            step_id=kw.get("step_id", self.current_step().id if not self.completed else ""),
            component_id=kw.get("component_id", ""),
            outcome=kw.get("outcome", ""),
            x_source=kw.get("x_source", 0.0),
            y_source=kw.get("y_source", 0.0),
        )
        self.log.log(e)
