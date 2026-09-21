# Progress Tracker — HHGOA Fraud Investigation Agent

_Last updated: Phase 0 complete_

---

## Phase Status

| Phase | Name | Status | Notes |
|-------|------|--------|-------|
| 0 | Project Scaffolding | ✅ Done | Repo structure, .gitignore, .env.example, requirements.txt, base models, CLI stub |
| 1 | Ingest Real Dataset Info | ⏳ Blocked — waiting for user | Need dataset README, file list, answer format spec, fraud policy, 5 fraud pattern docs |
| 2 | Graph Schema & Ingestion | ⏳ Pending Phase 1 | GSQL schema + loading jobs — must show before running |
| 3 | Fraud Pattern Detection | ⏳ Pending Phase 2 | GSQL queries for shared device fan-out, burst detection, ring detection, case similarity |
| 4 | GraphRAG Layer | ⏳ Pending Phase 3 | `gather_evidence_bundle()`, vector store embedding, policy/pattern doc retrieval |
| 5 | TigerGraph MCP Integration | ⏳ Pending Phase 4 | Wire Phase 3 queries as MCP tools; smoke test |
| 6 | Agent Orchestration Core | ⏳ Pending Phase 5 + 🔧 MCP smoke test | LangGraph graph: trigger → case → evidence → assess → decide → explain → memory |
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

### Before Phase 1 can start:
- [ ] Dataset README contents (paste or attach)
- [ ] Exact file list in `data/raw/` and what each file contains
- [ ] Answer format specification for the 20 benchmark case output files
- [ ] Text of the bank's fraud policy document
- [ ] Text of all five fraud pattern documents

### Before Phase 2 can start:
- [ ] All Phase 1 inputs above
- [ ] TigerGraph connection details (TG_HOST, TG_USERNAME, TG_PASSWORD, TG_GRAPH_NAME)
- [ ] Confirmation dataset has been unzipped to `data/raw/`

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
