"""Executable action and approval policy for the HHGOA case contract."""
from __future__ import annotations

from dataclasses import dataclass

from agent.models import ActionType, ApprovalRoute, InvestigationVerdict


class PolicyViolation(ValueError):
    """Raised when a recommendation requests an invalid approval route."""


@dataclass(frozen=True)
class PolicyDecision:
    action: ActionType
    route: ApprovalRoute
    executable: bool
    reason: str


@dataclass(frozen=True)
class PolicyContext:
    verdict: InvestigationVerdict
    fraud_probability: float
    exposure_usd: float = 0.0
    pattern: str = "none"
    shared_origin: bool = False
    connected_fraud: bool = False
    undocumented_pattern: bool = False
    customer_denied: bool = False
    customer_confirmed: bool = False
    evidence_requested: bool = False
    confirmed_card_count: int = 0
    credentials_compromised: bool = False


_AUTO_ACTIONS = {
    ActionType.ALLOW_TRANSACTION,
    ActionType.MONITOR_CARD,
    ActionType.MONITOR_CONNECTED_CARDS,
    ActionType.WARN_CUSTOMER,
    ActionType.VERIFY_WITH_CUSTOMER,
    ActionType.STEP_UP_AUTH,
    ActionType.GENERATE_REPORT,
    ActionType.CREATE_CASE,
    ActionType.ESCALATE_TO_ANALYST,
    ActionType.CLOSE_NO_FRAUD,
}


def required_route(action: ActionType, exposure_usd: float = 0.0) -> ApprovalRoute:
    """Return the mandatory dataset-policy route for an action."""
    if action in _AUTO_ACTIONS:
        return ApprovalRoute.AUTO
    if action is ActionType.DECLINE_TRANSACTION:
        return ApprovalRoute.L1
    if action is ActionType.BLOCK_CARD:
        return ApprovalRoute.L1 if exposure_usd <= 2500 else ApprovalRoute.L2
    if action in {ActionType.BLOCK_ALL_CARDS, ActionType.FILE_REPORT}:
        return ApprovalRoute.L2
    raise PolicyViolation(f"Unsupported action: {action}")


def validate_recommendation(
    action: ActionType,
    route: ApprovalRoute,
    exposure_usd: float = 0.0,
) -> PolicyDecision:
    """Validate a recommendation and state whether the agent may execute it."""
    mandatory_route = required_route(action, exposure_usd)
    if route is not mandatory_route:
        raise PolicyViolation(
            f"{action.value} requires route {mandatory_route.value}, got {route.value}"
        )
    return PolicyDecision(
        action=action,
        route=mandatory_route,
        executable=mandatory_route is ApprovalRoute.AUTO,
        reason=f"Policy route for {action.value}: {mandatory_route.value}",
    )


class PolicyEngine:
    """Authoritative action eligibility and approval-route enforcement."""

    def check(self, action: ActionType, context: PolicyContext) -> PolicyDecision:
        if action is ActionType.CREATE_CASE:
            if not (
                context.fraud_probability >= 0.30
                or context.evidence_requested
                or context.customer_denied
            ):
                raise PolicyViolation("CREATE_CASE requires probability >= 0.30, requested evidence, or a customer dispute")

        if action is ActionType.FILE_REPORT:
            report_triggered = (
                context.exposure_usd > 1000
                or context.shared_origin
                or context.connected_fraud
                or context.undocumented_pattern
            )
            strongly_suspected = (
                context.verdict is InvestigationVerdict.FRAUD
                or context.fraud_probability >= 0.70
            )
            if not (strongly_suspected and report_triggered):
                raise PolicyViolation("FILE_REPORT requires strong suspicion and a policy reporting trigger")

        if action is ActionType.BLOCK_CARD:
            weak_single_signal = (
                context.fraud_probability < 0.70
                and not context.customer_denied
                and context.pattern == "none"
            )
            if weak_single_signal:
                raise PolicyViolation("BLOCK_CARD is prohibited for a weak single signal under R1")

        if action is ActionType.BLOCK_ALL_CARDS:
            if context.confirmed_card_count < 2 and not context.credentials_compromised:
                raise PolicyViolation("BLOCK_ALL_CARDS requires two confirmed cards or compromised credentials")

        if action is ActionType.CLOSE_NO_FRAUD:
            settled_legitimate = (
                context.customer_confirmed
                or (
                    context.verdict is InvestigationVerdict.LEGITIMATE
                    and context.fraud_probability <= 0.15
                )
            )
            if not settled_legitimate:
                raise PolicyViolation("CLOSE_NO_FRAUD requires customer confirmation or a settled low-risk verdict")

        route = required_route(action, context.exposure_usd)
        return PolicyDecision(
            action=action,
            route=route,
            executable=route is ApprovalRoute.AUTO,
            reason=f"Policy check passed for {action.value}; route={route.value}",
        )
