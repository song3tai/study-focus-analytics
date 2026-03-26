const SESSION_RESULT_STORAGE_KEY = "study_focus_session_result";

const els = {
  emptyState: document.getElementById("empty-state"),
  resultPage: document.getElementById("result-page"),
  resultTitle: document.getElementById("result-title"),
  resultSubtitle: document.getElementById("result-subtitle"),
  resultInsight: document.getElementById("result-insight"),
  modeBadge: document.getElementById("mode-badge"),
  sessionMeta: document.getElementById("session-meta"),
  primarySummaryGrid: document.getElementById("primary-summary-grid"),
  secondarySummaryGrid: document.getElementById("secondary-summary-grid"),
  eventsCount: document.getElementById("events-count"),
  eventsList: document.getElementById("events-list"),
  timelineList: document.getElementById("timeline-list"),
  debugGrid: document.getElementById("debug-grid"),
};

function safeReadSessionResult() {
  try {
    const raw = window.sessionStorage.getItem(SESSION_RESULT_STORAGE_KEY);
    if (!raw) {
      return null;
    }
    return JSON.parse(raw);
  } catch (_error) {
    return null;
  }
}

function isNumber(value) {
  return value !== null && value !== undefined && !Number.isNaN(Number(value));
}

function formatSeconds(value) {
  if (!isNumber(value)) {
    return "-";
  }

  const total = Math.max(0, Math.round(Number(value)));
  const hours = String(Math.floor(total / 3600)).padStart(2, "0");
  const minutes = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
  const seconds = String(total % 60).padStart(2, "0");
  return `${hours}:${minutes}:${seconds}`;
}

function formatScore(value) {
  if (!isNumber(value)) {
    return "-";
  }
  return Number(value).toFixed(2);
}

function formatText(value) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }
  return String(value);
}

function formatDateTime(value) {
  if (!value) {
    return "-";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }
  return parsed.toLocaleString();
}

function escapeHtml(value) {
  return formatText(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function toTitleCase(value) {
  return formatText(value)
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function toneForMode(mode) {
  if (mode === "fast") {
    return "accent";
  }
  if (mode === "realtime") {
    return "success";
  }
  return "neutral";
}

function toneForState(value) {
  if (value === "present" || value === "studying") {
    return "success";
  }
  if (value === "away") {
    return "danger";
  }
  if (value === "unknown") {
    return "warning";
  }
  if (value) {
    return "accent";
  }
  return "neutral";
}

function buildResultIdentity(result) {
  if (result.analysis_mode === "fast") {
    return {
      title: "Fast Analysis Result",
      subtitle: "This result was produced from a video file using the fast offline analysis flow.",
    };
  }

  if (result.analysis_mode === "realtime") {
    return {
      title: "Realtime Session Result",
      subtitle: "This result was finalized after stopping a realtime analysis session.",
    };
  }

  return {
    title: "Analysis Result",
    subtitle: "This page summarizes one completed analysis session.",
  };
}

function buildResultInsight(result) {
  const summary = result.summary || {};
  const total = Number(summary.total_duration_sec || 0);
  const awayDuration = Number(summary.total_away_duration_sec || 0);
  const awayCount = Number(summary.away_count || 0);
  const averageFocus = Number(summary.average_focus_score || 0);
  const awayRatio = total > 0 ? awayDuration / total : 0;

  if (total <= 0) {
    return "This session completed, but there is not enough recorded duration to describe a clear pattern yet.";
  }

  if (awayCount === 0 && awayRatio < 0.1 && averageFocus >= 0.7) {
    return "This session stayed relatively stable with limited away time and a steady overall pattern.";
  }

  if (awayCount <= 1 && awayRatio < 0.2 && averageFocus >= 0.5) {
    return "This session included limited away time and a moderate overall focus level.";
  }

  if (awayCount >= 3 || awayRatio >= 0.35 || averageFocus < 0.4) {
    return "This session showed repeated away periods or a lower average focus level.";
  }

  return "This session included some interruptions alongside periods of stable activity.";
}

function buildEventExplanation(event) {
  const message = formatText(event.message);
  if (message !== "-") {
    return message.charAt(0).toUpperCase() + message.slice(1);
  }

  const explanations = {
    away_started: "The user left the study or work area.",
    away_ended: "The user returned to the study or work area.",
    studying_started: "The session entered a stable studying state.",
    studying_ended: "The session left the stable studying state.",
    present_started: "The user became present in the target area.",
    present_ended: "The user was no longer considered present in the target area.",
    state_changed: "The behavior state changed during the session.",
  };

  return explanations[event.event_type] || "A notable session event was recorded.";
}

function buildEventTechnicalSummary(event) {
  const parts = [];
  if (event.state_before || event.state_after) {
    parts.push(`Transition: ${formatText(event.state_before)} -> ${formatText(event.state_after)}`);
  }
  if (event.frame_id !== null && event.frame_id !== undefined) {
    parts.push(`Frame: ${formatText(event.frame_id)}`);
  }
  return parts;
}

function createMetaItem(label, value) {
  const item = document.createElement("article");
  item.className = "meta-item";
  item.innerHTML = `
    <span class="meta-label">${escapeHtml(label)}</span>
    <span class="meta-value">${escapeHtml(value)}</span>
  `;
  return item;
}

function createSummaryCard(label, value, className = "summary-card") {
  const card = document.createElement("article");
  card.className = className;
  const valueClass = className === "secondary-card" ? "secondary-value" : "summary-value";
  const labelClass = className === "secondary-card" ? "secondary-label" : "summary-label";
  card.innerHTML = `
    <span class="${labelClass}">${escapeHtml(label)}</span>
    <span class="${valueClass}">${escapeHtml(value)}</span>
  `;
  return card;
}

function createPlaceholder(message) {
  const placeholder = document.createElement("div");
  placeholder.className = "placeholder-card";
  placeholder.innerHTML = `<span class="meta-value">${escapeHtml(message)}</span>`;
  return placeholder;
}

function createTechnicalDetails(title, lines, payload) {
  const safeLines = lines.filter(Boolean);
  const hasPayload = payload && Object.keys(payload).length > 0;
  if (!safeLines.length && !hasPayload) {
    return "";
  }

  const detailItems = safeLines
    .map((line) => `<span class="technical-meta">${escapeHtml(line)}</span>`)
    .join("");
  const payloadBlock = hasPayload
    ? `<pre class="payload-box">${escapeHtml(JSON.stringify(payload, null, 2))}</pre>`
    : "";

  return `
    <details class="inline-details">
      <summary>${escapeHtml(title)}</summary>
      <div class="detail-grid">
        ${detailItems}
        ${payloadBlock}
      </div>
    </details>
  `;
}

function renderHeader(result) {
  const identity = buildResultIdentity(result);
  els.resultTitle.textContent = identity.title;
  els.resultSubtitle.textContent = identity.subtitle;
  els.modeBadge.textContent = toTitleCase(result.analysis_mode);
  els.modeBadge.className = `status-pill ${toneForMode(result.analysis_mode)}`;

  const items = [
    ["Source Name", formatText(result.source_name)],
    ["Source Type", toTitleCase(result.source_type)],
    ["Session Duration", formatSeconds(result.duration_sec)],
    ["Started At", formatDateTime(result.started_at)],
    ["Finished At", formatDateTime(result.finished_at)],
    ["Session ID", formatText(result.session_id)],
  ];

  els.sessionMeta.innerHTML = "";
  items.forEach(([label, value]) => {
    els.sessionMeta.appendChild(createMetaItem(label, value));
  });
}

function renderResultInsight(result) {
  els.resultInsight.textContent = buildResultInsight(result);
}

function renderSummary(summary) {
  const primaryMetrics = [
    ["Total Duration", formatSeconds(summary?.total_duration_sec)],
    ["Present Duration", formatSeconds(summary?.total_present_duration_sec)],
    ["Away Duration", formatSeconds(summary?.total_away_duration_sec)],
    ["Away Count", formatText(summary?.away_count)],
    ["Average Focus", formatScore(summary?.average_focus_score)],
  ];

  const secondaryMetrics = [
    ["Studying Duration", formatSeconds(summary?.total_studying_duration_sec)],
    ["Max Focus", formatScore(summary?.max_focus_score)],
    ["Min Focus", formatScore(summary?.min_focus_score)],
  ];

  els.primarySummaryGrid.innerHTML = "";
  primaryMetrics.forEach(([label, value]) => {
    els.primarySummaryGrid.appendChild(createSummaryCard(label, value));
  });

  els.secondarySummaryGrid.innerHTML = "";
  secondaryMetrics.forEach(([label, value]) => {
    els.secondarySummaryGrid.appendChild(createSummaryCard(label, value, "secondary-card"));
  });
}

function renderEvents(events) {
  const safeEvents = Array.isArray(events) ? events : [];
  els.eventsCount.textContent = `${safeEvents.length} events`;
  els.eventsList.innerHTML = "";

  if (!safeEvents.length) {
    els.eventsList.appendChild(createPlaceholder("No events available"));
    return;
  }

  safeEvents.forEach((event) => {
    const item = document.createElement("article");
    item.className = "event-item";

    const technicalDetails = createTechnicalDetails(
      "Technical details",
      buildEventTechnicalSummary(event),
      event.payload,
    );

    item.innerHTML = `
      <div class="event-head">
        <div>
          <div class="event-title">${escapeHtml(toTitleCase(event.event_type))}</div>
        </div>
        <span class="event-time">At ${escapeHtml(formatSeconds(event.timestamp))}</span>
      </div>
      <div class="event-body">
        <div class="event-explanation">${escapeHtml(buildEventExplanation(event))}</div>
        ${technicalDetails}
      </div>
    `;

    els.eventsList.appendChild(item);
  });
}

function extractTimelineFields(segment) {
  return {
    start: segment?.start_sec ?? segment?.start_time ?? segment?.start ?? null,
    end: segment?.end_sec ?? segment?.end_time ?? segment?.end ?? null,
    state: segment?.state ?? segment?.label ?? segment?.type ?? "segment",
    duration: segment?.duration_sec ?? segment?.duration ?? null,
  };
}

function buildTimelineExtraLines(segment) {
  if (!segment || typeof segment !== "object") {
    return [];
  }

  const ignoredKeys = new Set(["start_sec", "start_time", "start", "end_sec", "end_time", "end", "state", "label", "type", "duration_sec", "duration"]);
  return Object.entries(segment)
    .filter(([key]) => !ignoredKeys.has(key))
    .map(([key, value]) => `${key}: ${typeof value === "object" ? JSON.stringify(value) : String(value)}`);
}

function renderTimeline(timeline) {
  const safeTimeline = Array.isArray(timeline) ? timeline : [];
  els.timelineList.innerHTML = "";

  if (!safeTimeline.length) {
    els.timelineList.appendChild(createPlaceholder("Timeline not available yet"));
    return;
  }

  safeTimeline.forEach((segment) => {
    const fields = extractTimelineFields(segment);
    const extraDetails = createTechnicalDetails(
      "Segment details",
      buildTimelineExtraLines(segment),
      null,
    );

    const item = document.createElement("article");
    item.className = "timeline-item";
    item.innerHTML = `
      <div class="timeline-head">
        <span class="timeline-badge ${toneForState(fields.state)}">${escapeHtml(toTitleCase(fields.state))}</span>
        <span class="timeline-duration">Duration: ${escapeHtml(formatSeconds(fields.duration))}</span>
      </div>
      <div class="timeline-body">
        <span class="timeline-time">${escapeHtml(formatSeconds(fields.start))} -> ${escapeHtml(formatSeconds(fields.end))}</span>
        ${extraDetails}
      </div>
    `;

    els.timelineList.appendChild(item);
  });
}

function renderDebug(result) {
  const items = [
    ["session_id", formatText(result.session_id)],
    ["analysis_mode", formatText(result.analysis_mode)],
    ["source_type", formatText(result.source_type)],
    ["source_name", formatText(result.source_name)],
    ["events_count", formatText(Array.isArray(result.events) ? result.events.length : 0)],
    ["timeline_length", formatText(Array.isArray(result.timeline) ? result.timeline.length : 0)],
    ["duration_sec", formatText(result.duration_sec)],
    ["metadata", result.metadata ? JSON.stringify(result.metadata, null, 2) : "-"],
  ];

  els.debugGrid.innerHTML = "";
  items.forEach(([label, value]) => {
    const item = document.createElement("div");
    item.className = "debug-item";
    item.innerHTML = `
      <span class="debug-label">${escapeHtml(label)}</span>
      <div class="debug-value">${escapeHtml(value)}</div>
    `;
    els.debugGrid.appendChild(item);
  });
}

function renderResult(result) {
  renderHeader(result);
  renderResultInsight(result);
  renderSummary(result.summary || {});
  renderEvents(result.events || []);
  renderTimeline(result.timeline || []);
  renderDebug(result);
}

function initializePage() {
  const result = safeReadSessionResult();
  if (!result) {
    els.emptyState.classList.remove("hidden");
    els.resultPage.classList.add("hidden");
    return;
  }

  els.emptyState.classList.add("hidden");
  els.resultPage.classList.remove("hidden");
  renderResult(result);
}

initializePage();
