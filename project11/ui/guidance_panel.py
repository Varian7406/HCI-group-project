"""Guidance panel: renders the current instruction according to condition."""
import tkinter as tk
from tkinter import ttk

from project11.models import Condition, Step


class GuidancePanel(ttk.Frame):
    def __init__(self, master, condition: Condition, **kw):
        super().__init__(master, **kw)
        self.condition = condition
        self._build()

    def _build(self) -> None:
        self.title_lbl = ttk.Label(
            self, text="Instructions",
            font=("Inter", 13, "bold"),
        )
        self.title_lbl.pack(anchor="w", padx=12, pady=(12, 4))

        self.step_lbl = ttk.Label(
            self, text="Step -/-",
            font=("Inter", 11), foreground="#6b7280",
        )
        self.step_lbl.pack(anchor="w", padx=12)

        self.instr = tk.Text(
            self, wrap="word", height=6,
            font=("Inter", 12), padx=10, pady=10,
            bg="#131720", fg="#e6e6e6",
            relief="flat", highlightthickness=1,
            highlightbackground="#262b36",
        )
        self.instr.pack(fill="both", expand=True, padx=12, pady=8)
        self.instr.configure(state="disabled")

        self.why = tk.Text(
            self, wrap="word", height=4,
            font=("Inter", 11), padx=10, pady=10,
            bg="#0f1115", fg="#a5c2ff",
            relief="flat", highlightthickness=1,
            highlightbackground="#262b36",
        )
        if self.condition == Condition.C_EXPLANATORY:
            self.why.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.why.configure(state="disabled")

    def show_step(self, step: Step, index: int, total: int) -> None:
        self.step_lbl.configure(text=f"Step {index + 1} / {total}")
        self.instr.configure(state="normal")
        self.instr.delete("1.0", "end")
        self.instr.insert("1.0", step.instruction)
        self.instr.configure(state="disabled")

        if self.condition == Condition.C_EXPLANATORY:
            self.why.configure(state="normal")
            self.why.delete("1.0", "end")
            self.why.insert("1.0",
                            step.explanation or "(no explanation provided)")
            self.why.configure(state="disabled")
