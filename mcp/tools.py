"""
mcp/tools.py — Model Context Protocol (MCP) Tools for TigerGraph Fraud Investigation
Exposes the 6 GSQL fraud detection queries and unified GraphRAG evidence gatherer as standardized MCP tools.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from graph.queries_client import FraudGraphClient, PatternDetectionResult
from rag.evidence_gatherer import GraphRAGEvidenceGatherer, EvidenceBundle

# Shared client instances
_graph_client: Optional[FraudGraphClient] = None
_evidence_gatherer: Optional[GraphRAGEvidenceGatherer] = None

def get_graph_client() -> FraudGraphClient:
    global _graph_client
    if _graph_client is None:
        _graph_client = FraudGraphClient()
    return _graph_client

def get_evidence_gatherer() -> GraphRAGEvidenceGatherer:
    global _evidence_gatherer
    if _evidence_gatherer is None:
        _evidence_gatherer = GraphRAGEvidenceGatherer(graph_client=get_graph_client())
    return _evidence_gatherer

# ─── Tool Definitions ─────────────────────────────────────────────────────────

def detect_card_testing_tool(target_txn_id: str, max_micro_txns: int = 10) -> Dict[str, Any]:
    """
    Detects card testing authorization sequences (Pattern 1 / Policy Rule R5).
    Traverses the PREV_TXN chain from target_txn_id to detect 3+ micro-authorizations (<$5.00)
    preceding a larger purchase within 24 hours.
    """
    client = get_graph_client()
    res = client.detect_card_testing(target_txn_id, max_micro_txns)
    return res.model_dump()

def detect_burst_activity_tool(target_txn_id: str, window_hours: int = 48) -> Dict[str, Any]:
    """
    Detects card-not-present (CNP) online velocity bursts (Pattern 2 / Policy Rules R1-R4).
    Traverses PREV_TXN and NEXT_TXN chain edges within window_hours to identify velocity spikes.
    """
    client = get_graph_client()
    res = client.detect_burst_activity(target_txn_id, window_hours)
    return res.model_dump()

def detect_shared_device_fanout_tool(target_txn_id: str) -> Dict[str, Any]:
    """
    Detects card-not-present fraud from a new device or proxy (Pattern 3 / Policy Rule R6).
    Traverses Transaction -> DeviceProfile -> Transaction -> Card to identify multi-account device sharing.
    """
    client = get_graph_client()
    res = client.detect_shared_device_fanout(target_txn_id)
    return res.model_dump()

def detect_geographic_anomaly_tool(target_txn_id: str) -> Dict[str, Any]:
    """
    Detects out-of-region card-present transactions and impossible travel (Pattern 4 / Policy Rules R2, R3).
    Compares transaction addr1 against Customer.home_region and checks for concurrent home activity.
    """
    client = get_graph_client()
    res = client.detect_geographic_anomaly(target_txn_id)
    return res.model_dump()

def detect_fraud_ring_tool(card_id: str, max_hops: int = 2) -> Dict[str, Any]:
    """
    Detects organized multi-card fraud rings via multi-hop bipartite graph expansion (Rules R6, R9).
    Traverses Card ↔ DeviceProfile ↔ Card and queries ClosedCase vertices for shared confirmed fraud history.
    """
    client = get_graph_client()
    res = client.detect_fraud_ring(card_id, max_hops)
    return res.model_dump()

def find_similar_cases_tool(card_id: str, pattern_filter: str = "") -> Dict[str, Any]:
    """
    Retrieves historical closed investigation cases for the card or connected ring members (Policy Rule R8).
    Returns past analyst notes, outcomes, and exposures from graph case memory.
    """
    client = get_graph_client()
    res = client.find_similar_cases(card_id, pattern_filter)
    return res.model_dump()

def gather_evidence_bundle_tool(
    case_id: str,
    card_id: str,
    target_txn_id: str,
    customer_id: str = "",
    trigger_text: str = ""
) -> Dict[str, Any]:
    """
    Unified GraphRAG Tool: Executes all 6 GSQL pattern queries on TigerGraph, performs semantic vector
    search for similar closed-case precedents, and retrieves applicable regulatory and policy rules.
    """
    gatherer = get_evidence_gatherer()
    bundle = gatherer.gather_evidence_bundle(
        case_id=case_id,
        card_id=card_id,
        target_txn_id=target_txn_id,
        customer_id=customer_id,
        trigger_text=trigger_text
    )
    return bundle.model_dump()

# Tool registry metadata for LangChain / LangGraph integration
MCP_TOOL_DEFINITIONS = [
    {
        "name": "detect_card_testing",
        "description": "Detects micro-authorization testing sequences (<$5) on a card (Rule R5).",
        "func": detect_card_testing_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "target_txn_id": {"type": "string", "description": "Flagged TransactionID"}
            },
            "required": ["target_txn_id"]
        }
    },
    {
        "name": "detect_burst_activity",
        "description": "Detects rapid CNP velocity bursts within a 48h window (Rules R1-R4).",
        "func": detect_burst_activity_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "target_txn_id": {"type": "string", "description": "Flagged TransactionID"},
                "window_hours": {"type": "integer", "default": 48}
            },
            "required": ["target_txn_id"]
        }
    },
    {
        "name": "detect_shared_device_fanout",
        "description": "Detects new device, proxy usage, and multi-card device sharing (Rule R6).",
        "func": detect_shared_device_fanout_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "target_txn_id": {"type": "string", "description": "Flagged TransactionID"}
            },
            "required": ["target_txn_id"]
        }
    },
    {
        "name": "detect_geographic_anomaly",
        "description": "Detects out-of-region card-present use and impossible travel (Rules R2-R3).",
        "func": detect_geographic_anomaly_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "target_txn_id": {"type": "string", "description": "Flagged TransactionID"}
            },
            "required": ["target_txn_id"]
        }
    },
    {
        "name": "detect_fraud_ring",
        "description": "Performs multi-hop graph expansion to detect organized multi-card fraud rings (Rules R6, R9).",
        "func": detect_fraud_ring_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "card_id": {"type": "string", "description": "Investigated card_id (e.g. C00259-K1)"}
            },
            "required": ["card_id"]
        }
    },
    {
        "name": "find_similar_cases",
        "description": "Traverses graph memory to find past closed cases for this card or connected ring (Rule R8).",
        "func": find_similar_cases_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "card_id": {"type": "string", "description": "Investigated card_id"}
            },
            "required": ["card_id"]
        }
    },
    {
        "name": "gather_evidence_bundle",
        "description": "Comprehensive GraphRAG tool: runs all 6 graph queries, vector similarity on past cases, and policy retrieval.",
        "func": gather_evidence_bundle_tool,
        "parameters": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "card_id": {"type": "string"},
                "target_txn_id": {"type": "string"},
                "customer_id": {"type": "string"},
                "trigger_text": {"type": "string"}
            },
            "required": ["case_id", "card_id", "target_txn_id"]
        }
    }
]
