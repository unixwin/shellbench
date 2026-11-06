"""Hot-loop misc generator v2: remaining dispatch-cost surface.

Complements ``hotloop_gen.py`` (which owns the operator x shape matrices)
with the deeper dispatch families: arithmetic expression depth/structure,
function call machinery at arity/nesting/recursion depth, job & subshell
fork cost, redirection fd churn, command-dispatch prefixes, eval/source
re-entry cost, and script-kind text-processing shapes.

Rows are (suffix, title, setup, body, iters, extra_tags, files); scripts are
(suffix, title, body, files). Bodies must exit 0, be deterministic, and avoid
per-iteration sleeps; fork-heavy rows get N_SLOW iters, external spawns N_SPAWN.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

N = 10000
N_SLOW = 2000      # fork / comsub / procsub / source cost
N_SPAWN = 500      # external process spawn cost

ROWS = []
SCRIPTS = []
_SEQ = {}


def bump(key):
    """Deterministic per-section counter (hash() is salted per process)."""
    _SEQ[key] = _SEQ.get(key, 0) + 1
    return _SEQ[key]


def add(suffix, title, setup, body, iters=N, extra=(), files=()):
    ROWS.append((suffix, title, setup, body, iters, tuple(extra), tuple(files)))


def sadd(suffix, title, body, files):
    SCRIPTS.append((suffix, title, body, tuple(files)))


# ===========================================================================
# 1. ARITHMETIC DEEP
# ===========================================================================
# Expression-depth ladders: nested parens / var-mixed / logic / ternary /
# unary, each crossed with the four evaluation forms $(( )), (( )), let,
# eval.

ARITH_SETUP = "a=7;b=3;c=5;d=11;e=4;f=6;g=9;h=2;i=8;j=5;k=3"
_ARITH_OPS = "+-*/%&|^"
_ARITH_TERMS = ["+b", "-c", "*d", "/e", "%f", "&g", "|h", "^i", "+j", "-k"]


def nest_const(depth):
    e = "1"
    for k in range(depth):
        e = "(%s%s%d)" % (e, _ARITH_OPS[k % len(_ARITH_OPS)], k + 2)
    return e


def nest_var(depth):
    e = "a"
    for k in range(depth):
        e = "(%s%s)" % (e, _ARITH_TERMS[k % len(_ARITH_TERMS)])
    return e


def logic_chain(n):
    parts = []
    for k in range(n):
        parts.append(["(a<%d)" % (3 + k * 5), "(b>=%d)" % k,
                      "(c!=%d)" % (k + 2), "(d<=%d)" % (k + 7)][k % 4])
    joiner = " && " if n % 2 == 0 else " || "
    return "(%s)" % joiner.join(parts)


def tern_nest(n):
    e = "0"
    for k in range(n - 1, -1, -1):
        e = "(__bs_i>%d?%d:%s)" % (k * 1000, k, e)
    return e


def unary_nest(depth):
    e = "a"
    for k in range(depth):
        e = ("-(%s)" if k % 2 == 0 else "~(%s)") % e
    return e


FORMS = [
    ("d", "x=$((%s))"),
    ("c", "((%s))"),
    ("l", "let 'x=%s'"),
    ("e", "eval 'x=$((%s))'"),
]

ARITH_EXPRS = []
for depth in (2, 4, 8):
    ARITH_EXPRS.append(("p%d" % depth, nest_const(depth)))
    ARITH_EXPRS.append(("v%d" % depth, nest_var(depth)))
    ARITH_EXPRS.append(("g%d" % depth, logic_chain(depth)))
    ARITH_EXPRS.append(("t%d" % depth, tern_nest(depth)))
    ARITH_EXPRS.append(("u%d" % depth, unary_nest(depth)))

for ename, expr in ARITH_EXPRS:
    for fname, fmt in FORMS:
        # let needs an assignment target; (( )) needs no x=.
        if fname == "l":
            body = "let 'x=%s'" % expr
        elif fname == "c":
            body = "((%s))" % expr
        elif fname == "e":
            body = "eval 'x=$((%s))'" % expr
        else:
            body = "x=$((%s))" % expr
        add("arith_%s_%s" % (ename, fname),
            "arith depth %s via %s" % (ename, fname),
            ARITH_SETUP, body)

# Comma sequences.
for n in (3, 6, 12, 24):
    seq = ",".join(str(k + 1) for k in range(n))
    add("arith_comma_d_%d" % n, "comma seq $(( )) len %d" % n, "",
        "x=$((%s))" % seq)
    add("arith_comma_c_%d" % n, "comma seq (( )) len %d" % n, "",
        "((%s))" % seq)
# let multi-arg.
for n in (1, 2, 4):
    args = " ".join("'y%d=1'" % k for k in range(n))
    add("arith_let_args_%d" % n, "let argc %d" % n, "", "let %s" % args)

# Ternary min/max selection forms.
for expr, title in (
    ("x=$((a<b?a:b))", "ternary minmax $(( ))"),
    ("((a>b?a:b))", "ternary (( ))"),
    ("let 'x=a<b?a:b'", "ternary let"),
    ("x=$((a>b?(b>c?b:c):(a>c?a:c)))", "ternary nested select"),
):
    add("arith_tern_%d" % bump("tern"), title, ARITH_SETUP, expr)

# Power / shift ladders.
for expr, title in (
    ("x=$((2**3**2))", "pow right-assoc"),
    ("x=$((2**3**2**1))", "pow chain 4"),
    ("x=$((a**b))", "pow vars"),
    ("let 'x=2**8'", "pow let"),
    ("x=$((a<<2>>1))", "shift ladder"),
    ("x=$((a<<1<<2>>1))", "shift chain"),
):
    add("arith_pow_%d" % bump("pow"), title, ARITH_SETUP, expr)

# base#N and radix literals.
for lit in ("2#1010", "8#17", "16#ff", "64#z", "36#z", "10#42",
            "8#777", "16#deadbeef", "64#A", "2#11111111"):
    add("arith_base_%s" % lit.replace("#", "b"), "base#N %s" % lit, "",
        "x=$((%s))" % lit)
add("arith_base_mix", "hex+octal mix", "", "x=$((0xff+010))")
add("arith_base_mix2", "oct+hex mix", "", "x=$((017+0x10))")
add("arith_base_cmd", "base#N (( ))", "", "((16#ff>0))")

# Array-element arithmetic.
ARR_SETUP = "a=(10 20 30 40);b=2;c=5;d=7"
for expr, title in (
    ("x=$((a[__bs_i%4]+b))", "elem index by counter"),
    ("x=$((a[i&3]*b))", "elem index masked"),
    ("((a[1]+=b))", "elem += "),
    ("((a[2]++))", "elem ++"),
    ("x=$((a[b&3]+c))", "elem index var"),
    ("x=$((b[a[0]&3]))", "nested index"),
    ("declare -A h=([k]=5); x=$((h[k]+1))", "assoc elem arith"),
    ("x=$((a[0]+a[1]+a[2]+a[3]))", "elem sum"),
):
    add("arith_arr_%d" % bump("arr"), title, ARR_SETUP, expr)

# Assignment-operator chains (sequences inside one (( ))).
for n in (2, 4, 8):
    chain = ",".join("x+=%d" % (k + 1) for k in range(n))
    add("arith_chain_c_%d" % n, "assign chain (( )) len %d" % n, "x=0",
        "((%s))" % chain)
    add("arith_chain_d_%d" % n, "assign chain $(( )) len %d" % n, "x=0",
        "x=$((%s))" % chain)
add("arith_chain_mix", "mixed assign ops", "x=1;y=2;z=3",
    "((x+=5,y*=3,z^=7))")
add("arith_let_chain", "let assign chain", "x=0;y=0", "let 'x+=1' 'y+=2'")

# C-style for((;;)) nested inside the body + arithmetic-driven while/until.
for bound in (1, 3, 8):
    for inner_name, inner in (("nop", ":"), ("inc", "((j++))"),
                              ("acc", "x=$((x+j))")):
        add("arith_nestfor_%d_%s" % (bound, inner_name),
            "nested for((;;)) bound %d inner %s" % (bound, inner_name),
            "x=0" if inner_name == "acc" else "",
            "for ((j=0;j<%d;j++)); do %s; done" % (bound, inner))
add("arith_nestfor_2lvl", "two-level for((;;))", "",
    "for ((j=0;j<2;j++)); do for ((k=0;k<3;k++)); do :; done; done")
add("arith_nestfor_2lvl_arith", "two-level for((;;)) arith", "",
    "for ((j=0;j<2;j++)); do for ((k=0;k<3;k++)); do ((j*k)); done; done")
for bound in (3, 10):
    add("arith_while_%d" % bound, "while ((x<%d))" % bound, "",
        "x=0; while ((x<%d)); do x=$((x+1)); done" % bound)
add("arith_until", "until ((x>=3))", "",
    "x=0; until ((x>=3)); do x=$((x+1)); done")

# Arithmetic inside (( )) comparisons / [[ ]].
add("arith_cmp_incr", "((i+1<5000))", "i=3", "((i+1<5000))")
add("arith_cmp_var", "((i*2>j))", "i=3;j=5", "((i*2>j))")
add("arith_cmp_dollar", "[[ $((i+1)) -lt 5 ]]", "i=3",
    "[[ $((i+1)) -lt 5 ]]")
add("arith_cmp_mod", "((i%2==0))", "i=3", "((i%2==0))")

# Same expression through four evaluation forms.
for expr, title in (
    ("a*b+c-d", "mul-add-sub"),
    ("(a+b)*(c-d)", "paren product"),
    ("a**2%b+1", "pow mod add"),
    ("a<<2|b>>1", "shift or"),
):
    for fname, fmt in FORMS:
        if fname == "l":
            body = "let 'x=%s'" % expr
        elif fname == "c":
            body = "((%s))" % expr
        elif fname == "e":
            body = "eval 'x=$((%s))'" % expr
        else:
            body = "x=$((%s))" % expr
        add("arith_form_%s_%d" % (fname, bump("form_" + fname)),
            "arith form %s %s" % (fname, title), ARITH_SETUP, body)

# declare -i integer-attribute arithmetic on plain assignment.
add("arith_decl_i_add", "declare -i n; n=n+1", "declare -i n=5", "n=n+1")
add("arith_decl_i_mix", "declare -i n; n=n*2+1", "declare -i n=5", "n=n*2+1")

# ===========================================================================
# 2. FUNCTION DEEP
# ===========================================================================
ARITIES = (0, 1, 2, 3, 4, 6, 8, 12, 16)

FN_BODIES = [
    ("empty", ":"),
    ("local1", "local y=1; :"),
    ("local3", "local a=1 b=2 c=3; :"),
    ("arith", "local y=0; ((y++)); :"),
    ("echo", "echo x >/dev/null"),
    ("params", "local n=$#; local p=$1; :"),
    ("shift", "shift 2>/dev/null || :; local p=$1; :"),
]
FN_EXTRA_BODIES = [
    ("evalin", "eval 'x=1'; :", (0, 1, 4, 16)),
    ("arrlocal", "local -a a=(1 2 3); :", (0, 1, 4, 16)),
    ("dflt", ': "${1:-d}"; :', (0, 1, 4, 16)),
    ("ro", "local -r r=1; :", (0, 1, 4, 16)),
    ("comsub", "local y=$(true); :", (0, 1, 4)),
]


def call_args(arity):
    return " ".join("a%d" % k for k in range(arity))


for arity in ARITIES:
    args = call_args(arity)
    for bname, inner in FN_BODIES:
        call = "f %s" % args if args else "f"
        add("fn_%s_%d" % (bname, arity),
            "fn %s arity %d" % (bname, arity),
            "f() { %s; }" % inner, call)
for bname, inner, arities in FN_EXTRA_BODIES:
    for arity in arities:
        args = call_args(arity)
        call = "f %s" % args if args else "f"
        add("fn_%s_%d" % (bname, arity),
            "fn %s arity %d" % (bname, arity),
            "f() { %s; }" % inner, call, N_SLOW if bname == "comsub" else N)

# Nested call chains f0 -> f1 -> ... -> leaf.
for depth, leaf_name, leaf_inner in (
    (2, "colon", ":"),
    (4, "colon", ":"),
    (8, "colon", ":"),
    (2, "arith", "local y=0; ((y++))"),
    (4, "arith", "local y=0; ((y++))"),
    (8, "arith", "local y=0; ((y++))"),
):
    defs = []
    for k in range(depth):
        defs.append("f%d() { f%d; }" % (k, k + 1))
    defs.append("f%d() { %s; }" % (depth, leaf_inner))
    add("fn_nest_%d_%s" % (depth, leaf_name),
        "fn nest depth %d leaf %s" % (depth, leaf_name),
        "; ".join(defs), "f0")

# Bounded recursion through the function-call machinery.
FIB_DEF = ("fib() { local n=$1; if ((n<2)); then return $n; fi; "
           "fib $((n-1)); local a=$?; fib $((n-2)); local b=$?; "
           "return $((a+b)); }")
FACT_DEF = ("fact() { local n=$1 r=1; while ((n>1)); do "
            "r=$((r*n)); n=$((n-1)); done; return $r; }")
for n in (6, 8, 10):
    add("fn_rec_fib_%d" % n, "recursive fib(%d)" % n, FIB_DEF, "fib %d; :" % n)
for n in (5, 6, 7):
    add("fn_rec_fact_%d" % n, "recursive fact(%d)" % n, FACT_DEF,
        "fact %d; :" % n)

# Positional/special parameters inside functions.
for fname, inner, call in (
    ("dollar_at_loop", 'local n=0; for x in "$@"; do n=$((n+1)); done; :',
     "g a b c d"),
    ("dollar_star", 'echo "$*" >/dev/null', "g a b c"),
    ("dollar_hash", "local n=$#; :", "g a b c d e"),
    ("dollar_q", "local r=$?; :", "g"),
    ("dollar_zero", "echo $0 >/dev/null", "g"),
    ("dollar_dash", "echo $- >/dev/null", "g"),
    ("dollar_pid", "local p=$$; :", "g"),
    ("shift1", "shift; local p=$1; :", "g a b c"),
    ("shift2", "shift 2; local p=$1; :", "g a b c d"),
):
    add("fn_%s" % fname, "fn %s" % fname, "g() { %s; }" % inner, call)
add("fn_dollar_q_prev", "fn $? sees prior rc", "g() { local r=$?; :; }",
    "false; g")

# declare -f / -F / typeset dumps of a defined function.
for cmd in ("declare -f f", "declare -F f", "typeset -f f",
            "declare -f"):
    add("fn_dump_%d" % bump("dump"), "dump %s" % cmd,
        "f() { local x=1; :; }", "%s >/dev/null" % cmd)

# Nameref parameters.
add("fn_nameref_g", "declare -n ref global", "out=0; g() { declare -n r=out; r=$((r+1)); }",
    "g")
add("fn_nameref_arg", "declare -n ref $1", "out=0; g() { declare -n r=$1; r=2; }",
    "g out")

# Function redefinition churn inside the loop body.
add("fn_redef_same", "redefine + call", "f() { :; }",
    "f() { local x=1; :; }; f")
add("fn_redef_arity", "redefine arity change", "f() { :; }",
    "f() { local a=$1 b=$2; :; }; f x y")
add("fn_redef_unset", "unset -f + redefine", "f() { :; }",
    "unset -f f; f() { :; }; f")
add("fn_redef_two", "redefine two fns", "f() { :; }",
    "f() { :; }; g() { f; }; g")

# function keyword form vs () form.
add("fn_kw_form", "function f { } keyword", "function hf { :; }", "hf")
add("fn_kw_paren", "function f() { }", "function hp() { :; }", "hp")

# Return-code propagation shapes.
for name, inner in (
    ("rc_const", "return 3"),
    ("rc_var", "local n=7; return $n"),
    ("rc_lastcmd", "false"),
):
    add("fn_%s" % name, "fn %s" % name, "f() { %s; }" % inner, "f; :")
add("fn_command_v", "command -v finds function", "f() { :; }",
    "command -v f >/dev/null")

# ===========================================================================
# 3. JOBS / SUBSHELL (bounded; no real sleeps)
# ===========================================================================
add("job_subshell_fork", "( : ) subshell per-iter", "", "( : )", N_SLOW)
add("job_group_nofork", "{ :; } group per-iter", "", "{ :; }")
add("job_subshell_bg", "( : ) & wait", "", "( : ) & wait", N_SLOW)
add("job_group_bg", "{ :; } & wait", "", "{ :; } & wait", N_SLOW)

# Builtin pipelines of increasing stage count.
for stages in (2, 3, 4):
    pipe = " | ".join(["true"] * stages)
    add("job_pipe_%d" % stages, "pipeline %d builtin stages" % stages,
        "", pipe, N_SLOW)
add("job_pipe_echo_cat", "echo | cat", "", "echo x | cat >/dev/null", N_SLOW)
add("job_pipe_printf_cat", "printf | cat", "",
    "printf 'a\\nb\\n' | cat >/dev/null", N_SLOW)
add("job_pipe_echo_cat_cat", "echo | cat | cat", "",
    "echo x | cat | cat >/dev/null", N_SLOW)
add("job_pipe_group", "echo | { read; }", "",
    "echo x | { read y; echo $y >/dev/null; }", N_SLOW)
add("job_pipe_subst_stage", "( : ) | cat", "", "( : ) | cat >/dev/null", N_SLOW)

# Background job + wait shapes (external sleep spawn).
for name, body in (
    ("bgwait_plain", "sleep 0 & wait"),
    ("bgwait_pid", "sleep 0 & p=$!; wait $p"),
    ("bgwait_jobs", "sleep 0 & jobs >/dev/null; wait"),
    ("bgwait_two", "sleep 0 & sleep 0 & wait"),
    ("bgwait_disown", "sleep 0 & p=$!; disown; wait $p"),
    ("bgwait_jobs_l", "sleep 0 & jobs -l >/dev/null; wait"),
    ("bgwait_jobs_p", "sleep 0 & jobs -p >/dev/null; wait"),
    ("bgwait_waitn", "sleep 0 & sleep 0 & wait -n; wait"),
):
    add("job_%s" % name, "job %s" % name, "", body, N_SPAWN)
add("job_jobs_empty", "jobs with no jobs", "", "jobs >/dev/null")
add("job_bang_pipe", "! pipeline", "", "! true | true", N_SLOW)

# Coproc minimal forms (verified under bash 5.3).
add("job_coproc_simple", "coproc { :; }; wait", "",
    "coproc { :; }; wait", N_SLOW)
add("job_coproc_named", "coproc c { :; }; wait", "",
    "coproc c { :; }; wait", N_SLOW)
add("job_coproc_io", "coproc read + echo", "",
    "coproc c { read x; }; echo hi >&${c[1]}; wait", N_SLOW)

# Signal/job-control safe forms: TERM a spawned sleep, kill -0 probe.
SIG = ("cap:posix-signals",)
add("job_kill_term", "kill -TERM bg sleep", "",
    "sleep 30 & p=$!; kill -TERM $p; wait $p", N_SPAWN, SIG)
add("job_kill_probe", "kill -0 bg sleep", "",
    "sleep 30 & p=$!; kill -0 $p && kill -TERM $p; wait $p", N_SPAWN, SIG)
add("job_kill_usr1_sleep", "kill -USR1 ignored? use -0", "",
    "sleep 30 & p=$!; kill -0 $p; kill -TERM $p; wait $p 2>/dev/null",
    N_SPAWN, SIG)

# ===========================================================================
# 4. REDIRECTION DEEP
# ===========================================================================
# exec fd open/close churn across fd numbers.
for fd in (3, 4, 5, 7, 8, 9):
    add("redir_exec_open_%d" % fd, "exec %d>/dev/null + close" % fd, "",
        "exec %d>/dev/null; exec %d>&-" % (fd, fd), extra=("cap:devfs",))
    if fd in (3, 4, 5, 9):
        add("redir_exec_dup_%d" % fd, "exec %d>&1 + close" % fd, "",
            "exec %d>&1; exec %d>&-" % (fd, fd))
# Reopen same fd without close (fd slot reused; no leak).
add("redir_exec_reopen", "exec 9>/dev/null reopen", "",
    "exec 9>/dev/null", extra=("cap:devfs",))
add("redir_exec_dup_reopen", "exec 9>&1 reopen", "", "exec 9>&1")
# Dynamic fd allocation {fd}.
add("redir_dynfd_file", "exec {fd}>/dev/null churn", "",
    "exec {fd}>/dev/null; echo x >&$fd; exec {fd}>&-", extra=("cap:devfs",))
add("redir_dynfd_dup", "exec {fd}>&1 churn", "",
    "exec {fd}>&1; echo x >&$fd; exec {fd}>&-", extra=("cap:devfs",))
# Per-command fd duplication.
for op in ("3>&1", "4>&2", "5<&0"):
    add("redir_dup_%s" % op.replace(">&", "d").replace("<&", "d"),
        "per-command dup %s" % op, "", ": %s" % op)
add("redir_dup_echo", "echo 3>&1 >/dev/null", "",
    "echo x 3>&1 >/dev/null")
add("redir_dup_echo2", "echo 4>&2 >/dev/null", "",
    "echo x 4>&2 >/dev/null")

# Real fixture file append/truncate churn.
for op, title in ((">>", "append"), (">", "truncate")):
    add("redir_file_%s" % ("app" if op == ">>" else "trunc"),
        "echo x %s bench.tmp" % op, "", "echo x %s bench.tmp" % op)
add("redir_file_printf", "printf >> bench.tmp", "",
    "printf 'x\\n' >> bench.tmp")
add("redir_file_i", "echo $__bs_i >> bench.tmp", "",
    "echo $__bs_i >> bench.tmp")

# stderr file redirects.
add("redir_err_app", "echo >&2 2>>err.txt", "",
    "echo x >&2 2>>err.txt")
add("redir_err_trunc", "echo 2>err2.txt", "", "echo x 2>err2.txt")
add("redir_all_app", "echo >>all.txt 2>&1", "",
    "echo x >>all.txt 2>&1")

# Here-strings.
add("redir_herestring_read", "read <<< ", "", "read x <<< hi")
add("redir_herestring_ifs", "IFS=: read <<< ", "",
    "IFS=: read -r a b <<< x:y")
add("redir_herestring_arr", "read -ra <<< ", "", "read -ra arr <<< 'a b c'")
add("redir_herestring_cat", "cat <<< ", "", "cat <<< hi >/dev/null", N_SLOW)
add("redir_herestring_var", "cat <<< $v", "v=hello", "cat <<< \"$v\" >/dev/null",
    N_SLOW)

# Here-docs with literal newlines in the body.
add("redir_heredoc_cat", "cat <<EOF", "",
    "cat <<EOF\nx\nEOF\n>/dev/null", N_SLOW)
add("redir_heredoc_cat5", "cat <<EOF 5 lines", "",
    "cat <<EOF\na\nb\nc\nd\ne\nEOF\n>/dev/null", N_SLOW)
add("redir_heredoc_while", "while read <<EOF", "n=0",
    "while read -r l; do n=$((n+1)); done <<EOF\nx\ny\nz\nEOF", N_SLOW)
add("redir_heredoc_read", "read <<EOF", "",
    "read l <<EOF\nhello\nEOF", N_SLOW)

# Process substitution read/write forms.
add("redir_procsub_cat", "cat <(echo)", "",
    "cat <(echo hi) >/dev/null", N_SLOW)
add("redir_procsub_colon", "cat <(:)", "", "cat <(:) >/dev/null", N_SLOW)
add("redir_procsub_write", "echo > >(cat)", "",
    "echo hi > >(cat >/dev/null)", N_SLOW)
add("redir_procsub_read", "read < <(echo)", "",
    "read x < <(echo hi)", N_SLOW)
add("redir_procsub_printf", "cat <(printf 2 lines)", "",
    "cat <(printf 'a\\nb\\n') >/dev/null", N_SLOW)

# Redirect ordering / fd closing.
add("redir_order_21", "2>&1 then >/dev/null", "",
    "echo x 2>&1 >/dev/null")
add("redir_order_12", ">/dev/null then 2>&1", "",
    "echo x >/dev/null 2>&1")
add("redir_stderr_null", "2>/dev/null", "", "echo x 2>/dev/null")
add("redir_close_stdout", "{ echo >&-; }", "",
    "{ echo x >&-; } 2>/dev/null")
add("redir_close_stdin", "cat <&-", "", "cat <&- 2>/dev/null || :", N_SLOW)
add("redir_close_stderr", "echo 2>&-", "", "echo x 2>&- >/dev/null")
add("redir_devnull_rw", "cat <>/dev/null", "",
    "cat <>/dev/null", N_SLOW, ("cap:devfs",))

# ===========================================================================
# 5. COMMAND DISPATCH
# ===========================================================================
# command / builtin prefixes over the same target set.
for pre in ("command", "builtin"):
    for tgt, args in (("true", ""), (":", ""), ("echo", "x >/dev/null"),
                      ("pwd", ">/dev/null"), ("test", "1 -eq 1"),
                      ("[", "x = x ]")):
        suffix_t = tgt.replace("[", "bracket")
        body = "%s %s %s" % (pre, tgt, args)
        add("disp_%s_%s" % (pre, suffix_t),
            "%s %s" % (pre, tgt), "", body.strip())

# Lookup / type / hash-table forms.
for body, title in (
    ("command -v ls >/dev/null", "command -v external"),
    ("command -v echo >/dev/null", "command -v builtin"),
    ("command -pv ls >/dev/null", "command -pv"),
    ("type echo >/dev/null", "type builtin"),
    ("type -t echo >/dev/null", "type -t"),
    ("type -a echo >/dev/null", "type -a"),
    ("type -p ls >/dev/null", "type -p"),
):
    add("disp_lookup_%d" % bump("lookup"), title, "", body)

# hash builtin effects.
add("disp_hash_r", "hash -r flush", "", "hash -r")
add("disp_hash_r_ls", "hash -r; hash ls", "", "hash -r; hash ls")
add("disp_hash_add", "hash ls", "", "hash ls")
add("disp_hash_d", "hash -p /usr/bin/printf + call", "",
    "hash -p /usr/bin/printf hp; hp 'x\\n' >/dev/null", N_SPAWN,
    ("cap:posix-path",))
add("disp_hash_p", "hash -p /bin/echo + call", "",
    "hash -p /bin/echo he; he x >/dev/null", N_SPAWN, ("cap:posix-path",))

# External absolute-path dispatch.
for cmd in ("/bin/true", "/bin/echo x", "/usr/bin/printf 'x\\n'",
            "/usr/bin/env true", "/usr/bin/[ x = x ]",
            "/usr/bin/nice /bin/true", "/bin/pwd"):
    safe = cmd.split()[0].replace("/", "_")
    add("disp_ext_%s" % safe, "external %s" % cmd, "",
        "%s >/dev/null" % cmd if "echo" not in cmd and "printf" not in cmd
        else cmd + " >/dev/null", N_SPAWN, ("cap:posix-path",))

# Aliases (expand_aliases in setup; whole loop parsed after setup runs).
add("disp_alias_echo", "alias -> echo", "shopt -s expand_aliases; alias mxe='echo x >/dev/null'",
    "mxe")
add("disp_alias_true", "alias -> true", "shopt -s expand_aliases; alias mxt='true'",
    "mxt")
add("disp_alias_cmp", "alias -> compound", "shopt -s expand_aliases; alias mxc='x=1; y=2'",
    "mxc")
add("disp_alias_churn", "alias define/use/unalias via eval",
    "shopt -s expand_aliases", "eval \"alias az='true'; az; unalias az\"")

# Name shadowing: function overrides builtin/external dispatch.
add("disp_shadow_true", "fn shadows builtin true", "true() { :; }", "true")
add("disp_shadow_ls", "fn shadows external ls", "ls() { :; }", "ls")
add("disp_shadow_echo", "fn shadows builtin echo", "echo() { :; }", "echo x")
add("disp_shadow_pwd", "fn shadows builtin pwd", "pwd() { echo /x; }",
    "pwd >/dev/null")

# enable -n / enable churn on a builtin (no echo use inside window).
add("disp_enable_churn", "enable -n + enable echo", "",
    "enable -n echo; enable echo")

# ===========================================================================
# 6. SCRIPT-KIND: realistic hot text-processing shapes over fixtures.
# ===========================================================================
DATA = (("data.txt", "@gen:lines:100000"),)
KV = (("kv.txt", "@gen:kv:100000"),)

sadd("script_read_count", "while read count lines",
     "n=0\nwhile IFS= read -r l; do n=$((n+1)); done < data.txt\nprintf '%d\\n' \"$n\"\n",
     DATA)
sadd("script_field_len", "set -- split + field len",
     "t=0\nwhile IFS= read -r l; do set -- $l; t=$((t+${#2})); done < data.txt\n",
     DATA)
sadd("script_field_num", "set -- split + numeric field sum",
     "s=0\nwhile read -r l; do set -- $l; s=$((s+$2)); done < data.txt\n",
     DATA)
sadd("script_state_case", "case state machine over lines",
     "c=0\nwhile read -r l; do case $l in line*) c=$((c+1));; esac; done < data.txt\n",
     DATA)
sadd("script_state_glob", "glob match count",
     "c=0\nwhile read -r l; do case $l in *lorem*) c=$((c+1));; esac; done < data.txt\n",
     DATA)
sadd("script_read_a", "read -ra fields",
     "t=0\nwhile read -ra f; do t=$((t+${#f[@]})); done < data.txt\n",
     DATA)
sadd("script_upper_len", "${l^^} + length accumulate",
     "t=0\nwhile read -r l; do u=${l^^}; t=$((t+${#u})); done < data.txt\n",
     DATA)
sadd("script_mapfile_for", "mapfile then for over array",
     "mapfile -t a < data.txt\nfor l in \"${a[@]}\"; do :; done\n",
     DATA)
sadd("script_mapfile_idx", "mapfile then indexed while",
     "mapfile -t a < data.txt\ni=0\nwhile [ $i -lt ${#a[@]} ]; do l=${a[$i]}; i=$((i+1)); done\n",
     DATA)
sadd("script_kv_parse", "IFS= kv parse into assoc",
     "declare -A h\nwhile IFS='=' read -r k v; do h[$k]=$v; done < kv.txt\n",
     KV)
sadd("script_kv_count", "kv parse field count",
     "c=0\nwhile IFS='=' read -r k v; do c=$((c+1)); done < kv.txt\n",
     KV)
sadd("script_prefix_strip", "prefix strip + concat",
     "t=0\nwhile read -r l; do x=${l#line }; t=$((t+${#x})); done < data.txt\n",
     DATA)
sadd("script_subst_len", "parameter expansion length",
     "t=0\nwhile read -r l; do t=$((t+${#l})); done < data.txt\n",
     DATA)

# ===========================================================================
# 7. EVAL / SOURCE
# ===========================================================================
for s, title in (
    ("x=1", "eval const assign"),
    ("x=$((1+2))", "eval const arith"),
    ("x=$((1+2*3-4))", "eval const arith2"),
    ("x=1; y=2; z=x+y", "eval multi assign"),
    ("if [ 1 = 1 ]; then x=1; fi", "eval if-fi"),
    ("for j in 1 2 3; do x=$((x+1)); done", "eval for-done"),
    ("x=0; while [ $x -lt 3 ]; do x=$((x+1)); done", "eval while"),
    ("case a in a) y=1;; esac", "eval case"),
    ("echo hi >/dev/null", "eval echo redirect"),
    ("f() { :; }; f", "eval fn def+call"),
    ("eval 'x=1'", "eval nested eval"),
    ("", "eval empty"),
):
    setup = "x=0;y=0;z=0" if ("x" in s or "y" in s or "z" in s) else ""
    add("eval_%d" % bump("eval"), title, setup,
        "eval '%s'" % s.replace("'", "'\\''") if s else "eval ''")

# eval of variable-held strings.
add("eval_var_simple", "eval $s simple", "s='x=$((1+2))'", 'eval "$s"')
add("eval_var_loop", "eval $s loop", "s='for j in 1 2; do :; done'",
    'eval "$s"')
add("eval_var_if", "eval $s if", "s='if [ 1 = 1 ]; then x=1; fi'",
    'eval "$s"')
add("eval_var_args", "eval with positional args", "",
    "eval 'echo \"$1\" >/dev/null' _ hi")
add("eval_rc_false", "eval false rc", "", "eval 'false'")
add("eval_rc_true", "eval true rc", "", "eval 'true'")

# source / . per-iteration re-entry.
LIB = (("lib.sh", "x=1\ny=2\n"),)
LIB2 = (("lib2.sh", "".join("v%d=%d\n" % (k, k) for k in range(20))),)
for body, title, files in (
    ("source lib.sh", "source lib.sh", LIB),
    (". lib.sh", ". lib.sh", LIB),
    ("source ./lib.sh", "source ./lib.sh", LIB),
    ("source lib.sh a b", "source lib.sh args", LIB),
    (". ./lib.sh", ". ./lib.sh", LIB),
    ("source lib2.sh", "source lib2.sh (20 assigns)", LIB2),
):
    add("src_%d" % bump("src"), title, "", body, N_SLOW, files=files)


# ===========================================================================
def cases() -> list:
    out = []
    for suffix, title, setup, body, iters, extra, files in ROWS:
        out.append(Case(
            id="misc2_%s" % suffix,
            title="misc2 %s" % title,
            category="hotloop",
            kind="loop",
            tags=("hotloop", "generated", "v2") + extra,
            setup=setup, body=body, iters=iters, files=files))
    for suffix, title, body, files in SCRIPTS:
        out.append(Case(
            id="misc2_%s" % suffix,
            title="misc2 script %s" % title,
            category="hotloop",
            kind="script",
            tags=("hotloop", "generated", "v2"),
            body=body, iters=N, files=files))
    return out
