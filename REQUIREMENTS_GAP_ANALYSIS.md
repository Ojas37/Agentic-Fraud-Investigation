# Hackathon Requirements Gap Analysis

_Audit date: 2026-09-24. Statuses are based on source evidence, not prior progress claims._

| Requirement | Current status | Evidence/file | Missing work | Priority |
|---|---|---|---|---|
| Fraud investigation trigger | PARTIALLY COMPLETED | `agent/run.py`, `InvestigationTrigger` | Connect trigger to a real workflow and case pack loader | Critical |
| Evidence gathering | PARTIALLY COMPLETED | `rag/evidence_gatherer.py` | Make graph failures visible; preserve source/entity provenance | Critical |
| Knowledge graph investigation | PARTIALLY COMPLETED | `graph/schema.gsql`, `graph/queries/*.gsql` | Correct client signatures and verify all traversals | Critical |
| Transaction analysis | PARTIALLY COMPLETED | Transaction schema and burst/card-testing queries | Add bounded, tested transaction-window evidence | High |
| Device/identity analysis | PARTIALLY COMPLETED | `ingest_data.py`, device query | Verify identity joins and expose device IDs in bundle | High |
| Account behavior analysis | PARTIALLY COMPLETED | Customer/Card aggregates in schema | Add workflow-level customer/card history synthesis | High |
| Historical case analysis | PARTIALLY COMPLETED | `vector_store.py`, ClosedCase graph | Use exact retrieved case IDs in case output and graph memory | High |
| Fraud pattern identification | PARTIALLY COMPLETED | Six GSQL queries | Map outputs to exact seven answer-format pattern values | Critical |
| Risk assessment | NOT IMPLEMENTED | `agent/prompts.py` only | Structured LLM assessment with validation/calibration | Critical |
| Case creation | NOT IMPLEMENTED | `FraudCase` model/schema only | Create and persist lifecycle state | Critical |
| Case progression | NOT IMPLEMENTED | No orchestrator | Add updates before/after evidence requests | Critical |
| Case memory | NOT IMPLEMENTED for live cases | Schema has `FraudCase`; no writer | Persist case, summary, links, and retrieval | Critical |
| Similar case retrieval | PARTIALLY COMPLETED | Local TF-IDF plus graph query wrapper | Make retrieval a workflow input and write cited IDs | High |
| Additional evidence gathering | NOT IMPLEMENTED | Enums/models only | Simulate customer, step-up, analyst responses | Critical |
| Next-best-action | NOT IMPLEMENTED | Prompt prose only | Generate actions from evidence and validate policy | Critical |
| Policy enforcement | NOT IMPLEMENTED | `rag/policy_documents.py` is retrieval content | Implement executable rules, not prompt-only rules | Critical |
| Permissions | NOT IMPLEMENTED | `ApprovalRoute` enum differs from dataset routes | Enforce `auto`, `L1`, `L2` and action conditions | Critical |
| Human approval | NOT IMPLEMENTED | No approval state | Separate recommendation from execution and record route | Critical |
| Investigation stopping | NOT IMPLEMENTED | `max_iterations` field only | Implement probability/evidence/response stop rules | High |
| Explainability | PARTIALLY COMPLETED | Prompt template and Markdown synthesis | Generate auditable explanation citing policy and evidence | High |
| TigerGraph | PARTIALLY COMPLETED | pyTigerGraph client and live query output | Verify schema/counts and writes reproducibly | Critical |
| GSQL | PARTIALLY COMPLETED | Schema, ingestion, six queries | Fix signatures, hard-coded graph name, and deployment gaps | Critical |
| Graph algorithms | PARTIALLY COMPLETED | Pattern query files | Bound ring traversal and validate outputs | High |
| TigerGraph MCP | PARTIALLY COMPLETED/BROKEN | `mcp/server.py`, `mcp/client.py`, `mcp/tools.py` | Use official server/protocol and pass a real smoke test | High |
| GraphRAG | PARTIALLY COMPLETED | `rag/evidence_gatherer.py`, `vector_store.py` | Ground an LLM and align storage with required TigerGraph vector use | High |
| User interface | NOT IMPLEMENTED | `ui/__init__.py` only | Streamlit dashboard and live investigation view | High |
| Audit record | NOT IMPLEMENTED | Model fields only | Exact JSON answer files plus graph confirmation | Critical |
| 20 benchmark cases | NOT IMPLEMENTED | `case_pack.csv` only | Runner, outputs, summary, manual spot-check | Critical |

## Overall Assessment

The repository demonstrates meaningful graph, data, retrieval, and tool scaffolding, but it is not yet a compliant submission. The critical path is: correct graph contracts -> implement the workflow and policy engine -> persist exact case outputs -> benchmark -> UI/documentation. The current 8 passing tests do not establish hackathon capability because they do not execute the agent or assert successful graph evidence.
