"""Researcher setup dialog."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from uuid import uuid4

from project11.models import Condition


ORDER_CHOICES = ["ABC", "ACB", "BAC", "BCA", "CAB", "CBA"]


class ResearcherSetup(tk.Toplevel):
    def __init__(self, master, default_output: Path):
        super().__init__(master)
        self.title("Researcher — new session")
        self.geometry("480x360")
        self.result = None
        self._default_output = default_output
        self._build()
        self.grab_set()
        self.transient(master)

    def _build(self) -> None:
        f = ttk.Frame(self, padding=16)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Participant code:").grid(row=0, column=0, sticky="w")
        self.code_var = tk.StringVar(value=f"P{uuid4().hex[:4].upper()}")
        ttk.Entry(f, textvariable=self.code_var, width=16).grid(row=0, column=1, sticky="w")

        ttk.Label(f, text="Session ID:").grid(row=1, column=0, sticky="w", pady=6)
        self.session_var = tk.StringVar(value=uuid4().hex[:8])
        ttk.Entry(f, textvariable=self.session_var, width=20).grid(row=1, column=1, sticky="w")

        ttk.Label(f, text="Condition order:").grid(row=2, column=0, sticky="w")
        self.order_var = tk.StringVar(value=ORDER_CHOICES[0])
        ttk.Combobox(f, textvariable=self.order_var,
                     values=ORDER_CHOICES, state="readonly", width=10
                     ).grid(row=2, column=1, sticky="w")

        ttk.Label(f, text="Task ID:").grid(row=3, column=0, sticky="w", pady=6)
        self.task_var = tk.StringVar(value="task_01")
        ttk.Entry(f, textvariable=self.task_var, width=16).grid(row=3, column=1, sticky="w")

        self.practice_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(f, text="Mark as practice / pilot",
                        variable=self.practice_var).grid(row=4, column=0, columnspan=2, sticky="w", pady=6)

        ttk.Label(f, text="Output folder:").grid(row=5, column=0, sticky="w")
        self.out_var = tk.StringVar(value=str(self._default_output))
        ttk.Entry(f, textvariable=self.out_var, width=36).grid(row=5, column=1, sticky="w")
        ttk.Button(f, text="Browse...", command=self._browse).grid(row=5, column=2, padx=6)

        btns = ttk.Frame(f)
        btns.grid(row=6, column=0, columnspan=3, pady=18, sticky="e")
        ttk.Button(btns, text="Cancel", command=self._cancel).pack(side="right")
        ttk.Button(btns, text="Start session", command=self._ok).pack(side="right", padx=6)

    def _browse(self) -> None:
        d = filedialog.askdirectory(initialdir=self.out_var.get())
        if d:
            self.out_var.set(d)

    def _cancel(self) -> None:
        self.result = None
        self.destroy()

    def _ok(self) -> None:
        code = self.code_var.get().strip()
        sid = self.session_var.get().strip()
        if not code or not sid:
            messagebox.showerror("Missing", "Participant code and session ID are required.")
            return
        self.result = {
            "participant_code": code,
            "session_id": sid,
            "order": self.order_var.get(),
            "task_id": self.task_var.get().strip(),
            "is_practice": self.practice_var.get(),
            "output_dir": Path(self.out_var.get()),
        }
        self.destroy()
