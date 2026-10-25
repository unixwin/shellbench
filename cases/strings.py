"""String operations: building, joining, comparing, matching, regex."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402


def C(cid, title, body, iters=5000, setup="", kind="loop", **kw):
    return Case(id=cid, title=title, category="strings", body=body,
                setup=setup, iters=iters, kind=kind, tags=("strings",), **kw)


CASES = [
    C("strings.append_assign", "s+=chunk append", "s+=abcdef",
      setup="s=x"),
    C("strings.concat_subst", "s=$s$x concat", "s=$s$x",
      setup="s=x; x=chunk", iters=3000),
    C("strings.build_50k", "build 50k-char string by +=",
      "for ((j=0; j<10000; j++)); do s+=abcde; done; n=${#s}",
      kind="script", iters=10000, setup="s="),
    C("strings.join_default", "${a[*]} default join",
      "x=${a[*]}", setup="a=(aa bb cc dd ee ff gg hh)"),
    C("strings.join_ifs", "IFS=, join ${a[*]}",
      "x=$(IFS=,; echo ${a[*]})", setup="a=(aa bb cc dd ee)", iters=2000),
    C("strings.join_ifs_local", "local IFS join without subshell",
      "x=${a[*]}", setup="a=(aa bb cc dd ee); IFS=,", iters=5000),
    C("strings.compare_eq_loop", "[[ == ]] string compare",
      "[[ $a == $b ]]", setup="a=somevalue; b=somevalue"),
    C("strings.compare_lt_loop", "[[ < ]] lexicographic",
      "[[ $a < $b ]]", setup="a=apple; b=banana"),
    C("strings.pattern_prefix", "[[ == pat* ]] prefix match",
      "[[ $a == pre* ]]", setup="a=prefix_value_here"),
    C("strings.pattern_glob_mid", "[[ == *mid* ]] glob match",
      "[[ $a == *mid* ]]", setup="a=aa_mid_bb_cc"),
    C("strings.regex_simple", "[[ =~ ]] simple regex",
      "[[ $a =~ ^[a-z]+[0-9]+$ ]]", setup="a=abc123"),
    C("strings.regex_groups", "[[ =~ ]] capture groups + BASH_REMATCH",
      "[[ $a =~ ^([a-z]+)-([0-9]+)$ ]]; x=${BASH_REMATCH[2]}",
      setup="a=hostname-42", iters=3000),
    C("strings.regex_nomatch", "[[ =~ ]] non-matching",
      "[[ $a =~ ^z{3}[0-9]$ ]]", setup="a=abc123", iters=3000),
    C("strings.regex_alt", "[[ =~ ]] alternation",
      "[[ $a =~ ^(foo|bar|baz)[0-9]*$ ]]", setup="a=bar77", iters=3000),
    C("strings.trim_ws_param", "whitespace trim via patterns",
      "x=${a## }", setup="a='   spaced'", iters=3000),
    C("strings.case_conv_loop", "${v^^} on sentence",
      "x=${a^^}", setup="a='the quick brown fox'", iters=3000),
    C("strings.pad_printf", "printf padded field",
      "printf '%-24s|' $a >/dev/null", setup="a=word", iters=3000),
    C("strings.repeat_printf", "printf %*s width from arg",
      "printf '%*s' 40 '' >/dev/null", iters=3000),
]

# --- corpus v2 additions: Unicode / multibyte operations under
# C.UTF-8 (with C-locale contrast pairs) and length ladders (the
# op x length matrix itself lives in generators/v2_gen.py). Only
# C.utf8 exists on the reference box, so that is the locale used. ---
_UTF8 = (("LC_ALL", "C.UTF-8"),)
_CLOC = (("LC_ALL", "C"),)

_V2 = [
    C("strings.u_length_chars", "multibyte ${#s} under C.UTF-8",
      "x=${#s}", setup="s='café résumé naïve'", iters=5000, env=_UTF8),
    C("strings.u_length_bytes", "same string ${#s} under C (bytes)",
      "x=${#s}", setup="s='café résumé naïve'", iters=5000, env=_CLOC),
    C("strings.u_substr", "multibyte substring ${s:2:4}",
      "x=${s:2:4}", setup="s='aébc déf ghi'", iters=3000, env=_UTF8),
    C("strings.u_upper", "${s^^} with accented letters",
      "x=${s^^}", setup="s='café déjà vu'", iters=3000, env=_UTF8),
    C("strings.u_lower", "${s,,} with accented letters",
      "x=${s,,}", setup="s='CAFÉ DÉJÀ VU'", iters=3000, env=_UTF8),
    C("strings.u_pattern", "[[ == *word* ]] with multibyte word",
      "[[ $s == *résumé* ]]", setup="s='le résumé final'", iters=3000,
      env=_UTF8),
    C("strings.u_class_utf8", "[[:alpha:]] matches é under C.UTF-8",
      "[[ $w =~ ^[[:alpha:]]+$ ]]", setup="w='été'", iters=3000,
      env=_UTF8),
    C("strings.u_class_c", "[[:alpha:]] vs é bytes under C",
      "[[ $w =~ ^[[:alpha:]]+$ ]]", setup="w='été'", iters=3000,
      env=_CLOC),
    C("strings.u_replace", "${s//é/e} multibyte replace",
      "x=${s//é/e}", setup="s='café béret'", iters=3000, env=_UTF8),
    C("strings.u_emoji", "emoji string length + substring",
      "x=${s:1:3}; y=${#s}", setup="s='a😀b🎉cd'", iters=3000,
      env=_UTF8),
    C("strings.u_japanese_substr", "CJK substring ${s: -3}",
      "x=${s: -3}", setup="s='テストデータです'", iters=3000, env=_UTF8),
    C("strings.u_case_first", "${s^} on accented first letter",
      "x=${s^}", setup="s='élan vital'", iters=3000, env=_UTF8),
]

from dataclasses import replace as _replace  # noqa: E402

CASES += [_replace(c, tags=c.tags + ("v2",)) for c in _V2]
del _replace, _V2
