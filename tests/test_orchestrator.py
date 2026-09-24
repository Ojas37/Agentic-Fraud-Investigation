from agent.models import (
    ActionDecision,
    ActionProposal,
    EvidenceRequestType,
    InvestigationTrigger,
    InvestigationVerdict,
    RiskLevel,
    RiskAssessment,
    TriggerSource,
)
from agent.orchestrator import InvestigationOrchestrator
from rag.evidence_gatherer import EvidenceBundle, EvidenceItem


class FakeEvidenceProvider:
    def gather_evidence_bundle(self, **kwargs):
        return EvidenceBundle(
            case_id=kwargs["case_id"],
            card_id=kwargs["card_id"],
            target_txn_id=kwargs["target_txn_id"],
            customer_id=kwargs["customer_id"],
            trigger_text=kwargs["trigger_text"],
            items=[EvidenceItem(
                category="graph_pattern",
                title="Graph Signal: card_testing",
                confidence=0.8,
                summary="Three small authorizations preceded the flagged transaction.",
                data={"rule_ref": "R5"},
            )],
            synthesis_markdown="Card testing evidence from TigerGraph.",
        )


class FakeReasoner:
    def __init__(self):
        self.assessment_count = 0

    def assess(self, bundle, state):
        self.assessment_count += 1
        if self.assessment_count == 1:
            return RiskAssessment(
                verdict=InvestigationVerdict.UNCERTAIN,
                fraud_probability=0.55,
                risk_level=RiskLevel.MEDIUM,
                primary_pattern="card_testing",
                exposure_usd=120.0,
                needs_more_evidence=True,
                evidence_request_type=EvidenceRequestType.CUSTOMER_VALIDATION,
                rationale="The graph signal is strong but needs customer confirmation.",
            )
        return RiskAssessment(
            verdict=InvestigationVerdict.FRAUD,
            fraud_probability=0.9,
            risk_level=RiskLevel.HIGH,
            primary_pattern="card_testing",
            exposure_usd=120.0,
            rationale="The simulated customer response confirms unauthorized use.",
        )

    def decide(self, assessment, bundle, state):
        if not state.extra_evidence_requested:
            return ActionDecision(proposals=[
                ActionProposal(
                    action_type="verify_with_customer",
                    rationale="R1: verify a medium-confidence signal before blocking.",
                )
            ])
        return ActionDecision(
            proposals=[
                ActionProposal(
                    action_type="block_card",
                    rationale="R2/R5: the customer validation supports unauthorized use.",
                ),
                ActionProposal(
                    action_type="create_case",
                    rationale="A case is required for the investigation record.",
                ),
            ],
            stop_reason="Customer validation settled the assessment.",
        )

    def explain(self, case, assessment, bundle):
        return "The case was reassessed after simulated customer validation."


def test_investigation_reassesses_after_extra_evidence():
    trigger = InvestigationTrigger(
        source=TriggerSource.RISK_SCORE,
        entity_id="T-100",
        entity_type="transaction",
        risk_score=0.7,
        description="Model alert",
        raw_payload={
            "case_id": "HHG-TEST",
            "card_id": "C-1-K1",
            "customer_id": "C-1",
        },
    )
    reasoner = FakeReasoner()
    orchestrator = InvestigationOrchestrator(FakeEvidenceProvider(), reasoner)

    case = orchestrator.invoke(trigger)

    assert case.status.value == "resolved_fraud"
    assert len(case.actions_before_extra_evidence) == 1
    assert case.actions_before_extra_evidence[0].action_type.value == "verify_with_customer"
    assert case.actions_before_extra_evidence[0].approval_route.value == "auto"
    assert len(case.actions_after_extra_evidence) == 2
    assert case.actions_after_extra_evidence[0].action_type.value == "block_card"
    assert case.actions_after_extra_evidence[0].approval_route.value == "L1"
    assert case.actions_after_extra_evidence[1].action_type.value == "create_case"
    assert reasoner.assessment_count == 2
