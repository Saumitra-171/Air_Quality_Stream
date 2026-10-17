"""Turn raw pollutant values into 'ratio to this city's normal for this month'."""
import numpy as np
import pandas as pd


def row_keys(df):
    """'Kolkata|1' = Kolkata in January."""
    return df["City"] + "|" + pd.to_datetime(df["Date"]).dt.month.astype(str)


def baselines(df, cols):
    """Median of every pollutant per city, and per city+month (seasonal), plus a global fallback."""
    glob = df[cols].median()
    glob = glob.where(glob > 0, 1.0)
    by_city = df.groupby("City")[cols].median().fillna(glob)
    by_month = df.groupby(row_keys(df))[cols].median()
    city_of = by_month.index.str.split("|").str[0]
    fallback = pd.DataFrame(by_city.reindex(city_of).values, index=by_month.index, columns=cols)
    by_month = by_month.fillna(fallback)           # a gap in one month falls back to the city's overall median
    med = pd.concat([by_city, by_month])
    med = med.where(med > 0, 1.0)
    return med, glob


def matrix(df, cols, med, glob):
    """Return (raw, base): raw values (gaps stay NaN) and the seasonal baseline for every row."""
    base = med.reindex(row_keys(df)).values.astype(float)
    base = np.where(np.isnan(base), glob.values, base)
    return df[cols].values.astype(float), base


def to_ratio(raw, base):
    """Ratio to the normal. A missing pollutant takes the PM2.5 ratio of the same day.
    Column 0 must be PM2.5, which is always present."""
    ratio = raw / base
    return np.where(np.isnan(ratio), ratio[:, [0]], ratio)