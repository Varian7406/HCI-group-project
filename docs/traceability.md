# Traceability

Pattern: **requirement -> code -> test -> observation -> report limitation**,
plus the human-factors reason.

| Req | Code | Test | Human-factors rationale | Observation / limitation (fill in) |
|---|---|---|---|---|
| R01 | `procedure_loader.load_procedure` | `test_loader.py` | error prevention for content authors | |
| R02 | `geometry.Layout`, `display_to_norm` | `test_geometry.py` | feedback: the click lands where the eye sees the part | |
| R03 | `controller.SessionController.handle_click` | `test_controller.py` | consistency across conditions | |
| R04 | `controller.pause` -> `scheduler.Scheduler.pause` | `test_timing.py` | user control; fair attention measurement | |
| R05 | `controller.review_previous` | `test_review_does_not_reverse_state` | user control without risk of accidental undo | |
| R06 | `hazard.HazardManager` | (unit tests to add) | attention: spontaneous detection, not forced acknowledgement | |
| R07 | `secondary_task.SecondaryTask` | (unit tests to add) | attention: divided-attention load | |
| R08 | `event_logger.EventLogger`, `analysis/validate_logs.py` | `test_logs.py` | trustworthy evidence | |
| R09 | `EventLogger._open` raises `RuntimeError` | `test_bad_destination_raises` | never run an unrecorded study | |
| R10 | `.gitignore`, participant codes only | - | privacy | privacy review pending |
| R11 | `tools/generate_example_data.py` + analysis | - | reproducibility | lab run pending |
| R12 | `ui/guidance_panel.py`, `ui/machine_canvas.py` | - | perception: text + shape + colour | lab checklist pending |

Data-quality note: the double-click guard in `controller.py`
(`DOUBLE_CLICK_GUARD_MS`) keeps the tail of a double-click out of the error
counts; see `test_double_click_tail_is_ignored_not_an_error`.
