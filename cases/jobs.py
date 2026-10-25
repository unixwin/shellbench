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

# --- corpus v2 additions: trap density and scripted job-table forms
# (fanout / storm ladders live in generators/v2_gen.py) ---
_V2 = [
    C("jobs.trap_density_mix", "trap 6 signals + clear all (loop)",
      "trap 'x=1' USR1 USR2 PIPE INT TERM HUP; "
      "trap - USR1 USR2 PIPE INT TERM HUP", kind="loop", iters=1000),
    C("jobs.trap_err_loop", "ERR trap fires per failing command",
      "false", kind="loop", iters=2000, setup="c=0; trap 'c=$((c+1))' ERR",
      epilogue="echo hits=$c", expect_out="hits=2000"),
    C("jobs.trap_return_func", "RETURN trap fires per function return",
      "f", kind="loop", iters=1000,
      setup="set -T; c=0; trap 'c=$((c+1))' RETURN; f() { x=1; }",
      epilogue="echo hits=$c", expect_out="hits=1000"),
    C("jobs.bg_staggered_wait", "30 staggered sleeps, wait in spawn order",
      "declare -a pids=(); "
      "for ((j=0; j<30; j++)); do sleep 0.0$((j % 5 + 1)) & "
      "pids+=($!); done; "
      "s=0; for p in \"${pids[@]}\"; do wait $p; s=$((s+$?)); done; "
      "echo $s >/dev/null", iters=30),
    C("jobs.kill_many@30", "spawn 30 sleeps, kill all via jobs -p",
      "for ((j=0; j<30; j++)); do sleep 30 & done; "
      "kill $(jobs -p) 2>/dev/null; wait 2>/dev/null", iters=30),
    C("jobs.jobs_output_parse", "jobs -p of 30 live jobs into array",
      "for ((j=0; j<30; j++)); do sleep 0.3 & done; "
      "mapfile -t jp < <(jobs -p); echo ${#jp[@]} >/dev/null; wait",
      iters=30),
    C("jobs.wait_rc_sum@20", "sum of wait statuses over 20 exit jobs",
      "declare -a ps=(); s=0; "
      "for ((j=0; j<20; j++)); do ( exit $((j % 4)) ) & ps+=($!); done; "
      "for p in \"${ps[@]}\"; do wait $p; s=$((s+$?)); done; echo sum=$s",
      iters=20, expect_out="sum=30"),
    C("jobs.trap_chld_count", "CHLD trap over 50 short bg jobs",
      "c=0; trap 'c=$((c+1))' CHLD; "
      "for ((j=0; j<50; j++)); do true & done; wait; "
      "echo done >/dev/null", iters=50),
]

from dataclasses import replace as _replace  # noqa: E402

CASES += [_replace(c, tags=c.tags + ("v2",)) for c in _V2]
del _replace, _V2
