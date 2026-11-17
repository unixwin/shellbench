"""Per-builtin invocation-form matrices: dispatch-cost isolation at depth.

hotloop_gen.py covers one row per builtin plus echo/printf arg-count and
echo-flag ladders. This generator goes deeper on the *form* axis: for each
builtin it sweeps real option sets one flag at a time, arg-count ladders on
multi-assign builtins, value shapes, and allocate+free state-churn pairs —
all inside the same ``for ((__bs_i=0; …))`` wrapper so deltas isolate the
invocation form, not the loop machinery.

Rows are (suffix, title, setup, body, iters, extra_tags). Bodies must stay
rc=0 for every iteration (state that would fail on iteration 2 — readonly
reassignment, drained fds, consumed positionals — is either reset inside
the body or given per-iteration names).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

N = 10000
N_SLOW = 2000      # herestring / procsub / fd-reopen forms fork or pipe
N_DUMP = 500       # builtins that format a large listing per call
N_STATE = 1000     # accumulating-state forms (readonly/nameref names)

ROWS = []


def add(suffix, title, setup, body, iters=N, extra=()):
    ROWS.append((suffix, title, setup, body, iters, extra))


def words(n, prefix="w"):
    return " ".join("%s%d" % (prefix, k) for k in range(n))


# ===========================================================================
# echo: argc ladder (deeper than hotloop's 0..16), flag combos, value shapes.
# ===========================================================================
for argc in (0, 1, 2, 4, 8, 16, 32):
    args = words(argc)
    body = "echo %s >/dev/null" % args if args else "echo >/dev/null"
    add("echo_argc_%d" % argc, "echo argc %d" % argc, "", body)
for fl in ("-n", "-e", "-E", "-ne", "-en", "-nE", "-eE", "-nee", "-enE"):
    add("echo_flag_%s" % fl.lstrip("-"), "echo flags %s" % fl, "",
        "echo %s x >/dev/null" % fl)
for i, (vname, vval) in enumerate((
        ("empty", "''"), ("space", "'a  b   c'"), ("unicode", "'héllo wörld'"),
        ("globlit", "'*.rs'"), ("dollar", "'$v'"),
        ("long128", "'" + "x" * 128 + "'"), ("newlineesc", r"'a\nb'"))):
    add("echo_val_%d_%s" % (i, vname), "echo value %s" % vname,
        "v=VV", "echo %s >/dev/null" % vval)
# echo -e escape-class sweep (single flag, different escape payloads)
for i, esc in enumerate((r"'\t'", r"'\n\n'", r"'\x41\101'", r"'\c'",
                         r"'\a\b\r\v\f'", r"'\\'")):
    add("echo_esc_%d" % i, "echo -e escape %d" % i, "",
        "echo -e %s >/dev/null" % esc)

# ===========================================================================
# printf: format singles, width/precision ladder, escapes, -v, %(..)T, %b/%q.
# ===========================================================================
FMT_VAL = {
    "%s": "hello", "%d": "42", "%i": "42", "%u": "42", "%f": "3.14159",
    "%x": "255", "%X": "255", "%o": "64", "%e": "1.5", "%g": "1.5",
    "%c": "abc", "%q": "a b$c", "%b": r"a\tb\nc",
}
for i, (fmt, val) in enumerate(FMT_VAL.items()):
    add("printf_fmt_%d_%s" % (i, fmt.strip("%")), "printf format %s" % fmt,
        "", "printf '%s\\n' %s >/dev/null" % (fmt, val))
for i, fmt in enumerate((
        "%-20s", "%20s", "%05d", "%+d", "% d", "%.3f", "%10.2f",
        "%08.3f", "%-12.4e", "%.0f", "%5.1s", "%*d", "%-*s")):
    val = "7" if "*" in fmt else ("3.14159" if "f" in fmt or "e" in fmt
                                else ("42" if "d" in fmt else "hello"))
    star = " 8" if fmt.count("*") else ""
    add("printf_wp_%d" % i, "printf width/prec %s" % fmt, "",
        "printf '%s\\n' %s%s >/dev/null" % (fmt, val, star))
# escape-heavy single format string
add("printf_escapes", "printf format escape zoo", "",
    r"printf 'a\nb\tc\\d%%e\af\bg\ri\vj\fk\101l\x42m\n' >/dev/null")
for i, esc in enumerate((r"'a\tb'", r"'a\nb'", r"'\x41\101'", r"'a\\b'",
                         r"'\c'", r"'\0'")):
    add("printf_escarg_%d" % i, "printf %%b escape arg %d" % i, "",
        "printf '%%b\\n' %s >/dev/null" % esc)
for i, expr in enumerate((
        "printf -v pv '%s' x", "printf -v pv '%d' $__bs_i",
        "printf -v pv '%s %s' a b", "printf -v pv '%.3f' 1.5",
        "printf -v pa '%s ' a b c; : ${pa}")):
    add("printf_v_%d" % i, "printf -v capture %d" % i, "", expr)
for i, tfmt in enumerate(("%(%Y)T", "%(%H:%M:%S)T", "%(%s)T",
                          "%(%A %B)T", "%(%j)T")):
    add("printf_time_%d" % i, "printf time fmt %s" % tfmt, "",
        "printf '%s\\n' 0 >/dev/null" % tfmt)
for argc in (0, 1, 2, 4, 8, 16, 32):
    args = words(argc)
    body = "printf '%%s ' %s >/dev/null" % args if args else \
        "printf '%s ' >/dev/null"
    add("printf_argc_%d" % argc, "printf argc %d" % argc, "", body)

# ===========================================================================
# declare / typeset: one real flag at a time, pairs, multi-assign ladders,
# value shapes, print forms.
# ===========================================================================
add("declare_flag_a", "declare -a array literal", "",
    "declare -a da=([0]=v [1]=w)")
add("declare_flag_A", "declare -A assoc literal", "",
    "declare -A db=([k]=v)")
add("declare_flag_i", "declare -i arith", "",
    "declare -i di=$__bs_i+1")
add("declare_flag_x", "declare -x export attr", "",
    "declare -x dx=$__bs_i")
add("declare_flag_n", "declare -n nameref churn", "x=1",
    "declare -n dn=x; unset dn")
add("declare_flag_g", "declare -g global", "",
    "declare -g dg=$__bs_i")
add("declare_flag_l", "declare -l lowercase", "",
    "declare -l dl='ABC'")
add("declare_flag_u", "declare -u uppercase", "",
    "declare -u du='abc'")
add("declare_flag_t", "declare -t trace attr", "",
    "declare -t dt=$__bs_i")
add("declare_flag_p", "declare -p single", "dx=1",
    "declare -p dx >/dev/null")
add("declare_flag_pdump", "declare -p all dump", "",
    "declare -p >/dev/null", 200)
add("declare_flag_f", "declare -f func", "dfn() { :; }",
    "declare -f dfn >/dev/null")
add("declare_flag_F", "declare -F func name", "dfn() { :; }",
    "declare -F dfn >/dev/null")
add("declare_flag_r", "declare -r unique names", "",
    "declare -r dr$__bs_i=$__bs_i", N_STATE)
READONLY_PAIRS = ("-rx", "-ir", "-ar", "-Ar")
for i, fl in enumerate(("-ix", "-gx", "-tx", "-ux", "-lx", "-rx",
                        "-ir", "-ar", "-Ar", "-nx")):
    if fl in READONLY_PAIRS:
        # readonly forms must use unique names and lower iters
        nm = "dr%s$__bs_i" % fl.strip("-")
        if fl == "-ar":
            # compound array assign needs a literal name: eval expands it
            body = "eval \"declare %s drar$__bs_i=(v)\"" % fl
        elif fl == "-Ar":
            body = "eval \"declare %s drAr$__bs_i=([k]=v)\"" % fl
        else:
            body = "declare %s %s=1" % (fl, nm)
        add("declare_pair_%d_%s" % (i, fl.strip("-").replace("-", "")),
            "declare pair %s" % fl, "", body, N_STATE)
    elif fl == "-nx":
        add("declare_pair_%d_nx" % i, "declare pair -nx", "x=1",
            "declare -nx dn2=x; unset dn2")
    else:
        add("declare_pair_%d_%s" % (i, fl.strip("-")), "declare pair %s" % fl,
            "", "declare %s dpv=1" % fl)
# multi-assign ladders
for n in (1, 2, 4, 8):
    assigns = " ".join("d%d=%d" % (k, k) for k in range(n))
    add("declare_assign_%d" % n, "declare %d assigns" % n, "",
        "declare %s" % assigns)
    add("declare_naked_%d" % n, "declare %d names" % n, "",
        "declare %s" % " ".join("n%d" % k for k in range(n)))
# value shapes
for i, (vname, expr) in enumerate((
        ("short", "declare dv='abc'"),
        ("space", "declare dv='a b c d'"),
        ("unicode", "declare dv='héllo wörld'"),
        ("globlit", "declare dv='*.rs'"),
        ("empty", "declare dv="),
        ("long128", "declare dv='" + "y" * 128 + "'"),
        ("concat", "declare dv=pre$post"),
        ("arraylit", "declare -a dv=(a 'b c' d)"),
        ("assoclit", "declare -A dv=([k1]=v1 [k2]='v 2')"))):
    setup = "post=POST" if vname == "concat" else ""
    add("declare_val_%d_%s" % (i, vname), "declare value %s" % vname,
        setup, expr)
# typeset mirrors a representative subset
for i, (fl, body) in enumerate((
        ("", "typeset tv=1"), ("-i", "typeset -i ti=$__bs_i+1"),
        ("-a", "typeset -a ta=(v w)"), ("-A", "typeset -A tb=([k]=v)"),
        ("-x", "typeset -x tx=1"), ("-l", "typeset -l tl='ABC'"),
        ("-p", "typeset -p tx >/dev/null"), ("-n", "typeset -n tn=x; unset tn"))):
    add("typeset_%d_%s" % (i, fl or "plain"), "typeset %s" % (fl or "plain"),
        "x=1; tx=1" if fl == "-p" else ("x=1" if fl == "-n" else ""), body)

# ===========================================================================
# local: depth chains, multi-assign, attribute forms inside a function.
# ===========================================================================
add("local_plain", "local plain", "f() { local y=1; :; }", "f")
add("local_multi", "local 4 assigns", "f() { local a=1 b=2 c=3 d=4; :; }", "f")
add("local_names", "local 8 names", "f() { local a b c d e f2 g h; :; }", "f")
add("local_i", "local -i", "f() { local -i n=$1+1; :; }", "f 4")
add("local_a", "local -a", "f() { local -a arr=(x y); :; }", "f")
add("local_r", "local -r", "f() { local -r lr=1; :; }", "f")
add("local_x", "local -x", "f() { local -x lx=1; :; }", "f")
add("local_depth2", "local depth 2", "g() { local b=2; :; }; f() { local a=1; g; }", "f")
add("local_depth3", "local depth 3",
    "h() { local c=3; :; }; g() { local b=2; h; }; f() { local a=1; g; }", "f")
add("local_depth4", "local depth 4",
    "q() { local d=4; :; }; h() { local c=3; q; }; "
    "g() { local b=2; h; }; f() { local a=1; g; }", "f")
add("local_args", "local from params", "f() { local p=$2 q=$4; :; }",
    "f a b c d")
add("local_shift", "local + shift", "f() { local s=1; shift; :; }",
    "f a b c")

# ===========================================================================
# export / readonly / unset: flag forms, assign ladders, value shapes.
# ===========================================================================
add("export_flag_n", "export -n churn", "ev=1",
    "export ev=1; export -n ev")
add("export_flag_p", "export -p dump", "", "export -p >/dev/null", N_DUMP)
add("export_flag_f", "export -f func", "efn() { :; }",
    "export -f efn >/dev/null")
for n in (1, 2, 4, 8):
    assigns = " ".join("E%d=%d" % (k, k) for k in range(n))
    add("export_assign_%d" % n, "export %d assigns" % n, "",
        "export %s" % assigns)
for i, (vname, expr) in enumerate((
        ("short", "export ev='abc'"), ("space", "export ev='a b c'"),
        ("unicode", "export ev='héllo'"), ("globlit", "export ev='*.rs'"),
        ("empty", "export ev="), ("long128", "export ev='" + "z" * 128 + "'"))):
    add("export_val_%d_%s" % (i, vname), "export value %s" % vname, "", expr)
# readonly: unique names per iteration (reassignment of a readonly var
# fails), print forms, array form.
add("readonly_assign", "readonly unique assign", "",
    "readonly rv$__bs_i=$__bs_i", N_STATE)
add("readonly_space", "readonly space value", "",
    "readonly rvs$__bs_i='a b c'", N_STATE)
add("readonly_array", "readonly -a unique", "",
    "eval \"readonly -a ra$__bs_i=(v w)\"", N_STATE)
add("readonly_flag_p", "readonly -p", "readonly rp=1",
    "readonly -p rp >/dev/null")
add("readonly_dump", "readonly all dump", "", "readonly >/dev/null", 100)
# unset forms
add("unset_var", "unset var churn", "", "ux=1; unset ux")
add("unset_v", "unset -v", "", "uv=1; unset -v uv")
add("unset_multi", "unset 4 vars", "", "u1=1 u2=2 u3=3 u4=4; unset u1 u2 u3 u4")
add("unset_func", "unset -f churn", "", "uf() { :; }; unset -f uf")
add("unset_missing", "unset missing rc0", "", "unset nosuchvar_xyz")

# ===========================================================================
# set: positional ladders, -o option-name query matrix, flag churn pairs.
# ===========================================================================
for n in (0, 1, 2, 4, 8, 16, 32):
    args = words(n, "p")
    body = "set -- %s" % args if args else "set --"
    add("set_positional_%d" % n, "set -- %d positionals" % n, "", body)
SET_OPTS = ("allexport", "braceexpand", "errexit", "errtrace", "functrace",
            "hashall", "histexpand", "history", "ignoreeof",
            "interactive-comments", "keyword", "monitor", "noclobber",
            "noexec", "noglob", "nolog", "notify", "onecmd", "physical",
            "pipefail", "posix", "privileged", "verbose", "vi", "xtrace",
            "nounset")
for i, opt in enumerate(SET_OPTS):
    add("set_o_query_%d_%s" % (i, opt.replace("-", "")),
        "set -o %s query" % opt, "", "set -o %s >/dev/null" % opt)
for i, opt in enumerate(("errexit", "nounset", "xtrace", "pipefail",
                         "noglob", "noclobber", "allexport", "braceexpand",
                         "hashall", "verbose", "functrace", "errtrace")):
    if opt == "xtrace" or opt == "verbose":
        # trace/verbose output goes to the shell's stderr: wrap the pair
        body = "{ set -o %s; set +o %s; } 2>/dev/null" % (opt, opt)
    else:
        body = "set -o %s; set +o %s" % (opt, opt)
    add("set_flag_%d_%s" % (i, opt), "set -o/+o %s churn" % opt, "", body)
add("set_dump", "set -o all dump", "", "set -o >/dev/null", N_DUMP)
add("set_dash_o_posix", "set -o posix churn", "",
    "set -o posix; set +o posix")
add("set_short_e", "set -e/+e short", "", "set -e; :; set +e")
add("set_short_u", "set -u/+u short", "", "set -u; :; set +u")

# ===========================================================================
# shopt: {-s,-u,-q,-p,print} x real option names.
# ===========================================================================
SHOPTS = ("nullglob", "failglob", "extglob", "globstar", "dotglob",
          "nocaseglob", "expand_aliases", "sourcepath", "execfail",
          "shift_verbose", "xpg_echo")
for opt in SHOPTS:
    add("shopt_s_%s" % opt, "shopt -s %s" % opt, "", "shopt -s %s" % opt)
    add("shopt_u_%s" % opt, "shopt -u %s" % opt, "", "shopt -u %s" % opt)
    add("shopt_q_%s" % opt, "shopt -s+q %s" % opt, "",
        "shopt -s %s; shopt -q %s" % (opt, opt))
    # shopt opt / shopt -p opt return the option's set-status: force set first
    add("shopt_p_%s" % opt, "shopt -p %s" % opt, "",
        "shopt -s %s; shopt -p %s >/dev/null" % (opt, opt))
    add("shopt_print_%s" % opt, "shopt %s print" % opt, "",
        "shopt -s %s; shopt %s >/dev/null" % (opt, opt))
add("shopt_dump", "shopt all dump", "", "shopt >/dev/null", N_DUMP)
add("shopt_sq_s", "shopt -s multi", "",
    "shopt -s nullglob extglob dotglob")
add("shopt_sq_u", "shopt -u multi", "",
    "shopt -u nullglob extglob dotglob")

# ===========================================================================
# ulimit: query-only matrix (no -t CPU traps, no set forms).
# ===========================================================================
add("ulimit_bare", "ulimit bare query", "", "ulimit >/dev/null")
add("ulimit_a", "ulimit -a dump", "", "ulimit -a >/dev/null", N_DUMP)
# git-bash/MSYS bash lacks RLIMITs e,i,l,m,r -> only the portable set.
ULIM_FLAGS = "cdfnpstuv"
for fl in ULIM_FLAGS:
    add("ulimit_%s" % fl, "ulimit -%s query" % fl, "",
        "ulimit -%s >/dev/null" % fl)
for fl in ULIM_FLAGS:
    add("ulimit_H%s" % fl, "ulimit -H%s query" % fl, "",
        "ulimit -H%s >/dev/null" % fl)
    add("ulimit_S%s" % fl, "ulimit -S%s query" % fl, "",
        "ulimit -S%s >/dev/null" % fl)
add("ulimit_HS_n", "ulimit -Hn/-Sn pair", "",
    "ulimit -Hn >/dev/null; ulimit -Sn >/dev/null")

# ===========================================================================
# umask: query, set+restore pairs (original captured in setup).
# ===========================================================================
add("umask_query", "umask query", "", "umask >/dev/null")
add("umask_set_077", "umask 077 set+restore", "OM=$(umask)",
    "umask 077 >/dev/null; umask $OM >/dev/null")
add("umask_set_000", "umask 000 set+restore", "OM=$(umask)",
    "umask 000 >/dev/null; umask $OM >/dev/null")
add("umask_cycle", "umask 3-value cycle", "OM=$(umask)",
    "umask 077 >/dev/null; umask 022 >/dev/null; umask $OM >/dev/null")

# ===========================================================================
# shift / getopts: positional-param machinery.
# ===========================================================================
add("shift_1", "shift 1", "", "set -- a b c d e; shift")
add("shift_2", "shift 2", "", "set -- a b c d e; shift 2")
add("shift_all", "shift $#", "", "set -- a b c; shift $#")
add("shift_0", "shift 0 no-op", "", "set -- a b; shift 0")
add("positional_cycle", "set/shift cycle", "",
    "set -- p q r s; shift; set -- p q r s; shift")
# getopts: optstring length ladder + OPTIND reset cycles
add("getopts_short", "getopts 'a'", "set -- -a -a -a",
    "OPTIND=1; while getopts 'a' o; do :; done")
add("getopts_arg", "getopts 'ab:c'", "set -- -a -b val -c -b val2",
    "OPTIND=1; while getopts 'ab:c' o; do :; done")
add("getopts_long", "getopts 8-opt optstring", "set -- -a -b -c -d -e -f val -g -h",
    "OPTIND=1; while getopts 'abcdef:g:h' o; do :; done", N_SLOW)
add("getopts_silent", "getopts silent ':' optstring", "set -- -a -z -b",
    "OPTIND=1; while getopts ':ab' o; do :; done")
add("getopts_optind_reset", "getopts OPTIND reset cycle",
    "set -- -a -b val -c",
    "OPTIND=1; getopts 'ab:c' o; getopts 'ab:c' o; getopts 'ab:c' o; :")
add("getopts_shift", "getopts + shift consume", "set -- -a -b val -c",
    "OPTIND=1; while getopts 'ab:c' o; do :; done; shift $((OPTIND-1)) 2>/dev/null || :")

# ===========================================================================
# compgen / complete: -W candidate-count ladder, -A action matrix, specs.
# ===========================================================================
for n in (1, 4, 16, 64):
    wl = words(n)
    add("compgen_w_%d" % n, "compgen -W %d candidates" % n, "",
        "compgen -W '%s' -- w >/dev/null || :" % wl, N_SLOW if n >= 64 else N)
for i, prefix in enumerate(("", "w", "w1", "zz", "w10")):
    add("compgen_prefix_%d" % i, "compgen -W prefix %r" % prefix, "",
        "compgen -W 'w0 w1 w10 w11 w20' -- %s >/dev/null || :" %
        ("'%s'" % prefix if prefix else "''"), N_SLOW)
# "command"/"directory" dropped: they rescan PATH/cwd per call (>1 s/iter on
# git-bash) and would always hit the per-rep timeout; the remaining 22
# actions still cover the -A dispatch matrix.
COMPGEN_ACTIONS = ("alias", "arrayvar", "binding", "builtin",
                   "disabled", "enabled", "export", "file",
                   "function", "group", "helptopic", "hostname", "job",
                   "keyword", "running", "service", "setopt", "shopt",
                   "signal", "stopped", "user", "variable")
for i, act in enumerate(COMPGEN_ACTIONS):
    # empty categories legitimately return 1 -> normalize with || :
    add("compgen_A_%d_%s" % (i, act), "compgen -A %s" % act, "",
        "compgen -A %s >/dev/null || :" % act, N_DUMP)
add("compgen_C", "compgen -C command", "",
    "compgen -C 'printf \"a\\nb\\n\"' >/dev/null || :", N_SLOW)
add("compgen_f", "compgen -f files", "",
    "compgen -f -- s >/dev/null || :", N_DUMP)
# complete specs (redefine same command name each iter = replace, not grow)
add("complete_w", "complete -W spec", "",
    "complete -W 'a b c d e' bsc; complete -p bsc >/dev/null")
add("complete_w_r", "complete -W + -r churn", "",
    "complete -W 'a b' bsc2; complete -r bsc2")
add("complete_A", "complete -A action", "",
    "complete -A file bsc3; complete -p bsc3 >/dev/null")
add("complete_C", "complete -C command spec", "",
    "complete -C 'echo x' bsc4; complete -r bsc4")
add("complete_multi", "complete multi-option", "",
    "complete -o nospace -o filenames -W 'x y z' bsc5; complete -r bsc5")
add("complete_p_dump", "complete -p dump", "",
    "complete -p >/dev/null 2>&1", N_DUMP)

# ===========================================================================
# read family: flag forms, sources (herestring/redirect/pipe/fd), IFS churn.
# ===========================================================================
READ_FORMS = [
    ("r", "read -r x <<< 'a b c'"),
    ("ra", "read -ra arr <<< 'a b c d'"),
    ("n3", "read -n 3 x <<< 'abcdef'"),
    ("N3", "read -N 3 x <<< 'abcdef'"),
    ("p", "read -p 'p: ' -r x <<< 'v' 2>/dev/null"),
    ("t1", "read -t 1 -r x <<< 'v'"),
    ("d_nl", "read -d $'\\n' -r x <<< 'abc'"),
    ("s", "read -s -r x <<< 'abc'"),
]
for name, body in READ_FORMS:
    add("read_%s" % name, "read form %s" % name, "arr=()", body, N_SLOW)
add("read_d_nul", "read -d '' whole file", "",
    "read -r -d '' x < small.txt || :", N_SLOW)
add("read_u_fd", "read -u reopened fd", "",
    "exec 9<small.txt; read -u 9 -r x; exec 9<&-", N_SLOW)
add("read_redirect", "read < file", "",
    "read -r x < small.txt", N)
add("read_pipe", "read in pipeline (subshell)", "",
    "printf 'a b c\\n' | read -r x y z", N_SLOW)
add("read_heredoc", "read <<< herestring variant", "",
    "read -r x y <<< 'one two'", N_SLOW)
add("read_IFS_churn", "read + IFS restore", "SIFS=$IFS",
    "IFS=:; read -r a b <<< 'x:y:z'; IFS=$SIFS", N_SLOW)
add("read_IFS_multi", "read IFS multi-char", "SIFS=$IFS",
    "IFS=':;' ; read -r a b c <<< 'x:y;z'; IFS=$SIFS", N_SLOW)
add("read_fields_5", "read 5 fields", "",
    "read -r a b c d e <<< '1 2 3 4 5'", N_SLOW)

# ===========================================================================
# mapfile / readarray: option matrix over a small procsub input.
# ===========================================================================
LINES3 = "a\\nb\\nc\\n"
MAP_OPTS = [
    ("t", "mapfile -t ma < <(printf '%s')" % LINES3),
    ("n1", "mapfile -n 1 -t ma < <(printf '%s')" % LINES3),
    ("O1", "ma=(); mapfile -O 1 -t ma < <(printf '%s')" % LINES3),
    ("s1", "mapfile -s 1 -t ma < <(printf '%s')" % LINES3),
    ("c", "mapfile -C mcb -c 1 -t ma < <(printf '%s')" % LINES3),
    ("d_empty", "mapfile -d '' -t ma < <(printf '%s')" % LINES3),
    ("d_x", "mapfile -d x -t ma < <(printf 'axbxcx')"),
    ("u_fd", "exec 8<small.txt; mapfile -u 8 -t ma </dev/null; exec 8<&-"),
]
for name, body in MAP_OPTS:
    add("mapfile_%s" % name, "mapfile -%s" % name,
        "mcb() { :; }; ma=()" if name in ("c", "O1") else "ma=()",
        body, N_SLOW)
RA_OPTS = [
    ("t", "readarray -t ra < <(printf '%s')" % LINES3),
    ("n2", "readarray -n 2 -t ra < <(printf '%s')" % LINES3),
    ("s1", "readarray -s 1 -t ra < <(printf '%s')" % LINES3),
    ("d_empty", "readarray -d '' -t ra < <(printf '%s')" % LINES3),
]
for name, body in RA_OPTS:
    add("readarray_%s" % name, "readarray -%s" % name, "ra=()", body, N_SLOW)
# input-size ladder
for nlines in (1, 8, 32):
    lit = "".join("l%d\\n" % k for k in range(nlines))
    add("mapfile_lines_%d" % nlines, "mapfile %d lines" % nlines,
        "ma=()", "mapfile -t ma < <(printf '%s')" % lit, N_SLOW)

# ===========================================================================
# State-churn pairs: allocate + free per iteration.
# ===========================================================================
add("churn_declare_unset", "declare+unset", "", "cx=1; declare cy=$cx; unset cy cx")
add("churn_export_unset", "export+unset", "", "ex=1; export ex; unset ex")
add("churn_typeset_unset", "typeset+unset", "", "tx2=1; typeset ty=$tx2; unset ty tx2")
add("churn_assoc_key", "assoc key churn", "declare -A h",
    "h[k]=v; unset 'h[k]'")
add("churn_assoc_bounded", "assoc bounded keys", "declare -A h",
    "h[k$((__bs_i%8))]=v")
add("churn_array_elem", "array elem set/unset", "aa=(x y z)",
    "aa[1]=v; unset 'aa[1]'")
add("churn_array_bounded", "array bounded indices", "ab=()",
    "ab[$__bs_i%8]=v")
add("churn_assoc_grow", "assoc grow+reset", "",
    "declare -A hg=([k$__bs_i]=v)")
add("churn_func_def", "func def+unset", "",
    "cf() { :; }; unset -f cf")
add("churn_alias_pair", "alias def+unalias", "",
    "alias ca='echo x'; unalias ca")
add("churn_alias_args", "alias with args", "",
    "alias cb='ls -l /'; unalias cb", extra=("cap:posix-path",))
add("churn_positional", "positional set/shift", "",
    "set -- a b c d; shift 2; set -- a b")
add("churn_optind", "OPTIND reset cycle", "set -- -a -b -c",
    "OPTIND=1; getopts 'abc' o; getopts 'abc' o")
add("churn_ifs_read", "IFS set/read/restore", "SIFS=$IFS",
    "IFS='|'; read -r a b <<< 'x|y'; IFS=$SIFS", N_SLOW)
add("churn_declare_recreate", "declare array recreate", "",
    "declare -a ra2=(v w); ra2=()")

# ===========================================================================
# eval / let: string complexity ladder.
# ===========================================================================
for i, s in enumerate((
        "eval 'x=1'",
        "eval 'x=1; y=2'",
        "eval 'echo a b c >/dev/null'",
        "eval 'x=$((__bs_i+1))'",
        "eval 'for j in 1 2 3; do :; done'",
        "eval 'set -- a b; shift'",
        "eval '[[ 1 = 1 ]]'",
        "eval 'v=hello; echo $v >/dev/null'")):
    add("eval_%d" % i, "eval complexity %d" % i, "", s, N_SLOW)
for i, s in enumerate((
        "let 'a=1'",
        "let 'a=1' 'b=2'",
        "let 'a=__bs_i+1'",
        "let 'a=1+2*3'",
        "let 'a+=2'",
        "let 'a=(1+2)*3'",
        "let 'a++'",
        "let 'a=1' 'b=a+1' 'c=b*2'")):
    add("let_%d" % i, "let form %d" % i, "a=1", s)

# ===========================================================================
# help: topic-name matrix (output redirected, formatting cost measured).
# ===========================================================================
HELP_TOPICS = ("echo", "printf", "test", "[", "declare", "typeset",
               "local", "export", "readonly", "alias", "unalias", "set",
               "shopt", "ulimit", "umask", "read", "mapfile", "compgen",
               "complete", "eval", "let", "getopts", "shift", "enable",
               "type", "hash", "command", "builtin", "true", "false",
               "kill", "wait", "jobs", "times", "dirs", "pushd", "fc",
               "history", "unset", "cd", "pwd", "caller", "logout",
               "suspend", "break", "continue", "return", "trap", "times")
seen = set()
for i, topic in enumerate(HELP_TOPICS):
    if topic in seen:
        continue
    seen.add(topic)
    add("help_%d_%s" % (i, topic.strip("[]")), "help %s" % topic, "",
        "help %s >/dev/null 2>&1" % topic, N_DUMP)

# ===========================================================================
# enable / type / command / builtin / hash: dispatch-wrapper forms.
# ===========================================================================
add("enable_n_echo", "enable -n/enable echo", "",
    "enable -n echo; enable echo")
add("enable_n_printf", "enable -n/enable printf", "",
    "enable -n printf; enable printf")
add("enable_a", "enable -a dump", "", "enable -a >/dev/null", N_DUMP)
add("type_a", "type -a", "", "type -a echo >/dev/null")
add("type_t", "type -t", "", "type -t echo >/dev/null")
add("type_p", "type -p", "", "type -p echo >/dev/null")
add("type_P", "type -P", "", "type -P echo >/dev/null")
add("command_v", "command -v", "", "command -v echo >/dev/null")
add("command_V", "command -V", "", "command -V echo >/dev/null")
add("command_p", "command -p true", "", "command -p true")
add("builtin_echo", "builtin echo", "", "builtin echo x >/dev/null")
add("builtin_printf", "builtin printf", "",
    "builtin printf '%s\\n' x >/dev/null")
add("builtin_test", "builtin test", "", "builtin test 1 = 1")
add("builtin_decl", "builtin declare", "", "builtin declare bd=1")
add("hash_r", "hash -r flush", "", "hash -r")
add("hash_p", "hash -p record", "",
    "hash -p /bin/ls hsl; hash -d hsl", extra=("cap:posix-path",))
add("hash_list", "hash list dump", "", "hash >/dev/null", N_DUMP)
add("hash_d", "hash -d delete", "",
    "hash -p /bin/ls hsl2; hash -d hsl2", extra=("cap:posix-path",))

# ===========================================================================
# value-shape matrices on multi-assign builtins (declare/export/readonly
# covered above; here: set -- positional shapes are literal, add compgen -W
# shape variants and alias name/value shapes).
# ===========================================================================
for i, wl in enumerate((
        "'a b c'", "'one two three four five'",
        "'*.rs *.toml'", "''", "'héllo wörld x'",
        "'a  b  c  d'")):
    add("compgen_wshape_%d" % i, "compgen -W shape %d" % i, "",
        "compgen -W %s -- '' >/dev/null || :" % wl, N_SLOW)
for i, (nm, val) in enumerate((
        ("aln", "'echo hi'"), ("aln2", "'ls -la /tmp'"),
        ("aln3", "'printf \"%s\" x'"))):
    add("alias_shape_%d" % i, "alias name/value shape %d" % i, "",
        "alias %s=%s; unalias %s" % (nm, val, nm),
        extra=("cap:posix-path",) if "/" in val else ())


def cases() -> list:
    out = []
    files = (("small.txt", "@gen:lines:50"),)
    for suffix, title, setup, body, iters, extra in ROWS:
        need_files = ("small.txt" in body or "small.txt" in setup or
                      "data.txt" in body or "data.txt" in setup)
        out.append(Case(
            id="hotloop.%s" % suffix,
            title="hotloop bi2 %s" % title, category="hotloop",
            tags=("hotloop", "generated", "v2") + tuple(extra),
            setup=setup, body=body, iters=iters,
            files=files if need_files else ()))
    return out
