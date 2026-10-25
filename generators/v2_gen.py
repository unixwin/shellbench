"""Corpus v2 generator: scale ladders and matrix completions.

Where v1's generators expand operator/builtin/expansion tables, this
module expands *dimensions*: the same shape at several sizes (pipe
depth, procsub count, fanout, string length, file states, argument
counts...), plus the printf float/bigint forms and the deep arithmetic
forms v1 did not have. All cases carry the ``v2`` tag so the expansion
can be listed / verified / timed separately:

    python3 bench.py list --tag v2
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402


def _c(cid, title, category, body, iters=3000, setup="", kind="loop",
       tags=(), **kw):
    return Case(id=cid, title=title, category=category, body=body,
                setup=setup, iters=iters, kind=kind,
                tags=(category, "generated", "v2") + tuple(tags), **kw)


# ---------------------------------------------------------------------------
# printf: float / bigint / padding forms (builtin_gen covers %s, %d %f basic,
# -v %s and format reuse; these are the forms it does not have)
# ---------------------------------------------------------------------------

_PRINTF = [
    ("float_f", "printf %f", "printf '%f' 3.14159 >/dev/null", 3000),
    ("float_e", "printf %e", "printf '%e' 271828.1828 >/dev/null", 3000),
    ("float_g", "printf %g", "printf '%g' 0.000012345 >/dev/null", 3000),
    ("float_p2", "printf %.2f", "printf '%.2f' 3.14159 >/dev/null", 3000),
    ("float_p10", "printf %.10f", "printf '%.10f' 3.1415926535 >/dev/null",
     3000),
    ("float_a", "printf %a hex float", "printf '%a' 3.14159 >/dev/null", 3000),
    ("float_w15", "printf %15.3f pad", "printf '%15.3f|' 3.14159 >/dev/null",
     3000),
    ("float_l15", "printf %-15.3f left pad",
     "printf '%-15.3f|' 3.14159 >/dev/null", 3000),
    ("int_big_d", "printf %d int64 max",
     "printf '%d' 9223372036854775807 >/dev/null", 3000),
    ("int_big_x", "printf %x int64", "printf '%x' 9223372036854775807 "
     ">/dev/null", 3000),
    ("int_big_o", "printf %o int64", "printf '%o' 1234567890123 >/dev/null",
     3000),
    ("int_neg_u", "printf %u of -1", "printf '%u' -1 >/dev/null", 3000),
    ("char_num", "printf %c from code", "printf '%c' 65 >/dev/null", 3000),
    ("quote_q", "printf %q quoting", "printf '%q' 'a b|c$d' >/dev/null", 3000),
    ("esc_b", "printf %b escapes", r"printf '%b' 'a\tb\nc' >/dev/null", 3000),
    ("v_float", "printf -v with %.3f", "printf -v x '%.3f' 2.71828", 3000),
    ("recycle_pairs", "printf format recycle x6 pairs",
     "printf '%s=%d;' a 1 b 2 c 3 d 4 e 5 f 6 >/dev/null", 2000),
    ("s_pad24", "printf %24s pad", "printf '%24s|' word >/dev/null", 3000),
    ("d_zeropad", "printf %012d zero pad", "printf '%012d' 42 >/dev/null",
     3000),
    ("d_plus", "printf %+d sign", "printf '%+d' 42 >/dev/null", 3000),
    ("d_space", "printf % d space sign", "printf '% d' 42 >/dev/null", 3000),
]


def _printf_cases():
    out = [_c("builtin.printf_%s" % suf, "builtin printf: " + t, "builtin",
              body, iters=n, tags=("printf",))
           for suf, t, body, n in _PRINTF]
    out.append(_c("builtin.v2_mapfile_delim", "builtin mapfile: -d ',' split",
                  "builtin", "mapfile -d , -t arr <<< 'a,b,c,d,e'",
                  iters=1000, tags=("mapfile",)))
    out.append(_c("builtin.v2_readarray_n", "builtin readarray: -n 3",
                  "builtin", "readarray -n 3 -t arr < data.txt", iters=300,
                  files=(("data.txt", "@gen:lines:100"),),
                  tags=("mapfile",)))
    out.append(_c("builtin.v2_echo_e_long", "builtin echo: -e long escapes",
                  "builtin",
                  r"echo -e 'one\ttwo\nthree\rRETURN\x41\x42' >/dev/null",
                  iters=2000, tags=("echo",)))
    return out


# ---------------------------------------------------------------------------
# arithmetic: deep / wide forms the operator matrix does not reach
# ---------------------------------------------------------------------------

_ARITH_SETUP = "a=17; b=5; c=3; v=305419896"

_ARITH2 = [
    ("deep_nest", "deeply nested parens",
     "x=$(( ((((((((a + b)))))))) * ((a << 2) - b) ))", 5000),
    ("pow_chain", "power chain", "x=$(( (a ** 2) ** 2 + b ** 3 ))", 5000),
    ("bigint_div", "int64 divide/mod chain",
     "x=$(( (1 << 62) / 7 % 1000003 ))", 5000),
    ("bigint_mask", "wide shift + mask",
     "x=$(( (v << 20 | b) & 0xFFFFFFFFFF ))", 5000),
    ("ternary_nest", "nested ternary",
     "x=$(( a > b ? b > 3 ? a * b : a + b : b ))", 5000),
    ("comma_assign", "comma + embedded assigns",
     "x=$(( (c = 3, c *= a, c + b) ))", 5000),
    ("incdec_subscript", "subscript i++ cycling",
     "x=${arr[(i++) % 16]}", 5000),
    ("assign_ops", "compound assign chain",
     "x=$(( (c += a) * (c -= b) + (c <<= 1) ))", 5000),
    ("base_ladder", "base#n ladder 64/36/16",
     "x=$(( 64#z + 36#zz + 16#FF + 8#17 ))", 5000),
    ("logic_mix", "logic + ternary mix",
     "x=$(( a > b && b > 0 || a == 17 ? a * b : -1 ))", 5000),
    ("bitfield", "bitfield extract", "x=$(( (v >> 8) & 0xFF ))", 8000),
    ("neg_pow", "unary minus vs power", "x=$(( -a ** 2 + b ))", 8000),
]


def _arith_cases():
    out = []
    for suf, t, body, n in _ARITH2:
        setup = _ARITH_SETUP
        if "arr[" in body:
            setup += "; arr=(0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15); i=0"
        out.append(_c("arith.v2_%s" % suf, "arith v2: " + t, "arith",
                      body, iters=n, setup=setup, tags=("arith",)))
    return out


# ---------------------------------------------------------------------------
# expand: parameter forms x string scale (short / mid / long)
# ---------------------------------------------------------------------------

_EXP_STR = {
    "s": "alpha_beta_gamma.txt",
    "m": "dir_" + "segment_" * 24 + "file_name.tar.gz",
    "l": "seg/" * 800 + "alpha_beta_" * 200 + "file.tar.gz",
}
_EXP_OFF = {"s": 2, "m": 100, "l": 2500}
_EXP_FORMS = [
    ("length", "${#v}"),
    ("substr_mid", "${v:{O}:20}"),
    ("substr_from", "${v:{O}}"),
    ("substr_neg", "${v: -20}"),
    ("prefix_rm_short", "${v#*/}"),
    ("prefix_rm_long", "${v##*/}"),
    ("suffix_rm_short", "${v%.*}"),
    ("suffix_rm_long", "${v%%.*}"),
    ("replace_first", "${v/alpha/ALPHA}"),
    ("replace_all", "${v//a/A}"),
    ("upper_all", "${v^^}"),
    ("lower_all", "${v,,}"),
    ("replace_anchor_head", "${v/#seg/SEG}"),
    ("replace_anchor_tail", "${v/%.gz/.zip}"),
    ("substr_expr", "${v: ({O} > 10 ? {O} : 1):10}"),
]


_EXP_ITERS = {"s": 3000, "m": 1000, "l": 200}


def _expand_scale_cases():
    out = []
    for suf, expr in _EXP_FORMS:
        for scale in ("s", "m", "l"):
            body = "x=" + expr.replace("{O}", str(_EXP_OFF[scale]))
            out.append(_c("expand.scale_%s@%s" % (suf, scale),
                          "param form %s at scale %s" % (suf, scale),
                          "expand", body, iters=_EXP_ITERS[scale],
                          setup="v='%s'" % _EXP_STR[scale],
                          tags=("scale",)))
    return out


# ---------------------------------------------------------------------------
# strings: core ops x length ladder (content "abcd" repeated)
# ---------------------------------------------------------------------------

def _str_setup(var, length, extra=""):
    return ("%s=; for ((j=0; j<%d; j++)); do %s+=abcd; done"
            % (var, length // 4, var)) + extra


_STR_OPS = [
    ("len", "x=${#s}", ""),
    ("substr", None, ""),          # offset filled per rung below
    ("replace_all", "x=${s//bc/BC}", ""),
    ("compare_eq", "[[ $s == $t ]]", "twin"),
    ("pattern_tail", "[[ $s == *abcd ]]", ""),
    ("upper_all", "x=${s^^}", ""),
    ("prefix_rm_long", "x=${s##*b}", ""),
    ("copy_append", "t2=$s; t2+=tail", ""),
]


def _strings_ladder_cases():
    out = []
    for length in (100, 10000, 100000):
        for suf, body, extra in _STR_OPS:
            b = body
            if suf == "substr":
                b = "x=${s:%d:64}" % (length // 2)
            setup = _str_setup("s", length)
            if extra == "twin":
                setup += "; " + _str_setup("t", length)
            # greedy pattern removal is superlinear in length; keep
            # its base iteration count proportionally small (autorange
            # scales fast cases back up when timing for real)
            n = 1000
            if suf == "prefix_rm_long":
                n = {100: 1000, 10000: 500, 100000: 100}[length]
            out.append(_c("strings.lad_%s@%d" % (suf, length),
                          "string op %s on %d chars" % (suf, length),
                          "strings", b, iters=n, setup=setup,
                          tags=("ladder", "scale")))
    return out


# ---------------------------------------------------------------------------
# arrays: shapes x size rungs (script kind; iters = elements)
# ---------------------------------------------------------------------------

def _arr_fill(n):
    return "a=(); for ((j=0; j<%d; j++)); do a[j]=$j; done" % n


def _arr_fill_assoc(n):
    return ("declare -A m=(); for ((j=0; j<%d; j++)); "
            "do m[k$j]=$j; done" % n)


_ARR_FILL = "__FILL__"          # setup placeholder: indexed fill, per-rung
_ARR_FILL_ASSOC = "__FILL_ASSOC__"

_ARR_SHAPES = [
    ("fill_idx", "a=()", "for ((j=0; j<{n}; j++)); do a[j]=$j; done; "
     "x=${#a[@]}"),
    ("fill_append", "a=()", "for ((j=0; j<{n}; j++)); do a+=(v$j); done; "
     "x=${#a[@]}"),
    ("fill_assoc", "declare -A m=()", "for ((j=0; j<{n}; j++)); "
     "do m[k$j]=$j; done; x=${#m[@]}"),
    ("read_seq", _ARR_FILL, "s=0; for ((j=0; j<{n}; j++)); "
     "do s=$((s + a[j])); done; echo $s >/dev/null"),
    ("read_pseudo", _ARR_FILL, "s=0; for ((j=0; j<{n}; j++)); "
     "do s=$((s + a[(j * 37) % {n}])); done; echo $s >/dev/null"),
    ("iterate_atq", _ARR_FILL, "for e in \"${a[@]}\"; do c=$((c+1)); done"),
    ("assoc_keys_iter", _ARR_FILL_ASSOC,
     "for k in \"${!m[@]}\"; do x=${m[$k]}; done"),
    ("copy", _ARR_FILL, "b=(\"${a[@]}\"); x=${#b[@]}"),
]

def _arrays_ladder_cases():
    out = []
    for n in (100, 10000):
        for suf, setup_t, body_t in _ARR_SHAPES:
            if setup_t == _ARR_FILL:
                setup = _arr_fill(n)
            elif setup_t == _ARR_FILL_ASSOC:
                setup = _arr_fill_assoc(n)
            else:
                setup = setup_t
            out.append(_c("arrays.lad_%s@%d" % (suf, n),
                          "array shape %s at n=%d" % (suf, n), "arrays",
                          body_t.replace("{n}", str(n)), iters=n,
                          setup=setup + "; c=0", kind="script",
                          tags=("ladder", "scale"), timeout=300.0))
    return out


# ---------------------------------------------------------------------------
# cond: file tests x filesystem states
# ---------------------------------------------------------------------------

_COND_FILES = (("empty.txt", ""), ("full.txt", "@gen:lines:10"),
               ("somedir/inner.txt", "x\n"))
_COND_STATES = [("missing", "no_such_xyz_42"), ("empty", "empty.txt"),
                ("full", "full.txt")]


def _cond_matrix_cases():
    out = []
    for test in ("e", "f", "d", "s", "r", "w"):
        for state, path in _COND_STATES:
            if test == "w" and state == "missing":
                continue
            out.append(_c("cond.fs_%s_%s" % (test, state),
                          "[[ -%s %s ]]" % (test, state), "cond",
                          "[[ -%s %s ]]" % (test, path), iters=4000,
                          files=_COND_FILES, tags=("fsmatrix",)))
    out.append(_c("cond.fs_d_dir", "[[ -d directory ]]", "cond",
                  "[[ -d somedir ]]", iters=4000, files=_COND_FILES,
                  tags=("fsmatrix",)))
    out.append(_c("cond.fs_nt_pair", "[ full -nt empty ]", "cond",
                  "[ full.txt -nt empty.txt ]", iters=3000,
                  files=_COND_FILES, tags=("fsmatrix",)))
    out.append(_c("cond.fs_ef_self", "[ file -ef itself ]", "cond",
                  "[ case.sh -ef case.sh ]", iters=3000,
                  tags=("fsmatrix",)))
    return out


# ---------------------------------------------------------------------------
# control: case-branch scale, nesting ladders
# ---------------------------------------------------------------------------

def _case_stmt(patterns, hit):
    parts = ["case $v in"]
    for i in range(patterns):
        parts.append(" p%d) x=%d;;" % (i, i))
    parts.append(" *) x=0;; esac")
    return "".join(parts)


def _control_ladder_cases():
    out = []
    for p in (8, 32, 128):
        out.append(_c("control.case_scale@%d" % p,
                      "case with %d patterns, last hits" % p, "control",
                      _case_stmt(p, p - 1), iters=2000,
                      setup="v=p%d" % (p - 1), tags=("ladder",)))
    out.append(_c("control.case_scale_first@128",
                  "case with 128 patterns, first hits", "control",
                  _case_stmt(128, 0), iters=2000, setup="v=p0",
                  tags=("ladder",)))
    for d in (2, 4, 8, 16):
        body = "if true; then " * d + "x=1; " + "fi; " * d
        out.append(_c("control.nest_if@%d" % d, "if nesting depth %d" % d,
                      "control", body.rstrip("; "), iters=1500,
                      tags=("ladder", "nest")))
    for d in (2, 4, 8):
        body = "(" * d + " x=1 " + ")" * d
        out.append(_c("control.nest_subshell@%d" % d,
                      "subshell nesting depth %d" % d, "control", body,
                      iters=800, tags=("ladder", "nest")))
    return out


# ---------------------------------------------------------------------------
# funcs: argument-count / local-count / call-chain ladders
# ---------------------------------------------------------------------------

def _funcs_ladder_cases():
    out = []
    for k in (0, 1, 2, 4, 8, 16, 32):
        args = " ".join("w%d" % i for i in range(k))
        out.append(_c("funcs.lad_argc@%d" % k, "call with %d args" % k,
                      "funcs", ("f " + args).rstrip(), iters=3000,
                      setup="f() { x=$#; }", tags=("ladder",)))
    for k in (1, 4, 16, 64):
        decls = " ".join("v%d=%d" % (i, i) for i in range(k))
        out.append(_c("funcs.lad_locals@%d" % k,
                      "call with %d locals" % k, "funcs", "f", iters=3000,
                      setup="f() { local %s; x=$v0; }" % decls,
                      tags=("ladder",)))
    for d in (2, 5, 10, 25, 50):
        defs = []
        for i in range(d):
            nxt = "g%d" % (i + 1) if i + 1 < d else ":"
            defs.append("g%d() { %s; }" % (i, nxt))
        out.append(_c("funcs.lad_chain@%d" % d, "call chain depth %d" % d,
                      "funcs", "g0", iters=1500, setup="; ".join(defs),
                      tags=("ladder",)))
    return out


# ---------------------------------------------------------------------------
# jobs: fanout and trap-storm ladders
# ---------------------------------------------------------------------------

def _jobs_ladder_cases():
    out = []
    for n in (10, 50, 200, 1000):
        out.append(_c("jobs.lad_fanout@%d" % n,
                      "%d background builtins + wait" % n, "jobs",
                      "for ((j=0; j<%d; j++)); do true & done; wait" % n,
                      iters=n, kind="script", tags=("ladder", "spawn")))
    for n in (100, 1000, 5000):
        out.append(_c("jobs.lad_storm@%d" % n,
                      "USR1 trap storm x%d" % n, "jobs",
                      "c=0; trap 'c=$((c+1))' USR1; "
                      "for ((j=0; j<%d; j++)); do kill -USR1 $$; done; "
                      "echo hits=$c" % n,
                      iters=n, kind="script", tags=("ladder", "trap"),
                      expect_out="hits=%d" % n))
    for n in (10, 50):
        out.append(_c("jobs.lad_waitfan@%d" % n,
                      "%d background sleeps + wait" % n, "jobs",
                      "for ((j=0; j<%d; j++)); do sleep 0.02 & done; wait"
                      % n, iters=n, kind="script", tags=("ladder", "spawn")))
    return out


# ---------------------------------------------------------------------------
# mixed: realistic shapes x input sizes (script kind, @gen fixtures)
# ---------------------------------------------------------------------------

_MIXED_SHAPES = [
    ("csv_colsum", "sum last csv column",
     "s=0; while IFS=, read -r a b c d e f; do s=$((s+f)); "
     "done < data.txt; echo $s >/dev/null", "@gen:csv:{n}"),
    ("words_freq", "assoc word frequency (first field)",
     "declare -A m=(); while read -r w rest; do "
     "m[$w]=$(( ${m[$w]:-0} + 1 )); done < data.txt; x=${#m[@]}",
     "@gen:words:{n}"),
    ("path_transform", "path .txt -> .md transform",
     "while IFS= read -r p; do b=${p##*/}; d=${p%/*}; "
     "echo \"$d/${b%.txt}.md\"; done < data.txt >/dev/null", "@gen:path:{n}"),
    ("kv_stats", "kv sum + max",
     "s=0; mx=0; while IFS== read -r k v; do s=$((s+v)); "
     "(( v > mx )) && mx=$v; done < data.txt; echo $s $mx >/dev/null",
     "@gen:kv:{n}"),
    ("words_dedupe", "assoc dedupe with order count",
     "declare -A seen=(); o=0; while read -r w rest; do "
     "if [[ -z ${seen[$w]:-} ]]; then seen[$w]=1; o=$((o+1)); fi; "
     "done < data.txt; echo $o >/dev/null", "@gen:words:{n}"),
    ("csv_two_pass", "two passes over csv (count, then filter)",
     "n=0; while IFS=, read -r a b c d e f; do n=$((n+1)); done < data.txt; "
     "m=0; while IFS=, read -r a b c d e f; do "
     "(( f > 25 )) && m=$((m+1)); done < data.txt; echo $n $m >/dev/null",
     "@gen:csv:{n}"),
]


def _mixed_shape_cases():
    out = []
    for suf, t, body, fixture in _MIXED_SHAPES:
        for n in ((5000, 50000) if "csv" in suf else (5000, 20000)):
            out.append(_c("mixed.gen_%s@%d" % (suf, n),
                          "mixed shape: %s (n=%d)" % (t, n), "mixed",
                          body, iters=n, kind="script",
                          files=(("data.txt", fixture.format(n=n)),),
                          tags=("shape",), timeout=300.0))
    return out


# ---------------------------------------------------------------------------
# subst: nesting depth and capture-volume ladders
# ---------------------------------------------------------------------------

def _subst_ladder_cases():
    out = []
    for d in (2, 3, 5, 8, 13):
        s = "hi"
        for _ in range(d):
            s = "$(echo %s)" % s
        out.append(_c("subst.lad_nest@%d" % d,
                      "command substitution nested %d deep" % d, "subst",
                      "x=" + s, iters=200, tags=("ladder", "nest")))
    for n in (100, 1000, 10000):
        out.append(_c("subst.lad_volume@%d" % n,
                      "capture %d generated lines" % n, "subst",
                      "x=$(for ((j=0; j<%d; j++)); do echo \"line $j\"; "
                      "done); n=${#x}" % n,
                      iters=n, kind="script", tags=("ladder",),
                      timeout=300.0))
    for k in (2, 4, 8, 16, 32):
        body = "cat " + " ".join("<(echo a)" for _ in range(k)) \
            + " >/dev/null"
        out.append(_c("subst.lad_procsub@%d" % k,
                      "%d process substitutions into cat" % k, "subst",
                      body, iters=60, tags=("ladder", "spawn")))
    for n in (1000, 20000):
        out.append(_c("subst.lad_procsub_read@%d" % n,
                      "read %d lines from process substitution" % n,
                      "subst",
                      "c=0; while IFS= read -r l; do c=$((c+1)); "
                      "done < <(for ((j=0; j<%d; j++)); "
                      "do echo \"row $j\"; done); echo $c >/dev/null" % n,
                      iters=n, kind="script", tags=("ladder",),
                      timeout=300.0))
    for d in (2, 4, 8):
        out.append(_c("subst.lad_subshell@%d" % d,
                      "subshell nesting depth %d" % d, "subst",
                      "(" * d + "x=1" + ")" * d, iters=800,
                      tags=("ladder", "nest")))
    return out


# ---------------------------------------------------------------------------
# redir: pipeline depth, fd count, heredoc size ladders
# ---------------------------------------------------------------------------

def _redir_ladder_cases():
    out = []
    for d in (2, 3, 5, 8, 13, 21):
        body = "printf 'seed\\n' | " + " | ".join(["cat"] * d) \
            + " >/dev/null"
        out.append(_c("redir.lad_pipe@%d" % d, "pipeline of %d cats" % d,
                      "redir", body, iters=40 if d >= 13 else 100,
                      tags=("ladder", "spawn")))
    for k in (4, 8, 16, 32):
        opens = "; ".join("exec %d>/dev/null" % fd
                          for fd in range(3, 3 + k))
        out.append(_c("redir.lad_fdcount@%d" % k,
                      "writes across %d open fds" % k, "redir",
                      "fd=$((3 + __bs_i %% %d)); echo x >&$fd" % k,
                      iters=3000, setup=opens, tags=("ladder",)))
    for n in (10, 100, 1000):
        text = "cat >/dev/null <<EOF\n" + "\n".join(
            "heredoc body line %d of the case" % i for i in range(n)) \
            + "\nEOF"
        out.append(_c("redir.lad_heredoc@%d" % n,
                      "heredoc of %d lines" % n, "redir", text,
                      iters=100 if n == 1000 else 300, tags=("ladder",)))
    return out


# ---------------------------------------------------------------------------
# startup: environment size, PATH depth, rc size ladders (process kind)
# ---------------------------------------------------------------------------

def _startup_ladder_cases():
    out = []
    for k in (10, 100, 1000):
        env = tuple(("BSENV%d" % i, "value%d" % i) for i in range(k))
        out.append(Case(
            id="startup.lad_env@%d" % k,
            title="startup with %d environment variables" % k,
            category="startup", kind="process", argv=("-c", ":"),
            env=env, tags=("startup", "generated", "v2", "ladder")))
    fake = ["/bsfake%d" % i for i in range(100)]
    for k in (5, 25, 100):
        path = ":".join(fake[:k]) + ":/usr/bin:/bin"
        out.append(Case(
            id="startup.lad_pathmiss@%d" % k,
            title="command lookup miss over %d PATH dirs" % k,
            category="startup", kind="process",
            argv=("-c", "nosuch_wcmd_xyz_42"), expect_rc=127,
            env=(("PATH", path),),
            tags=("startup", "generated", "v2", "ladder")))
    for k in (25, 100):
        path = ":".join(fake[:k]) + ":/usr/bin:/bin"
        out.append(Case(
            id="startup.lad_pathhit@%d" % k,
            title="command -v hit after %d PATH dirs" % k,
            category="startup", kind="process",
            argv=("-c", "command -v ls >/dev/null"),
            env=(("PATH", path),),
            tags=("startup", "generated", "v2", "ladder")))
    for k in (10, 200, 2000):
        rc = "\n".join("alias a%d='true' # rc filler %d" % (i, i)
                       for i in range(k)) + "\n"
        out.append(Case(
            id="startup.lad_rc@%d" % k,
            title="-i startup with %d-line .bashrc" % k,
            category="startup", kind="process", argv=("-i", "-c", ":"),
            env=(("HOME", "{work}"), ("HISTFILE", "/dev/null"),
                 ("TERM", "dumb")),
            files=((".bashrc", rc),), timeout=60.0,
            tags=("startup", "generated", "v2", "ladder")))
    return out


# ---------------------------------------------------------------------------
# data: big-IO ladders (incl. the 1M-line rung from the DESIGN roadmap)
# ---------------------------------------------------------------------------

def _data_ladder_cases():
    out = []
    out.append(_c("data.lad_read_loop@1000000",
                  "read loop over 1M lines", "data",
                  "c=0; while IFS= read -r l; do c=$((c+1)); "
                  "done < data.txt; echo $c >/dev/null",
                  iters=1000000, kind="script",
                  files=(("data.txt", "@gen:lines:1000000"),),
                  tags=("ladder", "io"), timeout=600.0))
    out.append(_c("data.lad_read_mapfile@1000000",
                  "mapfile over 1M lines", "data",
                  "mapfile -t a < data.txt; x=${#a[@]}",
                  iters=1000000, kind="script",
                  files=(("data.txt", "@gen:lines:1000000"),),
                  tags=("ladder", "io"), timeout=600.0))
    out.append(_c("data.lad_write_append@100000",
                  "100k lines via per-line >> appends", "data",
                  "for ((j=0; j<100000; j++)); do "
                  "printf 'row %d payload\\n' $j >> out.txt; done",
                  iters=100000, kind="script", setup=": > out.txt",
                  tags=("ladder", "io"), timeout=600.0))
    out.append(_c("data.lad_write_block@100000",
                  "100k lines via one block redirect", "data",
                  "for ((j=0; j<100000; j++)); do "
                  "printf 'row %d payload\\n' $j; done > out.txt",
                  iters=100000, kind="script",
                  tags=("ladder", "io"), timeout=600.0))
    out.append(_c("data.lad_pipe3@100000",
                  "100k lines through 3-stage pipeline", "data",
                  "cat data.txt | cat | cat | wc -l >/dev/null",
                  iters=100000, kind="script",
                  files=(("data.txt", "@gen:lines:100000"),),
                  tags=("ladder", "io", "spawn"), timeout=600.0))
    out.append(_c("data.lad_two_fd_join@50000",
                  "lockstep join of two 50k-line files via fd 3/4",
                  "data",
                  "c=0; while IFS= read -r a <&3 && IFS= read -r b <&4; "
                  "do c=$((c+1)); done 3< f1.txt 4< f2.txt; "
                  "echo $c >/dev/null",
                  iters=50000, kind="script",
                  files=(("f1.txt", "@gen:lines:50000"),
                         ("f2.txt", "@gen:lines:50000")),
                  tags=("ladder", "io"), timeout=600.0))
    out.append(_c("data.lad_kv_assoc@100000",
                  "assoc fill from 100k kv lines + 1000 lookups", "data",
                  "declare -A m=(); while IFS== read -r k v; do "
                  "m[$k]=$v; done < data.txt; "
                  "for ((j=0; j<1000; j++)); do "
                  "x=${m[key$(( (j * 97) % 100000 ))]}; done",
                  iters=100000, kind="script",
                  files=(("data.txt", "@gen:kv:100000"),),
                  tags=("ladder", "io", "assoc"), timeout=600.0))
    heredoc = "cat > gen.txt <<EOF\n" + "\n".join(
        "generated content line %d with some payload text" % i
        for i in range(10000)) + "\nEOF"
    out.append(_c("data.lad_heredoc_file@10000",
                  "write 10k-line file via heredoc", "data", heredoc,
                  iters=10000, kind="script", tags=("ladder", "io"),
                  timeout=600.0))
    return out


# ---------------------------------------------------------------------------
# glob: tree-size ladders
# ---------------------------------------------------------------------------

def _glob_ladder_cases():
    tree1k = tuple(("tree1k/f%04d.txt" % i, "") for i in range(1000))
    deep = tuple(("deep/d%d/d%d/f%04d.txt" % (i % 10, i % 7, i), "")
                 for i in range(1000))
    return [
        _c("glob.lad_star@1000", "*.txt over a 1000-file tree", "glob",
           "for f in tree1k/*.txt; do c=$((c+1)); done",
           iters=1000, setup="c=0", kind="script", files=tree1k,
           tags=("ladder", "scale")),
        _c("glob.lad_deepstar@1000", "** over 1000 files, 2-deep tree",
           "glob", "for f in deep/**/*.txt; do c=$((c+1)); done",
           iters=1000, setup="shopt -s globstar; c=0", kind="script",
           files=deep, tags=("ladder", "scale")),
    ]


def cases() -> list:
    out = []
    out += _printf_cases()
    out += _arith_cases()
    out += _expand_scale_cases()
    out += _strings_ladder_cases()
    out += _arrays_ladder_cases()
    out += _cond_matrix_cases()
    out += _control_ladder_cases()
    out += _funcs_ladder_cases()
    out += _jobs_ladder_cases()
    out += _mixed_shape_cases()
    out += _subst_ladder_cases()
    out += _redir_ladder_cases()
    out += _startup_ladder_cases()
    out += _data_ladder_cases()
    out += _glob_ladder_cases()
    return out
