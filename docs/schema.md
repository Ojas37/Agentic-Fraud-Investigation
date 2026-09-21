# Graph Schema — HHGOA Fraud Investigation Agent

_Generated from the HHGOA_IEEE dataset README. Implement in `graph/schema.gsql`._

---

## Data Files

| File | Rows | Columns | Purpose |
|------|------|---------|---------|
| `transactions.csv` | 590,742 | 397 | All transactions (393 Vesta cols + `customer_id`, `ts`, `channel`, `risk_score`) |
| `identity.csv` | 144,432 | 41 | Device/connection records for online transactions; joins on `TransactionID` |
| `closed_cases_history.csv` | 5,565 | 15 | Historical investigations Jul–Oct; agent's starting memory |
| `case_pack.csv` | 20 | 8 | Benchmark exam cases (Nov–Dec) |

---

## Vertex Types

### `Customer`
One vertex per `customer_id` (e.g. `C01234`). Derived from the card issuer field.

| Attribute | Type | Source |
|-----------|------|--------|
| `customer_id` | STRING (PK) | `transactions.customer_id` |
| `first_seen_ts` | DATETIME | min(`ts`) across all their transactions |
| `last_seen_ts` | DATETIME | max(`ts`) |
| `total_txn_count` | INT | computed |
| `total_spend_usd` | FLOAT | computed |

---

### `Card`
One vertex per `card_id` (e.g. `C01234-K1`). A customer may hold multiple cards.

| Attribute | Type | Source |
|-----------|------|--------|
| `card_id` | STRING (PK) | `case_pack.card_id` / derived |
| `customer_id` | STRING | FK to Customer |
| `card1`–`card6` | STRING | `transactions.card1`–`card6` |
| `card4` | STRING | Network: visa / mastercard / american express / discover |
| `card6` | STRING | Type: credit / debit |
| `is_blocked` | BOOL | agent-maintained |
| `block_reason` | STRING | agent-maintained |

---

### `Transaction`
One vertex per `TransactionID`. Stores all 397 source columns.

| Attribute Group | Columns | Source |
|----------------|---------|--------|
| Identity | `transaction_id`, `customer_id`, `card_id`, `ts`, `channel`, `risk_score` | Added columns |
| Vesta core | `TransactionDT`, `TransactionAmt`, `ProductCD` | transactions.csv |
| Card detail (denorm) | `card1`–`card6` | transactions.csv |
| Billing | `addr1`, `addr2`, `dist1`, `dist2` | transactions.csv |
| Email | `P_emaildomain`, `R_emaildomain` | transactions.csv |
| Count features | `C1`–`C14` | transactions.csv |
| Time-delta features | `D1`–`D15` | transactions.csv |
| Match flags | `M1`–`M9` | transactions.csv |
| Vesta V-features | `V1`–`V339` stored in `v_features_json` blob; key ones (`V1`,`V2`,`V3`,`V4`,`V12`,`V13`,`V14`,`V83`,`V127`) also as individual float attrs | transactions.csv |
| Channel derived | `channel` = `in_person` (ProductCD=W) or `online` | computed |
| Agent flags | `is_suspicious`, `in_case` | agent-maintained |

> **V-feature note:** Vesta did not publish individual V-column definitions. Store all 339 in a JSON blob for completeness; use the individually-exposed V-attrs as signal features when they appear correlated. Always note in evidence that their meaning is unknown.

---

### `DeviceProfile`
Deduplicated fingerprint: `DeviceInfo` + OS (`id_30`) + browser (`id_31`) + screen (`id_33`).

| Attribute | Type | Source |
|-----------|------|--------|
| `device_profile_id` | STRING (PK) | SHA-256 of composite key |
| `DeviceType` | STRING | identity.csv `DeviceType` |
| `DeviceInfo` | STRING | identity.csv `DeviceInfo` |
| `os` | STRING | identity.csv `id_30` |
| `browser` | STRING | identity.csv `id_31` |
| `screen` | STRING | identity.csv `id_33` |
| `proxy_flag` | STRING | identity.csv `id_23` |
| `device_match_status` | STRING | identity.csv `id_34` |
| `card_count` | INT | count of distinct cards that used this profile |

> **Key signal:** A single `DeviceProfile` appearing across multiple `Card` vertices in a short window is the primary indicator of a fraud ring or shared-device attack (Pattern 3 / Rule R6).

---

### `EmailDomain`
One vertex per unique email domain string.

---

### `BillingRegion`
One vertex per `addr1` value (anonymised region code). `addr2 == "87"` = home country.

---

### `ClosedCase`
Historical investigation from `closed_cases_history.csv`. Jul–Oct 2016. 5,565 rows.

| Attribute | Type | Notes |
|-----------|------|-------|
| `case_id` | STRING (PK) | e.g. `CC-0001` |
| `outcome` | STRING | `confirmed_fraud` / `cleared` |
| `pattern` | STRING | one of the 5 known patterns, `undocumented`, or `none` |
| `txn_ids` | STRING | pipe-separated `TransactionID`s |
| `connected_card_ids` | STRING | pipe-separated `card_id`s |
| `actions_taken` | STRING | pipe-separated action names |
| `analyst_notes` | STRING | free text — embedded into vector store for GraphRAG |

---

### `FraudCase`
Agent-generated live investigation. Written to the graph when the agent closes (or opens) a case. This is the case memory the next investigation retrieves.

| Attribute | Type | Notes |
|-----------|------|-------|
| `graph_case_id` | STRING (PK) | e.g. `CASE-2016-1187` |
| `case_id` | STRING | benchmark ID (e.g. `HHG-017`) or `""` for organic |
| `status` | STRING | `open` / `closed_fraud` / `closed_legitimate` / `escalated` |
| `verdict` | STRING | `fraud` / `legitimate` / `uncertain` |
| `fraud_probability` | FLOAT | 0–1 |
| `pattern` | STRING | one of the 7 pattern values |
| `evidence_json` | STRING | full evidence list as JSON blob |
| `next_best_actions_json` | STRING | initial + final actions as JSON blob |
| `sar_json` | STRING | SAR details as JSON blob |
| `summary` | STRING | 2–6 sentence human summary; embedded into vector store |

---

## Edge Types

| Edge | From → To | Direction | Purpose |
|------|-----------|-----------|---------|
| `OWNS` | Customer → Card | directed | Customer holds a card |
| `MADE` | Card → Transaction | directed | Card used in transaction |
| `FROM_DEVICE` | Transaction → DeviceProfile | directed | Device used (online only) |
| `PURCHASER_EMAIL` | Transaction → EmailDomain | directed | Purchaser's email domain |
| `RECIPIENT_EMAIL` | Transaction → EmailDomain | directed | Recipient's email domain |
| `BILLED_IN` | Transaction → BillingRegion | directed | Billing region (addr1) |
| `NEXT_TXN` | Transaction → Transaction | directed | Chronological chain per card; `time_gap_seconds` attr |
| `CASE_INVOLVES` | ClosedCase → Transaction | directed | Transactions in historical case |
| `CASE_ON_CARD` | ClosedCase → Card | directed | Primary card in historical case |
| `CASE_CONNECTED_TO` | ClosedCase → Card | directed | Connected cards in historical ring |
| `LIVE_CASE_INVOLVES` | FraudCase → Transaction | directed | Transactions in live case |
| `LIVE_CASE_ON_CARD` | FraudCase → Card | directed | Primary card in live case |
| `LIVE_CONNECTED_CARD` | FraudCase → Card | directed | Connected cards in live case |
| `LIVE_CONNECTED_DEV` | FraudCase → DeviceProfile | directed | Device profiles in live case |
| `SIMILAR_TO` | FraudCase → ClosedCase | directed | Memory retrieval link; `similarity_score` attr |

---

## Vector Store Collections

Two collections embedded into TigerGraph's native vector store:

| Collection | Documents | Embedding field |
|-----------|-----------|----------------|
| `case_memory` | `ClosedCase.analyst_notes` + pattern + outcome | For similar-case retrieval |
| `documents` | README fraud patterns (5 sections) + Fraud Policy (10 rules) + regulatory refs | For GraphRAG policy grounding |
| `live_cases` | `FraudCase.summary` | So new investigations can find recent agent-written cases |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| V1–V339 stored as JSON blob | 339 columns × 590K rows would balloon TigerGraph schema; keep the few critical ones individual; bulk-retrieve from blob as needed |
| `DeviceProfile` deduplicated vertex | Enables cross-card fan-out queries without full-text matching on each transaction |
| `NEXT_TXN` edge | Pre-computes chronological card history for burst-detection queries (Pattern 1: card testing) |
| `FraudCase` separate from `ClosedCase` | Agent writes new cases to a separate type; keeps historical ground-truth clean |
| `SIMILAR_TO` edge | Persists the similarity link so the graph itself is queryable for "which cases were informed by CC-0141" |
