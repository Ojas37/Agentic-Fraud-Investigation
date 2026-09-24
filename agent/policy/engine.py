"""Executable action and approval policy for the HHGOA case contract."""
from __future__ import annotations

from dataclasses import dataclass

from agent.models import ActionType, ApprovalRoute


class PolicyViolation(ValueError):
    """Raised when a recommendation requests an invalid approval route."""


@dataclass(frozen=True)
class PolicyDecision:
    action: ActionType
    route: ApprovalRoute
    executable: bool
    reason: str


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
