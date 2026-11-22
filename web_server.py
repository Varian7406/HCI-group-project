# imports existing logic, recreates timer, uses FastAPI for web access
# takes the place of app and main_window


# web_server.py


import threading
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from project11.controller import SessionContext, SessionController
from project11.event_logger import EventLogger
from project11.models import Condition
from project11.procedure_loader import load_procedure
from project11.scheduler import now_ms


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")


controller = None
CURRENT_CONDITION = Condition.B_OVERLAY

start_time = 0


def background_tick():
    """Update the secondary task and trigger scripted hazards."""
    global controller

    while controller and not controller.completed and not controller.aborted:
        time.sleep(0.05)

        t = now_ms()

        # Update the secondary task.
        controller.secondary.tick(t)

        # Present a hazard once its configured step has been completed.
        if controller.hazard.armed:
            controller.hazard.present(t)

        # Check whether the hazard response time has expired.
        controller.hazard.miss_if_expired(t)


@app.on_event("startup")
async def startup():
    global controller, start_time

    proc_path = Path("assets/procedures/example_procedure.json")
    procedure = load_procedure(proc_path)

    ctx = SessionContext(
        participant_code="WEB_USER",
        session_id="WEB_001",
        condition=CURRENT_CONDITION,
        condition_order=1,
        is_practice=True,
        task_id="WEB_TASK",
    )

    logger = EventLogger(
        Path("data/raw-local/web_attempt.csv"),
        "web_001",
    )

    class MockSched:
        def elapsed_ms(self):
            return now_ms() - start_time

        def cancel_all(self):
            pass

        def pause(self):
            pass

        def resume(self):
            pass

    start_time = now_ms()

    controller = SessionController(
        procedure,
        ctx,
        logger,
        MockSched(),
    )

    controller.start(now_ms())

    threading.Thread(
        target=background_tick,
        daemon=True,
    ).start()


@app.get("/state")
async def get_state():
    if not controller:
        return {"status": "idle"}

    if controller.completed:
        status = "completed"
    elif controller.aborted:
        status = "aborted"
    else:
        status = "running"

    step = controller.current_step()
    component = controller.proc.component_by_id(step.component_id)

    secondary = controller.secondary.snapshot()
    hazard = controller.hazard.state

    return {
        "status": status,

        "step_index": controller.step_index,
        "total_steps": len(controller.proc.steps),

        "instruction": step.instruction,
        "expected_action": step.expected_action,
        "explanation": step.explanation or "",

        "components": [
            {
                "id": c.id,
                "label": c.label,
                "bounds": list(c.bounds),
            }
            for c in controller.proc.components
        ],

        "highlight": {
            "component_id": step.component_id,
            "label": component.label if component else "",
            "bounds": list(component.bounds) if component else None,
        },

        "condition": CURRENT_CONDITION.value,

        "secondary": secondary,

        "hazard": {
            "active": hazard.active and not hazard.responded,
            "responded": hazard.responded,
            "correct": hazard.correct,
            "message": controller.proc.hazard.message,
            "correct_component_id":
                controller.proc.hazard.correct_component_id,
        },

        "elapsed_ms": controller.sched.elapsed_ms(),
    }


@app.post("/click")
async def handle_click(request: Request):
    data = await request.json()

    if controller and not controller.completed and not controller.aborted:
        controller.handle_click(
            data["component_id"],
            now_ms(),
            data.get("xn", 0.5),
            data.get("yn", 0.5),
        )

    return {"ok": True}


@app.post("/secondary")
async def handle_secondary():
    if controller and not controller.completed and not controller.aborted:
        controller.secondary.correct(now_ms())

    return {"ok": True}


@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as file:
        return file.read()

