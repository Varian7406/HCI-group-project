"""Secondary task: a gauge that drifts out of a target band."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class SecondaryState:
    value: float = 0.5
    out_of_band_since_ms: int = 0
    corrections: int = 0
    misses: int = 0
    opportunities: int = 0
    total_out_ms: int = 0
    events: List[dict] = field(default_factory=list)


class SecondaryTask:
    def __init__(self, target_band=(0.45, 0.55), drift_per_second=0.08,
                 correct_key="Space", vent_cooldown_ms=5000):
        self.target_band = target_band
        self.drift_per_second = drift_per_second
        self.correct_key = correct_key
        # Minimum time between two actual vents, so the key
        # cannot be spammed.
        self.vent_cooldown_ms = vent_cooldown_ms
        self.state = SecondaryState()
        self._last_tick_ms = 0
        self._last_correct_ms = -10**9
        self._direction = 1.0

    def start(self, now_ms: int) -> None:
        self._last_tick_ms = now_ms
        self.state.value = 0.5

    def shift(self, delta_ms: int) -> None:
        """Skip over a pause of delta_ms milliseconds."""
        self._last_tick_ms += delta_ms
        self._last_correct_ms += delta_ms
        if self.state.out_of_band_since_ms:
            self.state.out_of_band_since_ms += delta_ms

    def tick(self, now_ms: int) -> None:
        dt = (now_ms - self._last_tick_ms) / 1000.0
        self._last_tick_ms = now_ms
        if dt <= 0:
            return
        self.state.value += self._direction * self.drift_per_second * dt
        # No upper bounce: an unvented gauge must be able to climb
        # all the way to 1.0 (maximum temperature) so the overheat
        # abort and explosion can trigger.
        if self.state.value <= 0.05:
            self._direction = 1.0

        lo, hi = self.target_band
        in_band = lo <= self.state.value <= hi
        if in_band:
            if self.state.out_of_band_since_ms:
                self.state.total_out_ms += now_ms - self.state.out_of_band_since_ms
                self.state.out_of_band_since_ms = 0
        else:
            if not self.state.out_of_band_since_ms:
                self.state.out_of_band_since_ms = now_ms
                self.state.opportunities += 1

    def correct(self, now_ms: int) -> bool:

        # Enforce the vent cooldown: presses that arrive too soon
        # after the last successful vent do nothing.
        if now_ms - self._last_correct_ms < self.vent_cooldown_ms:
            return False

        lo, hi = self.target_band
        if self.state.value < lo or self.state.value > hi:
            self.state.value = 0.5
            self.state.corrections += 1
            self._last_correct_ms = now_ms
            self.state.events.append({"t": now_ms, "kind": "correction"})
            return True
        return False

    def snapshot(self) -> dict:
        return {
            "value": self.state.value,
            "corrections": self.state.corrections,
            "opportunities": self.state.opportunities,
            "total_out_ms": self.state.total_out_ms,
        }
