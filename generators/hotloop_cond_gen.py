"""Hot-loop conditional / control-flow deep-matrix generator.

hotloop_gen.py covers ~40 basic if/[ /[[ /case rows; this generator goes
deep on the conditional and control-flow surface:

- ``test`` / ``[ ]`` binary operators: full integer-operand cross product
  (the INT_PAIRS matrix in hotloop_gen.py only emitted its first pair due
  to a ``break`` bug) plus a string-operator matrix.
- ``test`` / ``[ ]`` unary operators across file/dir/device/missing/string/
  fd/variable targets.
- ``[[ ]]`` forms: ``=~`` regex, string/integer ops, ``&&``/``||``/``!``/
  parentheses, ``-v``, ``-nt``/``-ot`` file comparisons.
- Control structures: if/elif/else chains, nested if×case×for, inner
  while/until loops with small fixed bounds, for-in over literal lists and
  arrays, case arm ladders including ``;&``/``;;&``, select, groups,
  short-circuit chains, break/continue.
- Read-only query forms: ``trap -p``, ``times``, ``caller``.
- A handful of ``kind="script"`` replays of realistic control-flow shapes.

Rows are (suffix, title, setup, body, iters, extra_tags, files). Bodies are
always compiled inside ``for ((__bs_i=0; …))`` and must exit 0; every
conditional row ends in ``|| :`` (or an equivalent always-true tail) so a
false test can never leak a non-zero status out of the loop.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

N = 10000
N_INNER = 3000   # bodies with small bounded inner loops

ROWS = []

FIX_FILES = (
    ("cond_fixture.txt", "alpha\nbeta\ngamma\n"),
    ("cond_old.txt", "old\n"),
    ("cond_new.txt", "new\n"),
)
FILE_ONLY = (("cond_fixture.txt", "alpha\nbeta\ngamma\n"),)


def add(suffix, title, setup, body, iters=N, extra=(), files=()):
    ROWS.append((suffix, title, setup, body, iters, tuple(extra), tuple(files)))


# ---------------------------------------------------------------------------
# 1a. test builtin: integer binary operators x operand-shape cross product.
# ---------------------------------------------------------------------------
INT_PAIRS = [
    ("$i", "5"), ("5", "$i"), ("$i", "$i"), ("$i", "-1"), ("-1", "$i"),
    ("$i", "0"), ("$i", "2147483647"), ("-2147483648", "$i"),
    ("$i", "$j"), ("$j", "$i"), ("$__bs_i", "5000"),
    ("5000", "$__bs_i"), ("$i", "999999999"), ("$j", "0"),
]
INT_OPS = ("-eq", "-ne", "-lt", "-le", "-gt", "-ge")
for op in INT_OPS:
    safe_op = op.strip("-")
    for pi, (a, b) in enumerate(INT_PAIRS):
        add("tint_%s_%02d" % (safe_op, pi),
            "test int %s %s %s" % (a, op, b),
            "i=3; j=7",
            "test %s %s %s || :" % (a, op, b))
# [ ] bracket variants: one row per op x a 4-pair subset
BR_INT = [("$i", "5"), ("$i", "-1"), ("$j", "$i"), ("$__bs_i", "5000")]
for op in INT_OPS:
    safe_op = op.strip("-")
    for pi, (a, b) in enumerate(BR_INT):
        add("bint_%s_%d" % (safe_op, pi),
            "[ ] int %s %s %s" % (a, op, b),
            "i=3; j=7",
            "[ %s %s %s ] || :" % (a, op, b))

# ---------------------------------------------------------------------------
# 1b. test builtin: string binary operators (= == != < >) x operand shapes.
# '<' and '>' must be escaped inside test/[ ] (they are redirections).
# ---------------------------------------------------------------------------
STR_PAIRS = [
    ("$v", "hello"), ("$v", "world"), ("a$v", "ahello"), ("pre$v", "prehello"),
    ("$v$post", "hellox"), ("$v$v", "hellohello"), ("$v", '""'),
    ('"$u"', '""'), ('"$v"', '"hello world"'),
]
STR_OPS = ("=", "==", "!=", "\\<", "\\>")
STR_SETUP = "v=hello; post=x"
for op in STR_OPS:
    safe_op = op.replace("\\", "").replace("=", "eq").replace("!", "ne") \
                  .replace("<", "lt").replace(">", "gt")
    for pi, (a, b) in enumerate(STR_PAIRS):
        add("tstr_%s_%02d" % (safe_op, pi),
            "test str %s %s %s" % (a, op.strip("\\"), b),
            STR_SETUP,
            "test %s %s %s || :" % (a, op, b))
# [ ] variants on a 6-pair subset
BR_STR = STR_PAIRS[:6]
for op in STR_OPS:
    safe_op = op.replace("\\", "").replace("=", "eq").replace("!", "ne") \
                  .replace("<", "lt").replace(">", "gt")
    for pi, (a, b) in enumerate(BR_STR):
        add("bstr_%s_%d" % (safe_op, pi),
            "[ ] str %s" % op.strip("\\"), STR_SETUP,
            "[ %s %s %s ] || :" % (a, op, b))

# ---------------------------------------------------------------------------
# 1c. test builtin: unary operators across targets.
# ---------------------------------------------------------------------------
# File-path unary ops x { /dev/null, fixture file, '.', missing path }.
PATH_OPS = ("-e", "-f", "-d", "-r", "-w", "-x", "-s", "-b", "-c", "-p",
            "-S", "-L", "-O", "-G", "-N")
PATH_TARGETS = (
    ("devnull", "/dev/null", ("cap:devfs",), ()),
    ("fixfile", "cond_fixture.txt", (), FILE_ONLY),
    ("dot", ".", (), ()),
    ("missing", "/nonexistent-xyz", (), ()),
)
# Rarely-true-on-anything ops skip the "." target to stay in budget.
RARE_PATH_OPS = ("-b", "-c", "-p", "-S", "-L", "-O", "-G", "-N")
for op in PATH_OPS:
    safe_op = op.strip("-")
    targets = PATH_TARGETS[:1] + PATH_TARGETS[2:] \
        if op in RARE_PATH_OPS else PATH_TARGETS
    for tname, tgt, textra, tfiles in targets:
        add("tuna_%s_%s" % (safe_op, tname),
            "test unary %s %s" % (op, tgt), "",
            "test %s %s || :" % (op, tgt),
            extra=textra, files=tfiles)
# String-value unary ops (-z -n) x operand shapes.
for op in ("-z", "-n"):
    safe_op = op.strip("-")
    for oi, (arg, shape) in enumerate((
            ("$u", "unset-var"), ('""', "empty"), ("x", "one-char"),
            ("'hello world'", "phrase"))):
        # $u is unset: use quoted form so empty expansion stays one arg.
        if arg == "$u":
            arg = '"$u"'
        add("tuna_%s_%s" % (safe_op, shape),
            "test unary %s %s" % (op, shape), STR_SETUP,
            "test %s %s || :" % (op, arg))
# -t fd tests (stdin/stdout/stderr; none are ttys in bench harness, rc-safe).
for fd in ("0", "1", "2"):
    add("tuna_t_fd%s" % fd, "test -t fd %s" % fd, "",
        "test -t %s || :" % fd)
# -v variable tests (set, unset, array element).
add("tuna_v_set", "test -v set var", STR_SETUP, "test -v v || :")
add("tuna_v_unset", "test -v unset var", STR_SETUP, 'test -v "u" || :')
add("tuna_v_elem", "test -v array elem", "arr=(a b c)",
    "test -v 'arr[1]' || :")
# -R readable-variable tests.
add("tuna_R_set", "test -R set var", STR_SETUP, "test -R v || :")
add("tuna_R_unset", "test -R unset var", STR_SETUP, "test -R u || :")

# ---------------------------------------------------------------------------
# 2. [[ ]] forms.
# ---------------------------------------------------------------------------
DB_SETUP = "i=3; j=7; v=hello; u=; post=x; arr=(a b c)"
# =~ regex x subject.
REGEXES = (
    ("^h", "prefix-h"), ("o$", "suffix-o"), ("^h.llo$", "full-match"),
    ("^[a-z]+$", "lower-alpha"), ("^h.*o$", "greedy"), ("^z", "no-match"),
    ("^h[ae]llo$", "class"), ("^(h|w)", "alternation"), ("l+o", "repeat"),
)
for pat, pname in REGEXES:
    for subj_name, subj in (("v", "$v"), ("u", "$u")):
        add("dbr_re_%s_%s" % (pname, subj_name),
            "[[ =~ %s on %s" % (pat, subj_name), DB_SETUP,
            "[[ %s =~ %s ]] || :" % (subj, pat))
# [[ ]] string ops (= == != < >) x pair subset.
DB_STR_PAIRS = STR_PAIRS[:6]
for op in ("=", "==", "!=", "<", ">"):
    safe_op = op.replace("=", "eq").replace("!", "ne") \
                  .replace("<", "lt").replace(">", "gt")
    for pi, (a, b) in enumerate(DB_STR_PAIRS):
        add("dbr_str_%s_%02d" % (safe_op, pi),
            "[[ %s %s %s" % (a, op, b), DB_SETUP,
            "[[ %s %s %s ]] || :" % (a, op, b))
# [[ ]] integer ops x operand pairs.
DB_INT_PAIRS = [("$i", "5"), ("$i", "$j"), ("$__bs_i", "5000"), ("-1", "$i")]
for op in INT_OPS:
    safe_op = op.strip("-")
    for pi, (a, b) in enumerate(DB_INT_PAIRS):
        add("dbr_int_%s_%d" % (safe_op, pi),
            "[[ int %s %s %s" % (a, op, b), DB_SETUP,
            "[[ %s %s %s ]] || :" % (a, op, b))
# [[ ]] file unary subset x targets.
DB_PATH = (("fixfile", "cond_fixture.txt", FILE_ONLY),
           ("dot", ".", ()),
           ("missing", "/nonexistent-xyz", ()))
for op in ("-e", "-f", "-d", "-s", "-x"):
    safe_op = op.strip("-")
    for tname, tgt, tfiles in DB_PATH:
        add("dbr_file_%s_%s" % (safe_op, tname),
            "[[ %s %s" % (op, tgt), "",
            "[[ %s %s ]] || :" % (op, tgt), files=tfiles)
# [[ ]] -v / -nt / -ot.
for vn in ("v", "u", "arr[0]"):
    add("dbr_v_%s" % vn.replace("[", "_").replace("]", ""),
        "[[ -v %s" % vn, DB_SETUP, "[[ -v %s ]] || :" % vn)
NT_SETUP = "touch -t 202001010000.00 cond_old.txt; " \
           "touch -t 202001010100.00 cond_new.txt"
add("dbr_nt_true", "[[ new -nt old", NT_SETUP,
    "[[ cond_new.txt -nt cond_old.txt ]] || :", files=FIX_FILES)
add("dbr_nt_false", "[[ old -nt new", NT_SETUP,
    "[[ cond_old.txt -nt cond_new.txt ]] || :", files=FIX_FILES)
add("dbr_ot_true", "[[ old -ot new", NT_SETUP,
    "[[ cond_old.txt -ot cond_new.txt ]] || :", files=FIX_FILES)
add("dbr_nt_same", "[[ file -nt itself", NT_SETUP,
    "[[ cond_old.txt -nt cond_old.txt ]] || :", files=FIX_FILES)
# [[ ]] compound && / || / ! / parentheses.
COMPOUNDS = [
    ("[[ $i -lt 5 && $v = hello ]] || :", "and-2"),
    ("[[ $i -ge 5 || $v != hello ]] || :", "or-2"),
    ("[[ ! $v = world ]] || :", "bang-str"),
    ("[[ ! ( $i -lt 0 ) ]] || :", "bang-paren"),
    ("[[ ( $i -lt 5 || $i -gt 100 ) && $v == h* ]] || :", "paren-mixed"),
    ("[[ $v == h* && $i -lt 5000 && $j -gt 0 ]] || :", "and-3"),
    ("[[ $v != h* || $i -ge 0 && $j -le 9 ]] || :", "or-and-mix"),
    ("[[ -v v && -n $v && -z $u ]] || :", "unary-compound"),
    ("[[ -f cond_fixture.txt && -s cond_fixture.txt ]] || :", "file-compound",
     FILE_ONLY),
    ("[[ -d . && -e cond_fixture.txt ]] || :", "dir-file-compound",
     FILE_ONLY),
    ("[[ $i -lt 3 ]] && [[ $v = hello ]] || :", "two-brackets"),
    ("[[ $v =~ ^h && $i -lt 5000 ]] || :", "regex-and"),
    ("[[ $v == @(h|H)ello ]] || :", "extglob"),
]
for row in COMPOUNDS:
    body, name = row[0], row[1]
    files = row[2] if len(row) > 2 else ()
    setup = DB_SETUP
    extra = ()
    if name == "extglob":
        setup = "shopt -s extglob; " + DB_SETUP
    add("dbr_cmp_%s" % name, "[[ ]] compound %s" % name, setup, body,
        files=files)

# ---------------------------------------------------------------------------
# 3. Control structures.
# ---------------------------------------------------------------------------
# if/elif/else chains of depth 2-4 x condition forms.
CHAIN_CONDS = [
    ("[ $__bs_i -lt 5000 ]", "test-bracket"),
    ("[[ $__bs_i -lt 5000 ]]", "dbracket"),
    ("((__bs_i < 5000))", "arith"),
    ("test $__bs_i -lt 5000", "test-builtin"),
]
for ci, (c0, cname) in enumerate(CHAIN_CONDS):
    for depth in (2, 3, 4):
        parts = ["if %s; then :" % c0]
        for k in range(1, depth):
            parts.append("elif [ $__bs_i -lt %d ]; then :" % (5000 + k))
        parts.append("else :; fi")
        add("ctl_elif_%s_d%d" % (cname, depth),
            "if/elif chain depth %d (%s)" % (depth, cname), "",
            "; ".join(parts))
# if without else (false branch still rc 0).
add("ctl_if_noelse", "if no-else false", "",
    "if [ $__bs_i -lt 0 ]; then :; fi")
# Nested if x case x for combinations.
NESTED = [
    ("if [ $__bs_i -lt 5000 ]; then "
     "case $v in h*) for j in 1 2 3; do :; done;; *) :;; esac; fi",
     "if-case-for", DB_SETUP),
    ("for j in 1 2 3; do "
     "if [ $j -lt 2 ]; then case x in x) :;; esac; fi; done",
     "for-if-case", ""),
    ("case $v in h*) "
     "if [ $__bs_i -lt 5000 ]; then for j in 1 2; do :; done; fi;; esac",
     "case-if-for", DB_SETUP),
    ("if [[ $v == h* ]]; then "
     "for j in 1 2 3 4; do if [ $j -gt 1 ]; then :; fi; done; fi",
     "if-for-nested-if", DB_SETUP),
    ("for w in a b c; do "
     "case $w in a) if [ -n $w ]; then :; fi;; *) :;; esac; done",
     "for-case-if", ""),
    ("if [ $__bs_i -lt 5000 ]; then "
     "while :; do break; done; fi",
     "if-while-break", ""),
    ("while [ $j -lt 3 ]; do "
     "if [ $j -eq 1 ]; then case x in x) :;; esac; fi; ((j++)); done",
     "while-if-case", "j=0"),
    ("for j in 1 2 3; do "
     "for k in 1 2; do if [ $k -eq 1 ]; then :; fi; done; done",
     "for-for-if", ""),
]
for body, name, setup in NESTED:
    add("ctl_nest_%s" % name, "nested %s" % name, setup, body, N_INNER)
# Inner while/until loops with small fixed bounds (counter reset per outer iter).
INNER_BOUNDS = (2, 3, 5)
for bound in INNER_BOUNDS:
    add("ctl_while_lt_%d" % bound,
        "inner while -lt %d" % bound, "",
        "j=0; while [ $j -lt %d ]; do :; ((j++)); done; :" % bound, N_INNER)
    add("ctl_while_dbr_%d" % bound,
        "inner while [[ ]] %d" % bound, "",
        "j=0; while [[ $j -lt %d ]]; do :; ((j++)); done; :" % bound, N_INNER)
    add("ctl_until_ge_%d" % bound,
        "inner until %d" % bound, "",
        "j=0; until [ $j -ge %d ]; do :; ((j++)); done; :" % bound, N_INNER)
# while/until bodies with break/continue.
add("ctl_while_break", "inner while break", "",
    "j=0; while [ $j -lt 5 ]; do [ $j -eq 2 ] && break; :; ((j++)); done; :",
    N_INNER)
add("ctl_while_continue", "inner while continue", "",
    "j=0; while [ $j -lt 5 ]; do ((j++)); [ $j -eq 2 ] && continue; :; done; :",
    N_INNER)
add("ctl_until_arith", "inner until (( ))", "",
    "j=0; until ((j >= 4)); do :; ((j++)); done; :", N_INNER)
# for-in over literal lists of 1/3/8 items.
for nitems, items in ((1, "solo"), (3, "a b c"), (8, " ".join("w%d" % k for k in range(8)))):
    add("ctl_forin_lit%d" % nitems,
        "for-in literal %d items" % nitems, "",
        "for w in %s; do [ -n \"$w\" ] || :; done" % items, N_INNER)
    add("ctl_forin_case%d" % nitems,
        "for-in + case %d items" % nitems, "",
        "for w in %s; do case $w in w*) :;; *) :;; esac; done" % items,
        N_INNER)
# for-in over "${arr[@]}" at sizes 4/16/64.
for size in (4, 16, 64):
    fill = " ".join("e%d" % k for k in range(size))
    add("ctl_forin_arr%d" % size, "for-in arr[@] size %d" % size,
        "arr=(%s)" % fill,
        'for w in "${arr[@]}"; do [ -n "$w" ] || :; done', N_INNER)
# for-in over indices "${!arr[@]}".
add("ctl_forin_keys", "for-in arr keys", "arr=(a b c d)",
    'for k in "${!arr[@]}"; do :; done', N_INNER)
# case arm ladders: 2/4/8/16 arms, subject hitting mid arm.
for arms in (2, 4, 8, 16):
    mid = arms // 2
    pat_list = " ".join(
        "%d) :;;" % k if k != mid else "%d) :;;" % k for k in range(arms))
    add("ctl_case_arms%d" % arms, "case %d arms mid-hit" % arms, "",
        "case %d in %s *) :;; esac" % (mid, pat_list))
    # variant: subject misses all explicit arms -> default only
    add("ctl_case_arms%d_miss" % arms, "case %d arms default" % arms, "",
        "case 999 in %s *) :;; esac" % pat_list)
# ;& fall-through and ;;& test arms.
add("ctl_case_fall", "case ;& fallthrough", "",
    "case 1 in 1) :;& 2) :;& *) :;; esac")
add("ctl_case_fall2", "case ;& partial", "",
    "case 2 in 1) :;; 2) :;& 3) :;; *) :;; esac")
add("ctl_case_test", "case ;;& test arms", "",
    "case ab in a*) [ -n x ] && : ;;& b*) :;; *) :;; esac")
add("ctl_case_nested", "case nested", "",
    "case 1 in 1) case 2 in 2) :;; esac;; *) :;; esac")
# select statement (menu suppressed, stdin at EOF).
add("ctl_select_1", "select 1 item", "",
    "select x in solo; do break; done </dev/null 2>/dev/null")
add("ctl_select_3", "select 3 items", "",
    "select x in a b c; do [ -n \"$x\" ] || :; break; done </dev/null 2>/dev/null")
# { } vs ( ) groups.
add("ctl_group_brace", "{ } group", "",
    "{ if [ $__bs_i -lt 5000 ]; then :; fi; }")
add("ctl_group_sub", "( ) subshell group", "",
    "( if [ $__bs_i -lt 5000 ]; then :; fi )")
add("ctl_group_seq", "{ } sequence", "v=hello; u=",
    "{ [ -n \"$v\" ] && :; [ -z \"$u\" ] || :; }")
add("ctl_group_sub_var", "( ) var isolation", "DBG=x",
    "( DBG=y ); [ \"$DBG\" = x ] || :")
# ! negation forms.
add("ctl_bang_test", "! [ ]", "", "! [ $__bs_i -lt 0 ] || :")
add("ctl_bang_arith", "! (( ))", "", "! ((__bs_i < 0)) || :")
add("ctl_bang_dbr", "! [[ ]]", "i=3; v=hello", "! [[ $v = world ]] || :")
add("ctl_bang_cmd", "! pipeline-ish", "", "! false || :")
# && / || short-circuit chains of length 2-4.
CHAINS = [
    ("[ $__bs_i -lt 5000 ] && [ -n v ] || :", "and2"),
    ("[ $__bs_i -lt 5000 ] && [ -n v ] && [ -z u ] || :", "and3"),
    ("false && : || :", "and-short-circuit"),
    ("true || false && : || :", "or-and-chain"),
    ("[ 1 -eq 1 ] && [ 2 -eq 2 ] && [ 3 -eq 3 ] && [ 4 -eq 4 ] || :", "and4"),
    ("[[ $v == h* ]] || [[ $v == w* ]] || :", "dbr-or2"),
    ("test -n \"$v\" && test -z \"$u\" || :", "test-and2"),
    ("((__bs_i >= 0)) && ((j = 1)) && : || :", "arith-and", "j=0"),
]
for row in CHAINS:
    body, name = row[0], row[1]
    setup = row[2] if len(row) > 2 else ("i=3; j=7; v=hello; u=" if "v" in body or "$v" in body else "")
    if "$__bs_i" in body or "__bs_i" in body:
        pass
    add("ctl_chain_%s" % name, "short-circuit %s" % name, setup, body)
# break / continue across nested for loops.
add("ctl_nested_break", "break inner for", "",
    "for a in 1 2; do for b in 1 2 3; do [ $b -eq 2 ] && break; done; done",
    N_INNER)
add("ctl_nested_continue", "continue inner for", "",
    "for a in 1 2; do for b in 1 2 3; do [ $b -eq 2 ] && continue; :; done; done",
    N_INNER)
add("ctl_nested_break2", "break outer via flag", "",
    "for a in 1 2; do for b in 1 2; do [ $b -eq 2 ] && break 2; done; done",
    N_INNER)
# Triple nesting: for x while x if.
add("ctl_tri_nest", "for>while>if", "",
    "j=0; for w in 1 2; do while [ $j -lt 3 ]; do if [ $j -eq 1 ]; then :; fi; "
    ":; ((j++)); done; j=0; done; :", N_INNER)

# ---------------------------------------------------------------------------
# 4. Read-only query forms (trap-adjacent, times, caller).
# ---------------------------------------------------------------------------
add("q_trap_list", "trap -p listing", "", "trap -p >/dev/null")
add("q_trap_list_sig", "trap -p specific", "", "trap -p EXIT >/dev/null 2>&1")
add("q_times", "times", "", "times >/dev/null")
add("q_caller", "caller in func", "f() { caller 0 >/dev/null; }", "f")
add("q_caller_nested", "caller nested funcs",
    "g() { caller 0 >/dev/null; }; f() { g; }", "f")

# ---------------------------------------------------------------------------
# 5. Script-kind replays of realistic control-flow shapes.
# ---------------------------------------------------------------------------
SCRIPT_ROWS = [
    ("nested_counters", "nested for counters",
     "n=0\n"
     "for ((i=0; i<{iters}; i++)); do\n"
     "    for ((j=0; j<3; j++)); do ((n++)); done\n"
     "done\n"),
    ("case_state_machine", "case-driven state machine",
     "state=0\n"
     "for ((i=0; i<{iters}; i++)); do\n"
     "    case $((i % 4)) in\n"
     "        0) state=$((state+1));;\n"
     "        1) state=$((state+2));;\n"
     "        2) [ $state -gt 100 ] && state=0;;\n"
     "        *) state=$((state-1));;\n"
     "    esac\n"
     "done\n"),
    ("elif_ladder", "if/elif dispatch ladder",
     "acc=0\n"
     "for ((i=0; i<{iters}; i++)); do\n"
     "    m=$((i % 5))\n"
     "    if [ $m -eq 0 ]; then acc=$((acc+1))\n"
     "    elif [ $m -eq 1 ]; then acc=$((acc+2))\n"
     "    elif [ $m -eq 2 ]; then acc=$((acc+3))\n"
     "    elif [ $m -eq 3 ]; then acc=$((acc+4))\n"
     "    else acc=$((acc+5)); fi\n"
     "done\n"),
    ("while_dbracket", "while [[ ]] inner while",
     "i=0\n"
     "while [[ $i -lt {iters} ]]; do\n"
     "    j=0\n"
     "    while [ $j -lt 2 ]; do :; ((j++)); done\n"
     "    ((i++))\n"
     "done\n"),
    ("forin_arr_case", "for-in array + case",
     "arr=(red green blue)\n"
     "hits=0\n"
     "for ((i=0; i<{iters}; i++)); do\n"
     "    for c in \"${arr[@]}\"; do\n"
     "        case $c in\n"
     "            g*) hits=$((hits+1));;\n"
     "            *) :;;\n"
     "        esac\n"
     "    done\n"
     "done\n"),
    ("until_dispatch", "until + &&/|| dispatch",
     "i={iters}\n"
     "until [ $i -le 0 ]; do\n"
     "    [ $i -gt 500 ] && i=$((i-7)) || i=$((i-1))\n"
     "done\n"),
]


def cases() -> list:
    out = []
    for suffix, title, setup, body, iters, extra, files in ROWS:
        if suffix.startswith(("tint_", "tstr_", "tuna_")):
            sid = "hotloop.cond_%s" % suffix
        elif suffix.startswith(("bint_", "bstr_")):
            sid = "hotloop.cond_%s" % suffix
        elif suffix.startswith("dbr_"):
            sid = "hotloop.cond_%s" % suffix
        elif suffix.startswith("ctl_"):
            sid = "hotloop.ctrl_%s" % suffix
        else:
            sid = "hotloop.ctrl_%s" % suffix
        out.append(Case(
            id=sid,
            title="hotloop %s" % title,
            category="hotloop",
            tags=("hotloop", "generated", "v2") + extra,
            setup=setup, body=body, iters=iters, files=files))
    for suffix, title, body in SCRIPT_ROWS:
        out.append(Case(
            id="hotloop.script_cond_%s" % suffix,
            title="hotloop script %s" % title, category="hotloop",
            kind="script", tags=("hotloop", "generated", "v2"),
            body=body, iters=N))
    return out
