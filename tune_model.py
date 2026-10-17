"""Stand-out feature #2: compare IsolationForest contamination levels.

The dataset has no anomaly labels, so we create them: hold out 25% of the rows and inject
known spikes (2.5-5x on 1-3 pollutants) into 3% of them. Then for each contamination level
we measure how many injected spikes the model catches (recall) and how many of its alarms
are real (precision). Output: tuning_results.csv and tuning_results.png.
"""
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
import config
from features import baselines, matrix

GRID = [0.005, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10]
INJECT_RATE = 0.03

cols = [config.FEATURES[k] for k in config.FEATURES]
df = pd.read_csv(config.DATA_PATH, usecols=["City", "Date"] + cols).dropna(subset=["PM2.5"])
med, glob = baselines(df, cols)
RAW, BASE = matrix(df, cols, med, glob)

rng = np.random.default_rng(0)
order = rng.permutation(len(RAW))
n_test = len(RAW) // 4
te, tr = order[:n_test], order[n_test:]
Xte_raw, Bte = RAW[te].copy(), BASE[te]
Xtr = RAW[tr] / BASE[tr]
Xte = Xte_raw      # spikes are injected into raw values, then converted to ratios below

y = np.zeros(len(Xte_raw), dtype=int)
for i in rng.choice(len(Xte_raw), size=int(INJECT_RATE * len(Xte_raw)), replace=False):
    feats = rng.choice(len(cols), size=rng.integers(1, 4), replace=False)
    Xte_raw[i, feats] *= rng.uniform(2.5, 5.0, size=len(feats))
    y[i] = 1
Xte = Xte_raw / Bte
print(f"Train rows: {len(Xtr)} | test rows: {len(Xte)} | injected anomalies: {y.sum()}\n")

rows = []
for c in GRID:
    pred = IsolationForest(n_estimators=200, contamination=c, random_state=42).fit(Xtr).predict(Xte) == -1
    tp = int((pred & (y == 1)).sum())
    fp = int((pred & (y == 0)).sum())
    fn = int((~pred & (y == 1)).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    rows.append(dict(contamination=c, flagged=int(pred.sum()), caught=tp, missed=fn,
                     false_alarms=fp, precision=round(precision, 3), recall=round(recall, 3), f1=round(f1, 3)))

res = pd.DataFrame(rows)
print(res.to_string(index=False))
res.to_csv("tuning_results.csv", index=False)

best = res.loc[res["f1"].idxmax()]
print(f"\nBest F1 = {best.f1} at contamination = {best.contamination}")
print(f"Use it with:  python train_model.py --contamination {best.contamination}")

fig, ax = plt.subplots(figsize=(7, 4))
for m in ("precision", "recall", "f1"):
    ax.plot(res["contamination"], res[m], marker="o", label=m)
ax.axvline(INJECT_RATE, color="grey", ls=":", label="true injected rate")
ax.set_xlabel("contamination setting")
ax.set_ylabel("score")
ax.set_title("Anomaly detector: catching real spikes vs false alarms")
ax.legend()
fig.tight_layout()
fig.savefig("tuning_results.png", dpi=150)
print("Saved tuning_results.csv and tuning_results.png")
