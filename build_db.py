import pandas as pd
import sqlite3

df = pd.read_csv("data/raw/calpers_raw.csv")

conn = sqlite3.connect("openlp.db")
df.to_sql("funds", conn, if_exists="replace", index=False)
conn.close()

print("Database created: openlp.db")

