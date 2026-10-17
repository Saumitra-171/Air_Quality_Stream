"""Explain the anomaly flags: which pollutant drove each one, and why big PM2.5 days were not flagged.
Run after (or during) a stream:  python explain_anomalies.py
Every pollutant is shown as a ratio to its city's normal (1.0 = typical for that city)."""
import joblib, pandas as pd, psycopg2
import config

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)

b = joblib.load(config.MODEL_PATH)
keys, cm, glob = b["features"], b["city_medians"], b["medians"]

conn = psycopg2.connect(**config.DB)
cur = conn.cursor()
cur.execute("SELECT city, reading_date, " + ", ".join(keys) + ", anomaly_score, is_anomaly FROM readings")
df = pd.DataFrame(cur.fetchall(), columns=["city", "date"] + keys + ["score", "flag"])
conn.close()
if df.empty:
    raise SystemExit("No readings in the database yet. Run the stream first.")

bases = [cm.get(f"{c}|{d.month}") or cm.get(c) or glob for c, d in zip(df["city"], df["date"])]
ratio = pd.DataFrame({k: df[k].astype(float) / pd.Series([b[k] for b in bases]) for k in keys})
ratio = ratio.fillna(1.0).round(2)             # a gap counts as normal, same as in the processor
out = pd.concat([df[["city", "date", "pm25", "score", "flag"]].round(2), ratio.add_prefix("x_")], axis=1)
out["driver"] = ratio.idxmax(axis=1)
out["driver_x"] = ratio.max(axis=1)

print(f"{len(df)} readings, {int(df.flag.sum())} flagged\n")
print("What 'normal' is for each city (median values the ratios divide by):")
print(pd.DataFrame({c: v for c, v in cm.items() if "|" not in c}).T[keys].round(2).to_string(), "\n")

fl = out[out.flag == 1]
if not fl.empty:
    print("Flagged readings: which pollutant had the biggest ratio (the driver)")
    print(fl.groupby(["city", "driver"]).size().rename("flags").to_string(), "\n")
    print("Most unusual flagged readings:")
    print(fl.sort_values("score").head(10).drop(columns="flag").to_string(index=False), "\n")

print("Highest PM2.5 days that were NOT flagged:")
print(out[out.flag == 0].sort_values("pm25", ascending=False).head(8).drop(columns="flag").to_string(index=False))
