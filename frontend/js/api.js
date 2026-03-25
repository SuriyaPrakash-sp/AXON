/**
 * frontend/js/api.js
 * Fetch ML-shaped dashboard data.
 *
 * For now, the dashboard needs a single JSON shape (ML_SAMPLE_OUTPUT-like):
 * { meta, city, zoneCounts, predictions }
 *
 * This file tries to build that shape from the FastAPI endpoints:
 * - GET /api/nodes
 * - GET /api/stats
 *
 * If backend is not reachable, throw so dashboard can fall back to mockData.js.
 */

function getApiBase() {
  const m = document.querySelector('meta[name="api-base"]');
  const raw = (m && m.getAttribute("content")) || "";
  // For GH Pages we expect the fetch to fail and fall back to mock data.
  return (raw && raw.trim()) || "";
}

function normalizeBase(base) {
  if (!base) return "";
  return base.replace(/\/$/, "");
}

function buildUrl(base, path) {
  const p = path.startsWith("/") ? path : `/${path}`;
  if (!base) return p;
  // Use URL to avoid breaking "http://"
  return new URL(p, `${normalizeBase(base)}/`).toString();
}

function mapAlertToZone(alertLevel) {
  // Backend labels are: SAFE, WATCH, WARNING, DANGER
  const s = String(alertLevel).toUpperCase();
  if (s === "SAFE") return "Green";
  if (s === "WATCH") return "Yellow";
  if (s === "WARNING") return "Orange";
  if (s === "DANGER") return "Red";
  return "Green";
}

async function tryFetchPredictionsFromFastApi(base) {
  const nodesUrl = buildUrl(base, "/api/nodes");
  const statsUrl = buildUrl(base, "/api/stats");

  const [nodesRes, statsRes] = await Promise.all([fetch(nodesUrl), fetch(statsUrl)]);
  if (!nodesRes.ok) throw new Error(`nodes HTTP ${nodesRes.status}`);
  if (!statsRes.ok) throw new Error(`stats HTTP ${statsRes.status}`);

  const nodes = await nodesRes.json();
  await statsRes.json(); // currently unused, but keeps API contract checked

  const counts = { Green: 0, Yellow: 0, Orange: 0, Red: 0 };
  let activeSosCount = 0;

  const predictions = nodes.map((n) => {
    const zone = mapAlertToZone(n.alert_level);
    counts[zone] = (counts[zone] || 0) + 1;
    if (String(n.alert_level).toUpperCase() === "DANGER") activeSosCount += 1;

    // FastAPI gives confidence as percent (e.g., 62.5) -> convert to 0..1 for our UI.
    const p = typeof n.confidence === "number" ? n.confidence : parseFloat(n.confidence);
    const floodProbability = Number.isFinite(p) ? p / 100 : 0;

    return {
      location: n.node_name,
      zone,
      floodProbability,
      waterLevelCm: n.water_level_cm,
      sos: String(n.alert_level).toUpperCase() === "DANGER"
    };
  });

  const total = nodes.length || 1;
  const scoreWeighted =
    (counts.Red * 90 + counts.Orange * 70 + counts.Yellow * 40 + counts.Green * 10) / total;
  const riskScore = Math.round(scoreWeighted);

  const overallRisk =
    counts.Red > 0 ? "severe" : counts.Orange > 0 ? "high" : counts.Yellow > 0 ? "elevated" : "low";

  const generatedAt = nodes[0]?.timestamp || new Date().toISOString();

  return {
    meta: {
      modelId: "chennai-flood-risk-v0",
      modelVersion: "fastapi-live",
      generatedAt,
      source: "backend-fastapi"
    },
    city: {
      overallRisk,
      riskScore,
      activeSosCount,
      sensorsOnline: nodes.length,
      sensorsTotal: nodes.length
    },
    zoneCounts: counts,
    predictions
  };
}

/**
 * @returns {Promise<object>} ML_SAMPLE_OUTPUT-like JSON
 */
async function fetchPredictions() {
  // 1) Prefer explicit base from meta tag (useful for local testing / different ports)
  const base = getApiBase();
  try {
    return await tryFetchPredictionsFromFastApi(base);
  } catch (e) {
    // 2) Fallback to relative URLs (same-origin) in case base is blank/wrong port
    return await tryFetchPredictionsFromFastApi("");
  }
}

// Expose globally for dashboard.js
window.fetchPredictions = fetchPredictions;