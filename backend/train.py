"""
backend/train.py
Run ONCE to produce model.pkl and scaler.pkl.

  cd backend
  python train.py

Feature order must stay in sync with FEATURES list in app.py.
"""

import os

import joblib
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import classification_report
from sklearn.preprocessing import StandardScaler

# ── Must match FEATURES in app.py exactly ────────────────────────────────────
FEATURES = [
    "temp_c",
    "humidity_pct",
    "pressure_hpa",
    "dew_point_c",
    "cloud_cover_pct",
    "visibility_m",
    "wind_speed_ms",
    "wind_gust_ms",
    "uvi",
    "rain_1h_mm",
    "prob_precip",
    "rain_next6h_mm",
    "weather_severity",
    "rainfall_mm",
    "rain_6h_roll",
    "rain_24h_roll",
    "rain_intensity_score",
    "water_level_cm",
    "wl_rate_of_change",
    "wl_roll_mean_6h",
    "wl_roll_max_6h",
    "soil_moisture_pct",
    "upstream_flow_cms",
    "monsoon_season",
    "hour_of_day",
    "is_night",
]


def generate_data(n=8000, seed=42):
    np.random.seed(seed)
    hours = pd.date_range("2015-01-01", periods=n, freq="h")
    months = hours.month.values
    monsoon = np.isin(months, [6, 7, 8, 9, 10, 11]).astype(int)
    hour_of_day = hours.hour.values
    doy = hours.dayofyear.values

    rain_1h = np.clip(np.random.exponential(1.5, n) * (1 + 3.5 * monsoon), 0, 80)
    clouds = np.clip(20 + rain_1h * 4 + np.random.normal(0, 10, n), 0, 100)
    temp_c = 28 + 4 * np.sin((doy - 60) * 2 * np.pi / 365) + np.random.normal(0, 1, n)
    humidity = np.clip(55 + rain_1h * 2 + monsoon * 10 + np.random.normal(0, 5, n), 30, 100)
    dew_point = temp_c - ((100 - humidity) / 5.0)
    pressure = np.clip(1013 - rain_1h * 0.3 + np.random.normal(0, 3, n), 980, 1030)
    wind_speed = np.clip(np.random.exponential(3, n) + rain_1h * 0.1, 0, 25)
    wind_gust = wind_speed * np.random.uniform(1.1, 2.2, n)
    uvi = np.clip(10 * (1 - clouds / 100) + np.random.normal(0, 0.5, n), 0, 12)
    visibility = np.clip(10000 - rain_1h * 150 + np.random.normal(0, 500, n), 200, 10000)

    rs = pd.Series(rain_1h)
    rain_6h = rs.rolling(6, min_periods=1).sum().values
    rain_24h = rs.rolling(24, min_periods=1).sum().values
    rain_next6h = rs.shift(-6).rolling(6, min_periods=1).sum().fillna(0).values
    prob_precip = np.clip(clouds / 100 * 0.8 + rain_1h / 50, 0, 1)

    drain = 0.15
    wl = np.zeros(n)
    for i in range(1, n):
        wl[i] = np.clip(wl[i - 1] * (1 - drain) + rain_1h[i] * 0.85, 0, 300)
    ws = pd.Series(wl)
    wl_mean = ws.rolling(6, min_periods=1).mean().values
    wl_max = ws.rolling(6, min_periods=1).max().values
    wl_roc = np.gradient(wl)

    rain_intensity = rain_1h * clouds / 100.0
    soil_moisture = np.clip(30 + rain_24h * 1.8 + (humidity - 60) * 0.4, 0, 100)
    upstream_flow = np.clip(wl * 0.78 + rain_6h * 1.5, 0, 500)
    is_night = ((hour_of_day < 6) | (hour_of_day > 18)).astype(int)

    def sev(r, g):
        if g > 20 or r > 30:
            return 4
        if r > 15:
            return 3
        if r > 5:
            return 2
        return 0

    weather_severity = np.array([sev(r, g) for r, g in zip(rain_1h, wind_gust)])

    def label(wl_v, r, s):
        if wl_v > 220 or (wl_v > 160 and r > 20) or s == 4:
            return 3
        if wl_v > 150 or (wl_v > 100 and r > 15) or s == 3:
            return 2
        if wl_v > 80 or r > 8:
            return 1
        return 0

    labels = np.array([label(wl[i], rain_1h[i], weather_severity[i]) for i in range(n)])

    # Inject known Chennai flood events
    for start, end, lv in [("2015-11-01", "2015-12-15", 3), ("2021-11-05", "2021-11-20", 2)]:
        mask = (hours >= start) & (hours <= end)
        labels[mask] = lv
        rain_1h[mask] = np.maximum(rain_1h[mask], 25)

    return pd.DataFrame(
        {
            "temp_c": temp_c,
            "humidity_pct": humidity,
            "pressure_hpa": pressure,
            "dew_point_c": dew_point,
            "cloud_cover_pct": clouds,
            "visibility_m": visibility,
            "wind_speed_ms": wind_speed,
            "wind_gust_ms": wind_gust,
            "uvi": uvi,
            "rain_1h_mm": rain_1h,
            "prob_precip": prob_precip,
            "rain_next6h_mm": rain_next6h,
            "weather_severity": weather_severity.astype(float),
            "rainfall_mm": rain_1h,
            "rain_6h_roll": rain_6h,
            "rain_24h_roll": rain_24h,
            "rain_intensity_score": rain_intensity,
            "water_level_cm": wl,
            "wl_rate_of_change": wl_roc,
            "wl_roll_mean_6h": wl_mean,
            "wl_roll_max_6h": wl_max,
            "soil_moisture_pct": soil_moisture,
            "upstream_flow_cms": upstream_flow,
            "monsoon_season": monsoon,
            "hour_of_day": hour_of_day,
            "is_night": is_night,
            "label": labels,
        }
    )


if __name__ == "__main__":
    print("Training FloodSense model...")

    # Use real data if available, else synthetic
    if os.path.exists("flood_training_data.csv"):
        print("  Using real data: flood_training_data.csv")
        df = pd.read_csv("flood_training_data.csv")
        for col in FEATURES:
            if col not in df.columns:
                df[col] = 0.0
    else:
        print("  No real data found — generating synthetic data (8000 samples)")
        df = generate_data()

    X = df[FEATURES].values
    y = df["label"].values

    split = int(0.8 * len(X))
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_tr, X_te = X_scaled[:split], X_scaled[split:]
    y_tr, y_te = y[:split], y[split:]

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_tr, y_tr)

    print(
        classification_report(
            y_te, model.predict(X_te), target_names=["SAFE", "WATCH", "WARNING", "DANGER"]
        )
    )

    joblib.dump(model, "model.pkl")
    joblib.dump(scaler, "scaler.pkl")
    print("Saved: model.pkl  scaler.pkl")
"""
backend/train.py
Run ONCE to produce model.pkl and scaler.pkl.

  cd backend
  python train.py

Feature order must stay in sync with FEATURES list in app.py.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
import xgboost as xgb
import joblib, os

# ── Must match FEATURES in app.py exactly ────────────────────────────────────
FEATURES = [
    "temp_c", "humidity_pct", "pressure_hpa", "dew_point_c",
    "cloud_cover_pct", "visibility_m", "wind_speed_ms", "wind_gust_ms",
    "uvi", "rain_1h_mm", "prob_precip", "rain_next6h_mm", "weather_severity",
    "rainfall_mm", "rain_6h_roll", "rain_24h_roll", "rain_intensity_score",
    "water_level_cm", "wl_rate_of_change", "wl_roll_mean_6h", "wl_roll_max_6h",
    "soil_moisture_pct", "upstream_flow_cms",
    "monsoon_season", "hour_of_day", "is_night",
]


def generate_data(n=8000, seed=42):
    np.random.seed(seed)
    hours   = pd.date_range("2015-01-01", periods=n, freq="h")
    months  = hours.month.values
    monsoon = np.isin(months, [6,7,8,9,10,11]).astype(int)
    hour_of_day = hours.hour.values
    doy     = hours.dayofyear.values

    rain_1h     = np.clip(np.random.exponential(1.5, n) * (1 + 3.5*monsoon), 0, 80)
    clouds      = np.clip(20 + rain_1h*4 + np.random.normal(0,10,n), 0, 100)
    temp_c      = 28 + 4*np.sin((doy-60)*2*np.pi/365) + np.random.normal(0,1,n)
    humidity    = np.clip(55 + rain_1h*2 + monsoon*10 + np.random.normal(0,5,n), 30, 100)
    dew_point   = temp_c - ((100 - humidity) / 5.0)
    pressure    = np.clip(1013 - rain_1h*0.3 + np.random.normal(0,3,n), 980, 1030)
    wind_speed  = np.clip(np.random.exponential(3,n) + rain_1h*0.1, 0, 25)
    wind_gust   = wind_speed * np.random.uniform(1.1, 2.2, n)
    uvi         = np.clip(10*(1-clouds/100) + np.random.normal(0,.5,n), 0, 12)
    visibility  = np.clip(10000 - rain_1h*150 + np.random.normal(0,500,n), 200, 10000)

    rs          = pd.Series(rain_1h)
    rain_6h     = rs.rolling(6,  min_periods=1).sum().values
    rain_24h    = rs.rolling(24, min_periods=1).sum().values
    rain_next6h = rs.shift(-6).rolling(6, min_periods=1).sum().fillna(0).values
    prob_precip = np.clip(clouds/100*0.8 + rain_1h/50, 0, 1)

    drain = 0.15
    wl = np.zeros(n)
    for i in range(1, n):
        wl[i] = np.clip(wl[i-1]*(1-drain) + rain_1h[i]*0.85, 0, 300)
    ws          = pd.Series(wl)
    wl_mean     = ws.rolling(6, min_periods=1).mean().values
    wl_max      = ws.rolling(6, min_periods=1).max().values
    wl_roc      = np.gradient(wl)

    rain_intensity = rain_1h * clouds / 100.0
    soil_moisture  = np.clip(30 + rain_24h*1.8 + (humidity-60)*0.4, 0, 100)
    upstream_flow  = np.clip(wl*0.78 + rain_6h*1.5, 0, 500)
    is_night       = ((hour_of_day < 6) | (hour_of_day > 18)).astype(int)

    def sev(r, g):
        if g > 20 or r > 30: return 4
        if r > 15: return 3
        if r > 5:  return 2
        return 0
    weather_severity = np.array([sev(r, g) for r, g in zip(rain_1h, wind_gust)])

    def label(wl_v, r, s):
        if wl_v > 220 or (wl_v > 160 and r > 20) or s == 4: return 3
        if wl_v > 150 or (wl_v > 100 and r > 15) or s == 3: return 2
        if wl_v > 80  or r > 8:                              return 1
        return 0
    labels = np.array([label(wl[i], rain_1h[i], weather_severity[i]) for i in range(n)])

    # Inject known Chennai flood events
    for start, end, lv in [("2015-11-01","2015-12-15",3),("2021-11-05","2021-11-20",2)]:
        mask = (hours >= start) & (hours <= end)
        labels[mask] = lv
        rain_1h[mask] = np.maximum(rain_1h[mask], 25)

    return pd.DataFrame({
        "temp_c": temp_c, "humidity_pct": humidity, "pressure_hpa": pressure,
        "dew_point_c": dew_point, "cloud_cover_pct": clouds,
        "visibility_m": visibility, "wind_speed_ms": wind_speed,
        "wind_gust_ms": wind_gust, "uvi": uvi, "rain_1h_mm": rain_1h,
        "prob_precip": prob_precip, "rain_next6h_mm": rain_next6h,
        "weather_severity": weather_severity.astype(float),
        "rainfall_mm": rain_1h, "rain_6h_roll": rain_6h,
        "rain_24h_roll": rain_24h, "rain_intensity_score": rain_intensity,
        "water_level_cm": wl, "wl_rate_of_change": wl_roc,
        "wl_roll_mean_6h": wl_mean, "wl_roll_max_6h": wl_max,
        "soil_moisture_pct": soil_moisture, "upstream_flow_cms": upstream_flow,
        "monsoon_season": monsoon, "hour_of_day": hour_of_day,
        "is_night": is_night, "label": labels,
    })


if __name__ == "__main__":
    print("Training FloodSense model...")

    # Use real data if available, else synthetic
    if os.path.exists("flood_training_data.csv"):
        print("  Using real data: flood_training_data.csv")
        df = pd.read_csv("flood_training_data.csv")
        for col in FEATURES:
            if col not in df.columns:
                df[col] = 0.0
    else:
        print("  No real data found — generating synthetic data (8000 samples)")
        df = generate_data()

    X = df[FEATURES].values
    y = df["label"].values

    split    = int(0.8 * len(X))
    scaler   = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    X_tr, X_te = X_scaled[:split], X_scaled[split:]
    y_tr, y_te = y[:split], y[split:]

    model = xgb.XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        eval_metric="mlogloss", random_state=42, n_jobs=-1,
    )
    model.fit(X_tr, y_tr)

    print(classification_report(y_te, model.predict(X_te),
          target_names=["SAFE","WATCH","WARNING","DANGER"]))

    joblib.dump(model,  "model.pkl")
    joblib.dump(scaler, "scaler.pkl")
    print("Saved: model.pkl  scaler.pkl")