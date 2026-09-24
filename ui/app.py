"""Streamlit analyst dashboard for the HHGOA fraud investigation agent."""
from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

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
    :root {
        --bg: #eef3f4;
        --panel: #ffffff;
        --panel-soft: #f6f9fa;
        --panel-strong: #eaf1f3;
        --sidebar-bg: #0a2028;
        --sidebar-panel: rgba(255, 255, 255, 0.04);
        --primary: #0f5e68;
        --primary-strong: #0c4950;
        --primary-soft: #dff5f3;
        --accent: #ea7d40;
        --accent-soft: #fff0e8;
        --text: #122a2f;
        --muted: #5f7277;
        --border: rgba(12, 42, 48, 0.08);
        --success: #1d7a62;
        --shadow: 0 10px 30px rgba(15, 35, 42, 0.08);
        --radius-xl: 22px;
        --radius-lg: 18px;
        --radius-md: 12px;
    }

    html, body, .stApp {
        background: var(--bg) !important;
        color: var(--text) !important;
        font-family: "Inter", "Segoe UI", sans-serif;
    }

    [data-testid="stAppViewContainer"] {
        background: linear-gradient(180deg, #edf3f4 0%, #f4f7f8 100%);
    }

    [data-testid="stAppViewContainer"] .main {
        background: transparent;
    }

    [data-testid="stAppViewContainer"] .block-container {
        max-width: 1480px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    [data-testid="stAppViewContainer"] h1,
    [data-testid="stAppViewContainer"] h2,
    [data-testid="stAppViewContainer"] h3,
    [data-testid="stAppViewContainer"] h4,
    [data-testid="stAppViewContainer"] p,
    [data-testid="stAppViewContainer"] li,
    [data-testid="stAppViewContainer"] label,
    [data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"],
    [data-testid="stAppViewContainer"] [data-testid="stMarkdownContainer"],
    [data-testid="stAppViewContainer"] [data-testid="stExpander"] summary,
    [data-testid="stAppViewContainer"] [data-testid="stAlert"],
    [data-testid="stAppViewContainer"] [data-testid="stStatusWidget"],
    [data-testid="stAppViewContainer"] .stTabs [role="tablist"] button {
        color: var(--text) !important;
    }

    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--sidebar-bg) 0%, #102d36 100%);
        border-right: 1px solid rgba(255,255,255,0.06);
        box-shadow: inset -1px 0 0 rgba(255,255,255,0.03);
    }

    [data-testid="stSidebar"] > div {
        padding-top: 1.1rem;
    }

    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] li,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
        color: #edf7f5 !important;
    }

    [data-testid="stSidebar"] .stTextInput > div,
    [data-testid="stSidebar"] .stNumberInput > div,
    [data-testid="stSidebar"] .stTextArea > div,
    [data-testid="stSidebar"] .stSelectbox > div {
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        overflow: hidden;
    }

    [data-testid="stSidebar"] input,
    [data-testid="stSidebar"] textarea,
    [data-testid="stSidebar"] [data-baseweb="select"] {
        color: #ffffff !important;
        background: rgba(255,255,255,0.02) !important;
        border: none !important;
        border-radius: 14px !important;
        font-size: 1rem;
    }

    [data-testid="stSidebar"] input::placeholder,
    [data-testid="stSidebar"] textarea::placeholder {
        color: rgba(237, 247, 245, 0.6) !important;
    }

    [data-testid="stSidebar"] .stButton > button {
        width: 100%;
        border: none;
        border-radius: 14px;
        padding: 0.8rem 1rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        background: linear-gradient(135deg, #7ecfbd 0%, #5eb9a5 100%);
        color: #0b1d20 !important;
        box-shadow: 0 10px 20px rgba(94, 185, 165, 0.22);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }

    [data-testid="stSidebar"] .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 12px 24px rgba(94, 185, 165, 0.28);
    }

    [data-testid="stSidebar"] .stButton > button:focus {
        box-shadow: 0 0 0 3px rgba(126, 207, 189, 0.3);
    }

    .hero {
        background: linear-gradient(135deg, #0f3d3e 0%, #0d5963 100%);
        color: #f4feff;
        border-radius: var(--radius-xl);
        padding: 2rem 2rem 1.75rem;
        margin: 0 0 1.5rem;
        box-shadow: var(--shadow);
        border: 1px solid rgba(255,255,255,0.06);
    }

    .hero h1 {
        margin: 0;
        font-size: clamp(2.1rem, 3vw, 3rem);
        line-height: 1.1;
        letter-spacing: -0.04em;
        color: #f6ffff !important;
        font-weight: 800;
    }

    .hero p {
        margin: 0.8rem 0 0;
        color: rgba(245,255,255,0.8) !important;
        font-size: 1.08rem;
        line-height: 1.6;
    }

    .metric {
        background: linear-gradient(180deg, #ffffff 0%, #f9fbfb 100%);
        border: 1px solid var(--border);
        border-left: 5px solid var(--accent);
        border-radius: var(--radius-lg);
        padding: 1rem 1rem 0.9rem;
        min-height: 116px;
        box-shadow: var(--shadow);
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }

    .metric-value {
        color: var(--text);
        font-size: clamp(1.2rem, 2vw, 1.8rem);
        font-weight: 800;
        letter-spacing: -0.04em;
        margin-top: 0.5rem;
    }

    [data-testid="stAppViewContainer"] .stSubheader {
        margin-top: 1.8rem;
        margin-bottom: 0.9rem;
        color: var(--text) !important;
        font-weight: 800;
        letter-spacing: -0.03em;
        font-size: 1.15rem;
    }

    [data-testid="stAppViewContainer"] h3 {
        margin-top: 1.6rem !important;
        margin-bottom: 0.8rem !important;
        letter-spacing: -0.025em;
    }

    [data-testid="stAppViewContainer"] [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stAppViewContainer"] [data-testid="stHorizontalBlockBorderWrapper"],
    [data-testid="stAppViewContainer"] [data-testid="stVerticalBlock"] > div,
    [data-testid="stAppViewContainer"] [data-testid="stHorizontalBlock"] > div {
        border-radius: 16px;
    }

    [data-testid="stAppViewContainer"] .stAlert,
    [data-testid="stAppViewContainer"] .stInfo,
    [data-testid="stAppViewContainer"] .stSuccess,
    [data-testid="stAppViewContainer"] .stWarning,
    [data-testid="stAppViewContainer"] .stError {
        border-radius: 14px;
        border: 1px solid rgba(17, 29, 33, 0.07);
        box-shadow: none;
        padding: 0.9rem 1rem;
    }

    [data-testid="stAppViewContainer"] [data-testid="stExpander"] {
        border: 1px solid var(--border);
        border-radius: 14px;
        background: rgba(255,255,255,0.42);
        box-shadow: 0 4px 18px rgba(15, 35, 42, 0.04);
        overflow: hidden;
    }

    [data-testid="stAppViewContainer"] [data-testid="stExpander"] summary {
        font-weight: 700;
        padding: 0.8rem 0.9rem;
        border-bottom: 1px solid rgba(17, 29, 33, 0.04);
    }

    [data-testid="stAppViewContainer"] [data-testid="stExpander"] .streamlit-expanderContent {
        padding: 0.8rem 0.9rem 0.9rem;
    }

    [data-testid="stAppViewContainer"] .stMarkdown {
        line-height: 1.75;
    }

    [data-testid="stAppViewContainer"] .stMarkdown p {
        margin-top: 0.2rem;
        margin-bottom: 0.75rem;
    }

    [data-testid="stAppViewContainer"] .stMarkdown ul,
    [data-testid="stAppViewContainer"] .stMarkdown ol {
        padding-left: 1.4rem;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
    }

    [data-testid="stAppViewContainer"] .stMarkdown strong {
        color: var(--text);
    }

    .metric {
        background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(247,250,250,0.96) 100%);
        border: 1px solid rgba(18, 42, 47, 0.08);
        border-left: 5px solid var(--accent);
        border-radius: 18px;
        padding: 1rem 1rem 0.95rem;
        min-height: 118px;
        box-shadow: 0 18px 28px rgba(15, 35, 42, 0.05);
        transition: transform 0.18s ease, box-shadow 0.18s ease;
    }

    .metric:hover {
        transform: translateY(-2px);
        box-shadow: 0 20px 30px rgba(15, 35, 42, 0.08);
    }

    .metric-label {
        color: var(--muted);
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.12em;
        text-transform: uppercase;
    }

    .metric-value {
        color: var(--text);
        font-size: clamp(1.25rem, 1.7vw, 1.8rem);
        font-weight: 800;
        letter-spacing: -0.04em;
        margin-top: 0.52rem;
    }

    @media (max-width: 768px) {
        [data-testid="stAppViewContainer"] .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1rem;
        }

        [data-testid="stSidebar"] {
            width: 100% !important;
            min-width: 100% !important;
        }

        .hero {
            padding: 1.4rem 1.2rem 1.2rem;
            border-radius: 18px;
        }

        .metric {
            min-height: 90px;
            margin-bottom: 0.6rem;
        }
    }
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
