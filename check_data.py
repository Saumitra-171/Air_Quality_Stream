"""Sanity-check data/city_day.csv and suggest a good replay window for the demo."""
import sys
import pandas as pd
import config

path = sys.argv[1] if len(sys.argv) > 1 else config.DATA_PATH
df = pd.read_csv(path, parse_dates=["Date"])
need = ["City", "Date"] + list(config.FEATURES.values())
missing = [c for c in need if c not in df.columns]
if missing:
    raise SystemExit(f"Missing columns {missing}. Found: {list(df.columns)}\n"
                     "Fix the FEATURES mapping in config.py to match.")

ok = df.dropna(subset=["PM2.5"])
print(f"{path}: {len(df)} rows, {df['City'].nunique()} cities, "
      f"{df['Date'].min().date()} to {df['Date'].max().date()}")
print(f"Rows with PM2.5: {len(ok)} ({len(ok)/len(df):.0%})\n")
print("Share of values missing per pollutant:")
print((df[list(config.FEATURES.values())].isna().mean() * 100).round(1).to_string(), "\n")

year = ok[(ok["Date"] >= "2019-01-01") & (ok["Date"] <= "2019-12-31")]
cov = year.groupby("City").size().sort_values(ascending=False)
print("Days with PM2.5 in 2019, top cities:")
print(cov.head(10).to_string(), "\n")
top = ",".join(cov.head(6).index)
n = int(cov.head(6).sum())
print("Suggested demo replay (about 3-5 minutes at --delay 0.1):")
print(f'python producer.py --delay 0.1 --start 2019-01-01 --end 2019-12-31 --cities "{top}"')
print(f"(~{n} events, ~{n*0.1/60:.1f} min at 0.1 s per event)")
