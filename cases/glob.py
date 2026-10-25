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
      "shopt -s globstar; for f in tree/**/*.txt; do c=$((c+1)); done",
      setup="c=0", iters=250),
    C("glob.nomatch_plain", "no-match literal passthrough",
      "for f in tree/zzz*.txt; do x=$f; done", iters=300, kind="loop",
      files=TREE),
    C("glob.nomatch_nullglob", "no-match with nullglob",
      "shopt -s nullglob; a=(tree/zzz*.txt); x=${#a[@]}", iters=1000,
      kind="loop", files=TREE),
    C("glob.assign_array@200", "array from glob",
      "a=(tree/*.txt); x=${#a[@]}", iters=200, kind="loop", files=TREE),
    C("glob.extglob_plus", "extglob +(a|b)",
      "shopt -s extglob; for f in tree/f+(0|1)*.txt; do c=$((c+1)); done",
      setup="c=0", iters=200),
    C("glob.extglob_neg", "extglob !(...) exclusion",
      "shopt -s extglob; for f in tree/!(f0*).txt; do c=$((c+1)); done",
      setup="c=0", iters=200),
    C("glob.case_pattern", "case with glob patterns",
      "case $f in *.txt) x=1;; *.log) x=2;; *) x=3;; esac",
      setup="f=name.txt", iters=5000, kind="loop", files=()),
    C("glob.dotfiles", "dotglob expansion",
      "shopt -s dotglob; a=(dhome/*); x=${#a[@]}", iters=300, kind="loop",
      files=tuple(("dhome/.hidden%d" % i, "") for i in range(20)) +
      tuple(("dhome/vis%d" % i, "") for i in range(20))),
]
