/**
 * Backend API helpers. Base URL: <meta name="api-base" content="http://127.0.0.1:5000"> in index.html,
 * or defaults to http://127.0.0.1:5000 when the meta tag is absent.
 */

function getApiBase() {
  if (typeof document === "undefined") return "http://127.0.0.1:5000";
  const m = document.querySelector('meta[name="api-base"]');
  const raw = m && m.getAttribute("content");
  return (raw && raw.trim()) || "http://127.0.0.1:5000";
}

/**
 * @returns {Promise<object>} ML_SAMPLE_OUTPUT-shaped JSON from backend
 */
function fetchPredictions() {
  const base = getApiBase().replace(/\/$/, "");
  return fetch(`${base}/api/predictions`, {
    method: "GET",
    headers: { Accept: "application/json" }
  }).then((res) => {
    if (!res.ok) throw new Error(`predictions HTTP ${res.status}`);
    return res.json();
  });
}
