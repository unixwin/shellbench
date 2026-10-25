"""Command substitution, process substitution, backquotes.

Several cases spawn the shell itself or coreutils -- that cost is part of
the shape being measured and is tagged ``spawn`` so reports can separate
in-process work from process plumbing.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402


def C(cid, title, body, iters=300, setup="", kind="loop", **kw):
    tags = ("subst",) + tuple(kw.pop("tags", ()))
    return Case(id=cid, title=title, category="subst", body=body,
                setup=setup, iters=iters, kind=kind, tags=tags, **kw)


CASES = [
    C("subst.cmd_builtin_echo", "$(echo) builtin capture", "x=$(echo hi)"),
    C("subst.cmd_true", "$(true)", "x=$(true)", iters=500),
    C("subst.cmd_self", "$($BASH -c) self spawn", "x=$($BASH -c 'echo hi')",
      iters=100, tags=("subst", "spawn")),
    C("subst.cmd_ext_date", "$(date) external spawn", "x=$(date +%s)",
      iters=100, tags=("subst", "spawn")),
    C("subst.cmd_nested2", "two-level nesting", "x=$(echo $(echo hi))",
      iters=200),
    C("subst.cmd_big_output", "capture 200 lines",
      "x=$(printf 'l\\n%.0s' $(seq 1 200))", iters=50,
      tags=("subst", "spawn")),
    C("subst.cmd_assign_trim", "capture + trailing strip",
      "x=$(echo '  padded  ')", iters=300),
    C("subst.backquote_echo", "`echo` backquotes", "x=`echo hi`"),
    C("subst.procsub_cat", "cat <(echo) process substitution",
      "cat <(echo hi) >/dev/null", iters=100, tags=("subst", "spawn")),
    C("subst.procsub_read", "read loop over <(printf)",
      "while IFS= read -r l; do c=$((c+1)); done < <(printf 'a\\nb\\nc\\n')",
      setup="c=0", iters=100),
    C("subst.procsub_two", "diff-style two procsubs to cat",
      "cat <(echo a) <(echo b) >/dev/null", iters=100,
      tags=("subst", "spawn")),
    C("subst.arith_nested_subst", "$(( $(...) )) nesting",
      "x=$(( $(echo 40) + 2 ))", iters=200),
    C("subst.subshell_assign", "( ) subshell with assigns",
      "( a=1; b=2; c=$((a+b)) )", iters=500),
    C("subst.subshell_pipe", "subshell in pipeline",
      "( echo a; echo b ) | wc -l >/dev/null", iters=100,
      tags=("subst", "spawn")),
]
