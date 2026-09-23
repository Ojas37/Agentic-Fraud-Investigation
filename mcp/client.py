"""
mcp/client.py — MCP Tool Client & LangChain Tool Adapters
Wraps MCP tools into LangChain BaseTool instances for seamless integration into LangGraph agent nodes.
"""

from typing import List, Any, Type, Dict
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
from mcp.tools import (
    detect_card_testing_tool,
    detect_burst_activity_tool,
    detect_shared_device_fanout_tool,
    detect_geographic_anomaly_tool,
    detect_fraud_ring_tool,
    find_similar_cases_tool,
    gather_evidence_bundle_tool
)

class CardTestingInput(BaseModel):
    target_txn_id: str = Field(description="The flagged transaction ID to analyze for preceding micro-authorizations")
    max_micro_txns: int = Field(default=10, description="Max preceding transactions to inspect")

class BurstActivityInput(BaseModel):
    target_txn_id: str = Field(description="The flagged transaction ID to analyze for velocity bursts")
    window_hours: int = Field(default=48, description="Time window in hours")

class SharedDeviceInput(BaseModel):
    target_txn_id: str = Field(description="The flagged transaction ID to analyze for device sharing and proxy flags")

class GeographicAnomalyInput(BaseModel):
    target_txn_id: str = Field(description="The flagged transaction ID to analyze for out-of-region and impossible travel")

class FraudRingInput(BaseModel):
    card_id: str = Field(description="The card ID to expand multi-hop across shared devices to detect fraud rings")
    max_hops: int = Field(default=2, description="Max graph hops for bipartite expansion")

class SimilarCasesInput(BaseModel):
    card_id: str = Field(description="The card ID to find matching closed case history")
    pattern_filter: str = Field(default="", description="Optional pattern name filter")

class EvidenceBundleInput(BaseModel):
    case_id: str = Field(description="The investigation case identifier")
    card_id: str = Field(description="The card ID being investigated")
    target_txn_id: str = Field(description="The flagged transaction ID")
    customer_id: str = Field(default="", description="The customer ID")
    trigger_text: str = Field(default="", description="The trigger message or reason")

def get_langchain_mcp_tools() -> List[StructuredTool]:
    """Returns all TigerGraph MCP tools formatted as LangChain StructuredTools for LangGraph nodes"""
    return [
        StructuredTool.from_function(
            func=detect_card_testing_tool,
            name="detect_card_testing",
            description="Detects micro-authorization testing sequences (<$5) on a card (Rule R5).",
            args_schema=CardTestingInput
        ),
        StructuredTool.from_function(
            func=detect_burst_activity_tool,
            name="detect_burst_activity",
            description="Detects rapid CNP velocity bursts within a 48h window (Rules R1-R4).",
            args_schema=BurstActivityInput
        ),
        StructuredTool.from_function(
            func=detect_shared_device_fanout_tool,
            name="detect_shared_device_fanout",
            description="Detects new device, proxy usage, and multi-card device sharing (Rule R6).",
            args_schema=SharedDeviceInput
        ),
        StructuredTool.from_function(
            func=detect_geographic_anomaly_tool,
            name="detect_geographic_anomaly",
            description="Detects out-of-region card-present use and impossible travel (Rules R2-R3).",
            args_schema=GeographicAnomalyInput
        ),
        StructuredTool.from_function(
            func=detect_fraud_ring_tool,
            name="detect_fraud_ring",
            description="Performs multi-hop graph expansion to detect organized multi-card fraud rings (Rules R6, R9).",
            args_schema=FraudRingInput
        ),
        StructuredTool.from_function(
            func=find_similar_cases_tool,
            name="find_similar_cases",
            description="Traverses graph memory to find past closed cases for this card or connected ring (Rule R8).",
            args_schema=SimilarCasesInput
        ),
        StructuredTool.from_function(
            func=gather_evidence_bundle_tool,
            name="gather_evidence_bundle",
            description="Comprehensive GraphRAG tool: runs all 6 graph queries, vector similarity on past cases, and policy retrieval.",
            args_schema=EvidenceBundleInput
        )
    ]
