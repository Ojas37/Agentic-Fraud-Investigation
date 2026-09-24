"""Generate the benchmark answer files required by the project contract.

The repository's README defines the exact answer contract for each case in
`cases/`: one JSON object per case with the keys
`case_id`, `case`, `evidence_requests`, `next_best_actions`, `sar`,
`stop_reason`, `tool_calls`, `tokens`, and `latency_s`.

This script reads the canonical case pack and writes those answer files in the
required format. The agent may later replace these placeholder values with
fully-investigated outputs, but the file layout and JSON schema remain fixed.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


ALLOWED_CASE_STATUS = {"open", "closed_fraud", "closed_legitimate", "escalated"}
ALLOWED_VERDICTS = {"fraud", "legitimate", "uncertain"}


def build_case_answer(case_row: dict[str, Any]) -> dict[str, Any]:
    """Build a single benchmark-case answer that matches the project contract."""
    case_id = str(case_row.get("case_id", "")).strip()
    flagged_txn_id = str(case_row.get("flagged_txn_id", "") or "").strip()

    case_payload = {
        "status": "open",
        "verdict": "uncertain",
        "fraud_probability": 0.0,
        "pattern": "none",
        "pattern_description": "",
        "affected_txn_ids": [flagged_txn_id] if flagged_txn_id else [],
        "first_suspicious_txn_id": flagged_txn_id,
        "connected_card_ids": [],
        "connected_device_profiles": [],
        "exposure_usd": 0.0,
        "evidence": [],
        "similar_prior_cases": [],
        "summary": "",
        "written_to_graph": False,
        "graph_case_id": "",
    }

    answer = {
        "case_id": case_id,
        "case": case_payload,
        "evidence_requests": [],
        "next_best_actions": {
            "initial": [],
            "final": [],
            "what_changed": "nothing",
        },
        "sar": {
            "file": False,
            "reason": "",
            "narrative": "",
            "subjects": [],
            "total_amount_usd": 0,
            "activity_dates": [],
        },
        "stop_reason": (
            "Benchmark output template: actual investigation result should be filled by the agent "
            "for this case."
        ),
        "tool_calls": 0,
        "tokens": 0,
        "latency_s": 0.0,
    }

    assert answer["case"]["status"] in ALLOWED_CASE_STATUS
    assert answer["case"]["verdict"] in ALLOWED_VERDICTS
    return answer


def write_case_pack_answers(csv_path: str | Path, output_dir: str | Path) -> list[Path]:
    """Write every benchmark answer file for the project contract."""
    csv_path = Path(csv_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    case_rows = list(csv.DictReader(csv_path.open("r", encoding="utf-8", newline="")))
    written: list[Path] = []

    for row in case_rows:
        answer = build_case_answer(row)
        output_file = output_dir / f"{answer['case_id']}.json"
        output_file.write_text(json.dumps(answer, indent=2), encoding="utf-8")
        written.append(output_file)

    return written


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    csv_path = repo_root / "data" / "raw" / "case_pack.csv"
    output_dir = repo_root / "cases"
    written = write_case_pack_answers(csv_path, output_dir)
    print(f"Wrote {len(written)} benchmark answer files to {output_dir}")


if __name__ == "__main__":
    main()
