"""Layer 4 (offline): train the anomaly detector once and save it.
Each pollutant is expressed as a ratio to its city's median, so 'anomalous' means unusual FOR THAT CITY."""
import argparse, joblib, pandas as pd
from sklearn.ensemble import IsolationForest
import config
from features import baselines, matrix

ap = argparse.ArgumentParser()
ap.add_argument("--contamination", type=float, default=config.CONTAMINATION,
                help="expected fraction of anomalies (see tune_model.py)")
args = ap.parse_args()

keys = list(config.FEATURES)
cols = [config.FEATURES[k] for k in keys]

df = pd.read_csv(config.DATA_PATH, usecols=["City", "Date"] + cols).dropna(subset=["PM2.5"])
med, glob = baselines(df, cols)
raw, base = matrix(df, cols, med, glob)
X = raw / base

model = IsolationForest(n_estimators=200, contamination=args.contamination, random_state=42)
model.fit(X)

to_keys = {config.FEATURES[k]: k for k in keys}
joblib.dump({
    "model": model, "features": keys, "contamination": args.contamination,
    "medians": {to_keys[c]: float(glob[c]) for c in cols},                       # fallback baseline
    "city_medians": {city: {to_keys[c]: float(row[c]) for c in cols} for city, row in med.iterrows()},
}, config.MODEL_PATH)

flag = model.predict(X) == -1
print(f"Trained on {len(X)} rows (contamination={args.contamination}), "
      f"flagged {flag.sum()} ({flag.mean():.1%}) as anomalies.")
print("Flagged share per city (should be roughly even):")
print(pd.Series(flag, index=df["City"].values).groupby(level=0).mean().mul(100).round(1).to_string())
print(f"Saved {config.MODEL_PATH}")
