"""
mcp/server.py — Model Context Protocol (MCP) Server for TigerGraph
Provides standard MCP server interface for tools execution.
"""

import sys
import json
import asyncio
from typing import Any, Dict, List
from mcp.tools import MCP_TOOL_DEFINITIONS

class TigerGraphMCPServer:
    def __init__(self):
        self.tools = {t["name"]: t for t in MCP_TOOL_DEFINITIONS}

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["parameters"]
            }
            for t in MCP_TOOL_DEFINITIONS
        ]

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self.tools:
            return {"error": f"Tool '{name}' not found", "status": "error"}
        
        tool = self.tools[name]
        func = tool["func"]
        try:
            result = func(**arguments)
            return {"content": result, "status": "success"}
        except Exception as e:
            return {"error": str(e), "status": "error"}

    async def run_stdio(self):
        """Standard stdio transport loop for MCP clients"""
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)
        
        while True:
            line = await reader.readline()
            if not line:
                break
            
            try:
                msg = json.loads(line.decode("utf-8").strip())
                req_id = msg.get("id")
                method = msg.get("method")
                params = msg.get("params", {})

                if method == "tools/list":
                    res = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": self.list_tools()}}
                elif method == "tools/call":
                    tool_name = params.get("name")
                    tool_args = params.get("arguments", {})
                    out = self.call_tool(tool_name, tool_args)
                    res = {"jsonrpc": "2.0", "id": req_id, "result": out}
                else:
                    res = {"jsonrpc": "2.0", "id": req_id, "error": {"code": -32601, "message": "Method not found"}}

                sys.stdout.write(json.dumps(res) + "\n")
                sys.stdout.flush()
            except Exception as e:
                err_res = {"jsonrpc": "2.0", "error": {"code": -32700, "message": str(e)}}
                sys.stdout.write(json.dumps(err_res) + "\n")
                sys.stdout.flush()

if __name__ == "__main__":
    server = TigerGraphMCPServer()
    print("[MCP Server] TigerGraph MCP Server initialized with tools:", list(server.tools.keys()))
