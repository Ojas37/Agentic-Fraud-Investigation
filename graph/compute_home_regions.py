"""
Compute and persist Customer home_region from transactions.csv into TigerGraph FraudGraph
"""

import os
import pandas as pd
from collections import Counter
from dotenv import load_dotenv
import pyTigerGraph as tg

load_dotenv()

HOST = os.getenv("TG_HOST")
GRAPH_NAME = os.getenv("TG_GRAPH_NAME", "FraudGraph")
SECRET = os.getenv("TG_SECRET")

def compute_and_upsert_home_regions():
    print("Connecting to TigerGraph...")
    conn = tg.TigerGraphConnection(
        host=HOST,
        graphname=GRAPH_NAME,
        username=os.getenv("TG_USERNAME", "tigergraph"),
        password=os.getenv("TG_PASSWORD", "tigergraph"),
        gsqlSecret=SECRET
    )
    token = conn.getToken(SECRET)
    conn.apiToken = token[0] if isinstance(token, tuple) else token

    print("Reading transactions.csv to compute top BillingRegion (addr1) per customer...")
    cust_regions = {} # customer_id -> Counter(addr1 -> count)

    for chunk in pd.read_csv("data/raw/transactions.csv", usecols=["customer_id", "addr1"], chunksize=100000):
        chunk = chunk.dropna(subset=["customer_id", "addr1"])
        for _, row in chunk.iterrows():
            cid = str(row["customer_id"])
            addr = str(row["addr1"]).replace(".0", "").strip()
            if addr and addr != "nan":
                if cid not in cust_regions:
                    cust_regions[cid] = Counter()
                cust_regions[cid][addr] += 1

    print(f"Computed region frequencies for {len(cust_regions)} customers.")
    
    # Select most frequent region per customer
    cust_vertices = []
    for cid, counts in cust_regions.items():
        top_region = counts.most_common(1)[0][0]
        cust_vertices.append((cid, {"home_region": top_region}))

    print(f"Upserting home_region for {len(cust_vertices)} customers to FraudGraph...")
    for i in range(0, len(cust_vertices), 1000):
        conn.upsertVertices("Customer", cust_vertices[i:i+1000])

    print("[SUCCESS] Customer home_region populated successfully!")

if __name__ == "__main__":
    compute_and_upsert_home_regions()
