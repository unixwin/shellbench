"""Control flow and compound commands."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402


def C(cid, title, body, iters=3000, setup="", **kw):
    return Case(id=cid, title=title, category="control", body=body,
                setup=setup, iters=iters, tags=("control",), **kw)


CASES = [
    C("control.if_true", "if true branch", "if true; then x=1; fi"),
    C("control.if_false_else", "if/else false branch",
      "if false; then x=1; else x=2; fi"),
    C("control.elif_chain_hit3", "elif chain, 3rd matches",
      "if [ $n -eq 1 ]; then x=1; elif [ $n -eq 2 ]; then x=2; "
      "elif [ $n -eq 3 ]; then x=3; else x=9; fi", setup="n=3"),
    C("control.for_list", "for over literal list (body x20)",
      "for v in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; "
      "do x=$v; done", iters=1000),
    C("control.for_arith_inner", "for((;;)) inner loop x50",
      "for ((j=0; j<50; j++)); do x=$j; done", iters=500),
    C("control.while_count", "while arithmetic count x50",
      "j=0; while (( j < 50 )); do ((j++)); done", iters=500),
    C("control.until_count", "until arithmetic count x50",
      "j=0; until (( j >= 50 )); do ((j++)); done", iters=500),
    C("control.case_first", "case first pattern hits",
      "case $v in alpha) x=1;; beta) x=2;; *) x=9;; esac", setup="v=alpha"),
    C("control.case_last", "case last pattern hits",
      "case $v in alpha) x=1;; beta) x=2;; gamma) x=3;; delta) x=4;; esac",
      setup="v=delta"),
    C("control.case_fallthrough", "case ;& fallthrough",
      "case $v in a) x=1 ;& b) x=2 ;;& *) x=3;; esac", setup="v=a"),
    C("control.and_or", "&& || list chain",
      "true && x=1 || x=2; false || y=1 && y=2"),
    C("control.negation", "! negation", "! false"),
    C("control.brace_group", "{ } group", "{ x=1; y=2; z=3; }"),
    C("control.subshell_group", "( ) subshell group", "( x=1; y=2 )",
      iters=500),
    C("control.double_paren_cmd", "(( )) as condition",
      "(( n > 2 ))", setup="n=5", iters=8000),
    C("control.test_bracket_chain", "[ ] && [ ] chain",
      "[ $a = x ] && [ $b = y ]", setup="a=x; b=y", iters=5000),
    C("control.cond_dbracket_and", "[[ && ]] compound",
      "[[ $a == x && $b == y ]]", setup="a=x; b=y", iters=5000),
    C("control.pipeline_status", "PIPESTATUS read after pipeline",
      "true | true; x=${PIPESTATUS[0]}", iters=1000),
    C("control.select_pick", "select picks first item",
      "select o in aa bb cc; do break; done < pick.txt",
      kind="script", iters=20,
      files=(("pick.txt", "1\n"),)),
]
