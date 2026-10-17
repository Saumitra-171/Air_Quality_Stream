"""Optional: generate a synthetic dataset with the same columns as the Kaggle
'Air Quality Data in India' city_day.csv, so you can test before downloading."""
import numpy as np, pandas as pd

rng = np.random.default_rng(42)
cities = {"Delhi": 140, "Mumbai": 70, "Bengaluru": 45, "Chennai": 55, "Kolkata": 95, "Hyderabad": 60}
dates = pd.date_range("2019-01-01", periods=730)
rows = []
for city, base in cities.items():
    season = 1 + 0.45 * np.cos((np.asarray(dates.dayofyear) - 20) / 365 * 2 * np.pi)   # winter peak
    pm25 = np.clip(base * season + rng.normal(0, base * 0.15, len(dates)), 5, None)
    spikes = rng.random(len(dates)) < 0.015
    pm25[spikes] *= rng.uniform(2.2, 3.5, spikes.sum())
    df = pd.DataFrame({
        "City": city, "Date": dates, "PM2.5": pm25.round(2),
        "PM10": (pm25 * rng.uniform(1.5, 2.2, len(dates))).round(2),
        "NO2": (pm25 * rng.uniform(0.2, 0.5, len(dates))).round(2),
        "CO": rng.uniform(0.3, 2.0, len(dates)).round(2),
        "SO2": rng.uniform(4, 25, len(dates)).round(2),
        "O3": rng.uniform(15, 70, len(dates)).round(2),
    })
    df.loc[spikes, ["CO", "NO2"]] *= 2.5
    df.loc[rng.random(len(df)) < 0.04, "CO"] = np.nan      # realistic gaps
    rows.append(df)
pd.concat(rows).to_csv("data/city_day.csv", index=False)
print("Wrote data/city_day.csv")
