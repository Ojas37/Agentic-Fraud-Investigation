"""Phase 6 investigation workflow.

The graph owns orchestration and state transitions. GraphRAG owns evidence
retrieval, while the reasoner is limited to assessment, action proposals, and
explanation. Policy validation remains deterministic and authoritative.
"""
from __future__ import annotations

from datetime import datetime
from time import perf_counter
from typing import Any, Callable, Protocol

from langgraph.graph import END, StateGraph
from langchain_core.callbacks import UsageMetadataCallbackHandler

from agent.models import (
    ActionDecision,
    ActionProposal,
    AgentState,
    ApprovalRoute,
    CaseStatus,
    Evidence,
    EvidenceRequest,
    EvidenceRequestType,
    FraudCase,
    FraudPatternMatch,
    InvestigationTrigger,
    InvestigationVerdict,
    RecommendedAction,
    RiskAssessment,
    RiskLevel,
)
from agent.policy.engine import PolicyContext, PolicyEngine
from agent.memory.store import CaseMemory, TigerGraphCaseWriter
from rag.evidence_gatherer import EvidenceBundle, GraphRAGEvidenceGatherer


class EvidenceProvider(Protocol):
    def gather_evidence_bundle(self, **kwargs: Any) -> EvidenceBundle:
        ...


class Reasoner(Protocol):
    def assess(self, bundle: EvidenceBundle, state: AgentState) -> RiskAssessment:
        ...

    def decide(
        self,
        assessment: RiskAssessment,
        bundle: EvidenceBundle,
        state: AgentState,
    ) -> ActionDecision:
        ...

    def explain(
        self,
        case: FraudCase,
        assessment: RiskAssessment,
        bundle: EvidenceBundle,
    ) -> str:
        ...


class EvidenceSimulator(Protocol):
    def respond(
        self,
        request_type: EvidenceRequestType,
        trigger: InvestigationTrigger,
    ) -> str:
        ...


class DefaultEvidenceSimulator:
    """Deterministic simulated responses required by the dataset contract."""

    def respond(
        self,
        request_type: EvidenceRequestType,
        trigger: InvestigationTrigger,
    ) -> str:
        if request_type is EvidenceRequestType.CUSTOMER_VALIDATION:
            if trigger.source.value == "customer_report":
                return "Simulated response: the customer report confirms the transaction was unauthorized."
            return "Simulated response: no customer reply within 24 hours."
        if request_type is EvidenceRequestType.STEP_UP_AUTH:
            return "Simulated response: step-up authentication was not completed."
        return "Simulated response: the analyst provided no additional information."


class LangChainReasoner:
    """LLM adapter used by the assessment and action-decision nodes."""

    def __init__(self, model: Any | None = None):
        self.model = model or self._build_model()
        self.input_tokens = 0
        self.output_tokens = 0

    def _invoke(self, runnable: Any, prompt: str) -> Any:
        usage_handler = UsageMetadataCallbackHandler()
        response = runnable.invoke(prompt, config={"callbacks": [usage_handler]})
        for usage in usage_handler.usage_metadata.values():
            self.input_tokens += int(usage.get("input_tokens", 0))
            self.output_tokens += int(usage.get("output_tokens", 0))
        return response

    @staticmethod
    def _build_model() -> Any:
        from agent.config import get_settings

        settings = get_settings()
        provider = settings.llm_provider.lower()
        if provider == "groq":
            from langchain_groq import ChatGroq

            return ChatGroq(model=settings.llm_model, api_key=settings.llm_api_key)
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(model=settings.llm_model, api_key=settings.llm_api_key)
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(model=settings.llm_model, api_key=settings.llm_api_key)
        raise ValueError(f"Unsupported LLM_PROVIDER: {settings.llm_provider}")

    def assess(self, bundle: EvidenceBundle, state: AgentState) -> RiskAssessment:
        structured = self.model.with_structured_output(RiskAssessment)
        response = self._invoke(structured,
            "Assess fraud risk using only this synthesized evidence. Do not invent graph facts. "
            "A risk score is not a verdict. Decide whether more evidence is needed.\n\n"
            f"{bundle.synthesis_markdown}\n\n"
            f"Additional response: {state.extra_evidence_response or 'none'}"
        )
        return response if isinstance(response, RiskAssessment) else RiskAssessment.model_validate(response)

    def decide(
        self,
        assessment: RiskAssessment,
        bundle: EvidenceBundle,
        state: AgentState,
    ) -> ActionDecision:
        structured = self.model.with_structured_output(ActionDecision)
        response = self._invoke(structured,
            "Propose only actions from the exact HHGOA action catalogue. Do not choose approval "
            "routes; the policy engine will assign them. Keep recommendations proportional.\n"
            "Allowed action values: allow_transaction, decline_transaction, monitor_card, "
            "monitor_connected_cards, warn_customer, verify_with_customer, step_up_auth, "
            "block_card, block_all_cards, generate_report, create_case, file_report, "
            "escalate_to_analyst, close_no_fraud. Use these lowercase values exactly.\n\n"
            f"Assessment: {assessment.model_dump_json()}\n"
            f"Evidence: {bundle.synthesis_markdown}\n"
            f"Evidence response: {state.extra_evidence_response or 'none'}"
        )
        return response if isinstance(response, ActionDecision) else ActionDecision.model_validate(response)

    def explain(
        self,
        case: FraudCase,
        assessment: RiskAssessment,
        bundle: EvidenceBundle,
    ) -> str:
        response = self._invoke(self.model,
            "Write a concise audit narrative explaining the trigger, graph/document evidence, "
            "uncertainty, policy rules, actions, and stopping reason. Do not add facts.\n\n"
            f"Assessment: {assessment.model_dump_json()}\n"
            f"Case: {case.model_dump_json()}\n"
            f"Evidence: {bundle.synthesis_markdown}"
        )
        return str(getattr(response, "content", response))


class InvestigationOrchestrator:
    def __init__(
        self,
        evidence_provider: EvidenceProvider,
        reasoner: Reasoner,
        evidence_simulator: EvidenceSimulator | None = None,
        policy_engine: PolicyEngine | None = None,
        case_memory: CaseMemory | None = None,
    ):
        self.evidence_provider = evidence_provider
        self.reasoner = reasoner
        self.evidence_simulator = evidence_simulator or DefaultEvidenceSimulator()
        self.policy_engine = policy_engine or PolicyEngine()
        self.case_memory = case_memory
        self.graph = self._build_graph()

    def invoke(self, trigger: InvestigationTrigger) -> FraudCase:
        started = perf_counter()
        initial = AgentState(trigger=trigger)
        result = self.graph.invoke(initial.model_dump())
        final_state = AgentState.model_validate(result)
        if final_state.case is None:
            raise RuntimeError("Investigation ended without a case")
        metrics = {
            "latency_s": round(perf_counter() - started, 3),
            "tokens": int(getattr(self.reasoner, "input_tokens", 0))
            + int(getattr(self.reasoner, "output_tokens", 0)),
        }
        return final_state.case.model_copy(update=metrics)

    def _build_graph(self):
        workflow = StateGraph(AgentState)
        workflow.add_node("open_or_update_case", self._open_or_update_case)
        workflow.add_node("gather_evidence", self._gather_evidence)
        workflow.add_node("assess", self._assess)
        workflow.add_node("decide_action", self._decide_action)
        workflow.add_node("check_policy_permissions", self._check_policy_permissions)
        workflow.add_node("request_more_evidence", self._request_more_evidence)
        workflow.add_node("explain", self._explain)

        workflow.set_entry_point("open_or_update_case")
        workflow.add_edge("open_or_update_case", "gather_evidence")
        workflow.add_edge("gather_evidence", "assess")
        workflow.add_edge("assess", "decide_action")
        workflow.add_edge("decide_action", "check_policy_permissions")
        workflow.add_conditional_edges(
            "check_policy_permissions",
            self._route_after_decision,
            {
                "request_more_evidence": "request_more_evidence",
                "explain": "explain",
            },
        )
        workflow.add_edge("request_more_evidence", "gather_evidence")
        workflow.add_edge("explain", END)
        return workflow.compile()

    @staticmethod
    def _state(value: dict[str, Any]) -> AgentState:
        return AgentState.model_validate(value)

    def _open_or_update_case(self, value: dict[str, Any]) -> dict[str, Any]:
        state = self._state(value)
        case = state.case or FraudCase(
            trigger=state.trigger,
            status=CaseStatus.IN_PROGRESS,
        )
        case.status = CaseStatus.IN_PROGRESS
        case.updated_at = datetime.utcnow()
        return {"case": case, "current_node": "open_or_update_case"}

    def _gather_evidence(self, value: dict[str, Any]) -> dict[str, Any]:
        state = self._state(value)
        if state.case is None:
            raise RuntimeError("Cannot gather evidence before opening a case")

        payload = state.trigger.raw_payload
        card_id = str(payload.get("card_id", ""))
        customer_id = str(payload.get("customer_id", ""))
        target_txn_id = str(payload.get("flagged_txn_id", state.trigger.entity_id))
        if not card_id and hasattr(self.evidence_provider, "resolve_transaction_context"):
            context = self.evidence_provider.resolve_transaction_context(target_txn_id)
            card_id = context["card_id"]
            customer_id = customer_id or context["customer_id"]
            trigger = state.trigger.model_copy(update={
                "raw_payload": {
                    **state.trigger.raw_payload,
                    "flagged_txn_id": target_txn_id,
                    "card_id": card_id,
                    "customer_id": customer_id,
                }
            })
        else:
            trigger = state.trigger
        bundle = self.evidence_provider.gather_evidence_bundle(
            case_id=state.case.case_id,
            card_id=card_id,
            target_txn_id=target_txn_id,
            customer_id=customer_id,
            trigger_text=state.trigger.description,
            risk_score=state.trigger.risk_score,
        )

        evidence = [self._evidence_from_item(item) for item in bundle.items]
        case = state.case.model_copy(update={
            "trigger": trigger,
            "evidence": evidence,
            "tool_calls": state.case.tool_calls + len(bundle.graph_patterns) + 3,
            "similar_past_cases": [
                str(item.get("metadata", {}).get("case_id"))
                for item in bundle.case_precedents
                if item.get("metadata", {}).get("case_id")
            ],
            "updated_at": datetime.utcnow(),
        })
        return {
            "case": case,
            "evidence_bundle": bundle.model_dump(),
            "iteration_count": state.iteration_count + 1,
            "current_node": "gather_evidence",
        }

    @staticmethod
    def _evidence_from_item(item: Any) -> Evidence:
        source_map = {
            "graph_pattern": "graph",
            "case_precedent": "case_memory",
            "policy_rule": "document",
            "regulatory_guidance": "document",
        }
        return Evidence(
            source=source_map.get(item.category, item.category),
            content=item.summary,
            confidence=item.confidence,
            metadata={"title": item.title, **item.data},
        )

    def _assess(self, value: dict[str, Any]) -> dict[str, Any]:
        state = self._state(value)
        bundle = EvidenceBundle.model_validate(state.evidence_bundle or {})
        assessment = self.reasoner.assess(bundle, state)
        if state.case is None:
            raise RuntimeError("Cannot assess without a case")
        patterns = []
        if assessment.primary_pattern != "none":
            patterns.append(FraudPatternMatch(
                pattern_name=assessment.primary_pattern,
                confidence=assessment.fraud_probability,
                supporting_evidence=[e.evidence_id for e in state.case.evidence],
                description=assessment.rationale,
            ))
        patterns.extend(
            FraudPatternMatch(
                pattern_name=pattern,
                confidence=assessment.fraud_probability,
                supporting_evidence=[e.evidence_id for e in state.case.evidence],
            )
            for pattern in assessment.secondary_patterns
        )
        case = state.case.model_copy(update={
            "risk_level": assessment.risk_level,
            "confidence": assessment.fraud_probability,
            "pattern_matches": patterns,
            "updated_at": datetime.utcnow(),
        })
        return {"case": case, "assessment": assessment, "current_node": "assess"}

    def _decide_action(self, value: dict[str, Any]) -> dict[str, Any]:
        state = self._state(value)
        if state.case is None or state.assessment is None:
            raise RuntimeError("Cannot decide without case assessment")
        bundle = EvidenceBundle.model_validate(state.evidence_bundle or {})
        decision = self.reasoner.decide(state.assessment, bundle, state)
        return {"action_decision": decision, "current_node": "decide_action"}

    def _check_policy_permissions(self, value: dict[str, Any]) -> dict[str, Any]:
        state = self._state(value)
        if state.case is None or state.assessment is None or state.action_decision is None:
            raise RuntimeError("Cannot check policy without a case decision")

        response = state.extra_evidence_response.lower()
        pattern_names = {match.pattern_name for match in state.case.pattern_matches}
        context = PolicyContext(
            verdict=state.assessment.verdict,
            fraud_probability=state.assessment.fraud_probability,
            exposure_usd=state.assessment.exposure_usd,
            pattern=state.assessment.primary_pattern,
            shared_origin=bool(pattern_names & {"fraud_ring", "cnp_new_device", "shared_origin"}),
            connected_fraud="confirmed fraud" in response,
            undocumented_pattern=state.assessment.primary_pattern == "undocumented",
            customer_denied=any(term in response for term in ("unauthorized", "did not", "denied")),
            customer_confirmed=any(term in response for term in ("authorized", "made the transaction")),
            evidence_requested=bool(state.evidence_requests),
            confirmed_card_count=1 + len({match.pattern_name for match in state.case.pattern_matches if match.pattern_name == "fraud_ring"}),
            credentials_compromised="credentials" in response and "compromised" in response,
        )

        actions = []
        for proposal in state.action_decision.proposals:
            policy = self.policy_engine.check(proposal.action_type, context)
            actions.append(RecommendedAction(
                action_type=proposal.action_type,
                approval_route=policy.route,
                rationale=proposal.rationale,
                executed=policy.executable,
                execution_log="mock_auto_execute" if policy.executable else "awaiting_human_approval",
            ))

        case_update = {
            "sar_required": state.action_decision.sar_required,
            "updated_at": datetime.utcnow(),
        }
        if state.extra_evidence_requested:
            case_update["actions_after_extra_evidence"] = actions
        else:
            case_update["actions_before_extra_evidence"] = actions
        return {
            "case": state.case.model_copy(update=case_update),
            "current_node": "check_policy_permissions",
        }

    @staticmethod
    def _route_after_decision(value: dict[str, Any]) -> str:
        state = AgentState.model_validate(value)
        if (
            state.assessment
            and state.assessment.needs_more_evidence
            and not state.extra_evidence_requested
            and state.iteration_count < state.max_iterations
        ):
            return "request_more_evidence"
        return "explain"

    def _request_more_evidence(self, value: dict[str, Any]) -> dict[str, Any]:
        state = self._state(value)
        if state.assessment is None:
            raise RuntimeError("Cannot request evidence without an assessment")
        request_type = state.assessment.evidence_request_type or EvidenceRequestType.CUSTOMER_VALIDATION
        request = EvidenceRequest(
            request_type=request_type,
            asked_after_step=state.iteration_count,
            assumed_response=self.evidence_simulator.respond(request_type, state.trigger),
        )
        return {
            "evidence_requests": [*state.evidence_requests, request],
            "extra_evidence_requested": True,
            "extra_evidence_received": True,
            "extra_evidence_response": request.assumed_response,
            "case": state.case.model_copy(update={"status": CaseStatus.AWAITING_EVIDENCE}),
            "current_node": "request_more_evidence",
        }

    def _explain(self, value: dict[str, Any]) -> dict[str, Any]:
        state = self._state(value)
        if state.case is None or state.assessment is None:
            raise RuntimeError("Cannot explain without a completed assessment")
        bundle = EvidenceBundle.model_validate(state.evidence_bundle or {})
        status = {
            InvestigationVerdict.FRAUD: CaseStatus.RESOLVED_FRAUD,
            InvestigationVerdict.LEGITIMATE: CaseStatus.RESOLVED_CLEARED,
            InvestigationVerdict.UNCERTAIN: CaseStatus.ESCALATED,
        }[state.assessment.verdict]
        stop_reason = (
            state.action_decision.stop_reason
            if state.action_decision and state.action_decision.stop_reason
            else "Assessment completed with no further evidence step selected."
        )
        case = state.case.model_copy(update={
            "status": status,
            "explanation": self._build_explanation(state.case, state.assessment),
            "evidence_requests": state.evidence_requests,
            "stop_reason": stop_reason,
            "updated_at": datetime.utcnow(),
        })
        if self.case_memory is not None:
            case = self.case_memory.write_case(case)
        return {"case": case, "stop_reason": stop_reason, "current_node": "explain"}

    @staticmethod
    def _build_explanation(case: FraudCase, assessment: RiskAssessment) -> str:
        """Build the audit explanation deterministically after the LLM decisions."""
        patterns = ", ".join(match.pattern_name for match in case.pattern_matches) or "no confirmed pattern"
        return (
            f"Assessment: {assessment.verdict.value} with fraud probability "
            f"{assessment.fraud_probability:.2f}. Primary signals: {patterns}. "
            f"Rationale: {assessment.rationale}"
        )


def build_investigation_graph(
    evidence_provider: EvidenceProvider | None = None,
    reasoner: Reasoner | None = None,
    evidence_simulator: EvidenceSimulator | None = None,
    case_memory: CaseMemory | None = None,
) -> InvestigationOrchestrator:
    """Build the production graph, with injectable dependencies for tests."""
    provider = evidence_provider or GraphRAGEvidenceGatherer()
    selected_reasoner = reasoner or LangChainReasoner()
    selected_memory = case_memory
    if selected_memory is None:
        graph_client = getattr(provider, "graph_client", None)
        writer = TigerGraphCaseWriter(graph_client=graph_client) if graph_client is not None else None
        selected_memory = CaseMemory(graph_writer=writer)
    return InvestigationOrchestrator(
        provider,
        selected_reasoner,
        evidence_simulator,
        case_memory=selected_memory,
    )


def run_investigation(trigger: InvestigationTrigger) -> FraudCase:
    """Run one investigation using configured production dependencies."""
    return build_investigation_graph().invoke(trigger)
