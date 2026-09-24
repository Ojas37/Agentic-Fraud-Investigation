# Development Roadmap

_Based on the verified repository state on 2026-09-24._

## Phase 1: Stabilize Existing Implementation

1. Preserve and review the uncommitted `mcp/server.py` and `agent/prompts.py` changes.
2. Align every Python query parameter with its installed GSQL signature.
3. Add mocked query-contract tests and make evidence gathering report graph failures explicitly.
4. Remove hard-coded `FraudGraph` from deployment/install paths.
5. Resolve declared/runtime dependency gaps, including `loguru` and `pydantic-settings`.

Expected result: graph evidence calls are trustworthy and the baseline environment starts cleanly.

## Phase 2: Complete TigerGraph Integration

1. Verify schema deployment and all vertex/edge counts against local source files.
2. Add or remove the referenced vector schema deliberately; do not leave an aspirational deployment path.
3. Bound fraud-ring traversal and implement `pattern_filter`.
4. Decide whether the official TigerGraph MCP repository is used directly or the local wrapper is retired.

Expected result: repeatable, documented read/write graph integration.

## Phase 3: Implement Agent Tools and Policy

1. Replace alternate action enums with the exact dataset identifiers: `ALLOW_TRANSACTION`, `DECLINE_TRANSACTION`, `MONITOR_CARD`, `MONITOR_CONNECTED_CARDS`, `WARN_CUSTOMER`, `VERIFY_WITH_CUSTOMER`, `STEP_UP_AUTH`, `BLOCK_CARD`, `BLOCK_ALL_CARDS`, `GENERATE_REPORT`, `CREATE_CASE`, `FILE_REPORT`, `ESCALATE_TO_ANALYST`, `CLOSE_NO_FRAUD`.
2. Implement an executable policy/permission engine for `auto`, `L1`, and `L2` routes.
3. Add mock executors that only execute `auto` actions and log all recommendations.

Expected result: prompts cannot bypass policy.

## Phase 4: Complete Investigation Workflow

Implement typed nodes for trigger, open/update case, evidence gathering, assessment, evidence request, reassessment, decision, permission check, explanation, and memory update. Use LangGraph only where it adds the required stateful loop; keep the graph query layer deterministic.

Expected result: one CLI trigger produces an auditable case record without hardcoded answers.

## Phase 5: Evidence and Uncertainty

1. Add transaction-window and entity-resolution synthesis around the graph query results.
2. Implement customer validation, step-up, and analyst-info simulated responses.
3. Record the request and assumed response exactly as required by the answer format.
4. Implement stopping at settled response or probability/evidence thresholds.

Expected result: initial and final recommendations can differ for a defensible reason.

## Phase 6: GraphRAG and Case Memory

1. Pass synthesized graph findings, policy documents, and prior-case context to the LLM.
2. Add FraudCase graph writes, live-case edges, summary embeddings, and retrieval.
3. Test that a resolved synthetic case can be retrieved by a later similar case.

Expected result: memory is both auditable and operational.

## Phase 7: Benchmark Evaluation

1. Implement `tests/run_benchmark.py` from `case_pack.csv`.
2. Serialize the exact README JSON contract, including SAR defaults and timing/token fields.
3. Run all 20 cases and print a summary without tuning on the benchmark answers.
4. Perform the user's manual spot-check before final changes.

Expected result: 20 answer files in `cases/` and measured, reproducible results.

## Phase 8: UI/UX

Build `ui/app.py` only after the CLI workflow is stable. Show trigger, timeline, evidence, uncertainty, request/response, initial/final actions, approval routes, explanation, and graph-write status. Add a trigger form and live progress display.

## Phase 9: Performance and Security

Measure query latency, retrieval latency, LLM token use, and total case latency. Address TLS verification, secret handling, retry behavior, and large fanout limits.

## Phase 10: Submission

Update README and docs from verified behavior, draft the blog post, prepare a repeatable demo script, and leave video/social publishing to the project owner.

## Immediate Next Task

Implement Phase 1 stabilization first: correct the graph query parameter contract and add a failing-path test that prevents GraphRAG from claiming a complete bundle when graph evidence could not be gathered. This is the smallest change that removes a root cause shared by MCP, GraphRAG, and the future agent.
