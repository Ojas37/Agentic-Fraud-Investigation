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
