/* Project 11 web frontend logic.
 *
 * The server (and behind it project11.controller) is authoritative for all
 * experiment state. This file only: renders state, forwards clicks, runs the
 * audio/voice presentation layer, and handles pause on hidden tabs.
 * It never decides what is a correct action.
 */
"use strict";

const $ = (id) => document.getElementById(id);
const pollMs = 250;

let session = null;        // {id, condition}
let actionSeq = 0;         // increments per action; server replays duplicates
let lastSeq = -1;          // last state seq rendered
let lastStepIndex = -1;
let hazardSeen = false;
let hazardWindowMs = 6000;
let pollTimer = null;
let audioCtx = null;

/* ---------------- audio (identical in ALL conditions) ---------------- */
function beep(kind) {
  try {
    audioCtx = audioCtx || new (window.AudioContext || window.webkitAudioContext)();
    const t = audioCtx.currentTime;
    const o = audioCtx.createOscillator();
    const g = audioCtx.createGain();
    o.connect(g); g.connect(audioCtx.destination);
    if (kind === "ok")       { o.type = "sine";   o.frequency.value = 880; g.gain.value = 0.05; o.start(t); o.stop(t + 0.12); }
    if (kind === "error")    { o.type = "square"; o.frequency.value = 220; g.gain.value = 0.04; o.start(t); o.stop(t + 0.18); }
    if (kind === "hazard")   { o.type = "sawtooth"; o.frequency.value = 440; g.gain.value = 0.06; o.start(t); o.stop(t + 0.35); }
  } catch (e) { /* audio is presentation only; never block the task */ }
}

/* ---------------- voice (Condition C ONLY) ---------------- */
function speak(text) {
  if (session.condition !== "C" || !("speechSynthesis" in window)) return;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 0.95; u.pitch = 1;
    window.speechSynthesis.speak(u);
  } catch (e) { /* voice is presentation only; text is always shown */ }
}

/* ---------------- API helpers ---------------- */
async function api(path, body) {
  const res = await fetch(`/api/session/${session.id}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

async function startSession() {
  const body = {
    participant_code: $("f-code").value.trim(),
    condition_order: $("f-order").value,
    procedure_id: $("f-proc").value,
    is_practice: $("f-practice").checked,
  };
  const res = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    $("setup-error").textContent = err.detail || "Could not start session.";
    $("setup-error").classList.remove("hidden");
    return;
  }
  const data = await res.json();
  session = { id: data.session_id, condition: data.state.condition };
  $("setup").classList.add("hidden");
  $("task").classList.remove("hidden");
  $("hud-condition").textContent = `condition ${data.state.condition}`;
  lastSeq = -1; lastStepIndex = -1; hazardSeen = false; actionSeq = 0;
  render(data.state);
  pollTimer = setInterval(poll, pollMs);
}

async function poll() {
  if (!session) return;
  try {
    const res = await fetch(`/api/session/${session.id}/state`);
    if (res.ok) render(await res.json());
  } catch (e) { /* transient; next poll retries. State GETs are safe. */ }
}

/* ---------------- rendering ---------------- */
function render(s) {
  // paused overlay
  $("paused-overlay").classList.toggle("hidden", !s.paused);
  $("btn-pause").disabled = s.paused || s.completed || s.aborted;

  if (s.seq === lastSeq && s.step_index === lastStepIndex && !s.hazard) {
    updateGauge(s); updateHazardTimer(s);
    return;
  }
  const hazardNew = !!s.hazard && !hazardSeen;
  lastSeq = s.seq;

  $("step-counter").textContent = `Step ${s.step_index + 1} / ${s.total_steps}`;
  $("hud-step").textContent = `Step ${s.step_index + 1} / ${s.total_steps}`;
  $("instruction").textContent = s.instruction;

  // Condition C: explanation box. A and B never see it.
  const showExp = s.condition === "C" && s.explanation;
  $("explanation-box").classList.toggle("hidden", !showExp);
  if (showExp) $("explanation").textContent = s.explanation;

  // Conditions B/C: highlight the target. A never does.
  drawOverlay(s.target_component);

  // hazard banner
  if (s.hazard) {
    if (hazardNew) { beep("hazard"); hazardWindowMs = s.hazard.remaining_ms; hazardSeen = true; }
    $("hazard-banner").classList.remove("hidden");
    $("hazard-text").textContent = s.hazard.message;
    $("hazard-ring").classList.remove("hidden");
  } else {
    $("hazard-banner").classList.add("hidden");
    $("hazard-ring").classList.add("hidden");
    if (!s.hazard && lastStepIndex >= 0 && s.step_index !== lastStepIndex) hazardSeen = false;
  }

  // completion
  if (s.completed || s.aborted) {
    clearInterval(pollTimer);
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    $("done-title").textContent = s.completed ? "Task complete" : "Session ended";
    $("done-text").textContent = s.completed
      ? "All steps finished. Thank you."
      : "The session was ended early. Data up to this point is saved.";
    $("done-overlay").classList.remove("hidden");
    return;
  }

  // new step: visual state + voice + chime
  if (s.step_index !== lastStepIndex) {
    applyPcState(s);
    $("feedback").classList.add("hidden");
    $("btn-hint").classList.add("hidden");
    if (lastStepIndex >= 0) beep("ok");
    speak(s.instruction);
    lastStepIndex = s.step_index;
  }
  updateGauge(s);
}

/* PC visual state derives from step progress; the server stays authoritative
   for progression, this only mirrors it on screen.  All three procedures
   share the same opening (PSU off -> thumbscrew -> panel -> ground) and
   closing (panel back on -> PSU on), so the map is step-id based. */
const PROC_MAP = {
  pc_ram: { psuOff: "s01", panelOff: "s03", panelOn: "s09", psuOn: "s10" },
  pc_gpu: { psuOff: "s01", panelOff: "s03", panelOn: "s10", psuOn: "s11" },
  pc_fan: { psuOff: "s01", panelOff: "s03", panelOn: "s11", psuOn: "s12" },
};

function applyPcState(s) {
  const ids = s.step_ids || [];
  const idx = (id) => ids.indexOf(id);
  const done = s.last_completed_step_id ? idx(s.last_completed_step_id) : -1;
  const cur = idx(s.step_id);
  const m = PROC_MAP[s.procedure] || PROC_MAP.pc_ram;

  // PSU rocker (and fan spin) follow the power steps.
  const psuOff = done >= idx(m.psuOff) && done < idx(m.psuOn);
  $("psu_switch").classList.toggle("is-off", psuOff);
  $("psu-rocker-label").textContent = psuOff ? "I" : "O";
  $("pc").classList.toggle("psu-off", psuOff);

  // Side panel: closed -> removed -> held (refit step) -> closed again.
  const openPhase = done >= idx(m.panelOff) && cur < idx(m.panelOn);
  const held = cur === idx(m.panelOn);
  const panel = $("case-panel");
  panel.classList.toggle("is-removed", openPhase);
  panel.classList.toggle("is-held", held);
  // With the case shut only the rear-access PSU switch and the panel itself
  // are reachable (this closes the keyboard path; the mouse path is blocked
  // by the panel piece itself).  Panel off or held: everything is reachable.
  document.querySelectorAll("#pc .comp").forEach((el) => {
    const active = openPhase || held
      || el.id === "psu_switch" || panel.contains(el);
    el.toggleAttribute("inert", !active);
  });
  $("side_screw").classList.toggle("is-removed",
      done >= idx(m.panelOff) && cur < idx(m.panelOn));

  if (s.procedure === "pc_ram") {
    $("dimm_clip_top").classList.toggle("is-open", done >= idx("s05"));
    $("dimm_clip_bottom").classList.toggle("is-open", done >= idx("s06"));
    $("dimm_slot_2").classList.toggle("is-removed",
        done >= idx("s07") && cur < idx("s08"));
  } else if (s.procedure === "pc_gpu") {
    $("pcie_power").classList.toggle("is-disconnected",
        done >= idx("s05") && cur < idx("s09"));
    $("pcie_tab").classList.toggle("is-open", done >= idx("s06"));
    $("gpu_card").classList.toggle("is-removed",
        done >= idx("s07") && cur < idx("s08"));
  } else if (s.procedure === "pc_fan") {
    $("fan_header").classList.toggle("is-disconnected",
        done >= idx("s05") && cur < idx("s10"));
    $("fan_screws").classList.toggle("is-removed",
        done >= idx("s06") && cur < idx("s09"));
    $("case_fan").classList.toggle("is-removed",
        done >= idx("s07") && cur < idx("s08"));
  }
}

function drawOverlay(targetId) {
  const overlay = $("overlay");
  if (!targetId) { overlay.classList.add("hidden"); return; }
  const el = document.querySelector(`[data-component="${targetId}"]`);
  if (!el) { overlay.classList.add("hidden"); return; }
  const b = el.getBBox();
  overlay.setAttribute("x", b.x - 6);
  overlay.setAttribute("y", b.y - 6);
  overlay.setAttribute("width", b.width + 12);
  overlay.setAttribute("height", b.height + 12);
  overlay.classList.remove("hidden");
  overlay.classList.add("pulse");
}

function updateGauge(s) {
  const needle = $("gauge-needle");
  needle.style.left = `calc(${(s.secondary.value * 100).toFixed(1)}% - 2px)`;
  needle.classList.toggle("out", !s.secondary.in_band);
  $("secondary-stats").textContent =
    `fixes ${s.secondary.corrections}/${s.secondary.opportunities}`;
}

function updateHazardTimer(s) {
  if (!s.hazard) return;
  $("hazard-timer-fill").style.width =
    `${Math.max(0, (s.hazard.remaining_ms / hazardWindowMs) * 100)}%`;
}

/* ---------------- input ----------------
 * Delegated on the SVG so nested components work (the thumbscrew sits inside
 * the side panel; the fan screws are four circles in one group): the
 * innermost .comp wins. */
const pcSvg = $("pc");
pcSvg.addEventListener("click", (e) => {
  const el = e.target.closest(".comp");
  if (el) submitAction(el.dataset.component, el);
});
document.querySelectorAll("#pc .comp").forEach((el) => {
  el.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      submitAction(el.dataset.component, el);
    }
  });
});

async function submitAction(componentId, el) {
  if (!session) return;
  const svg = $("pc");
  const pt = svg.createSVGPoint();
  let x = 0.5, y = 0.5;
  if (el) {
    const b = el.getBBox();
    x = (b.x + b.width / 2) / 800;
    y = (b.y + b.height / 2) / 600;
  }
  try {
    const data = await api("/action", {
      component_id: componentId,
      action_seq: ++actionSeq,
      x_source: Math.round(x * 1000) / 1000,
      y_source: Math.round(y * 1000) / 1000,
    });
    showFeedback(data.outcome, data.state);
    render(data.state);
  } catch (e) {
    // Never blind-retry a state-changing POST: show it and resync from state.
    showFeedback("error", null);
    $("feedback").textContent = "Connection problem — state reloaded, action not repeated.";
    poll();
  }
}

/* Step-based recovery: a wrong click never undoes anything and never leaves
   the participant stuck.  The message points back at the current step, and
   after two wrong clicks on the same step a "Show me" hint appears (logged
   server-side as HINT_SHOWN). */
function showFeedback(outcome, s) {
  const fb = $("feedback");
  fb.classList.remove("hidden", "error", "ok", "recover");
  $("btn-hint").classList.add("hidden");
  if (outcome === "accepted") {
    fb.classList.add("ok"); fb.textContent = "Correct.";
  } else if (outcome === "rejected") {
    fb.classList.add("error");
    fb.textContent = "Not this part. The step asks: " + (s ? s.instruction : "check the instruction.");
    beep("error");
    if (s && s.hint_ready) $("btn-hint").classList.remove("hidden");
  } else {
    fb.textContent = ""; fb.classList.add("hidden");
  }
}

let hintFlashTimer = null;

$("btn-hint").addEventListener("click", async () => {
  if (!session) return;
  try {
    const d = await api("/hint");
    const h = d.hint;
    $("btn-hint").classList.add("hidden");
    const fb = $("feedback");
    fb.classList.remove("hidden", "error", "ok");
    fb.classList.add("recover");
    fb.textContent = "Remember: " + h.instruction;
    if (session.condition === "C") speak(h.instruction);
    if (h.target_component) {
      drawOverlay(h.target_component);
      clearTimeout(hintFlashTimer);
      hintFlashTimer = setTimeout(() => poll(), 2500);  // resync overlay
    }
  } catch (e) { /* hint is optional help; never block the task */ }
});

/* ---------------- buttons & global keys ---------------- */
$("btn-start").addEventListener("click", startSession);
$("btn-pause").addEventListener("click", () => api("/pause").then((d) => render(d.state)));
$("btn-resume").addEventListener("click", () => api("/resume").then((d) => render(d.state)));
$("btn-abort").addEventListener("click", async () => {
  if (!session || confirm("End this session? Data up to now is saved.")) {
    if (session) await api("/abort").catch(() => {});
    location.reload();
  }
});
$("btn-review").addEventListener("click", async () => {
  if (!session) return;
  const d = await api("/review");
  if (d.reviewed_instruction) {
    $("reviewed-box").classList.remove("hidden");
    $("reviewed-text").textContent = d.reviewed_instruction;
  }
});

document.addEventListener("keydown", (e) => {
  if (e.code === "Space" && session && !$("task").classList.contains("hidden")) {
    e.preventDefault();
    api("/secondary").then((d) => render(d.state)).catch(() => {});
  }
  if (e.key === "Escape" && session) {
    api("/pause").then((d) => render(d.state)).catch(() => {});
  }
});

/* A hidden tab makes timing data meaningless: auto-pause, visible banner. */
document.addEventListener("visibilitychange", () => {
  if (document.hidden && session) {
    api("/pause").then((d) => render(d.state)).catch(() => {});
  }
});
