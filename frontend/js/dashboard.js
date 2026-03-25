/**
 * Dashboard renderer (preset UI).
 *
 * index.html expects the ML_SAMPLE_OUTPUT-like shape:
 * { meta, city, zoneCounts, predictions }
 */

function formatTime(iso) {
  try {
    return new Date(iso).toLocaleString("en-IN", {
      dateStyle: "medium",
      timeStyle: "short",
      timeZone: "Asia/Kolkata"
    });
  } catch {
    return String(iso);
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
  const { meta, city, zoneCounts, predictions } = data || {};
  if (!meta || !city || !zoneCounts || !Array.isArray(predictions)) return;

  const dashGenerated = document.getElementById("dash-generated");
  const dashModel = document.getElementById("dash-model");
  const dashSource = document.getElementById("dash-source");

  const statRiskScore = document.getElementById("stat-risk-score");
  const statOverall = document.getElementById("stat-overall");
  const statSos = document.getElementById("stat-sos");
  const statSensors = document.getElementById("stat-sensors");

  if (dashGenerated) dashGenerated.textContent = formatTime(meta.generatedAt);
  if (dashModel) dashModel.textContent = `${meta.modelId} · ${meta.modelVersion}`;
  if (dashSource) {
    dashSource.textContent =
      meta.source === "preset" ? "Sample preset (swap for API)" : String(meta.source);
  }

  if (statRiskScore) statRiskScore.textContent = String(city.riskScore);
  if (statOverall) statOverall.textContent = city.overallRisk;
  if (statSos) statSos.textContent = String(city.activeSosCount);
  if (statSensors) statSensors.textContent = `${city.sensorsOnline}/${city.sensorsTotal}`;

  const zoneGrid = document.getElementById("zone-grid");
  if (zoneGrid) {
    zoneGrid.innerHTML = "";
    ["Green", "Yellow", "Orange", "Red"].forEach((name) => {
      const n = zoneCounts[name] ?? 0;
      const el = document.createElement("div");
      el.className = "zone-card";
      el.innerHTML = `<span class="${zoneClass(name)}">${name}</span><strong>${n}</strong><span class="zone-card-label">nodes</span>`;
      zoneGrid.appendChild(el);
    });
  }

  const tbody = document.querySelector("#predictions-table tbody");
  if (tbody) {
    tbody.innerHTML = "";
    predictions
      .slice()
      .sort((a, b) => (b.floodProbability || 0) - (a.floodProbability || 0))
      .forEach((row) => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${row.location}</td>
          <td><span class="${zoneClass(row.zone)}">${row.zone}</span></td>
          <td>${((row.floodProbability || 0) * 100).toFixed(1)}%</td>
          <td>${row.waterLevelCm}</td>
          <td>${row.sos ? '<span class="sos-flag">SOS</span>' : "—"}</td>
        `;
        tbody.appendChild(tr);
      });
  }
}

async function loadDashboardData() {
  // If fetchPredictions exists (api.js loaded), try it. Otherwise use preset.
  if (typeof window.fetchPredictions === "function") {
    try {
      return await window.fetchPredictions();
    } catch (e) {
      console.warn("API unavailable, using mockData:", e);
    }
  }
  return window.ML_SAMPLE_OUTPUT;
}

document.addEventListener("DOMContentLoaded", async () => {
  const data = await loadDashboardData();
  renderDashboard(data);
});