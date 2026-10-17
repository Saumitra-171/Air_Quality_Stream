"""Shared settings for every layer of the pipeline."""
import os

# --- Layer 2: Kafka ---
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
TOPIC = "air-quality-events"
NUM_PARTITIONS = 3

# --- Layer 1: data ---
DATA_PATH = os.getenv("DATA_PATH", "data/city_day.csv")
# event field -> CSV column
FEATURES = {
    "pm25": "PM2.5",
    "pm10": "PM10",
    "no2": "NO2",
    "co": "CO",
    "so2": "SO2",
    "o3": "O3",
}

# --- Layer 3: processor ---
WINDOW = 7  # rolling window = last 7 readings per city

# --- Layer 4b: ARIMA forecast ---
FORECAST_STEPS = 7      # predict the next 7 days
FORECAST_HISTORY = 60   # fit on the last 60 readings per city
FORECAST_EVERY = 3      # refit a city's forecast every 3rd reading (keeps the processor fast)

# --- Layer 4: ML ---
MODEL_PATH = "anomaly_model.pkl"
CONTAMINATION = 0.02  # expected fraction of anomalies

# --- Layer 5: PostgreSQL ---
DB = dict(
    host=os.getenv("PGHOST", "localhost"),
    port=int(os.getenv("PGPORT", "5432")),
    dbname=os.getenv("PGDATABASE", "airquality"),
    user=os.getenv("PGUSER", "postgres"),
    password=os.getenv("PGPASSWORD", "postgres"),
)
