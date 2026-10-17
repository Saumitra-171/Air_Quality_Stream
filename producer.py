"""Layers 1 + 2: replay the CSV as a live stream into Kafka (keyed by city)."""
import argparse, json, math, os, time
import pandas as pd
from kafka import KafkaProducer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import config

ap = argparse.ArgumentParser()
ap.add_argument("--delay", type=float, default=0.3, help="seconds between events")
ap.add_argument("--limit", type=int, default=0, help="stop after N events (0 = all)")
ap.add_argument("--start", help="first date to replay, e.g. 2019-01-01")
ap.add_argument("--end", help="last date to replay, e.g. 2019-12-31")
ap.add_argument("--cities", help="comma-separated cities to replay, e.g. Delhi,Mumbai,Chennai")
args = ap.parse_args()

# create the topic if needed
admin = KafkaAdminClient(bootstrap_servers=config.KAFKA_BOOTSTRAP)
try:
    admin.create_topics([NewTopic(config.TOPIC, num_partitions=config.NUM_PARTITIONS, replication_factor=1)])
    print(f"Created topic {config.TOPIC}")
except TopicAlreadyExistsError:
    pass
admin.close()


def num(v):
    """NaN / blank -> None so bad values never crash the stream."""
    return None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


df = pd.read_csv(config.DATA_PATH, parse_dates=["Date"])
df = df.dropna(subset=["PM2.5"])
if args.cities:
    df = df[df["City"].isin([c.strip() for c in args.cities.split(",")])]
if args.start:
    df = df[df["Date"] >= args.start]
if args.end:
    df = df[df["Date"] <= args.end]
df = df.sort_values(["Date", "City"])          # one "day" at a time, all cities
if df.empty:
    raise SystemExit("No rows left after filtering. Check --cities / --start / --end.")
print(f"Replaying {len(df)} events for {df['City'].nunique()} cities "
      f"({df['Date'].min().date()} to {df['Date'].max().date()})")

producer = KafkaProducer(
    bootstrap_servers=config.KAFKA_BOOTSTRAP,
    key_serializer=lambda k: k.encode("utf-8"),
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

sent, paused_msg = 0, False
for row in df.to_dict("records"):
    while os.path.exists("PAUSE"):             # demo trick: create a file named PAUSE to freeze the stream
        if not paused_msg:
            print("PAUSED (delete the PAUSE file to resume)")
            paused_msg = True
        time.sleep(0.5)
    if paused_msg:
        print("Resumed")
        paused_msg = False

    event = {"city": row["City"], "date": row["Date"].strftime("%Y-%m-%d")}
    event.update({k: num(row.get(col)) for k, col in config.FEATURES.items()})
    producer.send(config.TOPIC, key=row["City"], value=event)   # same city -> same partition
    sent += 1
    if sent % 50 == 0:
        print(f"sent {sent} events (latest: {event['city']} {event['date']})")
    if args.limit and sent >= args.limit:
        break
    time.sleep(args.delay)

producer.flush()
print(f"Done. Sent {sent} events.")
