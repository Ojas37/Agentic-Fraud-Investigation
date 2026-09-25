"""
rag/evidence_gatherer.py — GraphRAG Unified Evidence Gatherer
Combines:
  1. Structural GSQL pattern detection queries from TigerGraph FraudGraph
  2. Semantic vector search over historical closed case narratives
  3. Policy rules and regulatory guidance retrieval
Outputs a structured EvidenceBundle for the LangGraph agent core.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from graph.queries_client import FraudGraphClient, PatternDetectionResult
from rag.vector_store import FraudVectorStore

class EvidenceItem(BaseModel):
    category: str  # "graph_pattern" | "case_precedent" | "policy_rule" | "regulatory_guidance"
    title: str
    confidence: float = 1.0
    summary: str
    data: Dict[str, Any] = Field(default_factory=dict)

class EvidenceBundle(BaseModel):
    case_id: str
    card_id: str
    target_txn_id: str
    customer_id: str = ""
    trigger_text: str = ""
    graph_patterns: Dict[str, PatternDetectionResult] = Field(default_factory=dict)
    case_precedents: List[Dict[str, Any]] = Field(default_factory=list)
    applicable_policies: List[Dict[str, Any]] = Field(default_factory=list)
    regulatory_citations: List[Dict[str, Any]] = Field(default_factory=list)
    items: List[EvidenceItem] = Field(default_factory=list)
    synthesis_markdown: str = ""

class GraphRAGEvidenceGatherer:
    def __init__(self, graph_client: Optional[FraudGraphClient] = None, vector_store: Optional[FraudVectorStore] = None):
        self.graph_client = graph_client or FraudGraphClient()
        self.vector_store = vector_store or FraudVectorStore()

    def resolve_transaction_context(self, transaction_id: str) -> Dict[str, str]:
        return self.graph_client.resolve_transaction_context(transaction_id)

    def gather_evidence_bundle(
        self,
        case_id: str,
        card_id: str,
        target_txn_id: str,
        customer_id: str = "",
        trigger_text: str = "",
        risk_score: Optional[float] = None
    ) -> EvidenceBundle:
        
        bundle = EvidenceBundle(
            case_id=case_id,
            card_id=card_id,
            target_txn_id=target_txn_id,
            customer_id=customer_id,
            trigger_text=trigger_text
        )

        # ─── 1. Run only the graph patterns relevant to this trigger ─────────
        try:
            patterns = self._run_relevant_patterns(
                target_txn_id=target_txn_id,
                card_id=card_id,
                trigger_text=trigger_text,
                risk_score=risk_score,
            )
            bundle.graph_patterns = patterns
            
            for pname, p_res in patterns.items():
                if p_res.confidence_score > 0.15 or p_res.risk_indicator in ["medium", "high"]:
                    bundle.items.append(EvidenceItem(
                        category="graph_pattern",
                        title=f"Graph Signal: {p_res.pattern_name} ({p_res.risk_indicator.upper()} risk)",
                        confidence=p_res.confidence_score,
                        summary=f"Detected pattern {p_res.pattern_name} with confidence {p_res.confidence_score:.2f}. Details: {p_res.details}",
                        data=p_res.details
                    ))
        except Exception as e:
            print(f"[EvidenceGatherer] Graph pattern query notice: {e}")

        # ─── 2. Retrieve Similar Closed-Case Precedents ────────────────────
        query_terms = [trigger_text, f"Card {card_id}"]
        if bundle.graph_patterns:
            top_pattern = max(bundle.graph_patterns.values(), key=lambda p: p.confidence_score)
            if top_pattern.confidence_score > 0.3:
                query_terms.append(f"Pattern {top_pattern.pattern_name}")

        search_query = " ".join(query_terms)
        similar_cases = self.vector_store.search(search_query, top_k=2, doc_type="closed_case")
        bundle.case_precedents = similar_cases

        for c in similar_cases:
            bundle.items.append(EvidenceItem(
                category="case_precedent",
                title=f"Precedent Case: {c['title']} (Score: {c['score']:.2f})",
                confidence=c["score"],
                summary=c["content"],
                data=c["metadata"]
            ))

        # ─── 3. Retrieve Applicable Policy Rules & Regulatory Guidance ─────
        policy_matches = self.vector_store.search(search_query, top_k=1, doc_type="policy_rule")
        bundle.applicable_policies = policy_matches
        for p in policy_matches:
            bundle.items.append(EvidenceItem(
                category="policy_rule",
                title=f"Policy Rule: {p['title']}",
                confidence=p["score"],
                summary=p["content"],
                data=p["metadata"]
            ))

        reg_matches = self.vector_store.search(search_query, top_k=1, doc_type="regulatory_guidance")
        bundle.regulatory_citations = reg_matches
        for r in reg_matches:
            bundle.items.append(EvidenceItem(
                category="regulatory_guidance",
                title=f"Regulatory Reference: {r['title']}",
                confidence=r["score"],
                summary=r["content"],
                data=r["metadata"]
            ))

        # ─── 4. Build Synthesized Markdown Summary ─────────────────────────
        bundle.synthesis_markdown = self._format_synthesis_markdown(bundle)
        return bundle

    def _run_relevant_patterns(
        self,
        target_txn_id: str,
        card_id: str,
        trigger_text: str,
        risk_score: Optional[float],
    ) -> Dict[str, PatternDetectionResult]:
        """Select a small, high-signal query set for the trigger type."""
        trigger = trigger_text.lower()
        selected: Dict[str, PatternDetectionResult] = {}

        if "customer" in trigger or "never made" in trigger or "unauthorized" in trigger:
            selected["shared_device"] = self.graph_client.detect_shared_device_fanout(target_txn_id)
            selected["geographic_anomaly"] = self.graph_client.detect_geographic_anomaly(target_txn_id)
        elif "analyst" in trigger or "same unusual device" in trigger:
            selected["shared_device"] = self.graph_client.detect_shared_device_fanout(target_txn_id)
            selected["fraud_ring"] = self.graph_client.detect_fraud_ring(card_id)
        else:
            selected["card_testing"] = self.graph_client.detect_card_testing(target_txn_id)
            selected["burst_activity"] = self.graph_client.detect_burst_activity(target_txn_id)

        if risk_score is None or risk_score >= 0.70:
            selected["fraud_ring"] = self.graph_client.detect_fraud_ring(card_id)
        else:
            selected["similar_cases"] = self.graph_client.find_similar_cases(card_id)

        return selected

    def _format_synthesis_markdown(self, bundle: EvidenceBundle) -> str:
        md = [
            f"### Evidence Synthesis for Case `{bundle.case_id}`",
            f"- **Card ID:** `{bundle.card_id}` | **Customer:** `{bundle.customer_id}` | **Flagged Txn:** `{bundle.target_txn_id}`",
            f"- **Trigger:** {bundle.trigger_text}\n",
            "#### 1. Graph Pattern Signals (TigerGraph Live Execution):"
        ]

        if bundle.graph_patterns:
            for pname, pres in bundle.graph_patterns.items():
                md.append(f"- **{pres.pattern_name}** | Confidence: `{pres.confidence_score:.2f}` | Risk: `{pres.risk_indicator.upper()}` | Details: {str(pres.details)[:300]}")
        else:
            md.append("- No active graph signals triggered.")

        md.append("\n#### 2. Top Historical Case Precedents (Vector RAG):")
        for c in bundle.case_precedents:
            meta = c.get("metadata", {})
            md.append(f"- **Case {meta.get('case_id')}** ({meta.get('outcome')}, pattern: `{meta.get('pattern')}`): {meta.get('analyst_notes', '')[:160]}...")

        md.append("\n#### 3. Governing Policy Rules & Regulatory Citations:")
        for p in bundle.applicable_policies:
            md.append(f"- **{p['title']}:** {p['content'][:500]}")
        for r in bundle.regulatory_citations:
            md.append(f"- **{r['title']}:** {r['content'][:350]}")

        return "\n".join(md)
