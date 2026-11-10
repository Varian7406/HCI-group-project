"""Geometry tests (R02)."""
from project11.geometry import Layout, display_to_norm, norm_to_display_rect


def _layout():
    return Layout(canvas_w=800, canvas_h=600,
                  img_src_w=1000, img_src_h=500).compute()


def test_letterbox_margins_rejected():
    L = _layout()
    assert display_to_norm(L, 5, 5) is None


def test_round_trip():
    L = _layout()
    bounds = (0.2, 0.3, 0.5, 0.6)
    x1, y1, x2, y2 = norm_to_display_rect(L, bounds)
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    xn, yn = display_to_norm(L, cx, cy)
    assert abs(xn - 0.35) < 0.02
    assert abs(yn - 0.45) < 0.02
