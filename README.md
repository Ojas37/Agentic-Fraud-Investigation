# HHGOA Fraud Investigation Agent

> **TigerGraph HHGOA Hackathon Submission**
> An agentic AI system that investigates financial fraud end-to-end — the way a
> human analyst would, but automated, graph-grounded, and explainable.

---

## Overview

This agent:
1. **Triggers** on a fraud signal, customer report, or analyst request
2. **Investigates** via a TigerGraph knowledge graph — traversing transactions,
   accounts, devices, and prior cases
3. **Gathers evidence** using GraphRAG (graph findings + policy/pattern document
   chunks) — synthesised context, not raw data dumps
4. **Assesses** fraud pattern(s), risk level, and confidence
5. **Requests more evidence** when uncertain (step-up auth, customer validation,
   analyst input) — then re-assesses
6. **Decides next actions** within a policy/permission engine
7. **Explains** every decision with full evidence chain
8. **Stores case memory** back to the graph for future investigations

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Graph DB + Vector Store | TigerGraph Savanna / Community Edition |
| Graph Query Language | GSQL + TigerGraph built-in algorithms |
| Agent Framework | LangGraph |
| LLM | Anthropic Claude (configurable) |
| GraphRAG | pyTigerGraph vector search + custom retrieval |
| MCP Exposure | TigerGraph MCP server |
| UI | Streamlit |
| Language | Python 3.11+ |

---

## Quick Start

### 1. Prerequisites
- Python 3.11+
- A running TigerGraph instance (Savanna or Community Edition)
- An LLM API key (Anthropic Claude or OpenAI)
- TigerGraph MCP server cloned: `git clone https://github.com/tigergraph/tigergraph-mcp`

### 2. Install dependencies
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment
```bash
cp .env.example .env
# Edit .env with your TigerGraph and LLM credentials
```

### 4. Load data (after completing Phase 2 setup)
```bash
# See docs/schema.md for GSQL schema and loading job instructions
```

### 5. Start MCP server (after Phase 5 setup)
```bash
# See docs/mcp-setup.md
```

### 6. Run an investigation
```bash
# From a trigger file:
python -m agent.run --trigger-file path/to/trigger.json

# From CLI args:
python -m agent.run --transaction-id TXN123456 --source risk_score --risk-score 0.87
```

### 7. Launch the UI
```bash
streamlit run ui/app.py
```

### 8. Run all 20 benchmark cases
```bash
python tests/run_benchmark.py
# Output → cases/  (one JSON file per case)
```

---

## Repository Structure

```
hhgoa-fraud-agent/
├── data/           # raw + processed dataset (gitignored)
├── graph/          # GSQL schema, loading jobs, algorithms
├── mcp/            # TigerGraph MCP server config + tool wrappers
├── rag/            # GraphRAG retrieval + document embedding
├── agent/
│   ├── config.py   # Centralised settings (loads .env)
│   ├── models.py   # Pydantic data models shared across all nodes
│   ├── run.py      # CLI entrypoint
│   ├── orchestrator.py   # LangGraph graph definition (Phase 6)
│   ├── tools/      # Individual tool implementations
│   ├── memory/     # Case memory read/write
│   └── policy/     # Policy & permission engine
├── cases/          # Generated case output files (benchmark)
├── ui/             # Streamlit analyst dashboard
├── tests/          # Unit + integration tests; run_benchmark.py
├── docs/           # Schema, algorithm, MCP setup, blog post, progress
├── .env.example    # Environment variable template
├── requirements.txt
└── README.md
```

---

## Documentation

- [`docs/progress.md`](docs/progress.md) — Phase-by-phase build status
- [`docs/schema.md`](docs/schema.md) — TigerGraph graph schema _(Phase 2)_
- [`docs/algorithms.md`](docs/algorithms.md) — Fraud detection GSQL queries _(Phase 3)_
- [`docs/mcp-setup.md`](docs/mcp-setup.md) — MCP server setup _(Phase 5)_
- [`docs/blog-post.md`](docs/blog-post.md) — Technical blog post _(Phase 11)_

---

## Status

> 🚧 **Active development** — Phase 0 complete. See [`docs/progress.md`](docs/progress.md) for current status.

---

## Team

Built for the TigerGraph HHGOA Hackathon.
