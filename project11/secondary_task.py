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
                 correct_key="Space"):
        self.target_band = target_band
        self.drift_per_second = drift_per_second
        self.correct_key = correct_key
        self.state = SecondaryState()
        self._last_tick_ms = 0
        self._direction = 1.0

    def start(self, now_ms: int) -> None:
        self._last_tick_ms = now_ms
        self.state.value = 0.5

    def tick(self, now_ms: int) -> None:
        dt = (now_ms - self._last_tick_ms) / 1000.0
        self._last_tick_ms = now_ms
        if dt <= 0:
            return
        self.state.value += self._direction * self.drift_per_second * dt
        if self.state.value >= 0.95:
            self._direction = -1.0
        elif self.state.value <= 0.05:
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
        lo, hi = self.target_band
        if self.state.value < lo or self.state.value > hi:
            self.state.value = 0.5
            self.state.corrections += 1
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
