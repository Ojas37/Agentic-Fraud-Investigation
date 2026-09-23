"""
Tests for Phase 5 TigerGraph MCP Integration
"""

import pytest
from mcp.tools import MCP_TOOL_DEFINITIONS
from mcp.server import TigerGraphMCPServer
from mcp.client import get_langchain_mcp_tools

def test_mcp_tool_definitions():
    assert len(MCP_TOOL_DEFINITIONS) == 7
    tool_names = [t["name"] for t in MCP_TOOL_DEFINITIONS]
    assert "detect_card_testing" in tool_names
    assert "detect_burst_activity" in tool_names
    assert "detect_shared_device_fanout" in tool_names
    assert "detect_geographic_anomaly" in tool_names
    assert "detect_fraud_ring" in tool_names
    assert "find_similar_cases" in tool_names
    assert "gather_evidence_bundle" in tool_names

def test_mcp_server_listing():
    server = TigerGraphMCPServer()
    tools = server.list_tools()
    assert len(tools) == 7
    for t in tools:
        assert "name" in t
        assert "description" in t
        assert "input_schema" in t

def test_langchain_mcp_tools_bindings():
    lc_tools = get_langchain_mcp_tools()
    assert len(lc_tools) == 7
    for tool in lc_tools:
        assert tool.name in [
            "detect_card_testing",
            "detect_burst_activity",
            "detect_shared_device_fanout",
            "detect_geographic_anomaly",
            "detect_fraud_ring",
            "find_similar_cases",
            "gather_evidence_bundle"
        ]
        assert tool.args_schema is not None
