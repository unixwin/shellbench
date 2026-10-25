"""Case registry: hand-written modules + generator output.

Every taxonomy category contributes at least one batch. Generators expand
compact tables into the bulk of the corpus; see generators/.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from . import (arrays, cond, control, coproc, data, errors, expand,  # noqa: E402
               funcs, glob, jobs, mixed, parse, redir, startup, strings,
               subst)
from generators import (arith_gen, builtin_gen, expand_gen, scale_gen,  # noqa: E402
                        v2_gen)

CASES = []
for _mod in (startup, parse, expand, strings, arrays, control, funcs,
             subst, redir, glob, cond, jobs, data, mixed, coproc, errors):
    CASES += list(_mod.CASES)
CASES += expand_gen.cases()
CASES += builtin_gen.cases()
CASES += arith_gen.cases()
CASES += scale_gen.cases()
CASES += v2_gen.cases()

# ---------------------------------------------------------------------------
# Platform-applicability annotation (capability predicates), v2 cases.
#
# A case that silently assumes a Unix-ism would produce meaningless (or
# silently wrong-shaped) numbers on a platform that lacks it, so every
# v2 case carries `cap:*` tags naming the capabilities it requires.
# A platform profile (DESIGN.md section 7) lists the capabilities each
# platform + shell stack provides; a case is applicable exactly when
# its required caps are a subset of the profile's. Cases with no cap
# tags are applicable everywhere the suite itself runs.
#
# Vocabulary:
#   cap:devfs             references /dev/... device paths (on Windows
#                         these are provided by the shell layer, not
#                         the OS -- the assumption is still explicit)
#   cap:posix-signals     uses USR1/USR2/CHLD/PIPE signal specs
#   cap:utf8-locale       pins LC_ALL=C.UTF-8 (glibc-spelled locale)
#   cap:posix-path        Unix PATH morphology (':' separator, / roots)
#   cap:case-sensitive-fs needs files differing only by case to coexist
#
# Text/env-derivable caps are inferred by the deterministic rules
# below; caps that need human judgement are in the explicit tables.
# ---------------------------------------------------------------------------

import re as _re
from dataclasses import replace as _replace

_CAP_TEXT_RULES = (
    (_re.compile(r"/dev/"), "cap:devfs"),
    (_re.compile(r"\b(USR1|USR2|CHLD|PIPE)\b"), "cap:posix-signals"),
)
_CAP_BY_ID = {
    "glob.sort_mc_c": ("cap:case-sensitive-fs",),
    "glob.sort_mc_utf8": ("cap:case-sensitive-fs",),
}
_CAP_BY_PREFIX = (
    ("startup.lad_path", ("cap:posix-path",)),
)


def _annotate(case):
    if "v2" not in case.tags:
        return case
    add = list(_CAP_BY_ID.get(case.id, ()))
    for prefix, caps in _CAP_BY_PREFIX:
        if case.id.startswith(prefix):
            add += caps
    text = "\n".join((case.body, case.setup, case.epilogue,
                      " ".join(case.argv),
                      "\n".join(content for _, content in case.files)))
    for rx, cap in _CAP_TEXT_RULES:
        if rx.search(text):
            add.append(cap)
    if any(k == "LC_ALL" and v == "C.UTF-8" for k, v in case.env):
        add.append("cap:utf8-locale")
    add = [t for t in add if t not in case.tags]
    if add:
        return _replace(case, tags=case.tags + tuple(add))
    return case


CASES = [_annotate(_case) for _case in CASES]
del _annotate, _replace, _re

__all__ = ["CASES"]
