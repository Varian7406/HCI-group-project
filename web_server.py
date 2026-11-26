

from __future__ import annotations

import csv
import random
import re
import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from project11.controller import SessionContext, SessionController
from project11.event_logger import EventLogger
from project11.models import Condition, Outcome, Step
from project11.procedure_loader import load_procedure
from project11.scheduler import Scheduler, now_ms


# ============================================================
# APPLICATION SETUP
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR / "static")),
    name="static",
)

app.mount(
    "/assets",
    StaticFiles(directory=str(BASE_DIR / "assets")),
    name="assets",
)


# ============================================================
# SESSION SETTINGS
# ============================================================

# The active condition. The welcome page sets this through
# POST /condition before the training session starts.
current_condition = Condition.B_OVERLAY

# The participant number entered on the welcome page. It is used
# as the participant_code in every logged event, so the data of
# each participant can be told apart in the CSV files.
current_participant = "WEB_USER"

# The hardware version of the PC shown in the session. Every
# condition (A, B, C) has three versions that each change one
# component separately: "ram" (different RAM), "gpu" (different
# graphics card) and "fans" (all fans different). When the welcome
# page does not pick one, a version is chosen at random.
VARIANTS = ["ram", "gpu", "fans"]

current_variant = "ram"


def build_variant_steps(variant: str):
    """
    Return the actual tutorial procedure for the selected hardware version.

    A/B/C are the guidance conditions. The hardware version (RAM/GPU/fans)
    decides which component-replacement task is taught.
    """
    if variant == "gpu":
        definitions = [
            ("s01", "Shut down the PC through its operating system. Wait until all fans and lights have stopped, then click the case power button to confirm shutdown.", "select", "power_button", "A full shutdown is required before working inside the computer."),
            ("s02", "Switch the power supply unit (PSU) to 0 (OFF).", "toggle", "psu_switch", "This prevents the PSU from supplying power to the system."),
            ("s03", "Disconnect the AC power cable from the back of the computer.", "remove", "power_cable", "Never remove internal components while the PC is connected to mains power."),
            ("s04", "Remove the tempered-glass side panel. Touch unpainted metal on the case or use an anti-static wrist strap before handling the graphics card.", "remove", "glass_panel", "This gives access to the graphics card and helps reduce electrostatic-discharge risk."),
            ("s05", "Disconnect the graphics card's PCIe power cable from the card.", "remove", "cable_gpu", "Release the connector latch and pull the plug by its housing, not by the wires."),
            ("s06", "Remove the existing graphics card from the PCIe slot. Release the slot latch and remove the bracket screws first.", "remove", "gpu", "Support the card while releasing it so that it does not drop or bend the PCIe slot."),
            ("s07", "Install the replacement graphics card into the PCIe x16 slot. Press evenly until the slot latch engages, then secure the bracket.", "install", "gpu", "Align the card with the slot and avoid forcing it. Check the card is fully seated."),
            ("s08", "Reconnect the PCIe power cable to the replacement graphics card.", "install", "cable_gpu", "Make sure the connector is fully seated and its latch clicks into place."),
            ("s09", "Reinstall the tempered-glass side panel.", "install", "glass_panel", "Check that no cables are trapped and the panel is properly secured."),
            ("s10", "Reconnect the AC power cable to the computer.", "install", "power_cable", "Reconnect mains power only after the case is closed."),
            ("s11", "Switch the PSU back to I (ON).", "toggle", "psu_switch", "The computer can now receive power."),
            ("s12", "Press the case power button to start the PC.", "select", "power_button", "Check that the system starts and detects the replacement graphics card."),
        ]
    elif variant == "fans":
        definitions = [
            ("s01", "Shut down the PC through its operating system. Wait until all fans and lights have stopped, then click the case power button to confirm shutdown.", "select", "power_button", "A full shutdown is required before working inside the computer."),
            ("s02", "Switch the power supply unit (PSU) to 0 (OFF).", "toggle", "psu_switch", "This prevents the PSU from supplying power to the system."),
            ("s03", "Disconnect the AC power cable from the back of the computer.", "remove", "power_cable", "Never replace fans while the PC is connected to mains power."),
            ("s04", "Remove the tempered-glass side panel. Touch unpainted metal on the case or use an anti-static wrist strap before handling internal parts.", "remove", "glass_panel", "This gives access to the case fans and their motherboard headers."),
            ("s05", "Remove the upper front case fan. Disconnect its 3-pin or 4-pin fan header before removing it.", "remove", "front_fan_1", "Pull the connector by its housing, not by the wires. Keep track of the mounting screws."),
            ("s06", "Remove the middle front case fan and disconnect its fan header.", "remove", "front_fan_2", "Keep the fan screws together so they can be reused for the replacement."),
            ("s07", "Remove the lower front case fan and disconnect its fan header.", "remove", "front_fan_3", "Make sure all three original front fans have been removed."),
            ("s08", "Install the replacement upper front fan and connect its fan header to a compatible motherboard fan header.", "install", "front_fan_1", "Match the airflow arrow on the fan frame to the intended front-to-back airflow direction."),
            ("s09", "Install the replacement middle front fan and connect its fan header.", "install", "front_fan_2", "Tighten the screws evenly without overtightening them."),
            ("s10", "Install the replacement lower front fan and connect its fan header.", "install", "front_fan_3", "Check that the fan cable cannot touch the blades."),
            ("s11", "Reinstall the tempered-glass side panel.", "install", "glass_panel", "Check that no cables are trapped and the panel is properly secured."),
            ("s12", "Reconnect the AC power cable to the computer.", "install", "power_cable", "Reconnect mains power only after the case is closed."),
            ("s13", "Switch the PSU back to I (ON).", "toggle", "psu_switch", "The computer can now receive power."),
            ("s14", "Press the case power button to start the PC. Check that the replacement fans spin freely.", "select", "power_button", "Listen for unusual noise and confirm that all replacement fans operate."),
        ]
    else:
        return None

    return [
        Step(
            id=step_id,
            instruction=instruction,
            expected_action=action,
            component_id=component_id,
            explanation=explanation,
        )
        for step_id, instruction, action, component_id, explanation in definitions
    ]

VALID_CONDITIONS = {
    "A": Condition.A_MANUAL,
    "B": Condition.B_OVERLAY,
    "C": Condition.C_EXPLANATORY,
}

# Participant numbers: letters, digits, dashes and underscores.
PARTICIPANT_PATTERN = re.compile(r"^[A-Za-z0-9_-]{2,32}$")


def sanitize_participant(raw: str) -> str | None:
    """
    Normalise a participant number, or return None when it is
    not usable (empty, too short, or contains other characters).
    """

    if raw is None:
        return None

    code = raw.strip()

    if not PARTICIPANT_PATTERN.match(code):
        return None

    return code

PROCEDURE_PATH = (
    BASE_DIR / "assets" / "procedures" / "example_procedure.json"
)

LOG_DIR = BASE_DIR / "data" / "raw-local"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# One summary row per finished session (completed or failed),
# appended here so progress can be checked at a glance.
SUMMARY_PATH = LOG_DIR / "participant_summaries.csv"

# The session id already written to the summary file, so a
# finished session is never summarised twice.
last_summarised_session = None

controller = None
logger = None
background_thread = None
stop_event = None

session_lock = threading.RLock()
reset_lock = threading.Lock()


# ============================================================
# BACKGROUND TASK
# ============================================================

def background_tick(session_controller, session_stop_event):
    """
    Update the secondary task and trigger scripted hazards.
    """
    while not session_stop_event.is_set():
        time.sleep(0.05)

        with session_lock:
            if session_stop_event.is_set():
                break

            if session_controller.completed or session_controller.aborted:
                break

            # Nothing moves while the session is paused.
            if session_controller.paused:
                continue

            current_time = now_ms()

            # Update the secondary task.
            session_controller.secondary.tick(current_time)

            # Present a hazard after its configured trigger step.
            if session_controller.hazard.armed:
                session_controller.hazard.present(current_time)

            # Check whether the hazard response time expired.
            session_controller.hazard.miss_if_expired(current_time)
            
            # --- NEW: Check for Critical Overheat ---
            if session_controller.secondary.state.value >= 1.0:
                session_controller.aborted = True
                break

# ============================================================
# CREATE A COMPLETELY FRESH SESSION
# ============================================================

def reset_session():
    """
    Stop the previous session and create a completely new one.

    This resets:
    - Tutorial step
    - Completed actions
    - Hazard state
    - Secondary task
    - Session timer
    - Event log
    """

    global controller
    global logger
    global background_thread
    global stop_event

    # Prevent two simultaneous refreshes from creating
    # competing sessions.
    with reset_lock:

        old_thread = None
        old_logger = None

        # Stop the previous background thread.
        with session_lock:

            if stop_event is not None:
                stop_event.set()

            old_thread = background_thread
            old_logger = logger

        # Wait for the old background thread to finish.
        if old_thread is not None and old_thread.is_alive():
            old_thread.join(timeout=1.0)

        # Close the previous event log.
        if old_logger is not None:
            old_logger.close()

        # Load a fresh copy of the procedure.
        procedure = load_procedure(PROCEDURE_PATH)

        # The RAM version uses the original JSON procedure. GPU and fan
        # versions receive their own real replacement steps.
        variant_steps = build_variant_steps(current_variant)
        if variant_steps is not None:
            procedure.steps = variant_steps
            procedure.procedure_id = f"{procedure.procedure_id}_{current_variant}"
            procedure.content_version = f"{procedure.content_version}-{current_variant}"

        # Give this session a unique identifier.
        session_id = uuid.uuid4().hex[:12]

        ctx = SessionContext(
            participant_code=current_participant,
            session_id=session_id,
            condition=current_condition,
            condition_order=1,
            is_practice=True,
            task_id="WEB_TASK",
        )

        # EventLogger opens the CSV in write mode.
        # Therefore, each fresh session starts with a clean log.
               # Create a separate log file for this training attempt.
        # The filename carries the participant number and the
        # condition, so the data of each attempt is identifiable
        # without opening the file.
        new_logger = EventLogger(
            LOG_DIR / (
                f"{current_participant}_"
                f"{current_condition.value}_"
                f"{current_variant}_"
                f"{session_id}.csv"
            ),
            session_id,
        )

        # Create a completely new controller.
        new_controller = SessionController(
            procedure,
            ctx,
            new_logger,
            # Pause-aware, so paused time is left out of elapsed_ms.
            Scheduler(),
        )

        # Start at tutorial step zero.
        new_controller.start(now_ms())

        new_stop_event = threading.Event()

        new_thread = threading.Thread(
            target=background_tick,
            args=(new_controller, new_stop_event),
            daemon=True,
        )

        # Replace the global session.
        with session_lock:

            controller = new_controller
            logger = new_logger
            stop_event = new_stop_event
            background_thread = new_thread

        new_thread.start()

        return session_id


# ============================================================
# CONDITION SELECTION (WELCOME PAGE)
# ============================================================

@app.post("/condition")
async def select_condition(request: Request):
    """
    Called by the welcome page when the participant enters their
    number and picks a condition. Sets the participant and the
    active condition, then starts a fresh session under them.
    """

    global current_condition
    global current_participant
    global current_variant

    data = await request.json()

    participant = sanitize_participant(data.get("participant_id"))

    if participant is None:
        return {
            "ok": False,
            "message": (
                "Please enter a participant number of 2-32 "
                "letters, digits, dashes or underscores."
            ),
        }

    chosen = str(data.get("condition", "")).upper()

    if chosen not in VALID_CONDITIONS:
        return {"ok": False, "message": "Unknown condition."}

    # The hardware version: taken from the request when it names
    # one of the three versions, otherwise drawn at random, so
    # every session sees one of the three versions of its
    # condition.
    requested_variant = str(data.get("variant", "")).lower()

    if requested_variant in VARIANTS:
        current_variant = requested_variant

    else:
        current_variant = random.choice(VARIANTS)

    current_participant = participant
    current_condition = VALID_CONDITIONS[chosen]

    session_id = reset_session()

    return {
        "ok": True,
        "participant_id": current_participant,
        "condition": current_condition.value,
        "variant": current_variant,
        "session_id": session_id,
        "message": f"Condition {current_condition.value} started.",
    }


@app.get("/condition")
def get_condition():

    return {"condition": current_condition.value}


# ============================================================
# RESET ENDPOINT
# ============================================================

@app.post("/reset")
def reset_endpoint():
    """
    Called whenever the website is loaded or refreshed.
    """

    session_id = reset_session()

    return {
        "ok": True,
        "session_id": session_id,
        "message": "Training session restarted.",
    }


# ============================================================
# APPLICATION STARTUP AND SHUTDOWN
# ============================================================

@app.on_event("startup")
async def startup():
    """
    The browser creates the session by calling POST /reset.

    We deliberately do not create a session here, because that
    would create an unnecessary extra session on every page load.
    """
    pass


@app.on_event("shutdown")
async def shutdown():

    global stop_event
    global background_thread
    global logger

    with session_lock:

        if stop_event is not None:
            stop_event.set()

        thread_to_stop = background_thread
        logger_to_close = logger

    if thread_to_stop is not None and thread_to_stop.is_alive():
        thread_to_stop.join(timeout=1.0)

    if logger_to_close is not None:
        logger_to_close.close()


# ============================================================
# GET CURRENT SESSION STATE
# ============================================================

@app.get("/state")
def get_state():

    with session_lock:

        if controller is None:
            return {"status": "idle"}

        if controller.completed:
            status = "completed"

        elif controller.aborted:
            status = "aborted"

        else:
            status = "running"

        step = controller.current_step()

        component = controller.proc.component_by_id(
            step.component_id
        )

        secondary = controller.secondary.snapshot()
        hazard = controller.hazard.state
        
        # --- NEW: Determine failure reason ---
        failure_reason = None
        if status == "aborted" and secondary.get("value", 0) >= 0.99:
            failure_reason = "overheat"

        return {
            "status": status,
            "paused": controller.paused,
            "failure_reason": failure_reason,

            "step_index": controller.step_index,
            "total_steps": len(controller.proc.steps),

            "instruction": step.instruction,
            "expected_action": step.expected_action,
            "explanation": step.explanation or "",

            "components": [
                {
                    "id": component.id,
                    "label": component.label,
                    "bounds": list(component.bounds),
                }
                for component in controller.proc.components
            ],

            "highlight": {
                "component_id": step.component_id,
                "label": component.label if component else "",
                "bounds": (
                    list(component.bounds)
                    if component
                    else None
                ),
            },

            "condition": current_condition.value,

            "participant_code": current_participant,

            "variant": current_variant,

            "secondary": secondary,

            "hazard": {
                "active": (
                    hazard.active
                    and not hazard.responded
                ),

                "responded": hazard.responded,
                "correct": hazard.correct,

                "message": controller.proc.hazard.message,

                "correct_component_id": (
                    controller.proc.hazard.correct_component_id
                ),
            },

            "elapsed_ms": controller.sched.elapsed_ms(),
        }


# ============================================================
# COMPONENT CLICK
# ============================================================

@app.post("/click")
async def handle_click(request: Request):

    data = await request.json()

    # "outcome" tells the frontend which sound to play.
    outcome = Outcome.IGNORED

    with session_lock:

        if (
            controller is not None
            and not controller.completed
            and not controller.aborted
        ):

            outcome = controller.handle_click(
                data["component_id"],
                now_ms(),
                data.get("xn", 0.5),
                data.get("yn", 0.5),
            )

    return {"ok": True, "outcome": outcome.value}


# ============================================================
# PAUSE AND RESUME
# ============================================================

def set_paused(paused: bool):

    with session_lock:

        if controller is None:
            return {"ok": False, "paused": False}

        if paused:
            controller.pause(now_ms())

        else:
            controller.resume(now_ms())

        return {"ok": True, "paused": controller.paused}


@app.post("/pause")
def pause_endpoint():

    return set_paused(True)


@app.post("/resume")
def resume_endpoint():

    return set_paused(False)


# ============================================================
# SECONDARY TASK
# ============================================================

@app.post("/secondary")
def handle_secondary():

    vented = False

    with session_lock:

        if (
            controller is not None
            and not controller.completed
            and not controller.aborted
            and not controller.paused
        ):

            vented = controller.secondary.correct(now_ms())

    # "vented" tells the frontend whether the press was accepted
    # or blocked by the cooldown, so its countdown stays in sync.
    return {"ok": True, "vented": vented}


# ============================================================
# FINISH SESSION (SAVE PROGRESS)
# ============================================================

SUMMARY_FIELDS = [
    "saved_at",
    "participant_code",
    "condition",
    "variant",
    "session_id",
    "outcome",
    "steps_completed",
    "total_steps",
    "elapsed_ms",
]


@app.post("/finish")
def finish_session():
    """
    Called once by the training page when the session ends,
    either completed or failed. Appends one summary row for the
    participant, so their progress is saved under their number.
    """

    global last_summarised_session

    with session_lock:

        if controller is None:
            return {"ok": False, "message": "No active session."}

        if controller.completed:
            outcome = "completed"

        elif controller.aborted:
            outcome = "aborted"

        else:
            # The session is still running: nothing to save yet.
            return {"ok": False, "message": "Session still running."}

        if last_summarised_session == controller.ctx.session_id:
            return {"ok": True, "message": "Already saved."}

        SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)

        is_new_file = not SUMMARY_PATH.exists()

        try:
            with SUMMARY_PATH.open("a", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)

                if is_new_file:
                    writer.writeheader()

                writer.writerow({
                    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "participant_code": controller.ctx.participant_code,
                    "condition": controller.ctx.condition.value,
                    "variant": current_variant,
                    "session_id": controller.ctx.session_id,
                    "outcome": outcome,
                    "steps_completed": controller.step_index,
                    "total_steps": len(controller.proc.steps),
                    "elapsed_ms": controller.sched.elapsed_ms(),
                })
        except OSError as e:
            return {"ok": False, "message": f"Could not save: {e}"}

        last_summarised_session = controller.ctx.session_id

        return {
            "ok": True,
            "outcome": outcome,
            "message": "Progress saved.",
        }


# ============================================================
# MAIN WEBSITE
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def read_welcome():
    """
    Welcome page: the participant chooses condition A, B or C.
    """

    welcome_path = BASE_DIR / "static" / "welcome.html"

    return HTMLResponse(
        welcome_path.read_text(encoding="utf-8")
    )


@app.get("/training", response_class=HTMLResponse)
async def read_training():
    """
    The 3D training session itself.
    """

    index_path = BASE_DIR / "static" / "index.html"

    return HTMLResponse(
        index_path.read_text(encoding="utf-8")
    )
