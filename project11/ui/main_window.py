"""Main window: researcher setup -> task view -> post-condition."""
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from uuid import uuid4

from project11 import __version__, __study_version__
from project11.controller import SessionContext, SessionController
from project11.event_logger import EventLogger
from project11.models import Condition, Procedure
from project11.procedure_loader import load_procedure
from project11.scheduler import Scheduler, now_ms
from project11.ui.guidance_panel import GuidancePanel
from project11.ui.machine_canvas import MachineCanvas
from project11.ui.researcher_setup import ResearcherSetup


ASSETS = Path(__file__).resolve().parents[2] / "assets"


class MainWindow:
    def __init__(self, root: tk.Tk, practice_mode: bool, session_mode: bool):
        self.root = root
        self.practice_mode = practice_mode
        self.controller = None
        self._tick_job = None

        self._build_chrome()
        if session_mode or practice_mode:
            self._open_setup()
        else:
            self._show_welcome()

    def _build_chrome(self) -> None:
        top = ttk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=6)
        ttk.Label(top, text="Project 11 — One Step at a Time",
                  font=("Inter", 13, "bold")).pack(side="left")
        self.status = ttk.Label(top, text="idle", foreground="#6b7280")
        self.status.pack(side="right")

        self.body = ttk.Frame(self.root)
        self.body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        bar = ttk.Frame(self.root)
        bar.pack(fill="x", padx=10, pady=(0, 8))
        self.pause_btn = ttk.Button(bar, text="Pause", command=self._toggle_pause, state="disabled")
        self.pause_btn.pack(side="left")
        self.review_btn = ttk.Button(bar, text="Review previous", command=self._review, state="disabled")
        self.review_btn.pack(side="left", padx=6)
        self.exit_btn = ttk.Button(bar, text="Exit session", command=self._exit_session)
        self.exit_btn.pack(side="right")
        self.secondary_lbl = ttk.Label(bar, text="Secondary: -.-", foreground="#8b93a7")
        self.secondary_lbl.pack(side="right", padx=10)

        self.root.bind("<space>", self._on_space)
        self.root.bind("<Escape>", lambda e: self._exit_session())

    def _clear_body(self) -> None:
        for w in self.body.winfo_children():
            w.destroy()

    def _show_welcome(self) -> None:
        self._clear_body()
        f = ttk.Frame(self.body)
        f.pack(expand=True)
        ttk.Label(f, text="Welcome", font=("Inter", 18, "bold")).pack(pady=(20, 6))
        ttk.Label(f, wraplength=520, justify="center",
                  text="This is a screen-only simulation. You will follow maintenance "
                       "instructions under three guidance conditions. Participation is "
                       "voluntary. Press 'Start researcher setup' to begin a session."
                  ).pack(pady=6)
        ttk.Button(f, text="Start researcher setup",
                   command=self._open_setup).pack(pady=14)

    def _open_setup(self) -> None:
        default_out = Path("data/raw-local")
        dlg = ResearcherSetup(self.root, default_out)
        self.root.wait_window(dlg)
        if dlg.result is None:
            return
        self._start_session(dlg.result)

    def _start_session(self, info: dict) -> None:
        proc_path = ASSETS / "procedures" / "example_procedure.json"
        try:
            self.procedure = load_procedure(proc_path)
        except ValueError as e:
            messagebox.showerror("Procedure error", str(e))
            return

        order = info["order"]
        conditions = [Condition[c] for c in order]
        self._order = conditions
        self._order_index = 0
        self._info = info
        self._out_dir = info["output_dir"] / info["session_id"]
        self._start_condition(conditions[0])

    def _start_condition(self, cond: Condition) -> None:
        self._clear_body()
        left = MachineCanvas(self.body, on_click=self._on_machine_click)
        left.pack(side="left", fill="both", expand=True)
        right = GuidancePanel(self.body, condition=cond)
        right.pack(side="right", fill="y", padx=(10, 0))

        img_path = ASSETS / self.procedure.image_rel_path
        if not img_path.exists():
            messagebox.showwarning(
                "Missing image",
                f"Expected {img_path}. Using placeholder; clicks will not match components."
            )
        else:
            left.load_image(img_path)
        left.set_components(self.procedure.components)

        attempt_id = uuid4().hex[:8]
        log_path = self._out_dir / f"attempt_{cond.value}_{attempt_id}.csv"
        logger = EventLogger(log_path, attempt_id)

        ctx = SessionContext(
            participant_code=self._info["participant_code"],
            session_id=self._info["session_id"],
            condition=cond,
            condition_order=self._order.index(cond) + 1,
            is_practice=self._info["is_practice"],
            task_id=self._info["task_id"],
        )
        sched = Scheduler(after_fn=self.root.after,
                          cancel_fn=self.root.after_cancel)
        self.controller = SessionController(self.procedure, ctx, logger, sched)
        self._canvas = left
        self._guidance = right
        self._logger = logger
        self._cond = cond

        self.controller.start(now_ms())
        self._refresh_step()
        self.pause_btn.configure(state="normal")
        self.review_btn.configure(state="normal")
        self._tick()

    def _refresh_step(self) -> None:
        step = self.controller.current_step()
        self._guidance.show_step(step, self.controller.step_index,
                                 len(self.procedure.steps))
        comp = self.procedure.component_by_id(step.component_id)
        self._canvas.show_highlight(comp, self._cond)

    def _on_machine_click(self, component_id, xn, yn) -> None:
        if not self.controller or self.controller.completed or self.controller.aborted:
            return
        self.controller.handle_click(component_id, now_ms(), xn, yn)
        if self.controller.completed:
            self._condition_finished()
        else:
            self._refresh_step()

    def _on_space(self, _event) -> None:
        if not self.controller:
            return
        self.controller.secondary.correct(now_ms())

    def _tick(self) -> None:
        if not self.controller or self.controller.completed or self.controller.aborted:
            return
        t = now_ms()
        self.controller.secondary.tick(t)
        self.controller.hazard.miss_if_expired(t)
        s = self.controller.secondary.snapshot()
        self.secondary_lbl.configure(
            text=f"Secondary: {s['value']:.2f}  "
                 f"(corr {s['corrections']}/{s['opportunities']})"
        )
        self.status.configure(text=f"elapsed {self.controller.sched.elapsed_ms()} ms")
        self._tick_job = self.root.after(50, self._tick)

    def _toggle_pause(self) -> None:
        if not self.controller:
            return
        if self.pause_btn.cget("text") == "Pause":
            self.controller.pause(now_ms())
            self.pause_btn.configure(text="Resume")
        else:
            self.controller.resume(now_ms())
            self.pause_btn.configure(text="Pause")

    def _review(self) -> None:
        if not self.controller:
            return
        prev_id = self.controller.review_previous(now_ms())
        if prev_id:
            prev = next(s for s in self.procedure.steps if s.id == prev_id)
            self._guidance.show_step(prev, self.controller.step_index - 1,
                                     len(self.procedure.steps))

    def _exit_session(self) -> None:
        if not self.controller:
            self._show_welcome()
            return
        if not self.controller.completed and not self.controller.aborted:
            self.controller.abort(now_ms())
        self._teardown_condition()
        self._show_welcome()

    def _condition_finished(self) -> None:
        self._teardown_condition()
        self._order_index += 1
        if self._order_index >= len(self._order):
            messagebox.showinfo("Session complete",
                                "All conditions completed. Thank you.")
            self._show_welcome()
        else:
            messagebox.showinfo("Break",
                                f"Condition {self._cond.value} complete. "
                                "Take a short break, then press OK to continue.")
            self._start_condition(self._order[self._order_index])

    def _teardown_condition(self) -> None:
        if self._tick_job:
            self.root.after_cancel(self._tick_job)
            self._tick_job = None
        if self.controller:
            try:
                self.controller.sched.cancel_all()
                self._logger.close()
            except Exception:
                pass
        self.controller = None
        self.pause_btn.configure(state="disabled", text="Pause")
        self.review_btn.configure(state="disabled")

    def on_close(self) -> None:
        if self.controller and not self.controller.completed:
            self.controller.abort(now_ms())
        self._teardown_condition()
        self.root.destroy()
