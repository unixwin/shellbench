"""Function call overhead in its shapes."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402


def C(cid, title, body, iters=3000, setup="", kind="loop", **kw):
    tags = ("funcs",) + tuple(kw.pop("tags", ()))
    return Case(id=cid, title=title, category="funcs", body=body,
                setup=setup, iters=iters, kind=kind, tags=tags, **kw)


CASES = [
    C("funcs.call_empty", "call empty function", "f", setup="f() { :; }",
      iters=8000),
    C("funcs.call_args", "call with 4 args", "f aa bb cc dd",
      setup="f() { :; }", iters=5000),
    C("funcs.call_local", "call with local assign", "f",
      setup="f() { local y=1; }", iters=5000),
    C("funcs.call_local_arith", "local + arithmetic", "f",
      setup="f() { local y=$(( $1 + 1 )); }", iters=3000),
    C("funcs.call_return_code", "return code path", "f; x=$?",
      setup="f() { return 7; }", iters=5000),
    C("funcs.call_shift_args", "shift inside function", "f a b c d e",
      setup="f() { shift 2; x=$1; }", iters=3000),
    C("funcs.call_nested3", "3-deep call chain", "f1",
      setup="f3() { :; }; f2() { f3; }; f1() { f2; }", iters=3000),
    C("funcs.call_in_subst", "function call in $()", "x=$(f)",
      setup="f() { echo hi; }", iters=500),
    C("funcs.recursive_fib15", "recursive fib(15)",
      "r=$(fib 15)", setup=("fib() { if (( $1 < 2 )); then echo $1; "
                            "else echo $(( $(fib $(($1-1))) + "
                            "$(fib $(($1-2))) )); fi; }"),
      kind="script", iters=1, timeout=120.0),
    C("funcs.redefine", "function redefinition",
      "g() { :; }", iters=3000),
    C("funcs.declare_f_dump", "declare -f dump", "declare -f f >/dev/null",
      setup="f() { local a=1; echo $a; echo done; }", iters=1000),
    C("funcs.export_f", "export -f + child shell call",
      "$BASH -c f", setup="f() { :; }; export -f f", iters=200,
      tags=("funcs", "spawn")),
]

# --- corpus v2 additions (argument/local/chain ladders live in
# generators/v2_gen.py; these are the hand-shaped call forms) ---
CASES += [
    C("funcs.call_capture_counter", "call + capture counter via $()",
      "x=$(f)", setup="n=0; f() { n=$((n+1)); echo $n; }", iters=1000,
      tags=("v2",)),
    C("funcs.call_redir_devnull", "call with >/dev/null 2>&1 on the call",
      "f >/dev/null 2>&1", setup="f() { echo out; echo err >&2; }",
      iters=2000, tags=("v2",)),
    C("funcs.call_passthrough3", "arg transformed down a 3-call chain",
      "f 0",
      setup="h() { x=$1; }; g() { h $(($1+1)); }; "
            "f() { g $(($1+1)); }", iters=3000, tags=("v2",)),
    C("funcs.call_variadic_sum", "variadic $@ arithmetic sum",
      "f 1 2 3 4 5 6",
      setup="f() { local s=0 a; for a in \"$@\"; do s=$((s+a)); done; "
            "x=$s; }", iters=3000, tags=("v2",)),
    C("funcs.call_local_array", "local array inside function",
      "f", setup="f() { local -a t=(1 2 3); x=${t[1]}; }", iters=3000,
      tags=("v2",)),
    C("funcs.call_forward_at", "forward \"$@\" to another function",
      "f a b c d e", setup="g() { x=$#; }; f() { g \"$@\"; }",
      iters=3000, tags=("v2",)),
    C("funcs.recur_countdown@100", "recursive countdown sum from 100",
      "r=$(f 100); echo $r >/dev/null",
      setup="f() { if (( $1 <= 0 )); then echo 0; "
            "else echo $(( $1 + $(f $(($1-1))) )); fi; }",
      kind="script", iters=100, tags=("v2",), timeout=120.0),
    C("funcs.call_in_pipeline", "function as pipeline stage",
      "printf 'x\\n' | f | read -r x",
      setup="f() { read -r l; echo \"got:$l\"; }", iters=150,
      tags=("v2", "spawn")),
]
