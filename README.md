# Project 11 — One Step at a Time

A local desktop simulation comparing three guidance conditions for a
simulated maintenance-guidance experiment.

## Requirements
- Python 3.10+
- python3-tk (system package)
- Pillow

## Install
    python3 -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate
    python -m pip install -r requirements-dev.txt

## Run
    python -m project11 --practice   # Practice mode
    python -m project11 --session    # Researcher-run study
    python -m project11              # Just open the app

## Test
    python -m pytest -q

## Analyse
    python -m analysis.analyse --input data/example --output results/example

## Tools
    python tools/make_training_panel.py      # redraw panel + rewrite procedure JSONs
    python tools/simulated_participant.py    # one bot-run attempt per condition -> data/demo
    python tools/generate_example_data.py    # 6 fake participants -> data/example

The panel image and the procedure JSONs come from ONE Python spec
(`tools/make_training_panel.py`), so the clickable regions can never drift
away from the picture. Edit the spec, re-run the tool, commit both.

## Web frontend (new)
    python -m pip install -r requirements-web.txt
    python -m uvicorn webapp.server:app --port 8000
Then open http://127.0.0.1:8000 (Firefox on the lab machines).

The web app runs the SAME experiment engine as the tkinter app
(`project11.controller` + `event_logger`); `webapp/server.py` is only a thin
adapter. Logs land in `data/raw-local/<session_id>/` in the usual schema and
pass `analysis/validate_logs.py`. Auto-pauses when the tab is hidden.

Three procedures ship, all starting from a realistic state (PC powered ON,
case CLOSED): `pc_ram` (RAM swap), `pc_gpu` (graphics card) and `pc_fan`
(case fan). The researcher picks the procedure, condition order and
participant code in the setup dialog.

Error policy: no undo anywhere. A wrong click never changes machine state;
the guidance points back at the current step, and after two wrong clicks on
the same step a "Show me" hint re-presents it (logged as HINT_SHOWN).
Conditions B/C flash the target overlay on the hint; A re-shows the text
only, as with every other presentation difference.

## Docs
See `docs/architecture.md` (how the code fits together),
`docs/requirements.md` (requirements register) and `docs/traceability.md`
(requirement -> code -> test map).
