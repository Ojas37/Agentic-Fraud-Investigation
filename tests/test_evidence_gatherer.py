"""
Tests for Phase 4 GraphRAG Layer and Evidence Gatherer
"""

import pytest
from rag.vector_store import FraudVectorStore
from rag.evidence_gatherer import GraphRAGEvidenceGatherer, EvidenceBundle
from graph.queries_client import FraudGraphClient

def test_vector_store_indexing_and_search():
    store = FraudVectorStore()
    assert len(store.documents) > 0
    
    # Test search for card testing
    res = store.search("micro authorization under $5 card testing", top_k=3, doc_type="policy_rule")
    assert len(res) > 0
    assert any("R5" in r["id"] or "Card Testing" in r["title"] for r in res)

def test_vector_store_closed_case_search():
    store = FraudVectorStore()
    res = store.search("stolen card number unusual device proxy", top_k=3, doc_type="closed_case")
    assert len(res) > 0
    assert "metadata" in res[0]

def test_evidence_gatherer_bundle_creation():
    store = FraudVectorStore()
    gatherer = GraphRAGEvidenceGatherer(vector_store=store)
    
    bundle = gatherer.gather_evidence_bundle(
        case_id="TEST-001",
        card_id="C00259-K1",
        target_txn_id="3000120",
        customer_id="C00259",
        trigger_text="Real-time model scored transaction 3000120 at 0.75"
    )
    
    assert isinstance(bundle, EvidenceBundle)
    assert bundle.case_id == "TEST-001"
    assert len(bundle.case_precedents) > 0
    assert len(bundle.applicable_policies) > 0
    assert len(bundle.synthesis_markdown) > 0
