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

## Docs
See `docs/architecture.md` (how the code fits together),
`docs/requirements.md` (requirements register) and `docs/traceability.md`
(requirement -> code -> test map).
