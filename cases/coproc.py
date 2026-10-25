"""Coprocesses (bash 4+ `coproc`): spawn cost, request/response
round-trips through named coprocs, streaming producers/consumers and
lifecycle. Added in corpus v2 -- coprocs had no v1 coverage at all.

Shapes are chosen to be deadlock-free by construction: every case
either alternates write/read strictly (request/response) or only
reads from a finite producer.

External stream filters (tr, rev) block-buffer their output when it
is a pipe, which deadlocks a strict round-trip; those coprocs are
launched through `stdbuf -o0` so each line is readable as produced.
(cat uses unbuffered read/write and needs no such help.)

Lifecycle note: tearing a coproc down with `kill %job` is racy in a
respawn loop (a missed kill leaves `wait` hanging on a cat whose
stdin the shell still holds). The deterministic form used here is
EOF teardown: close the write fd (the filter sees EOF and exits),
close the read fd, then `wait $NAME_PID` to reap. Order matters:
both closes must precede the wait -- once the coproc is reaped its
fd array is cleared and `{NAME[0]}` expands to nothing ("ambiguous
redirect").
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402


def C(cid, title, body, iters=300, setup="", kind="loop", **kw):
    tags = ("coproc", "v2") + tuple(kw.pop("tags", ()))
    return Case(id=cid, title=title, category="coproc", body=body,
                setup=setup, iters=iters, kind=kind, tags=tags, **kw)


CASES = [
    C("coproc.cat_roundtrip", "coproc cat: write/read round-trip",
      'echo "msg$__bs_i" >&${CAT[1]}; read -r x <&${CAT[0]}',
      setup="coproc CAT { cat; }", iters=500),
    C("coproc.tr_roundtrip", "coproc tr (stdbuf -o0): case round-trip",
      'echo "abc$__bs_i" >&${TRC[1]}; read -r x <&${TRC[0]}',
      setup="coproc TRC { stdbuf -o0 tr 'a-z' 'A-Z'; }", iters=300,
      tags=("spawn",)),
    C("coproc.rev_roundtrip", "coproc rev (stdbuf -o0): reverse trip",
      'echo "str$__bs_i" >&${RV[1]}; read -r x <&${RV[0]}',
      setup="coproc RV { stdbuf -o0 rev; }", iters=300, tags=("spawn",)),
    C("coproc.two_named_chain", "two named coprocs chained by hand",
      'echo "ab$__bs_i" >&${CA[1]}; read -r t <&${CA[0]}; '
      'echo "$t" >&${CB[1]}; read -r x <&${CB[0]}',
      setup="coproc CA { cat; }; coproc CB { stdbuf -o0 tr 'a-z' 'A-Z'; }",
      iters=200, tags=("spawn",)),
    C("coproc.in_func", "coproc round-trip via function wrapper",
      "rt hello",
      setup="coproc CAT { cat; }; "
            "rt() { echo \"$1\" >&${CAT[1]}; read -r x <&${CAT[0]}; }",
      iters=300),
    C("coproc.spawn_oneshot@50", "coproc spawn + round-trip + EOF reap x50",
      "for ((j=0; j<50; j++)); do "
      "coproc C1 { cat; }; echo hi >&${C1[1]}; read -r x <&${C1[0]}; "
      "exec {C1[1]}>&-; exec {C1[0]}<&-; wait $C1_PID 2>/dev/null; done",
      kind="script", iters=50, tags=("spawn",)),
    C("coproc.generator_read@5000", "read 5000 lines from coproc producer",
      "c=0; while IFS= read -r l <&${GEN[0]}; do c=$((c+1)); done; "
      "echo $c >/dev/null",
      setup="coproc GEN { for ((j=0; j<5000; j++)); "
            "do echo \"row $j\"; done; }",
      kind="script", iters=5000),
    C("coproc.sort_stream@1000", "coproc sort: feed 1000, close, drain",
      "for ((j=0; j<1000; j++)); do "
      "printf 'key%04d\\n' $(( (j * 37) % 1000 )) >&${SRT[1]}; done; "
      "exec {SRT[1]}>&-; "
      "c=0; while IFS= read -r l <&${SRT[0]}; do c=$((c+1)); done; "
      "echo $c >/dev/null",
      setup="coproc SRT { sort; }",
      kind="script", iters=1000, tags=("spawn",)),
    C("coproc.reqresp@5000", "coproc responder loop: 5000 request/response",
      "for ((j=0; j<5000; j++)); do "
      "echo \"q$j\" >&${RSP[1]}; read -r x <&${RSP[0]}; done; "
      "echo done >/dev/null",
      setup="coproc RSP { while IFS= read -r q; do echo \"got $q\"; done; }",
      kind="script", iters=5000),
    C("coproc.lifecycle", "coproc start/use/close, twice in sequence",
      "coproc L1 { cat; }; echo a >&${L1[1]}; read -r x <&${L1[0]}; "
      "exec {L1[0]}<&- {L1[1]}>&-; "
      "coproc L2 { cat; }; echo b >&${L2[1]}; read -r y <&${L2[0]}; "
      "exec {L2[0]}<&- {L2[1]}>&-",
      kind="script", iters=2),
]
