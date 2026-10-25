"""Globbing / pathname expansion over a generated file tree, plus
pattern matching through [[ == ]] and case."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

_TXT = tuple(("tree/f%03d.txt" % i, "") for i in range(200))
_LOG = tuple(("tree/f%03d.log" % i, "") for i in range(50))
_NESTED = tuple(("tree/sub%d/deep/file%d.txt" % (i % 5, i), "")
                for i in range(50))
TREE = _TXT + _LOG + _NESTED


def C(cid, title, body, iters=1, setup="", kind="script", files=TREE, **kw):
    return Case(id=cid, title=title, category="glob", body=body,
                setup=setup, iters=iters, kind=kind, files=files,
                tags=("glob",), **kw)


CASES = [
    C("glob.star_txt@200", "*.txt expansion (200 matches)",
      "for f in tree/*.txt; do c=$((c+1)); done", setup="c=0", iters=200),
    C("glob.star_all@300", "* expansion (300 matches)",
      "for f in tree/*; do c=$((c+1)); done", setup="c=0", iters=300),
    C("glob.question@200", "?.txt pattern", "for f in tree/f?00.txt; "
      "do c=$((c+1)); done", setup="c=0", iters=200),
    C("glob.bracket@200", "[ab]*.txt bracket pattern",
      "for f in tree/f[01]*.txt; do c=$((c+1)); done", setup="c=0",
      iters=200),
    C("glob.starstar@300", "** recursive globstar",
      "for f in tree/**/*.txt; do c=$((c+1)); done",
      setup="shopt -s globstar; c=0", iters=250),
    C("glob.nomatch_plain", "no-match literal passthrough",
      "for f in tree/zzz*.txt; do x=$f; done", iters=300, kind="loop",
      files=TREE),
    C("glob.nomatch_nullglob", "no-match with nullglob",
      "shopt -s nullglob; a=(tree/zzz*.txt); x=${#a[@]}", iters=1000,
      kind="loop", files=TREE),
    C("glob.assign_array@200", "array from glob",
      "a=(tree/*.txt); x=${#a[@]}", iters=200, kind="loop", files=TREE),
    C("glob.extglob_plus", "extglob +(a|b)",
      "for f in tree/f+(0|1)*.txt; do c=$((c+1)); done",
      setup="shopt -s extglob; c=0", iters=200),
    C("glob.extglob_neg", "extglob !(...) exclusion",
      "for f in tree/!(f0*).txt; do c=$((c+1)); done",
      setup="shopt -s extglob; c=0", iters=200),
    C("glob.case_pattern", "case with glob patterns",
      "case $f in *.txt) x=1;; *.log) x=2;; *) x=3;; esac",
      setup="f=name.txt", iters=5000, kind="loop", files=()),
    C("glob.dotfiles", "dotglob expansion",
      "shopt -s dotglob; a=(dhome/*); x=${#a[@]}", iters=300, kind="loop",
      files=tuple(("dhome/.hidden%d" % i, "") for i in range(20)) +
      tuple(("dhome/vis%d" % i, "") for i in range(20))),
]

# --- corpus v2 additions: extglob operator forms over a controlled
# name set, [[:class:]] patterns, glob sort order under two locales,
# brace+glob and multi-pattern unions (tree-size ladders in v2_gen) ---
_GX = tuple(("gx/%s" % n, "") for n in (
    "a1.txt", "a2.txt", "a3.log", "ab.txt", "b1.txt", "b2.log",
    "ba.log", "c1.md", "x.txt", "y.log"))
_MC = tuple(("mc/%s" % n, "") for n in (
    "B1.txt", "Z1.txt", "a1.txt", "b1.txt"))

_V2 = [
    C("glob.gx_plus", "extglob +(a|b) prefix run",
      "for f in gx/+(a|b)*.txt; do c=$((c+1)); done",
      setup="shopt -s extglob; c=0", files=_GX),
    C("glob.gx_star", "extglob *(a|b) full stem",
      "for f in gx/*(a|b).txt; do c=$((c+1)); done",
      setup="shopt -s extglob; c=0", files=_GX),
    C("glob.gx_quest", "extglob ?(a) optional",
      "for f in gx/?(a)1.txt; do c=$((c+1)); done",
      setup="shopt -s extglob; c=0", files=_GX),
    C("glob.gx_at", "extglob @(a1|b1|x) alternatives",
      "for f in gx/@(a1|b1|x).txt; do c=$((c+1)); done",
      setup="shopt -s extglob; c=0", files=_GX),
    C("glob.gx_neg", "extglob !(...) over gx set",
      "for f in gx/!(*.log); do c=$((c+1)); done",
      setup="shopt -s extglob; c=0", files=_GX),
    C("glob.gx_combo", "extglob +(a|b)@(.txt|.log) combo",
      "for f in gx/+(a|b)@(.txt|.log); do c=$((c+1)); done",
      setup="shopt -s extglob; c=0", files=_GX),
    C("glob.class_alpha", "[[:alpha:]] leading class over tree",
      "for f in tree/[[:alpha:]]*.txt; do c=$((c+1)); done",
      setup="c=0", iters=200),
    C("glob.class_digit2", "[[:digit:]] pair in name over tree",
      "for f in tree/f[[:digit:]][[:digit:]]*.txt; do c=$((c+1)); done",
      setup="c=0", iters=200),
    C("glob.sort_mc_c", "glob sort order, mixed case, C collation",
      "a=(mc/*); x=${a[*]}", setup="LC_ALL=C", kind="loop", iters=2000,
      files=_MC, epilogue="echo ${a[*]}",
      expect_out=r"mc/B1\.txt mc/Z1\.txt mc/a1\.txt mc/b1\.txt"),
    C("glob.sort_mc_utf8", "glob sort order, mixed case, C.UTF-8",
      "a=(mc/*); x=${a[*]}", kind="loop", iters=2000, files=_MC,
      env=(("LC_ALL", "C.UTF-8"),), epilogue="echo ${a[*]}",
      expect_out=r"mc/B1\.txt mc/Z1\.txt mc/a1\.txt mc/b1\.txt"),
    C("glob.brace_then_glob", "brace expansion feeding two globs",
      "for f in tree/{f0,f1}*.txt; do c=$((c+1)); done",
      setup="c=0", iters=200),
    C("glob.multi_union", "two patterns in one word list",
      "for f in tree/*.txt tree/*.log; do c=$((c+1)); done",
      setup="c=0", iters=250),
]

from dataclasses import replace as _replace  # noqa: E402

CASES += [_replace(c, tags=c.tags + ("v2",)) for c in _V2]
del _replace, _V2
