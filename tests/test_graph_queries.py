"""
Tests for Phase 3 Fraud Pattern Detection Queries
"""

import pytest
from graph.queries_client import PatternDetectionResult, FraudGraphClient

def test_pattern_detection_result_model():
    res = PatternDetectionResult(
        pattern_name="card_testing",
        confidence_score=0.85,
        risk_indicator="high",
        details={"micro_txn_count": 4, "target_amount": 150.0}
    )
    assert res.pattern_name == "card_testing"
    assert res.confidence_score == 0.85
    assert res.risk_indicator == "high"
    assert res.details["micro_txn_count"] == 4

def test_pattern_result_parsing():
    client = FraudGraphClient.__new__(FraudGraphClient)
    raw_mock = [{
        "pattern_name": "fraud_ring",
        "confidence_score": 0.90,
        "risk_indicator": "high",
        "details": '{"ring_card_count": 4, "prior_confirmed_fraud_cases": 2}'
    }]
    parsed = client._parse_query_result(raw_mock, "fraud_ring")
    assert parsed.pattern_name == "fraud_ring"
    assert parsed.confidence_score == 0.90
    assert parsed.details["ring_card_count"] == 4
    assert parsed.details["prior_confirmed_fraud_cases"] == 2


def test_query_parameter_names_match_gsql_signatures():
    class RecordingConnection:
        def __init__(self):
            self.calls = []

        def runInstalledQuery(self, name, params):
            self.calls.append((name, params))
            return []

    client = FraudGraphClient.__new__(FraudGraphClient)
    client.conn = RecordingConnection()

    client.detect_card_testing("T-1")
    client.detect_burst_activity("T-1")
    client.detect_shared_device_fanout("T-1")
    client.detect_geographic_anomaly("T-1")
    client.detect_fraud_ring("C-1")
    client.find_similar_cases("C-1")

    calls = dict(client.conn.calls)
    assert calls["detect_card_testing"]["target_txn"] == ("T-1",)
    assert calls["detect_burst_activity"]["target_txn"] == ("T-1",)
    assert calls["detect_shared_device_fanout"]["target_txn"] == ("T-1",)
    assert calls["detect_geographic_anomaly"]["target_txn"] == ("T-1",)
    assert calls["detect_fraud_ring"]["target_card"] == ("C-1",)
    assert calls["find_similar_cases_graph"]["target_card"] == ("C-1",)


def test_transaction_context_resolution():
    class FakeFrame:
        def to_dict(self, orient):
            assert orient == "records"
            return [{"transaction_id": "T-1", "card_id": "C-1", "customer_id": "U-1"}]

    class RecordingConnection:
        def getVertexDataFrameById(self, vertex_type, vertex_id):
            assert vertex_type == "Transaction"
            assert vertex_id == "T-1"
            return FakeFrame()

    client = FraudGraphClient.__new__(FraudGraphClient)
    client.conn = RecordingConnection()
    assert client.resolve_transaction_context("T-1") == {
        "transaction_id": "T-1",
        "card_id": "C-1",
        "customer_id": "U-1",
    }
