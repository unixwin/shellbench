"""Hot-loop data generator v2: realistic data-processing throughput in pure shell.

Complements ``scale_gen.py`` (script-kind data ladders) and
``hotloop_misc_gen.py`` (dispatch-cost surface) with the "mixed script" class
at hot-loop scale: line/field/record surgery, config-ish parsing, filename
transforms, histograms/top-N/stats, and end-to-end report scripts over
``@gen:`` fixtures.

Rows are (suffix, title, setup, body, iters, extra_tags, files); scripts are
(suffix, title, body, iters, files). Bodies must exit 0, be deterministic,
and avoid per-iteration sleeps; fork-heavy rows get N_SLOW iters, external
spawns N_SPAWN.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

N = 10000
N_SLOW = 2000      # fork / comsub / procsub / source cost
N_SPAWN = 500      # external process spawn cost

ROWS = []
SCRIPTS = []
_SEQ = {}


def bump(key):
    """Deterministic per-section counter (hash() is salted per process)."""
    _SEQ[key] = _SEQ.get(key, 0) + 1
    return _SEQ[key]


def add(suffix, title, setup, body, iters=N, extra=(), files=()):
    ROWS.append((suffix, title, setup, body, iters, tuple(extra),
                 tuple(files)))


def sadd(suffix, title, body, iters, files=(), setup=""):
    SCRIPTS.append((suffix, title, body, iters, tuple(files), setup))


def sfile(name, spec):
    return ((name, spec),)


# ===========================================================================
# Fixture helpers (host-side content builders)
# ===========================================================================

# ~20 mixed-shape lines used as an in-memory "record stream" source for
# loop-kind micro cases. Covers: numbered text, k=v, bare number, path,
# timestamped level, colon fields, csv-ish, padded, mixed case, long run,
# short, k=v#comment, floats, upper/lower mix, deep path, 5 fields, radix
# literals, hashtag, trailing space.
LINE_STRS = [
    "line 1 lorem ipsum 7",
    "key42=value99",
    "alpha beta gamma delta",
    "12345",
    "dir3/sub5/file_9.txt",
    "INFO 2024-01-01 ok",
    "user:pass:host:22",
    "a,b,c,4,5",
    "  padded  ",
    "MiXeD CaSe LiNe",
    "x" * 40,
    "short",
    "k=v#comment",
    "10.5 20.25",
    "UPPER lower MiXeD",
    "path/to/deep/nested/file.log",
    "field1 field2 field3 field4 field5",
    "0x1F 0b101 0777",
    "#hashtag line",
    "trailing space ",
]
NLINES = len(LINE_STRS)

ARR_SETUP = "n=0;t=0;w=0;s=0;q=0;mn=999;mx=-1;prev=;declare -A f=()\n" \
            "A=(%s)" % " ".join("'%s'" % l.replace("'", "'\\''")
                                for l in LINE_STRS)

NUM_STRS = [str((i * 37) % 1000) for i in range(16)]
NUM_SETUP = ARR_SETUP + "\nN=(%s)" % " ".join(NUM_STRS)

# Small file fixtures for per-iter reopen reads (content irrelevant beyond
# line 1 since each iteration re-opens the file).
F_LINES8 = sfile("data.txt", "@gen:lines:8")
F_KV8 = sfile("kv.txt", "@gen:kv:8")
F_CSV8 = sfile("data.csv", "@gen:csv:8")
F_WORDS8 = sfile("words.txt", "@gen:words:8")
F_PATH8 = sfile("paths.txt", "@gen:path:8")

# 10k-line fixtures for pre-opened fd / mapfile consumption at iters=10000.
F_LINES10K = sfile("data.txt", "@gen:lines:10000")
F_KV10K = sfile("kv.txt", "@gen:kv:10000")
F_CSV10K = sfile("data.csv", "@gen:csv:10000")
F_WORDS10K = sfile("words.txt", "@gen:words:10000")
F_PATH10K = sfile("paths.txt", "@gen:path:10000")


def nums_file(n):
    return "".join("%d\n" % ((i * 37) % 1000) for i in range(n))


F_NUMS10K = (("nums.txt", nums_file(10000)),)

# NUL-delimited records, 2000 records, for read -d '' shapes.
NUL_REC = "".join("rec%d\0" % i for i in range(2000))
F_NUL2K = (("data.bin", NUL_REC),)

# Glob fixture tree: 12 files across 3 subdirs + loose files.
GLOB_FILES = tuple(
    [("d%da/f%02d.txt" % (i % 3, i), "x\n") for i in range(9)]
    + [("top%d.log" % i, "y\n") for i in range(3)]
)

# ===========================================================================
# 1. READ-FROM-FILE PER ITER (reopen fd0 / pre-opened fd / typed reads)
# ===========================================================================

# Reopen-per-iter: `read ... < file` re-opens fd 0 each iteration, so every
# read sees line 1 -- measures open+read+close+parse per op.
add("read_reopen_count", "reopen fd0 read, discard",
    "", "IFS= read -r l < data.txt", files=F_LINES8)
add("read_reopen_len", "reopen fd0 read + ${#l}",
    "n=0", "IFS= read -r l < data.txt; n=$((n+${#l}))",
    files=F_LINES8)
add("read_reopen_words", "reopen fd0 read + word count",
    "n=0", "IFS= read -r l < data.txt; set -- $l; n=$((n+$#))",
    files=F_LINES8)
add("read_reopen_arr", "reopen fd0 read -ra",
    "n=0", "IFS= read -ra p < data.txt; n=$((n+${#p[@]}))",
    files=F_WORDS8)
add("read_reopen_kv", "reopen fd0 IFS== kv split",
    "n=0", "IFS== read -r k v < kv.txt; n=$((n+${#k}+${#v}))",
    files=F_KV8)
add("read_reopen_csv", "reopen fd0 IFS=, csv split",
    "n=0", "IFS=, read -r a b c d e f < data.csv; n=$((n+${#a}+${#f}))",
    files=F_CSV8)
add("read_reopen_path", "reopen fd0 path fields",
    "n=0", "IFS= read -r p < paths.txt; b=${p##*/}; n=$((n+${#b}))",
    files=F_PATH8)

# Pre-opened fd: position advances across iters; file has exactly iters
# lines so every read consumes a real record. autorange disabled so the
# file never under-runs the iteration count.
add("read_fd9_count", "pre-opened fd9 consume lines",
    "exec 9< data.txt", "IFS= read -r -u 9 l || :", files=F_LINES10K)
add("read_fd9_len", "pre-opened fd9 + ${#l}",
    "exec 9< data.txt\nn=0",
    "IFS= read -r -u 9 l || :; n=$((n+${#l}))", files=F_LINES10K)
add("read_fd9_arr", "pre-opened fd9 read -ra",
    "exec 9< data.txt\nn=0",
    "IFS= read -ra -u 9 p || :; n=$((n+${#p[@]}))", files=F_WORDS10K)
add("read_fd9_kv", "pre-opened fd9 IFS== kv",
    "exec 9< kv.txt\nn=0",
    "IFS== read -r -u 9 k v || :; n=$((n+${#k}+${#v}))", files=F_KV10K)
add("read_fd9_csv", "pre-opened fd9 IFS=, csv",
    "exec 9< data.csv\nn=0",
    "IFS=, read -r -u 9 a b c d e f || :; n=$((n+a))", files=F_CSV10K)
add("read_fd9_num", "pre-opened fd9 numeric sum",
    "exec 9< nums.txt\nn=0",
    "IFS= read -r -u 9 x || :; n=$((n+x))", files=F_NUMS10K)
add("read_fd3_count", "pre-opened fd3 consume lines",
    "exec 3< data.txt", "IFS= read -r -u 3 l || :", files=F_LINES10K)
add("read_fd9_nul", "pre-opened fd9 read -d '' NUL records",
    "exec 9< data.bin\nn=0",
    "IFS= read -r -d '' -u 9 rec || :; n=$((n+1))", files=F_NUL2K,
    iters=N_SLOW)

# ===========================================================================
# 2. MAPFILE / ARRAY-INDEXED LINE SOURCES
# ===========================================================================

MAP_SETUP = "mapfile -t MA < data.txt"
MAP_OPS = [
    ("idx_len", "l=${MA[$__bs_i]}; n=$((n+${#l}))"),
    ("idx_strip", "l=${MA[$__bs_i]}; x=${l##* }; n=$((n+${#x}))"),
    ("idx_cut", "l=${MA[$__bs_i]}; x=${l:0:8}; y=${l:8:8}; "
               "n=$((n+${#x}+${#y}))"),
    ("idx_up", "l=${MA[$__bs_i]}; u=${l^^}; n=$((n+${#u}))"),
    ("idx_case", "l=${MA[$__bs_i]}; case $l in line*) n=$((n+1));; esac"),
    ("idx_mod", "l=${MA[$__bs_i%97]}; n=$((n+${#l}))"),
    ("idx_setdollar", "l=${MA[$__bs_i%997]}; set -- $l; n=$((n+$#))"),
    ("idx_prefix", "l=${MA[$__bs_i%991]}; case $l in INFO*|line*) "
                  "n=$((n+1));; esac"),
    ("idx_sub", "l=${MA[$__bs_i%983]}; x=${l// /_}; n=$((n+${#x}))"),
    ("idx_wordlen", "l=${MA[$__bs_i%971]}; set -- $l; for x in \"$@\"; "
                    "do w=$((w+${#x})); done"),
]
for suffix, body in MAP_OPS:
    add("mapfile_%s" % suffix, "mapfile idx %s" % suffix,
        MAP_SETUP + "\nn=0;t=0;w=0", body, files=F_LINES10K)

# ===========================================================================
# 3. ARRAY-SOURCED LINE OPS (in-memory record stream)
# ===========================================================================
# Each op runs once per iter on l=${A[i%20]}; covers the data-surgery class.

ARR_OPS = [
    ("len", "n=$((n+${#l}))"),
    ("up", "u=${l^^}; n=$((n+${#u}))"),
    ("low", "u=${l,,}; n=$((n+${#u}))"),
    ("atU", "u=${l@U}; n=$((n+${#u}))"),
    ("atu", "u=${l@u}; n=$((n+${#u}))"),
    ("atQ", "q=${l@Q}; n=$((n+${#q}))"),
    ("atE", "e=${l@E}; n=$((n+${#e}))"),
    ("atP", "p=${l@P}; n=$((n+${#p}))"),
    ("atA", "a2=${l@A}; n=$((n+${#a2}))"),
    ("cut08", "x=${l:0:8}; y=${l:8:8}; n=$((n+${#x}+${#y}))"),
    ("negoff", "x=${l: -8}; n=$((n+${#x}))"),
    ("sub1", "x=${l/x/YY}; n=$((n+${#x}))"),
    ("suball", "x=${l//a/A}; n=$((n+${#x}))"),
    ("subsp", "x=${l// /_}; n=$((n+${#x}))"),
    ("strip_hash", "x=${l##* }; n=$((n+${#x}))"),
    ("strip_path", "d=${l%/*}; b=${l##*/}; n=$((n+${#d}+${#b}))"),
    ("strip_ext", "b=${l##*/}; x=${b%.txt}; n=$((n+${#x}))"),
    ("trim_sp", "x=${l# }; y=${l% }; n=$((n+${#x}+${#y}))"),
    ("case_first", "case ${l:0:1} in [a-z]) n=$((n+1));; "
                  "[0-9]) t=$((t+1));; esac"),
    ("case_glob", "case $l in *key*|*dir*|*file*) n=$((n+1));; esac"),
    ("case_num", "case $l in [0-9]*) n=$((n+1));; esac"),
    ("case_ext", "case $l in *.txt|*.log) n=$((n+1));; esac"),
    ("if_prefix", "[[ $l == key* ]] && n=$((n+1))"),
    ("kv_split", "IFS== read -r k v <<<\"$l\"; "
                "n=$((n+${#k}+${#v}))"),
    ("colon_split", "IFS=: read -ra p <<<\"$l\"; n=$((n+${#p[@]}))"),
    ("comma_split", "IFS=, read -ra p <<<\"$l\"; n=$((n+${#p[@]}))"),
    ("set_dollar", "set -- $l; n=$((n+$#))"),
    ("readra_hs", "read -ra p <<<\"$l\"; n=$((n+${#p[@]}))"),
    ("nested_fields", "set -- $l; for x in \"$@\"; do "
                      "w=$((w+${#x})); done"),
    ("word_lens", "read -ra p <<<\"$l\"; for x in \"${p[@]}\"; do "
                 "w=$((w+${#x})); done"),
    ("prev_cmp", "[ \"$l\" = \"$prev\" ] && n=$((n+1)); prev=$l"),
    ("freq_assoc", "f[\"$l\"]=$(( ${f[\"$l\"]:-0} + 1 ))"),
    ("comment_strip", "x=${l%%#*}; n=$((n+${#x}))"),
    ("first_word", "x=${l%% *}; n=$((n+${#x}))"),
    ("last_word", "x=${l##* }; n=$((n+${#x}))"),
    ("mid_strip", "x=${l#* }; y=${x% *}; n=$((n+${#y}))"),
]
for op, expr in ARR_OPS:
    add("arr_%s" % op, "line-op %s over in-mem stream" % op,
        ARR_SETUP, "l=${A[$((__bs_i%%%d))]}; %s" % (NLINES, expr))

# Compound variants: two ops per iter on the same line.
COMPOUND_OPS = [
    ("len_cut", "x=${l:0:8}; n=$((n+${#l}+${#x}))"),
    ("strip_len", "x=${l##* }; y=${x%%#*}; n=$((n+${#y}))"),
    ("case_len", "case $l in key*) n=$((n+1));; esac; "
                "n=$((n+${#l}))"),
    ("up_len_sub", "u=${l^^}; x=${u// /_}; n=$((n+${#x}))"),
    ("split_len", "IFS=: read -ra p <<<\"$l\"; "
                 "for x in \"${p[@]}\"; do w=$((w+${#x})); done"),
    ("kv_split_trim", "x=${l%%#*}; IFS== read -r k v <<<\"$x\"; "
                     "n=$((n+${#k}+${#v}))"),
]
for op, expr in COMPOUND_OPS:
    add("arr2_%s" % op, "compound line-op %s" % op,
        ARR_SETUP, "l=${A[$((__bs_i%%%d))]}; %s" % (NLINES, expr))

# ===========================================================================
# 4. NUMERIC / STATS / HISTOGRAM / TOP-N over the stream
# ===========================================================================

NUM_OPS = [
    ("sum", "v=${N[$((__bs_i%16))]}; s=$((s+v))"),
    ("sumsq", "v=${N[$((__bs_i%16))]}; q=$((q+v*v))"),
    ("stats", "v=$((__bs_i%100)); s=$((s+v)); q=$((q+v*v)); "
             "((v<mn)) && mn=$v; ((v>mx)) && mx=$v"),
    ("hist3", "d=$((__bs_i%10)); case $d in 0|1|2|3|4) b0=$((b0+1));; "
             "5|6|7) b1=$((b1+1));; *) b2=$((b2+1));; esac"),
    ("hist_range", "v=$((__bs_i%97)); case $v in [0-9]|[0-9][0-9]) "
                  "b0=$((b0+1));; *) b1=$((b1+1));; esac"),
    ("top3", "v=$((__bs_i*37%97)); if ((v>t1)); then t3=$t2; t2=$t1; "
            "t1=$v; elif ((v>t2)); then t3=$t2; t2=$v; elif ((v>t3)); "
            "then t3=$v; fi"),
    ("mod_dispatch", "case $((__bs_i%6)) in 0|3) n=$((n+1));; 1|4) "
                    "t=$((t+1));; *) w=$((w+1));; esac"),
    ("running_avg", "s=$((s+__bs_i)); c=$((c+1))"),
]
NUM_SETUP = "s=0;q=0;c=0;b0=0;b1=0;b2=0;t1=-1;t2=-1;t3=-1;mn=999;mx=-1\n" \
            "N=(%s)" % " ".join(NUM_STRS)
for op, expr in NUM_OPS:
    add("num_%s" % op, "numeric op %s" % op, NUM_SETUP, expr)

# JSON-ish emit per iter (printf is the op under test).
add("emit_json", "printf json-line per iter",
    ARR_SETUP + "\nn=0",
    "l=${A[$((__bs_i%%%d))]}; printf '{\"i\":%%d,\"v\":\"%%s\"}\\n' "
    "$__bs_i \"$l\" >/dev/null" % NLINES, iters=N_SLOW)
add("emit_csv", "printf csv-row per iter",
    "",
    "printf '%d,field%d,3.14,item-%d,active,%d\\n' $__bs_i $__bs_i "
    "$__bs_i $((__bs_i%50)) >/dev/null", iters=N_SLOW)
add("emit_padded", "printf padded report row per iter",
    "",
    "printf '| %6d | %-12s | %8d |\\n' $__bs_i item$__bs_i "
    "$((__bs_i*7)) >/dev/null", iters=N_SLOW)

# ===========================================================================
# 5. FILENAME / GLOB BATCH TRANSFORMS (loop-kind micro)
# ===========================================================================

# Setup snapshots the glob once into an array; body does per-name surgery.
GLOB_SETUP = "shopt -s nullglob; G=(d*/* top*.log)"
GLOB_OPS = [
    ("basename", "f=${G[$((__bs_i%12))]}; b=${f##*/}; n=$((n+${#b}))"),
    ("dirname", "f=${G[$((__bs_i%12))]}; d=${f%/*}; n=$((n+${#d}))"),
    ("extfilter", "f=${G[$((__bs_i%12))]}; case $f in *.txt) "
                  "n=$((n+1));; *.log) t=$((t+1));; esac"),
    ("rename_var", "f=${G[$((__bs_i%12))]}; d=${f%/*}; b=${f##*/}; "
                  "x=${b%.txt}.out; n=$((n+${#d}+${#x}))"),
    ("fullpath", "f=${G[$((__bs_i%12))]}; n=$((n+${#f}))"),
    ("subdir", "f=${G[$((__bs_i%12))]}; d=${f%%/*}; n=$((n+${#d}))"),
]
for op, expr in GLOB_OPS:
    add("glob_%s" % op, "glob-name op %s" % op,
        GLOB_SETUP + "\nn=0;t=0", expr, files=GLOB_FILES)

# Per-iter glob expansion itself (small tree; glob cost is the op).
add("glob_expand_count", "per-iter glob d*/* count",
    "n=0", "for f in d*/*; do n=$((n+1)); done", files=GLOB_FILES)
add("glob_expand_basenames", "per-iter glob + basename",
    "n=0", "for f in d*/*; do b=${f##*/}; "
           "n=$((n+${#b})); done", files=GLOB_FILES)
add("glob_star_all", "per-iter glob * count",
    "n=0", "for f in *; do n=$((n+1)); done", files=GLOB_FILES)

# ===========================================================================
# 6. ESCAPE / BACKSLASH-AWARE SPLITS AND TRIMS
# ===========================================================================

ESC_SETUP = ARR_SETUP + "\nE=('a\\ b' 'c\\:d' 'plain' 'x\\ty' 'semi\\;colon' " \
            "'back\\\\slash' \"dq'q\")"
ESC_OPS = [
    ("bs_read", "IFS=: read -ra p <<<\"$l\"; n=$((n+${#p[@]}))"),
    ("bs_strip", "x=${l//\\\\/}; n=$((n+${#x}))"),
    ("bs_subst", "x=${l//\\ /_}; n=$((n+${#x}))"),
    ("bs_len", "n=$((n+${#l}))"),
]
for op, expr in ESC_OPS:
    add("esc_%s" % op, "backslash-aware op %s" % op,
        ESC_SETUP, "l=${E[$((__bs_i%%%d))]}; %s" % (7, expr))

# ===========================================================================
# 7. SCRIPT-KIND: end-to-end data-processing reports
# ===========================================================================
# iters = input size (lines/records processed) for ns/op derivation.

# --- line-processing ladders over @gen:lines ---
LINE_BODIES = [
    ("count", "n=0\nwhile IFS= read -r l; do n=$((n+1)); done < data.txt\n"
              "printf '%d\\n' \"$n\"\n"),
    ("len", "n=0\nwhile IFS= read -r l; do n=$((n+${#l})); done < data.txt\n"
            "printf '%d\\n' \"$n\"\n"),
    ("words", "w=0\nwhile IFS= read -r l; do set -- $l; "
             "w=$((w+$#)); done < data.txt\n"
             "printf '%d\\n' \"$w\"\n"),
    ("case_dispatch", "c=0;t=0\nwhile IFS= read -r l; do "
                     "case $l in line*) c=$((c+1));; "
                     "*lorem*) t=$((t+1));; esac; done < data.txt\n"
                     "printf '%d %d\\n' \"$c\" \"$t\"\n"),
    ("strip_prefix", "n=0\nwhile IFS= read -r l; do x=${l#line }; "
                    "n=$((n+${#x})); done < data.txt\n"
                    "printf '%d\\n' \"$n\"\n"),
    ("read_ra", "w=0\nwhile IFS= read -ra p; do "
                "w=$((w+${#p[@]})); done < data.txt\n"
                "printf '%d\\n' \"$w\"\n"),
]
for suffix, body in LINE_BODIES:
    for rung in (1000, 10000, 100000):
        sadd("script_lines_%s@%d" % (suffix, rung),
             "lines %s n=%d" % (suffix, rung), body, rung,
             files=sfile("data.txt", "@gen:lines:%d" % rung))

# --- kv / config-ish parse ---
KV_BODIES = [
    ("assoc", "declare -A h\nwhile IFS== read -r k v; do h[\"$k\"]=$v; "
              "done < kv.txt\nprintf '%d\\n' \"${#h[@]}\"\n"),
    ("count_fields", "c=0\nwhile IFS== read -r k v; do "
                     "c=$((c+${#k}+${#v})); done < kv.txt\n"
                     "printf '%d\\n' \"$c\"\n"),
    ("value_sum", "s=0\nwhile IFS== read -r k v; do s=$((s+v)); "
                 "done < kv.txt\nprintf '%d\\n' \"$s\"\n"),
]
for suffix, body in KV_BODIES:
    for rung in (1000, 10000, 100000):
        sadd("script_kv_%s@%d" % (suffix, rung),
             "kv %s n=%d" % (suffix, rung), body, rung,
             files=sfile("kv.txt", "@gen:kv:%d" % rung))

# --- csv aggregate ---
CSV_BODIES = [
    ("sum_col1", "s=0\nwhile IFS=, read -r a b c d e f; do "
                 "s=$((s+a)); done < data.csv\nprintf '%d\\n' \"$s\"\n"),
    ("count_active", "c=0\nwhile IFS=, read -r a b c d e f; do "
                    "[ \"$f\" -lt 25 ] && c=$((c+1)); done < data.csv\n"
                    "printf '%d\\n' \"$c\"\n"),
    ("fields_len", "t=0\nwhile IFS=, read -r a b c d e f; do "
                   "t=$((t+${#a}+${#b}+${#c}+${#d}+${#e}+${#f})); "
                   "done < data.csv\nprintf '%d\\n' \"$t\"\n"),
]
for suffix, body in CSV_BODIES:
    for rung in (1000, 10000):
        sadd("script_csv_%s@%d" % (suffix, rung),
             "csv %s n=%d" % (suffix, rung), body, rung,
             files=sfile("data.csv", "@gen:csv:%d" % rung))

# --- words file: wc-style passes ---
sadd("script_words_wc@10000", "words file wc-style (lines/words/chars)",
     "l=0;w=0;c=0\nwhile IFS= read -r line; do l=$((l+1)); "
     "set -- $line; w=$((w+$#)); for x in \"$@\"; do "
     "c=$((c+${#x}+1)); done; done < words.txt\n"
     "printf '%d %d %d\\n' \"$l\" \"$w\" \"$c\"\n", 10000,
     files=sfile("words.txt", "@gen:words:10000"))
sadd("script_words_wc@100000", "words file wc-style n=100000",
     "l=0;w=0\nwhile IFS= read -r line; do l=$((l+1)); "
     "set -- $line; w=$((w+$#)); done < words.txt\n"
     "printf '%d %d\\n' \"$l\" \"$w\"\n", 100000,
     files=sfile("words.txt", "@gen:words:100000"))

# --- path list transforms (@gen:path) ---
PATH_BODIES = [
    ("basename_len", "n=0\nwhile IFS= read -r p; do b=${p##*/}; "
                    "n=$((n+${#b})); done < paths.txt\n"
                    "printf '%d\\n' \"$n\"\n"),
    ("dirname_group", "declare -A g\nwhile IFS= read -r p; do "
                     "d=${p%/*}; g[\"$d\"]=$(( ${g[\"$d\"]:-0} + 1 )); "
                     "done < paths.txt\nprintf '%d\\n' \"${#g[@]}\"\n"),
    ("rename_var", "n=0\nwhile IFS= read -r p; do d=${p%/*}; "
                   "b=${p##*/}; x=${b%.txt}.md; "
                   "n=$((n+${#d}+${#x})); done < paths.txt\n"
                   "printf '%d\\n' \"$n\"\n"),
]
for suffix, body in PATH_BODIES:
    for rung in (1000, 10000):
        sadd("script_path_%s@%d" % (suffix, rung),
             "path %s n=%d" % (suffix, rung), body, rung,
             files=sfile("paths.txt", "@gen:path:%d" % rung))

# --- numeric file sum / stats ---
sadd("script_nums_sum@10000", "numeric file sum",
     "s=0\nwhile IFS= read -r x; do s=$((s+x)); done < nums.txt\n"
     "printf '%d\\n' \"$s\"\n", 10000,
     files=(("nums.txt", nums_file(10000)),))
sadd("script_nums_stats@10000", "numeric file min/max/sumsq",
     "s=0;q=0;mn=999999;mx=-1\nwhile IFS= read -r x; do "
     "s=$((s+x)); q=$((q+x*x)); ((x<mn)) && mn=$x; "
     "((x>mx)) && mx=$x; done < nums.txt\n"
     "printf '%d %d %d %d\\n' \"$s\" \"$q\" \"$mn\" \"$mx\"\n", 10000,
     files=(("nums.txt", nums_file(10000)),))

# --- config-ish: comments, sections, k=v, trim, prefix case ---
def cfg_content(n):
    out = []
    for i in range(n):
        m = i % 10
        if m == 0:
            out.append("# comment line %d" % i)
        elif m == 1:
            out.append("[section%d]" % (i % 5))
        elif m == 2:
            out.append("  spaced_key%d = value%d  " % (i, i))
        else:
            out.append("key%d=value%d" % (i, i * 3 % 997))
    return "\n".join(out) + "\n"


CFG_BODY = (
    "declare -A h; c=0; s=0\n"
    "while IFS= read -r l; do\n"
    "  x=${l%%#*}\n"
    "  case $x in ''|'['*) continue;; esac\n"
    "  IFS== read -r k v <<< \"$x\"\n"
    "  k=${k# }; k=${k% }; v=${v# }; v=${v% }\n"
    "  case $k in\n"
    "    spaced*) h[sp]=$(( ${h[sp]:-0} + 1 ));;\n"
    "    *) h[\"$k\"]=$v; c=$((c+1));;\n"
    "  esac\n"
    "done < cfg.txt\n"
    "printf '%d %d\\n' \"$c\" \"${#h[@]}\"\n")
for rung in (1000, 10000):
    sadd("script_cfg_parse@%d" % rung, "config-ish parse n=%d" % rung,
         CFG_BODY, rung,
         files=(("cfg.txt", cfg_content(rung)),))

# --- fixed-width records ---
def fixed_content(n):
    return "".join("%08d%-14s%8d\n" % (i, "name%d" % i, i * 3 % 997)
                   for i in range(n))


FW_BODY = (
    "s=0; c=0\n"
    "while IFS= read -r l; do\n"
    "  id=${l:0:8}; nm=${l:8:14}; amt=${l:22:8}\n"
    "  s=$((s+amt)); c=$((c+1))\n"
    "done < rec.txt\n"
    "printf '%d %d\\n' \"$s\" \"$c\"\n")
sadd("script_fixed_width@10000", "fixed-width field parse",
     FW_BODY, 10000, files=(("rec.txt", fixed_content(10000)),))

# --- line-number + length histogram ---
HIST_BODY = (
    "declare -A h; n=0\n"
    "while IFS= read -r l; do\n"
    "  n=$((n+1)); b=$(( ${#l} / 10 ))\n"
    "  h[\"$b\"]=$(( ${h[\"$b\"]:-0} + 1 ))\n"
    "done < data.txt\n"
    "printf '%d %d\\n' \"$n\" \"${#h[@]}\"\n")
for rung in (10000, 100000):
    sadd("script_len_hist@%d" % rung, "length histogram n=%d" % rung,
         HIST_BODY, rung,
         files=sfile("data.txt", "@gen:lines:%d" % rung))

# --- dedup-adjacent (transition count; input not sorted) ---
sadd("script_dedup_trans@100000", "adjacent-transition count",
     "prev=; d=0; n=0\n"
     "while IFS= read -r l; do\n"
     "  n=$((n+1))\n"
     "  [ \"$l\" != \"$prev\" ] && d=$((d+1))\n"
     "  prev=$l\n"
     "done < data.txt\n"
     "printf '%d %d\\n' \"$n\" \"$d\"\n", 100000,
     files=sfile("data.txt", "@gen:lines:100000"))

# --- prefix-group counts over words lines ---
sadd("script_prefix_group@10000", "first-word group counts",
     "declare -A g\nwhile IFS= read -r l; do\n"
     "  w=${l%% *}; g[\"$w\"]=$(( ${g[\"$w\"]:-0} + 1 ))\n"
     "done < words.txt\nprintf '%d\\n' \"${#g[@]}\"\n", 10000,
     files=sfile("words.txt", "@gen:words:10000"))

# --- top-3 tracking then sorted report ---
sadd("script_top3@100000", "top-3 values + sorted report",
     "t1=-1; t2=-1; t3=-1\n"
     "while IFS= read -r x; do\n"
     "  v=$((x % 100))\n"
     "  if ((v>t1)); then t3=$t2; t2=$t1; t1=$v;\n"
     "  elif ((v>t2)); then t3=$t2; t2=$v;\n"
     "  elif ((v>t3)); then t3=$v; fi\n"
     "done < nums.txt\n"
     "printf '%d %d %d\\n' \"$t1\" \"$t2\" \"$t3\"\n", 100000,
     files=(("nums.txt", nums_file(100000)),))

# --- running stats report ---
sadd("script_stats@100000", "sum/sumsq/min/max report",
     "s=0;q=0;mn=999999;mx=-1\n"
     "while IFS= read -r x; do\n"
     "  s=$((s+x)); q=$((q+x*x))\n"
     "  ((x<mn)) && mn=$x; ((x>mx)) && mx=$x\n"
     "done < nums.txt\n"
     "printf 'sum=%d sumsq=%d min=%d max=%d\\n' \"$s\" \"$q\" "
     "\"$mn\" \"$mx\"\n", 100000,
     files=(("nums.txt", nums_file(100000)),))

# --- JSON-lines emit (realistic transform-to-output shape) ---
sadd("script_json_emit_devnull@10000",
     "json-line emit to /dev/null",
     "while IFS= read -r l; do\n"
     "  printf '{\"line\":\"%s\",\"len\":%d}\\n' \"$l\" \"${#l}\"\n"
     "done < data.txt > /dev/null\n", 10000,
     files=sfile("data.txt", "@gen:lines:10000"))

# --- multi-pass: count then transform ---
sadd("script_multipass@10000", "two passes: count then transform",
     "n=0\nwhile IFS= read -r l; do n=$((n+1)); done < data.txt\n"
     "t=0\nwhile IFS= read -r l; do t=$((t+${#l})); done < data.txt\n"
     "printf '%d %d\\n' \"$n\" \"$t\"\n", 10000,
     files=sfile("data.txt", "@gen:lines:10000"))

# --- state machine over alternating line shapes ---
sadd("script_state_machine@10000", "two-state machine over kv lines",
     "state=0; kv=0; other=0\n"
     "while IFS= read -r l; do\n"
     "  case $state in\n"
     "    0) case $l in key*=*) state=1; kv=$((kv+1));; "
     "       *) other=$((other+1));; esac;;\n"
     "    1) case $l in key*=*) kv=$((kv+1));; "
     "       *) state=0; other=$((other+1));; esac;;\n"
     "  esac\n"
     "done < kv.txt\nprintf '%d %d\\n' \"$kv\" \"$other\"\n", 10000,
     files=sfile("kv.txt", "@gen:kv:10000"))

# --- mapfile + indexed processing script ---
sadd("script_mapfile_report@100000", "mapfile then indexed stats",
     "mapfile -t a < data.txt\nn=${#a[@]}; s=0; mn=999999; mx=-1\n"
     "i=0\nwhile ((i<n)); do\n"
     "  l=${a[i]}; s=$((s+${#l}))\n"
     "  (( ${#l} < mn )) && mn=${#l}\n"
     "  (( ${#l} > mx )) && mx=${#l}\n"
     "  i=$((i+1))\n"
     "done\nprintf '%d %d %d %d\\n' \"$n\" \"$s\" \"$mn\" \"$mx\"\n",
     100000, files=sfile("data.txt", "@gen:lines:100000"))

# --- escape-aware split script ---
ESC_FILE = "".join("field%d\\,with%d\\;escapes%d\n" % (i, i, i)
                    for i in range(5000))
sadd("script_escape_split@5000", "backslash-aware field split",
     "n=0; t=0\n"
     "while IFS= read -r l; do\n"
     "  x=${l//\\,/|}\n"
     "  IFS='|' read -ra p <<< \"$x\"\n"
     "  t=$((t+${#p[@]})); n=$((n+1))\n"
     "done < esc.txt\nprintf '%d %d\\n' \"$n\" \"$t\"\n", 5000,
     files=(("esc.txt", ESC_FILE),))

# --- assoc frequency + top report ---
sadd("script_freq_top@10000", "word frequency + top-5 report",
     "declare -A f\nwhile IFS= read -r l; do\n"
     "  for w in $l; do f[\"$w\"]=$(( ${f[\"$w\"]:-0} + 1 )); done\n"
     "done < words.txt\nprintf '%d\\n' \"${#f[@]}\"\n", 10000,
     files=sfile("words.txt", "@gen:words:10000"))

# --- cut-by-position script on kv values ---
sadd("script_cut_pos@10000", "substring extract + accumulate",
     "n=0\nwhile IFS== read -r k v; do\n"
     "  a=${v:0:4}; b=${v:4:4}; n=$((n+${#a}+${#b}))\n"
     "done < kv.txt\nprintf '%d\\n' \"$n\"\n", 10000,
     files=sfile("kv.txt", "@gen:kv:10000"))

# --- csv stats / field lengths (extend ladder to 100k) ---
sadd("script_csv_stats@10000", "csv col1 min/max/sum",
     "s=0;mn=999999999;mx=-1\nwhile IFS=, read -r a b c d e f; do\n"
     "  s=$((s+a)); ((a<mn)) && mn=$a; ((a>mx)) && mx=$a\n"
     "done < data.csv\nprintf '%d %d %d\\n' \"$s\" \"$mn\" \"$mx\"\n",
     10000, files=sfile("data.csv", "@gen:csv:10000"))
sadd("script_csv_stats@100000", "csv col1 min/max/sum n=100000",
     "s=0;mn=999999999;mx=-1\nwhile IFS=, read -r a b c d e f; do\n"
     "  s=$((s+a)); ((a<mn)) && mn=$a; ((a>mx)) && mx=$a\n"
     "done < data.csv\nprintf '%d %d %d\\n' \"$s\" \"$mn\" \"$mx\"\n",
     100000, files=sfile("data.csv", "@gen:csv:100000"))
sadd("script_csv_fieldlens@10000", "csv per-column char totals",
     "t=0\nwhile IFS=, read -r a b c d e f; do\n"
     "  t=$((t+${#a}+${#b}+${#c}+${#d}+${#e}+${#f}))\n"
     "done < data.csv\nprintf '%d\\n' \"$t\"\n", 10000,
     files=sfile("data.csv", "@gen:csv:10000"))

# --- assoc-join lookup: build map from kv, probe with pairs file ---
PAIRS = "".join("key%d %d\n" % ((i * 7) % 10000, i % 50)
                for i in range(20000))
sadd("script_join_lookup@20000", "kv assoc build + pair lookup sum",
     "declare -A h\nwhile IFS== read -r k v; do h[\"$k\"]=$v; "
     "done < kv.txt\ns=0;miss=0\nwhile read -r k x; do\n"
     "  if [ -n \"${h[$k]+x}\" ]; then s=$((s+${h[$k]})); "
     "  else miss=$((miss+1)); fi\ndone < pairs.txt\n"
     "printf '%d %d\\n' \"$s\" \"$miss\"\n", 20000,
     files=(("kv.txt", "@gen:kv:10000"), ("pairs.txt", PAIRS)))

# --- duplicate detection via assoc (whole-file, not just adjacent) ---
sadd("script_dup_assoc@10000", "dup first-word count via assoc",
     "declare -A seen; dup=0; total=0\n"
     "while IFS= read -r l; do\n"
     "  w=${l%% *}; total=$((total+1))\n"
     "  if [ -n \"${seen[$w]+x}\" ]; then dup=$((dup+1)); "
     "  else seen[\"$w\"]=1; fi\n"
     "done < words.txt\nprintf '%d %d\\n' \"$total\" \"$dup\"\n", 10000,
     files=sfile("words.txt", "@gen:words:10000"))

# --- ini-ish section tracking on the cfg fixture ---
sadd("script_ini_sections@10000", "ini section key counts",
     "declare -A sc; sec=; ks=0\n"
     "while IFS= read -r l; do\n"
     "  x=${l%%#*}\n"
     "  case $x in\n"
     "    \\[*\\]) sec=${x#\\[}; sec=${sec%\\]};;\n"
     "    *=*) [ -n \"$sec\" ] && { sc[\"$sec\"]=$(( ${sc[$sec]:-0} + 1 )); ks=$((ks+1)); };;\n"
     "  esac\n"
     "done < cfg.txt\nprintf '%d %d\\n' \"$ks\" \"${#sc[@]}\"\n", 10000,
     files=(("cfg.txt", cfg_content(10000)),))

# --- CRLF handling ---
CRLF = "".join("rec %d payload %d\r\n" % (i, i * 3 % 97)
               for i in range(10000))
sadd("script_crlf_strip@10000", "CRLF strip + field parse",
     "n=0;s=0\nwhile IFS= read -r l; do\n"
     "  l=${l%$'\\r'}; set -- $l; s=$((s+$#)); n=$((n+1))\n"
     "done < crlf.txt\nprintf '%d %d\\n' \"$n\" \"$s\"\n", 10000,
     files=(("crlf.txt", CRLF),))

# --- tab-separated parse ---
TSV = "".join("f%d\tval%d\t%d\n" % (i, i, i * 7 % 991)
              for i in range(10000))
sadd("script_tsv_parse@10000", "tab-separated field sum",
     "s=0\nwhile IFS=$'\\t' read -r a b c; do s=$((s+c)); "
     "done < data.tsv\nprintf '%d\\n' \"$s\"\n", 10000,
     files=(("data.tsv", TSV),))

# --- top-5 via repeated max-scan + unset (bounded small assoc) ---
sadd("script_top5_scan@10000", "top-5 keys by freq via rescan",
     "declare -A f\nwhile IFS= read -r l; do\n"
     "  for w in $l; do f[\"$w\"]=$(( ${f[$w]:-0} + 1 )); done\n"
     "done < words.txt\n"
     "i=0\nwhile ((i<5)); do\n"
     "  mk=; mv=-1\n"
     "  for k in \"${!f[@]}\"; do (( ${f[$k]} > mv )) && { mv=${f[$k]}; mk=$k; }; done\n"
     "  [ -n \"$mk\" ] && unset 'f[$mk]'\n"
     "  i=$((i+1))\n"
     "done\nprintf '%d\\n' \"${#f[@]}\"\n", 10000,
     files=sfile("words.txt", "@gen:words:10000"))

# --- collatz step counter over numeric file ---
sadd("script_collatz@2000", "collatz total steps over nums",
     "tot=0\nwhile IFS= read -r x; do\n"
     "  v=$x; ((v<1)) && v=1; steps=0\n"
     "  while ((v!=1)); do if ((v%2)); then v=$((v*3+1)); "
     "  else v=$((v/2)); fi; steps=$((steps+1)); done\n"
     "  tot=$((tot+steps))\n"
     "done < nums.txt\nprintf '%d\\n' \"$tot\"\n", 2000,
     files=(("nums.txt", nums_file(2000)),))

# --- trial-division prime count ---
sadd("script_primes@2000", "prime count via trial division",
     "pc=0\nwhile IFS= read -r x; do\n"
     "  v=$x; isp=1; d=2\n"
     "  while ((d*d<=v)); do if ((v%d==0)); then isp=0; "
     "  break; fi; d=$((d+1)); done\n"
     "  ((isp)) && pc=$((pc+1))\n"
     "done < nums.txt\nprintf '%d\\n' \"$pc\"\n", 2000,
     files=(("nums.txt", nums_file(2000)),))

# --- multi-delimiter field surgery ---
MULTI = "".join("a%d,b%d;c%d|d%d\n" % (i, i, i, i) for i in range(10000))
sadd("script_multi_delim@10000", "mixed-delimiter field extract",
     "s=0\nwhile IFS= read -r l; do\n"
     "  a=${l%%,*}; r1=${l#*,}; b=${r1%%;*}; r2=${r1#*;}\n"
     "  c=${r2%%|*}; d=${r2#*|}; s=$((s+${#a}+${#b}+${#c}+${#d}))\n"
     "done < multi.txt\nprintf '%d\\n' \"$s\"\n", 10000,
     files=(("multi.txt", MULTI),))

# --- sortedness / run stats on numeric file ---
sadd("script_runs@100000", "ascending-run count on nums",
     "prev=-1; runs=0; asc=0\n"
     "while IFS= read -r x; do\n"
     "  ((x>prev)) && asc=$((asc+1))\n"
     "  ((x<prev)) && runs=$((runs+1))\n"
     "  prev=$x\n"
     "done < nums.txt\nprintf '%d %d\\n' \"$asc\" \"$runs\"\n", 100000,
     files=(("nums.txt", nums_file(100000)),))

# --- squeeze repeated whitespace via extglob ---
sadd("script_squeeze@10000", "squeeze spaces + tokenize",
     "shopt -s extglob\nw=0\nwhile IFS= read -r l; do\n"
     "  x=${l//+( )/ }\n"
     "  set -- $x; w=$((w+$#))\n"
     "done < words.txt\nprintf '%d\\n' \"$w\"\n", 10000,
     setup="shopt -s extglob",
     files=sfile("words.txt", "@gen:words:10000"))

# --- per-word length histogram ---
sadd("script_wordlen_hist@10000", "word-length histogram",
     "declare -A h\nwhile IFS= read -r l; do\n"
     "  for w in $l; do b=${#w}; h[\"$b\"]=$(( ${h[$b]:-0} + 1 )); done\n"
     "done < words.txt\nprintf '%d\\n' \"${#h[@]}\"\n", 10000,
     files=sfile("words.txt", "@gen:words:10000"))

# --- hex/octal literal arithmetic parse ---
MIXED_NUM = "".join("%s %s %s\n" % ("0x%x" % i, "0%o" % (i % 64),
                                   str(i % 100)) for i in range(10000))
sadd("script_radix_parse@10000", "0x/0oct/dec arithmetic sum",
     "s=0\nwhile read -r a b c; do s=$((s+a+b+c)); "
     "done < nums.txt\nprintf '%d\\n' \"$s\"\n", 10000,
     files=(("nums.txt", MIXED_NUM),))

# --- glob-tree transform script ---
sadd("script_glob_tree@1000", "glob tree basename/ext report",
     "n=0; t=0\nfor f in d*/* top*.log; do\n"
     "  b=${f##*/}; case $b in *.txt) n=$((n+1));; "
     "  *.log) t=$((t+1));; esac\ndone\nprintf '%d %d\\n' \"$n\" \"$t\"\n", 1000,
     files=GLOB_FILES)

# --- backslash counting ---
sadd("script_backslash_count@5000", "backslash/escape census",
     "bs=0; lines=0\nwhile IFS= read -r l; do\n"
     "  lines=$((lines+1))\n"
     "  t=${l//[^\\]/}; bs=$((bs+${#t}))\n"
     "done < esc.txt\nprintf '%d %d\\n' \"$lines\" \"$bs\"\n", 5000,
     files=(("esc.txt", ESC_FILE),))

# --- report table from computed stats (no input file) ---
sadd("script_report_table@2000", "formatted report table",
     "for ((j=0; j<2000; j++)); do\n"
     "  printf '| %-14s | %8d | %6d | %5d |\\n' "
     "region$j $((j*13%997)) $((j*7%89)) $((j%17))\n"
     "done > report.txt\nprintf 'done\\n'\n", 2000)

# --- numeric validation gate ---
sadd("script_num_gate@10000", "skip non-numeric lines",
     "ok=0; bad=0\nwhile IFS= read -r l; do\n"
     "  case $l in ''|*[!0-9]*) bad=$((bad+1));; *) ok=$((ok+1));; esac\n"
     "done < nums.txt\nprintf '%d %d\\n' \"$ok\" \"$bad\"\n", 10000,
     files=(("nums.txt", nums_file(10000)),))

# --- assoc fill then emit per-key report rows ---
sadd("script_assoc_report@10000", "kv assoc + per-key report emit",
     "declare -A h\nwhile IFS== read -r k v; do h[\"$k\"]=$v; "
     "done < kv.txt\nfor k in \"${!h[@]}\"; do\n"
     "  printf 'key=%s value=%s\\n' \"$k\" \"${h[$k]}\"\n"
     "done > /dev/null\nprintf '%d\\n' \"${#h[@]}\"\n", 10000,
     files=sfile("kv.txt", "@gen:kv:10000"))

# --- avg / stdev-ish report over numeric file ---
sadd("script_avg_stdev@100000", "sum/sumsq -> avg report",
     "s=0;q=0\nwhile IFS= read -r x; do s=$((s+x)); "
     "q=$((q+x*x)); done < nums.txt\n"
     "printf 'sum=%d sumsq=%d\\n' \"$s\" \"$q\"\n", 100000,
     files=(("nums.txt", nums_file(100000)),))

# --- kv value last-digit buckets ---
sadd("script_kv_bucket@10000", "kv value mod-10 bucket counts",
     "declare -A b\nwhile IFS== read -r k v; do\n"
     "  d=$((v%10)); b[\"$d\"]=$(( ${b[$d]:-0} + 1 ))\n"
     "done < kv.txt\nprintf '%d\\n' \"${#b[@]}\"\n", 10000,
     files=sfile("kv.txt", "@gen:kv:10000"))

# --- csv per-column length counters ---
sadd("script_csv_cols@10000", "csv per-column char totals",
     "c1=0;c2=0;c3=0;c4=0;c5=0;c6=0\n"
     "while IFS=, read -r a b c d e f; do\n"
     "  c1=$((c1+${#a})); c2=$((c2+${#b})); c3=$((c3+${#c}));\n"
     "  c4=$((c4+${#d})); c5=$((c5+${#e})); c6=$((c6+${#f}))\n"
     "done < data.csv\nprintf '%d\\n' \"$((c1+c2+c3+c4+c5+c6))\"\n",
     10000, files=sfile("data.csv", "@gen:csv:10000"))

# --- path depth histogram ---
sadd("script_path_depth@10000", "path slash-depth histogram",
     "declare -A h\nwhile IFS= read -r p; do\n"
     "  o=${p//\\//}; d=$(( ${#p} - ${#o} ))\n"
     "  h[\"$d\"]=$(( ${h[$d]:-0} + 1 ))\n"
     "done < paths.txt\nprintf '%d\\n' \"${#h[@]}\"\n", 10000,
     files=sfile("paths.txt", "@gen:path:10000"))

# --- bigram (word-pair) frequency ---
sadd("script_bigrams@10000", "adjacent word-pair frequency",
     "declare -A h; prev=\nwhile IFS= read -r l; do\n"
     "  for w in $l; do [ -n \"$prev\" ] && "
     "  h[\"$prev $w\"]=$(( ${h[\"$prev $w\"]:-0} + 1 )); prev=$w; done\n"
     "done < words.txt\nprintf '%d\\n' \"${#h[@]}\"\n", 10000,
     files=sfile("words.txt", "@gen:words:10000"))

# --- key-prefix routing counters ---
sadd("script_prefix_route@10000", "kv key-prefix route counters",
     "declare -A r\nwhile IFS== read -r k v; do\n"
     "  case $k in key*) r[k]=$(( ${r[k]:-0} + 1 ));; "
     "  *) r[other]=$(( ${r[other]:-0} + 1 ));; esac\n"
     "done < kv.txt\nprintf '%d\\n' \"${#r[@]}\"\n", 10000,
     files=sfile("kv.txt", "@gen:kv:10000"))

# --- escape-then-emit json-ish ---
sadd("script_escape_emit@5000", "escape backslashes/quotes + emit",
     "while IFS= read -r l; do\n"
     "  x=${l//\\\\/}; x=${x//\\\"/};\n"
     "  printf '{\"v\":\"%s\"}\\n' \"$x\"\n"
     "done < esc.txt > /dev/null\nprintf 'ok\\n'\n", 5000,
     files=(("esc.txt", ESC_FILE),))

# --- generated report file (bounded) ---
sadd("script_report_file@5000", "write 5k report rows to file",
     "for ((j=0; j<5000; j++)); do\n"
     "  printf '%s\\t%d\\t%.1f\\n' item$j $((j*11%997)) 1.5\n"
     "done > report.tsv\nn=0\nwhile IFS= read -r l; do "
     "n=$((n+1)); done < report.tsv\nprintf '%d\\n' \"$n\"\n", 5000)

# --- fixed-width variant: name + amount columns ---
def fixed2_content(n):
    return "".join("%-12s%10.2f%6d\n" % ("item%d" % i, i * 1.5,
                                        i % 100) for i in range(n))
sadd("script_fixed_width2@5000", "fixed-width name/amount parse",
     "s=0\nwhile IFS= read -r l; do\n"
     "  nm=${l:0:12}; amt=${l:12:10}; q=${l:22:6}\n"
     "  case $amt in *.*) a=${amt%%.*};; *) a=$amt;; esac\n"
     "  s=$((s+a+q))\n"
     "done < rec.txt\nprintf '%d\\n' \"$s\"\n", 5000,
     files=(("rec.txt", fixed2_content(5000)),))

# --- line-length mod-7 buckets ---
sadd("script_len_deciles@100000", "length mod-7 bucket counts",
     "declare -A h\nwhile IFS= read -r l; do\n"
     "  b=$(( ${#l} % 7 )); h[\"$b\"]=$(( ${h[$b]:-0} + 1 ))\n"
     "done < data.txt\nprintf '%d\\n' \"${#h[@]}\"\n", 100000,
     files=sfile("data.txt", "@gen:lines:100000"))

# --- count lines matching several glob classes ---
sadd("script_glob_classes@10000", "multi-class line census",
     "a=0;b=0;c=0;d=0\nwhile IFS= read -r l; do\n"
     "  case $l in\n"
     "    line*) a=$((a+1));;\n"
     "    *lorem*) b=$((b+1));;\n"
     "    *[0-9]*) c=$((c+1));;\n"
     "    *) d=$((d+1));;\n"
     "  esac\n"
     "done < data.txt\nprintf '%d\\n' \"$((a+b+c+d))\"\n", 10000,
     files=sfile("data.txt", "@gen:lines:10000"))

# ===========================================================================
# 8. EXTRA LOOP-KIND FAMILIES (path/kv sources, more ops)
# ===========================================================================

# First-char case transforms and misc ops appended to the generic stream.
ARR_OPS2 = [
    ("first_up", "x=${l^}; n=$((n+${#x}))"),
    ("first_low", "x=${l,}; n=$((n+${#x}))"),
    ("atK", "k2=${l@K}; n=$((n+${#k2}))"),
    ("atL", "x2=${l@L}; n=$((n+${#x2}))"),
    ("substr1", "x=${l:1}; n=$((n+${#x}))"),
    ("lastch", "x=${l: -1}; n=$((n+${#x}))"),
    ("len_times", "n=$((n+${#l}*3))"),
    ("hash_pos", "x=${l%%#*}; y=${l#*#}; n=$((n+${#x}+${#y}))"),
    ("csv_pos", "x=${l:0:3}; y=${l:3:3}; z=${l:6:3}; "
               "n=$((n+${#x}+${#y}+${#z}))"),
    ("tolower_cmp", "[[ ${l,,} == *key* ]] && n=$((n+1))"),
    ("dflt", "x=${l:-zz}; n=$((n+${#x}))"),
    ("dflt_alt", "x=${u:-$l}; n=$((n+${#x}))"),
    ("arr_push", "p+=(\"$l\"); n=${#p[@]}"),
    ("assoc_keys", "f[\"$l\"]=x; n=${#f[@]}"),
    ("read_ifs_space", "read -r a b <<<\"$l\"; n=$((n+${#a}+${#b}))"),
    ("ifs_colon_2", "IFS=: read -r a b <<<\"$l\"; "
                   "n=$((n+${#a}+${#b}))"),
]
for op, expr in ARR_OPS2:
    add("arrx_%s" % op, "line-op x %s" % op,
        ARR_SETUP + "\np=()", "l=${A[$((__bs_i%%%d))]}; %s" % (NLINES, expr))

# Path-shaped record stream.
PATH_STRS = [
    "dir1/sub2/file_3.txt", "a/b/c/d/e.log", "x.txt",
    "deep/nested/path/name.dat", "top.md", "p/q/r/s/t/u/v.csv",
    "./rel/path.f", "abs/like/unix/path", "one/two", "file",
    "d//double/slash", "name.with.dots.txt",
]
NPS = len(PATH_STRS)
P_SETUP = ("n=0;t=0;w=0;s=0\nP=(%s)"
           % " ".join("'%s'" % p for p in PATH_STRS))
P_OPS = [
    ("pbase", "b=${l##*/}; n=$((n+${#b}))"),
    ("pdir", "d=${l%/*}; n=$((n+${#d}))"),
    ("pdirbase", "d=${l%/*}; b=${d##*/}; n=$((n+${#b}))"),
    ("pext_case", "case $l in *.txt) n=$((n+1));; *.log) "
                 "t=$((t+1));; *.csv|*.dat) w=$((w+1));; esac"),
    ("prename", "b=${l##*/}; x=${b%.*}.out; d=${l%/*}; "
               "n=$((n+${#d}+${#x}))"),
    ("pdepth", "o=${l//\\//}; n=$(( ${#l} - ${#o} ))"),
    ("pfirst", "x=${l%%/*}; n=$((n+${#x}))"),
    ("plast", "x=${l##*/}; y=${x%.*}; n=$((n+${#y}))"),
    ("pnorm", "case $l in /*) n=$((n+1));; */*) t=$((t+1));; "
             "*) w=$((w+1));; esac"),
    ("pdot", "case ${l##*/} in *.*) n=$((n+1));; *) "
            "t=$((t+1));; esac"),
    ("pjoin", "d=${l%/*}; b=${l##*/}; x=$d/$b; n=$((n+${#x}))"),
    ("pstrip_rel", "x=${l#./}; n=$((n+${#x}))"),
    ("pupper_ext", "b=${l##*/}; e=${b##*.}; u=${e^^}; "
                  "n=$((n+${#u}))"),
    ("psub_ext", "b=${l##*/}; case $b in *.*) x=${b%.*}.bak;; "
                "*) x=$b;; esac; n=$((n+${#x}))"),
    ("pcolon", "IFS=: read -ra p <<<\"$l\"; n=$((n+${#p[@]}))"),
    ("psplit_set", "set -- $l; n=$((n+$#))"),
]
for op, expr in P_OPS:
    add("parr_%s" % op, "path-op %s" % op, P_SETUP,
        "l=${P[$((__bs_i%%%d))]}; %s" % (NPS, expr))

# kv-shaped record stream.
KV_STRS = [
    "alpha=1", "beta=22", "gamma=333", "k=", "longkey=longvalue",
    "n=100", "port=8080", "path=/tmp/x", "flag=", "mix=A=B=C",
    "num=007", "emptyv=x",
]
NKV = len(KV_STRS)
K_SETUP = ("n=0;t=0;s=0\nK=(%s)"
           % " ".join("'%s'" % k.replace("'", "'\\''") for k in KV_STRS))
K_OPS = [
    ("kv_ifs", "IFS== read -r k v <<<\"$l\"; n=$((n+${#k}+${#v}))"),
    ("kv_pat", "k=${l%%=*}; v=${l#*=}; n=$((n+${#k}+${#v}))"),
    ("kv_first", "k=${l%%=*}; n=$((n+${#k}))"),
    ("kv_rest", "v=${l#*=}; n=$((n+${#v}))"),
    ("kv_numval", "v=${l#*=}; case $v in ''|*[!0-9]*) "
                 "t=$((t+1));; *) n=$((n+1));; esac"),
    ("kv_keycase", "k=${l%%=*}; case $k in [a-z]*) "
                  "n=$((n+1));; esac"),
    ("kv_len_prod", "k=${l%%=*}; v=${l#*=}; "
                    "s=$((s+${#k}*${#v}))"),
    ("kv_has_eq", "case $l in *=*) n=$((n+1));; esac"),
    ("kv_no_val", "v=${l#*=}; [ -z \"$v\" ] && n=$((n+1))"),
    ("kv_swap", "k=${l%%=*}; v=${l#*=}; x=$v=$k; "
               "n=$((n+${#x}))"),
    ("kv_prefix3", "k=${l%%=*}; x=${k:0:3}; "
                  "case $x in alp|bet|gam) n=$((n+1));; esac"),
]
for op, expr in K_OPS:
    add("kvarr_%s" % op, "kv-op %s" % op, K_SETUP,
        "l=${K[$((__bs_i%%%d))]}; %s" % (NKV, expr))

# More numeric shapes.
NUM_OPS2 = [
    ("bitops", "v=${N[$((__bs_i%16))]}; "
              "v=$(( (v&15)|(v^3) )); s=$((s+v))"),
    ("cmp_count", "((__bs_i%4==1)) && n=$((n+1))"),
    ("shift", "v=$((1 << (__bs_i%12))); s=$((s+v))"),
    ("divmod", "v=$((__bs_i%97)); a=$((v/10)); b=$((v%10)); "
              "s=$((s+a+b))"),
    ("abs_diff", "v=$((__bs_i%50)); d=$((v-__bs_i%30)); "
                "((d<0)) && d=$((-d)); s=$((s+d))"),
    ("fib_inner", "a=0;b=1;k=0;while((k<10));do "
                  "t=$((a+b));a=$((b));b=$((t));k=$((k+1));done; "
                  "s=$((s+b))"),
    ("collatz", "v=$((__bs_i%100+2)); steps=0; "
               "while((v!=1));do if((v%2));then v=$((v*3+1)); "
               "else v=$((v/2));fi; steps=$((steps+1));done; "
               "s=$((s+steps))"),
    ("prime", "v=$((__bs_i%100+2)); isp=1; d=2; "
             "while((d*d<=v));do if((v%d==0));then isp=0; "
             "break;fi; d=$((d+1));done; s=$((s+isp))"),
    ("hist10", "d=$((__bs_i%10)); case $d in 0|1) b0=$((b0+1));; "
              "2|3|4) b1=$((b1+1));; 5|6|7) b2=$((b2+1));; "
              "*) b3=$((b3+1));; esac"),
]
NUM_SETUP2 = NUM_SETUP + ";b3=0;n=0"
for op, expr in NUM_OPS2:
    add("numx_%s" % op, "numeric op x %s" % op, NUM_SETUP2, expr)

# printf -v assignment forms (no external spawn, no redirect).
add("emit_v_simple", "printf -v scalar assign",
    "", "printf -v x 'r%d' $__bs_i; n=${#x}", iters=N)
add("emit_v_padded", "printf -v padded assign",
    "", "printf -v x '[%5d]' $__bs_i; n=${#x}", iters=N)
add("emit_v_join", "printf -v two-field assign",
    ARR_SETUP + "\nn=0",
    "l=${A[$((__bs_i%%%d))]}; printf -v x '%%s|%%d' \"$l\" "
    "$__bs_i; n=$((n+${#x}))" % NLINES, iters=N)

# More per-iter read shapes (reopen fd0 on tiny fixtures).
add("read_n1_char", "reopen fd0 read -n 1 char",
    "", "IFS= read -r -n 1 c < data.txt", files=F_LINES8)
add("read_n4_chars", "reopen fd0 read -N 4 chars",
    "", "IFS= read -r -N 4 c < data.txt", files=F_LINES8)
add("read_3var", "reopen fd0 read 3 vars default IFS",
    "n=0", "read -r a b c < data.txt; n=$((n+${#a}+${#b}+${#c}))",
    files=F_LINES8)
add("read_csv_ra", "reopen fd0 IFS=, read -ra",
    "n=0", "IFS=, read -ra p < data.csv; n=$((n+${#p[@]}))",
    files=F_CSV8)
add("read_kv_colon", "reopen fd0 IFS=: read -ra on paths",
    "n=0", "IFS=: read -ra p < paths.txt; n=$((n+${#p[@]}))",
    files=F_PATH8)

# mapfile -d delimiter variant + negative-index probe.
add("mapfile_d_comma", "mapfile -d , index loop",
    "mapfile -d ',' -t MA < data.csv\nn=0",
    "v=${MA[$((__bs_i%${#MA[@]}))]}; n=$((n+${#v}))",
    files=sfile("data.csv", "@gen:csv:1000"))
add("mapfile_negidx", "mapfile negative-index probe",
    "mapfile -t MA < data.txt\nn=0",
    "l=${MA[-1]}; x=${MA[-$((__bs_i%10+1))]}; "
    "n=$((n+${#l}+${#x}))", files=F_LINES10K)

# More glob shapes.
add("glob_compgen", "per-iter compgen -G + array count",
    "n=0", "m=($(compgen -G 'd*/*')); n=${#m[@]}", files=GLOB_FILES)
add("glob_nomatch", "per-iter unmatched glob literal",
    "n=0", "for f in zzz*; do n=$((n+1)); done", files=GLOB_FILES)
add("glob_case_ext", "per-iter glob + ext case",
    "n=0;t=0", "for f in d*/*; do case $f in *.txt) "
                "n=$((n+1));; esac; done", files=GLOB_FILES)
add("glob_nested", "per-iter glob + basename surgery",
    "n=0", "for f in d*/*; do b=${f##*/}; x=${b%.txt}; "
           "n=$((n+${#x})); done", files=GLOB_FILES)

# Three-op compounds.
COMPOUND3 = [
    ("c3_len_cut_case", "x=${l:0:8}; case $l in key*) "
                       "n=$((n+1));; esac; n=$((n+${#x}))"),
    ("c3_split_stats", "IFS=: read -ra p <<<\"$l\"; s2=0; "
                       "for x in \"${p[@]}\"; do s2=$((s2+${#x})); "
                       "done; n=$((n+s2))"),
    ("c3_strip_sub_up", "x=${l##* }; y=${x%%#*}; u=${y^^}; "
                        "n=$((n+${#u}))"),
    ("c3_trim_fields", "x=${l# }; y=${x% }; set -- $y; "
                       "n=$((n+$#))"),
    ("c3_ext_rename", "b=${l##*/}; case $b in *.txt) "
                     "x=${b%.txt}.out;; *) x=$b;; esac; "
                     "n=$((n+${#x}))"),
    ("c3_prev_eq", "[[ $l == \"$prev\" ]] && n=$((n+1)); "
                  "prev=$l; n=$((n+${#l}))"),
]
for op, expr in COMPOUND3:
    add("comp3_%s" % op, "triple line-op %s" % op,
        ARR_SETUP, "l=${A[$((__bs_i%%%d))]}; %s" % (NLINES, expr))

# --- 9. TOP-UP: a few more shapes for corpus density ---
ARR_OPS3 = [
    ("strlen_cmp", "[[ ${#l} -gt 20 ]] && n=$((n+1))"),
    ("regex_alpha", "[[ $l =~ ^[a-z] ]] && n=$((n+1))"),
    ("regex_num", "[[ $l =~ ^[0-9] ]] && t=$((t+1))"),
    ("ifs_colon_3", "IFS=: read -r a b c <<<\"$l\"; "
                    "n=$((n+${#a}+${#b}+${#c}))"),
    ("glob_in_case2", "case $l in *.*) n=$((n+1));; "
                     "*/*) t=$((t+1));; *) w=$((w+1));; esac"),
    ("param_t", "x=${l%.*}; y=${l##*.}; n=$((n+${#x}+${#y}))"),
    ("swap_fields", "set -- $l; x=\"$2 $1\"; n=$((n+${#x}))"),
    ("hashcount", "t=${l//[^#]/}; n=$((n+${#t}))"),
]
for op, expr in ARR_OPS3:
    add("arry_%s" % op, "line-op y %s" % op,
        ARR_SETUP, "l=${A[$((__bs_i%%%d))]}; %s" % (NLINES, expr))

NUM_OPS3 = [
    ("is_even", "v=$((__bs_i%50)); ((v%2==0)) && n=$((n+1))"),
    ("clamp50", "v=$((__bs_i%97)); ((v>50)) && v=50; s=$((s+v))"),
    ("running_min", "v=$((__bs_i%89)); ((v<mn)) && mn=$v"),
    ("parity_hist", "v=$((__bs_i%6)); case $v in 0|2|4) "
                    "b0=$((b0+1));; *) b1=$((b1+1));; esac"),
]
NUM_SETUP3 = NUM_SETUP + ";b1=0;n=0"
for op, expr in NUM_OPS3:
    add("numy_%s" % op, "numeric op y %s" % op, NUM_SETUP3, expr)

add("read_heredoc_var", "herestring var read per iter",
    "v=line", "read -r l <<<\"$v\"; n=$((n+${#l}))", iters=N)
add("emit_v_multi", "printf -v two assigns",
    "", "printf -v a '%d' $__bs_i; printf -v b '%d' "
         "$((__bs_i*2)); n=${#a}+${#b}", iters=N)

# ===========================================================================
# Loop cases whose iteration count is tied to fixture size: pre-opened fds
# consume file position, and direct (non-modulo) mapfile indexes assume
# iters <= line count. Disable autorange so scaled-up iters can't run past
# EOF / array bounds and distort ns/op.
_NO_AUTORANGE = {
    "read_fd9_count", "read_fd9_len", "read_fd9_arr", "read_fd9_kv",
    "read_fd9_csv", "read_fd9_num", "read_fd3_count", "read_fd9_nul",
    "mapfile_idx_len", "mapfile_idx_strip", "mapfile_idx_cut",
    "mapfile_idx_up", "mapfile_idx_case",
}


def cases() -> list:
    out = []
    for suffix, title, setup, body, iters, extra, files in ROWS:
        out.append(Case(
            id="data2_%s" % suffix,
            title="data2 %s" % title,
            category="hotloop",
            kind="loop",
            tags=("hotloop", "generated", "v2") + extra,
            setup=setup, body=body, iters=iters, files=files,
            autorange=suffix not in _NO_AUTORANGE))
    for suffix, title, body, iters, files, setup in SCRIPTS:
        extra = ("cap:devfs",) if "/dev/null" in body else ()
        out.append(Case(
            id="data2_%s" % suffix,
            title="data2 script %s" % title,
            category="hotloop",
            kind="script",
            tags=("hotloop", "generated", "v2") + extra,
            setup=setup, body=body, iters=iters, files=files,
            timeout=300.0))
    return out
