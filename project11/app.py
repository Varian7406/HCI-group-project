"""Top-level launcher: builds the main Tk window."""
import tkinter as tk
from project11.ui.main_window import MainWindow


def run_app(practice: bool = False, session: bool = False) -> None:
    root = tk.Tk()
    root.title("Project 11 — One Step at a Time")
    root.geometry("1200x760")
    app = MainWindow(root, practice_mode=practice, session_mode=session)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
