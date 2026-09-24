import json
from pathlib import Path

from tests.run_benchmark import build_case_answer


def test_build_case_answer_matches_project_contract():
    case_row = {
        "case_id": "HHG-001",
        "trigger_type": "risk_score",
        "trigger_text": "Real-time model scored transaction 3514030 at 0.61.",
        "flagged_txn_id": "3514030",
        "card_id": "C12382-K1",
        "customer_id": "C12382",
        "risk_score": 0.61,
    }

    answer = build_case_answer(case_row)

    assert answer["case_id"] == "HHG-001"
    assert set(answer.keys()) == {
        "case_id",
        "case",
        "evidence_requests",
        "next_best_actions",
        "sar",
        "stop_reason",
        "tool_calls",
        "tokens",
        "latency_s",
    }
    assert answer["case"]["status"] in {"open", "closed_fraud", "closed_legitimate", "escalated"}
    assert answer["case"]["verdict"] in {"fraud", "legitimate", "uncertain"}
    assert isinstance(answer["evidence_requests"], list)
    assert isinstance(answer["next_best_actions"]["initial"], list)
    assert isinstance(answer["next_best_actions"]["final"], list)
    assert isinstance(answer["sar"]["subjects"], list)
    assert isinstance(answer["sar"]["activity_dates"], list)
    assert answer["tool_calls"] >= 0
    assert answer["tokens"] >= 0
    assert answer["latency_s"] >= 0


def test_run_benchmark_writes_all_case_files(tmp_path):
    csv_path = tmp_path / "case_pack.csv"
    csv_path.write_text(
        "case_id,opened_at,trigger_type,trigger_text,flagged_txn_id,card_id,customer_id,risk_score\n"
        "HHG-001,2016-12-05 01:55:28,risk_score,Trigger text,3514030,C12382-K1,C12382,0.61\n"
        "HHG-002,2016-11-22 23:27:07,risk_score,Trigger text,3478782,C11891-K1,C11891,0.79\n",
        encoding="utf-8",
    )

    output_dir = tmp_path / "cases"
    output_dir.mkdir()

    from tests.run_benchmark import write_case_pack_answers

    write_case_pack_answers(csv_path, output_dir)

    assert (output_dir / "HHG-001.json").exists()
    assert (output_dir / "HHG-002.json").exists()
    payload = json.loads((output_dir / "HHG-001.json").read_text(encoding="utf-8"))
    assert payload["case_id"] == "HHG-001"
