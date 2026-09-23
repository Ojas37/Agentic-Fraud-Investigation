"""
rag/policy_documents.py — Bank Fraud Policy & Regulatory Knowledge Base
Contains codified fraud policies (R1-R10), action authorization rules, and regulatory citations.
"""

from typing import List, Dict, Any

FRAUD_POLICY_RULES = [
    {
        "rule_id": "R1",
        "title": "Low-to-Medium Risk Card-Not-Present (CNP)",
        "condition": "CNP transaction with risk score 0.40 - 0.70 and no prior fraud history on card",
        "recommended_actions": ["CREATE_CASE", "VERIFY_WITH_CUSTOMER", "MONITOR_ACCOUNT"],
        "route": "auto",
        "description": "On its own, an unusual online purchase is ambiguous. Verify with customer before taking intrusive action."
    },
    {
        "rule_id": "R2",
        "title": "High Risk Card-Not-Present (CNP)",
        "condition": "CNP transaction with risk score > 0.70 or rapid velocity burst (>3 txns in 48h)",
        "recommended_actions": ["CREATE_CASE", "REQUEST_STEP_UP_AUTH", "WARN_CUSTOMER", "MONITOR_ACCOUNT"],
        "route": "auto",
        "description": "High probability of card number theft. Require step-up authentication and alert cardholder."
    },
    {
        "rule_id": "R3",
        "title": "Out-of-Region Card-Present Activity",
        "condition": "Card-present transaction in non-home region without concurrent home-region activity",
        "recommended_actions": ["CREATE_CASE", "VERIFY_WITH_CUSTOMER", "MONITOR_ACCOUNT"],
        "route": "auto",
        "description": "Cardholder may be traveling. Verify travel status. Several consecutive days in new region is a trip, not a clone."
    },
    {
        "rule_id": "R4",
        "title": "Impossible Travel / Concurrent Regional Activity",
        "condition": "Card-present transactions in different geographic regions within impossible travel window (<4h)",
        "recommended_actions": ["CREATE_CASE", "BLOCK_TRANSACTION", "BLOCK_ACCOUNT", "WARN_CUSTOMER", "FILE_SAR"],
        "route": "requires_human_approval",
        "description": "Physical card cloning confirmed by simultaneous presence in disparate locations. Block card and file SAR if exposure > $1,000."
    },
    {
        "rule_id": "R5",
        "title": "Card Testing Authorization Sequence",
        "condition": "3 or more micro-authorizations (<$5.00) followed by a larger transaction (> $20.00) within 24 hours",
        "recommended_actions": ["CREATE_CASE", "BLOCK_TRANSACTION", "BLOCK_ACCOUNT", "WARN_CUSTOMER"],
        "route": "requires_human_approval",
        "description": "Stolen card number validated via automated micro-charges. Confirmed by sequence itself. Block immediately."
    },
    {
        "rule_id": "R6",
        "title": "New Device & Shared Device Fingerprint Fanout",
        "condition": "CNP transaction from New device behind proxy or device fingerprint shared across multiple distinct cards",
        "recommended_actions": ["CREATE_CASE", "REQUEST_STEP_UP_AUTH", "BLOCK_TRANSACTION", "ESCALATE_TO_ANALYST", "FILE_SAR"],
        "route": "requires_human_approval",
        "description": "Indicates shared device attack or organized fraud ring. Step-up auth, investigate connected accounts, and file SAR if multi-card ring."
    },
    {
        "rule_id": "R7",
        "title": "Disputed But Legitimate Recurring Charge",
        "condition": "Customer disputes transaction matching recurring subscription pattern (same merchant, same amount, monthly cadence)",
        "recommended_actions": ["CREATE_CASE", "VERIFY_WITH_CUSTOMER", "WARN_CUSTOMER"],
        "route": "auto",
        "description": "False positive / forgotten subscription. Do not block card. Explain merchant billing descriptor to customer."
    },
    {
        "rule_id": "R8",
        "title": "Historical Precedent & Prior Compromise",
        "condition": "Card or device previously linked to confirmed fraud case in closed case history",
        "recommended_actions": ["CREATE_CASE", "BLOCK_ACCOUNT", "ESCALATE_TO_ANALYST", "FILE_SAR"],
        "route": "requires_human_approval",
        "description": "Repeat compromise or known bad actor infrastructure. Escalate with reference to prior closed case ID."
    },
    {
        "rule_id": "R9",
        "title": "Undocumented Coordinated Abuse",
        "condition": "Activity fits none of the 5 standard patterns but exhibits coordinated multi-customer anomalies",
        "recommended_actions": ["CREATE_CASE", "FILE_SAR", "ESCALATE_TO_ANALYST"],
        "route": "requires_senior_approval",
        "description": "Describe the pattern in custom narrative. Do not force into known category. Flag for senior fraud analyst review."
    },
    {
        "rule_id": "R10",
        "title": "Regulatory SAR Filing Thresholds",
        "condition": "Confirmed fraud with exposure > $1,000 OR shared ring/device across customers OR undocumented coordinated scheme",
        "recommended_actions": ["FILE_SAR"],
        "route": "requires_human_approval",
        "description": "FinCEN/FFIEC mandatory reporting. SAR narrative must detail who, what, when, where, how, and why it is suspicious."
    }
]

REGULATORY_GUIDANCE = [
    {
        "source": "FinCEN SAR Narrative Guidance (October 2025)",
        "topic": "Essential Elements of a SAR Narrative",
        "summary": "A complete SAR narrative answers Who, What, When, Where, Why, and How. It must clearly explain the method of operation (MOD), account connections, timeline of suspicious events, and why the activity is considered illicit rather than legitimate banking behavior."
    },
    {
        "source": "FinCEN Advisory on Account Takeover & Identity Theft",
        "topic": "Red Flags for Credential Compromise",
        "summary": "Red flags include rapid password/device changes followed by immediate high-value fund transfers, novel proxy IP usage, device fingerprint changes, and inconsistent channel usage."
    },
    {
        "source": "FATF Cyber-Enabled Fraud & Multi-Account Rings",
        "topic": "Organized Multi-Card Testing & Infrastructure Sharing",
        "summary": "Criminal rings utilize shared digital infrastructure (emulators, proxies, devices) across compromised credit card caches. Identifying graph linkage between seemingly unrelated cardholders is the primary tool for disruption."
    },
    {
        "source": "FFIEC BSA/AML Manual",
        "topic": "Suspicious Activity Monitoring and Reporting",
        "summary": "Financial institutions must maintain automated or repeatable processes to detect anomalous transaction bursts, impossible geographic travel, and unauthorized account access."
    }
]
