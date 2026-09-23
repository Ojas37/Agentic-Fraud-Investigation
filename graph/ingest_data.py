"""
Data Ingestion Pipeline for HHGOA Fraud Investigation Agent
Loads raw CSVs into TigerGraph FraudGraph:
  1. closed_cases_history.csv -> ClosedCase, Card, Customer, Case Edges
  2. identity.csv -> DeviceProfile, FROM_DEVICE mapping
  3. transactions.csv -> Customer, Card, Transaction, EmailDomain, BillingRegion, and Edges
  4. Post-load transaction chain builder (NEXT_TXN / PREV_TXN)
"""

import os
import hashlib
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
import pyTigerGraph as tg

load_dotenv()

HOST = os.getenv("TG_HOST")
USERNAME = os.getenv("TG_USERNAME", "tigergraph")
PASSWORD = os.getenv("TG_PASSWORD", "tigergraph")
GRAPH_NAME = os.getenv("TG_GRAPH_NAME", "FraudGraph")
SECRET = os.getenv("TG_SECRET")

def get_connection():
    print(f"Connecting to TigerGraph at {HOST}, graph: {GRAPH_NAME}...")
    conn = tg.TigerGraphConnection(
        host=HOST,
        graphname=GRAPH_NAME,
        username=USERNAME,
        password=PASSWORD,
        gsqlSecret=SECRET
    )
    if SECRET:
        try:
            conn.getToken(SECRET)
        except Exception as e:
            print(f"Note on token: {e}")
    return conn

def compute_device_profile_id(device_info, os_name, browser, screen):
    key = f"{str(device_info).strip()}|{str(os_name).strip()}|{str(browser).strip()}|{str(screen).strip()}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

def clean_val(val, default=None):
    if pd.isna(val) or val is None or str(val).lower() in ["nan", "none", "null", ""]:
        return default
    return val

def ingest_closed_cases(conn, csv_path="data/raw/closed_cases_history.csv", batch_size=500):
    print(f"\n=== Ingesting Closed Cases from {csv_path} ===")
    if not os.path.exists(csv_path):
        print(f"File {csv_path} not found!")
        return

    df = pd.read_csv(csv_path)
    print(f"Total closed cases to load: {len(df)}")

    closed_case_vertices = []
    case_on_card_edges = []
    case_involves_edges = []
    case_connected_edges = []

    for _, row in df.iterrows():
        case_id = str(row["case_id"])
        cust_id = str(row["customer_id"])
        card_id = str(row["card_id"])
        opened_at = str(row["opened_at"])
        closed_at = str(row["closed_at"])
        outcome = str(row["outcome"])
        pattern = str(clean_val(row["pattern"], ""))
        first_fraud_txn_id = str(clean_val(row["first_fraud_txn_id"], ""))
        txn_ids = str(clean_val(row["txn_ids"], ""))
        n_txns = int(row["n_txns"]) if not pd.isna(row["n_txns"]) else 0
        exposure_usd = float(row["exposure_usd"]) if not pd.isna(row["exposure_usd"]) else 0.0
        conn_cards = str(clean_val(row["connected_card_ids"], ""))
        actions = str(clean_val(row["actions_taken"], ""))
        report_filed = bool(row["report_filed"]) if not pd.isna(row["report_filed"]) else False
        analyst_notes = str(clean_val(row["analyst_notes"], ""))

        closed_case_vertices.append((
            case_id,
            {
                "customer_id": cust_id,
                "card_id": card_id,
                "opened_at": opened_at,
                "closed_at": closed_at,
                "outcome": outcome,
                "pattern": pattern,
                "first_fraud_txn_id": first_fraud_txn_id,
                "txn_ids": txn_ids,
                "n_txns": n_txns,
                "exposure_usd": exposure_usd,
                "connected_card_ids": conn_cards,
                "actions_taken": actions,
                "report_filed": report_filed,
                "analyst_notes": analyst_notes,
                "embedding_stored": False
            }
        ))

        # CASE_ON_CARD edge
        case_on_card_edges.append((case_id, card_id, {}))

        # CASE_INVOLVES edges
        if txn_ids:
            for tid in txn_ids.split("|"):
                tid = tid.strip()
                if tid:
                    case_involves_edges.append((case_id, tid, {}))

        # CASE_CONNECTED_TO edges
        if conn_cards:
            for cc in conn_cards.split("|"):
                cc = cc.strip()
                if cc and cc != card_id:
                    case_connected_edges.append((case_id, cc, {"relationship": "connected"}))

    # Batch upsert
    print(f"Upserting {len(closed_case_vertices)} ClosedCase vertices...")
    for i in range(0, len(closed_case_vertices), batch_size):
        conn.upsertVertices("ClosedCase", closed_case_vertices[i:i+batch_size])

    print(f"Upserting {len(case_on_card_edges)} CASE_ON_CARD edges...")
    for i in range(0, len(case_on_card_edges), batch_size):
        conn.upsertEdges("ClosedCase", "CASE_ON_CARD", "Card", case_on_card_edges[i:i+batch_size])

    print(f"Upserting {len(case_involves_edges)} CASE_INVOLVES edges...")
    for i in range(0, len(case_involves_edges), batch_size):
        conn.upsertEdges("ClosedCase", "CASE_INVOLVES", "Transaction", case_involves_edges[i:i+batch_size])

    if case_connected_edges:
        print(f"Upserting {len(case_connected_edges)} CASE_CONNECTED_TO edges...")
        for i in range(0, len(case_connected_edges), batch_size):
            conn.upsertEdges("ClosedCase", "CASE_CONNECTED_TO", "Card", case_connected_edges[i:i+batch_size])

    print("✅ Closed cases ingestion complete!")

def build_card_mapping(tx_csv_path="data/raw/transactions.csv"):
    """
    Scans transactions.csv to map unique (customer_id, card1..card6) -> {customer_id}-K{idx}
    """
    print("Building card mapping from transactions.csv...")
    cols = ["customer_id", "card1", "card2", "card3", "card4", "card5", "card6", "ts"]
    records = []
    
    for chunk in pd.read_csv(tx_csv_path, usecols=cols, chunksize=100000):
        records.append(chunk.dropna(subset=["customer_id"]))
        
    all_df = pd.concat(records, ignore_index=True)
    all_df["ts"] = pd.to_datetime(all_df["ts"])
    
    # Sort by ts to ensure K1, K2 reflects chronological order
    all_df = all_df.sort_values("ts")
    
    # Unique card combinations per customer
    unique_cards = all_df.drop_duplicates(subset=["customer_id", "card1", "card2", "card3", "card4", "card5", "card6"]).copy()
    unique_cards["card_seq"] = unique_cards.groupby("customer_id").cumcount() + 1
    unique_cards["card_id"] = unique_cards["customer_id"] + "-K" + unique_cards["card_seq"].astype(str)
    
    # Create lookup dict: (customer_id, card1, card2, card3, card4, card5, card6) -> card_id
    lookup = {}
    for _, r in unique_cards.iterrows():
        key = (
            str(r["customer_id"]),
            str(clean_val(r["card1"], "")),
            str(clean_val(r["card2"], "")),
            str(clean_val(r["card3"], "")),
            str(clean_val(r["card4"], "")),
            str(clean_val(r["card5"], "")),
            str(clean_val(r["card6"], ""))
        )
        lookup[key] = r["card_id"]
        
    print(f"✅ Card mapping built: {len(lookup)} distinct cards across {unique_cards['customer_id'].nunique()} customers.")
    return lookup, unique_cards

if __name__ == "__main__":
    conn = get_connection()
    ingest_closed_cases(conn)
