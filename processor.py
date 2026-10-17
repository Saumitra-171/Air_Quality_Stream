"""Layers 3 + 4 + 5: consume events, window per city, score with ML, forecast, write to PostgreSQL."""
import argparse, datetime as dt, json, time
from collections import defaultdict, deque
import joblib, numpy as np, psycopg2
from psycopg2.extras import execute_values
import config
from forecaster import forecast
from features import to_ratio


def aqi_category(pm25):
    """PM2.5 (ug/m3) bands, following India's CPCB AQI scheme."""
    for limit, name in [(30, "Good"), (60, "Satisfactory"), (90, "Moderate"),
                        (120, "Poor"), (250, "Very Poor")]:
        if pm25 <= limit:
            return name
    return "Severe"


class Processor:
    def __init__(self, cur):
        bundle = joblib.load(config.MODEL_PATH)     # train offline, serve live: load once
        self.model, self.keys, self.medians = bundle["model"], bundle["features"], bundle["medians"]
        self.city_medians = bundle["city_medians"]
        self.cur = cur
        # streaming state, kept in memory between events
        self.windows = defaultdict(lambda: deque(maxlen=config.WINDOW))
        self.history = defaultdict(lambda: deque(maxlen=config.FORECAST_HISTORY))
        self.peaks = defaultdict(float)
        self.counts = defaultdict(int)
        self.anomalies = defaultdict(int)

    def handle(self, e):
        city = e["city"]

        # --- windowing ---
        self.windows[city].append(e["pm25"])
        self.history[city].append(e["pm25"])
        rolling = sum(self.windows[city]) / len(self.windows[city])
        self.peaks[city] = max(self.peaks[city], e["pm25"])
        self.counts[city] += 1
        category = aqi_category(e["pm25"])

        # --- ML scoring: each pollutant as a ratio to this city's normal; gaps copy the PM2.5 ratio ---
        month = int(e["date"][5:7])
        base = self.city_medians.get(f"{city}|{month}") or self.city_medians.get(city) or self.medians
        vals = np.array([[e[k] if e.get(k) is not None else np.nan for k in self.keys]], dtype=float)
        x = to_ratio(vals, np.array([[base[k] for k in self.keys]]))
        is_anomaly = int(self.model.predict(x)[0] == -1)
        score = float(self.model.decision_function(x)[0])       # lower = more unusual
        self.anomalies[city] += is_anomaly

        # --- store ---

        # --- store ---
        c = self.cur
        c.execute(
            """INSERT INTO readings (city, reading_date, pm25, pm10, no2, co, so2, o3,
                                     rolling_avg_pm25, aqi_category, anomaly_score, is_anomaly)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (city, e["date"], e["pm25"], e.get("pm10"), e.get("no2"), e.get("co"),
             e.get("so2"), e.get("o3"), rolling, category, score, is_anomaly))
        c.execute(
            """INSERT INTO city_latest (city, reading_date, pm25, rolling_avg_pm25, peak_pm25,
                                        aqi_category, readings_count, anomaly_count, updated_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s, now())
               ON CONFLICT (city) DO UPDATE SET
                   reading_date = EXCLUDED.reading_date, pm25 = EXCLUDED.pm25,
                   rolling_avg_pm25 = EXCLUDED.rolling_avg_pm25, peak_pm25 = EXCLUDED.peak_pm25,
                   aqi_category = EXCLUDED.aqi_category, readings_count = EXCLUDED.readings_count,
                   anomaly_count = EXCLUDED.anomaly_count, updated_at = now()""",
            (city, e["date"], e["pm25"], rolling, self.peaks[city], category,
             self.counts[city], self.anomalies[city]))

        # --- ARIMA forecast (refit every few readings) ---
        if self.counts[city] % config.FORECAST_EVERY == 0:
            self.update_forecast(city, e["date"])
        return rolling, category, is_anomaly

    def update_forecast(self, city, last_date):
        result = forecast(list(self.history[city]), steps=config.FORECAST_STEPS)
        if result is None:
            return
        yhat, lower, upper = result
        d0 = dt.date.fromisoformat(last_date)
        rows = [(city, i + 1, d0 + dt.timedelta(days=i + 1), float(yhat[i]), float(lower[i]), float(upper[i]))
                for i in range(len(yhat))]
        execute_values(
            self.cur,
            """INSERT INTO forecasts (city, horizon, forecast_date, yhat, lower, upper) VALUES %s
               ON CONFLICT (city, horizon) DO UPDATE SET forecast_date = EXCLUDED.forecast_date,
                   yhat = EXCLUDED.yhat, lower = EXCLUDED.lower, upper = EXCLUDED.upper, updated_at = now()""",
            rows)


def main():
    from kafka import KafkaConsumer
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-beginning", action="store_true",
                    help="read the topic from the start (default: only new events)")
    args = ap.parse_args()

    conn = psycopg2.connect(**config.DB)
    conn.autocommit = True
    proc = Processor(conn.cursor())

    consumer = KafkaConsumer(
        config.TOPIC,
        bootstrap_servers=config.KAFKA_BOOTSTRAP,
        group_id=f"aq-processor-{int(time.time())}",
        auto_offset_reset="earliest" if args.from_beginning else "latest",
        value_deserializer=lambda b: json.loads(b.decode("utf-8")),
    )
    print("Processor ready, waiting for events...")
    for msg in consumer:
        e = msg.value
        rolling, category, is_anomaly = proc.handle(e)
        flag = "  <-- ANOMALY" if is_anomaly else ""
        print(f"{e['city']:<12} {e['date']}  pm2.5={e['pm25']:>7.1f}  avg={rolling:>7.1f}  {category}{flag}")


if __name__ == "__main__":
    main()
