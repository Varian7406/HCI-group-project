"""Descriptive analysis: per-participant / per-condition summaries."""
import argparse
import csv
from pathlib import Path


def summarise(log_dir: Path) -> list:
    rows = []
    # Logs live in per-session folders: data/<input>/<session_id>/attempt_*.csv
    for p in sorted(log_dir.glob("**/attempt_*.csv")):
        with p.open(encoding="utf-8") as f:
            events = list(csv.DictReader(f))
        if not events:
            continue
        first = events[0]
        start = next((e for e in events if e["event_type"] == "TASK_STARTED"), None)
        end = next((e for e in events if e["event_type"] == "TASK_COMPLETED"), None)
        errors = sum(1 for e in events if e["event_type"] == "ACTION_REJECTED")
        hazard = next((e for e in events if e["event_type"] == "HAZARD_RESPONSE"), None)
        rows.append({
            "file": p.name,
            "participant": first["participant_code"],
            "condition": first["condition"],
            "task_id": first["task_id"],
            "is_practice": first["is_practice"],
            "completed": end is not None,
            "completion_ms": int(end["elapsed_ms"]) - int(start["elapsed_ms"])
                             if start and end else None,
            "errors": errors,
            "hazard_correct": hazard["outcome"] == "accepted" if hazard else None,
        })
    return rows


def write_summary(rows, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "summary.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    rows = summarise(args.input)
    if not rows:
        print("No logs found."); return
    write_summary(rows, args.output)


if __name__ == "__main__":
    main()
