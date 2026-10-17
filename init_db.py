"""Create (or reset) the tables. Run once, and again before each fresh demo."""
import psycopg2
import config

conn = psycopg2.connect(**config.DB)
with conn, conn.cursor() as cur:
    cur.execute(open("schema.sql").read())
conn.close()
print("Tables created / reset.")
