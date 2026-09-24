"""
agent/run.py — CLI entrypoint for the fraud investigation agent.

Usage:
    python -m agent.run --trigger-file <path/to/trigger.json>
    python -m agent.run --transaction-id <txn_id> --source risk_score
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

try:
    from loguru import logger
except ModuleNotFoundError:  # pragma: no cover - exercised by minimal installs
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

from agent.models import InvestigationTrigger, TriggerSource

app = typer.Typer(help="HHGOA Fraud Investigation Agent")


@app.command()
def run(
    trigger_file: Path = typer.Option(None, "--trigger-file", "-f",
                                       help="Path to a JSON trigger file."),
    transaction_id: str = typer.Option(None, "--transaction-id", "-t",
                                        help="Single transaction ID to investigate."),
    source: TriggerSource = typer.Option(TriggerSource.RISK_SCORE, "--source", "-s",
                                          help="Trigger source type."),
    risk_score: float = typer.Option(None, "--risk-score",
                                      help="Risk score (0‒1) when source=risk_score."),
) -> None:
    """Run a fraud investigation from a trigger file or CLI arguments."""
    # ── Build trigger ─────────────────────────────────────────────────────────
    if trigger_file:
        raw = json.loads(trigger_file.read_text())
        trigger = InvestigationTrigger(**raw)
    elif transaction_id:
        trigger = InvestigationTrigger(
            source=source,
            entity_id=transaction_id,
            entity_type="transaction",
            risk_score=risk_score,
        )
    else:
        logger.error("Provide either --trigger-file or --transaction-id.")
        raise typer.Exit(1)

    logger.info(f"Starting investigation for entity={trigger.entity_id} "
                f"source={trigger.source} trigger_id={trigger.trigger_id}")

    # ── Run agent ────────────────────────────────────────────────────────────
    try:
        from agent.orchestrator import run_investigation  # noqa: PLC0415
    except ModuleNotFoundError as exc:
        if exc.name != "agent.orchestrator":
            raise
        logger.warning("Orchestrator not yet wired — Phase 6 is pending.")
        typer.echo(f"[Phase 0] Trigger parsed OK: {trigger.model_dump_json(indent=2)}")
        return

    case = run_investigation(trigger)
    typer.echo(f"\n✅  Investigation complete. Case ID: {case.case_id}")
    typer.echo(f"   Status : {case.status}")
    typer.echo(f"   Risk   : {case.risk_level}")
    typer.echo(f"   Written to graph: {case.written_to_graph}")


if __name__ == "__main__":
    app()
