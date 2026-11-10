"""Machine canvas: shows the procedure image, letterboxed, with overlays."""
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk

from project11.geometry import (
    Layout, display_to_norm, norm_to_display_rect,
)
from project11.models import Condition


class MachineCanvas(tk.Canvas):
    def __init__(self, master, on_click, **kw):
        super().__init__(master, highlightthickness=0, bg="#1b1f27", **kw)
        self._on_click = on_click
        self._layout = None
        self._photo = None
        self._overlay_ids = []
        self._components = []
        self.bind("<Configure>", self._on_resize)
        self.bind("<Button-1>", self._on_click_event)

    def load_image(self, image_path: Path) -> None:
        self._src_image = Image.open(image_path).convert("RGBA")
        self._redraw()

    def _on_resize(self, _event) -> None:
        self._redraw()

    def _redraw(self) -> None:
        if not hasattr(self, "_src_image"):
            return
        cw = self.winfo_width() or 800
        ch = self.winfo_height() or 600
        sw, sh = self._src_image.size
        self._layout = Layout(cw, ch, sw, sh).compute()
        L = self._layout
        resized = self._src_image.resize((L.display_w, L.display_h))
        self._photo = ImageTk.PhotoImage(resized)
        self.delete("all")
        self.create_image(L.offset_x, L.offset_y, anchor="nw", image=self._photo)
        self._overlay_ids = []

    def show_highlight(self, component, condition: Condition) -> None:
        if not self._layout:
            return
        for oid in self._overlay_ids:
            self.delete(oid)
        self._overlay_ids = []
        if condition == Condition.A_MANUAL:
            return
        x1, y1, x2, y2 = norm_to_display_rect(self._layout, component.bounds)
        colour = "#2d6cdf" if condition == Condition.B_OVERLAY else "#2ea043"
        oid = self.create_rectangle(x1, y1, x2, y2,
                                    outline=colour, width=3, dash=(6, 3))
        self._overlay_ids.append(oid)
        cx = (x1 + x2) // 2
        self._overlay_ids.append(
            self.create_text(cx, y1 - 12, text=f"-> {component.label}",
                             fill=colour, font=("Inter", 11, "bold"))
        )

    def _on_click_event(self, event) -> None:
        if not self._layout:
            return
        norm = display_to_norm(self._layout, event.x, event.y)
        if norm is None:
            return
        xn, yn = norm
        for c in self._components:
            if c.contains_norm(xn, yn):
                self._on_click(c.id, xn, yn)
                return

    def set_components(self, components) -> None:
        self._components = components
