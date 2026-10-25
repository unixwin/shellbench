"""Startup family: process-launch cost in its several flavours."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

_BIG_LIB = "\n".join("fn%d() { local a=%d; x=$((a + %d)); }" % (i, i, i)
                     for i in range(2000)) + "\n"

CASES = [
    Case(id="startup.empty_c", title="shell -c ':'", category="startup",
         kind="process", argv=("-c", ":"), tags=("startup",)),
    Case(id="startup.true_c", title="shell -c 'true'", category="startup",
         kind="process", argv=("-c", "true"), tags=("startup",)),
    Case(id="startup.assign_c", title="shell -c assignments", category="startup",
         kind="process", argv=("-c", "a=1; b=2; c=$((a+b))"),
         tags=("startup",)),
    Case(id="startup.norc_c", title="shell --norc -c ':'", category="startup",
         kind="process", argv=("--norc", "-c", ":"), tags=("startup",)),
    Case(id="startup.script_noop", title="script file ':'", category="startup",
         kind="process", argv=("{script}",), body=":",
         tags=("startup",)),
    Case(id="startup.script_small", title="script file: assigns + fn def",
         category="startup", kind="process", argv=("{script}",),
         body="a=1\nf() { return 0; }\nf\n", tags=("startup",)),
    Case(id="startup.login_c", title="--login -c ':' (profile fixture)",
         category="startup", kind="process", argv=("--login", "-c", ":"),
         env=(("HOME", "{work}"),),
         files=((".bash_profile",
                 "export PATH=$PATH:/usr/local/bin\nPS1='x$ '\n"),),
         tags=("startup",)),
    Case(id="startup.interactive_c", title="-i -c ':' (rc fixture)",
         category="startup", kind="process", argv=("-i", "-c", ":"),
         env=(("HOME", "{work}"), ("HISTFILE", "/dev/null"),
              ("TERM", "dumb")),
         files=((".bashrc", "alias ll='ls -l'\nPS1='x$ '\n"),),
         tags=("startup",), timeout=30.0),
    Case(id="startup.biglib_source", title="source 2000-function library",
         category="startup", kind="process",
         argv=("-c", "source {work}/lib.sh"),
         files=(("lib.sh", _BIG_LIB),), iters=2000,
         tags=("startup", "parse")),
    Case(id="startup.subshell_c", title="shell -c '( : )'", category="startup",
         kind="process", argv=("-c", "( : )"), tags=("startup",)),
    # --- corpus v2 additions (env/PATH/rc ladders in v2_gen) ---
    Case(id="startup.version_only", title="shell --version",
         category="startup", kind="process", argv=("--version",),
         tags=("startup", "v2")),
    Case(id="startup.posix_c", title="shell --posix -c ':'",
         category="startup", kind="process", argv=("--posix", "-c", ":"),
         tags=("startup", "v2")),
    Case(id="startup.noprofile_login_c",
         title="--login --noprofile -c ':' (profile present, skipped)",
         category="startup", kind="process",
         argv=("--login", "--noprofile", "-c", ":"),
         env=(("HOME", "{work}"),),
         files=((".bash_profile",
                 "export PATH=$PATH:/usr/local/bin\nPS1='x$ '\n"),),
         tags=("startup", "v2")),
]
