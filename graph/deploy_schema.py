import os
import re
from dotenv import load_dotenv
import pyTigerGraph as tg

load_dotenv()

host = os.getenv("TG_HOST")
username = os.getenv("TG_USERNAME", "tigergraph")
password = os.getenv("TG_PASSWORD", "tigergraph")
secret = os.getenv("TG_SECRET")

print(f"Connecting to TigerGraph at {host}...")
conn = tg.TigerGraphConnection(
    host=host,
    username=username,
    password=password,
    gsqlSecret=secret
)

with open("graph/schema.gsql", "r", encoding="utf-8") as f:
    text = f.read()

# Filter /* ... */ comments
text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)

lines = []
for line in text.splitlines():
    line = line.strip()
    if not line or line.startswith("--") or line.startswith("USE GRAPH"):
        continue
    # remove trailing comments
    line = re.sub(r'--.*$', '', line).strip()
    if line:
        lines.append(line)

gsql_clean = "\n".join(lines)
gsql_full = f"""
{gsql_clean}
CREATE GRAPH FraudGraph(*)
"""

print("Deploying FraudGraph schema to TigerGraph...")
res = conn.gsql(gsql_full)
print("=== Deployment Result ===")
print(res)

print("\n=== Verifying Graph Schema ===")
print(conn.gsql("ls"))
