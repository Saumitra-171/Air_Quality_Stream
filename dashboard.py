"""Layer 6: live Streamlit dashboard. Re-queries PostgreSQL every 2 seconds."""
import time
import altair as alt
import pandas as pd
import psycopg2
import streamlit as st
import config

st.set_page_config(page_title="Live Air Quality", layout="wide")
st.title("Live Air-Quality Monitor")


def query(sql, params=None):
    """Fresh connection per call, so the view is never a stale snapshot."""
    conn = psycopg2.connect(**config.DB)
    try:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            cols = [c[0] for c in cur.description]
            return pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        conn.close()


cities = query("SELECT city FROM city_latest ORDER BY city")["city"].tolist()
if not cities:
    st.info("Waiting for the first events... start the producer.")
    time.sleep(2)
    st.rerun()

city = st.sidebar.selectbox("City", cities)
history = st.sidebar.slider("Readings to show", 30, 300, 120)
show_fc = st.sidebar.checkbox("Show 7-day ARIMA forecast", value=True)
st.sidebar.caption("Auto-refreshes every 2 seconds")


@st.fragment(run_every=2)
def live_view(city, history, show_fc):
    latest = query("SELECT * FROM city_latest ORDER BY city")
    row = latest[latest["city"] == city].iloc[0]

    fc = query("SELECT forecast_date AS reading_date, yhat, lower, upper FROM forecasts "
               "WHERE city = %s ORDER BY horizon", (city,))
    fc["reading_date"] = pd.to_datetime(fc["reading_date"])

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Latest PM2.5", f"{row.pm25:.1f}")
    c2.metric("Rolling avg", f"{row.rolling_avg_pm25:.1f}")
    c3.metric("Peak", f"{row.peak_pm25:.1f}")
    c4.metric("Air quality", row.aqi_category)
    c5.metric("Anomalies", int(row.anomaly_count))
    c6.metric("Forecast avg (7d)", f"{fc['yhat'].mean():.1f}" if not fc.empty else "n/a")
    st.caption(f"{city}: {int(row.readings_count)} readings processed, latest date {row.reading_date}")

    df = query(
        "SELECT reading_date, pm25, rolling_avg_pm25, is_anomaly FROM readings "
        "WHERE city = %s ORDER BY id DESC LIMIT %s", (city, history))
    df = df.iloc[::-1]
    df["reading_date"] = pd.to_datetime(df["reading_date"])

    base = alt.Chart(df).encode(x=alt.X("reading_date:T", title="Date"))
    lines = (base.transform_fold(["pm25", "rolling_avg_pm25"], as_=["series", "value"])
             .mark_line().encode(y=alt.Y("value:Q", title="PM2.5 (µg/m³)"), color=alt.Color("series:N", title="")))
    dots = (base.transform_filter("datum.is_anomaly == 1")
            .mark_point(color="red", filled=True, size=90).encode(y="pm25:Q"))
    layers = lines + dots
    if show_fc and not fc.empty:
        fbase = alt.Chart(fc).encode(x="reading_date:T")
        band = fbase.mark_area(opacity=0.2, color="orange").encode(y="lower:Q", y2="upper:Q")
        fline = fbase.mark_line(color="orange", strokeDash=[6, 4]).encode(y="yhat:Q")
        layers = layers + band + fline
    st.altair_chart(layers.properties(height=340), width="stretch")
    st.caption("Red dots = readings flagged by the IsolationForest model. "
               "Orange dashed line and band = 7-day ARIMA forecast with 80% interval.")

    left, right = st.columns(2)
    with left:
        st.subheader("All cities: rolling average")
        st.bar_chart(latest.set_index("city")["rolling_avg_pm25"])
    with right:
        st.subheader("Latest anomalies (all cities)")
        recent = query(
            "SELECT city, reading_date, pm25, round(anomaly_score::numeric, 3) AS score "
            "FROM readings WHERE is_anomaly = 1 ORDER BY id DESC LIMIT 8")
        st.dataframe(recent, hide_index=True, width="stretch")


live_view(city, history, show_fc)
