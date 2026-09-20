from __future__ import annotations

import sys

from aidlc.workers import run_worker


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python -m aidlc.worker_main <dev|qa|review|deploy>")
    run_worker(sys.argv[1])

