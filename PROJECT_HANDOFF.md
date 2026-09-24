# Project Handoff: TigerGraph Agentic Fraud Investigation

_Last audited: 2026-09-24 from the VS Code workspace._

## 1. Project Overview

This repository is a partial implementation of the HHGOA TigerGraph agentic fraud-investigation hackathon project. The intended system investigates a transaction or analyst/customer alert using TigerGraph graph queries, GraphRAG evidence, policy controls, an LLM, case memory, and a user interface.

The verified implementation now includes a runnable Phase 6 LangGraph agent. Policy enforcement, live case persistence, UI, benchmark runner, and answer files remain absent.

Current stack: Python 3.10 runtime; pyTigerGraph; GSQL; Pydantic; LangChain/LangGraph; Groq `openai/gpt-oss-120b`; pandas/numpy/scikit-learn TF-IDF retrieval; a custom MCP-like JSON-RPC wrapper; Streamlit declared but no app.

## 2. Current Status

| Component | Status | Current implementation | Working? | Remaining work |
|---|---|---|---|---|
| Frontend | NOT IMPLEMENTED | `ui/__init__.py` only | No UI to start | Build analyst dashboard |
| Backend | NOT IMPLEMENTED | No API service | No | Define service boundary if needed |
| Agent | PARTIALLY COMPLETED | `agent/orchestrator.py` provides typed LangGraph workflow and CLI | End-to-end smoke test succeeds; graph memory is not written | Add case persistence and benchmark output |
| TigerGraph | PARTIALLY COMPLETED | Live graph is reachable from current environment; credentials loaded from `.env` | Read-only access evidenced | Verify schema/counts and secure TLS |
| GSQL | PARTIALLY COMPLETED | Schema, ingestion scripts, six detection queries | Direct query smoke test succeeds; deployment scripts have hard-coded graph name | Bound fanout and document verified deployment |
| Graph algorithms | PARTIALLY COMPLETED | Pattern queries for card testing, burst, device, geography, ring, similar cases | Python vertex bindings now use correct one-tuples; ring traversal remains broad | Bound fanout |
| TigerGraph MCP | BROKEN/PARTIAL | Custom registry/server and LangChain adapters | In-process tests pass; Windows stdio fails; not official SDK protocol | Implement/clone official server integration and smoke test |
| GraphRAG | PARTIALLY COMPLETED | `GraphRAGEvidenceGatherer` combines graph calls and local TF-IDF retrieval | Vector retrieval works; graph errors are swallowed | Use real TigerGraph vector store or document the deliberate fallback; fail loudly on graph gaps |
| LLM | PARTIALLY COMPLETED | `LangChainReasoner` uses Groq structured output for assess/decide/explain | Production smoke test reaches Groq; retry/rate-limit observability remains | Harden retries and token accounting |
| Fraud investigation | PARTIALLY COMPLETED | LangGraph trigger → case → evidence → assess → decide → request/reassess → explain | Smoke test resolves a case; no graph write or exact answer file | Add persistence and output contract |
| Evidence gathering | PARTIALLY COMPLETED | Evidence bundle model and gatherer | Policy/case retrieval works; graph portion can be empty on exception | Make evidence provenance and failure state explicit |
| Risk assessment | PARTIALLY COMPLETED | `RiskAssessment` and reasoner structured output | Live result works; calibration not measured | Evaluate against closed cases |
| Case management | NOT IMPLEMENTED | `FraudCase` model only | No graph write | Add case lifecycle and output serialization |
| Case memory | NOT IMPLEMENTED | Historical cases are indexed locally; no live-case write/retrieval | Historical local search works | Write FraudCase and retrieve resolved cases |
| Next-best-action | PARTIALLY COMPLETED | `ActionDecision` proposals are validated before case actions are recorded | No benchmark evaluation yet | Align all policy rules and evaluate |
| Policy engine | PARTIALLY COMPLETED | `agent/policy/engine.py` enforces exact action routes | Full rule table and approval workflow remain | Complete policy conditions |
| Human approval | NOT IMPLEMENTED | Enum placeholders only | No approval state or gate | Add approval records and execution separation |
| Dataset | COMPLETED/NOT VERIFIED END-TO-END | Five raw files present; README read; local vector cache present | Files exist | Verify every ingestion mapping and benchmark join |
| Evaluation | NOT IMPLEMENTED | No runner or answer files | No | Implement exact 20-case output |
| Testing | PARTIALLY COMPLETED | 4 test modules, 13 tests | `pytest` passed 13 tests; TLS/LangGraph warnings remain | Add live-write and benchmark tests |
| Documentation | PARTIALLY COMPLETED | README/schema/progress; three placeholder docs | Existing docs overstate status | Update docs as implementation becomes real |
| Demo | NOT IMPLEMENTED | No UI or end-to-end run | No | Build a repeatable demo path |

## 3. Existing Architecture

The actual current path is:

```text
CLI trigger parser (agent/run.py)
        |
        | orchestrator import (missing)
        v
Custom MCP tool registry / LangChain StructuredTools
        |
        +--> pyTigerGraph query client --> live TigerGraph GSQL queries
        |
        +--> GraphRAGEvidenceGatherer --> local TF-IDF vector cache
                                      +--> policy/regulatory constants
```

The intended but not implemented path is trigger -> case -> graph evidence -> policy/document retrieval -> assessment -> more evidence loop -> action decision -> permission check -> explanation -> graph case memory -> answer file/UI.

There is no frontend/backend communication path. There is no LLM communication path. The MCP server is a local custom JSON-RPC loop, not verified interoperability with the official TigerGraph MCP server.

## 4. Important Files

| File/folder | Purpose and status |
|---|---|
| `agent/models.py` | Pydantic enums and models for triggers, evidence, patterns, actions, cases, and intended agent state. Action names do not match the dataset policy identifiers. |
| `agent/config.py` | Loads `.env` and exposes `Settings`; imports `pydantic-settings`, which is not declared in `requirements.txt`. |
| `agent/run.py` | Typer CLI. Parses trigger JSON or transaction ID, then imports missing `agent.orchestrator`; import of `loguru` currently fails first in the observed environment. |
| `agent/prompts.py` | Untracked local prompt templates for risk, action, explanation, and SAR generation. No caller exists. |
| `graph/schema.gsql` | TigerGraph schema for Customer, Card, Transaction, DeviceProfile, EmailDomain, BillingRegion, ClosedCase, FraudCase and related edges. References missing `graph/vector_schema.gsql`. |
| `graph/ingest_data.py` | Pandas/pyTigerGraph ingestion for closed cases, identity/device profiles, cards, customers, transactions, and edges. Does not populate every schema field advertised by comments. |
| `graph/deploy_schema.py` | Deployment helper; hard-codes `FraudGraph` when creating the graph rather than using `TG_GRAPH_NAME`. |
| `graph/install_queries.py` | Installs six query files; hard-codes `USE GRAPH FraudGraph`. |
| `graph/queries/*.gsql` | Six fraud detection queries. Their parameter signatures must be checked against `graph/queries_client.py`; the live error showed `target_txn` was expected while the client sent `target_txn_id`. |
| `graph/queries_client.py` | pyTigerGraph wrapper and `PatternDetectionResult`. It sends names that do not match at least some installed query parameters and ignores bounded `max_hops` behavior in the GSQL implementation. |
| `rag/policy_documents.py` | In-code policy and regulatory text. It is not the same as enforcing the dataset's exact action/route contract. |
| `rag/vector_store.py` | Local pickle-backed TF-IDF retrieval over 5,565 historical cases plus in-code policy/regulatory documents. It is not TigerGraph-native vector storage. |
| `rag/evidence_gatherer.py` | Combines six graph results with local retrieval and Markdown synthesis. Catches graph exceptions and continues, allowing tests to pass without graph evidence. |
| `mcp/tools.py` | Functions wrapping graph queries and evidence gathering; registry metadata for seven tools. |
| `mcp/server.py` | Custom JSON-RPC server. Current working-tree change invokes `asyncio.run(run_stdio())`; that path fails on Windows pipe setup in the observed terminal. |
| `mcp/client.py` | LangChain `StructuredTool` adapters; no network MCP client. |
| `tests/test_*.py` | Model/parser, vector, evidence bundle, registry, server listing, and adapter tests. No end-to-end workflow tests. |
| `README.md` | Quick start and planned architecture; lists files/commands that do not yet exist. |
| `docs/progress.md` | Phase tracker; status is inconsistent with source and still contains old blockers. |
| `docs/schema.md` | Schema design notes; partly aspirational, including vector collections not implemented. |
| `ui/` | Package marker only. |
| `cases/` | `.gitkeep` only; no benchmark outputs. |

## 5. How to Run

Verified from the repository root:

```powershell
pytest
```

Result on 2026-09-24: `8 passed, 2 warnings`. Warnings are unverified HTTPS requests to TigerGraph.

The documented CLI is:

```powershell
python -m agent.run --trigger-file path/to/trigger.json
python -m agent.run --transaction-id TXN123456 --source risk_score --risk-score 0.87
```

The second form was attempted with transaction `3000120`; it failed before agent execution with `ModuleNotFoundError: No module named 'loguru'`. Even after that dependency is present, `agent.orchestrator` is absent.

The README documents these commands, but the corresponding implementation is absent and therefore unverified:

```powershell
streamlit run ui/app.py
python tests/run_benchmark.py
```

Data ingestion and query installation scripts exist, but they mutate TigerGraph and were not rerun during this audit. The repository does not contain a verified command for launching the official TigerGraph MCP server.

## 6. Environment Variables

Read from `.env` through `agent/config.py` or direct `os.getenv` calls:

- `TG_HOST`, `TG_USERNAME`, `TG_PASSWORD`, `TG_GRAPH_NAME`, `TG_SECRET`, `TG_TOKEN`: TigerGraph connection/authentication.
- `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`: intended LLM provider and model.
- `EMBEDDING_MODEL`, `EMBEDDING_PROVIDER`, `EMBEDDING_API_KEY`: intended embedding configuration; current vector store uses local TF-IDF instead.
- `MCP_SERVER_URL`, `MCP_LOG_LEVEL`: declared MCP settings; URL is not used by the current server/client.
- `CASES_OUTPUT_DIR`, `DATA_RAW_DIR`, `DATA_PROCESSED_DIR`: paths declared in settings; several modules still use relative literals.
- `LOG_LEVEL`: application logging level.

Secret values are intentionally omitted. `.env` is present locally and `.gitignore` excludes it.

## 7. Dataset

Verified local files:

- `data/raw/transactions.csv`: 590,742 rows, 397 columns per the dataset README; local size 707,936,515 bytes.
- `data/raw/identity.csv`: 144,432 identity rows, 41 columns; local size 26,716,154 bytes.
- `data/raw/closed_cases_history.csv`: 5,565 historical investigations; local size 2,706,417 bytes.
- `data/raw/case_pack.csv`: 20 benchmark cases; local size 3,548 bytes.
- `data/raw/README.md`: full dataset/task/policy/answer-format document; local size 38,663 bytes.

The README defines Customer, Card, Transaction, DeviceProfile, EmailDomain, BillingRegion, ClosedCase, five known patterns, exact policy action identifiers/routes, evidence-request simulation, stopping thresholds, and the JSON answer format. The ingestion code derives card IDs and device profile IDs and creates graph vertices/edges. The local processed artifact is `data/processed/vector_index.pkl` (451,549,529 bytes), a pickle TF-IDF index.

TigerGraph data is reported in prior progress notes, but the complete counts and ingestion correctness are NOT VERIFIED by a reproducible repository command in this audit. No benchmark answer file exists.

## 8. TigerGraph

The schema includes eight vertex types and case/device/email/region/transaction edges. `NEXT_TXN` is intended to be built after ingestion by `graph/build_txn_chain.gsql`. Six installed-query source files target card testing, burst activity, shared-device fanout, geographic anomaly, fraud ring, and similar cases.

The live environment is reachable from the current `.env` in read-only query calls. The captured live output included real results for the six query calls, but also showed parameter errors for client calls and a fraud-ring result of 1,907 cards / 1,555 prior confirmed cases for one input, suggesting the current traversal is not bounded as its API implies. Do not use those values as quality metrics.

The agent currently accesses TigerGraph indirectly through `graph/queries_client.py` and `mcp/tools.py`. There is no implemented case write, transaction update, FraudCase edge creation, vector schema deployment, or graph-native embedding workflow.

## 9. Agent

Implemented: trigger parsing, typed state/models, CLI entrypoint, LangGraph orchestration, Groq structured reasoner, policy route validation, and simulated evidence responses.

Partial: `mcp/client.py` exposes LangChain tools, but the orchestration currently calls the GraphRAG provider directly rather than through a network MCP client.

Missing: live case-memory update, exact answer-file output, token/latency accounting, and benchmark evaluation.

## 10. GraphRAG

The gatherer calls all six graph wrappers, searches the local TF-IDF index for closed cases, policy rules, and regulatory guidance, then builds a synthesized Markdown bundle. The vector index contains 5,565 historical cases plus in-code policy/regulatory entries. README pattern sections and external regulatory documents are not separately loaded. Graph exceptions are printed and suppressed, so a bundle can look successful without graph evidence. Context is not passed to an LLM because no LLM caller exists.

## 11. Case Memory

Historical memory: local closed-case CSV rows are embedded into the pickle-backed TF-IDF index and retrieved by text query. Graph memory: `ClosedCase` vertices and edges exist in ingestion/schema code and live data was previously observed. Live memory: NOT IMPLEMENTED. No code writes `FraudCase`, embeds case summaries, creates `SIMILAR_TO`, or uses resolved agent cases in a later investigation.

## 12. Investigation Workflow

| Step | Status | Current file/function | Limitation |
|---|---|---|---|
| Trigger | COMPLETED | `agent/run.py`, `InvestigationTrigger` | Direct CLI lookup resolves transaction context from TigerGraph |
| Create/open case | PARTIAL | `agent/orchestrator.py`, `FraudCase` | In-memory only; no graph persistence |
| Investigate entities | PARTIAL | graph queries/client | Live query works; ring traversal remains broad |
| Gather evidence | PARTIAL | `gather_evidence_bundle` | Graph errors swallowed; local rather than TigerGraph vector store |
| Assess risk | PARTIAL | `LangChainReasoner.assess`, `RiskAssessment` | Live result works; no calibration |
| Assess uncertainty | PARTIAL | `RiskAssessment.needs_more_evidence` | LLM-controlled sufficiency needs policy tests |
| Request evidence | PARTIAL | `request_more_evidence` node | Responses are simulated, not external |
| Reassess | COMPLETED | LangGraph conditional loop | No multi-case evaluation |
| Recommend action | PARTIAL | `LangChainReasoner.decide` | Exact output contract not yet serialized |
| Policy/permission check | PARTIAL | `agent/policy/engine.py` | Route enforcement exists; full conditions remain |
| Human approval | NOT IMPLEMENTED | enum only | No approval state |
| Execute action | NOT IMPLEMENTED | no executors | No mock action log |
| Explain | PARTIAL | `LangChainReasoner.explain` | Live narrative works; no SAR/output serialization |
| Update memory | NOT IMPLEMENTED | no writer | No live case graph/vector update |
| Stop | NOT IMPLEMENTED | `max_iterations` field only | No defensible stopping logic |

## 13. Current Results

- Existing automated tests: **13 passed, 8 warnings** under Python 3.10 on 2026-09-24.
- Local vector retrieval: tests returned policy and closed-case results; no benchmark accuracy measured.
- TigerGraph reachability: live transaction-context lookup and card-testing query succeeded for transaction `3000120`; no complete count audit exists.
- End-to-end smoke test: CLI reached TigerGraph, local GraphRAG, Groq structured assessment/decision/explanation, and returned `resolved_fraud`; no graph write was claimed.
- Agent accuracy, precision, recall, F1: **NOT YET MEASURED**.
- Benchmark results: **NOT RUN**.
- End-to-end latency/tokens/API performance: **NOT YET MEASURED**.
- UI/backend results: **NOT AVAILABLE**.

## 14. Benchmark Evaluation

The 20 case IDs are present in `case_pack.csv` and documented in the dataset README. No case has a generated answer file. Therefore investigation result, evidence, pattern, risk, uncertainty, extra evidence, action, approval, decision, and explanation are all **NOT YET PRODUCED** for HHG-001 through HHG-020.

## 15. Testing

Existing tests cover Pydantic parsing, local vector search, bundle construction, MCP registry listing, and LangChain adapter construction. Missing tests cover live query parameter contracts, GSQL installation/schema, graph failure visibility, agent nodes/loops, exact policy actions/routes, case writes, approval gates, action executors, memory updates, answer serialization, benchmark evaluation, API/UI, and end-to-end investigations.

## 16. Known Issues

| Issue | Severity | File | Cause | Current behavior | Status |
|---|---|---|---|---|---|
| Graph failures hidden | High | `rag/evidence_gatherer.py` | Broad exception handling | Tests can pass without graph evidence | Open |
| Groq transient rate limits | Medium | Production smoke test | Provider returned 429 once and retried | Run completed after retry | Monitor |
| Policy identifiers mismatch | Critical | `agent/models.py`, `agent/prompts.py`, `rag/policy_documents.py` | Code uses alternate action names | Cannot produce compliant answer files | Open |
| MCP stdio fails on Windows | High | `mcp/server.py` | Async pipe setup is incompatible with observed Proactor stdin | Server errors before protocol | Open |
| Custom MCP is not official MCP | High | `mcp/server.py`, `mcp/client.py` | Hand-rolled JSON-RPC; no initialize/capabilities | Interoperability unverified | Open |
| Ring traversal not bounded | High | `detect_fraud_ring.gsql` | `max_hops` not used to constrain traversal | Very large fanout result | Open |
| Hard-coded graph name | Medium | `graph/deploy_schema.py`, `graph/install_queries.py`, GSQL | `FraudGraph` literals | Env graph name ignored | Open |
| Missing vector schema | Medium | `graph/schema.gsql` | Referenced file absent | Native vector plan cannot deploy | Open |
| No UI/benchmark/case outputs | Critical | `ui/`, `tests/`, `cases/` | Not implemented | Submission deliverables absent | Open |
| Documentation overstates completion | Medium | `README.md`, `docs/progress.md` | Planned files described as present | Misleading setup/status | Open |

## 17. Completed Work

- [x] Repository scaffold and Python package markers.
- [x] Environment template and ignore rules.
- [x] Dataset downloaded locally and README read.
- [x] TigerGraph schema and ingestion scripts written.
- [x] Six GSQL query files and Python result model written.
- [x] Local closed-case/policy retrieval index built.
- [x] Evidence bundle and MCP-like tool registry written.
- [x] Existing unit/integration tests run: 8 passed.

## 18. Remaining Work

### CRITICAL

- [ ] Align GSQL parameter signatures and Python bindings; add tests that assert real graph evidence.
- [ ] Implement the typed investigation orchestrator and CLI execution.
- [ ] Implement exact dataset policy identifiers/routes and authoritative permission checks.
- [ ] Implement FraudCase graph writes and exact answer-file serialization.
- [ ] Build and run the 20-case benchmark without hardcoded answers.

### HIGH

- [ ] Implement evidence-request simulation and reassessment/stop conditions.
- [ ] Implement LLM assess/decide/explain calls with structured validation.
- [ ] Replace or explicitly isolate the custom MCP server with official TigerGraph MCP integration.
- [ ] Implement resolved-case memory retrieval and update.
- [ ] Implement the Streamlit case dashboard.

### MEDIUM

- [ ] Bound fraud-ring traversal and apply `pattern_filter`.
- [ ] Remove graph-name hard-coding and verify schema/vector deployment.
- [ ] Expand tests for graph, policy, workflow, memory, and output contracts.
- [ ] Reconcile README/progress/schema/algorithm/MCP documentation with verified behavior.

### LOW / OPTIONAL

- [ ] Measure latency, token use, precision/recall, and query performance.
- [ ] Add external regulatory documents and TigerGraph-native embeddings.
- [ ] Prepare demo and final blog after the application is runnable.
