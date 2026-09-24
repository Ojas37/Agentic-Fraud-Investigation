from datetime import datetime

from agent.memory.store import CaseMemory
from agent.models import (
    CaseStatus,
    Evidence,
    FraudCase,
    FraudPatternMatch,
    InvestigationTrigger,
    TriggerSource,
)
from rag.vector_store import FraudVectorStore


class RecordingWriter:
    def __init__(self):
        self.written = []

    def write_case(self, case):
        self.written.append(case.case_id)
        return f"GRAPH-{case.case_id}"


def make_case(case_id: str) -> FraudCase:
    case = FraudCase(
        case_id=case_id,
        trigger=InvestigationTrigger(
            source=TriggerSource.RISK_SCORE,
            entity_id="T-1",
            entity_type="transaction",
            description="online card testing sequence",
        ),
        status=CaseStatus.RESOLVED_FRAUD,
        confidence=0.9,
        evidence=[Evidence(
            source="graph",
            content="Three micro authorizations preceded a larger online purchase.",
        )],
        pattern_matches=[FraudPatternMatch(
            pattern_name="card_testing",
            confidence=0.9,
            supporting_evidence=[],
        )],
        explanation="Card testing was confirmed by the transaction sequence.",
    )
    case.updated_at = datetime.utcnow()
    return case


def test_case_memory_writes_graph_and_retrieves_live_case(tmp_path):
    writer = RecordingWriter()
    store = FraudVectorStore(cache_file=str(tmp_path / "memory.pkl"))
    memory = CaseMemory(graph_writer=writer, vector_store=store)

    first = memory.write_case(make_case("CASE-1"))
    matches = memory.retrieve_similar_cases(make_case("CASE-2"))

    assert first.written_to_graph is True
    assert first.case_id == "CASE-1"
    assert first.graph_case_id == "GRAPH-CASE-1"
    assert writer.written == ["CASE-1"]
    assert matches
    assert matches[0]["id"] == "CASE-1"
    assert matches[0]["doc_type"] == "live_case"
