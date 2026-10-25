"""Arrays and associative arrays: fill, iterate, slice, dump, mutate.

Cases whose body contains its own full traversal are script-kind with
``iters`` = element count, so ns/op reads as per-element cost.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

_FILL1K = "a=(); for ((j=0; j<1000; j++)); do a[j]=$j; done"
_FILL_ASSOC = ("declare -A m=(); for ((j=0; j<1000; j++)); "
               "do m[key$j]=$j; done")


def C(cid, title, body, iters=3000, setup="", kind="loop", **kw):
    return Case(id=cid, title=title, category="arrays", body=body,
                setup=setup, iters=iters, kind=kind, tags=("arrays",), **kw)


CASES = [
    C("arrays.append_loop", "a+=(x) append in loop", "a+=(item)",
      setup="a=()"),
    C("arrays.assign_idx_mod", "a[i%64]=x indexed assign",
      "a[__bs_i % 64]=x", setup="a=()", iters=8000),
    C("arrays.read_elem", "a[42] element read", "x=${a[42]}",
      setup="a=(0 1 2 3 4 5 6 7 8 9)", iters=8000),
    C("arrays.read_negidx", "a[-1] negative index", "x=${a[-1]}",
      setup="a=(0 1 2 3 4 5 6 7 8 9)", iters=8000),
    C("arrays.compound_assign", "a=(...) compound assign",
      "a=(one two three four five)", iters=3000),
    C("arrays.iterate_atq@1000", '"${a[@]}" full iteration',
      "for e in \"${a[@]}\"; do c=$((c+1)); done",
      setup=_FILL1K + "; c=0", kind="script", iters=1000),
    C("arrays.iterate_index@1000", "indexed iteration a[j]",
      "for ((j=0; j<1000; j++)); do x=${a[j]}; done",
      setup=_FILL1K, kind="script", iters=1000),
    C("arrays.iterate_keys@1000", '"${!a[@]}" index iteration',
      "for k in \"${!a[@]}\"; do x=${a[k]}; done",
      setup=_FILL1K, kind="script", iters=1000),
    C("arrays.slice@1000", "slice ${a[@]:100:50} of 1000",
      "b=(\"${a[@]:100:50}\")", setup=_FILL1K, iters=300),
    C("arrays.copy_unset@1000", "copy + unset middle element",
      "b=(\"${a[@]}\"); unset 'b[500]'", setup=_FILL1K, iters=200),
    C("arrays.declare_p@1000", "declare -p of 1000-element array",
      "declare -p a >/dev/null", setup=_FILL1K, iters=100),
    C("arrays.assoc_setget", "assoc set+get pair",
      "m[k$__bs_i]=$__bs_i; x=${m[k$__bs_i]}",
      setup="declare -A m=()", iters=3000),
    C("arrays.assoc_get_hit", "assoc get (hit)", "x=${m[key500]}",
      setup=_FILL_ASSOC, iters=8000),
    C("arrays.assoc_get_miss", "assoc get (miss)", "x=${m[nope]}",
      setup=_FILL_ASSOC, iters=8000),
    C("arrays.assoc_iterate@1000", '"${!m[@]}" assoc key iteration',
      "for k in \"${!m[@]}\"; do x=${m[$k]}; done",
      setup=_FILL_ASSOC, kind="script", iters=1000),
    C("arrays.assoc_values@1000", '"${m[@]}" assoc value iteration',
      "for v in \"${m[@]}\"; do c=$((c+1)); done",
      setup=_FILL_ASSOC + "; c=0", kind="script", iters=1000),
    C("arrays.assoc_fill@10000", "assoc fill 10000 entries",
      "for ((j=0; j<10000; j++)); do m[key$j]=v$j; done; n=${#m[@]}",
      setup="declare -A m=()", kind="script", iters=10000),
    C("arrays.append@100000", "append 100k elements one by one",
      "for ((j=0; j<100000; j++)); do a+=(x$j); done; n=${#a[@]}",
      setup="a=()", kind="script", iters=100000, timeout=300.0),
    C("arrays.sparse_set", "sparse array far index assign",
      "a[100000]=x; unset 'a[100000]'", setup="a=()", iters=1000),
    C("arrays.length_elem", "${#a[3]} element length", "x=${#a[3]}",
      setup="a=(aa bbb cccc ddddd)", iters=8000),
]
