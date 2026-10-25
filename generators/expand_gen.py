"""Parameter-expansion matrix generator.

One table row per expansion form; each row becomes a loop case that
evaluates the form against a representative value. Substring/pattern forms
additionally run at two string scales (short / long) because several
engines change strategy with length.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

_SHORT = "alpha_beta_gamma.txt"
_LONG = "prefix_alpha_beta_gamma_delta_epsilon_zeta_eta_theta_iota.tar.gz"

# (suffix, title, setup, expression) -- expression may use {S} for the string
FORMS = [
    ("plain", "plain $v", "v=hello", "$v"),
    ("braced", "braced ${v}", "v=hello", "${v}"),
    ("length_str", "${#v} string length", "v=hello_world", "${#v}"),
    ("length_arr", "${#a[@]} array length", "a=(1 2 3 4 5 6 7 8)", "${#a[@]}"),
    ("default_unset", "${u:-def} unset", "", "${u:-fallback}"),
    ("default_set", "${v:-def} set", "v=value", "${v:-fallback}"),
    ("default_assign", "${u:=def}", "", "${u:=fallback}"),
    ("default_err_ok", "${v:?} set", "v=value", "${v:?boom}"),
    ("alt_set", "${v:+alt} set", "v=value", "${v:+alt}"),
    ("alt_unset", "${u:+alt} unset", "", "${u:+alt}"),
    ("substr", "${v:2:4} substring", "v={S}", "${v:2:4}"),
    ("substr_neg", "${v: -3} negative offset", "v={S}", "${v: -3}"),
    ("substr_from", "${v:5} from offset", "v={S}", "${v:5}"),
    ("prefix_rm_short", "${v#*/} shortest prefix", "v=a/b/c/file", "${v#*/}"),
    ("prefix_rm_long", "${v##*/} longest prefix", "v=a/b/c/file", "${v##*/}"),
    ("suffix_rm_short", "${v%.*} shortest suffix", "v={S}", "${v%.*}"),
    ("suffix_rm_long", "${v%%.*} longest suffix", "v={S}", "${v%%.*}"),
    ("replace_first", "${v/x/y} first", "v={S}", "${v/beta/BETA}"),
    ("replace_all", "${v//x/y} all", "v={S}", "${v//a/A}"),
    ("replace_prefix", "${v/#pre} anchored head", "v={S}", "${v/#prefix/PRE}"),
    ("replace_suffix", "${v/%suf} anchored tail", "v={S}", "${v/%.gz/.zip}"),
    ("upper_first", "${v^} upper first", "v={S}", "${v^}"),
    ("upper_all", "${v^^} upper all", "v={S}", "${v^^}"),
    ("lower_first", "${v,} lower first", "v=ALPHA_beta", "${v,}"),
    ("lower_all", "${v,,} lower all", "v=ALPHA_BETA", "${v,,}"),
    ("indirect", "${!n} indirect", "n=v; v=target", "${!n}"),
    ("nameref_read", "nameref read", "v=target; declare -n r=v", "$r"),
    ("positional", "$1 positional", "set -- aa bb cc", "$1"),
    ("special_status", "$? status", "true", "$?"),
    ("special_pid", "$$ pid", "", "$$"),
    ("special_opts", "$- flags", "", "$-"),
    ("special_argc", "$# argc", "set -- a b c", "$#"),
    ("at_join", '"${a[@]}" join-read', "a=(aa bb cc dd)", "${a[@]}"),
    ("at_elem", "${a[2]} element", "a=(aa bb cc dd ee)", "${a[2]}"),
    ("star_join", '"${a[*]}" star', "a=(aa bb cc dd)", "${a[*]}"),
    ("keys", "${!a[@]} indices", "a=(aa bb cc dd ee)", "${!a[@]}"),
    ("assoc_read", "assoc ${m[k]}", "declare -A m=([k1]=v1 [k2]=v2 [k3]=v3)", "${m[k2]}"),
    ("assoc_keys", "${!m[@]} assoc keys", "declare -A m=([k1]=v1 [k2]=v2)", "${!m[@]}"),
    ("quoted_at_len", '"${#a[@]}" quoted', "a=(1 2 3)", "${#a[@]}"),
]


def cases() -> list:
    out = []
    for suffix, title, setup, expr in FORMS:
        scales = [("s", _SHORT), ("l", _LONG)] if "{S}" in setup + expr \
            else [("", None)]
        for tag, s in scales:
            st = setup.replace("{S}", s or "")
            ex = expr.replace("{S}", s or "")
            cid = "expand.param_%s%s" % (suffix, ("_" + tag) if tag else "")
            out.append(Case(
                id=cid, title="parameter expansion: " + title,
                category="expand", tags=("expand", "generated"),
                setup=st, body="x=%s" % ex, iters=5000))
    return out
