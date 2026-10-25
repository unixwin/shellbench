"""Big-data shapes beyond the generated ladders: bulk output, big dumps,
bulk string/array growth (the historically quadratic-prone paths)."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402


def C(cid, title, body, iters, setup="", files=(), timeout=300.0, **kw):
    return Case(id=cid, title=title, category="data", body=body,
                setup=setup, iters=iters, kind="script", files=files,
                timeout=timeout, tags=("data",), **kw)


CASES = [
    C("data.printf_bulk@10000", "printf 10k formatted lines",
      "for ((j=0; j<10000; j++)); do printf '%06d name-%d %.2f\\n' "
      "$j $j 3.14; done >/dev/null", 10000),
    C("data.echo_bulk@10000", "echo 10k lines",
      "for ((j=0; j<10000; j++)); do echo \"line $j\"; done >/dev/null",
      10000),
    C("data.declare_p_assoc@10000", "declare -p 10k-entry assoc",
      "declare -p m >/dev/null", 1,
      setup="declare -A m=(); for ((j=0; j<10000; j++)); "
            "do m[k$j]=v$j; done"),
    C("data.declare_p_array@10000", "declare -p 10k-element array",
      "declare -p a >/dev/null", 1,
      setup="a=(); for ((j=0; j<10000; j++)); do a[j]=$j; done"),
    C("data.env_dump", "env output with 500 vars",
      "env >/dev/null", 500,
      setup="\n".join("export BSV%d=v%d" % (i, i) for i in range(500))),
    C("data.set_dump", "set output with 500 vars + functions",
      "set >/dev/null", 500,
      setup="\n".join("BSV%d=v%d" % (i, i) for i in range(500))),
    C("data.string_growth@50000", "string += growth to ~350KB",
      "for ((j=0; j<50000; j++)); do s+=abcdefg; done; n=${#s}", 50000,
      setup="s="),
    C("data.array_growth_read@100000", "read 100k lines into vars",
      "c=0; while IFS= read -r l; do c=$((c+1)); done < data.txt", 100000,
      files=(("data.txt", "@gen:lines:100000"),)),
    C("data.wc_style_count@100000", "count words via read -a over 100k lines",
      "w=0; while read -ra f; do w=$((w+${#f[@]})); done < data.txt",
      100000, files=(("data.txt", "@gen:words:100000"),)),
    C("data.kv_parse@50000", "parse 50k key=value lines with ${} ops",
      "while IFS= read -r l; do k=${l%%=*}; v=${l#*=}; c=$((c+1)); "
      "done < data.txt", 50000,
      files=(("data.txt", "@gen:kv:50000"),)),
]

# --- corpus v2 additions: delimiter reads, fd reads, bulk file
# write/read shapes (1M-line and throughput ladders in v2_gen) ---
_NULS = "\0".join("rec%d" % i for i in range(10000)) + "\0"
_CSVLINE = ",".join("f%d" % i for i in range(260))

_V2 = [
    C("data.read_delim_nul@10000", "read -d '' over 10k NUL records",
      "c=0; while IFS= read -r -d '' rec; do c=$((c+1)); "
      "done < data.bin; echo $c >/dev/null", 10000,
      files=(("data.bin", _NULS),)),
    C("data.mapfile_delim_comma", "mapfile -d , over one 260-field line",
      "mapfile -d , -t a < data.csv; x=${#a[@]}", 260,
      files=(("data.csv", _CSVLINE + "\n"),)),
    C("data.printf_file_block@50000", "printf 50k lines, one redirect",
      "for ((j=0; j<50000; j++)); do printf 'row %d x\\n' $j; "
      "done > out.txt; read -r l < out.txt", 50000),
    C("data.read_u_fd@20000", "read -u 3 over 20k lines",
      "c=0; while IFS= read -r -u 3 l; do c=$((c+1)); "
      "done 3< data.txt; echo $c >/dev/null", 20000,
      files=(("data.txt", "@gen:lines:20000"),)),
    C("data.line_transform_write@20000", "read/transform/write 20k lines",
      "while IFS= read -r l; do "
      "printf '%s|%s\\n' \"${l%% *}\" \"${#l}\"; "
      "done < data.txt > out.txt", 20000,
      files=(("data.txt", "@gen:lines:20000"),)),
    C("data.tail_ring@100000", "ring buffer of last 8 over 100k lines",
      "declare -a ring=(); i=0; while IFS= read -r l; do "
      "ring[i%8]=$l; i=$((i+1)); done < data.txt; x=${ring[0]}", 100000,
      files=(("data.txt", "@gen:lines:100000"),)),
]

from dataclasses import replace as _replace  # noqa: E402

CASES += [_replace(c, tags=c.tags + ("v2",)) for c in _V2]
del _replace, _V2
