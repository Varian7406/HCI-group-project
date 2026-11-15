# imports existing logic, recreates timer, uses FastAPI for web access
# takes the place of app and main_window


# web_server.py
import threading
import time
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

# Import your existing logic
from project11.controller import SessionContext, SessionController
from project11.event_logger import EventLogger
from project11.models import Condition
from project11.procedure_loader import load_procedure
from project11.scheduler import now_ms

app = FastAPI()
# Serve static HTML/CSS/JS files from a 'static' folder
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")

# Global state
controller = None
CURRENT_CONDITION = Condition.B_OVERLAY  # Change as needed

def background_tick():
    """Replaces root.after(50, self._tick)"""
    global controller
    while controller and not controller.completed and not controller.aborted:
        time.sleep(0.05)  # 50ms
        t = now_ms()
        controller.secondary.tick(t)
        controller.hazard.miss_if_expired(t)

@app.on_event("startup")
async def startup():
    global controller
    proc_path = Path("assets/procedures/example_procedure.json")
    procedure = load_procedure(proc_path)
    
    ctx = SessionContext(
        participant_code="WEB_USER", session_id="WEB_001", 
        condition=CURRENT_CONDITION, condition_order=1, 
        is_practice=True, task_id="WEB_TASK"
    )
    logger = EventLogger(Path("data/raw-local/web_attempt.csv"), "web_001")
    
    # Mock scheduler to satisfy SessionController signature, 
    # since we are handling the tick loop manually in background_tick
    class MockSched:
        def elapsed_ms(self): return now_ms() - start_time
        def cancel_all(self): pass
        
    global start_time
    start_time = now_ms()
    
    controller = SessionController(procedure, ctx, logger, MockSched())
    controller.start(now_ms())
    
    # Start the 50ms visual/logic tick in a background thread
    threading.Thread(target=background_tick, daemon=True).start()

@app.get("/state")
async def get_state():
    if not controller:
        return {"status": "idle"}

    step = controller.current_step()
    comp = controller.proc.component_by_id(step.component_id)
    s = controller.secondary.snapshot()

    return {
        "status": "completed" if controller.completed else "running",
        "step_index": controller.step_index,
        "total_steps": len(controller.proc.steps),
        "instruction": step.instruction,
        "explanation": step.explanation or "",
        "image_path": "/assets/" + controller.proc.image_rel_path,
        "components": [
            {"id": c.id, "label": c.label, "bounds": list(c.bounds)}
            for c in controller.proc.components
        ],
        "highlight": {
            "component_id": step.component_id,
            "label": comp.label if comp else "",
            "bounds": list(comp.bounds) if comp else None
        },
        "condition": CURRENT_CONDITION.value,
        "secondary": s,
        "elapsed_ms": controller.sched.elapsed_ms()
    }

@app.post("/click")
async def handle_click(request: Request):
    data = await request.json()
    if controller and not controller.completed and not controller.aborted:
        controller.handle_click(data["component_id"], now_ms(), data["xn"], data["yn"])
    return {"ok": True}

@app.post("/secondary")
async def handle_secondary():
    if controller and not controller.completed and not controller.aborted:
        controller.secondary.correct(now_ms())
    return {"ok": True}

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()