DROP TABLE IF EXISTS readings;
DROP TABLE IF EXISTS city_latest;
DROP TABLE IF EXISTS forecasts;

-- every processed event: feeds the live curve
CREATE TABLE readings (
    id               BIGSERIAL PRIMARY KEY,
    city             TEXT NOT NULL,
    reading_date     DATE NOT NULL,
    pm25             DOUBLE PRECISION,
    pm10             DOUBLE PRECISION,
    no2              DOUBLE PRECISION,
    co               DOUBLE PRECISION,
    so2              DOUBLE PRECISION,
    o3               DOUBLE PRECISION,
    rolling_avg_pm25 DOUBLE PRECISION,
    aqi_category     TEXT,
    anomaly_score    DOUBLE PRECISION,
    is_anomaly       SMALLINT DEFAULT 0,
    processed_at     TIMESTAMP DEFAULT now()
);
CREATE INDEX idx_readings_city_id ON readings (city, id);

-- one row per city, updated on every event: feeds the KPI tiles
CREATE TABLE city_latest (
    city             TEXT PRIMARY KEY,
    reading_date     DATE,
    pm25             DOUBLE PRECISION,
    rolling_avg_pm25 DOUBLE PRECISION,
    peak_pm25        DOUBLE PRECISION,
    aqi_category     TEXT,
    readings_count   INTEGER,
    anomaly_count    INTEGER,
    updated_at       TIMESTAMP DEFAULT now()
);

-- latest ARIMA forecast per city (replaced every refit): feeds the dashed forecast line
CREATE TABLE forecasts (
    city          TEXT NOT NULL,
    horizon       SMALLINT NOT NULL,          -- 1 = next day ... 7 = a week ahead
    forecast_date DATE,
    yhat          DOUBLE PRECISION,
    lower         DOUBLE PRECISION,           -- 80% interval
    upper         DOUBLE PRECISION,
    updated_at    TIMESTAMP DEFAULT now(),
    PRIMARY KEY (city, horizon)
);
