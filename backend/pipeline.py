"""
backend/pipeline.py
Fetches One Call API 3.0, engineers features, returns a flat dict
ready to feed into the ML model.
"""

import requests
import numpy as np
from collections import deque
from datetime import datetime, timezone

OWM_URL = "https://api.openweathermap.org/data/3.0/onecall"

# One rolling window per node (stays in memory while server is running)
_windows = {}

def _get_window(node_id):
    if node_id not in _windows:
        _windows[node_id] = {"rain": deque(maxlen=24), "wl": deque(maxlen=24)}
    return _windows[node_id]


def fetch_weather(lat, lon, api_key):
    """Calls OWM One Call 3.0, returns raw JSON or None on failure."""
    try:
        r = requests.get(OWM_URL, params={
            "lat": lat, "lon": lon,
            "appid": api_key,
            "units": "metric",
            "exclude": "minutely,alerts"
        }, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.HTTPError as e:
        print(f"[OWM] HTTP {r.status_code}: {e}")
    except Exception as e:
        print(f"[OWM] Error: {e}")
    return None


def build_features(raw, node_id):
    """
    Extracts all OWM fields and engineers derived features.
    Returns a flat dict of 20 features.
    """
    cur     = raw.get("current", {})
    hourly  = raw.get("hourly", [])
    daily   = raw.get("daily", [{}])

    # ── Direct API fields ─────────────────────────────────────────────────────
    rain_1h     = cur.get("rain", {}).get("1h", 0.0)
    cloud_pct   = cur.get("clouds", 0)
    humidity    = cur.get("humidity", 70)
    pressure    = cur.get("pressure", 1010)
    temp_c      = cur.get("temp", 28.0)
    dew_point   = cur.get("dew_point", 22.0)
    wind_speed  = cur.get("wind_speed", 0.0)
    wind_gust   = cur.get("wind_gust", daily[0].get("wind_gust", 0.0))
    visibility  = cur.get("visibility", 10000)
    uvi         = cur.get("uvi", daily[0].get("uvi", 0.0))

    # Probability of precip — next 6 hours max
    prob_precip = max((h.get("pop", 0) for h in hourly[:6]), default=0.0)
    # Rainfall sum over next 6 hours
    rain_next6h = sum(h.get("rain", {}).get("1h", 0) for h in hourly[:6])

    # ── Temporal ──────────────────────────────────────────────────────────────
    dt       = cur.get("dt", 0)
    dt_obj   = datetime.fromtimestamp(dt, tz=timezone.utc)
    month    = dt_obj.month
    hour     = dt_obj.hour
    monsoon  = int(month in [6, 7, 8, 9, 10, 11])
    is_night = int(dt < cur.get("sunrise", 0) or dt > cur.get("sunset", 86400))

    # Weather severity from OWM condition code
    wid = cur.get("weather", [{}])[0].get("id", 800)
    if   200 <= wid <= 232: sev = 4   # thunderstorm
    elif 500 <= wid <= 531: sev = 3   # rain
    elif 300 <= wid <= 321: sev = 2   # drizzle
    elif wid >= 900:        sev = 4   # extreme
    else:                   sev = 0

    # ── Rolling / derived ─────────────────────────────────────────────────────
    win = _get_window(node_id)

    # Water level proxy: cumulative rain with 15% hourly drainage
    prev_wl = win["wl"][-1] if win["wl"] else 0.0
    wl      = float(np.clip(prev_wl * 0.85 + rain_1h * 0.85, 0, 300))

    win["rain"].append(rain_1h)
    win["wl"].append(wl)

    rain_6h  = sum(list(win["rain"])[-6:])
    rain_24h = sum(list(win["rain"]))
    wl_list  = list(win["wl"])
    wl_roc   = wl_list[-1] - wl_list[-2] if len(wl_list) >= 2 else 0.0
    wl_mean  = float(np.mean(wl_list[-6:])) if wl_list else 0.0
    wl_max   = float(np.max(wl_list[-6:]))  if wl_list else 0.0

    soil_moisture  = float(np.clip(30 + rain_24h * 1.8 + (humidity - 60) * 0.4, 0, 100))
    upstream_flow  = float(np.clip(wl * 0.78 + rain_6h * 1.5, 0, 500))
    rain_intensity = round(rain_1h * cloud_pct / 100.0, 3)

    return {
        # Direct
        "temp_c":               round(temp_c, 2),
        "humidity_pct":         humidity,
        "pressure_hpa":         pressure,
        "dew_point_c":          round(dew_point, 2),
        "cloud_cover_pct":      cloud_pct,
        "visibility_m":         visibility,
        "wind_speed_ms":        round(wind_speed, 2),
        "wind_gust_ms":         round(wind_gust, 2),
        "uvi":                  round(uvi, 1),
        "rain_1h_mm":           round(rain_1h, 2),
        "prob_precip":          round(prob_precip, 2),
        "rain_next6h_mm":       round(rain_next6h, 2),
        "weather_severity":     sev,
        # Derived
        "rainfall_mm":          round(rain_1h, 2),
        "rain_6h_roll":         round(rain_6h, 2),
        "rain_24h_roll":        round(rain_24h, 2),
        "rain_intensity_score": rain_intensity,
        "water_level_cm":       round(wl, 2),
        "wl_rate_of_change":    round(wl_roc, 3),
        "wl_roll_mean_6h":      round(wl_mean, 2),
        "wl_roll_max_6h":       round(wl_max, 2),
        "soil_moisture_pct":    round(soil_moisture, 2),
        "upstream_flow_cms":    round(upstream_flow, 2),
        # Temporal
        "monsoon_season":       monsoon,
        "hour_of_day":          hour,
        "is_night":             is_night,
        # Pass-through for dashboard display
        "_weather_desc":        cur.get("weather", [{}])[0].get("description", ""),
        "_timestamp":           dt_obj.isoformat(),
    }