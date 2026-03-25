/**
 * Dashboard UI driven by ML_SAMPLE_OUTPUT in data.js.
 * Later: replace loadDashboardData() body with fetch(url).then(r => r.json()).
 */

function loadDashboardData() {
  return Promise.resolve(ML_SAMPLE_OUTPUT);
}

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Asia/Kolkata"
    });
  } catch {
    return iso;
  }
}

function zoneClass(zone) {
  const z = String(zone).toLowerCase();
  if (z === "green") return "zone-pill zone-green";
  if (z === "yellow") return "zone-pill zone-yellow";
  if (z === "orange") return "zone-pill zone-orange";
  if (z === "red") return "zone-pill zone-red";
  return "zone-pill";
}

function renderDashboard(data) {
  const { meta, city, zoneCounts, predictions } = data;

  document.getElementById("dash-generated").textContent = formatTime(meta.generatedAt);
  document.getElementById("dash-model").textContent = `${meta.modelId} · ${meta.modelVersion}`;
  document.getElementById("dash-source").textContent =
    meta.source === "preset" ? "Sample preset (swap for API)" : meta.source;

  document.getElementById("stat-risk-score").textContent = String(city.riskScore);
  document.getElementById("stat-overall").textContent = city.overallRisk;
  document.getElementById("stat-sos").textContent = String(city.activeSosCount);
  document.getElementById("stat-sensors").textContent = `${city.sensorsOnline}/${city.sensorsTotal}`;

  const zoneGrid = document.getElementById("zone-grid");
  zoneGrid.innerHTML = "";
  ["Green", "Yellow", "Orange", "Red"].forEach((name) => {
    const n = zoneCounts[name] ?? 0;
    const el = document.createElement("div");
    el.className = "zone-card";
    el.innerHTML = `<span class="${zoneClass(name)}">${name}</span><strong>${n}</strong><span class="zone-card-label">nodes</span>`;
    zoneGrid.appendChild(el);
  });

  const tbody = document.querySelector("#predictions-table tbody");
  tbody.innerHTML = "";
  predictions
    .slice()
    .sort((a, b) => b.floodProbability - a.floodProbability)
    .forEach((row) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${row.location}</td>
        <td><span class="${zoneClass(row.zone)}">${row.zone}</span></td>
        <td>${(row.floodProbability * 100).toFixed(1)}%</td>
        <td>${row.waterLevelCm}</td>
        <td>${row.sos ? '<span class="sos-flag">SOS</span>' : "—"}</td>
      `;
      tbody.appendChild(tr);
    });
}

document.addEventListener("DOMContentLoaded", () => {
  loadDashboardData().then(renderDashboard);
});
