"""Tests for the interval scheduler (no real sleeping, bounded cycles)."""

import pytest
from app.collection.scheduler import run_scheduler


def test_runs_exactly_max_cycles():
    calls = []
    sleeps = []
    ran = run_scheduler(
        lambda i: calls.append(i),
        interval_seconds=60,
        max_cycles=3,
        sleep=sleeps.append,
    )
    assert ran == 3
    assert calls == [0, 1, 2]
    # Sleeps between cycles but not after the last one.
    assert sleeps == [60, 60]


def test_single_cycle_does_not_sleep():
    sleeps = []
    run_scheduler(lambda i: None, interval_seconds=5, max_cycles=1, sleep=sleeps.append)
    assert sleeps == []


def test_cycle_error_does_not_stop_loop():
    seen = []
    errors = []

    def cycle(i):
        seen.append(i)
        if i == 1:
            raise RuntimeError("boom")

    ran = run_scheduler(
        cycle,
        interval_seconds=1,
        max_cycles=3,
        sleep=lambda _s: None,
        on_error=lambda i, exc: errors.append((i, str(exc))),
    )
    assert ran == 3
    assert seen == [0, 1, 2]  # loop continued past the failure
    assert errors == [(1, "boom")]


def test_nonpositive_interval_rejected():
    with pytest.raises(ValueError, match="interval_seconds must be positive"):
        run_scheduler(lambda i: None, interval_seconds=0, max_cycles=1)
