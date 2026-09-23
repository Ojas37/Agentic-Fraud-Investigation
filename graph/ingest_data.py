"""
Data Ingestion Pipeline for HHGOA Fraud Investigation Agent
Loads raw CSVs into TigerGraph FraudGraph:
  1. closed_cases_history.csv -> ClosedCase, Card, Customer, Case Edges
  2. identity.csv -> DeviceProfile, Transaction-Device mappings
  3. transactions.csv -> Customer, Card, Transaction, EmailDomain, BillingRegion, and Edges
  4. Post-load transaction chain builder (NEXT_TXN / PREV_TXN)
"""

import os
import sys
import hashlib
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
import pyTigerGraph as tg

# Fix Windows console encoding and force line-buffering
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)

load_dotenv()

HOST = os.getenv("TG_HOST")
USERNAME = os.getenv("TG_USERNAME", "tigergraph")
PASSWORD = os.getenv("TG_PASSWORD", "tigergraph")
GRAPH_NAME = os.getenv("TG_GRAPH_NAME", "FraudGraph")
SECRET = os.getenv("TG_SECRET")

def get_connection():
    log(f"Connecting to TigerGraph at {HOST}, graph: {GRAPH_NAME}...")
    conn = tg.TigerGraphConnection(
        host=HOST,
        graphname=GRAPH_NAME,
        username=USERNAME,
        password=PASSWORD,
        gsqlSecret=SECRET
    )
    if SECRET:
        try:
            token = conn.getToken(SECRET)
            conn.apiToken = token[0] if isinstance(token, tuple) else token
        except Exception as e:
            log(f"Note on token: {e}")
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

    print("[SUCCESS] Closed cases ingestion complete!")

def ingest_identity(conn, csv_path="data/raw/identity.csv", batch_size=1000):
    print(f"\n=== Ingesting Identity / Device Profiles from {csv_path} ===")
    if not os.path.exists(csv_path):
        print(f"File {csv_path} not found!")
        return {}

    df = pd.read_csv(csv_path)
    print(f"Total identity rows: {len(df)}")

    # Deduplicate device profiles
    device_profiles = {}
    txn_device_map = {} # TransactionID -> (device_profile_id, is_new, proxy_used)

    for _, row in df.iterrows():
        tx_id = str(row["TransactionID"])
        dev_type = str(clean_val(row.get("DeviceType"), ""))
        dev_info = str(clean_val(row.get("DeviceInfo"), ""))
        os_val = str(clean_val(row.get("id_30"), ""))
        browser_val = str(clean_val(row.get("id_31"), ""))
        screen_val = str(clean_val(row.get("id_33"), ""))
        proxy_val = str(clean_val(row.get("id_23"), ""))
        match_status = str(clean_val(row.get("id_34"), ""))
        status_15 = str(clean_val(row.get("id_15"), ""))

        profile_id = compute_device_profile_id(dev_info, os_val, browser_val, screen_val)
        
        is_new = (status_15 == "New")
        proxy_used = bool(proxy_val and proxy_val.lower() not in ["unknown", "none", ""])

        if profile_id not in device_profiles:
            device_profiles[profile_id] = {
                "DeviceType": dev_type,
                "DeviceInfo": dev_info,
                "os": os_val,
                "browser": browser_val,
                "screen": screen_val,
                "proxy_flag": proxy_val,
                "device_match_status": match_status,
                "card_count": 0
            }

        txn_device_map[tx_id] = (profile_id, is_new, proxy_used)

    print(f"Unique Device Profiles found: {len(device_profiles)}")
    dev_vertices = [(k, v) for k, v in device_profiles.items()]

    for i in range(0, len(dev_vertices), batch_size):
        conn.upsertVertices("DeviceProfile", dev_vertices[i:i+batch_size])

    print(f"[SUCCESS] Upserted {len(dev_vertices)} DeviceProfile vertices.")
    return txn_device_map

def build_card_mapping(tx_csv_path="data/raw/transactions.csv"):
    print("Building card mapping from transactions.csv...")
    cols = ["customer_id", "card1", "card2", "card3", "card4", "card5", "card6", "ts"]
    records = []
    
    for chunk in pd.read_csv(tx_csv_path, usecols=cols, chunksize=100000):
        records.append(chunk.dropna(subset=["customer_id"]))
        
    all_df = pd.concat(records, ignore_index=True)
    all_df["ts"] = pd.to_datetime(all_df["ts"])
    all_df = all_df.sort_values("ts")
    
    unique_cards = all_df.drop_duplicates(subset=["customer_id", "card1", "card2", "card3", "card4", "card5", "card6"]).copy()
    unique_cards["card_seq"] = unique_cards.groupby("customer_id").cumcount() + 1
    unique_cards["card_id"] = unique_cards["customer_id"] + "-K" + unique_cards["card_seq"].astype(str)
    
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
        
    print(f"[SUCCESS] Card mapping built: {len(lookup)} distinct cards across {unique_cards['customer_id'].nunique()} customers.")
    return lookup, unique_cards

def ingest_transactions(conn, tx_csv_path="data/raw/transactions.csv", id_csv_path="data/raw/identity.csv", chunk_size=25000):
    print(f"\n=== Ingesting Transactions from {tx_csv_path} ===")
    
    # Step 1: Load identity mappings
    txn_device_map = ingest_identity(conn, id_csv_path)

    # Step 2: Build card mappings
    card_lookup, unique_cards = build_card_mapping(tx_csv_path)

    # Step 3: Upsert Card and Customer base records
    print("Upserting Card vertices...")
    card_vertices = []
    owns_edges = []
    for _, r in unique_cards.iterrows():
        cid = r["card_id"]
        cust_id = str(r["customer_id"])
        c1 = str(clean_val(r["card1"], ""))
        c2 = str(clean_val(r["card2"], ""))
        c3 = str(clean_val(r["card3"], ""))
        c4 = str(clean_val(r["card4"], ""))
        c5 = str(clean_val(r["card5"], ""))
        c6 = str(clean_val(r["card6"], ""))
        
        card_vertices.append((cid, {
            "customer_id": cust_id,
            "card1": c1,
            "card2": c2,
            "card3": c3,
            "card4": c4,
            "card5": c5,
            "card6": c6,
            "is_blocked": False,
            "block_reason": ""
        }))
        owns_edges.append((cust_id, cid, {}))

    for i in range(0, len(card_vertices), 1000):
        conn.upsertVertices("Card", card_vertices[i:i+1000])
        conn.upsertEdges("Customer", "OWNS", "Card", owns_edges[i:i+1000])

    print(f"[SUCCESS] Upserted {len(card_vertices)} Card vertices & OWNS edges.")

    # Step 4: Stream transactions in chunks
    total_tx_loaded = 0
    start_time = time.time()

    # Pre-select columns for fast ingestion
    core_cols = [
        "TransactionID", "customer_id", "ts", "channel", "risk_score",
        "TransactionDT", "TransactionAmt", "ProductCD",
        "card1", "card2", "card3", "card4", "card5", "card6",
        "addr1", "addr2", "dist1", "dist2",
        "P_emaildomain", "R_emaildomain",
        "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14",
        "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12", "D13", "D14", "D15",
        "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9",
        "V1", "V2", "V3", "V4", "V12", "V13", "V14", "V83", "V127"
    ]

    for chunk in pd.read_csv(tx_csv_path, chunksize=chunk_size):
        tx_vertices = []
        cust_vertices = {}
        email_domains = set()
        billing_regions = set()
        
        made_edges = []
        from_device_edges = []
        purchaser_email_edges = []
        recipient_email_edges = []
        billed_in_edges = []

        for _, row in chunk.iterrows():
            tx_id = str(row["TransactionID"])
            cust_id = str(row["customer_id"]) if not pd.isna(row["customer_id"]) else ""
            ts_val = str(row["ts"]) if not pd.isna(row["ts"]) else ""
            channel_val = str(clean_val(row.get("channel"), "online"))
            risk_val = float(row["risk_score"]) if not pd.isna(row.get("risk_score")) else 0.0
            
            c1 = str(clean_val(row["card1"], ""))
            c2 = str(clean_val(row["card2"], ""))
            c3 = str(clean_val(row["card3"], ""))
            c4 = str(clean_val(row["card4"], ""))
            c5 = str(clean_val(row["card5"], ""))
            c6 = str(clean_val(row["card6"], ""))

            key = (cust_id, c1, c2, c3, c4, c5, c6)
            card_id = card_lookup.get(key, f"{cust_id}-K1" if cust_id else "UNKNOWN")

            addr1 = str(clean_val(row.get("addr1"), ""))
            addr2 = str(clean_val(row.get("addr2"), ""))
            p_email = str(clean_val(row.get("P_emaildomain"), ""))
            r_email = str(clean_val(row.get("R_emaildomain"), ""))

            # Build vertex dict
            v_data = {
                "customer_id": cust_id,
                "card_id": card_id,
                "ts": ts_val,
                "channel": channel_val,
                "risk_score": risk_val,
                "TransactionDT": int(row["TransactionDT"]) if not pd.isna(row["TransactionDT"]) else 0,
                "TransactionAmt": float(row["TransactionAmt"]) if not pd.isna(row["TransactionAmt"]) else 0.0,
                "ProductCD": str(clean_val(row.get("ProductCD"), "")),
                "card1": c1, "card2": c2, "card3": c3, "card4": c4, "card5": c5, "card6": c6,
                "addr1": addr1, "addr2": addr2,
                "dist1": float(row["dist1"]) if not pd.isna(row.get("dist1")) else 0.0,
                "dist2": float(row["dist2"]) if not pd.isna(row.get("dist2")) else 0.0,
                "P_emaildomain": p_email, "R_emaildomain": r_email,
                "is_suspicious": False, "in_case": False
            }

            # Add C and D features
            for col in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10", "C11", "C12", "C13", "C14"]:
                v_data[col] = float(row[col]) if col in row and not pd.isna(row[col]) else 0.0
            for col in ["D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9", "D10", "D11", "D12", "D13", "D14", "D15"]:
                v_data[col] = float(row[col]) if col in row and not pd.isna(row[col]) else 0.0
            for col in ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]:
                v_data[col] = str(clean_val(row.get(col), ""))
            for col in ["V1", "V2", "V3", "V4", "V12", "V13", "V14", "V83", "V127"]:
                v_data[col] = float(row[col]) if col in row and not pd.isna(row[col]) else 0.0

            tx_vertices.append((tx_id, v_data))

            # Edge: MADE
            if card_id:
                made_edges.append((card_id, tx_id, {"ts": ts_val}))

            # Edge: FROM_DEVICE
            if tx_id in txn_device_map:
                dev_id, is_new, proxy_used = txn_device_map[tx_id]
                from_device_edges.append((tx_id, dev_id, {"device_new": is_new, "proxy_used": proxy_used}))

            # Email domains
            if p_email:
                email_domains.add(p_email)
                purchaser_email_edges.append((tx_id, p_email, {}))
            if r_email:
                email_domains.add(r_email)
                recipient_email_edges.append((tx_id, r_email, {}))

            # Billing region
            if addr1:
                billing_regions.add((addr1, addr2))
                billed_in_edges.append((tx_id, addr1, {"addr1": addr1, "addr2": addr2}))

            # Customer tracking
            if cust_id:
                if cust_id not in cust_vertices:
                    cust_vertices[cust_id] = {"first_seen_ts": ts_val, "last_seen_ts": ts_val, "total_txn_count": 0, "total_spend_usd": 0.0}
                cust_vertices[cust_id]["last_seen_ts"] = ts_val
                cust_vertices[cust_id]["total_txn_count"] += 1
                cust_vertices[cust_id]["total_spend_usd"] += float(row["TransactionAmt"]) if not pd.isna(row["TransactionAmt"]) else 0.0

        # Upsert chunk to TigerGraph
        if email_domains:
            conn.upsertVertices("EmailDomain", [(d, {}) for d in email_domains])
        if billing_regions:
            conn.upsertVertices("BillingRegion", [(a1, {"country_code": a2}) for a1, a2 in billing_regions])
        if cust_vertices:
            conn.upsertVertices("Customer", list(cust_vertices.items()))

        conn.upsertVertices("Transaction", tx_vertices)
        conn.upsertEdges("Card", "MADE", "Transaction", made_edges)

        if from_device_edges:
            conn.upsertEdges("Transaction", "FROM_DEVICE", "DeviceProfile", from_device_edges)
        if purchaser_email_edges:
            conn.upsertEdges("Transaction", "PURCHASER_EMAIL", "EmailDomain", purchaser_email_edges)
        if recipient_email_edges:
            conn.upsertEdges("Transaction", "RECIPIENT_EMAIL", "EmailDomain", recipient_email_edges)
        if billed_in_edges:
            conn.upsertEdges("Transaction", "BILLED_IN", "BillingRegion", billed_in_edges)

        total_tx_loaded += len(tx_vertices)
        elapsed = time.time() - start_time
        log(f"Loaded {total_tx_loaded:,} transactions ({len(tx_vertices)} this chunk) in {elapsed:.1f}s...")

    log(f"\n[SUCCESS] All {total_tx_loaded:,} transactions ingested successfully in {time.time()-start_time:.1f}s!")

if __name__ == "__main__":
    conn = get_connection()
    ingest_closed_cases(conn)
    ingest_transactions(conn)
