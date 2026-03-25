"""
backend/app.py  — FloodSense unified server
Serves frontend/ as static files AND exposes the ML API.

  cd backend
  pip install -r requirements.txt
  python train.py          # once
  python app.py            # then open http://localhost:8000
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import numpy as np
import joblib
import sqlite3
import os
import sys
import subprocess
from dotenv import load_dotenv
from pipeline import fetch_weather, build_features

# Load API key from either backend/.env or repo-root .env (common on Windows setups).
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# ── Config ────────────────────────────────────────────────────────────────────
OWM_API_KEY = os.getenv("OWM_API_KEY", "")
FRONTEND    = os.path.join(os.path.dirname(__file__), "..", "frontend")
PAGES_ROOT  = os.path.join(os.path.dirname(__file__), "..")
DB_PATH     = "floodsense.db"

FEATURES = [
    "temp_c", "humidity_pct", "pressure_hpa", "dew_point_c",
    "cloud_cover_pct", "visibility_m", "wind_speed_ms", "wind_gust_ms",
    "uvi", "rain_1h_mm", "prob_precip", "rain_next6h_mm", "weather_severity",
    "rainfall_mm", "rain_6h_roll", "rain_24h_roll", "rain_intensity_score",
    "water_level_cm", "wl_rate_of_change", "wl_roll_mean_6h", "wl_roll_max_6h",
    "soil_moisture_pct", "upstream_flow_cms",
    "monsoon_season", "hour_of_day", "is_night",
]

LABELS  = {0:"SAFE", 1:"WATCH", 2:"WARNING", 3:"DANGER"}
COLORS  = {0:"#00C77A", 1:"#F59E0B", 2:"#F97316", 3:"#EF4444"}
ACTIONS = {
    0: "No action required.",
    1: "Monitor closely. Alert ward officials.",
    2: "Issue public advisory. Prepare evacuation routes.",
    3: "IMMEDIATE EVACUATION. Activate all emergency protocols.",
}

# Chennai sensor node locations
NODES = {
    "NODE_001": {"name": "Adyar River",    "lat": 13.0050, "lon": 80.2552},
    "NODE_002": {"name": "Velachery Lake", "lat": 12.9788, "lon": 80.2209},
    "NODE_003": {"name": "Kotturpuram",    "lat": 13.0180, "lon": 80.2414},
    "NODE_004": {"name": "Pallikaranai",   "lat": 12.9373, "lon": 80.2195},
    "NODE_005": {"name": "Saidapet",       "lat": 13.0211, "lon": 80.2237},
}

# ── Load model ────────────────────────────────────────────────────────────────
def _ensure_model_artifacts():
    """
    Ensure model.pkl and scaler.pkl exist and are readable.
    If missing/corrupt (common after repo moves or bad placeholders), regenerate via train.py.
    """
    need_train = (not os.path.exists("model.pkl")) or (not os.path.exists("scaler.pkl"))
    if not need_train:
        try:
            joblib.load("model.pkl")
            joblib.load("scaler.pkl")
            return
        except Exception:
            need_train = True

    if need_train:
        # Train using synthetic data if real CSV is absent.
        cmd = [sys.executable, "train.py"]
        subprocess.run(cmd, check=True)


_ensure_model_artifacts()
model = joblib.load("model.pkl")
scaler = joblib.load("scaler.pkl")

# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="FloodSense AXON", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

# ── DB ────────────────────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT, node_name TEXT, timestamp TEXT,
            alert_level TEXT, alert_code INTEGER, confidence REAL,
            water_level_cm REAL, rainfall_mm REAL,
            cloud_cover_pct REAL, humidity_pct REAL
        )
    """)
    conn.commit(); conn.close()

def save(node_id, node_name, ts, alert_level, alert_code, conf, features):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO readings VALUES (NULL,?,?,?,?,?,?,?,?,?,?)",
        (node_id, node_name, ts, alert_level, alert_code, conf,
         features["water_level_cm"], features["rainfall_mm"],
         features["cloud_cover_pct"], features["humidity_pct"])
    )
    conn.commit(); conn.close()

def query(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(sql, params).fetchall(); conn.close()
    return rows

init_db()

# ── ML helper ─────────────────────────────────────────────────────────────────
def run_model(features: dict):
    X = np.array([[features.get(f, 0.0) for f in FEATURES]])
    Xs = scaler.transform(X)
    idx   = int(model.predict(Xs)[0])
    proba = model.predict_proba(Xs)[0]
    return idx, proba


# ── API routes ────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "nodes": len(NODES), "api_key_set": bool(OWM_API_KEY)}


@app.get("/api/predict/{node_id}")
def predict(node_id: str):
    """Fetch live OWM data for a node and return ML prediction."""
    if node_id not in NODES:
        raise HTTPException(404, f"Unknown node: {node_id}")
    if not OWM_API_KEY:
        raise HTTPException(503, "OWM_API_KEY not set in .env")

    cfg  = NODES[node_id]
    raw  = fetch_weather(cfg["lat"], cfg["lon"], OWM_API_KEY)
    if raw is None:
        raise HTTPException(503, "OWM API unreachable")

    features = build_features(raw, node_id)
    idx, proba = run_model(features)
    conf = round(float(proba[idx]) * 100, 1)

    save(node_id, cfg["name"], features["_timestamp"],
         LABELS[idx], idx, conf, features)

    return {
        "node_id":       node_id,
        "node_name":     cfg["name"],
        "alert_level":   LABELS[idx],
        "alert_code":    idx,
        "alert_color":   COLORS[idx],
        "confidence":    conf,
        "probabilities": {LABELS[i]: round(float(p)*100,1) for i,p in enumerate(proba)},
        "action":        ACTIONS[idx],
        "timestamp":     features["_timestamp"],
        "weather_desc":  features["_weather_desc"],
        "features": {k: v for k, v in features.items() if not k.startswith("_")},
    }


@app.get("/api/nodes")
def all_nodes():
    """Predict all nodes — called by dashboard every few seconds."""
    if not OWM_API_KEY:
        raise HTTPException(503, "OWM_API_KEY not set in .env")
    results = []
    for node_id, cfg in NODES.items():
        try:
            raw = fetch_weather(cfg["lat"], cfg["lon"], OWM_API_KEY)
            if raw is None: continue
            features = build_features(raw, node_id)
            idx, proba = run_model(features)
            conf = round(float(proba[idx])*100, 1)
            save(node_id, cfg["name"], features["_timestamp"],
                 LABELS[idx], idx, conf, features)
            results.append({
                "node_id":      node_id,
                "node_name":    cfg["name"],
                "alert_level":  LABELS[idx],
                "alert_code":   idx,
                "alert_color":  COLORS[idx],
                "confidence":   conf,
                "action":       ACTIONS[idx],
                "timestamp":    features["_timestamp"],
                "water_level_cm": features["water_level_cm"],
                "rainfall_mm":    features["rainfall_mm"],
                "cloud_cover_pct":features["cloud_cover_pct"],
                "humidity_pct":   features["humidity_pct"],
                "weather_desc":   features["_weather_desc"],
            })
        except Exception as e:
            print(f"[{node_id}] error: {e}")
    results.sort(key=lambda r: r["alert_code"], reverse=True)
    return results


@app.get("/api/history/{node_id}")
def history(node_id: str, limit: int = 30):
    rows = query(
        "SELECT timestamp, water_level_cm, rainfall_mm, alert_level, confidence "
        "FROM readings WHERE node_id=? ORDER BY id DESC LIMIT ?",
        (node_id, limit)
    )
    return [{"timestamp":r[0],"water_level_cm":r[1],"rainfall_mm":r[2],
             "alert_level":r[3],"confidence":r[4]} for r in reversed(rows)]


@app.get("/api/stats")
def stats():
    total = query("SELECT COUNT(*) FROM readings")[0][0]
    dist  = dict(query("SELECT alert_level, COUNT(*) FROM readings GROUP BY alert_level"))
    return {"total": total, "distribution": dist}


# ── Serve frontend static files ───────────────────────────────────────────────
if os.path.isdir(FRONTEND):
    # Serve assets under /frontend/* so root HTML can reference them.
    app.mount("/frontend", StaticFiles(directory=FRONTEND), name="frontend")

    @app.get("/")
    def root():
        idx = os.path.join(PAGES_ROOT, "index.html")
        return FileResponse(idx) if os.path.exists(idx) else HTMLResponse(
            "<h2>Missing index.html in repo root</h2>"
        )

    @app.get("/{path:path}")
    def catch_all(path: str):
        # First try repo-root pages (map.html, etc.)
        fp_root = os.path.join(PAGES_ROOT, path)
        if os.path.isfile(fp_root):
            return FileResponse(fp_root)

        # Then try assets under frontend/
        fp_assets = os.path.join(FRONTEND, path)
        if os.path.isfile(fp_assets):
            return FileResponse(fp_assets)

        raise HTTPException(404, f"{path} not found")


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    print("\n  FloodSense AXON")
    print("  Dashboard -> http://localhost:8000")
    print("  API docs  -> http://localhost:8000/docs\n")
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)