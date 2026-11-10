# Architecture in one page

## The rule that makes the study valid
**One task engine for all three conditions.** `project11/controller.py`
(`SessionController`) knows nothing about Tk and nothing about A/B/C. The
conditions only change what the *screen* draws (`ui/guidance_panel.py`, the
overlay in `ui/machine_canvas.py`). Every click is handled by the same code
path in every condition, so differences in the logs come from the guidance,
not from the engine.

## One action, end to end
```
mouse click in the window
  -> MachineCanvas._on_click_event   display pixel -> normalised source coords
                                     (geometry.py); clicks in the letterbox
                                     bars are dropped and never logged
  -> MainWindow._on_machine_click    forwards (component_id, x, y)
  -> SessionController.handle_click  1 completed/aborted?  -> IGNORED
                                     2 double-click tail?  -> DOUBLE_CLICK_IGNORED
                                       (same component within 350 ms of an
                                       accepted action; logged, not an error)
                                     3 hazard active?      -> HAZARD_RESPONSE
                                     4 wrong component?    -> ACTION_REJECTED
                                       (state untouched)
                                     5 right component     -> ACTION_ACCEPTED,
                                       next step presented
  -> EventLogger.log                 one CSV row per event, monotonic numbering
```
Every attempt ends in exactly one ACCEPTED / REJECTED / IGNORED row.

## Modules
| module | job | knows about Tk? |
|---|---|---|
| `project11/models.py` | data classes: Condition, Procedure, Step, Event | no |
| `project11/procedure_loader.py` | load + validate procedure JSON, clear errors | no |
| `project11/geometry.py` | letterbox maths, click mapping | no |
| `project11/scheduler.py` | pause-aware timers and elapsed time | no |
| `project11/hazard.py` | scripted hazard state machine | no |
| `project11/secondary_task.py` | drifting gauge | no |
| `project11/event_logger.py` | the ONLY writer of experiment events | no |
| `project11/controller.py` | task/session rules, one engine for A/B/C | no |
| `project11/ui/*` | Tkinter screens; redraw from controller state | yes |
| `analysis/*` | validate + summarise CSV logs | no |
| `tools/*` | panel generator, simulated participant, example data | no |

Everything left of `ui/` is the backend. If the interface is rebuilt in
JS/CSS/HTML, only the `ui/` package is replaced; the engine, the logger and
the analysis pipeline stay as they are, behind a small API server.

## Tools
`tools/make_training_panel.py` draws the fictional panel AND writes the
procedure JSONs from one Python spec, so the clickable regions can never
drift away from the picture. The three variants share the same 8-step shape
and nearly the same cursor travel (see the `travel()` function).
`tools/simulated_participant.py` plays the real controller with a fake clock,
so example data is produced in milliseconds and the analysis pipeline can be
tested without a human.
