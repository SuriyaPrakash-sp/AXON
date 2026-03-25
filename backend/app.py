"""
AXON flood API — serves ML-shaped JSON for the frontend dashboard.
Loads optional model.pkl from this directory when present; otherwise uses built-in demo payload.
"""

import os
from datetime import datetime, timezone

from flask import Flask, jsonify
from flask_cors import CORS

APP_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(APP_DIR, "model.pkl")

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


def _load_model_meta():
    """Optional: read metadata from model.pkl if joblib/pickle model exists."""
    try:
        import pickle

        with open(MODEL_PATH, "rb") as f:
            obj = pickle.load(f)
        if isinstance(obj, dict):
            return obj
        return {"artifact": str(type(obj).__name__)}
    except Exception:
        return None


def _demo_payload():
    tz = timezone.utc
    now = datetime.now(tz).isoformat().replace("+00:00", "Z")
    model_meta = _load_model_meta()
    version = "0.4.2-demo"
    if model_meta and isinstance(model_meta, dict) and "version" in model_meta:
        version = str(model_meta["version"])

    return {
        "meta": {
            "modelId": "chennai-flood-risk-v0",
            "modelVersion": version,
            "generatedAt": now,
            "source": "backend" if model_meta else "backend-demo",
        },
        "city": {
            "overallRisk": "elevated",
            "riskScore": 62,
            "activeSosCount": 4,
            "sensorsOnline": 20,
            "sensorsTotal": 20,
        },
        "zoneCounts": {"Green": 4, "Yellow": 6, "Orange": 6, "Red": 4},
        "predictions": [
            {
                "location": "Tondiarpet",
                "zone": "Red",
                "floodProbability": 0.82,
                "waterLevelCm": 118,
                "sos": True,
            },
            {
                "location": "Washermanpet",
                "zone": "Orange",
                "floodProbability": 0.58,
                "waterLevelCm": 72,
                "sos": False,
            },
            {
                "location": "Royapuram",
                "zone": "Yellow",
                "floodProbability": 0.41,
                "waterLevelCm": 48,
                "sos": False,
            },
            {
                "location": "Egmore",
                "zone": "Orange",
                "floodProbability": 0.55,
                "waterLevelCm": 68,
                "sos": False,
            },
            {
                "location": "Central",
                "zone": "Red",
                "floodProbability": 0.79,
                "waterLevelCm": 105,
                "sos": True,
            },
            {
                "location": "Triplicane",
                "zone": "Yellow",
                "floodProbability": 0.38,
                "waterLevelCm": 42,
                "sos": False,
            },
            {
                "location": "T Nagar",
                "zone": "Red",
                "floodProbability": 0.85,
                "waterLevelCm": 124,
                "sos": True,
            },
            {
                "location": "Kodambakkam",
                "zone": "Orange",
                "floodProbability": 0.52,
                "waterLevelCm": 65,
                "sos": False,
            },
            {
                "location": "Ashok Nagar",
                "zone": "Yellow",
                "floodProbability": 0.35,
                "waterLevelCm": 38,
                "sos": False,
            },
            {
                "location": "Guindy",
                "zone": "Orange",
                "floodProbability": 0.49,
                "waterLevelCm": 61,
                "sos": False,
            },
            {
                "location": "Saidapet",
                "zone": "Yellow",
                "floodProbability": 0.33,
                "waterLevelCm": 36,
                "sos": False,
            },
            {
                "location": "Velachery",
                "zone": "Red",
                "floodProbability": 0.77,
                "waterLevelCm": 98,
                "sos": True,
            },
            {
                "location": "Perungudi",
                "zone": "Orange",
                "floodProbability": 0.54,
                "waterLevelCm": 69,
                "sos": False,
            },
            {
                "location": "Thoraipakkam",
                "zone": "Yellow",
                "floodProbability": 0.36,
                "waterLevelCm": 40,
                "sos": False,
            },
            {
                "location": "Sholinganallur",
                "zone": "Green",
                "floodProbability": 0.18,
                "waterLevelCm": 22,
                "sos": False,
            },
            {
                "location": "Anna Nagar",
                "zone": "Green",
                "floodProbability": 0.15,
                "waterLevelCm": 18,
                "sos": False,
            },
            {
                "location": "Mogappair",
                "zone": "Green",
                "floodProbability": 0.12,
                "waterLevelCm": 15,
                "sos": False,
            },
            {
                "location": "Ambattur",
                "zone": "Yellow",
                "floodProbability": 0.31,
                "waterLevelCm": 34,
                "sos": False,
            },
            {
                "location": "Porur",
                "zone": "Orange",
                "floodProbability": 0.47,
                "waterLevelCm": 58,
                "sos": False,
            },
            {
                "location": "Poonamallee",
                "zone": "Green",
                "floodProbability": 0.14,
                "waterLevelCm": 16,
                "sos": False,
            },
        ],
    }


@app.get("/api/predictions")
def predictions():
    return jsonify(_demo_payload())


@app.get("/api/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
