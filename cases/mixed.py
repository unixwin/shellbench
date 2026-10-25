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

# --- corpus v2 additions: more realistic script shapes (size ladders
# for generated shapes live in generators/v2_gen.py) ---
_INI2000 = "\n".join(
    ("[sec%d]" % (i // 20)) if i % 20 == 0 else
    ("key%d=value%d" % (i, i)) for i in range(2000)) + "\n"

_V2 = [
    C("mixed.ini_section_parse@2000", "ini parse: sections into assoc",
      "declare -A cfg=(); sec=base; "
      "while IFS= read -r l; do "
      "case $l in \\[*\\]) sec=${l#[}; sec=${sec%]};; "
      "*) cfg[$sec.${l%%=*}]=${l#*=};; esac; "
      "done < cfg.ini; x=${cfg[sec5.key105]}", 2000,
      files=(("cfg.ini", _INI2000),)),
    C("mixed.log_levels_count@20000", "count 2nd-field value over word log",
      "declare -A cnt=(); "
      "while read -r w1 w2 rest; do "
      "case $w2 in charlie) cnt[c]=$(( ${cnt[c]:-0} + 1 ));; "
      "*) cnt[o]=$(( ${cnt[o]:-0} + 1 ));; esac; "
      "done < log.txt; echo ${cnt[c]} >/dev/null", 20000,
      files=(("log.txt", "@gen:words:20000"),)),
    C("mixed.url_split@5000", "split URLs into proto/host/path",
      "for ((j=0; j<5000; j++)); do "
      "u=\"https://cdn$((j % 50)).example.com/assets/img$j.png?v=$j\"; "
      "proto=${u%%://*}; rest=${u#*://}; host=${rest%%/*}; "
      "path=${rest#*/}; done; x=$host", 5000),
    C("mixed.semver_compare@2000", "semver-ish compare loop",
      "gt=0; for ((j=0; j<2000; j++)); do "
      "a=\"1.$((j % 20)).$((j % 7))\"; b=\"1.$((j % 20)).5\"; "
      "IFS=. read -ra pa <<< \"$a\"; IFS=. read -ra pb <<< \"$b\"; "
      "if (( pa[2] > pb[2] )); then gt=$((gt+1)); fi; done; "
      "echo $gt >/dev/null", 2000),
    C("mixed.rpn_machine@5000", "RPN stack machine over token cycle",
      "declare -a st=(); top=0; "
      "for ((j=0; j<5000; j++)); do "
      "case $((j % 5)) in "
      "0|1) st[top++]=$j;; "
      "2) top=$((top-1)); st[top-1]=$(( st[top-1] + st[top] ));; "
      "3) top=$((top-1)); st[top-1]=$(( st[top-1] * st[top] ));; "
      "4) x=${st[top-1]};; esac; done; echo $x >/dev/null", 5000),
    C("mixed.merge_sorted@2000", "merge two sorted 1000-arrays",
      "i=0; j=0; c=0; "
      "while (( i < 1000 && j < 1000 )); do "
      "if (( a[i] < b[j] )); then last=${a[i]}; i=$((i+1)); "
      "else last=${b[j]}; j=$((j+1)); fi; c=$((c+1)); done; "
      "echo $c >/dev/null", 2000,
      setup="a=(%s); b=(%s)" % (
          " ".join(str(2 * i) for i in range(1000)),
          " ".join(str(2 * i + 1) for i in range(1000)))),
    C("mixed.backoff_calc@10000", "exponential backoff with cap, summed",
      "d=1; s=0; for ((j=0; j<10000; j++)); do d=$((d * 2)); "
      "if (( d > 30000 )); then d=30000; fi; s=$((s + d)); done; "
      "echo $s >/dev/null", 10000),
    C("mixed.env_sanitize@2000", "filter kv lines by key pattern, re-emit",
      "n=0; while IFS== read -r k v; do "
      "case $k in key1*) echo \"export $k='$v'\"; n=$((n+1));; esac; "
      "done < env.txt > out.txt; echo $n >/dev/null", 2000,
      files=(("env.txt", "@gen:kv:2000"),)),
]

from dataclasses import replace as _replace  # noqa: E402

CASES += [_replace(c, tags=c.tags + ("v2",)) for c in _V2]
del _replace, _V2
