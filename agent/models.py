"""
agent/models.py — Shared Pydantic data models used across all agent nodes.

These are placeholders/shells; field definitions will be fleshed out in
Phase 1 once the real dataset schema and answer-format spec are received.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


# ─── Enumerations ─────────────────────────────────────────────────────────────

class TriggerSource(str, Enum):
    RISK_SCORE = "risk_score"
    CUSTOMER_REPORT = "customer_report"
    ANALYST_REQUEST = "analyst_request"
    SYSTEM_EVENT = "system_event"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    AWAITING_EVIDENCE = "awaiting_evidence"
    AWAITING_APPROVAL = "awaiting_approval"
    RESOLVED_FRAUD = "resolved_fraud"
    RESOLVED_CLEARED = "resolved_cleared"
    ESCALATED = "escalated"


class ActionType(str, Enum):
    ALLOW_TRANSACTION = "allow_transaction"
    DECLINE_TRANSACTION = "decline_transaction"
    MONITOR_CARD = "monitor_card"
    MONITOR_CONNECTED_CARDS = "monitor_connected_cards"
    WARN_CUSTOMER = "warn_customer"
    VERIFY_WITH_CUSTOMER = "verify_with_customer"
    STEP_UP_AUTH = "step_up_auth"
    BLOCK_CARD = "block_card"
    BLOCK_ALL_CARDS = "block_all_cards"
    GENERATE_REPORT = "generate_report"
    CREATE_CASE = "create_case"
    FILE_REPORT = "file_report"
    ESCALATE_TO_ANALYST = "escalate_to_analyst"
    CLOSE_NO_FRAUD = "close_no_fraud"


class ApprovalRoute(str, Enum):
    AUTO = "auto"
    L1 = "L1"
    L2 = "L2"


class EvidenceRequestType(str, Enum):
    CUSTOMER_VALIDATION = "customer_validation"
    STEP_UP_AUTH = "step_up_auth"
    ANALYST_INFO = "analyst_info"


class InvestigationVerdict(str, Enum):
    FRAUD = "fraud"
    LEGITIMATE = "legitimate"
    UNCERTAIN = "uncertain"


# ─── Core Models ──────────────────────────────────────────────────────────────

class InvestigationTrigger(BaseModel):
    trigger_id: str = Field(default_factory=lambda: str(uuid4()))
    source: TriggerSource
    entity_id: str                    # transaction_id, account_id, or customer_id
    entity_type: str                  # "transaction" | "account" | "customer"
    risk_score: float | None = None   # bank model score if available
    description: str = ""
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    source: str                       # e.g. "graph_query", "document_rag", "case_memory"
    content: str                      # synthesised text (NOT raw rows)
    confidence: float = 1.0           # 0‒1
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FraudPatternMatch(BaseModel):
    pattern_name: str
    confidence: float                 # 0‒1
    supporting_evidence: list[str]    # evidence_ids
    description: str = ""


class RecommendedAction(BaseModel):
    action_type: ActionType
    approval_route: ApprovalRoute
    rationale: str
    executed: bool = False
    execution_log: str = ""
    recorded_at: datetime = Field(default_factory=datetime.utcnow)


class EvidenceRequest(BaseModel):
    request_type: EvidenceRequestType
    asked_after_step: int
    assumed_response: str


class RiskAssessment(BaseModel):
    verdict: InvestigationVerdict
    fraud_probability: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    primary_pattern: str = "none"
    secondary_patterns: list[str] = Field(default_factory=list)
    top_signals: list[str] = Field(default_factory=list)
    exposure_usd: float = Field(default=0.0, ge=0.0)
    needs_more_evidence: bool = False
    evidence_request_type: EvidenceRequestType | None = None
    rationale: str = ""


class ActionProposal(BaseModel):
    action_type: ActionType
    rationale: str


class ActionDecision(BaseModel):
    proposals: list[ActionProposal] = Field(default_factory=list)
    sar_required: bool = False
    sar_reason: str = ""
    stop_reason: str = ""


class FraudCase(BaseModel):
    case_id: str = Field(default_factory=lambda: str(uuid4()))
    trigger: InvestigationTrigger
    status: CaseStatus = CaseStatus.OPEN
    risk_level: RiskLevel | None = None
    confidence: float | None = None   # overall assessment confidence
    evidence: list[Evidence] = Field(default_factory=list)
    pattern_matches: list[FraudPatternMatch] = Field(default_factory=list)
    actions_before_extra_evidence: list[RecommendedAction] = Field(default_factory=list)
    actions_after_extra_evidence: list[RecommendedAction] = Field(default_factory=list)
    explanation: str = ""
    sar_required: bool = False
    sar_report: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    written_to_graph: bool = False
    similar_past_cases: list[str] = Field(default_factory=list)  # case_ids


class AgentState(BaseModel):
    """LangGraph state — passed between all nodes."""
    trigger: InvestigationTrigger
    case: FraudCase | None = None
    evidence_bundle: dict[str, Any] | None = None
    assessment: RiskAssessment | None = None
    action_decision: ActionDecision | None = None
    evidence_requests: list[EvidenceRequest] = Field(default_factory=list)
    extra_evidence_response: str = ""
    current_node: str = "trigger"
    iteration_count: int = 0
    max_iterations: int = 10          # circuit-breaker
    extra_evidence_requested: bool = False
    extra_evidence_received: bool = False
    stop_reason: str = ""
    error: str | None = None
