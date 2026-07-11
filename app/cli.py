"""Command-line entry point for operational jobs.

Usage:
    python -m app.cli collect-keepa [--category ID] [--max-products N]

The Keepa collection command runs one pass over a fixed US bestseller category
and persists observations, facts, signals, and events. It reads the API key only
from KEEPA_API_KEY.
"""

import argparse
import sys

from app.collection.keepa_job import (
    DEFAULT_MAX_PRODUCTS,
    DEFAULT_US_CATEGORY_ID,
    run_keepa_collection,
)
from app.core.config import get_settings
from app.core.db import get_session_factory
from app.providers.keepa import KeepaClient, KeepaConfigError


def _cmd_collect_keepa(args: argparse.Namespace) -> int:
    settings = get_settings()
    try:
        client = KeepaClient(settings.keepa_api_key)
    except KeepaConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    session = get_session_factory()()
    try:
        result = run_keepa_collection(
            session,
            client,
            category_id=args.category,
            max_products=args.max_products,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ecom", description="Ecom research operational jobs.")
    sub = parser.add_subparsers(dest="command", required=True)

    keepa = sub.add_parser("collect-keepa", help="Run one Keepa bestseller collection pass.")
    keepa.add_argument(
        "--category",
        type=int,
        default=DEFAULT_US_CATEGORY_ID,
        help=f"Keepa US category node id (default {DEFAULT_US_CATEGORY_ID}).",
    )
    keepa.add_argument(
        "--max-products",
        type=int,
        default=DEFAULT_MAX_PRODUCTS,
        help=f"Max products to enrich per run (default {DEFAULT_MAX_PRODUCTS}).",
    )
    keepa.set_defaults(func=_cmd_collect_keepa)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
