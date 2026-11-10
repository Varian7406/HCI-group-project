# Requirements register

Values are *proposed engineering checks*, not lecturer-set targets. Add
Owner / Status in your live register. "Evidence" says what exists **in this
draft**; "Gap" says what a human still has to do.

| ID | Requirement / acceptance check | Evidence in this draft | Gap |
|---|---|---|---|
| R01 | Valid procedure loads; missing/invalid fields give a clear error | `tests/test_loader.py` | content review against the real source |
| R02 | All image regions map correctly after resizing/letterboxing | `tests/test_geometry.py` | lab check on the real display sizes |
| R03 | Every predefined action updates state as specified, in all conditions | `tests/test_controller.py` | run every shipped step once by hand |
| R04 | Pause freezes task and secondary timers; resume restores state | `tests/test_timing.py` | observe a real pause in the pilot |
| R05 | Reviewing a previous instruction never reverses state | `test_review_does_not_reverse_state` | - |
| R06 | Hazard trigger, response, latency logged exactly once | controller logic (`hazard.py` + `controller.py`) | **hazard unit tests not yet written** |
| R07 | Secondary-task events include opportunities, responses and misses | `secondary_task.py`; example logs | gauge unit tests not yet written; pilot the difficulty |
| R08 | Logs contain every required field; incomplete sessions preserved | `tests/test_logs.py`, `analysis/validate_logs.py` | - |
| R09 | Invalid destination / log failure is visible and stops progression | `test_bad_destination_raises` | try a really full USB stick |
| R10 | No names, consent records or identifiable recordings in repo/logs | `.gitignore`; participant codes only | **human privacy review of real exports** |
| R11 | Clean Ubuntu checkout installs, runs, reproduces analysis | tools generate + analyse example data | **dated run on the lab machines** |
| R12 | Guidance readable and controllable; no colour-only warning | overlays carry text labels; pause/review/exit exist | UI checklist on the lab display |

## Study acceptance criteria
Choose them before the main study, from pilot findings. Nothing in this
draft sets them.
