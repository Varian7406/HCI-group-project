"""Data models used across the app.

Pure data — no Tkinter, no I/O. Easy to unit-test.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


class Condition(str, Enum):
    A_MANUAL = "A"
    B_OVERLAY = "B"
    C_EXPLANATORY = "C"


class Outcome(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IGNORED = "ignored"


@dataclass(frozen=True)
class Component:
    id: str
    label: str
    bounds: Tuple[float, float, float, float]

    def contains_norm(self, x: float, y: float) -> bool:
        l, t, r, b = self.bounds
        return l <= x <= r and t <= y <= b


@dataclass(frozen=True)
class Step:
    id: str
    instruction: str
    expected_action: str
    component_id: str
    explanation: str = ""


@dataclass(frozen=True)
class HazardConfig:
    trigger_after_step: Optional[str]
    message: str
    correct_component_id: str
    response_window_ms: int = 6000


@dataclass(frozen=True)
class SecondaryConfig:
    kind: str = "gauge"
    drift_per_second: float = 0.08
    target_band: Tuple[float, float] = (0.45, 0.55)
    correct_key: str = "Space"


@dataclass
class Procedure:
    schema_version: int
    procedure_id: str
    content_version: str
    image_rel_path: str
    source: str
    components: List[Component]
    steps: List[Step]
    hazard: HazardConfig
    secondary: SecondaryConfig = field(default_factory=SecondaryConfig)

    def component_by_id(self, cid: str) -> Optional[Component]:
        for c in self.components:
            if c.id == cid:
                return c
        return None


@dataclass
class Event:
    """One row in the CSV log."""
    schema_version: int
    app_version: str
    study_version: str
    participant_code: str
    session_id: str
    attempt_id: str
    task_id: str
    condition: str
    condition_order: int
    is_practice: bool
    event_number: int
    elapsed_ms: int
    event_type: str
    step_id: str = ""
    component_id: str = ""
    outcome: str = ""
    x_source: float = 0.0
    y_source: float = 0.0
