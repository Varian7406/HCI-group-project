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
