"""Conditional expressions: [[ ]] forms and test/[ ] forms beyond the
builtin generator's basic rows."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402


def C(cid, title, body, iters=5000, setup="", files=(), **kw):
    return Case(id=cid, title=title, category="cond", body=body,
                setup=setup, iters=iters, files=files, tags=("cond",), **kw)


CASES = [
    C("cond.dbracket_str_eq", "[[ == ]]", "[[ $a == value ]]", setup="a=value"),
    C("cond.dbracket_str_ne", "[[ != ]]", "[[ $a != other ]]", setup="a=value"),
    C("cond.dbracket_int_chain", "[[ -lt && -gt ]]",
      "[[ $n -gt 3 && $n -lt 10 ]]", setup="n=5"),
    C("cond.dbracket_or", "[[ || ]]", "[[ $a == x || $a == value ]]",
      setup="a=value"),
    C("cond.dbracket_not", "[[ ! -e ]]", "[[ ! -e no_such_file ]]"),
    C("cond.dbracket_file_e", "[[ -e file ]]", "[[ -e case.sh ]]"),
    C("cond.dbracket_file_f", "[[ -f file ]]", "[[ -f case.sh ]]"),
    C("cond.dbracket_file_d", "[[ -d dir ]]", "[[ -d . ]]"),
    C("cond.dbracket_file_s", "[[ -s nonempty ]]", "[[ -s data.txt ]]",
      files=(("data.txt", "@gen:lines:10"),), iters=3000),
    C("cond.dbracket_v_var", "[[ -v var ]]", "[[ -v a ]]", setup="a=1"),
    C("cond.dbracket_v_unset", "[[ -v unset ]]", "[[ -v never_set_var ]]"),
    C("cond.dbracket_o_opt", "[[ -o opt ]]", "[[ -o pipefail ]]"),
    C("cond.dbracket_regex_var", "[[ =~ $re ]] regex from variable",
      "[[ $a =~ $re ]]", setup="a=abc123; re='^[a-z]+[0-9]+$'", iters=3000),
    C("cond.dbracket_pattern_var", "[[ == $pat ]] pattern from variable",
      "[[ $a == $p ]]", setup="a=hello.txt; p='*.txt'", iters=3000),
    C("cond.bracket_combo", "[ ] -a combo", "[ $a = x -a $b = y ]",
      setup="a=x; b=y", iters=3000),
    C("cond.bracket_o_combo", "[ ] -o combo", "[ $a = z -o $a = x ]",
      setup="a=x", iters=3000),
    C("cond.test_file_newer", "test -nt", "[ case.sh -nt data.txt ]",
      files=(("data.txt", "x\n"),), iters=2000),
    C("cond.dbracket_arith_cmp", "[[ a -eq b ]] vars",
      "[[ $a -eq $b ]]", setup="a=42; b=42"),
]
