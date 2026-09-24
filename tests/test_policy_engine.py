import pytest

from agent.models import ActionType, ApprovalRoute, InvestigationVerdict
from agent.policy.engine import PolicyContext, PolicyEngine, PolicyViolation, validate_recommendation


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


def test_policy_rejects_block_on_weak_single_signal():
    context = PolicyContext(
        verdict=InvestigationVerdict.UNCERTAIN,
        fraud_probability=0.55,
    )
    with pytest.raises(PolicyViolation):
        PolicyEngine().check(ActionType.BLOCK_CARD, context)


def test_policy_requires_reporting_trigger():
    context = PolicyContext(
        verdict=InvestigationVerdict.FRAUD,
        fraud_probability=0.90,
        shared_origin=True,
    )
    decision = PolicyEngine().check(ActionType.FILE_REPORT, context)
    assert decision.route is ApprovalRoute.L2
    assert decision.executable is False


def test_policy_protects_block_all_cards():
    context = PolicyContext(
        verdict=InvestigationVerdict.FRAUD,
        fraud_probability=0.95,
        confirmed_card_count=1,
    )
    with pytest.raises(PolicyViolation):
        PolicyEngine().check(ActionType.BLOCK_ALL_CARDS, context)
