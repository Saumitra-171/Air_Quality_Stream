# Demo guide (about 6 minutes)

## Before the day
- [ ] Real `city_day.csv` is in `data/` and `python check_data.py` runs cleanly.
- [ ] `python tune_model.py` has been run, so `tuning_results.png` and `tuning_results.csv` exist.
- [ ] `python train_model.py --contamination <best value from tuning>` has been run.
- [ ] One full dry run of the steps below, start to finish.
- [ ] Notifications off, browser zoom 110-125%, dashboard on its own window, processor terminal visible.
- [ ] Screen recording tested as a backup (Windows: Win+Alt+R in Xbox Game Bar, or OBS). Record one clean run anyway.

## Start-up (about 1 minute, before you present)

**Easy way:** `powershell -ExecutionPolicy Bypass -File .\demo.ps1 -KafkaDir C:\kafka`
It starts Kafka, resets the tables, opens the processor and the dashboard, and waits for you to press Enter before it starts the producer.

**Manual way (5 terminals):** Kafka, then `python init_db.py`, then `python processor.py`, then `streamlit run dashboard.py`. Keep the producer ready:
```
python producer.py --delay 0.15 --start 2019-01-01 --end 2019-12-31 --cities "<cities from check_data.py>"
```
Pick a window of about 2 to 4 minutes of events: events x delay = run time. Winter months (Oct to Jan) usually show the biggest pollution spikes, so check coverage with `check_data.py` and consider `--start 2019-10-01 --end 2020-01-31`.

## Script

| Time | Do | Say |
|------|----|-----|
| 0:00 | Show the dashboard waiting, then the architecture slide or the README layer table | "Six layers: a paced CSV source, Kafka, a Python processor, two ML models, PostgreSQL and a Streamlit dashboard. Everything starts empty." |
| 0:30 | Start the producer. Point at the processor terminal, then the KPI tiles | "Each line is one event passing through Kafka. The tiles update on their own because the dashboard re-queries every 2 seconds." |
| 1:15 | Pick a city, show the PM2.5 line and the smoother rolling average | "The processor keeps a 7-reading window per city in memory. The average lags behind spikes, and that lag is the window doing its job." |
| 2:00 | Wait for or point at a red dot | "This is IsolationForest, trained offline and used live. It flagged this reading because of the combination of pollutants, judged against this city's own normal, not a national average." |
| 2:45 | Show the orange forecast band, switch city | "Every few readings the processor refits an ARIMA model on the last 60 readings and writes a 7-day forecast with an 80% interval." |
| 3:30 | In a terminal: `New-Item PAUSE`. Wait 10 seconds. Then `Remove-Item PAUSE` | "The dashboard still refreshes, but the numbers freeze, because live depends on data moving and not on a refresh timer. Resume and the curve continues." |
| 4:15 | Show `tuning_results.png` | "I compared contamination levels using injected spikes as ground truth. Higher settings catch more real events but raise false alarms. I chose X because it had the best balance." |
| 5:15 | Return to the dashboard | "Kafka for transport, windowed state in the processor, a model trained offline and served live, a database as the serving layer, and a dashboard that only updates when new data arrives." |

## Likely questions

- **Why Kafka?** It decouples producer and processor, buffers events, and keeps events for one city in order by using the city as the message key.
- **Why train offline?** Training is slow and the stream needs microsecond scoring, so the model is loaded once and only scores.
- **Why per-city ratios?** A global model flags the most polluted cities all the time. Dividing by each city's median makes "anomalous" mean unusual for that city.
- **What does contamination do?** It sets the expected share of anomalies. Higher values catch more real events and also raise false alarms.
- **How good is the forecast?** ARIMA(2,1,1) on a short window is a simple baseline. It captures the recent level and trend, not seasonality or sudden events, which is why the interval is wide.
- **What if the processor restarts?** Its window, peaks and counts are in memory and reset. The database keeps the history. A production system would checkpoint state or rebuild it from Kafka.
- **Is the data truly real-time?** It is a replay of historical daily data, paced to behave like a live feed. The pipeline code is the same for a real feed.

## If something goes wrong
| Symptom | Fix |
|---------|-----|
| Producer: `NoBrokersAvailable` | Kafka isn't running or is still starting. Wait for "Kafka Server started". |
| Dashboard stuck on "Waiting for the first events" | Start the producer. Check the processor window for errors. |
| Processor: `password authentication failed` | `$env:PGPASSWORD="..."` in that window. |
| Dashboard numbers frozen | Producer finished or is paused: look for a `PAUSE` file. |
| Forecast missing | Needs about 20 readings per city. Wait a few seconds. |
| Anything else mid-demo | Switch to the screen recording and keep talking. |
