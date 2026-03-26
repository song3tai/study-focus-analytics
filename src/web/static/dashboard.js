const state = {
  status: null,
  latest: null,
  summary: null,
  wsState: "connecting",
  lastProcessResultAt: null,
  pendingProcessResult: null,
  processResultFlushTimer: null,
  videoErrored: false,
  videoBlockedByServiceError: false,
  videoLoading: false,
};

const SESSION_RESULT_STORAGE_KEY = "study_focus_session_result";
const SESSION_RESULT_PAGE_URL = "/static/session_result.html";

const els = {
  serviceRunning: document.getElementById("service-running"),
  wsStatus: document.getElementById("ws-status"),
  sessionState: document.getElementById("session-state"),
  sourceType: document.getElementById("source-type"),
  statusMeta: document.getElementById("status-meta"),
  globalError: document.getElementById("global-error"),
  videoPreview: document.getElementById("video-preview"),
  videoOverlay: document.getElementById("video-overlay"),
  currentState: document.getElementById("current-state"),
  focusScore: document.getElementById("focus-score"),
  focusBar: document.getElementById("focus-bar"),
  focusLevel: document.getElementById("focus-level"),
  stateDuration: document.getElementById("state-duration"),
  awayCount: document.getElementById("away-count"),
  totalDuration: document.getElementById("total-duration"),
  totalPresent: document.getElementById("total-present"),
  totalAway: document.getElementById("total-away"),
  averageFocus: document.getElementById("average-focus"),
  reasonsList: document.getElementById("reasons-list"),
  personDetected: document.getElementById("person-detected"),
  personInRoi: document.getElementById("person-in-roi"),
  roiOverlap: document.getElementById("roi-overlap"),
  stabilityScore: document.getElementById("stability-score"),
  motionDelta: document.getElementById("motion-delta"),
  sessionDuration: document.getElementById("session-duration"),
  currentAwayDuration: document.getElementById("current-away-duration"),
  studyingTotal: document.getElementById("studying-total"),
  maxFocus: document.getElementById("max-focus"),
  minFocus: document.getElementById("min-focus"),
  frameId: document.getElementById("frame-id"),
  frameTimestamp: document.getElementById("frame-timestamp"),
  sourceName: document.getElementById("source-name"),
  fpsHint: document.getElementById("fps-hint"),
  inferenceMs: document.getElementById("inference-ms"),
  statusLastFrameId: document.getElementById("status-last-frame-id"),
  statusLastTimestamp: document.getElementById("status-last-timestamp"),
  statusLastError: document.getElementById("status-last-error"),
  processErrorMessage: document.getElementById("process-error-message"),
  lastUpdated: document.getElementById("last-updated"),
  sourceTypeInput: document.getElementById("source-type-input"),
  sourceInput: document.getElementById("source-input"),
  startButton: document.getElementById("start-button"),
  fastButton: document.getElementById("fast-button"),
  stopButton: document.getElementById("stop-button"),
  refreshButton: document.getElementById("refresh-button"),
};

const sourceInputDefaults = {
  camera: "",
  video_file: "input/sample.mp4",
  rtsp: "rtsp://",
};

function formatSeconds(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  const total = Math.max(0, Math.round(Number(value)));
  const hours = String(Math.floor(total / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
  const seconds = String(total % 60).padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  return Number(value).toFixed(digits);
}

function normalizeFocusScore(rawValue) {
  if (rawValue === null || rawValue === undefined || Number.isNaN(Number(rawValue))) {
    return null;
  }
  const numeric = Number(rawValue);
  if (numeric <= 1) {
    return Math.max(0, Math.min(100, numeric * 100));
  }
  return Math.max(0, Math.min(100, numeric));
}

function boolText(value) {
  if (value === null || value === undefined) {
    return "--";
  }
  return value ? "true" : "false";
}

function setPill(el, text, tone) {
  el.textContent = text;
  el.className = `status-pill ${tone}`;
}

function setStateChip(el, text, tone) {
  el.textContent = text;
  el.className = `state-chip ${tone}`;
}

function stateTone(stateValue) {
  if (stateValue === "running" || stateValue === "studying" || stateValue === "present") {
    return "success";
  }
  if (stateValue === "starting" || stateValue === "stopping" || stateValue === "medium") {
    return "warning";
  }
  if (stateValue === "error" || stateValue === "away" || stateValue === "low" || stateValue === "disconnected") {
    return "danger";
  }
  if (stateValue === "connected" || stateValue === "video_file" || stateValue === "camera" || stateValue === "rtsp" || stateValue === "high") {
    return "accent";
  }
  return "neutral";
}

function renderStatus() {
  const status = state.status || {};
  setPill(els.serviceRunning, status.running ? "running" : "idle", status.running ? "success" : "neutral");
  setPill(els.wsStatus, state.wsState, stateTone(state.wsState));
  setPill(els.sessionState, status.session_state || "idle", stateTone(status.session_state));
  setPill(els.sourceType, status.source_type || "none", stateTone(status.source_type));
  els.statusMeta.textContent = `source=${status.source || "--"} | latest=${status.has_latest_result ? "yes" : "no"} | started_at=${status.started_at || "--"}`;
  els.statusLastFrameId.textContent = status.last_frame_id ?? "--";
  els.statusLastTimestamp.textContent = status.last_timestamp ?? "--";
  els.statusLastError.textContent = status.last_error || "--";

  const sessionState = status.session_state || "idle";
  els.startButton.disabled = sessionState === "running" || sessionState === "starting" || sessionState === "stopping";
  els.fastButton.disabled =
    sessionState === "running" ||
    sessionState === "starting" ||
    sessionState === "stopping" ||
    els.sourceTypeInput.value !== "video_file";
  els.stopButton.disabled = sessionState === "idle" || sessionState === "stopping" || sessionState === "error";
}

function syncSourceInputState() {
  const sourceType = els.sourceTypeInput.value;
  const isCamera = sourceType === "camera";
  els.sourceInput.disabled = isCamera;

  if (isCamera) {
    els.sourceInput.value = "";
    els.sourceInput.placeholder = "camera source is not required";
    renderStatus();
    return;
  }

  if (!els.sourceInput.value.trim()) {
    els.sourceInput.value = sourceInputDefaults[sourceType] || "";
  }
  els.sourceInput.placeholder =
    sourceType === "video_file"
      ? "input/sample.mp4"
      : "rtsp://your-stream-address";
  renderStatus();
}

function persistSessionResult(result) {
  try {
    window.sessionStorage.setItem(SESSION_RESULT_STORAGE_KEY, JSON.stringify(result));
    return true;
  } catch (_error) {
    return false;
  }
}

function openSessionResultPage(result) {
  if (!result) {
    return false;
  }
  if (!persistSessionResult(result)) {
    setGlobalError("Unable to open the result page because session storage is unavailable.");
    return false;
  }
  window.location.href = SESSION_RESULT_PAGE_URL;
  return true;
}

function renderSummary() {
  const summary = state.summary || state.latest?.summary || {};
  els.totalDuration.textContent = formatSeconds(summary.total_duration_sec);
  els.totalPresent.textContent = formatSeconds(summary.total_present_duration_sec);
  els.totalAway.textContent = formatSeconds(summary.total_away_duration_sec);
  els.averageFocus.textContent = formatNumber(summary.average_focus_score, 2);
  els.studyingTotal.textContent = formatSeconds(summary.total_studying_duration_sec);
  els.maxFocus.textContent = formatNumber(summary.max_focus_score, 2);
  els.minFocus.textContent = formatNumber(summary.min_focus_score, 2);
}

function renderLatest() {
  const result = state.latest || {};
  const framePacket = result.frame_packet || {};
  const features = result.frame_features || {};
  const snapshot = result.state_snapshot || {};
  const focus = result.focus_estimate || {};

  setStateChip(els.currentState, snapshot.current_state || "unknown", stateTone(snapshot.current_state));
  const focusPercent = normalizeFocusScore(focus.focus_score);
  els.focusScore.textContent = focusPercent === null ? "--" : formatNumber(focusPercent, 2);
  els.focusBar.style.width = `${focusPercent ?? 0}%`;
  setPill(els.focusLevel, focus.focus_level || "unknown", stateTone(focus.focus_level));
  els.stateDuration.textContent = formatSeconds(snapshot.state_duration_sec);
  els.awayCount.textContent = snapshot.away_count ?? 0;

  els.personDetected.textContent = boolText(features.person_detected);
  els.personInRoi.textContent = boolText(features.person_in_roi);
  els.roiOverlap.textContent = formatNumber(features.roi_overlap_ratio, 3);
  els.stabilityScore.textContent = formatNumber(features.stability_score, 3);
  els.motionDelta.textContent = formatNumber(features.motion_delta, 3);
  els.sessionDuration.textContent = formatSeconds(snapshot.current_session_duration_sec);
  els.currentAwayDuration.textContent = formatSeconds(snapshot.current_away_duration_sec);

  els.frameId.textContent = framePacket.frame_id ?? "--";
  els.frameTimestamp.textContent = framePacket.timestamp ?? "--";
  els.sourceName.textContent = framePacket.source_name || "--";
  els.fpsHint.textContent = framePacket.fps_hint ?? "--";
  els.inferenceMs.textContent = result.detection_result?.inference_ms ?? "--";
  els.processErrorMessage.textContent = result.error_message || "--";

  const reasons = Array.isArray(focus.reasons) ? focus.reasons : [];
  els.reasonsList.innerHTML = reasons.length
    ? reasons.map((reason) => `<span class="tag">${reason}</span>`).join("")
    : '<span class="muted">No reasons available</span>';

  els.lastUpdated.textContent = state.lastProcessResultAt
    ? `Last process_result at ${new Date(state.lastProcessResultAt).toLocaleTimeString()}`
    : "No process result yet";
}

function setGlobalError(message) {
  if (!message) {
    els.globalError.classList.add("hidden");
    els.globalError.textContent = "";
    return;
  }
  els.globalError.classList.remove("hidden");
  els.globalError.textContent = message;
}

function showVideoOverlay(message) {
  els.videoOverlay.textContent = message;
  els.videoOverlay.classList.remove("hidden");
}

function hideVideoOverlay() {
  els.videoOverlay.classList.add("hidden");
}

function clearVideoPreview() {
  state.videoLoading = false;
  state.videoErrored = false;
  state.videoBlockedByServiceError = false;
  els.videoPreview.removeAttribute("src");
  hideVideoOverlay();
}

function refreshVideoPreview(showLoading = false) {
  state.videoErrored = false;
  state.videoBlockedByServiceError = false;
  state.videoLoading = showLoading;
  if (showLoading) {
    showVideoOverlay("Loading preview...");
  } else {
    hideVideoOverlay();
  }
  const cacheBust = `t=${Date.now()}`;
  els.videoPreview.src = `/analysis/video?${cacheBust}`;
}

function clearVideoOverlayIfRecoverable() {
  if (state.videoErrored || state.videoBlockedByServiceError || state.videoLoading) {
    return;
  }
  hideVideoOverlay();
}

function syncVideoPreviewWithSession(showLoading = false) {
  const sessionState = state.status?.session_state;
  const shouldShowPreview = sessionState === "starting" || sessionState === "running";
  if (!shouldShowPreview) {
    clearVideoPreview();
    return;
  }

  if (!els.videoPreview.getAttribute("src") || showLoading) {
    refreshVideoPreview(showLoading);
  }
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || `request failed: ${response.status}`);
  }
  return data;
}

async function initializeData() {
  const [status, latest, summary] = await Promise.all([
    fetchJson("/analysis/status"),
    fetchJson("/analysis/latest"),
    fetchJson("/analysis/summary"),
  ]);

  state.status = status;
  state.summary = summary?.data || null;
  state.latest = latest?.data || null;
  renderStatus();
  renderSummary();
  renderLatest();
}

function queueProcessResult(data) {
  state.pendingProcessResult = data;
  if (state.processResultFlushTimer) {
    return;
  }
  state.processResultFlushTimer = window.setTimeout(() => {
    state.latest = state.pendingProcessResult;
    state.summary = state.pendingProcessResult?.summary || state.summary;
    state.lastProcessResultAt = Date.now();
    state.pendingProcessResult = null;
    state.processResultFlushTimer = null;
    renderLatest();
    renderSummary();
  }, 200);
}

function connectWebSocket() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocol}://${window.location.host}/ws/analysis`);

  ws.addEventListener("open", () => {
    state.wsState = "connected";
    renderStatus();
  });

  ws.addEventListener("close", () => {
    state.wsState = "disconnected";
    renderStatus();
    window.setTimeout(connectWebSocket, 1500);
  });

  ws.addEventListener("error", () => {
    state.wsState = "error";
    renderStatus();
  });

  ws.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type === "service_status") {
      state.status = payload.data;
      renderStatus();
      if (!state.latest && !state.summary && payload.data?.last_error) {
        setGlobalError(payload.data.last_error);
      }
      const recovered =
        !payload.data?.last_error &&
        payload.data?.session_state &&
        payload.data.session_state !== "error";
      if (recovered) {
        setGlobalError(null);
        state.videoBlockedByServiceError = false;
        state.videoLoading = false;
        clearVideoOverlayIfRecoverable();
      }
      syncVideoPreviewWithSession(false);
      return;
    }

    if (payload.type === "process_result") {
      setGlobalError(null);
      state.videoBlockedByServiceError = false;
      state.videoLoading = false;
      clearVideoOverlayIfRecoverable();
      syncVideoPreviewWithSession(false);
      queueProcessResult(payload.data);
      return;
    }

    if (payload.type === "service_error") {
      state.status = {
        ...(state.status || {}),
        session_state: "error",
        last_error: payload.data?.message || "service error",
      };
      renderStatus();
      setGlobalError(payload.data?.message || "service error");
      state.videoBlockedByServiceError = true;
      state.videoLoading = false;
      showVideoOverlay("Video unavailable / session error");
    }
  });
}

async function startAnalysis() {
  const sourceType = els.sourceTypeInput.value;
  const sourceValue = els.sourceInput.value.trim();
  const body = {
    source_type: sourceType,
    debug: false,
  };
  if (sourceValue) {
    body.source = sourceValue;
  }

  try {
    setGlobalError(null);
    await fetchJson("/analysis/start", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    await initializeData();
    syncVideoPreviewWithSession(true);
  } catch (error) {
    setGlobalError(error.message);
  }
}

async function runFastAnalysis() {
  const sourceType = els.sourceTypeInput.value;
  const sourceValue = els.sourceInput.value.trim();

  if (sourceType !== "video_file") {
    setGlobalError("Fast analysis is only available for video files.");
    return;
  }

  if (!sourceValue) {
    setGlobalError("Please provide a video file path for fast analysis.");
    return;
  }

  try {
    setGlobalError(null);
    const response = await fetchJson("/analysis/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_type: "video_file",
        source: sourceValue,
        mode: "fast",
      }),
    });
    openSessionResultPage(response.data);
  } catch (error) {
    setGlobalError(error.message);
  }
}

async function stopAnalysis() {
  try {
    setGlobalError(null);
    const response = await fetchJson("/analysis/stop", { method: "POST" });
    if (response.session_result) {
      openSessionResultPage(response.session_result);
      return;
    }
    await initializeData();
    syncVideoPreviewWithSession(false);
  } catch (error) {
    setGlobalError(error.message);
  }
}

async function refreshAll() {
  try {
    setGlobalError(null);
    await initializeData();
    syncVideoPreviewWithSession(true);
  } catch (error) {
    setGlobalError(error.message);
  }
}

function shouldAutoStopOnPageExit() {
  const sessionState = state.status?.session_state;
  const sourceType = state.status?.source_type;
  return (
    (sessionState === "running" || sessionState === "starting") &&
    sourceType === "camera"
  );
}

function stopAnalysisOnPageExit() {
  if (!shouldAutoStopOnPageExit()) {
    return;
  }

  try {
    fetch("/analysis/stop", {
      method: "POST",
      keepalive: true,
    });
  } catch (_error) {
    // Best effort only; the page is closing.
  }
}

els.videoPreview.addEventListener("load", () => {
  state.videoLoading = false;
  clearVideoOverlayIfRecoverable();
});

els.videoPreview.addEventListener("error", () => {
  state.videoLoading = false;
  state.videoErrored = true;
  showVideoOverlay("Preview unavailable");
});

els.startButton.addEventListener("click", startAnalysis);
els.fastButton.addEventListener("click", runFastAnalysis);
els.stopButton.addEventListener("click", stopAnalysis);
els.refreshButton.addEventListener("click", refreshAll);
els.sourceTypeInput.addEventListener("change", syncSourceInputState);
window.addEventListener("pagehide", stopAnalysisOnPageExit);

initializeData()
  .catch((error) => setGlobalError(error.message))
  .finally(() => {
    syncSourceInputState();
    renderStatus();
    renderSummary();
    renderLatest();
    syncVideoPreviewWithSession(false);
    connectWebSocket();
  });




