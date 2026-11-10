"""Validate CSV logs against the event schema."""
import csv
from pathlib import Path

from project11.event_logger import FIELDS


def validate(path: Path) -> list:
    errors = []
    if not path.exists():
        return [f"missing: {path}"]
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            errors.append(f"{path}: fieldnames mismatch")
        prev_n = 0
        prev_t = -1
        has_start = has_end = False
        for row in reader:
            n = int(row["event_number"])
            t = int(row["elapsed_ms"])
            if n != prev_n + 1:
                errors.append(f"{path}: event_number not monotonic at {n}")
            if t < prev_t:
                errors.append(f"{path}: elapsed_ms decreased at {n}")
            prev_n, prev_t = n, t
            if row["event_type"] == "SESSION_STARTED": has_start = True
            if row["event_type"] == "SESSION_ENDED": has_end = True
        if not has_start: errors.append(f"{path}: no SESSION_STARTED")
        if not has_end:   errors.append(f"{path}: no SESSION_ENDED")
    return errors


if __name__ == "__main__":
    import sys
    for p in sys.argv[1:]:
        errs = validate(Path(p))
        print(p, "OK" if not errs else errs)
