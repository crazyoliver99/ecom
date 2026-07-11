"""A minimal, dependency-free interval scheduler (Atlas Autonomy M1).

`run_scheduler` executes a cycle function on a fixed interval, forever, without
any human interaction. It is deliberately tiny: no threads, no external
scheduler, no cron parsing — the operating system's cron (or any supervisor)
launches `atlas schedule`, and this loop paces the work.

Testability: `sleep` is injectable and `max_cycles` bounds the loop, so tests run
a deterministic number of cycles with a no-op sleep. A cycle that raises is
logged and does not stop the loop — one bad night must not end the autonomy.
"""

import logging
import time
from collections.abc import Callable

logger = logging.getLogger(__name__)

CycleFn = Callable[[int], None]


def run_scheduler(
    cycle_fn: CycleFn,
    interval_seconds: float,
    *,
    max_cycles: int | None = None,
    sleep: Callable[[float], None] = time.sleep,
    on_error: Callable[[int, Exception], None] | None = None,
) -> int:
    """Run cycle_fn(cycle_index) every interval_seconds.

    Blocks until max_cycles is reached (or forever if None). Sleeps between
    cycles but not after the final one. Returns the number of cycles executed.
    """
    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be positive")

    cycle = 0
    while max_cycles is None or cycle < max_cycles:
        try:
            cycle_fn(cycle)
        except Exception as exc:  # noqa: BLE001 - one failure must not end the loop
            logger.exception("scheduled cycle %d failed", cycle)
            if on_error is not None:
                on_error(cycle, exc)

        cycle += 1
        is_last = max_cycles is not None and cycle >= max_cycles
        if not is_last:
            sleep(interval_seconds)

    return cycle
