"""Expansion & data-shape deep-matrix hot-loop generator (exp2 family).

Companion to ``hotloop_gen.py``: same ``for ((__bs_i=0; …))`` wrapper and
iter ladder, but aimed at expansion/data-shape depth rather than the
operator x value x consume matrix hotloop already covers:

- ``${var@transform}`` (bash 4.4+): @Q @E @P @A @a @K @k @L @U @u — every
  transform verified present in bash 5.3.20 — across unset/empty/short/
  phrase/glob/punct/path/quote/newline/utf8/long value shapes, in both
  assignment and echo-argument consume forms.
- Indirection: ``${!name}``, ``${!prefix@}``/``${!prefix*}``,
  ``${!arr[@]}``/``${!arr[*]}`` index lists, element-wise
  ``${arr[@]/pat/repl}`` substitution, ``${arr[@]@Q/@E/@K/@k}``,
  ``declare -n`` nameref chains, ``${var@Q}`` round-trips.
- Array deep ops: index arrays at sizes {4,64,256} x ~20 ops (subscript
  arithmetic, negative indices, slices incl. negative offsets, element-wise
  prefix/suffix/replace, quoted/unquoted iteration, bounded churn, unset
  element, declare -p); assoc arrays at the same sizes (key/value
  iteration, bounded churn, @K/@k listings, copies).
- String building: bounded ``+=`` growth, concat chains, ``IFS`` join
  variants, ``printf -v``, here-string ``read``, ``case`` and ``[[ == ]]``
  pattern matching incl. extglob.
- Glob/pathname expansion over a setup-created fixture tree: ``* ? [abc]
  [!a]``, extglob, globstar, dotglob, nullglob, locale-sorted variants,
  brace expansion, tilde and ANSI-C/locale quoting forms.
- Arithmetic-in-expansion: bases (``16#ff``, ``2#101``, ``8#10``),
  ``**``, array-element arithmetic, comma operator, assignment-in-expr,
  ternary.

Bodies are chosen so the last command exits 0 (``|| :`` guards on
conditionals); nothing accumulates unboundedly across iterations.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

N = 10000
N_SLOW = 2000   # command/process-substitution bodies
N_SPAWN = 500   # external-binary bodies

ROWS = []
_COUNT = {}


def add(area, slug, title, setup, body, iters=N, extra=(), env=(), files=()):
    ROWS.append((area, slug, title, setup, body, iters, extra, env, files))


def _cid(area, slug):
    key = (area, slug)
    n = _COUNT.get(key, 0) + 1
    _COUNT[key] = n
    return "exp2_%s_%s_%d" % (area, slug, n)


# ---------------------------------------------------------------------------
# 1. ${var@transform} — bash 4.4+ transform family x value shapes.
#    Transforms verified on bash 5.3.20: Q E P A a K k L U u all exist.
#    @K/@k emit key/value (assoc) or index/value (array) listings; on
#    scalars they quote like @Q.
# ---------------------------------------------------------------------------
TRANSFORMS = ("Q", "E", "P", "A", "a", "K", "k", "L", "U", "u")
XSHAPES = [
    ("unset",   "",                    "w"),
    ("empty",   "w=",                  "w"),
    ("short",   "w=hi",                "w"),
    ("digits",  "w=12345",             "w"),
    ("phrase",  "w='hello world'",     "w"),
    ("dblspace","w='a  b'",            "w"),
    ("glob",    "w='*.rs'",            "w"),
    ("punct",   "w='a*b?c[d]'",        "w"),
    ("path",    "w='/a/b/c d'",        "w"),
    ("squote",  'w="a\'b"',            "w"),
    ("nl",      "w=$'a\\nb'",          "w"),
    ("utf8",    "w='héllo wörld'",     "w"),
    ("long",    "w='" + "a" * 128 + "'", "w"),
]
for sname, ssetup, var in XSHAPES:
    for t in TRANSFORMS:
        for form, expr in (
            ("assign", "x=${%s@%s}" % (var, t)),
            ("echo",   'echo "${%s@%s}" >/dev/null' % (var, t)),
        ):
            add("xf", "%s_%s" % (sname, form),
                "@%s transform on %s (%s)" % (t, sname, form),
                ssetup, expr)

# ---------------------------------------------------------------------------
# 2. Indirection / nameref / element-wise substitution.
# ---------------------------------------------------------------------------
for sname, vsetup in (
    ("short", "v=hello"),
    ("phrase", "v='a b c'"),
    ("nl", "v=$'x\\ny'"),
):
    add("ind", "name_" + sname, "${!vn} on %s" % sname,
        vsetup + "; vn=v", "x=${!vn}")
    add("ind", "name_echo_" + sname, "echo ${!vn} on %s" % sname,
        vsetup + "; vn=v", "echo ${!vn} >/dev/null")
add("ind", "name_default", "${!vn:-DEF} unset target",
    "vn=nosuchvar", "x=${!vn:-DEF}")
add("ind", "name_default_set", "${!vn:-DEF} set target",
    "v=hello; vn=v", "x=${!vn:-DEF}")

# prefix expansion ${!prefix@} / ${!prefix*}
add("ind", "prefix_at_count", "${!p@} name list",
    "pa=1 pb=2 pc=3 pd=4", "n=0; for y in ${!p@}; do ((n++)); done")
add("ind", "prefix_star_argv", "set -- ${!p*}",
    "pa=1 pb=2 pc=3 pd=4", "set -- ${!p*}; x=$#")
add("ind", "prefix_nomatch", "${!zz@} no match",
    "pa=1", "set -- ${!zz@}; x=$#")

# index-list expansion ${!arr[@]} / ${!arr[*]}
IA_SETUP = "ia=(aa bb cc dd)"
add("ind", "idxlist_at", "${!ia[@]} indices",
    IA_SETUP, "x=${!ia[@]}")
add("ind", "idxlist_star", "set -- ${!ia[*]}",
    IA_SETUP, "set -- ${!ia[*]}; x=$#")
add("ind", "idxlist_loop", "for i in ${!ia[@]}",
    IA_SETUP, "n=0; for i in ${!ia[@]}; do x=$i; ((n++)); done")

# element-wise pattern substitution on arrays (bash 4.4+ for @-subscript forms)
EA_SETUP = "a=(aa ab ba ca abc axb)"
for slug, expr in (
    ("ew_first",   'b=("${a[@]/a/X}")'),
    ("ew_prefix",  'b=("${a[@]/#/P}")'),
    ("ew_suffix",  'b=("${a[@]/%/S}")'),
    ("ew_allpat",  'b=("${a[@]/*/Z}")'),
    ("ew_pat",     'b=("${a[@]/a*/Q}")'),
    ("ew_pat2",    'b=("${a[@]/?b/R}")'),
    ("ew_q",       'b=("${a[@]@Q}")'),
    ("ew_e",       'b=("${a[@]@E}")'),
    ("ew_k",       'b=("${a[@]@K}")'),
    ("ew_k_low",   'b=("${a[@]@k}")'),
    ("ew_u",       'x=${a[@]@U}'),
):
    add("ind", slug, "element-wise %s" % slug, EA_SETUP, expr)

# namerefs (declare -n)
add("ind", "nameref_basic", "declare -n nr=v; x=$nr",
    "declare -n nr=v; v=hello", "x=$nr")
add("ind", "nameref_echo", "echo $nr",
    "declare -n nr=v; v=hello", "echo $nr >/dev/null")
add("ind", "nameref_chain", "n2 -> n1 -> v chain",
    "v=hi; declare -n n1=v; declare -n n2=n1", "x=$n2")
add("ind", "nameref_elem", "nameref to array element",
    "declare -a aa=(10 20 30); declare -n ne=aa[1]", "x=$ne")
add("ind", "nameref_elem_set", "write through nameref",
    "declare -a aa=(10 20 30); declare -n ne=aa[1]", "ne=99; x=${aa[1]}")

# ${var@Q} round-trips through eval
for sname, vsetup in (("space", "v='a b'"), ("quote", 'v="a\'b"'),
                      ("nl", "v=$'x\\ny'")):
    add("ind", "qround_" + sname, "@Q roundtrip %s" % sname,
        vsetup, 'q=${v@Q}; eval "y=$q"')

# ---------------------------------------------------------------------------
# 3. Index arrays: sizes {4,64,256} x op ladder.
# ---------------------------------------------------------------------------
ARR_OPS = [
    ("read_mod",   "x=${a[__bs_i % SIZE]}"),
    ("read_first", "x=${a[0]}"),
    ("read_last",  "x=${a[-1]}"),
    ("len_at",     "x=${#a[@]}"),
    ("len_star",   "x=${#a[*]}"),
    ("copy_at",    'b=("${a[@]}")'),
    ("copy_star",  'b=("${a[*]}")'),
    ("slice",      'b=("${a[@]:1:2}")'),
    ("slice_neg",  'b=("${a[@]: -2}")'),
    ("slice_from", 'b=("${a[@]:2}")'),
    ("pfx",        'b=("${a[@]/#/P}")'),
    ("sfx",        'b=("${a[@]/%/S}")'),
    ("repl",       'b=("${a[@]/w/X}")'),
    ("iter_q",     'for y in "${a[@]}"; do :; done'),
    ("iter_uq",    "for y in ${a[@]}; do :; done"),
    ("churn",      "a[$((__bs_i % SIZE))]=$__bs_i"),
    ("elem_set",   "a[0]=$__bs_i"),
    ("unset_elem", "unset 'a[1]'"),
    ("declare_p",  "declare -p a >/dev/null"),
    ("klist",      'b=("${a[@]@K}")'),
    ("klist_u",    'b=("${a[@]@k}")'),
    ("join_star",  'IFS=:; x="${a[*]}"'),
]
for size in (4, 64, 256):
    fill = " ".join("w%d" % k for k in range(size))
    setup_f = "a=(%s)" % fill
    for slug, expr in ARR_OPS:
        body = expr.replace("SIZE", str(size))
        add("arr", "%s_%d" % (slug, size),
            "array %s size %d" % (slug, size), setup_f, body)
    # literal (re)fill measured per-iteration
    add("arr", "fill_%d" % size, "array literal fill size %d" % size,
        "a=()", "a=(%s)" % fill)

# ---------------------------------------------------------------------------
# 4. Assoc arrays: sizes {4,64,256} x op ladder.
# ---------------------------------------------------------------------------
ASSOC_OPS = [
    ("read",      "x=${h[k0]}"),
    ("read_dyn",  "kk=k$((__bs_i % SIZE)); x=${h[$kk]}"),
    ("len",       "x=${#h[@]}"),
    ("keys",      'for k in "${!h[@]}"; do :; done'),
    ("vals",      'for v in "${h[@]}"; do :; done'),
    ("churn",     "h[k$((__bs_i % SIZE))]=$__bs_i"),
    ("declare_p", "declare -p h >/dev/null"),
    ("klist",     'b=("${h[@]@K}")'),
    ("klist_u",   'b=("${h[@]@k}")'),
    ("copy_vals", 'b=("${h[@]}")'),
    ("copy_keys", 'b=("${!h[@]}")'),
]
for size in (4, 64, 256):
    fill = " ".join("[k%d]=v%d" % (k, k) for k in range(size))
    setup_f = "declare -A h=(%s)" % fill
    for slug, expr in ASSOC_OPS:
        body = expr.replace("SIZE", str(size))
        add("assoc", "%s_%d" % (slug, size),
            "assoc %s size %d" % (slug, size), setup_f, body)
    add("assoc", "fill_%d" % size, "assoc literal fill size %d" % size,
        "", "declare -A h=(%s)" % fill)

# ---------------------------------------------------------------------------
# 5. String building ladders.
# ---------------------------------------------------------------------------
add("str", "append_bounded", "s+=v with tail-trim",
    "v=abcdefgh; s=", "s+=$v; s=${s: -48}")
add("str", "concat4", "x=$a$b$c$d",
    "a=aa b=bb c=cc d=dd", "x=$a$b$c$d")
add("str", "concat5", "x=$v x5",
    "v=abcdefgh", "x=$v$v$v$v$v")
add("str", "substr_neg", "x=${s: -5}",
    "s='hello world'", "x=${s: -5}")
add("str", "replace_space", "x=${s// /_}",
    "s='hello world foo'", "x=${s// /_}")

# IFS join / split forms on a=(aa bb cc dd)
J_SETUP = "a=(aa bb cc dd)"
for slug, body in (
    ("ifs_colon",  'IFS=:; x="${a[*]}"'),
    ("ifs_space",  "IFS=' '; x=\"${a[*]}\""),
    ("ifs_default", 'x="${a[*]}"'),
    ("star_uq",    "set -- ${a[*]}; x=$#"),
    ("star_q",     'set -- "${a[*]}"; x=$#'),
    ("at_scalar",  "x=${a[@]}"),
    ("star_scalar", "x=${a[*]}"),
):
    add("str", slug, "IFS/join form %s" % slug, J_SETUP, body)

# printf -v / here-string / read
add("str", "printf_v", "printf -v capture",
    "v=hi", "printf -v x '%s|%d' \"$v\" $__bs_i")
add("str", "printf_v_arr", "printf -v over array",
    "a=(aa bb cc)", "printf -v x '%s,' \"${a[@]}\"")
add("str", "read_line", "read <<< herestring",
    "v='hello world'", 'read -r x <<< "$v"')
add("str", "read_ifs_arr", "IFS=: read -ra",
    "", "IFS=: read -ra b <<< 'x:y:z'")
add("str", "mapfile_hs", "mapfile <<< herestring",
    "v=line1", "mapfile -t b <<< \"$v\"")
add("str", "mapfile_ps", "mapfile < <(printf)",
    "", "mapfile -t b < <(printf 'p\\nq\\n')", N_SLOW)

# case / [[ == ]] pattern matching (guard last-cmd rc with || :)
add("str", "case_prefix", "case $s in h*)",
    "s='hello world'", "case $s in hello*) :;; *) :;; esac")
add("str", "case_multi", "case multi-arm",
    "s='hello world'", "case $s in x*) :;; h*) :;; *) :;; esac")
add("str", "dbracket_pre", "[[ $s == hello* ]]",
    "s='hello world'", "[[ $s == hello* ]] || :")
add("str", "dbracket_suf", "[[ $s == *world ]]",
    "s='hello world'", "[[ $s == *world ]] || :")
add("str", "dbracket_regex", "[[ $s =~ ^h.*d$ ]]",
    "s='hello world'", "[[ $s =~ ^h.*d$ ]] || :")
add("str", "dbracket_neg", "[[ ! $s == x* ]]",
    "s='hello world'", "[[ ! $s == x* ]] || :")
# extglob needs shopt -s extglob in setup
add("str", "extglob_at", "[[ == @(a|b) ]]",
    "shopt -s extglob; s='ab'", "[[ $s == @(a|b) ]] || :")
add("str", "extglob_q", "[[ == h?(e)llo* ]]",
    "shopt -s extglob; s='hello world'", "[[ $s == h?(e)llo* ]] || :")
add("str", "extglob_star", "[[ == *(wor)* ]]",
    "shopt -s extglob; s='hello world'", "[[ $s == *(wor)* ]] || :")
add("str", "extglob_plus", "[[ == +(hel|wor)* ]]",
    "shopt -s extglob; s='hello world'", "[[ $s == +(hel|wor)* ]] || :")
add("str", "extglob_bang", "[[ == !(x)* ]]",
    "shopt -s extglob; s='hello world'", "[[ $s == !(x)* ]] || :")

# ---------------------------------------------------------------------------
# 6. Glob / pathname expansion over a setup-created fixture tree.
# ---------------------------------------------------------------------------
TREE_SETUP = (
    "mkdir -p gx/d1 gx/d2; "
    ": > gx/a.txt; : > gx/b.log; : > gx/c.txt; : > gx/.hid; "
    ": > gx/d1/x.txt; : > gx/d1/y.log; : > gx/d2/z.txt"
)
for slug, pat in (
    ("star", "gx/*"),
    ("txt", "gx/*.txt"),
    ("quest", "gx/?.txt"),
    ("cls", "gx/[ab].*"),
    ("cls_neg", "gx/[!a].txt"),
    ("cls_range", "gx/[a-c].*"),
    ("sub_glob", "gx/d?/*.txt"),
    ("sub_one", "gx/d1/*.txt"),
    ("dotfiles", "gx/.*"),
    ("abs_mid", "gx/d1/../*.txt"),
):
    add("glob", slug, "glob %s" % pat, TREE_SETUP,
        "for f in %s; do :; done" % pat)
# shopt-gated glob forms
add("glob", "dotglob", "dotglob gx/*",
    TREE_SETUP + "; shopt -s dotglob", "for f in gx/*; do :; done")
add("glob", "globstar", "globstar gx/**/*.txt",
    TREE_SETUP + "; shopt -s globstar", "for f in gx/**/*.txt; do :; done")
add("glob", "globstar_q", "globstar gx/**/?.txt",
    TREE_SETUP + "; shopt -s globstar", "for f in gx/**/?.txt; do :; done")
add("glob", "nullglob", "nullglob gx/*.zzz",
    TREE_SETUP + "; shopt -s nullglob", "for f in gx/*.zzz; do :; done")
add("glob", "extglob_g", "extglob gx/@(a|b|c).*",
    TREE_SETUP + "; shopt -s extglob", "for f in gx/@(a|b|c).*; do :; done")
add("glob", "extglob_ng", "extglob gx/!(d?)*",
    TREE_SETUP + "; shopt -s extglob", "for f in gx/!(d?)*; do :; done")
# locale-sorted glob variants (sort order depends on LC_COLLATE)
add("glob", "sort_c", "glob gx/* LC_ALL=C",
    TREE_SETUP, "for f in gx/*; do :; done",
    env=(("LC_ALL", "C"),))
add("glob", "sort_utf8", "glob gx/* LC_ALL=C.UTF-8",
    TREE_SETUP, "for f in gx/*; do :; done",
    extra=("cap:utf8-locale",), env=(("LC_ALL", "C.UTF-8"),))
# brace expansion (command position only — assignment RHS does not expand)
add("glob", "brace_pair", "set -- {a,b}{1,2}",
    "", "set -- {a,b}{1,2}; x=$#")
add("glob", "brace_range", "set -- {1..5}",
    "", "set -- {1..5}; x=$#")
add("glob", "brace_nested", "set -- {a,{b,c}}",
    "", "set -- {a,{b,c}}; x=$#")
add("glob", "brace_loop", "for x in {1..4}{p,q}",
    "", "n=0; for x in {1..4}{p,q}; do ((n++)); done")
add("glob", "brace_assign_nx", "x={a,b} no brace-expand",
    "", "x={a,b}{1,2}")
# tilde expansion
add("glob", "tilde_home", "x=~ tilde expand",
    "", "x=~")
add("glob", "tilde_dir", "[ -d ~ ]",
    "", "d=~; [ -d \"$d\" ] || :")

# ---------------------------------------------------------------------------
# 7. Quoting forms: ANSI-C $'..', locale $"..", mixed quotes.
# ---------------------------------------------------------------------------
for slug, expr in (
    ("ansic_tab",  "x=$'a\\tb'"),
    ("ansic_hex",  "x=$'\\x41\\x42'"),
    ("ansic_nl",   "x=$'a\\nb'"),
    ("ansic_esc",  "x=$'a\\'b'"),
    ("dquote",     'x="a b c"'),
    ("squote",     "x='a b c'"),
    ("locale",     'x=$"hello world"'),
    ("mixed",      "x=a\"b c\"'d'e"),
):
    add("quote", slug, "quoting form %s" % slug, "", expr)
add("quote", "locale_utf8", "x=$\"héllo\" LC_ALL=C.UTF-8",
    "", 'x=$"héllo"', extra=("cap:utf8-locale",),
    env=(("LC_ALL", "C.UTF-8"),))
add("quote", "ansic_utf8", "x=$'h\\u00e9llo'",
    "", "x=$'h\\u00e9llo'", extra=("cap:utf8-locale",))

# ---------------------------------------------------------------------------
# 8. Arithmetic-in-expansion deep forms.
# ---------------------------------------------------------------------------
ARITHX = [
    ("pow",        "x=$((2**10))", ""),
    ("hex",        "x=$((16#ff))", ""),
    ("hex_var",    "x=$((16#$h))", "h=ff"),
    ("bases",      "x=$((2#101 + 8#17))", ""),
    ("oct",        "x=$((8#10))", ""),
    ("hex_shift",  "x=$((16#FF >> 4))", ""),
    ("muladd",     "x=$((__bs_i * 3 + 1))", ""),
    ("mod",        "x=$((__bs_i % 7))", ""),
    ("nested",     "x=$((($v + 1) * 2))", "v=3"),
    ("paren",      "y=$(( (1 + 2) * (3 + 4) ))", ""),
    ("arrelem",    "x=$((a[2] + 1))", "a=(10 20 30 40)"),
    ("arrdyn",     "x=$((a[__bs_i % 4] + 1))", "a=(10 20 30 40)"),
    ("assign",     "y=$((x += 2))", "x=1"),
    ("comma",      "y=$(( (p=1, q=2, p+q) ))", ""),
    ("preinc",     "y=$((++c))", "c=0"),
    ("postinc",    "y=$((c++))", "c=0"),
    ("ternary",    "y=$((__bs_i < 5000 ? 1 : 0))", ""),
    ("bnot",       "y=$((~mask))", "mask=15"),
    ("lnot",       "y=$((!flag))", "flag=0"),
    ("neg",        "y=$((-base))", "base=42"),
]
for slug, expr, setup in ARITHX:
    add("arithx", slug, "arith-in-expansion %s" % slug, setup, expr)

# ---------------------------------------------------------------------------
# 9. Misc expansion edges.
# ---------------------------------------------------------------------------
add("misc", "at_scalar_first", "x=${a[@]} scalar ctx = elem0",
    "a=(aa bb cc)", "x=${a[@]}")
add("misc", "star_scalar_join", "x=${a[*]} scalar ctx = join",
    "a=(aa bb cc)", "x=${a[*]}")
add("misc", "idxlist_star_ind", "${!ia[*]} star form",
    "ia=(aa bb cc)", "set -- ${!ia[*]}; x=$#")
add("misc", "printf_v_elem", "printf -v into array elem",
    "declare -a pa=(0 0 0)", "printf -v 'pa[1]' '%s' hi; x=${pa[1]}")
add("misc", "declare_p_assoc", "declare -p assoc dump",
    "declare -A h=([k]=v)", "declare -p h >/dev/null")
add("misc", "typeset_p", "typeset -p var",
    "v=hi", "typeset -p v >/dev/null")

# ---------------------------------------------------------------------------
# 10. Fork-heavy (N_SLOW) and external-spawn (N_SPAWN) expansion bodies.
# ---------------------------------------------------------------------------
for slug, setup, body in (
    ("cs_printf", "v='hello world'", 'x=$(printf \'%s\' "$v")'),
    ("cs_echo_q", "v='hello world'", 'x=$(echo "$v")'),
    ("cs_echo_uq", "v='hello world'", "x=$(echo ${v})"),
    ("cs_split_arr", "v='a b c'", "b=($(echo \"$v\"))"),
    ("cs_nested", "v=hi", "x=$(echo $(echo $v))"),
):
    add("slow", slug, "comsub expand %s" % slug, setup, body, N_SLOW)

for slug, setup, body in (
    ("spawn_printf", "v=hi", '/usr/bin/printf \'%s\' "$v" >/dev/null'),
    ("spawn_echo", "v=hi", '/bin/echo "$v" >/dev/null'),
    ("spawn_echo_n", "", "/bin/echo -n x >/dev/null"),
    ("spawn_true", "", "/bin/true"),
    ("spawn_cat_hs", "v=hi", '/bin/cat <<< "$v" >/dev/null'),
):
    add("spawn", slug, "external spawn %s" % slug, setup, body, N_SPAWN,
        ("cap:posix-path",))


def cases() -> list:
    out = []
    for area, slug, title, setup, body, iters, extra, env, files in ROWS:
        out.append(Case(
            id=_cid(area, slug),
            title="hotloop-exp2 %s" % title,
            category="hotloop",
            tags=("hotloop", "generated", "v2") + tuple(extra),
            setup=setup, body=body, iters=iters,
            env=tuple(env), files=tuple(files)))
    return out
