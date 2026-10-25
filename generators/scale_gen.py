"""Scale-ladder generator: one spec row -> one case per scale rung.

Data-family cases are script-kind: the fixture is generated host-side at
each rung (lines/elements), the script processes it once per repetition,
and ``iters`` records the rung size so throughput is ops/second.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

# (suffix, title, fixture spec template, body, tags)
ROWS = [
    ("read_loop", "while read line loop", "@gen:lines:{n}",
     "while IFS= read -r l; do c=$((c+1)); done < data.txt", ("io",)),
    ("read_mapfile", "mapfile whole file", "@gen:lines:{n}",
     "mapfile -t a < data.txt; x=${#a[@]}", ("io",)),
    ("read_ifs_fields", "read fields per line", "@gen:csv:{n}",
     "while IFS=, read -r f1 f2 f3 f4 f5 f6; do c=$((c+1)); done < data.txt", ("io",)),
    ("grep_builtin_loop", "pattern test per line", "@gen:words:{n}",
     "while IFS= read -r l; do [[ $l == *charlie* ]] && c=$((c+1)); done < data.txt", ("io", "cond")),
    ("sort_via_array", "array sort builtin loop (bubble-free: sort ext excluded; uses string join)",
     "@gen:words:{n}",
     "mapfile -t a < data.txt; x=${a[*]}", ("io",)),
    ("word_count_loop", "accumulate lengths", "@gen:lines:{n}",
     "while IFS= read -r l; do t=$((t+${#l})); done < data.txt", ("io",)),
    ("assoc_fill", "assoc fill from kv file", "@gen:kv:{n}",
     "while IFS== read -r k v; do m[$k]=$v; done < data.txt; x=${#m[@]}",
     ("assoc",)),
    ("array_fill_lines", "indexed fill from file", "@gen:lines:{n}",
     "i=0; while IFS= read -r l; do a[i++]=$l; done < data.txt", ("array",)),
]

RUNGS = (10, 1000, 100000)


def cases() -> list:
    out = []
    for suffix, title, fixture, body, tags in ROWS:
        for n in RUNGS:
            out.append(Case(
                id="data.%s@%d" % (suffix, n),
                title="data ladder: %s (n=%d)" % (title, n),
                category="data", kind="script",
                tags=("data", "generated", "ladder") + tags,
                setup="declare -A m=(); a=(); c=0; t=0",
                body=body, iters=n,
                files=(("data.txt", fixture.format(n=n)),),
                timeout=300.0))
    return out
