"""
Query Installer for HHGOA Fraud Investigation Agent
Installs all 6 standardized GSQL fraud detection queries and home-region derivation query.
"""

import os
import glob
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
            token = conn.getToken(SECRET)
            conn.apiToken = token[0] if isinstance(token, tuple) else token
        except Exception as e:
            print(f"Note on token: {e}")
    return conn

def install_queries(conn):
    query_files = [
        "graph/queries/detect_card_testing.gsql",
        "graph/queries/detect_burst_activity.gsql",
        "graph/queries/detect_shared_device_fanout.gsql",
        "graph/queries/detect_geographic_anomaly.gsql",
        "graph/queries/detect_fraud_ring.gsql",
        "graph/queries/find_similar_cases_graph.gsql"
    ]

    print("\n=== Installing 6 Standardized Fraud Detection Queries ===")
    
    # Read and concatenate queries
    gsql_script = "USE GRAPH FraudGraph\n"
    query_names = []
    
    for qf in query_files:
        if os.path.exists(qf):
            qname = os.path.basename(qf).replace(".gsql", "")
            query_names.append(qname)
            with open(qf, "r", encoding="utf-8") as f:
                content = f.read().replace("USE GRAPH FraudGraph", "")
                gsql_script += f"\n{content}\n"

    install_cmd = f"INSTALL QUERY {', '.join(query_names)}"
    full_script = f"{gsql_script}\n{install_cmd}\n"

    print(f"Submitting {len(query_names)} queries to TigerGraph for compilation & installation...")
    res = conn.gsql(full_script)
    print("=== GSQL Installation Result ===")
    print(res)

if __name__ == "__main__":
    conn = get_connection()
    install_queries(conn)
