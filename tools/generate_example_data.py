"""Generate example study data with simulated participants.

Creates a small fake dataset (a few participants x three conditions) under
data/example/, ready for the analysis pipeline:

    python tools/generate_example_data.py
    python -m analysis.analyse --input data/example --output results/example
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from project11.models import Condition
from project11.procedure_loader import load_procedure
from tools.simulated_participant import BotProfile, simulate_attempt

N_PARTICIPANTS = 6
ORDERS = ["ABC", "BCA", "CAB"]     # counterbalanced condition orders


def main() -> None:
    proc = load_procedure(Path("assets/procedures/example_procedure.json"))
    out_root = Path("data/example")
    rng = random.Random(7)

    for p in range(1, N_PARTICIPANTS + 1):
        code = f"P{p:02d}"
        session_id = f"ex{p:02d}"
        order = ORDERS[(p - 1) % len(ORDERS)]
        # Everyone gets slightly different speed/accuracy, like real people.
        profile = BotProfile(
            step_seconds=rng.uniform(2.5, 5.0),
            error_prob=rng.uniform(0.02, 0.10),
            hazard_respond_prob=rng.uniform(0.75, 1.0),
        )
        out_dir = out_root / session_id
        for i, cond_id in enumerate(order, start=1):
            path = simulate_attempt(proc, out_dir, code, session_id,
                                    Condition(cond_id), i, profile, rng)
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
