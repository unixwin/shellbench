"""Hot-loop jobs generator v2: process/job/signal dispatch cost.

Complements ``hotloop_misc_gen.py``'s job section with the deeper
process/job/signal surface: subshell/group fork-cost ladders, command
substitution capture forms, pipeline stage-count and lastpipe shapes,
background-job lifecycle (builtin and external), wait forms and rc
propagation, trap/signal install+deliver+clear churn (including self-USR1
delivery which is safe because the trap is installed first), process
substitution fd lifecycle, coproc fd request/response cycles, and
command-not-found / error-path dispatch.

Safety contract: every body exits 0, is deterministic, and never leaks
processes -- background children are always ``wait``ed (or killed then
waited) within the same iteration; ``sleep 30`` children are always
terminated before the iteration ends; self-signals are only sent to
trapped signals (USR1/USR2/TERM/INT/HUP with a handler installed).
``fg``/``bg`` are only used under ``set -m`` and only on ``sleep 0`` /
SIGSTOP+SIGCONT-bounded jobs.

Rows are (suffix, title, setup, body, iters, extra_tags, files); scripts are
(suffix, title, body, files). Iters: N=10000 cheap, N_SLOW=2000 fork-heavy,
N_SPAWN=500 external spawn, N_TRAP=500 DEBUG-trap-heavy.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

N = 10000
N_SLOW = 2000       # fork / comsub / procsub / builtin-bg cost
N_SPAWN = 500       # external process spawn cost
N_TRAP = 500        # DEBUG-trap-per-command cost

ROWS = []
SCRIPTS = []
_SEQ = {}

SIG = ("cap:posix-signals",)
PATH = ("cap:posix-path",)
DEV = ("cap:devfs",)


def bump(key):
    _SEQ[key] = _SEQ.get(key, 0) + 1
    return _SEQ[key]


def add(suffix, title, setup, body, iters=N, extra=(), files=()):
    ROWS.append((suffix, title, setup, body, iters, tuple(extra), tuple(files)))


def sadd(suffix, title, body, files=()):
    SCRIPTS.append((suffix, title, body, tuple(files)))


# ===========================================================================
# 1. SUBSHELL / GROUP FORK-COST LADDER
# ===========================================================================
# Pure-fork ladder: bare subshell, multi-command, exit codes, nesting depth,
# function calls inside, redirect variants. Groups ({ }) share the fork-cost
# contrast (no fork for the last stage / plain group).

for suffix, title, body in (
    ("subsh_colon", "( : ) bare subshell", "( : )"),
    ("subsh_pair", "( :; : ) two cmds", "( :; : )"),
    ("subsh_triple", "( :; :; : ) three cmds", "( :; :; : )"),
    ("subsh_exit0", "( exit 0 )", "( exit 0 )"),
    ("subsh_exit3", "( exit 3 ) rc propagates", "( exit 3 )"),
    ("subsh_exit7_wait", "( exit 7 ) & wait $!", "( exit 7 ) & wait $!"),
    ("subsh_nest2", "( ( : ) ) depth 2", "( ( : ) )"),
    ("subsh_nest3", "( ( ( : ) ) ) depth 3", "( ( ( : ) ) )"),
    ("subsh_nest_mixed", "( :; ( : ) ) mixed", "( :; ( : ) )"),
    ("subsh_assign", "( x=1; y=$((x+2)) )", "( x=1; y=$((x+2)) )"),
    ("subsh_read", "( read l <<< hi )", "( read l <<< hi )"),
    ("subsh_echo", "( echo x ) >/dev/null", "( echo x ) >/dev/null"),
    ("subsh_echo_devnull_in", "( echo x >/dev/null )", "( echo x >/dev/null )"),
    ("subsh_redir", "( : ) >/dev/null", "( : ) >/dev/null"),
    ("subsh_printf", "( printf 'a\\nb\\n' ) >/dev/null", "( printf 'a\\nb\\n' ) >/dev/null"),
    ("subsh_fn", "( f ) fn call in subshell", "( f )"),
    ("subsh_fn_args", "( f a b c ) fn+args", "( f a b c )"),
    ("subsh_fn_inner", "( f() { local x=$1; :; }; f hi )", "( f() { local x=$1; :; }; f hi )"),
    ("subsh_bg_pair", "( : ) & ( : ) & wait", "( : ) & ( : ) & wait"),
    ("subsh_bg_waitn", "( : ) & ( : ) & wait -n; wait", "( : ) & ( : ) & wait -n; wait"),
):
    setup = "f() { :; }" if "fn" in suffix and "inner" not in suffix else ""
    extra = DEV if "/dev/null" in body else ()
    add("subsh_%s" % suffix.replace("subsh_", ""), title, setup, body,
        N_SLOW, extra)

# Group ({ }) counterparts: no fork for the compound itself.
for suffix, title, setup, body, extra in (
    ("grp_colon", "{ :; } bare group", "", "{ :; }", ()),
    ("grp_pair", "{ :; :; } two cmds", "", "{ :; :; }", ()),
    ("grp_echo", "{ echo x >/dev/null; }", "", "{ echo x >/dev/null; }", DEV),
    ("grp_subsh", "{ ( : ); } group+subshell", "", "{ ( : ); }", ()),
    ("grp_fn", "{ f; } fn call", "f() { :; }", "{ f; }", ()),
    ("grp_assign", "{ x=$((x+1)); } persists", "x=0", "{ x=$((x+1)); }", ()),
    ("grp_redir", "{ :; } >/dev/null", "", "{ :; } >/dev/null", DEV),
    ("grp_nested", "{ { :; }; } nested group", "", "{ { :; }; }", ()),
    ("grp_if", "{ if [ 1 = 1 ]; then :; fi; }", "", "{ if [ 1 = 1 ]; then :; fi; }", ()),
    ("grp_while1", "{ n=0; while n<3 } group+while", "",
     "{ n=0; while [ $n -lt 3 ]; do n=$((n+1)); done; }", ()),
):
    add(suffix, title, setup, body, N if "subsh" not in suffix else N_SLOW, extra)

# ===========================================================================
# 2. COMMAND SUBSTITUTION FORMS
# ===========================================================================
# Capture vs discard, nesting depth, multi-command bodies, pipeline inside.

for suffix, title, body, iters, extra in (
    ("comsub_colon", "x=$( : )", "x=$( : )", N_SLOW, ()),
    ("comsub_true", "x=$(true)", "x=$(true)", N_SLOW, ()),
    ("comsub_false", "x=$(false); :", "x=$(false); :", N_SLOW, ()),
    ("comsub_empty", "x=$()", "x=$()", N_SLOW, ()),
    ("comsub_echo", "x=$(echo hi)", "x=$(echo hi)", N_SLOW, ()),
    ("comsub_echo_null", "x=$(echo hi >/dev/null)", "x=$(echo hi >/dev/null)",
     N_SLOW, DEV),
    ("comsub_printf3", "x=$(printf 'a\\nb\\nc\\n')", "x=$(printf 'a\\nb\\nc\\n')",
     N_SLOW, ()),
    ("comsub_printf_args", "x=$(printf '%s\\n' a b c d)", "x=$(printf '%s\\n' a b c d)",
     N_SLOW, ()),
    ("comsub_multicmd", "x=$(echo a; echo b)", "x=$(echo a; echo b)", N_SLOW, ()),
    ("comsub_herestr", "x=$(cat <<< hi)", "x=$(cat <<< hi)", N_SLOW, ()),
    ("comsub_cat_devnull", "x=$(cat </dev/null)", "x=$(cat </dev/null)",
     N_SPAWN, DEV),
    ("comsub_nested1", "x=$(echo $(echo hi))", "x=$(echo $(echo hi))", N_SLOW, ()),
    ("comsub_nested2", "x=$(echo $(echo $(echo hi)))",
     "x=$(echo $(echo $(echo hi)))", N_SLOW, ()),
    ("comsub_subshell", "x=$( ( : ) ) inner subshell", "x=$( ( : ) )", N_SLOW, ()),
    ("comsub_pipe_builtin", "x=$(echo hi | { read l; echo \"$l\"; })",
     "x=$(echo hi | { read l; echo \"$l\"; })", N_SLOW, ()),
    ("comsub_pipe_cat", "x=$(echo hi | cat)", "x=$(echo hi | cat)", N_SPAWN, ()),
    ("comsub_assign_in", "x=$(y=1; echo $y)", "x=$(y=1; echo $y)", N_SLOW, ()),
    ("comsub_chain2", "x=$(echo hi); y=$(echo $x)", "x=$(echo hi); y=$(echo $x)",
     N_SLOW, ()),
    ("comsub_exec_out", "$(echo :) executes output", "$(echo :)", N_SLOW, ()),
    ("comsub_var_expand", "x=$(echo ${HOME:+hi})", "x=$(echo ${HOME:+hi})",
     N_SLOW, ()),
    ("comsub_if", "x=$(if [ 1 = 1 ]; then echo y; fi)",
     "x=$(if [ 1 = 1 ]; then echo y; fi)", N_SLOW, ()),
    ("comsub_while", "x=$(while read -r l; do echo \"$l\"; done <<< hi)",
     "x=$(while read -r l; do echo \"$l\"; done <<< hi)", N_SLOW, ()),
    ("comsub_arith_val", "x=$((1+2)) literal", "x=$((1+2))", N, ()),
):
    add("comsub_%s" % suffix.replace("comsub_", ""), title, "", body, iters, extra)

# ===========================================================================
# 3. PIPELINE STAGE-COUNT / SHAPE LADDER
# ===========================================================================

for stages in (5, 6, 8):
    pipe = " | ".join(["true"] * stages)
    add("pipe_true%d" % stages, "pipeline %d builtin stages" % stages,
        "", pipe, N_SLOW)

# External-cat ladders.
for suffix, title, body in (
    ("pipe_cat_mixed", "true | cat | cat", "true | cat | cat >/dev/null"),
    ("pipe_cat3", "printf | cat x3", "printf 'x\\n' | cat | cat | cat >/dev/null"),
    ("pipe_cat4", "printf | cat x4", "printf 'x\\n' | cat | cat | cat | cat >/dev/null"),
    ("pipe_cat_echo", "echo | cat | cat | cat", "echo x | cat | cat | cat >/dev/null"),
    ("pipe_cat_devnull_in", "cat </dev/null | cat", "cat </dev/null | cat >/dev/null"),
    ("pipe_cat_devnull_both", "cat </dev/null | cat >/dev/null",
     "cat </dev/null | cat >/dev/null"),
    ("pipe_echo_2err", "echo 2>&1 | cat", "echo x 2>&1 | cat >/dev/null"),
    ("pipe_herestring_cat", "cat <<< | cat", "cat <<< hi | cat >/dev/null"),
    ("pipe_group_producer", "{ echo; } | cat", "{ echo x; } | cat >/dev/null"),
    ("pipe_subshell_stage", "( echo ) | cat", "( echo x ) | cat >/dev/null"),
    ("pipe_subshell_both", "( : ) | ( : )", "( : ) | ( : )"),
    ("pipe_neg_false", "! false", "! false"),
    ("pipe_neg_pipe", "! true | cat", "! true | cat >/dev/null"),
    ("pipe_procsub_mix", "cat <(echo) | cat", "cat <(echo a) | cat >/dev/null"),
):
    iters = N_SPAWN if ("cat" in body or "diff" in body or "sort" in body) else N_SLOW
    add("pipe_%s" % suffix.replace("pipe_", ""), title, "", body, iters,
        DEV if "/dev/null" in body else ())

# Group/while last stages (all-builtin, fork per stage without lastpipe).
for suffix, title, body in (
    ("grp_read1", "echo | { read }", "echo x | { IFS= read -r l; }"),
    ("grp_read2", "printf | { read x2 }", "printf 'a\\nb\\n' | { read -r x; read -r y; :; }"),
    ("grp_readarr", "printf | { read -ra }", "printf 'a b c\\n' | { read -ra arr; :; }"),
    ("grp_echo_stage", "{ echo; } | { read }", "{ echo x; } | { read -r l; }"),
    ("while_read_pipe", "echo | while read", "echo x | while read -r l; do :; done"),
    ("while_read3", "printf3 | while read", "printf 'a\\nb\\nc\\n' | while read -r l; do n=$((n+1)); done"),
    ("pipe_test_stage", "echo | test", "echo x | test -n x"),
    ("pipe_colon_stage", "echo | :", "echo x | :"),
):
    add(suffix, title, "n=0" if "while" in suffix else "", body, N_SLOW)

# lastpipe variants: last stage runs in the current shell.
LP = ("shopt -s lastpipe",)
for suffix, title, body, extra in (
    ("lp_read", "lastpipe echo | read", "echo x | read -r l", LP),
    ("lp_read2", "lastpipe printf | { read x2 }",
     "printf 'a\\nb\\n' | { read -r x; read -r y; echo \"$x$y\" >/dev/null; }", LP),
    ("lp_while", "lastpipe echo | while read",
     "echo x | while read -r l; do :; done", LP),
    ("lp_group_cat", "lastpipe echo | { cat }", "echo x | { cat >/dev/null; }", LP),
):
    add("lp_%s" % suffix.replace("lp_", ""), title, extra[0], body, N_SLOW)

# pipefail interaction.
add("pipefail_false_true", "pipefail false|true", "set -o pipefail",
    "false | true || :")
add("pipefail_true_false", "pipefail true|false", "set -o pipefail",
    "true | false || :")
add("pipefail_true_true", "pipefail true|true", "set -o pipefail",
    "true | true")
add("pipefail_bg", "pipefail pipeline & wait", "set -o pipefail",
    "false | true & wait $!; :", N_SLOW)

# ===========================================================================
# 4. BACKGROUND JOB LIFECYCLE -- BUILTIN CHILDREN (fork, no exec)
# ===========================================================================

for suffix, title, body in (
    ("bg_true_wait", "true & wait", "true & wait"),
    ("bg_true_pid", "true & p=$!; wait $p", "true & p=$!; wait $p"),
    ("bg_echo", "echo hi & wait", "echo hi & wait"),
    ("bg_subsh_echo", "( echo hi ) & wait", "( echo hi ) & wait"),
    ("bg_false_wait", "false & wait $! rc1", "false & wait $!; :"),
    ("bg_false_or", "false & wait $! || :", "false & wait $! || :"),
    ("bg_two_true", "true & true & wait", "true & true & wait"),
    ("bg_three_true", "true & x3 & wait", "true & true & true & wait"),
    ("bg_four_true", "true & x4 & wait", "true & true & true & true & wait"),
    ("bg_mixed", "true & ( : ) & wait", "true & ( : ) & wait"),
    ("bg_seq2", "two sequential spawns", "true & wait; true & wait"),
    ("bg_seq3", "three sequential spawns", "true & wait; true & wait; true & wait"),
    ("bg_pids2", "two pids wait $p1 $p2", "true & p=$!; true & q=$!; wait $p $q"),
    ("bg_pids3", "three pids wait", "true & p=$!; true & q=$!; true & r=$!; wait $p $q $r"),
    ("bg_wait_bang", "true & wait $!", "true & wait $!"),
    ("bg_waitn", "true & true & wait -n; wait", "true & true & wait -n; wait"),
    ("bg_pid_echo", "$! expansion", "true & p=$!; echo $p >/dev/null; wait $p"),
    ("bg_jobs_q", "true & jobs; wait", "true & jobs >/dev/null; wait"),
    ("bg_jobs_l", "true & jobs -l; wait", "true & jobs -l >/dev/null; wait"),
    ("bg_jobs_p", "true & jobs -p; wait", "true & jobs -p >/dev/null; wait"),
    ("bg_jobs_r", "true & jobs -r; wait", "true & jobs -r >/dev/null; wait"),
    ("bg_jobs_s", "true & jobs -s; wait", "true & jobs -s >/dev/null; wait"),
    ("bg_jobs_spec", "true & jobs %1; wait", "true & jobs %1 >/dev/null; wait"),
    ("bg_disown", "true & disown; wait", "true & disown %1; wait"),
    ("bg_kill0", "true & kill -0 $p", "true & p=$!; kill -0 $p 2>/dev/null || :; wait $p"),
    ("bg_subst_rc", "x=$(true) & wait", "x=$(true) & wait"),
):
    add("bg_%s" % suffix.replace("bg_", ""), title, "", body, N_SLOW)

# ===========================================================================
# 5. BACKGROUND JOB LIFECYCLE -- EXTERNAL CHILDREN (sleep 0 / sleep 30)
# ===========================================================================
# sleep 30 children are always TERM/KILLed and waited inside the iteration.

SLEEP0 = "sleep 0"
for suffix, title, body in (
    ("sl_wait_bang", "sleep 0 & wait $!", "sleep 0 & wait $!"),
    ("sl_pids2", "sleep 0 x2 wait $p $q", "sleep 0 & p=$!; sleep 0 & q=$!; wait $p $q"),
    ("sl_pids3", "sleep 0 x3 wait pids", "sleep 0 & p=$!; sleep 0 & q=$!; sleep 0 & r=$!; wait $p $q $r"),
    ("sl_three", "sleep 0 x3 wait", "sleep 0 & sleep 0 & sleep 0 & wait"),
    ("sl_four", "sleep 0 x4 wait", "sleep 0 & sleep 0 & sleep 0 & sleep 0 & wait"),
    ("sl_eight", "sleep 0 x8 wait", " & ".join(["sleep 0"] * 8) + " & wait"),
    ("sl_mixed", "sleep 0 & true & wait", "sleep 0 & true & wait"),
    ("sl_seqpair", "two sequential sleep0", "sleep 0 & wait; sleep 0 & wait"),
    ("sl_seq4", "four sequential sleep0", "sleep 0 & wait; sleep 0 & wait; sleep 0 & wait; sleep 0 & wait"),
    ("sl_par_vs_seq", "par 4 vs seq marker", "sleep 0 & sleep 0 & sleep 0 & sleep 0 & wait"),
    ("sl_jobs_r", "sleep 0 & jobs -r; wait", "sleep 0 & jobs -r >/dev/null; wait"),
    ("sl_jobs_s", "sleep 0 & jobs -s; wait", "sleep 0 & jobs -s >/dev/null; wait"),
    ("sl_jobs_lspec", "sleep 0 & jobs -l %1; wait", "sleep 0 & jobs -l %1 >/dev/null; wait"),
    ("sl_disown_spec", "sleep 0 & disown %1; wait", "sleep 0 & disown %1; wait"),
    ("sl_disown_bare", "sleep 0 & disown; wait", "sleep 0 & disown; wait"),
    ("sl_kill_probe_loop", "sleep30 kill -0 probe x3 then TERM",
     "sleep 30 & p=$!; n=0; while kill -0 $p 2>/dev/null && [ $n -lt 3 ]; do n=$((n+1)); done; kill -TERM $p; wait $p 2>/dev/null"),
):
    add("sl_%s" % suffix.replace("sl_", ""), title, "", body, N_SPAWN, SIG)

# Signal-delivery variants on a spawned sleep 30 (always reaped).
# QUIT/USR1/USR2 do not reliably kill `sleep &` (SIGQUIT is ignored for
# async children without job control; USR1/USR2 use default action), so
# those get a follow-up TERM probe to stay bounded.
for sname in ("TERM", "KILL", "INT", "HUP", "PIPE", "ALRM"):
    body = "sleep 30 & p=$!; kill -%s $p; wait $p 2>/dev/null" % sname
    add("sl_kill_%s" % sname.lower(), "kill -%s bg sleep" % sname, "",
        body, N_SPAWN, SIG)
for sname in ("USR1", "USR2", "QUIT"):
    body = ("sleep 30 & p=$!; kill -%s $p 2>/dev/null; "
            "kill -TERM $p 2>/dev/null; wait $p 2>/dev/null" % sname)
    add("sl_kill_%s" % sname.lower(), "kill -%s bg sleep (+TERM)" % sname, "",
        body, N_SPAWN, SIG)
add("sl_kill_s_term", "kill -s TERM", "",
    "sleep 30 & p=$!; kill -s TERM $p; wait $p 2>/dev/null", N_SPAWN, SIG)
add("sl_kill_sigterm", "kill -SIGTERM name", "",
    "sleep 30 & p=$!; kill -SIGTERM $p; wait $p 2>/dev/null", N_SPAWN, SIG)
add("sl_kill_num15", "kill -15 numeric", "",
    "sleep 30 & p=$!; kill -15 $p; wait $p 2>/dev/null", N_SPAWN, SIG)
add("sl_kill_multi", "kill two sleeps", "",
    "sleep 30 & p=$!; sleep 30 & q=$!; kill -TERM $p $q; wait $p $q 2>/dev/null",
    N_SPAWN, SIG)

# Job control (monitor mode) forms -- verified under bash 5.3 non-interactive.
add("sl_fg_sleep0", "set -m; sleep 0 & fg %1", "set -m",
    "sleep 0 & fg %1 2>/dev/null; wait", N_SPAWN, SIG)
add("sl_bg_stopped", "set -m; STOP+CONT+TERM", "set -m",
    "sleep 30 & p=$!; kill -STOP $p; bg %1 2>/dev/null; kill -TERM $p 2>/dev/null; wait $p 2>/dev/null",
    N_SPAWN, SIG)
add("sl_jobctl_jobs", "set -m; sleep 0 & jobs -l", "set -m",
    "sleep 0 & jobs -l >/dev/null; wait", N_SPAWN)
add("sl_fg_builtin", "set -m; true & fg %1", "set -m",
    "true & fg %1 2>/dev/null; wait", N_SLOW)

# ===========================================================================
# 6. TRAP / SIGNAL CHURN
# ===========================================================================
# Self-delivery is only ever to a trapped signal. USR1/USR2 names carry the
# cap:posix-signals tag; CHLD/PIPE too.

for sname in ("USR1", "USR2", "PIPE", "CHLD", "EXIT", "ERR"):
    add("tr_setclear_%s" % sname.lower(), "trap ':' %s; trap - %s" % (sname, sname),
        "", "trap ':' %s; trap - %s" % (sname, sname), N, SIG)

for sname in ("USR1", "USR2", "TERM", "INT", "HUP"):
    add("tr_self_%s" % sname.lower(), "trap + self kill -%s" % sname,
        "", "trap ':' %s; kill -%s $$" % (sname, sname), N, SIG)
    add("tr_selfclr_%s" % sname.lower(), "trap + self kill + clear",
        "", "trap ':' %s; kill -%s $$; trap - %s" % (sname, sname, sname),
        N, SIG)

add("tr_self_multi_sig", "trap USR1+USR2, deliver both", "",
    "trap ':' USR1 USR2; kill -USR1 $$; kill -USR2 $$", N, SIG)
add("tr_self_sig_prefix", "kill -s USR1 self", "",
    "trap ':' USR1; kill -s USR1 $$", N, SIG)
add("tr_self_counter", "USR1 trap increments counter", "c=0",
    "trap 'c=$((c+1))' USR1; kill -USR1 $$", N, SIG)
add("tr_self_counter2", "USR1+USR2 counter", "c=0",
    "trap 'c=$((c+1))' USR1 USR2; kill -USR1 $$; kill -USR2 $$", N, SIG)
add("tr_ignore_usr1", "trap '' USR1 ignore + deliver", "",
    "trap '' USR1; kill -USR1 $$", N, SIG)
add("tr_ignore_reset", "trap '' then trap - reset", "",
    "trap '' USR1; trap - USR1", N, SIG)
add("tr_pquery", "trap -p query", "", "trap -p >/dev/null")
add("tr_pquery_sig", "trap -p USR1", "", "trap -p USR1 >/dev/null", N, SIG)
add("tr_list", "trap list", "", "trap >/dev/null")
add("tr_clear_unset", "trap - USR1 unset", "", "trap - USR1", N, SIG)
add("tr_kill_l", "kill -l list", "", "kill -l >/dev/null")
add("tr_kill_l_sig", "kill -l USR1", "", "kill -l USR1 >/dev/null", N, SIG)
add("tr_kill_l_num", "kill -l 9", "", "kill -l 9 >/dev/null")
add("tr_kill_probe_self", "kill -0 $$", "", "kill -0 $$")
add("tr_kill_probe_ppid", "kill -0 $PPID", "", "kill -0 $PPID")
add("tr_exit_install", "trap ':' EXIT install", "", "trap ':' EXIT")
add("tr_err_body", "ERR trap fires on false", "trap ':' ERR", "false; :")
add("tr_err_setclear_fire", "ERR trap install+fire+clear", "",
    "trap ':' ERR; false; trap - ERR; :")

# CHLD delivery via child exit.
add("tr_chld_true", "CHLD trap + true & wait", "c=0",
    "trap 'c=$((c+1))' CHLD; true & wait", N_SLOW, SIG)
add("tr_chld_two", "CHLD trap + two children", "c=0",
    "trap 'c=$((c+1))' CHLD; true & true & wait", N_SLOW, SIG)
add("tr_chld_sleep", "CHLD trap + sleep 0", "c=0",
    "trap 'c=$((c+1))' CHLD; sleep 0 & wait", N_SPAWN, SIG)
add("tr_chld_subshell", "CHLD trap + subshell bg", "c=0",
    "trap 'c=$((c+1))' CHLD; ( : ) & wait", N_SLOW, SIG)

# DEBUG trap: fires before every command -- realistic overhead at low iters.
add("tr_debug_persist", "DEBUG trap ':' persistent", "trap ':' DEBUG", ":",
    N_TRAP)
add("tr_debug_counter", "DEBUG trap counter persistent", "trap 'c=$((c+1))' DEBUG; c=0",
    ": ; :", N_TRAP)
add("tr_debug_install", "DEBUG trap install+clear", "",
    "trap ':' DEBUG; :; trap - DEBUG", N_TRAP)
add("tr_debug_counter_cycle", "DEBUG trap install/counter/clear", "c=0",
    "trap 'c=$((c+1))' DEBUG; :; :; trap - DEBUG", N_TRAP)
add("tr_debug_two", "DEBUG trap + 4 cmds", "trap ':' DEBUG",
    ":; :; :; :", N_TRAP)

# ===========================================================================
# 7. WAIT FORMS
# ===========================================================================

for suffix, title, body, iters in (
    ("wait_empty", "wait no jobs", "wait", N),
    ("wait_badpid", "wait 99999 suppressed", "wait 99999 2>/dev/null; :", N),
    ("wait_n_nojobs", "wait -n no jobs", "wait -n 2>/dev/null; :", N),
    ("wait_n_empty", "wait -n then wait", "true & wait -n; wait", N_SLOW),
    ("wait_n_sleep", "wait -n x2 sleep triple", "sleep 0 & sleep 0 & sleep 0 & wait -n; wait -n; wait",
     N_SPAWN),
    ("wait_rc3", "( exit 3 ) & wait $! rc", "( exit 3 ) & wait $!", N_SLOW),
    ("wait_after_disown", "disown then wait empty", "true & disown %1; wait", N_SLOW),
    ("wait_twice", "wait; wait again", "true & wait; wait", N_SLOW),
    ("wait_pid_reaped", "wait $p after reaped", "true & p=$!; wait; wait $p 2>/dev/null; :",
     N_SLOW),
):
    add("wait_%s" % suffix.replace("wait_", ""), title, "", body, iters, SIG
        if "sleep" in body else ())

# ===========================================================================
# 8. PROCESS SUBSTITUTION -- FD LIFECYCLE
# ===========================================================================

for suffix, title, body, iters in (
    ("ps_read_echo", "read < <(echo)", "read x < <(echo hi)", N_SLOW),
    ("ps_read_printf", "read < <(printf 2)", "read x < <(printf 'a\\nb\\n')", N_SLOW),
    ("ps_read_two", "two read < <()", "read a < <(echo x); read b < <(echo y)", N_SLOW),
    ("ps_mapfile", "mapfile < <(printf)", "mapfile -t a < <(printf 'a\\nb\\nc\\n')", N_SLOW),
    ("ps_mapfile1", "mapfile < <(echo)", "mapfile -t a < <(echo hi)", N_SLOW),
    ("ps_while_read", "while read < <(printf3)", "while read -r l; do :; done < <(printf 'a\\nb\\nc\\n')", N_SLOW),
    ("ps_read_arr", "read -ra < <(echo)", "read -ra arr < <(echo 'a b c')", N_SLOW),
    ("ps_fd_dyn_read", "exec {fd}< <(echo) + read + close",
     "exec {fd}< <(echo hi); read x <&$fd; exec {fd}<&-", N_SLOW),
    ("ps_fd_dyn_write", "exec {fd}> >(cat) + write + close",
     "exec {fd}> >(cat >/dev/null); echo hi >&$fd; exec {fd}>&-", N_SPAWN),
    ("ps_cat_echo", "cat <(echo)", "cat <(echo hi) >/dev/null", N_SPAWN),
    ("ps_cat_colon", "cat <(:)", "cat <(:) >/dev/null", N_SPAWN),
    ("ps_cat_printf", "cat <(printf)", "cat <(printf 'a\\nb\\n') >/dev/null", N_SPAWN),
    ("ps_cat_multi", "cat <() x3", "cat <(echo a) <(echo b) <(echo c) >/dev/null", N_SPAWN),
    ("ps_cat_nested", "cat <(cat <(echo))", "cat <(cat <(echo hi)) >/dev/null", N_SPAWN),
    ("ps_cat_deep", "cat <(cat <(cat <(echo)))", "cat <(cat <(cat <(echo hi))) >/dev/null", N_SPAWN),
    ("ps_cat_inpipe", "cat <(echo | cat)", "cat <(echo a | cat) >/dev/null", N_SPAWN),
    ("ps_write_cat", "echo > >(cat)", "echo hi > >(cat >/dev/null)", N_SPAWN),
    ("ps_write_printf", "printf > >(cat)", "printf 'x\\n' > >(cat >/dev/null)", N_SPAWN),
    ("ps_write_group", "{ echo; echo; } > >(cat)", "{ echo a; echo b; } > >(cat >/dev/null)", N_SPAWN),
    ("ps_write_read", "echo > >(read; echo)", "echo hi > >(read x; echo \"$x\" >/dev/null)", N_SLOW),
    ("ps_both_dirs", "cat <() > >()", "cat <(echo in) > >(cat >/dev/null)", N_SPAWN),
    ("ps_diff_same", "diff <() <() same", "diff <(printf 'a\\nb\\n') <(printf 'a\\nb\\n')", N_SPAWN),
    ("ps_comsub_cat", "x=$(cat <(echo))", "x=$(cat <(echo hi))", N_SPAWN),
    ("ps_sort_proc", "sort <(echo)", "sort <(echo hi) >/dev/null", N_SPAWN),
):
    add("ps_%s" % suffix.replace("ps_", ""), title, "", body, iters,
        DEV if "/dev/null" in body else ())

# ===========================================================================
# 9. COPROC FD LIFECYCLE
# ===========================================================================
# Named and unnamed coproc request/response, fd close ordering, inner loops.

for suffix, title, body in (
    ("cp_rr_named", "coproc named req/resp",
     "coproc c { while read -r x; do echo \"got:$x\"; done; }; echo hi >&${c[1]}; read -r r <&${c[0]}; exec {c[1]}>&-; exec {c[0]}<&-; wait"),
    ("cp_rr_unnamed", "coproc unnamed req/resp",
     "coproc { while read -r x; do echo \"got:$x\"; done; }; echo hi >&${COPROC[1]}; read -r r <&${COPROC[0]}; exec {COPROC[1]}>&-; exec {COPROC[0]}<&-; wait"),
    ("cp_rr_3rounds", "coproc 3 req/resp rounds",
     "coproc c { while read -r x; do echo \"$x\"; done; }; for j in 1 2 3; do echo r$j >&${c[1]}; read -r y <&${c[0]}; done; exec {c[1]}>&-; exec {c[0]}<&-; wait"),
    ("cp_cat_drain", "coproc cat drain",
     "coproc c { cat >/dev/null; }; echo x >&${c[1]}; exec {c[1]}>&-; wait"),
    ("cp_printf_drain", "coproc printf drain",
     "coproc c { cat >/dev/null; }; printf 'a\\nb\\n' >&${c[1]}; exec {c[1]}>&-; wait"),
    ("cp_two", "two coprocs", "coproc a { :; }; coproc b { :; }; wait"),
    ("cp_pid", "$COPROC_PID echo", "coproc c { :; }; echo $COPROC_PID >/dev/null; wait"),
    ("cp_read_eof", "coproc read EOF", "coproc c { :; }; read -r r <&${c[0]} 2>/dev/null; exec {c[0]}<&- {c[1]}>&-; wait"),
    ("cp_wait_pid", "wait $COPROC_PID", "coproc c { :; }; wait $COPROC_PID"),
    ("cp_group", "coproc group form", "coproc c { :; :; }; wait"),
):
    iters = N_SPAWN if "cat" in body else N_SLOW
    add("cp_%s" % suffix.replace("cp_", ""), title, "", body, iters,
        DEV if "/dev/null" in body else ())

# ===========================================================================
# 10. COMMAND-NOT-FOUND / ERROR-PATH DISPATCH
# ===========================================================================

for suffix, title, setup, body in (
    ("cnf_plain", "nonexistent cmd", "", "nonexistent_cmd_xyz_abc 2>/dev/null"),
    ("cnf_plain2", "nonexistent cmd 2", "", "definitely_missing_cmd_99 2>/dev/null"),
    ("cnf_dot", "./nonexistent", "", "./nonexistent_xyz_file 2>/dev/null"),
    ("cnf_abs", "abs nonexistent path", "", "/nonexistent-dir-xyz-123/cmd 2>/dev/null"),
    ("cnf_command", "command nonexistent", "", "command nonexistent_xyz 2>/dev/null"),
    ("cnf_builtin", "builtin nonexistent", "", "builtin nonexistent_xyz 2>/dev/null"),
    ("cnf_type", "type nonexistent", "", "type nonexistent_xyz 2>/dev/null"),
    ("cnf_commandv", "command -v nonexistent", "", "command -v nonexistent_xyz 2>/dev/null"),
    ("cnf_eval", "eval nonexistent", "", "eval 'nonexistent_xyz' 2>/dev/null"),
    ("cnf_path_empty", "PATH=/nonexistent cmd", "", "PATH=/nonexistent nonexistent_xyz 2>/dev/null"),
    ("cnf_subshell", "( nonexistent )", "", "( nonexistent_xyz ) 2>/dev/null"),
    ("cnf_comsub", "x=$(nonexistent)", "", "x=$(nonexistent_xyz 2>/dev/null)"),
    ("cnf_bg", "nonexistent & wait", "", "nonexistent_xyz 2>/dev/null & wait 2>/dev/null; :"),
    ("cnf_hash_flush", "hash -r + nonexistent", "", "hash -r; nonexistent_xyz 2>/dev/null"),
):
    iters = 500
    extra = PATH if suffix == "cnf_abs" else ()
    add("err_%s" % suffix.replace("cnf_", ""), title, setup, body, iters, extra)

# Permission / directory / redirection error paths.
add("err_perm_noexec", "./noexec.sh EACCES",
    "printf '#!/bin/sh\\necho hi\\n' > noexec.sh; chmod 644 noexec.sh",
    "./noexec.sh 2>/dev/null", 500)
add("err_isdir", "./adir is a directory", "mkdir -p adir", "./adir 2>/dev/null", 500)
add("err_redir_abs", "redirect to missing dir",
    "", "{ echo x > /nonexistent-dir-xyz/f; } 2>/dev/null", N, PATH)
add("err_redir_append", "append to missing dir",
    "", "{ echo x >> /nonexistent-dir-xyz/f; } 2>/dev/null", N, PATH)
add("err_redir_group", "group redirect fail",
    "", "{ : > /nonexistent-dir-xyz/f; } 2>/dev/null", N, PATH)
add("err_cnf_long", "very long cmd name", "",
    "nonexistent_cmd_with_a_ridiculously_long_name_abcdefghijklmnopqrstuvwxyz_0123456789 2>/dev/null", 500)

# ===========================================================================
# 11. SCRIPT-KIND: job-pipeline aggregator shapes
# ===========================================================================
# {iters} is the ops count; bodies divide it into bounded rounds.

sadd("sc_fanout_true", "fan-out 3 true per round",
     "r=0\nwhile [ $r -lt $(({iters}/25)) ]; do true & true & true & wait; r=$((r+1)); done\n")
sadd("sc_fanout_mixed", "fan-out mixed builtin/subshell",
     "r=0\nwhile [ $r -lt $(({iters}/50)) ]; do true & ( : ) & echo x & wait; r=$((r+1)); done\n")
sadd("sc_fanout_sleep", "fan-out 3 sleep 0 per round",
     "r=0\nwhile [ $r -lt $(({iters}/100)) ]; do sleep 0 & sleep 0 & sleep 0 & wait; r=$((r+1)); done\n")
sadd("sc_seq_spawn", "sequential spawn pairs",
     "r=0\nwhile [ $r -lt $(({iters}/200)) ]; do sleep 0 & wait; sleep 0 & wait; r=$((r+1)); done\n")
sadd("sc_pipe_group_agg", "pipeline into group reader rounds",
     "r=0\nwhile [ $r -lt $(({iters}/50)) ]; do printf 'a\\nb\\nc\\nd\\ne\\n' | { read -r a; read -r b; read -r c; read -r d; read -r e; }; r=$((r+1)); done\n")
sadd("sc_pipe_cat_agg", "printf | cat x3 aggregate",
     "r=0\nwhile [ $r -lt $(({iters}/200)) ]; do printf 'x\\ny\\nz\\n' | cat | cat | cat >/dev/null; r=$((r+1)); done\n")
sadd("sc_coproc_rr", "coproc request/response rounds",
     "coproc c { while read -r x; do echo \"got:$x\"; done; }\n"
     "r=0\nwhile [ $r -lt $(({iters}/200)) ]; do echo ping >&${c[1]}; read -r resp <&${c[0]}; r=$((r+1)); done\n"
     "exec {c[1]}>&-; exec {c[0]}<&-; wait\n")
sadd("sc_trap_count", "USR1 self-signal counting",
     "trap 'n=$((n+1))' USR1\nn=0\n"
     "r=0\nwhile [ $r -lt $(({iters}/50)) ]; do kill -USR1 $$; r=$((r+1)); done\n"
     "trap - USR1\necho \"count=$n\"\n")
sadd("sc_trap_debug", "DEBUG trap counting colons",
     "trap 'n=$((n+1))' DEBUG\nn=0\n"
     "r=0\nwhile [ $r -lt $(({iters}/20)) ]; do :; :; r=$((r+1)); done\n"
     "trap - DEBUG\necho \"dbg=$n\"\n")
sadd("sc_waitn_loop", "wait -n rounds",
     "r=0\nwhile [ $r -lt $(({iters}/100)) ]; do sleep 0 & sleep 0 & wait -n; wait; r=$((r+1)); done\n")
sadd("sc_jobs_audit", "jobs -l audit per spawn",
     "r=0\nwhile [ $r -lt $(({iters}/100)) ]; do sleep 0 & jobs -l >/dev/null; wait; r=$((r+1)); done\n")
sadd("sc_error_path", "command-not-found rounds",
     "r=0\nwhile [ $r -lt $(({iters}/10)) ]; do nonexistent_xyz_abc 2>/dev/null; r=$((r+1)); done\n")
sadd("sc_disown", "spawn + disown rounds",
     "r=0\nwhile [ $r -lt $(({iters}/50)) ]; do sleep 0 & disown %1; r=$((r+1)); done\n")
sadd("sc_nested_fork", "nested subshell bg rounds",
     "r=0\nwhile [ $r -lt $(({iters}/100)) ]; do ( ( ( : ) ) ) & wait; r=$((r+1)); done\n")
sadd("sc_kill_fanout", "kill fan-out sleep 30 rounds",
     "r=0\nwhile [ $r -lt $(({iters}/100)) ]; do sleep 30 & sleep 30 & sleep 30 & sleep 30 & for p in $(jobs -p); do kill -TERM $p; done; wait 2>/dev/null; r=$((r+1)); done\n")
sadd("sc_trap_chld", "CHLD trap + spawn rounds",
     "trap 'n=$((n+1))' CHLD\nn=0\n"
     "r=0\nwhile [ $r -lt $(({iters}/100)) ]; do true & wait; r=$((r+1)); done\n"
     "trap - CHLD\necho \"chld=$n\"\n")
sadd("sc_procsub_rounds", "procsub read rounds",
     "r=0\nwhile [ $r -lt $(({iters}/100)) ]; do read x < <(echo hi); r=$((r+1)); done\n")
sadd("sc_comsub_rounds", "comsub capture rounds",
     "r=0\nwhile [ $r -lt $(({iters}/50)) ]; do x=$(printf 'a\\nb\\nc\\n'); r=$((r+1)); done\n")

# Script tags: signal-using scripts get cap:posix-signals.
SCRIPT_TAGS = {
    "sc_trap_count": SIG,
    "sc_trap_debug": (),
    "sc_kill_fanout": SIG,
    "sc_trap_chld": SIG,
}


# ===========================================================================
def cases() -> list:
    out = []
    for suffix, title, setup, body, iters, extra, files in ROWS:
        out.append(Case(
            id="jobs2_%s" % suffix,
            title="jobs2 %s" % title,
            category="hotloop",
            kind="loop",
            tags=("hotloop", "generated", "v2") + extra,
            setup=setup, body=body, iters=iters, files=files))
    for suffix, title, body, files in SCRIPTS:
        out.append(Case(
            id="jobs2_%s" % suffix,
            title="jobs2 script %s" % title,
            category="hotloop",
            kind="script",
            tags=("hotloop", "generated", "v2") + SCRIPT_TAGS.get(suffix, ()),
            body=body, iters=N, files=files))
    return out
