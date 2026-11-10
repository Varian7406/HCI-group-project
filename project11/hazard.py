"""Scripted hazard: triggered after a configured step (R06)."""
from dataclasses import dataclass
from typing import Optional

from project11.models import HazardConfig, Procedure


@dataclass
class HazardState:
    active: bool = False
    presented_at_ms: int = 0
    responded: bool = False
    response_at_ms: int = 0
    correct: Optional[bool] = None


class HazardManager:
    def __init__(self, procedure: Procedure):
        self.cfg = procedure.hazard
        self.state = HazardState()
        self._armed = self.cfg.trigger_after_step is None

    def maybe_arm_after_step(self, step_id: str) -> bool:
        if self.state.active or self.state.responded:
            return False
        if self.cfg.trigger_after_step and self.cfg.trigger_after_step == step_id:
            self._armed = True
            return True
        return False

    @property
    def armed(self) -> bool:
        return self._armed and not self.state.active and not self.state.responded

    def present(self, now_ms: int) -> None:
        self.state.active = True
        self.state.presented_at_ms = now_ms

    def respond(self, component_id: str, now_ms: int) -> None:
        if not self.state.active or self.state.responded:
            return
        self.state.responded = True
        self.state.response_at_ms = now_ms
        self.state.correct = (component_id == self.cfg.correct_component_id)

    def miss_if_expired(self, now_ms: int) -> bool:
        if not self.state.active or self.state.responded:
            return False
        if now_ms - self.state.presented_at_ms >= self.cfg.response_window_ms:
            self.state.responded = True
            self.state.correct = False
            return True
        return False

    def latency_ms(self) -> Optional[int]:
        if not self.state.responded:
            return None
        return self.state.response_at_ms - self.state.presented_at_ms
