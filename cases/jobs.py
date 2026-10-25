"""Job control (non-interactive shapes), traps and signals."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402


def C(cid, title, body, iters=100, setup="", kind="script", **kw):
    return Case(id=cid, title=title, category="jobs", body=body,
                setup=setup, iters=iters, kind=kind, tags=("jobs",), **kw)


CASES = [
    C("jobs.bg_wait_one", "one bg job + wait", "sleep 0.05 & wait", iters=1),
    C("jobs.bg_many@20", "20 bg jobs + wait",
      "for ((j=0; j<20; j++)); do sleep 0.02 & done; wait", iters=20),
    C("jobs.bg_pid_capture", "bg spawn + $! capture loop",
      "for ((j=0; j<50; j++)); do sleep 0 & p=$!; wait $p; done", iters=50),
    C("jobs.kill_term", "spawn, kill -TERM, wait",
      "sleep 30 & p=$!; kill -TERM $p; wait $p 2>/dev/null; rc=$?",
      iters=1),
    C("jobs.kill_check_loop", "kill -0 poll loop",
      "sleep 0.2 & p=$!; while kill -0 $p 2>/dev/null; do :; done",
      iters=1),
    C("jobs.jobs_list_live", "jobs output with live jobs",
      "sleep 0.3 & sleep 0.3 & jobs >/dev/null; wait", iters=2),
    C("jobs.disown_one", "bg + disown", "sleep 0.05 & disown; wait",
      iters=1),
    C("jobs.trap_set_clear", "trap install + clear (loop)",
      "trap 'x=1' USR1; trap - USR1", kind="loop", iters=2000),
    C("jobs.trap_raise@200", "trap delivery: raise USR1 x200",
      "c=0; trap 'c=$((c+1))' USR1; "
      "for ((j=0; j<200; j++)); do kill -USR1 $$; done; echo hits=$c",
      iters=200, expect_out=r"hits=200"),
    C("jobs.trap_exit", "EXIT trap execution",
      "trap 'echo bye' EXIT", kind="process", argv=("-c", "trap 'true' EXIT; :"),
      iters=1),
    C("jobs.trap_debug_stmt", "DEBUG trap per statement",
      "trap 'd=$((d+1))' DEBUG; x=1; y=2; z=3; trap - DEBUG",
      kind="loop", iters=1000, setup="d=0"),
    C("jobs.sigpipe_shape", "yes-style pipe early close (head builtin-side)",
      "printf 'a\\n%.0s' 1 2 3 | head -1 >/dev/null", iters=1),
]
