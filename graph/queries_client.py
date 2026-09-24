"""
TigerGraph Queries Client for HHGOA Fraud Investigation Agent
Executes the 6 standardized fraud detection queries and formats results for the agent.
"""

import os
import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import pyTigerGraph as tg

load_dotenv()

class PatternDetectionResult(BaseModel):
    pattern_name: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    risk_indicator: str  # "low" | "medium" | "high"
    details: Dict[str, Any] = Field(default_factory=dict)
    raw_details_str: str = ""

class FraudGraphClient:
    def __init__(self, host: Optional[str] = None, graph_name: Optional[str] = None, secret: Optional[str] = None):
        self.host = host or os.getenv("TG_HOST")
        self.graph_name = graph_name or os.getenv("TG_GRAPH_NAME", "FraudGraph")
        self.secret = secret or os.getenv("TG_SECRET")
        self.username = os.getenv("TG_USERNAME", "tigergraph")
        self.password = os.getenv("TG_PASSWORD", "tigergraph")
        
        self.conn = tg.TigerGraphConnection(
            host=self.host,
            graphname=self.graph_name,
            username=self.username,
            password=self.password,
            gsqlSecret=self.secret
        )
        if self.secret:
            try:
                token = self.conn.getToken(self.secret)
                self.conn.apiToken = token[0] if isinstance(token, tuple) else token
            except Exception as e:
                print(f"[FraudGraphClient] Token init note: {e}")

    def _parse_query_result(self, raw_res: Any, default_pattern: str) -> PatternDetectionResult:
        if not raw_res or not isinstance(raw_res, list):
            return PatternDetectionResult(
                pattern_name=default_pattern,
                confidence_score=0.0,
                risk_indicator="low",
                details={},
                raw_details_str="{}"
            )
        
        row = raw_res[0] if len(raw_res) > 0 else {}
        pname = row.get("pattern_name", default_pattern)
        conf = float(row.get("confidence_score", 0.0))
        risk = str(row.get("risk_indicator", "low"))
        details_raw = row.get("details", "{}")
        
        try:
            details_dict = json.loads(details_raw) if isinstance(details_raw, str) else details_raw
        except Exception:
            details_dict = {"raw": details_raw}
            
        return PatternDetectionResult(
            pattern_name=pname,
            confidence_score=max(0.0, min(1.0, conf)),
            risk_indicator=risk,
            details=details_dict,
            raw_details_str=str(details_raw)
        )

    def detect_card_testing(self, target_txn_id: str, max_micro_txns: int = 10) -> PatternDetectionResult:
        res = self.conn.runInstalledQuery("detect_card_testing", params={
            "target_txn": target_txn_id,
            "max_micro_txns": max_micro_txns
        })
        return self._parse_query_result(res, "card_testing")

    def detect_burst_activity(self, target_txn_id: str, window_hours: int = 48) -> PatternDetectionResult:
        res = self.conn.runInstalledQuery("detect_burst_activity", params={
            "target_txn": target_txn_id,
            "window_hours": window_hours
        })
        return self._parse_query_result(res, "cnp")

    def detect_shared_device_fanout(self, target_txn_id: str) -> PatternDetectionResult:
        res = self.conn.runInstalledQuery("detect_shared_device_fanout", params={
            "target_txn": target_txn_id
        })
        return self._parse_query_result(res, "cnp_new_device")

    def detect_geographic_anomaly(self, target_txn_id: str) -> PatternDetectionResult:
        res = self.conn.runInstalledQuery("detect_geographic_anomaly", params={
            "target_txn": target_txn_id
        })
        return self._parse_query_result(res, "out_of_region")

    def detect_fraud_ring(self, card_id: str, max_hops: int = 2) -> PatternDetectionResult:
        res = self.conn.runInstalledQuery("detect_fraud_ring", params={
            "target_card": card_id,
            "max_hops": max_hops
        })
        return self._parse_query_result(res, "fraud_ring")

    def find_similar_cases(self, card_id: str, pattern_filter: str = "") -> PatternDetectionResult:
        res = self.conn.runInstalledQuery("find_similar_cases_graph", params={
            "target_card": card_id,
            "pattern_filter": pattern_filter
        })
        return self._parse_query_result(res, "case_memory_match")

    def run_all_detection_patterns(self, target_txn_id: str, card_id: str) -> Dict[str, PatternDetectionResult]:
        """Runs all 6 detection queries in parallel/sequence for comprehensive case assessment"""
        return {
            "card_testing": self.detect_card_testing(target_txn_id),
            "burst_activity": self.detect_burst_activity(target_txn_id),
            "shared_device": self.detect_shared_device_fanout(target_txn_id),
            "geographic_anomaly": self.detect_geographic_anomaly(target_txn_id),
            "fraud_ring": self.detect_fraud_ring(card_id),
            "similar_cases": self.find_similar_cases(card_id)
        }
