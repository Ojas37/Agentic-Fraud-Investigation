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
    BLOCK_TRANSACTION = "block_transaction"
    BLOCK_ACCOUNT = "block_account"
    MONITOR_ACCOUNT = "monitor_account"
    WARN_CUSTOMER = "warn_customer"
    REQUEST_VALIDATION = "request_validation"
    REQUEST_STEP_UP_AUTH = "request_step_up_auth"
    REQUEST_ANALYST_INFO = "request_analyst_info"
    CREATE_CASE = "create_case"
    FILE_SAR = "file_sar"
    ESCALATE_TO_ANALYST = "escalate_to_analyst"
    CLOSE_CASE = "close_case"


class ApprovalRoute(str, Enum):
    AUTO_EXECUTE = "auto_execute"           # agent executes directly
    RECOMMEND_ONLY = "recommend_only"       # agent recommends; human decides
    REQUIRES_HUMAN_APPROVAL = "requires_human_approval"  # must wait for approval
    REQUIRES_SENIOR_APPROVAL = "requires_senior_approval"


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
    current_node: str = "trigger"
    iteration_count: int = 0
    max_iterations: int = 10          # circuit-breaker
    extra_evidence_requested: bool = False
    extra_evidence_received: bool = False
    stop_reason: str = ""
    error: str | None = None
