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

from . import (arrays, cond, control, data, expand, funcs, glob, jobs,  # noqa: E402
               mixed, parse, redir, startup, strings, subst)
from generators import arith_gen, builtin_gen, expand_gen, scale_gen  # noqa: E402

CASES = []
for _mod in (startup, parse, expand, strings, arrays, control, funcs,
             subst, redir, glob, cond, jobs, data, mixed):
    CASES += list(_mod.CASES)
CASES += expand_gen.cases()
CASES += builtin_gen.cases()
CASES += arith_gen.cases()
CASES += scale_gen.cases()

__all__ = ["CASES"]
