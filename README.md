# Live Air-Quality Monitor (multi-city streaming pipeline)

CSV replay -> Kafka -> Python processor (per-city window) -> IsolationForest + ARIMA forecast -> PostgreSQL -> Streamlit

## 1. One-time setup
- `pip install -r requirements.txt`
- Java 17+, Kafka (KRaft mode: format storage once, see below), PostgreSQL with a database named `airquality`.
- Data: download **Air Quality Data in India (2015-2020)** from Kaggle (author Rohan Rao), extract `city_day.csv` into `data/`.
  Then run `python check_data.py`: it validates the columns and prints a suggested producer command.
  (No download? `python make_sample_data.py` makes a synthetic file with the same columns.)

Kafka 3.x on Windows, from the Kafka folder:
    bin\windows\kafka-storage.bat random-uuid
    bin\windows\kafka-storage.bat format -t <UUID> -c config\kraft\server.properties
    bin\windows\kafka-server-start.bat config\kraft\server.properties

## 2. Tune and train the model
    python tune_model.py                              # compares contamination levels, writes tuning_results.csv/.png
    python train_model.py --contamination 0.02        # use the best value from the tuning table

## 3. Run (one terminal each, or use demo.ps1)
1. Kafka
2. `python init_db.py`         (creates/resets all tables)
3. `python processor.py`
4. `streamlit run dashboard.py`
5. `python producer.py --delay 0.15 --start 2019-01-01 --end 2019-12-31 --cities "Delhi,Mumbai,Chennai"`

Producer options: `--delay`, `--limit`, `--start`, `--end`, `--cities`.
Pause/resume the stream during a demo: `New-Item PAUSE` / `Remove-Item PAUSE`.
See DEMO.md for the demo script, likely questions and troubleshooting.

## Layer map
| # | Layer | File |
|---|-------|------|
| 1 | Data source | data/city_day.csv, producer.py, check_data.py |
| 2 | Streaming tool | Kafka topic `air-quality-events`, keyed by city |
| 3 | Stream processor | processor.py (7-reading window per city, running peak, AQI category) |
| 4 | ML | train_model.py + features.py (IsolationForest on per-city ratios), forecaster.py (ARIMA), tune_model.py |
| 5 | Database | schema.sql: `readings`, `city_latest`, `forecasts` |
| 6 | Visualization | dashboard.py (auto-refresh every 2 s, anomaly dots, forecast band) |
