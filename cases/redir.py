"""Pipelines and redirections."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402


def C(cid, title, body, iters=1000, setup="", **kw):
    tags = ("redir",) + tuple(kw.pop("tags", ()))
    return Case(id=cid, title=title, category="redir", body=body,
                setup=setup, iters=iters, tags=tags, **kw)


CASES = [
    C("redir.devnull_write", "echo >/dev/null", "echo hi >/dev/null",
      iters=5000),
    C("redir.file_append", "echo >>file append", "echo line >> out.log",
      setup=": > out.log", iters=2000),
    C("redir.file_truncate_write", "echo >file per iter",
      "echo line > out.txt", iters=1000),
    C("redir.stderr_merge", "2>&1 merge", "echo hi 2>&1 >/dev/null",
      iters=3000),
    C("redir.both_to_file", "&>file both streams", "echo hi &> out.txt",
      iters=1000),
    C("redir.heredoc_small", "heredoc 3 lines to cat",
      "cat >/dev/null <<EOF\nalpha\nbeta\ngamma\nEOF", iters=500),
    C("redir.heredoc_expand", "heredoc with expansion",
      "cat >/dev/null <<EOF\nvalue is $v and $((1+2))\nEOF",
      setup="v=xyz", iters=500),
    C("redir.herestring_cat", "herestring to cat", "cat <<< 'some words' "
      ">/dev/null", iters=500, tags=("redir", "spawn")),
    C("redir.herestring_read", "herestring into read",
      "read -r x <<< 'hello world'", iters=3000),
    C("redir.fd_open_close", "exec fd open + close",
      "exec 3>/dev/null; exec 3>&-", iters=2000),
    C("redir.fd_dup_write", "write via dup fd", "echo hi >&3",
      setup="exec 3>/dev/null", iters=3000),
    C("redir.input_redirect_read", "read <file", "read -r x < one.txt",
      files=(("one.txt", "hello world\n"),), iters=2000),
    C("redir.pipe_two_builtin", "builtin | builtin pipeline",
      "echo hi | read -r x", iters=300),
    C("redir.pipe_two_ext", "echo | cat pipeline", "echo hi | cat "
      ">/dev/null", iters=200, tags=("redir", "spawn")),
    C("redir.pipe_three_ext", "three-stage pipeline",
      "echo hi | cat | cat >/dev/null", iters=150, tags=("redir", "spawn")),
    C("redir.pipe_data_10k", "10k lines through two cats",
      "cat data.txt | cat | wc -l >/dev/null", kind="script", iters=10000,
      files=(("data.txt", "@gen:lines:10000"),), tags=("redir", "spawn")),
    C("redir.clobber_guard", "noclobber拒 overwrite attempt cost",
      "set -C; echo x >| out.txt", setup=": > out.txt", iters=1000),
    C("redir.devfull_nowhere", "write to /dev/null via fd var",
      "echo hi >&$fd", setup="exec {fd}>/dev/null", iters=3000),
]
