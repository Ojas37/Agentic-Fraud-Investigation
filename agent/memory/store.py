"""Case memory persistence and retrieval for Phase 8."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Protocol

from agent.models import FraudCase
from graph.queries_client import FraudGraphClient
from rag.vector_store import FraudVectorStore


class GraphCaseWriter(Protocol):
    def write_case(self, case: FraudCase) -> str:
        ...


class TigerGraphCaseWriter:
    """Write a completed case and its known entity links to TigerGraph."""

    def __init__(self, graph_client: FraudGraphClient | None = None):
        self.graph_client = graph_client or FraudGraphClient()

    def write_case(self, case: FraudCase) -> str:
        graph_case_id = case.graph_case_id or f"CASE-{case.case_id}"
        payload = case.trigger.raw_payload
        card_id = str(payload.get("card_id", ""))
        txn_id = str(payload.get("flagged_txn_id", case.trigger.entity_id))
        pattern = case.pattern_matches[0].pattern_name if case.pattern_matches else "none"
        pattern_description = case.pattern_matches[0].description if case.pattern_matches else ""

        vertex = {
            "case_id": case.case_id,
            "customer_id": str(payload.get("customer_id", "")),
            "card_id": card_id,
            "status": case.status.value,
            "verdict": self._verdict(case),
            "fraud_probability": case.confidence or 0.0,
            "pattern": pattern,
            "pattern_description": pattern_description,
            "exposure_usd": self._exposure(case),
            "summary": case.explanation,
            "stop_reason": case.stop_reason,
            "opened_at": case.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "closed_at": case.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "evidence_json": json.dumps([item.model_dump(mode="json") for item in case.evidence]),
            "next_best_actions_json": json.dumps({
                "before": [item.model_dump(mode="json") for item in case.actions_before_extra_evidence],
                "after": [item.model_dump(mode="json") for item in case.actions_after_extra_evidence],
            }),
            "sar_json": json.dumps({"required": case.sar_required, "report": case.sar_report}),
            "evidence_requests_json": json.dumps([item.model_dump(mode="json") for item in case.evidence_requests]),
            "tool_calls": 0,
            "tokens": 0,
            "latency_s": 0.0,
            "written_to_graph": True,
            "embedding_stored": False,
        }
        self.graph_client.conn.upsertVertices("FraudCase", [(graph_case_id, vertex)])

        if card_id:
            self.graph_client.conn.upsertEdges(
                "FraudCase", "LIVE_CASE_ON_CARD", "Card", [(graph_case_id, card_id, {})]
            )
        if txn_id:
            self.graph_client.conn.upsertEdges(
                "FraudCase", "LIVE_CASE_INVOLVES", "Transaction", [(graph_case_id, txn_id, {"flagged": True})]
            )
        return graph_case_id

    @staticmethod
    def _verdict(case: FraudCase) -> str:
        if case.status.value == "resolved_fraud":
            return "fraud"
        if case.status.value == "resolved_cleared":
            return "legitimate"
        return "uncertain"

    @staticmethod
    def _exposure(case: FraudCase) -> float:
        amounts = [item.data.get("exposure_usd") for item in case.evidence if item.data.get("exposure_usd") is not None]
        return float(max(amounts, default=0.0))


class CaseMemory:
    """Coordinate graph persistence and semantic retrieval of live case summaries."""

    def __init__(
        self,
        graph_writer: GraphCaseWriter | None = None,
        vector_store: FraudVectorStore | None = None,
    ):
        self.graph_writer = graph_writer
        self.vector_store = vector_store or FraudVectorStore()

    def write_case(self, case: FraudCase) -> FraudCase:
        if self.graph_writer is not None:
            graph_case_id = self.graph_writer.write_case(case)
            case.written_to_graph = True
            case.graph_case_id = graph_case_id
        self.vector_store.add_case(case)
        return case

    def retrieve_similar_cases(self, case: FraudCase, top_k: int = 3) -> list[dict[str, Any]]:
        query = self._case_query(case)
        return self.vector_store.search(query, top_k=top_k, doc_type="live_case")

    @staticmethod
    def _case_query(case: FraudCase) -> str:
        patterns = " ".join(match.pattern_name for match in case.pattern_matches)
        evidence = " ".join(item.content for item in case.evidence[:3])
        return f"{patterns} {case.trigger.description} {evidence}".strip()


def build_case_memory() -> CaseMemory:
    """Build production memory backed by TigerGraph and the local vector index."""
    return CaseMemory(graph_writer=TigerGraphCaseWriter())
