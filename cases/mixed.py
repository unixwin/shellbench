"""Mixed realistic workloads: small end-to-end scripts in the shapes
people actually run -- log tallying, config parsing, report formatting,
token state machines. Each is script-kind; iters = input size."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402


def C(cid, title, body, iters, files=(), setup="", **kw):
    return Case(id=cid, title=title, category="mixed", body=body,
                setup=setup, iters=iters, kind="script", files=files,
                tags=("mixed",), **kw)


CASES = [
    C("mixed.log_tally@20000", "log tally: count by 3rd field (assoc)",
      "declare -A cnt=(); "
      "while read -r f1 f2 f3 rest; do cnt[$f3]=$(( ${cnt[$f3]:-0} + 1 )); "
      "done < log.txt; "
      "for k in \"${!cnt[@]}\"; do echo \"$k ${cnt[$k]}\"; done >/dev/null",
      20000, files=(("log.txt", "@gen:words:20000"),)),
    C("mixed.config_parse@2000", "config parse: kv + path building",
      "while IFS== read -r k v; do "
      "case $k in path*) eval \"P_$k=$v\";; *) eval \"C_$k=$v\";; esac; "
      "done < cfg.txt; x=$C_key500", 2000,
      files=(("cfg.txt", "@gen:kv:2000"),)),
    C("mixed.name_transform@5000", "filename transform over path list",
      "while IFS= read -r p; do d=${p%/*}; b=${p##*/}; n=${b%.txt}.md; "
      "echo \"$d/$n\"; done < paths.txt >/dev/null", 5000,
      files=(("paths.txt", "@gen:path:5000"),)),
    C("mixed.report_table@2000", "formatted report table via printf",
      "for ((j=0; j<2000; j++)); do "
      "printf '| %-12s | %8d | %6.2f |\\n' item$j $j 2.5; done >/dev/null",
      2000),
    C("mixed.token_machine@10000", "token state machine over csv",
      "state=0; total=0; "
      "while IFS=, read -r a b c d e f; do "
      "case $state in 0) state=1;; 1) total=$((total+a)); state=0;; esac; "
      "done < data.csv; echo $total >/dev/null", 10000,
      files=(("data.csv", "@gen:csv:10000"),)),
    C("mixed.field_extract@20000", "field extraction via ${} surgery",
      "while IFS= read -r l; do h=${l%% *}; t=${l##* }; m=${l#* }; "
      "c=$((c+1)); done < log.txt", 20000,
      files=(("log.txt", "@gen:lines:20000"),), setup="c=0"),
    C("mixed.dispatch_loop@5000", "command dispatch loop (case + funcs)",
      "for ((j=0; j<5000; j++)); do "
      "case $((j % 4)) in 0) inc;; 1) add 3;; 2) noop;; 3) get;; esac; done",
      5000,
      setup="n=0; inc() { n=$((n+1)); }; add() { n=$((n+$1)); }; "
            "noop() { :; }; get() { x=$n; }"),
    C("mixed.arg_parse@1000", "hand-rolled CLI arg parsing loop",
      "set -- -v --out file.txt --count 42 target; "
      "while (( $# )); do case $1 in -v) v=1;; --out) shift; o=$1;; "
      "--count) shift; c=$1;; *) t=$1;; esac; shift; done", 1000),
]
