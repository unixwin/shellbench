"""Error-path throughput (corpus v2): the cost of failing operations --
command lookup failure, failing redirections, failing builtins.

Error text goes to stderr (discarded while timing, captured on the
verify run). None of these abort the script: forms whose failure is
fatal to a non-interactive shell (special-builtin / expansion errors)
are wrapped in a subshell so the loop survives; plain failing commands
need no guard because the shell continues after them.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

_FAKE_PATH = ":".join("/bsfake%d" % i for i in range(30)) + ":/usr/bin:/bin"


def C(cid, title, body, iters=1000, setup="", files=(), **kw):
    tags = ("errors", "v2") + tuple(kw.pop("tags", ()))
    return Case(id=cid, title=title, category="errors", body=body,
                setup=setup, iters=iters, files=files, tags=tags, **kw)


CASES = [
    C("errors.cmd_not_found", "command not found (short PATH)",
      "nosuch_cmd_xyz_42", iters=500),
    C("errors.cmd_not_found_path", "command not found (30 fake PATH dirs)",
      "nosuch_cmd_xyz_42", setup="PATH=%s" % _FAKE_PATH, iters=500),
    C("errors.cd_missing", "cd to missing directory",
      "cd /nonexistent_dir_xyz_42", iters=2000),
    C("errors.redirect_missing_dir", "redirect into missing directory",
      "echo x > nodir_xyz_42/out.txt", iters=2000),
    C("errors.redirect_is_dir", "redirect onto a directory",
      "echo x > somedir", iters=2000,
      files=(("somedir/keep.txt", "x\n"),)),
    C("errors.bad_fd_write", "write to unopened fd 9",
      "echo x >&9", iters=3000),
    C("errors.readonly_assign_sub", "readonly assignment (subshell guard)",
      "( RO=2 )", setup="readonly RO=1", iters=1000),
    C("errors.unset_var_u_sub", "set -u unset reference (subshell guard)",
      "( set -u; echo $NEVER_SET_XYZ_42 )", iters=500),
    C("errors.arith_div_zero_sub", "division by zero (subshell guard)",
      "( x=$(( 1 / 0 )) )", iters=1000),
    C("errors.source_missing_sub", "source missing file (subshell guard)",
      "( source ./no_such_file_xyz_42.sh )", iters=1000),
    C("errors.exec_missing_sub", "exec missing command (subshell guard)",
      "( exec nosuch_cmd_xyz_42 )", iters=500),
    C("errors.shift_past_end_sub", "shift past $# (subshell guard)",
      "( set -- a b; shift 5 )", iters=2000),
]
