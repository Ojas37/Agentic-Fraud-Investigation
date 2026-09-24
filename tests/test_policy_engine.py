import pytest

from agent.models import ActionType, ApprovalRoute
from agent.policy.engine import PolicyViolation, validate_recommendation


def test_auto_action_is_executable():
    decision = validate_recommendation(
        ActionType.CREATE_CASE,
        ApprovalRoute.AUTO,
    )
    assert decision.executable is True


def test_block_card_route_depends_on_exposure():
    low = validate_recommendation(
        ActionType.BLOCK_CARD,
        ApprovalRoute.L1,
        exposure_usd=2500,
    )
    high = validate_recommendation(
        ActionType.BLOCK_CARD,
        ApprovalRoute.L2,
        exposure_usd=2500.01,
    )
    assert low.executable is False
    assert high.route is ApprovalRoute.L2


def test_invalid_route_is_rejected():
    with pytest.raises(PolicyViolation):
        validate_recommendation(ActionType.FILE_REPORT, ApprovalRoute.AUTO)
