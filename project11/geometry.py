"""Map normalised source-image coordinates to display pixels (R02)."""
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class Layout:
    canvas_w: int
    canvas_h: int
    img_src_w: int
    img_src_h: int
    display_w: int = 0
    display_h: int = 0
    offset_x: int = 0
    offset_y: int = 0

    def compute(self) -> "Layout":
        scale = min(self.canvas_w / self.img_src_w,
                    self.canvas_h / self.img_src_h)
        self.display_w = int(self.img_src_w * scale)
        self.display_h = int(self.img_src_h * scale)
        self.offset_x = (self.canvas_w - self.display_w) // 2
        self.offset_y = (self.canvas_h - self.display_h) // 2
        return self


def display_to_norm(layout: Layout, x: int, y: int) -> Optional[Tuple[float, float]]:
    if not (layout.offset_x <= x < layout.offset_x + layout.display_w
            and layout.offset_y <= y < layout.offset_y + layout.display_h):
        return None
    rel_x = (x - layout.offset_x) / layout.display_w
    rel_y = (y - layout.offset_y) / layout.display_h
    return max(0.0, min(1.0, rel_x)), max(0.0, min(1.0, rel_y))


def norm_to_display_rect(layout: Layout, bounds):
    l, t, r, b = bounds
    x1 = layout.offset_x + int(l * layout.display_w)
    y1 = layout.offset_y + int(t * layout.display_h)
    x2 = layout.offset_x + int(r * layout.display_w)
    y2 = layout.offset_y + int(b * layout.display_h)
    return x1, y1, x2, y2
