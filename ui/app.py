"""Streamlit analyst dashboard for the HHGOA fraud investigation agent."""
from __future__ import annotations

import streamlit as st

from agent.models import InvestigationTrigger, TriggerSource
from agent.orchestrator import run_investigation


st.set_page_config(
    page_title="Fraud Investigation Desk",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .stApp { background: #f5f7f8; }
    [data-testid="stSidebar"] { background: #102a2e; }
    [data-testid="stSidebar"] * { color: #f4fbf9; }
    .hero { background: #0f3d3e; color: #f5fffb; padding: 1.5rem 1.8rem; border-radius: 0.35rem; margin-bottom: 1rem; }
    .hero h1 { margin: 0; font-size: 2rem; letter-spacing: 0; }
    .hero p { margin: 0.45rem 0 0; color: #b9d8d0; }
    .metric { background: white; border-left: 4px solid #e28b3f; padding: 0.85rem 1rem; border-radius: 0.25rem; min-height: 5.5rem; }
    .metric-label { color: #557174; font-size: 0.78rem; text-transform: uppercase; }
    .metric-value { color: #102a2e; font-size: 1.45rem; font-weight: 700; margin-top: 0.25rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


def render_action(action):
    route = action.approval_route.value
    state = "Executed" if action.executed else f"Approval: {route}"
    st.markdown(f"**{action.action_type.value}** · `{state}`")
    st.caption(action.rationale)


def render_case(case):
    assessment = case.risk_level.value.upper() if case.risk_level else "UNKNOWN"
    probability = f"{case.confidence:.0%}" if case.confidence is not None else "n/a"
    pattern = case.pattern_matches[0].pattern_name if case.pattern_matches else "none"

    metrics = st.columns(4)
    for column, label, value in zip(
        metrics,
        ("Verdict", "Risk", "Fraud probability", "Graph memory"),
        (case.status.value, assessment, probability, "Written" if case.written_to_graph else "Not written"),
    ):
        column.markdown(
            f'<div class="metric"><div class="metric-label">{label}</div>'
            f'<div class="metric-value">{value}</div></div>',
            unsafe_allow_html=True,
        )

    st.subheader("Investigation summary")
    st.write(case.explanation or "No explanation returned.")
    st.caption(f"Primary pattern: {pattern} · Case ID: {case.case_id}")

    left, right = st.columns(2)
    with left:
        st.subheader("Evidence")
        if not case.evidence:
            st.info("No evidence items were returned.")
        for index, item in enumerate(case.evidence, start=1):
            with st.expander(f"{index}. {item.source} · confidence {item.confidence:.0%}"):
                st.write(item.content)
                if item.metadata:
                    st.json(item.metadata)

        st.subheader("Prior cases")
        if case.similar_past_cases:
            st.write(", ".join(case.similar_past_cases))
        else:
            st.caption("No prior case IDs recorded.")

    with right:
        st.subheader("Actions before additional evidence")
        if case.actions_before_extra_evidence:
            for action in case.actions_before_extra_evidence:
                render_action(action)
        else:
            st.caption("No initial actions recorded.")

        st.subheader("Actions after additional evidence")
        if case.actions_after_extra_evidence:
            for action in case.actions_after_extra_evidence:
                render_action(action)
        else:
            st.caption("No second recommendation was required.")

        st.subheader("Evidence requests")
        if case.evidence_requests:
            for request in case.evidence_requests:
                st.info(
                    f"{request.request_type.value} after step {request.asked_after_step}: "
                    f"{request.assumed_response}"
                )
        else:
            st.caption("No additional evidence requested.")

    with st.expander("Audit details"):
        st.write(f"Stop reason: {case.stop_reason or 'not recorded'}")
        st.write(f"SAR required: {'yes' if case.sar_required else 'no'}")
        st.write(f"Graph case ID: {case.graph_case_id or 'not recorded'}")
        st.json(case.model_dump(mode="json"))


st.markdown(
    '<div class="hero"><h1>Fraud Investigation Desk</h1>'
    '<p>Graph-grounded investigation, policy-controlled actions, and auditable case memory.</p></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("New investigation")
    source = st.selectbox(
        "Trigger source",
        options=list(TriggerSource),
        format_func=lambda item: item.value.replace("_", " ").title(),
    )
    transaction_id = st.text_input("Transaction ID", value="3000120")
    risk_score = st.number_input("Risk score", min_value=0.0, max_value=1.0, value=0.90, step=0.01)
    description = st.text_area(
        "Trigger description",
        value="Review the transaction and determine the next best action.",
        height=100,
    )
    card_id = st.text_input("Card ID (optional)", value="")
    customer_id = st.text_input("Customer ID (optional)", value="")
    investigate = st.button("Run investigation", type="primary", use_container_width=True)

if investigate:
    if not transaction_id.strip():
        st.error("A transaction ID is required.")
    else:
        trigger = InvestigationTrigger(
            source=source,
            entity_id=transaction_id.strip(),
            entity_type="transaction",
            risk_score=risk_score if source is TriggerSource.RISK_SCORE else None,
            description=description,
            raw_payload={
                "card_id": card_id.strip(),
                "customer_id": customer_id.strip(),
                "flagged_txn_id": transaction_id.strip(),
            },
        )
        with st.status("Running graph investigation...", expanded=True) as status:
            try:
                st.write("Resolving transaction context, gathering graph evidence, and assessing risk.")
                st.session_state["case"] = run_investigation(trigger)
                status.update(label="Investigation complete", state="complete", expanded=False)
            except Exception as exc:
                status.update(label="Investigation failed", state="error", expanded=True)
                st.exception(exc)

case = st.session_state.get("case")
if case is None:
    st.info("Enter a trigger in the sidebar to begin an investigation.")
else:
    render_case(case)
