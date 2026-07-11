"""Command-line entry point for Atlas operational jobs.

Usage:
    atlas collect-keepa [--category ID] [--max-products N]
    atlas schedule [--interval-seconds S] [--category ID] [--max-products N] [--max-cycles N]
    atlas morning-report

(`python -m app.cli ...` works identically.)

collect-keepa   runs one Keepa collection pass.
schedule        runs collection cycles autonomously on an interval, generating a
                summary after each successful cycle.
morning-report  prints the latest successful collection summary.

The Keepa API key is read only from KEEPA_API_KEY.
"""

import argparse
import sys

from app.collection.autonomy import run_keepa_collection_cycle
from app.collection.keepa_job import (
    DEFAULT_MAX_PRODUCTS,
    DEFAULT_US_CATEGORY_ID,
    run_keepa_collection,
)
from app.collection.scheduler import run_scheduler
from app.collection.summary import format_summary, get_latest_successful_summary
from app.core.config import get_settings
from app.core.db import get_session_factory
from app.providers.keepa import KeepaClient, KeepaConfigError


def _build_client_or_exit() -> KeepaClient | int:
    settings = get_settings()
    try:
        return KeepaClient(settings.keepa_api_key)
    except KeepaConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _cmd_collect_keepa(args: argparse.Namespace) -> int:
    client = _build_client_or_exit()
    if isinstance(client, int):
        return client

    session = get_session_factory()()
    try:
        result = run_keepa_collection(
            session, client, category_id=args.category, max_products=args.max_products
        )
    finally:
        session.close()

    if result.status == "failed":
        print(f"Keepa collection FAILED (run {result.run_id}): {result.error}", file=sys.stderr)
        return 1

    print(
        f"Keepa collection succeeded (run {result.run_id}): "
        f"{result.new_candidates} new candidate(s), "
        f"{result.observations} observation(s), "
        f"{result.facts} fact(s), "
        f"{result.signals} signal(s) {sorted(set(result.signal_types))}"
    )
    return 0


def _cmd_schedule(args: argparse.Namespace) -> int:
    client = _build_client_or_exit()
    if isinstance(client, int):
        return client

    settings = get_settings()
    interval = (
        args.interval_seconds
        if args.interval_seconds is not None
        else settings.keepa_collection_interval_seconds
    )

    def cycle(index: int) -> None:
        session = get_session_factory()()
        try:
            outcome = run_keepa_collection_cycle(
                session, client, category_id=args.category, max_products=args.max_products
            )
        finally:
            session.close()

        result = outcome.result
        if result.status == "succeeded":
            print(
                f"[cycle {index}] run {result.run_id} succeeded: "
                f"{result.new_candidates} new, {result.observations} obs, "
                f"{result.facts} facts, {result.signals} signals"
            )
        else:
            print(
                f"[cycle {index}] run {result.run_id} FAILED: {result.error}",
                file=sys.stderr,
            )

    print(
        f"Atlas scheduler starting: every {interval}s"
        + (f", {args.max_cycles} cycle(s)" if args.max_cycles else ", indefinitely")
    )
    run_scheduler(cycle, interval, max_cycles=args.max_cycles)
    return 0


def _cmd_morning_report(args: argparse.Namespace) -> int:  # noqa: ARG001
    session = get_session_factory()()
    try:
        summary = get_latest_successful_summary(session)
    finally:
        session.close()

    if summary is None:
        print("No successful collection runs yet. Run `atlas collect-keepa` first.")
        return 0

    print(format_summary(summary))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="atlas", description="Atlas operational jobs.")
    sub = parser.add_subparsers(dest="command", required=True)

    def _add_collection_args(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--category",
            type=int,
            default=DEFAULT_US_CATEGORY_ID,
            help=f"Keepa US category node id (default {DEFAULT_US_CATEGORY_ID}).",
        )
        p.add_argument(
            "--max-products",
            type=int,
            default=DEFAULT_MAX_PRODUCTS,
            help=f"Max products to enrich per run (default {DEFAULT_MAX_PRODUCTS}).",
        )

    keepa = sub.add_parser("collect-keepa", help="Run one Keepa bestseller collection pass.")
    _add_collection_args(keepa)
    keepa.set_defaults(func=_cmd_collect_keepa)

    schedule = sub.add_parser(
        "schedule", help="Run collection cycles autonomously on an interval."
    )
    _add_collection_args(schedule)
    schedule.add_argument(
        "--interval-seconds",
        type=float,
        default=None,
        help="Seconds between cycles (default from KEEPA_COLLECTION_INTERVAL_SECONDS).",
    )
    schedule.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Stop after this many cycles (default: run indefinitely).",
    )
    schedule.set_defaults(func=_cmd_schedule)

    report = sub.add_parser(
        "morning-report", help="Print the latest successful collection summary."
    )
    report.set_defaults(func=_cmd_morning_report)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
