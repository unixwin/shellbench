"""Per-builtin generator: one row per builtin invocation shape.

Every builtin in the taxonomy gets at least one timed loop case. Rows are
(builtin, suffix, title, setup, body, iters). Bodies must be valid inside
a plain counting loop; builtins with loop-hostile semantics (exec, exit)
are covered by the process family in cases/startup.py instead.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

ROWS = [
    ("echo", "plain", "echo literal", "", "echo hello >/dev/null", 3000),
    ("echo", "var", "echo variable", "v=hello", "echo $v >/dev/null", 3000),
    ("echo", "n_flag", "echo -n", "", "echo -n hello >/dev/null", 3000),
    ("echo", "e_escapes", "echo -e escapes", "", r"echo -e 'a\tb\nc' >/dev/null", 3000),
    ("printf", "fmt_s", "printf %s", "", "printf '%s\n' hello >/dev/null", 3000),
    ("printf", "fmt_nums", "printf %d %f", "", "printf '%d %.3f\n' 42 3.14159 >/dev/null", 2000),
    ("printf", "v_assign", "printf -v", "", "printf -v x '%s' hello", 3000),
    ("printf", "reuse", "printf format reuse", "", "printf '%s,' a b c d e >/dev/null", 2000),
    ("test", "str_eq", "test string =", "a=foo", "test $a = foo", 5000),
    ("test", "int_lt", "test int -lt", "a=5", "test $a -lt 10", 5000),
    ("test", "file_t", "test -e file", "", "test -e case.sh", 3000),
    ("test", "unary_z", "test -z", "a=", "test -z $a", 5000),
    (" bracket", "expr", "[ ] expression", "a=foo", "[ $a = foo ]", 5000),
    ("declare", "assign", "declare assign", "", "declare x=42", 5000),
    ("declare", "local_like", "declare -i arithmetic", "", "declare -i n=1+2", 3000),
    ("declare", "print", "declare -p", "x=42", "declare -p x >/dev/null", 1000),
    ("local", "in_func", "local in function", "f() { local y=1; }", "f", 5000),
    ("typeset", "assign", "typeset assign", "", "typeset x=42", 5000),
    ("export", "assign", "export assign", "", "export BSX=42", 3000),
    ("unset", "var", "unset var", "", "x=1; unset x", 3000),
    ("readonly", "set", "readonly set", "", "readonly BSR$__bs_i=1 2>/dev/null", 1000),
    ("shift", "one", "shift", "set -- a b c d", "shift; set -- a b c d", 3000),
    ("getopts", "parse", "getopts loop", "set -- -a -b val -c", "OPTIND=1; while getopts 'ab:c' o; do :; done", 500),
    ("cd", "dot", "cd .", "", "cd .", 3000),
    ("pwd", "plain", "pwd", "", "pwd >/dev/null", 3000),
    ("pwd", "subst", "pwd in $()", "", "x=$(pwd)", 1000),
    ("type", "builtin", "type echo", "", "type echo >/dev/null", 1000),
    ("hash", "lookup", "hash lookup", "", "hash ls", 1000),
    ("command", "v", "command -v", "", "command -v ls >/dev/null", 1000),
    ("command", "run", "command true", "", "command true", 3000),
    ("builtin", "run", "builtin true", "", "builtin true", 5000),
    ("true", "plain", "true", "", "true", 20000),
    ("false", "plain", "false (rc ignored)", "", "false", 20000),
    ("colon", "plain", ": no-op", "", ":", 20000),
    ("eval", "simple", "eval assignment", "", "eval 'x=1'", 2000),
    ("eval", "concat", "eval concat args", "", "eval echo a b '>/dev/null'", 1000),
    ("exec", "redir_only", "exec redirect open/close", "", "exec 3>/dev/null; exec 3>&-", 1000),
    ("jobs", "list", "jobs empty", "", "jobs >/dev/null", 3000),
    ("wait", "none", "wait no jobs", "", "wait", 3000),
    ("kill", "l_list", "kill -l", "", "kill -l >/dev/null", 1000),
    ("ulimit", "read", "ulimit -n read", "", "ulimit -n >/dev/null", 3000),
    ("umask", "read", "umask read", "", "umask >/dev/null", 3000),
    ("shopt", "query", "shopt set/query/unset", "", "shopt -s nullglob; shopt -q nullglob; shopt -u nullglob", 3000),
    ("set", "query", "set -o query", "", "set -o >/dev/null", 1000),
    ("alias", "define", "alias define+unalias", "", "alias bsa='true'; unalias bsa", 1000),
    ("history", "list", "history builtin (non-interactive)", "", "history >/dev/null 2>&1", 500),
    ("enable", "list", "enable -a list", "", "enable -a >/dev/null", 500),
    ("help", "one", "help echo", "", "help echo >/dev/null", 500),
    ("let", "simple", "let a=1+2", "", "let 'a=1+2'", 5000),
    ("let", "multi", "let multi", "", "let 'a=1' 'b=a+1' 'c=b*2'", 3000),
    ("return", "in_func", "return from function", "f() { return 3; }", "f; test $? -eq 3", 5000),
    ("break", "loop", "break inner", "", "for j in 1 2 3 4 5; do break; done", 3000),
    ("continue", "loop", "continue inner", "", "for j in 1 2 3; do continue; done", 3000),
    ("mapfile", "small", "mapfile from procsub", "", "mapfile -t arr < <(printf 'a\nb\nc\n')", 200),
    ("readarray", "small", "readarray", "", "readarray -t arr < <(printf 'x\ny\n')", 200),
    ("read", "line", "read one line", "", "read -r line < data.txt", 1000),
    ("read", "fields", "read fields IFS split", "", "IFS=: read -r a b c <<< 'x:y:z'", 2000),
    ("read", "array", "read -a split", "", "read -ra arr <<< 'one two three'", 2000),
    ("read", "d_delim", "read -d ''", "", "read -r -d '' x < data.txt", 200),
    ("kill", "zero_self", "kill -0 self liveness", "", "kill -0 $$", 3000),
    ("times", "plain", "times", "", "times >/dev/null", 3000),
    ("caller", "in_func", "caller in function", "f() { caller 0 >/dev/null; }", "f", 1000),
    ("compgen", "word", "compgen -W", "", "compgen -W 'alpha beta gamma' -- a >/dev/null", 500),
    ("complete", "list", "complete -p list-ish", "", "complete -p >/dev/null 2>&1", 200),
    ("fc", "list", "fc -l with seeded history", "set -o history; history -s 'echo seeded'", "fc -l >/dev/null", 200),
    ("popd", "pair", "pushd/popd pair", "", "pushd . >/dev/null; popd >/dev/null", 1000),
    ("dirs", "list", "dirs", "", "dirs >/dev/null", 3000),
    ("bgfg", "job_cycle", "spawn + wait cycle", "", "sleep 0 & p=$!; wait $p", 100),
]


def cases() -> list:
    out = []
    files = (("data.txt", "@gen:lines:100"),)
    for name, suffix, title, setup, body, iters in ROWS:
        bname = name.strip()
        out.append(Case(
            id="builtin.%s_%s" % (bname, suffix),
            title="builtin %s: %s" % (bname, title), category="builtin",
            tags=("builtin", "generated", bname),
            setup=setup, body=body, iters=iters,
            files=files if "data.txt" in body else ()))
    return out
