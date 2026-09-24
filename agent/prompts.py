"""
agent/prompts.py — LLM prompt templates for the HHGOA fraud investigation agent.

Design principles:
  - All factual pattern detection is done by GSQL graph queries (not the LLM).
  - The LLM only: interprets graph results, synthesises a narrative, decides on
    policy actions, drafts the SAR, and produces the human-readable explanation.
  - Prompts are deliberate about not over-blocking (≈50% legitimate cases).
"""
from __future__ import annotations

SYSTEM_FRAUD_ANALYST = """\
You are a senior fraud investigator AI at a financial institution.
You have deep expertise in card fraud, anti-money-laundering (AML), BSA/SAR requirements,
and dispute regulations (NACHA, Reg E, Visa/MC rules).

Your job is to analyse evidence produced by a live TigerGraph fraud-detection system
and reach a clear, defensible conclusion.

Core principles:
1. EVIDENCE-FIRST: base every decision on the graph evidence supplied. Do not speculate
   beyond what the data shows.
2. PROPORTIONALITY: roughly half of all flagged cases are legitimate. Blocking a legitimate
   customer is just as serious as missing real fraud. Apply the minimum necessary action.
3. TRANSPARENCY: every action must cite the specific graph signals and policy rules that
   justify it.
4. SAR DISCIPLINE: only file a SAR when the threshold is genuinely met
   (exposure > $1,000 OR ring / shared-device confirmed OR coordinated undocumented pattern).
"""

ASSESS_RISK_PROMPT = """\
## Task: Risk Assessment

You have received the following evidence bundle from the TigerGraph FraudGraph and
case-memory vector store. Assess the overall fraud risk of this transaction/account.

### Evidence Bundle
{evidence_markdown}

### Detected Graph Patterns (GSQL Results)
{pattern_summary}

### Instructions
1. Identify which of the 5 known fraud patterns best matches (or note if undocumented).
2. Assign an overall risk level: LOW | MEDIUM | HIGH | CRITICAL.
3. Give a numeric confidence score between 0.0 and 1.0.
4. List the top 3 strongest evidence signals in order of weight.

### Output Format (JSON only — no markdown fences)
{{
  "risk_level": "HIGH",
  "confidence": 0.85,
  "primary_pattern": "card_testing",
  "secondary_patterns": ["cnp"],
  "top_signals": [
    "5 micro-authorisations < $5.00 in 18 minutes preceding $340 CNP purchase",
    "Device flagged as new (id_15=1) with no prior card history",
    "PREV_TXN chain shows unusual velocity: 7 txns in 3 hours"
  ],
  "is_undocumented_pattern": false,
  "undocumented_description": ""
}}
"""

DECIDE_ACTION_PROMPT = """\
## Task: Action Decision

Based on the risk assessment below, select the correct set of next-best-actions
from the approved action catalogue.

### Risk Assessment
{risk_assessment_json}

### Evidence Summary
{evidence_markdown}

### Fraud Policy Rules (abbreviated)
- R1  CNP velocity burst (3+ txns / 6h) → block_card + create_case
- R2  Out-of-region card-present (no travel notice, dist > 500km) → request_step_up_auth
- R3  Impossible travel (two simultaneous locations) → block_card + create_case
- R4  High-velocity online spike (5+ / 24h) → monitor + create_case
- R5  Card-testing sequence (3+ micro <$5 → large purchase) → block_card + file_sar (if exposure >$1k)
- R6  New-device / proxy CNP → request_step_up_auth; if confirmed → block_card
- R7  Account-info-change + high spend → request_step_up_auth
- R8  Repeat offender (closed-case history confirmed_fraud) → block_account + file_sar
- R9  Multi-card fraud ring (ring_size >= 3) → block_all_ring_cards + file_sar
- R10 Low-risk anomaly, customer reachable → warn_customer + monitor

### SAR Filing Threshold (file if ANY true)
- Cumulative suspicious exposure > $1,000
- Ring detected (ring_size >= 3) with >= 1 confirmed-fraud card
- Coordinated / undocumented pattern with multiple accounts

### Approval Routes
- AUTO_EXECUTE: LOW risk standard actions (monitor, warn)
- RECOMMEND_ONLY: MEDIUM risk (step-up auth, create_case)
- REQUIRES_HUMAN_APPROVAL: HIGH/CRITICAL (block_card, block_account, file_sar)

### Instructions
Return ONLY valid JSON.  Select 1-3 actions.  Do not block if risk < 0.40.
If risk_level is LOW and confidence < 0.5, prefer warn_customer or monitor_account.

### Output Format
{{
  "actions": [
    {{
      "action_type": "block_card",
      "approval_route": "REQUIRES_HUMAN_APPROVAL",
      "rationale": "Card-testing sequence (R5) confirmed: 5 micro-auths < $5 in 18 min. Exposure $340 exceeds $1k threshold when annualised velocity included."
    }}
  ],
  "sar_required": true,
  "sar_trigger_reason": "Exposure $340 on card-testing sequence; card part of 4-card device-sharing ring (R9).",
  "stop_reason": "High-confidence card testing with ring membership confirmed by graph."
}}
"""

EXPLAIN_CASE_PROMPT = """\
## Task: Case Explanation Narrative

Draft the final investigation narrative for a human fraud analyst to review.
This will be saved as the case explanation and may be used in a SAR.

### Case ID: {case_id}
### Risk Level: {risk_level}  |  Confidence: {confidence}
### Primary Pattern: {primary_pattern}
### Actions Decided: {actions_summary}

### Evidence Bundle
{evidence_markdown}

### Instructions
Write a professional narrative (200-400 words) covering:
1. What triggered the investigation
2. What the graph evidence revealed (cite specific signals)
3. Why the fraud pattern was (or was not) confirmed
4. What actions are recommended and the policy rules they satisfy
5. Any caveats or next steps for the human reviewer

Write in clear, concise English suitable for a regulatory SAR filing.
Do not add any JSON or markdown headings — plain prose only.
"""

SAR_DRAFT_PROMPT = """\
## Task: SAR Draft

Draft a Suspicious Activity Report (SAR) summary for regulatory submission.

### Case Details
- Case ID: {case_id}
- Card ID: {card_id}
- Customer ID: {customer_id}
- Investigation Date: {investigation_date}
- Primary Pattern: {primary_pattern}
- Total Suspicious Exposure: ${exposure_usd}
- Ring Size: {ring_size} cards

### Evidence
{evidence_markdown}

### Instructions
Write a concise SAR narrative (150-250 words) covering:
1. Subject(s) of the report (card/account identifiers)
2. Nature and date range of suspicious activity
3. Why the activity is suspicious (graph evidence)
4. Amount involved
5. Any law-enforcement referral notes

Use plain professional language. Do not speculate beyond the evidence.
"""
