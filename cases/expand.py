"""Expansion family, hand-written supplements to the generated matrix:
tilde, brace, word splitting, nested and mixed expansion shapes."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402


def C(cid, title, body, iters=5000, setup="", **kw):
    return Case(id=cid, title=title, category="expand", body=body,
                setup=setup, iters=iters, tags=("expand",), **kw)


CASES = [
    C("expand.tilde_home", "tilde ~ expansion", "x=~/sub/dir",
      env=(("HOME", "{work}"),)),
    C("expand.tilde_user", "tilde ~user expansion", "x=~root/bin"),
    C("expand.tilde_plus", "tilde ~+ (PWD)", "x=~+"),
    C("expand.brace_list", "brace {a,b,c} in assignment", "x={aa,bb,cc}"),
    C("expand.brace_range_num", "brace {1..50}", "a=({1..50})", iters=500),
    C("expand.brace_range_alpha", "brace {a..z}", "a=({a..z})", iters=1000),
    C("expand.brace_range_step", "brace {0..100..5}", "a=({0..100..5})",
      iters=500),
    C("expand.brace_nested", "brace nested", "x={a,{b,c}d,e}", iters=3000),
    C("expand.brace_cartesian", "brace cartesian x{A,B}y{1,2}",
      "a=(x{A,B}y{1,2})", iters=1000),
    C("expand.word_split", "unquoted word splitting", "set -- $v; x=$#",
      setup="v='aa bb  cc   dd ee'", iters=3000),
    C("expand.word_nosplit_quoted", "quoted no-split", 'x="$v"',
      setup="v='aa bb cc'", iters=8000),
    C("expand.nested_cmdsubst", "nested command substitution",
      "x=$(echo $(echo $(echo deep)))", iters=500),
    C("expand.default_cmdsubst", "${v:-$(...)} default with cmdsubst",
      "x=${u:-$(echo fallback)}", iters=1000),
    C("expand.arith_in_subscript", "arithmetic inside subscript",
      "x=${a[$((__bs_i % 8 + 1))]}", setup="a=(0 1 2 3 4 5 6 7 8 9)",
      iters=5000),
    C("expand.double_nested_param", "${!a[i]} indirect via array",
      "x=${!a[1]}", setup="a=(p q); p=hit", iters=5000),
    C("expand.glob_pattern_var", "pattern from variable in ${v#pat}",
      "x=${v#$p}", setup="v=a/b/c; p='*/'", iters=5000),
    C("expand.multi_word_assign", "multi expansion assignment",
      "x=$a-$b.${c}_end", setup="a=foo; b=bar; c=baz", iters=8000),
    C("expand.history_char_bang", "$! last bg pid (set/unset mix)",
      "x=$!", iters=8000),
    C("expand.random_read", "$RANDOM read", "x=$RANDOM", iters=8000),
    C("expand.seconds_read", "$SECONDS read", "x=$SECONDS", iters=8000),
    C("expand.lineno_read", "$LINENO read", "x=$LINENO", iters=8000),
]

# --- corpus v2 additions: ${v@...} transforms, prefix indirection,
# deep default chains, positional slicing (form x scale matrix in
# generators/v2_gen.py) ---
_V2 = [
    C("expand.at_Q", "${v@Q} quoting transform", "x=${v@Q}",
      setup="v='a b|c'", iters=3000),
    C("expand.at_U", "${v@U} upper transform", "x=${v@U}",
      setup="v=hello", iters=3000),
    C("expand.at_a", "${v@a} attribute flags", "x=${n@a}",
      setup="declare -i n=5", iters=3000),
    C("expand.indirect_prefix_list", "${!BS_*} name list",
      "x=${!BS_*}", setup="BS_A=1; BS_B=2; BS_C=3", iters=3000),
    C("expand.nested_default3", "3-deep nested defaults",
      "x=${u1:-${u2:-${u3:-deep}}}", iters=3000),
    C("expand.positional_slice", "${@:2:2} positional slice",
      "x=${@:2:2}", setup="set -- a b c d e", iters=3000),
    C("expand.join_ifs_multi", "${a[*]} with two-char IFS",
      "x=${a[*]}", setup="a=(aa bb cc); IFS='::'", iters=3000),
    C("expand.substr_expr_offset", "expression offset in substring",
      "x=${v: (n > 1 ? 2 : 0):4}", setup="v=abcdefghij; n=3",
      iters=3000),
]

from dataclasses import replace as _replace  # noqa: E402

CASES += [_replace(c, tags=c.tags + ("v2",)) for c in _V2]
del _replace, _V2
