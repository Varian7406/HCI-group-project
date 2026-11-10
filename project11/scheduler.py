"""Scheduler: owns active timers, supports pause/resume (R04)."""
import time
from typing import Callable, Dict, Optional


def now_ms() -> int:
    return time.perf_counter_ns() // 1_000_000


class Scheduler:
    def __init__(self, clock=now_ms, after_fn=None, cancel_fn=None):
        self._clock = clock
        self._after_fn = after_fn or (lambda d, c: None)
        self._cancel_fn = cancel_fn or (lambda tid: None)
        self._timers: Dict[str, dict] = {}
        self._paused_at: Optional[int] = None
        self._total_paused_ms: int = 0
        self._session_start: int = clock()

    def elapsed_ms(self) -> int:
        if self._paused_at is not None:
            return self._paused_at - self._session_start - self._total_paused_ms
        return self._clock() - self._session_start - self._total_paused_ms

    def schedule(self, name: str, delay_ms: int, callback: Callable) -> None:
        self.cancel(name)
        fire_at = self._clock() + delay_ms
        self._timers[name] = {
            "fire_at": fire_at,
            "remaining": delay_ms,
            "callback": callback,
            "tid": self._after_fn(delay_ms, callback),
        }

    def cancel(self, name: str) -> None:
        t = self._timers.pop(name, None)
        if t:
            self._cancel_fn(t["tid"])

    def pause(self) -> None:
        if self._paused_at is not None:
            return
        self._paused_at = self._clock()
        for name, t in list(self._timers.items()):
            self._cancel_fn(t["tid"])
            t["remaining"] = max(0, t["fire_at"] - self._paused_at)

    def resume(self) -> None:
        if self._paused_at is None:
            return
        paused_for = self._clock() - self._paused_at
        self._total_paused_ms += paused_for
        self._paused_at = None
        for name, t in self._timers.items():
            t["fire_at"] = self._clock() + t["remaining"]
            t["tid"] = self._after_fn(t["remaining"], t["callback"])

    def cancel_all(self) -> None:
        for name in list(self._timers.keys()):
            self.cancel(name)
