const state = {
  sessionKey: null,
  drivers: [],
  selectedDrivers: [],
};

const api = {
  sessions: "/api/sessions",
  summary: (sessionKey) => `/api/race_intelligence/session_summary?session_key=${sessionKey}`,
  drivers: (sessionKey) => `/api/race_intelligence/driver_options?session_key=${sessionKey}`,
  duel: (sessionKey, driverOne, driverTwo) =>
    `/api/race_intelligence/driver_duel?session_key=${sessionKey}&driver_1=${driverOne}&driver_2=${driverTwo}`,
  timeline: (sessionKey) => `/api/race_intelligence/strategy_timeline?session_key=${sessionKey}`,
  health: (sessionKey) => `/api/race_intelligence/pipeline_health?session_key=${sessionKey}`,
  predictions: (sessionKey) => `/api/race_intelligence/prediction_status?session_key=${sessionKey}`,
};

async function getJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

function setText(id, value) {
  document.getElementById(id).textContent = value ?? "--";
}

function emptyState(message) {
  return `<div class="empty-state">${message}</div>`;
}

function formatNumber(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "--";
  }
  return Number(value).toFixed(digits);
}

function renderSessions(sessions) {
  const select = document.getElementById("sessionKey");
  select.innerHTML = "";
  sessions.forEach((session) => {
    const option = document.createElement("option");
    option.value = session.session_key;
    option.textContent = `${session.year} ${session.country_name} - ${session.session_name}`;
    select.appendChild(option);
  });
  state.sessionKey = sessions[0]?.session_key ?? null;
}

function renderSummary(summary) {
  if (!summary.available || !summary.data) {
    setText("winnerValue", "No session");
    setText("winnerMeta", summary.metadata?.empty_state?.message || "Unavailable");
    setText("driverCount", "0");
    setText("eventCount", "0");
    setText("pipelineStatus", "Unavailable");
    setText("pipelineMeta", summary.reason);
    return;
  }

  const data = summary.data;
  setText("winnerValue", data.winner?.driver || "--");
  setText("winnerMeta", data.winner?.team || data.session.country_name || "--");
  setText("driverCount", data.driver_count);
  setText("eventCount", data.event_count);
  setText("pipelineStatus", data.latest_pipeline_status || "No run");
  setText("pipelineMeta", data.gold_predictions_available ? "Gold available" : "Gold pending");
}

function renderDriverSelects(drivers) {
  state.drivers = drivers.data || [];
  const selects = [document.getElementById("driverOne"), document.getElementById("driverTwo")];
  selects.forEach((select) => {
    select.innerHTML = "";
    state.drivers.forEach((driver) => {
      const option = document.createElement("option");
      option.value = driver.driver_number;
      option.textContent = `${driver.name_acronym || driver.driver_number} - ${driver.team_name || "Unknown"}`;
      select.appendChild(option);
    });
  });
  const comparableDrivers = state.drivers.filter((driver) => driver.has_telemetry);
  const defaultDrivers = comparableDrivers.length > 1 ? comparableDrivers : state.drivers;
  if (defaultDrivers.length > 1) {
    selects[0].value = defaultDrivers[0].driver_number;
    selects[1].value = defaultDrivers[1].driver_number;
  }
  state.selectedDrivers = selects.map((select) => Number(select.value)).filter(Boolean);
}

function renderDuel(duel) {
  const cards = document.getElementById("duelCards");
  if (!duel.available || !duel.data) {
    cards.innerHTML = emptyState(duel.metadata?.empty_state?.message || "No comparable telemetry.");
    const chart = document.getElementById("duelChart");
    Plotly.purge(chart);
    chart.innerHTML = emptyState("No telemetry comparison is available for the selected drivers.");
    return;
  }
  const drivers = Object.values(duel.data.drivers);
  cards.innerHTML = drivers
    .map(
      (driver) => `
        <article class="driver-card">
          <strong>#${driver.driver_number}</strong>
          <dl>
            <dt>Max speed</dt><dd>${formatNumber(driver.max_speed, 0)} km/h</dd>
            <dt>Max RPM</dt><dd>${formatNumber(driver.max_rpm, 0)}</dd>
            <dt>Full throttle</dt><dd>${formatNumber(driver.full_throttle_pct)}%</dd>
            <dt>Best pit</dt><dd>${formatNumber(driver.best_pit)}s</dd>
          </dl>
        </article>
      `,
    )
    .join("");

  const traces = drivers.map((driver) => ({
    type: "bar",
    name: `#${driver.driver_number}`,
    x: ["Speed", "RPM", "Throttle", "DRS"],
    y: [
      driver.max_speed || 0,
      (driver.max_rpm || 0) / 40,
      driver.full_throttle_pct || 0,
      driver.drs_pct || 0,
    ],
  }));
  Plotly.react("duelChart", traces, {
    paper_bgcolor: "#191d24",
    plot_bgcolor: "#191d24",
    font: { color: "#edf1f5" },
    margin: { t: 20, r: 16, b: 40, l: 42 },
    legend: { orientation: "h" },
    colorway: ["#e43d30", "#22b8a7", "#f2b84b"],
  }, { displayModeBar: false, responsive: true });
}

function renderTimeline(timeline) {
  const target = document.getElementById("timelineList");
  if (!timeline.available || !timeline.data.length) {
    target.innerHTML = emptyState("No strategy events were found for this session.");
    return;
  }
  target.innerHTML = timeline.data
    .map(
      (event) => `
        <article class="timeline-item ${event.severity}">
          <span class="timeline-time">${event.timestamp || "--"}</span>
          <span class="timeline-source">${event.event_type}</span>
          <div>
            <strong>${event.label}</strong>
            <div>${event.driver || "General"} ${event.lap_number ? `- Lap ${event.lap_number}` : ""}</div>
          </div>
        </article>
      `,
    )
    .join("");
}

function renderHealth(health) {
  const target = document.getElementById("healthPanel");
  if (!health.available || !health.data) {
    target.innerHTML = emptyState(health.metadata?.empty_state?.message || "No pipeline history.");
    return;
  }
  const latest = health.data.latest_execution;
  target.innerHTML = `
    <div class="health-row"><strong>${health.data.health_status}</strong></div>
    <div class="health-row">Run: ${latest.run_id || "--"}</div>
    <div class="health-row">Duration: ${formatNumber(latest.duration_seconds, 2)}s</div>
    <div class="health-row">Rows Silver: ${latest.total_rows_silver ?? "--"}</div>
    <div class="health-row">Quarantine: ${formatNumber((latest.quarantine_rate || 0) * 100, 2)}%</div>
  `;
}

function renderPredictions(predictions) {
  const target = document.getElementById("predictionPanel");
  if (!predictions.available || !predictions.data?.available) {
    target.innerHTML = emptyState(
      predictions.metadata?.empty_state?.message || "Gold predictions are not available for this session.",
    );
    return;
  }
  const data = predictions.data;
  target.innerHTML = `
    <div class="prediction-kpis">
      <div><strong>${data.prediction_count}</strong><span>Predictions</span></div>
      <div><strong>${data.driver_count}</strong><span>Drivers</span></div>
      <div><strong>${formatNumber(data.avg_delta, 3)}s</strong><span>Avg delta</span></div>
      <div><strong>${formatNumber(data.max_delta, 3)}s</strong><span>Max delta</span></div>
    </div>
  `;
}

async function refreshDashboard() {
  if (!state.sessionKey) return;
  const sessionKey = state.sessionKey;
  const [summary, drivers, timeline, health, predictions] = await Promise.all([
    getJson(api.summary(sessionKey)),
    getJson(api.drivers(sessionKey)),
    getJson(api.timeline(sessionKey)),
    getJson(api.health(sessionKey)),
    getJson(api.predictions(sessionKey)),
  ]);
  renderSummary(summary);
  renderDriverSelects(drivers);
  renderTimeline(timeline);
  renderHealth(health);
  renderPredictions(predictions);
  await refreshDuel();
}

async function refreshDuel() {
  const driverOne = Number(document.getElementById("driverOne").value);
  const driverTwo = Number(document.getElementById("driverTwo").value);
  if (!state.sessionKey || !driverOne || !driverTwo || driverOne === driverTwo) {
    document.getElementById("duelCards").innerHTML = emptyState("Select two different drivers.");
    document.getElementById("duelChart").innerHTML = emptyState("Select two different drivers.");
    return;
  }
  const duel = await getJson(api.duel(state.sessionKey, driverOne, driverTwo));
  renderDuel(duel);
}

function bindEvents() {
  document.getElementById("refreshButton").addEventListener("click", refreshDashboard);
  document.getElementById("sessionKey").addEventListener("change", (event) => {
    state.sessionKey = Number(event.target.value);
    refreshDashboard();
  });
  document.getElementById("driverOne").addEventListener("change", refreshDuel);
  document.getElementById("driverTwo").addEventListener("change", refreshDuel);
  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      document.querySelectorAll(".tab-button").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
      button.classList.add("active");
      document.getElementById(button.dataset.view).classList.add("active");
    });
  });
}

async function bootstrap() {
  bindEvents();
  try {
    const sessions = await getJson(api.sessions);
    renderSessions(sessions);
    await refreshDashboard();
  } catch (error) {
    document.querySelector(".app-shell").innerHTML = emptyState(
      "Race Intelligence API is unavailable or no sessions were found.",
    );
  }
}

bootstrap();
