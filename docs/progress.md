# Progress Tracker — HHGOA Fraud Investigation Agent

_Last updated: Phase 6 Agent Orchestration Core in progress_

---

## Phase Status

| Phase | Name | Status | Notes |
|-------|------|--------|-------|
| 0 | Project Scaffolding | ✅ Done | Repo structure, .gitignore, .env.example, requirements.txt, base models, CLI stub |
| 1 | Ingest Real Dataset Info | ✅ Done | README parsed, all 5 files downloaded, answer format + fraud policy + 5 patterns extracted |
| 2 | Graph Schema & Ingestion | ✅ Done | `FraudGraph` schema deployed live, all 590K txns, 14.8K cards, 13.5K customers, 9.7K devices, 5.5K cases ingested |
| 3 | Fraud Pattern Detection | ✅ Done | 6 standardized GSQL detection queries installed on live graph; queries client & test suite complete |
| 4 | GraphRAG Layer | ✅ Done | Vector store indexing 5.5K closed cases, policy & regulatory rules, unified `gather_evidence_bundle()` |
| 5 | TigerGraph MCP Integration | ✅ Done | Standard MCP server, 7 MCP tool definitions, and LangChain StructuredTool bindings |
| 6 | Agent Orchestration Core | 🟡 In progress | LangGraph trigger → case → evidence → assess → decide → optional simulated evidence loop → explain; graph memory write remains Phase 8 |
| 7 | Policy & Permission Engine | ⏳ Pending Phase 6 | YAML rules table; check_policy_permissions node; stubbed action executors |
| 8 | Case Memory | ⏳ Pending Phase 7 | Write resolved cases to graph; vector-embed summaries; retrieve_similar_cases() |
| 9 | UI / Dashboard | ⏳ Pending Phase 8 | Streamlit: live investigation view, evidence, actions, trigger new case |
| 10 | Benchmark Run | ⏳ Pending Phase 9 + 🔧 dataset spot-check | run_benchmark.py; 20 case answer files |
| 11 | Docs & Submission Prep | ⏳ Pending Phase 10 | blog-post.md draft, final README |

---

## Files Created So Far

```
hhgoa-fraud-agent/
├── .gitignore
├── .env.example
├── requirements.txt
├── agent/
│   ├── __init__.py
│   ├── config.py          # Pydantic settings from .env
│   ├── models.py          # Shared data models (FraudCase, Evidence, AgentState, …)
│   └── run.py             # CLI entrypoint (python -m agent.run)
│   ├── tools/__init__.py
│   ├── memory/__init__.py
│   └── policy/__init__.py
├── graph/__init__.py
├── mcp/__init__.py
├── rag/__init__.py
├── ui/__init__.py
├── tests/__init__.py
├── data/
│   ├── raw/               # gitignored
│   └── processed/         # gitignored
├── cases/
├── docs/
│   └── progress.md        # ← this file
```

---

## Pending Inputs Needed from User

### Phase 1 — ALL DONE ✅
- [x] Dataset README parsed (all columns, answer format, fraud policy, 5 patterns, 20 cases)
- [x] Files downloaded to `data/raw/`: transactions.csv (708MB), identity.csv, closed_cases_history.csv, case_pack.csv, README.md
- [x] Answer format spec extracted (JSON with case / evidence_requests / next_best_actions / sar / stop_reason)
- [x] Fraud Policy 10 rules + 14 actions + approval routes documented
- [x] 5 fraud patterns + 7 pattern enum values documented

### Before Phase 2 can run on live TigerGraph:
- [ ] **User reviews `graph/schema.gsql` and approves it** ← current blocker
- [ ] TigerGraph connection details added to `.env` (TG_HOST, TG_USERNAME, TG_PASSWORD, TG_GRAPH_NAME)

### Before Phase 5 (MCP) can proceed:
- [ ] Clone of https://github.com/tigergraph/tigergraph-mcp confirmed locally

### Before Phase 10 (Benchmark):
- [ ] 🔧 Manual spot-check of several case output files by the user

---

## Key Design Decisions Made

| Decision | Rationale |
|----------|-----------|
| **LangGraph** for orchestration | Best fit: stateful, cyclic (evidence re-gathering loop), human-in-the-loop checkpoints |
| **Pydantic v2 models** as LangGraph state | Type safety across nodes; serializable to JSON for case output |
| **Centralised `agent/config.py`** | Single source of truth for env vars; all modules import Settings, not os.getenv |
| **LLM only for assess/decide/explain nodes** | Pattern detection stays graph-driven (GSQL); LLM cannot substitute |
| **Stubbed action executors** | Real banking integrations out of scope; logged mocks suffice for demo |

## Phase 6 Notes

- `agent/orchestrator.py` now provides the typed LangGraph workflow with injectable evidence and reasoner dependencies.
- Assessment, action proposal, and explanation are the only LLM-facing interfaces; policy routes are assigned and validated deterministically.
- Customer, step-up, and analyst evidence responses are simulated and recorded in state; live case graph writes remain pending Phase 8.
- Offline orchestration coverage is in `tests/test_orchestrator.py`.
