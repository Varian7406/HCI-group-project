"""Pause / resume with an injected fake clock (R04)."""
from project11.scheduler import Scheduler


def test_pause_freezes_elapsed():
    t = [1000]
    s = Scheduler(clock=lambda: t[0])
    assert s.elapsed_ms() == 0
    t[0] = 2000
    assert s.elapsed_ms() == 1000
    s.pause()
    t[0] = 5000
    assert s.elapsed_ms() == 1000
    s.resume()
    t[0] = 6000
    assert s.elapsed_ms() == 2000


def test_schedule_respects_pause():
    t = [0]
    fired = []
    s = Scheduler(clock=lambda: t[0],
                  after_fn=lambda d, c: (t, d, c),
                  cancel_fn=lambda tid: None)
    s.schedule("x", 500, lambda: fired.append(1))
    assert "x" in s._timers
    s.pause()
    assert s._timers["x"]["remaining"] == 500
    t[0] = 1000
    s.resume()
    assert s._timers["x"]["remaining"] == 500
