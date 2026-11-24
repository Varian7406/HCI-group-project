

import threading
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from project11.controller import SessionContext, SessionController
from project11.event_logger import EventLogger
from project11.models import Condition
from project11.procedure_loader import load_procedure
from project11.scheduler import now_ms


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

VALID_CONDITIONS = {
    "A": Condition.A_MANUAL,
    "B": Condition.B_OVERLAY,
    "C": Condition.C_EXPLANATORY,
}

PROCEDURE_PATH = (
    BASE_DIR / "assets" / "procedures" / "example_procedure.json"
)

LOG_DIR = BASE_DIR / "data" / "raw-local"
LOG_DIR.mkdir(parents=True, exist_ok=True)

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

        # Give this session a unique identifier.
        session_id = uuid.uuid4().hex[:12]

        ctx = SessionContext(
            participant_code="WEB_USER",
            session_id=session_id,
            condition=current_condition,
            condition_order=1,
            is_practice=True,
            task_id="WEB_TASK",
        )

        # EventLogger opens the CSV in write mode.
        # Therefore, each fresh session starts with a clean log.
               # Create a separate log file for this training attempt.
        new_logger = EventLogger(
            LOG_DIR / f"web_attempt_{session_id}.csv",
            session_id,
        )

        # Give the new session its own timer.
        session_start_time = now_ms()

        class MockSched:

            def elapsed_ms(self):
                return now_ms() - session_start_time

            def cancel_all(self):
                pass

            def pause(self):
                pass

            def resume(self):
                pass

        # Create a completely new controller.
        new_controller = SessionController(
            procedure,
            ctx,
            new_logger,
            MockSched(),
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
    Called by the welcome page when the participant picks a
    condition. Sets the active condition and starts a fresh
    session under it.
    """

    global current_condition

    data = await request.json()

    chosen = str(data.get("condition", "")).upper()

    if chosen not in VALID_CONDITIONS:
        return {"ok": False, "message": "Unknown condition."}

    current_condition = VALID_CONDITIONS[chosen]

    session_id = reset_session()

    return {
        "ok": True,
        "condition": current_condition.value,
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

    with session_lock:

        if (
            controller is not None
            and not controller.completed
            and not controller.aborted
        ):

            controller.handle_click(
                data["component_id"],
                now_ms(),
                data.get("xn", 0.5),
                data.get("yn", 0.5),
            )

    return {"ok": True}


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
        ):

            vented = controller.secondary.correct(now_ms())

    # "vented" tells the frontend whether the press was accepted
    # or blocked by the cooldown, so its countdown stays in sync.
    return {"ok": True, "vented": vented}


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
