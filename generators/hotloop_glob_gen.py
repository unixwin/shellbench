"""Pathname-expansion (glob) deep-matrix hot-loop generator (glob2 family).

Companion to ``hotloop_exp_gen.py``'s ~22 basic glob rows: this file goes
deep on pathname expansion at scale. Fixture trees are built *in setup*
(``rm -rf`` a unique dir + ``mkdir -p`` + touch loops), because the corpus
runner gives each case its own workdir and setup runs once before timing.

Coverage areas:

- ``size``   -- tree-size ladder: flat trees of {10,100,500} files x a
                ~20-pattern sweep, plus a prefixed-name tree {aa_,bb_,cc_,
                dd_} for character-class / length-class patterns.
- ``shape``  -- 2-level dir trees, deep nesting, mixed extensions, dotfiles,
                names with spaces / UTF-8 / glob metacharacters.
- ``opts``   -- shopt option matrix: nullglob, failglob, dotglob, extglob,
                globstar, nocaseglob, globasciiranges, GLOBIGNORE, set -f,
                LC_ALL sort-order pairs.
- ``brace``  -- brace x glob combos: ``*.{txt,log}``, ``{a,b}*``, nested
                braces, brace ranges, brace-of-globs, brace no-match.
- ``expand`` -- expansion-vs-no-expand contrasts: quoted/escaped patterns,
                variable-held patterns, ``set -f``, ``GLOBIGNORE``.
- ``dtest``  -- directory-vs-file discrimination: ``*/``, ``-d`` tests
                inside glob loops, ``[[ == */ ]]``, empty dirs.
- ``script`` -- kind="script" replays: extension histogram, dry-run rename,
                duplicate-basename detection, name-sort proxy.
- ``tilde``  -- HOME-override tilde expansion edges.

Bodies exit 0: ``for f in PAT`` iterates once on a literal no-match (rc 0),
and every conditional tail carries ``|| :``. Non-match cases that would
abort under ``failglob`` are guarded with ``|| :`` on the ``for`` command.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

ROWS = []
_COUNT = {}

TAGS = ("hotloop", "generated", "v2")


def add(area, slug, title, setup, body, iters=2000, extra=(), env=(),
        kind="loop"):
    ROWS.append((area, slug, title, setup, body, iters, tuple(extra),
                 tuple(env), kind))


def _cid(area, slug):
    key = (area, slug)
    n = _COUNT.get(key, 0) + 1
    _COUNT[key] = n
    return "glob2_%s_%s_%d" % (area, slug, n)


# ---------------------------------------------------------------------------
# Setup builders. Each emits: rm -rf <unique dir>; mkdir; cd; fixture loops.
# ``cd`` persists for the rest of the rendered script, so bodies use
# relative patterns.
# ---------------------------------------------------------------------------

def _flat(d, n, exts=("txt", "log", "md", "dat"), dots=()):
    """Flat dir ``d`` with n files fNNNN.<ext cycling> + dotfiles."""
    e = len(exts)
    cases = " ".join("%d) x=%s;;" % (i, x) for i, x in enumerate(exts))
    cases += " *) x=dat;;"
    s = ("rm -rf %s; mkdir -p %s; cd %s || exit 1; " % (d, d, d))
    s += ("for k in {1..%d}; do n=$(printf '%%04d' $k); "
          "case $((k %% %d)) in %s esac; : > \"f$n.$x\"; done; "
          % (n, e, cases))
    s += ": > README; "
    for i, name in enumerate(dots):
        s += ": > '%s'; " % name
    return s


def _pfx(d, n, exts=("txt", "log", "md", "dat")):
    """Flat dir with prefixed names aa_NNNN.ext .. dd_NNNN.ext."""
    e = len(exts)
    cases = " ".join("%d) x=%s;;" % (i, x) for i, x in enumerate(exts))
    cases += " *) x=dat;;"
    s = ("rm -rf %s; mkdir -p %s; cd %s || exit 1; "
         "pp=(aa bb cc dd); " % (d, d, d))
    s += ("for k in {1..%d}; do n=$(printf '%%04d' $k); "
          "p=${pp[$((k %% 4))]}; case $((k %% %d)) in %s esac; "
          ": > \"${p}_${n}.${x}\"; done"
          % (n, e, cases))
    return s


def _levels(d, ndirs=10, per=4):
    """Two-level tree: dNN/ each with per .txt files + .log + .md."""
    s = ("rm -rf %s; mkdir -p %s; cd %s || exit 1; " % (d, d, d))
    s += ("for i in {1..%d}; do dd=$(printf 'd%%02d' $i); "
          "mkdir -p $dd; " % ndirs)
    s += ("for j in {1..%d}; do : > $dd/f$j.txt; done; "
          ": > $dd/f1.log; : > $dd/note.md; done" % per)
    return s


def _mixed(d, n):
    """Flat dir, n files fNNNN.<ext> cycling txt/log/md/dat/none/sh."""
    s = ("rm -rf %s; mkdir -p %s; cd %s || exit 1; " % (d, d, d))
    s += ("for k in {1..%d}; do n=$(printf '%%04d' $k); "
          "case $((k %% 6)) in "
          "0) x=txt;; 1) x=log;; 2) x=md;; 3) x=dat;; "
          "4) x=sh;; *) x=;; esac; "
          "if [ -n \"$x\" ]; then : > \"f$n.$x\"; else : > \"f$n\"; fi; "
          "done" % n)
    return s


def _dots(d):
    """Dotfile-heavy dir."""
    s = ("rm -rf %s; mkdir -p %s/%s %s; cd %s || exit 1; "
         % (d, d, ".cfg", d, d))
    s += ("for k in {1..5}; do : > .a$k; done; "
          ": > .hidden.txt; : > .cfg/x.txt; : > .cfg/y.log; "
          ": > .gitignore; : > v1.txt; : > v2.log; : > README")
    return s


def _weird(d):
    """Names with spaces, UTF-8, and glob metacharacters."""
    s = ("rm -rf %s; mkdir -p %s/%s %s; cd %s || exit 1; "
         % (d, d, "a b", d, d))
    s += (": > 'my file.txt'; : > 'a b/c d.log'; : > 'héllo.txt'; "
          ": > '.txt'; : > '[ab].txt'; : > 'star*.txt'; "
          ": > 'q?.log'; : > under_score.dat; : > plain.md; "
          ": > '.dotfile'")
    return s


def _opts(d):
    """Small tree for the option matrix: files + dirs + dotfiles."""
    s = ("rm -rf %s; mkdir -p %s/d1 %s/d2 %s/empty; cd %s || exit 1; "
         % (d, d, d, d, d))
    s += (": > apple.txt; : > apricot.log; : > banana.txt; "
          ": > cherry.md; : > ax.txt; : > .h1; : > .h2; "
          ": > d1/x.txt; : > d1/y.log; : > d2/z.md; : > d2/w.txt")
    return s


def _globstar(d):
    """3-level tree for globstar on/off."""
    s = ("rm -rf %s; mkdir -p %s/a/b %s/x/y; cd %s || exit 1; "
         % (d, d, d, d))
    s += (": > a/b/c.txt; : > a/b/d.log; : > a/e.txt; "
          ": > x/y/z.txt; : > top.md; : > a/b2.txt")
    return s


def _nocase(d):
    s = ("rm -rf %s; mkdir -p %s; cd %s || exit 1; " % (d, d, d))
    s += ": > Note.TXT; : > note.txt; : > NOTE.Log; : > Readme"
    return s


def _sortmix(d):
    s = ("rm -rf %s; mkdir -p %s; cd %s || exit 1; " % (d, d, d))
    s += (": > A.txt; : > a.txt; : > B.txt; : > b.txt; : > Z.txt; "
          ": > z.txt; : > _u.txt; : > 0top.txt")
    return s


def _brace(d):
    s = ("rm -rf %s; mkdir -p %s/d1 %s/d2; cd %s || exit 1; "
         % (d, d, d, d))
    s += (": > a1.txt; : > a2.txt; : > b1.txt; : > c1.log; "
          ": > x1.txt; : > y1.txt; : > file1.dat; : > file2.dat; "
          ": > file3.dat; : > f00.dat; : > f01.dat; "
          ": > d1/q.txt; : > d1/r.log; : > d2/q.txt; : > d2/r.log")
    return s


def _expand(d):
    """Tree for quoting/escape/var-held-pattern contrasts."""
    s = ("rm -rf %s; mkdir -p %s/sub; cd %s || exit 1; " % (d, d, d))
    s += (": > 'normal.txt'; : > '[x].txt'; : > 'q?.log'; "
          ": > '*.txt'; : > '*'; : > note.TXT; : > sub/in.txt")
    return s


def _dtest(d):
    s = ("rm -rf %s; mkdir -p %s/d1/sub %s/d2 %s/empty; cd %s || exit 1; "
         % (d, d, d, d, d))
    s += (": > f1.txt; : > f2.log; : > d1/a.txt; : > d1/b.log; "
          ": > d2/b.md")
    return s


def _script(d, n=40):
    """Script-kind tree: dirs + mixed files for realistic replays."""
    s = ("rm -rf %s; mkdir -p %s/d1 %s/d2 %s/d3; cd %s || exit 1; "
         % (d, d, d, d, d))
    s += ("for k in {1..%d}; do n=$(printf '%%03d' $k); "
          "case $((k %% 4)) in 0) x=txt;; 1) x=log;; 2) x=md;; *) x=dat;; "
          "esac; dd=$((k %% 3 + 1)); : > d$dd/top$n.$x; "
          ": > leaf$n.$x; done" % n)
    return s


# ---------------------------------------------------------------------------
# 1. size -- tree-size ladder. Flat fNNNN.<ext> trees at 10/100/500 files.
# ---------------------------------------------------------------------------

FLAT_PATS = [
    ("star", "*"), ("star_txt", "*.txt"), ("star_log", "*.log"),
    ("star_md", "*.md"), ("star_dat", "*.dat"), ("star_dot", "*.*"),
    ("star_notxt", "*txt"), ("fstar", "f*"), ("fstar_txt", "f*.txt"),
    ("f_4dig", "f????.txt"), ("f_3dig", "f???.txt"),
    ("f_br_dig", "f[0-9]*"), ("f_br_ndig", "f[!0-9]*"),
    ("f_cls_dig", "f[[:digit:]]*"), ("f_cls_al", "f[[:alpha:]]*"),
    ("quest_txt", "?.txt"), ("quest2_txt", "??*.txt"),
    ("cls_notf", "[!f]*"), ("cls_f", "[f]*"), ("starstar", "**"),
]
for n in (10, 100, 500):
    d = "g2_flat%d" % n
    iters = 2000 if n <= 100 else 700
    setup = _flat(d, n, dots=(".hidden1", ".hidden2")) + "; c=0"
    for slug, pat in FLAT_PATS:
        add("size", "%s_%d" % (slug, n),
            "flat%d glob %s" % (n, pat), setup,
            "for f in %s; do c=$((c+1)); done" % pat,
            iters=iters)

# prefixed-name tree: aa_/bb_/cc_/dd_ prefixes for class/length patterns
PFX_PATS = [
    ("cls_a_c", "[a-c]*"), ("cls_not_a_c", "[!a-c]*"),
    ("cls_ab", "[ab]*"), ("cls_d_z", "[d-z]*"),
    ("a_star", "a*"), ("aa_us", "aa_*"), ("bb_us", "bb_*"),
    ("len2_us", "??_*.txt"), ("len3_us", "???_*.txt"),
    ("dig_us", "*_[0-9]*"), ("cls_low", "[[:lower:]]*"),
    ("cls_up", "[[:upper:]]*") , ("dd_only", "dd_*"),
    ("cls_pair", "[a-d][a-d]_*.log"),
]
for n in (10, 100, 500):
    d = "g2_pfx%d" % n
    iters = 2000 if n <= 100 else 700
    setup = _pfx(d, n) + "; c=0"
    for slug, pat in PFX_PATS:
        add("size", "%s_pfx%d" % (slug, n),
            "pfx%d glob %s" % (n, pat), setup,
            "for f in %s; do c=$((c+1)); done" % pat, iters=iters)

# ---------------------------------------------------------------------------
# 2. shape -- 2-level, deep, mixed-ext, dotfiles, weird names.
# ---------------------------------------------------------------------------

LVL_PATS = [
    ("lvl_d_txt", "*/*.txt"), ("lvl_d01", "d01/*.txt"),
    ("lvl_d0star", "d0*/*.txt"), ("lvl_d1star", "d1*/*.txt"),
    ("lvl_fq", "*/f?.txt"), ("lvl_fl", "*/f?.log"),
    ("lvl_md", "*/*.md"), ("lvl_dirs", "*/"), ("lvl_all1", "*"),
    ("lvl_all2", "*/*"), ("lvl_dqq", "d??/*.txt"),
    ("lvl_cls", "[d]*/f1.*"), ("lvl_fbr", "*/f[0-9].txt"),
    ("lvl_deep_nomatch", "*/*/*"),
]
d = "g2_lvl"
setup = _levels(d) + "; c=0"
for slug, pat in LVL_PATS:
    add("shape", slug, "2level glob %s" % pat, setup,
        "for f in %s; do c=$((c+1)); done" % pat)

DEEP_PATS = [
    ("deep_1", "*"), ("deep_2", "*/*"), ("deep_3", "*/*/*"),
    ("deep_4", "*/*/*/*"), ("deep_a", "a/*"), ("deep_ab", "a/b/*"),
    ("deep_abc", "a/b/c/*"), ("deep_xy", "x/*"),
    ("deep_xyy", "x/y/*"), ("deep_globstar_off", "**/*.txt"),
]
d = "g2_deep"
setup = ("rm -rf %s; mkdir -p %s/a/b/c %s/x/y; cd %s || exit 1; "
         ": > a/b/c/d1.txt; : > a/b/c/d2.txt; : > a/b/e.txt; "
         ": > a/f.txt; : > x/y/z.txt; : > top.txt" % (d, d, d, d))
for slug, pat in DEEP_PATS:
    extra_setup = setup
    if slug == "deep_globstar_off":
        extra_setup = setup + "; c=0"
    add("shape", slug, "deep glob %s" % pat, extra_setup + "; c=0",
        "for f in %s; do c=$((c+1)); done" % pat)
# globstar ON variant of **/*.txt
add("shape", "deep_globstar_on", "deep globstar **/*.txt on",
    setup + "; shopt -s globstar; c=0",
    "for f in **/*.txt; do c=$((c+1)); done")

MIX_PATS = [
    ("mix_txt", "*.txt"), ("mix_log", "*.log"), ("mix_md", "*.md"),
    ("mix_dat", "*.dat"), ("mix_sh", "*.sh"), ("mix_dot", "*.*"),
    ("mix_all", "*"), ("mix_fdot", "f*.?"), ("mix_f4", "f????.*"),
    ("mix_noext", "f????"),
]
d = "g2_mix"
setup = _mixed(d, 60) + "; c=0"
for slug, pat in MIX_PATS:
    add("shape", slug, "mixed-ext glob %s" % pat, setup,
        "for f in %s; do c=$((c+1)); done" % pat)

DOT_PATS_ON = [
    ("dot_star_off", "*", False), ("dot_star_on", "*", True),
    ("dot_all", ".*", False), ("dot_all_on", ".*", True),
    ("dot_cfg", ".cfg/*", False), ("dot_txt", ".*.txt", False),
    ("dot_nondot", ".[!.]*", False), ("dot_nomatch", ".zzz*", False),
]
d = "g2_dots"
setup = _dots(d)
for slug, pat, on in DOT_PATS_ON:
    s = setup + ("; shopt -s dotglob" if on else "") + "; c=0"
    add("shape", slug, "dotfiles glob %s dotglob=%s" % (pat, on), s,
        "for f in %s; do c=$((c+1)); done" % pat)
# nullglob on a dotfile no-match
add("shape", "dot_nullglob", "dotfiles .zzz* with nullglob",
    setup + "; shopt -s nullglob; c=0",
    "for f in .zzz*; do c=$((c+1)); done")

WEIRD_PATS = [
    ("wq_all", "*"), ("wq_dot", "*.*"), ("wq_my", "my*"),
    ("wq_file", "*file*"), ("wq_txt", "*.txt"), ("wq_sub", "*/*.txt"),
    ("wq_space", "* *"), ("wq_brack", "*\\[*"), ("wq_starfile", "star*"),
    ("wq_q", "q*"),
]
d = "g2_weird"
setup = _weird(d) + "; c=0"
for slug, pat in WEIRD_PATS:
    add("shape", slug, "weird-names glob %s" % pat, setup,
        "for f in %s; do c=$((c+1)); done" % pat)

# ---------------------------------------------------------------------------
# 3. opts -- shopt / option matrix on the shared o-tree.
# ---------------------------------------------------------------------------

d = "g2_opts"
O = _opts(d)

# nullglob: match vs no-match, on vs off (array-length form, rc-safe)
for slug, pat, on in (
    ("ng_match_off", "d1/*.txt", False), ("ng_match_on", "d1/*.txt", True),
    ("ng_nomatch_off", "zzz*", False), ("ng_nomatch_on", "zzz*", True),
    ("ng_star_off", "*", False), ("ng_star_on", "*", True),
):
    s = O + ("; shopt -s nullglob" if on else "")
    add("opts", slug, "nullglob=%s %s" % (on, pat), s,
        "a=(%s); x=${#a[@]}" % pat)
# nullglob in for-list form: zero iterations when on
add("opts", "ng_for_empty", "nullglob for-list empty",
    O + "; shopt -s nullglob; c=0",
    "for f in zzz*; do c=$((c+1)); done")
add("opts", "ng_for_nomatch_off", "no nullglob for-list literal",
    O + "; c=0",
    "for f in zzz*; do c=$((c+1)); done")
# failglob: match is safe; no-match aborts expansion -> guard with || :
add("opts", "fg_match", "failglob match",
    O + "; shopt -s failglob", "for f in d1/*.txt; do :; done")
add("opts", "fg_nomatch", "failglob no-match guarded",
    O + "; shopt -s failglob; c=0",
    "for f in zzz*; do c=$((c+1)); done || :")
add("opts", "fg_set_o", "set -o failglob match",
    O + "; set -o failglob", "for f in *.md; do :; done")
add("opts", "fg_set_o_nomatch", "set -o failglob no-match guarded",
    O + "; set -o failglob; c=0",
    "for f in zzz*; do c=$((c+1)); done || :")
# dotglob on the o-tree (.h1 .h2 present)
for slug, pat, on in (
    ("dg_star_off", "*", False), ("dg_star_on", "*", True),
    ("dg_dot", ".*", False), ("dg_dot_on", ".*", True),
    ("dg_txt_on", "*.txt", True), ("dg_h", ".h*", False),
):
    s = O + ("; shopt -s dotglob" if on else "") + "; c=0"
    add("opts", slug, "dotglob=%s %s" % (on, pat), s,
        "for f in %s; do c=$((c+1)); done" % pat)
# extglob forms on o/ names (apple.txt apricot.log banana.txt cherry.md ax.txt)
EG_PATS = [
    ("eg_at", "@(apple|banana).*"), ("eg_at3", "@(apple|banana|cherry).*"),
    ("eg_bang", "!(a)*"), ("eg_plus_a", "+(a)*"),
    ("eg_star_a", "*(a)*"), ("eg_quest", "?(cherry).*"),
    ("eg_plus_ap", "+(ap)*.txt"), ("eg_bang2", "!(apple|banana|cherry|ax|apricot).*"),
]
for slug, pat in EG_PATS:
    add("opts", slug, "extglob %s" % pat,
        O + "; shopt -s extglob; c=0",
        "for f in %s; do c=$((c+1)); done" % pat)
# globstar on/off on g2_gs tree
d = "g2_gs"
GS = _globstar(d)
for slug, pat, on in (
    ("gs_txt_off", "**/*.txt", False), ("gs_txt_on", "**/*.txt", True),
    ("gs_log_on", "**/*.log", True), ("gs_c_on", "**/c.txt", True),
    ("gs_mid_on", "a/**/*.txt", True), ("gs_mid_off", "a/**/*.txt", False),
    ("gs_star2_on", "a/**", True), ("gs_star2_off", "a/**", False),
    ("gs_level2", "*/*.txt", False), ("gs_b2txt", "a/b2.txt", False),
):
    s = GS + ("; shopt -s globstar" if on else "") + "; c=0"
    add("opts", slug, "globstar=%s %s" % (on, pat), s,
        "for f in %s; do c=$((c+1)); done" % pat)
# nocaseglob on case-differing names (cap: filesystem must be case-sensitive
# for the off-cases to discriminate; on Windows/NTFS both behave alike)
d = "g2_nc"
NC = _nocase(d)
for slug, pat, on in (
    ("nc_txt_off", "*.txt", False), ("nc_txt_on", "*.txt", True),
    ("nc_TXT_off", "*.TXT", False), ("nc_TXT_on", "*.TXT", True),
    ("nc_note_off", "note.*", False), ("nc_note_on", "note.*", True),
    ("nc_NOTE_on", "NOTE.*", True),
):
    s = NC + ("; shopt -s nocaseglob" if on else "") + "; c=0"
    add("opts", slug, "nocaseglob=%s %s" % (on, pat), s,
        "for f in %s; do c=$((c+1)); done" % pat,
        extra=("cap:case-sensitive-fs",))
# LC_ALL sort-order pairs on mixed-case names
d = "g2_sort"
SM = _sortmix(d)
for loc, slug in (("C", "sort_c"), ("C.UTF-8", "sort_utf8")):
    add("opts", slug, "glob sort LC_ALL=%s" % loc, SM + "; c=0",
        "for f in *; do c=$((c+1)); done",
        env=(("LC_ALL", loc),))
# globasciiranges on/off under C.UTF-8 (range [a-z] vs collation)
d = "g2_sort"
for on, slug in ((False, "gar_off"), (True, "gar_on")):
    s = SM + ("; shopt -s globasciiranges" if on else "")
    add("opts", slug, "globasciiranges=%s [a-z]*" % on, s,
        "a=([a-z]*); x=${#a[@]}", env=(("LC_ALL", "C.UTF-8"),))
# GLOBIGNORE (bash 3.0+): colon-separated basename patterns
for slug, gi, pat in (
    ("gi_txt", "*.txt", "*"), ("gi_txt_log", "*.txt:*.log", "*"),
    ("gi_d", "d*", "*"), ("gi_none", "*.zzz", "*"),
):
    add("opts", slug, "GLOBIGNORE=%s on %s" % (gi, pat),
        O + "; GLOBIGNORE='%s'; c=0" % gi,
        "for f in %s; do c=$((c+1)); done" % pat)
# set -f (noglob): pattern stays literal
add("opts", "noglob_for", "set -f literal glob",
    O + "; c=0", "set -f; for f in *; do c=$((c+1)); done")
add("opts", "noglob_arr", "set -f array literal",
    O, "set -f; a=(d1/*.txt); x=${#a[@]}")
add("opts", "noglob_off_again", "set +f restores glob",
    O + "; c=0", "set -f; set +f; for f in *.txt; do c=$((c+1)); done")

# ---------------------------------------------------------------------------
# 4. brace -- brace x glob combos on the b/ tree.
# ---------------------------------------------------------------------------

d = "g2_brace"
B = _brace(d)
BRACE_PATS = [
    ("br_ext2", "*.{txt,log}"), ("br_ext3", "*.{txt,md,log}"),
    ("br_pref", "{a,b}*.txt"), ("br_pref3", "{a,x,y}1.txt"),
    ("br_range", "file{1..3}.dat"), ("br_range0", "f{00..01}.dat"),
    ("br_nested", "{{a,b}1,{x,y}1}.txt"), ("br_nomatch", "*.{zzz,qqq}"),
    ("br_empty", "*.{txt,}"), ("br_dirs", "d{1,2}/*.txt"),
    ("br_dirs2", "{d1,d2}/*"), ("br_dirs_both", "{d1,d2}/{q,r}.*"),
    ("br_mid", "a{1,2}.txt"), ("br_adj", "a{1..2}{.txt,.log}"),
    ("br_multi", "{a1,a2,b1}.txt"), ("br_globs", "{*.txt,*.log}"),
    ("br_for", "{a,c}*"), ("br_dg", "{d1,d2}/q.txt"),
]
for slug, pat in BRACE_PATS:
    add("brace", slug, "brace-glob %s" % pat, B + "; c=0",
        "for f in %s; do c=$((c+1)); done" % pat)
add("brace", "br_setargs", "set -- brace-glob count",
    B, "set -- *.{txt,log}; x=$#")
add("brace", "br_assign_noglob", "x={a,b} no brace in assign",
    "", "x={a,b}{1,2}")
add("brace", "br_for_nest", "for over brace-glob",
    B + "; n=0",
    "for f in {d1,d2}/*; do n=$((n+1)); done")

# ---------------------------------------------------------------------------
# 5. expand -- quoted/escaped/variable-held patterns, noglob, GLOBIGNORE.
# ---------------------------------------------------------------------------

d = "g2_exp"
E = _expand(d)
EX_ROWS = [
    ("xq_bare", "*", "glob all"),
    ("xq_esc", "\\*", "escaped star -> literal '*' file"),
    ("xq_sq", "'*'", "single-quoted literal"),
    ("xq_dq", "\"*\"", "double-quoted literal"),
    ("xq_esc_txt", "\\*.txt", "escaped *.txt literal file"),
    ("xq_glob_txt", "*.txt", "glob *.txt (matches literal '*.txt' too)"),
    ("xq_brack", "\\[*\\].txt", "escaped brackets literal [x].txt"),
    ("xq_brack_glob", "*\\[*", "glob star + literal ["),
    ("xq_qfile", "q?.log", "? pattern"),
    ("xq_dotfile", ".*", "dotfiles"),
    ("xq_dir", "*/", "dirs only"),
    ("xq_sub", "*/*.txt", "mid-glob"),
    ("xq_dotpath", "./*.txt", "leading ./"),
    ("xq_dslash", "//*", "double-slash root-ish"),
]
for slug, pat, desc in EX_ROWS:
    add("expand", slug, "%s: %s" % (desc, pat), E + "; c=0",
        "for f in %s; do c=$((c+1)); done" % pat)
# variable-held patterns
add("expand", "xv_unquoted", "var-held pattern unquoted",
    E + "; p='*.txt'; c=0", "for f in $p; do c=$((c+1)); done")
add("expand", "xv_quoted", "var-held pattern quoted (no glob)",
    E + "; p='*'; c=0", "for f in \"$p\"; do c=$((c+1)); done")
add("expand", "xv_partial", "partial-quoted glob",
    E + "; c=0", "for f in \"$PWD\"/*.txt 2>/dev/null; do :; done || :")
# partial quote via concatenation: 'sub'/*.txt
add("expand", "xq_concat", "concat-quoted glob sub/*.txt",
    E + "; c=0", "for f in 'sub'/*.txt; do c=$((c+1)); done")
add("expand", "xq_concat2", "concat-quoted glob */in.txt",
    E + "; c=0", "for f in */'in.txt'; do c=$((c+1)); done")
# echo/printf consume forms (noise redirected)
add("expand", "xe_echo", "echo glob", E, "echo *.txt >/dev/null")
add("expand", "xe_printf", "printf glob", E, "printf '%s\\n' * >/dev/null")
add("expand", "xe_setargs", "set -- glob; $#",
    E, "set -- *; x=$#")
add("expand", "xe_assign_arr", "a=(glob) len",
    E, "a=(*.txt); x=${#a[@]}")
# compgen -G (builtin) as a glob consumer
add("expand", "xg_compgen", "compgen -G count",
    E + "; n=0", "for f in $(compgen -G '*.txt'); do n=$((n+1)); done")
add("expand", "xg_compgen_star", "compgen -G * count",
    E + "; n=0", "for f in $(compgen -G '*'); do n=$((n+1)); done")
# GLOBIGNORE interplay with literal-star filenames
add("expand", "xgi_txt", "GLOBIGNORE *.txt",
    E + "; GLOBIGNORE='*.txt'; c=0",
    "for f in *; do c=$((c+1)); done")
add("expand", "xgi_starfile", "GLOBIGNORE '*' pattern effect",
    E + "; GLOBIGNORE='*'; c=0",
    "for f in *; do c=$((c+1)); done")
# case pattern (non-pathname) for contrast
add("expand", "xc_case", "case glob-pattern match",
    "v='a*b'", "case $v in a*b) :;; *) :;; esac")
add("expand", "xc_dbracket", "[[ == ]] pattern match",
    "v='a*b'", "[[ $v == a*b ]] || :")

# ---------------------------------------------------------------------------
# 6. dtest -- directory-vs-file discrimination.
# ---------------------------------------------------------------------------

d = "g2_dt"
DT = _dtest(d)
DT_PATS = [
    ("dt_dirs", "*/"), ("dt_all", "*"), ("dt_deepdirs", "*/*/"),
    ("dt_suball", "*/*"), ("dt_subtxt", "*/*.txt"), ("dt_d1", "d?"),
    ("dt_dstar", "d*/"), ("dt_d1sub", "d1/*"),
]
for slug, pat in DT_PATS:
    add("dtest", slug, "dtest glob %s" % pat, DT + "; c=0",
        "for f in %s; do c=$((c+1)); done" % pat)
# -d test inside glob loop
add("dtest", "dt_isdir", "[ -d ] count inside glob",
    DT + "; c=0", "for f in *; do [ -d \"$f\" ] && c=$((c+1)); done")
add("dtest", "dt_isfile", "[ -f ] count inside glob",
    DT + "; c=0", "for f in *; do [ -f \"$f\" ] && c=$((c+1)); done")
add("dtest", "dt_dbrack_dir", "[[ == */ ]] count",
    DT + "; c=0",
    "for f in *; do [[ $f == */ ]] && c=$((c+1)) || :; done")
add("dtest", "dt_case_dir", "case */ count",
    DT + "; c=0",
    "for f in *; do case $f in */) c=$((c+1));; esac; done")
add("dtest", "dt_arr_dirs", "a=(*/) array",
    DT, "a=(*/); x=${#a[@]}")
add("dtest", "dt_arr_all", "a=(*) array",
    DT, "a=(*); x=${#a[@]}")
# empty-dir and file-with-trailing-slash edges
add("dtest", "dt_empty_lit", "empty/* literal no-match",
    DT + "; c=0", "for f in empty/*; do c=$((c+1)); done")
add("dtest", "dt_empty_ng", "empty/* nullglob",
    DT + "; shopt -s nullglob", "a=(empty/*); x=${#a[@]}")
add("dtest", "dt_file_slash", "file/ trailing slash no-match",
    DT + "; c=0", "for f in f1.txt/; do c=$((c+1)); done")
add("dtest", "dt_compgen", "compgen -G dirs",
    DT + "; n=0", "for f in $(compgen -G '*/'); do n=$((n+1)); done")
add("dtest", "dt_norm", "d1/../d2/* mid-path",
    DT + "; c=0", "for f in d1/../d2/*; do c=$((c+1)); done")

# ---------------------------------------------------------------------------
# 7. tilde / HOME edges.
# ---------------------------------------------------------------------------

TH = ("rm -rf g2home; mkdir -p g2home/sub; : > g2home/a.txt; "
      ": > g2home/b.log; : > g2home/sub/c.txt; HOME=$PWD/g2home")
add("tilde", "th_assign", "x=~ tilde expand", TH, "x=~")
add("tilde", "th_star", "~/* glob", TH + "; c=0",
    "for f in ~/*; do c=$((c+1)); done")
add("tilde", "th_txt", "~/*.txt glob", TH + "; c=0",
    "for f in ~/*.txt; do c=$((c+1)); done")
add("tilde", "th_nomatch", "~/zzz* literal", TH + "; c=0",
    "for f in ~/zzz*; do c=$((c+1)); done")
add("tilde", "th_nomatch_ng", "~/zzz* nullglob",
    TH + "; shopt -s nullglob", "a=(~/zzz*); x=${#a[@]}")
add("tilde", "th_sub", "~/*/*.txt mid-glob", TH + "; c=0",
    "for f in ~/*/*.txt; do c=$((c+1)); done")
add("tilde", "th_user", "~user literal no-such", "c=0",
    "for f in ~nosuchuserxyz*; do c=$((c+1)); done")

# ---------------------------------------------------------------------------
# 8. script -- realistic script-kind replays.
# ---------------------------------------------------------------------------

SC = _script("g2_sc", 40)

add("script", "sc_ext_count", "count .txt via glob+case",
    SC, """n=0
for f in leaf*.txt; do n=$((n+1)); done
for ((i=0; i<{iters}; i++)); do :; done
""", iters=40, kind="script")

add("script", "sc_hist", "extension histogram assoc",
    SC, """declare -A h
for f in d1/* d2/* d3/*; do
    e=${f##*.}
    h[$e]=$(( ${h[$e]:-0} + 1 ))
done
x=${#h[@]}
""", iters=120, kind="script")

add("script", "sc_rename_dry", "rename dry-run txt->md",
    SC, """n=0
for f in leaf*.txt; do
    t=${f%.txt}.md
    [ "$t" != "$f" ] && n=$((n+1))
done
""", iters=10, kind="script")

add("script", "sc_dupbase", "duplicate basenames across dirs",
    SC, """declare -A c; declare -A seen
for f in d?/*; do
    b=${f##*/}
    case ${seen[$b]:-} in
        "") seen[$b]=$f ;;
        *) c[$b]=1 ;;
    esac
done
n=${#c[@]}
""", iters=120, kind="script")

add("script", "sc_newest", "newest by name-sort proxy",
    SC, """a=(d1/* d2/* d3/*)
last=${a[-1]}
first=${a[0]}
x=$last
""", iters=120, kind="script")

add("script", "sc_namelen", "sum filename lengths",
    SC, """t=0
for f in *; do t=$((t + ${#f})); done
""", iters=40, kind="script")

add("script", "sc_globstar", "globstar recursive count",
    SC + "; shopt -s globstar",
    """n=0
for f in **/*.txt; do n=$((n+1)); done
""", iters=120, kind="script")

add("script", "sc_brace", "brace-glob set -- count",
    SC, """set -- leaf*.{txt,log}
n=$#
""", iters=1, kind="script")

add("script", "sc_dirtree", "dir-vs-file split",
    SC, """nd=0; nf=0
for f in *; do
    if [ -d "$f" ]; then nd=$((nd+1)); else nf=$((nf+1)); fi
done
""", iters=40, kind="script")

add("script", "sc_midglob", "mid-glob d*/*.ext count",
    SC, """n=0
for f in d*/*.txt; do n=$((n+1)); done
for f in d*/*.log; do n=$((n+1)); done
""", iters=120, kind="script")

add("script", "sc_tilde", "tilde glob in script",
    "rm -rf g2_sc_home; mkdir -p g2_sc_home/sub; "
    ": > g2_sc_home/a.txt; : > g2_sc_home/b.log; "
    ": > g2_sc_home/sub/c.txt; HOME=$PWD/g2_sc_home",
    """n=0
for f in ~/*; do n=$((n+1)); done
for f in ~/*.txt; do n=$((n+1)); done
""", iters=1, kind="script")

add("script", "sc_pats", "multi-pattern sweep script",
    SC, """n=0
for p in '*' '*.txt' '*.log' '*.md' '*.dat' 'd?/*' '*/*.txt'; do
    for f in $p; do n=$((n+1)); done
done
""", iters=120, kind="script")

add("script", "sc_extswap", "extension swap collect",
    SC, """out=
for f in leaf*.txt; do out="$out ${f%.txt}.md"; done
n=${#out}
""", iters=10, kind="script")


# ---------------------------------------------------------------------------

def cases() -> list:
    out = []
    for area, slug, title, setup, body, iters, extra, env, kind in ROWS:
        out.append(Case(
            id=_cid(area, slug),
            title="hotloop-glob2 %s" % title,
            category="hotloop",
            tags=TAGS + tuple(e for e in extra if e.startswith("cap:")),
            setup=setup, body=body, iters=iters, env=env,
            kind=kind))
    return out
