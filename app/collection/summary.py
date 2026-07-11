"""Deterministic collection summaries (Atlas Autonomy M1).

`generate_collection_summary` is a pure counting function over what a run
persisted — no LLM, no judgment. It is generated once at the end of a successful
run and stored. `format_summary` renders a stored summary as clean text for
`atlas morning-report`.

Counts are read back from the database by run id (observations, events, facts,
signals) so the summary reflects what was actually persisted, not what the job
believed it did. The only field that lives solely in the run's execution — the
list of provider warnings — is carried in via the result.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.collection.keepa_job import PRODUCT_OBSERVATION_TYPE, KeepaCollectionResult
from app.collection.models import CollectionSummary
from app.ingestion.models import CollectionRun, RawObservation
from app.signals.models import Event, Fact


def _count(session: Session, stmt) -> int:
    return int(session.scalar(stmt) or 0)


def compute_summary_fields(
    session: Session,
    run: CollectionRun,
    result: KeepaCollectionResult,
) -> dict:
    """Pure counting function: the summary's fields derived from what the run
    persisted. No writes — call it as many times as you like and it yields the
    same values, which is what makes the summary deterministic and recomputable."""
    duration_seconds = None
    if run.started_at is not None and run.finished_at is not None:
        duration_seconds = (run.finished_at - run.started_at).total_seconds()

    events_emitted = _count(
        session, select(func.count()).select_from(Event).where(Event.run_id == run.id)
    )
    new_candidates = _count(
        session,
        select(func.count())
        .select_from(Event)
        .where(Event.run_id == run.id, Event.event_type == "NewProductDiscovered"),
    )
    signals_emitted = _count(
        session,
        select(func.count(func.distinct(Event.signal_id))).where(
            Event.run_id == run.id, Event.event_type == "SignalDetected"
        ),
    )
    provider_error_events = session.scalars(
        select(Event).where(Event.run_id == run.id, Event.event_type == "ProviderFailed")
    ).all()
    provider_errors = [e.payload for e in provider_error_events]

    observations_stored = _count(
        session,
        select(func.count())
        .select_from(RawObservation)
        .where(RawObservation.run_id == run.id),
    )
    # One product observation per candidate touched this run.
    candidates_discovered = _count(
        session,
        select(func.count())
        .select_from(RawObservation)
        .where(
            RawObservation.run_id == run.id,
            RawObservation.observation_type == PRODUCT_OBSERVATION_TYPE,
        ),
    )
    existing_candidates_updated = candidates_discovered - new_candidates

    facts_created = _count(
        session,
        select(func.count())
        .select_from(Fact)
        .join(RawObservation, Fact.source_observation_id == RawObservation.id)
        .where(RawObservation.run_id == run.id),
    )

    return {
        "run_id": run.id,
        "status": run.status,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "duration_seconds": duration_seconds,
        "candidates_discovered": candidates_discovered,
        "new_candidates": new_candidates,
        "existing_candidates_updated": existing_candidates_updated,
        "observations_stored": observations_stored,
        "facts_created": facts_created,
        "signals_emitted": signals_emitted,
        "events_emitted": events_emitted,
        "provider_warnings": list(result.provider_warnings),
        "provider_errors": provider_errors,
    }


def generate_collection_summary(
    session: Session,
    run: CollectionRun,
    result: KeepaCollectionResult,
    *,
    now: datetime | None = None,  # noqa: ARG001 - kept for a stable call signature
) -> CollectionSummary:
    """Compute and persist the summary for one (successful) collection run."""
    fields = compute_summary_fields(session, run, result)
    summary = CollectionSummary(**fields)
    session.add(summary)
    session.flush()
    return summary


def get_latest_successful_summary(session: Session) -> CollectionSummary | None:
    """The most recent summary of a succeeded run.

    Ordered by the run's finished_at (a per-run wall-clock time captured in
    Python), so "latest" is deterministic even for summaries written in the same
    DB transaction, where created_at (Postgres now()) would collide."""
    return session.scalar(
        select(CollectionSummary)
        .where(CollectionSummary.status == "succeeded")
        .order_by(
            CollectionSummary.finished_at.desc(),
            CollectionSummary.created_at.desc(),
            CollectionSummary.id.desc(),
        )
        .limit(1)
    )


def get_summary_for_run(session: Session, run_id: uuid.UUID) -> CollectionSummary | None:
    return session.scalar(
        select(CollectionSummary).where(CollectionSummary.run_id == run_id)
    )


def _fmt_ts(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")


def _fmt_duration(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    seconds = float(seconds)
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes}m {secs}s"


def format_summary(summary: CollectionSummary) -> str:
    """Render a stored summary as a clean, human-readable morning report."""
    lines = [
        "Atlas Morning Report",
        "====================",
        "",
        f"Collection run : {summary.run_id}",
        f"Status         : {summary.status}",
        f"Started        : {_fmt_ts(summary.started_at)}",
        f"Finished       : {_fmt_ts(summary.finished_at)}",
        f"Duration       : {_fmt_duration(summary.duration_seconds)}",
        "",
        f"Candidates discovered      : {summary.candidates_discovered}",
        f"  New candidates           : {summary.new_candidates}",
        f"  Existing (updated)       : {summary.existing_candidates_updated}",
        f"Observations stored        : {summary.observations_stored}",
        f"Facts created              : {summary.facts_created}",
        f"Signals emitted            : {summary.signals_emitted}",
        f"Events emitted             : {summary.events_emitted}",
        "",
        f"Provider warnings          : {len(summary.provider_warnings)}",
        f"Provider errors            : {len(summary.provider_errors)}",
    ]
    for warning in summary.provider_warnings:
        lines.append(f"  ⚠ {warning}")
    for err in summary.provider_errors:
        detail = err.get("message") if isinstance(err, dict) else str(err)
        lines.append(f"  ✗ {detail}")
    lines.append("")
    lines.append(f"Report generated from run {summary.run_id} ({_fmt_ts(summary.created_at)}).")
    return "\n".join(lines)
