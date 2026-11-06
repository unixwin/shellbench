"""Hot-loop micro-op generator: per-operation dispatch cost at scale.

Every case shares the same ``for ((__bs_i=0; …))`` wrapper, so the ``:``
baseline row measures pure loop machinery and each other row's delta is
the isolated cost of one operation — builtin dispatch, a ``[``/``[[``
test, one arithmetic form, one expansion form, one substitution. This is
the class that catches per-op overhead regressions (e.g. a builtin or
expansion path growing 10-25x) which single-shot or composite cases miss.

Bodies run inside the counting loop; ``$__bs_i`` is the counter. ``i`` is
a scratch variable seeded in setup where a body needs its own counter.
Rows are (suffix, title, setup, body, iters, extra_tags).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

N = 10000

ROWS = [
    # -- loop machinery floor -------------------------------------------
    ("floor_colon", "bare colon (for-machinery floor)", "", ":", N, ()),
    ("floor_arith_incr", "for-machinery + (( )) increment", "", "((__bs_i + 1))", N, ()),

    # -- conditionals / tests --------------------------------------------
    ("test_bracket_int", "[ ] integer -lt", "", "[ $__bs_i -lt 5000 ]", N, ()),
    ("test_builtin_int", "test builtin -lt", "", "test $__bs_i -lt 5000", N, ()),
    ("test_dbracket", "[[ ]] integer", "", "[[ $__bs_i -lt 5000 ]]", N, ()),
    ("test_file_devnull", "[ ] -e /dev/null", "", "[ -e /dev/null ]", N, ("cap:devfs",)),
    ("cond_if", "if [ ] then :", "", "if [ $__bs_i -lt 5000 ]; then :; fi", N, ()),
    ("cond_and", "[ ] && :", "", "[ $__bs_i -lt 5000 ] && :", N, ()),
    ("cond_case", "case single arm", "", "case x in x) :;; esac", N, ()),

    # -- arithmetic -------------------------------------------------------
    ("arith_postincr", "((i++)) own counter", "i=0", "((i++))", N, ()),
    ("arith_dollar_assign", "i=$((i+1))", "i=0", "i=$((i+1))", N, ()),
    ("arith_let", "let i=i+1", "i=0", "let 'i=i+1'", N, ()),
    ("arith_eval", "eval ((i++))", "i=0", "eval '((i++))'", N, ()),
    ("arith_cmp", "(( )) comparison", "", "((__bs_i < 5000))", N, ()),

    # -- parameter expansion ----------------------------------------------
    ("exp_assign", "x=$v plain", "v=hello", "x=$v", N, ()),
    ("exp_assign_quoted", 'x="$v$v" quoted concat', "v=hello", 'x="$v$v"', N, ()),
    ("exp_default", "x=${v:-d}", "v=hello", "x=${v:-d}", N, ()),
    ("exp_alt", "x=${v:+d}", "v=hello", "x=${v:+d}", N, ()),
    ("exp_len", "x=${#v}", "v=hello", "x=${#v}", N, ()),
    ("exp_trim_pre", "x=${v#pat}", "v=hello", "x=${v#he}", N, ()),
    ("exp_trim_suf", "x=${v%pat}", "v=hello", "x=${v%lo}", N, ()),
    ("exp_replace", "x=${v//l/L}", "v=hello", "x=${v//l/L}", N, ()),
    ("exp_substr", "x=${v:off:len}", "v=hello", "x=${v:1:3}", N, ()),
    ("exp_concat", "x=$a$v$b", "a=1 v=hello b=2", "x=$a$v$b", N, ()),
    ("exp_word_split", "set -- $v splitting", 'v="a b c"', "set -- $v", N, ()),
    ("exp_brace", "set -- {1..3} brace", "", "set -- {1..3}", N, ()),

    # -- builtin dispatch (single minimal op) ------------------------------
    ("bi_colon", "builtin : dispatch", "", ":", N, ()),
    ("bi_true", "builtin true", "", "true", N, ()),
    ("bi_echo_devnull", "echo >/dev/null", "", "echo x >/dev/null", N, ()),
    ("bi_printf_lit", "printf literal", "", "printf 'x\\n' >/dev/null", N, ()),
    ("bi_printf_var", "printf %s \"$v\"", "v=hi", 'printf \'%s\\n\' "$v" >/dev/null', N, ()),
    ("bi_test_self", "[ 1 = 1 ]", "", "[ 1 = 1 ]", N, ()),
    ("bi_pwd", "pwd >/dev/null", "", "pwd >/dev/null", N, ()),
    ("bi_cd_dot", "cd .", "", "cd .", N, ()),
    ("bi_unset", "x=1; unset x", "", "x=1; unset x", N, ()),
    ("bi_shift", "set -- + shift", "", "set -- a b c; shift", N, ()),
    ("bi_command", "command true", "", "command true", N, ()),
    ("bi_builtin_kw", "builtin true", "", "builtin true", N, ()),
    ("bi_eval", "eval 'x=1'", "", "eval 'x=1'", N, ()),

    # -- the reported composite (while-loop printf+arith shape) -------------
    ("composite_reported", "printf %d var + ((i++)) loop", "i=1", 'printf \'%d\\n\' "$i"; ((i++))', N, ()),

    # -- substitution -------------------------------------------------------
    ("sub_comsub_true", "x=$(true)", "", "x=$(true)", 2000, ()),
    ("sub_comsub_echo", "x=$(echo hi)", "", "x=$(echo hi)", 2000, ()),
    ("sub_comsub_pwd", "x=$(pwd)", "", "x=$(pwd)", 1000, ()),
    ("sub_dollar_in_expand", "echo $(true) inline", "", "echo $(true) >/dev/null", 1000, ()),

    # -- functions -----------------------------------------------------------
    ("fn_call", "empty function call", "f() { :; }", "f", N, ()),
    ("fn_local", "function with local", "f() { local y=1; :; }", "f", N, ()),

    # -- external spawn control ---------------------------------------------
    ("ext_true", "/bin/true spawn", "", "/bin/true", 500, ("cap:posix-path",)),
    ("ext_echo", "/bin/echo spawn", "", "/bin/echo x >/dev/null", 500, ("cap:posix-path",)),
]

# Script-kind case: the exact while-loop shape from the field report,
# timed once over `iters` operations.
SCRIPT_ROWS = [
    ("while_printf_arith", "while loop: printf %d + ((i++))",
     "i=1\nwhile [ $i -le {iters} ]; do\n    printf '%d\\n' \"$i\"\n    ((i++))\ndone\n", N),
    ("while_test_only", "while loop: test + ((i++))",
     "i=1\nwhile [ $i -le {iters} ]; do\n    :\n    ((i++))\ndone\n", N),
]


def cases() -> list:
    out = []
    for suffix, title, setup, body, iters, extra in ROWS:
        out.append(Case(
            id="hotloop.%s" % suffix,
            title="hotloop %s" % title, category="hotloop",
            tags=("hotloop", "generated", "v2") + extra,
            setup=setup, body=body, iters=iters))
    for suffix, title, body, iters in SCRIPT_ROWS:
        out.append(Case(
            id="hotloop.script_%s" % suffix,
            title="hotloop script %s" % title, category="hotloop",
            kind="script", tags=("hotloop", "generated", "v2"),
            body=body, iters=iters))
    return out
