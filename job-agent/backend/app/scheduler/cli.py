from __future__ import annotations

import signal
import sys
import time

from app.observability import get_logger
from app.scheduler import JobScheduler


def main() -> int:
    log = get_logger("scheduler.cli")
    sched = JobScheduler()
    sched.start()
    print("Scheduler running. Registered jobs:")
    for j in sched.list_jobs():
        print(f"  - {j['id']}: next={j['next_run']} trigger={j['trigger']}")
    print("Press Ctrl+C to stop.")

    stop = False

    def _handler(_signum, _frame):
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)

    while not stop:
        time.sleep(1)

    sched.stop()
    log.info("scheduler.cli_exited")
    return 0


if __name__ == "__main__":
    sys.exit(main())
