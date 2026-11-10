"""Event logger: the ONLY component that writes experiment events."""
import csv
from dataclasses import asdict
from pathlib import Path

from project11.models import Event


FIELDS = [
    "schema_version", "app_version", "study_version",
    "participant_code", "session_id", "attempt_id", "task_id",
    "condition", "condition_order", "is_practice",
    "event_number", "elapsed_ms", "event_type",
    "step_id", "component_id", "outcome",
    "x_source", "y_source",
]


class EventLogger:
    def __init__(self, destination: Path, attempt_id: str):
        self.destination = destination
        self.attempt_id = attempt_id
        self._file = None
        self._writer = None
        self._n = 0
        self._open()

    def _open(self) -> None:
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._file = self.destination.open("w", encoding="utf-8", newline="")
            self._writer = csv.DictWriter(self._file, fieldnames=FIELDS)
            self._writer.writeheader()
            self._file.flush()
        except OSError as e:
            raise RuntimeError(f"Cannot open log {self.destination}: {e}")

    def log(self, event: Event) -> None:
        self._n += 1
        event.event_number = self._n
        try:
            self._writer.writerow(asdict(event))
            if self._n % 5 == 0:
                self._file.flush()
        except OSError as e:
            raise RuntimeError(f"Log write failed: {e}")

    def close(self) -> None:
        if self._file:
            try:
                self._file.flush()
                self._file.close()
            except OSError:
                pass
            self._file = None
