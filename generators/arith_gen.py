"""Arithmetic matrix generator: operators x evaluation contexts.

Contexts: $(( )) expansion, (( )) command, let, for((;;)) header work,
and (( )) with assignment. Every operator row runs in the cheap contexts;
division/modulo guard against zero divisors by construction.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from benchsuite.model import Case  # noqa: E402

# (suffix, title, expression using a=17, b=5)
OPS = [
    ("add", "a + b", "a + b"),
    ("sub", "a - b", "a - b"),
    ("mul", "a * b", "a * b"),
    ("div", "a / b", "a / b"),
    ("mod", "a % b", "a % b"),
    ("pow", "a ** 3", "a ** 3"),
    ("shl", "a << 3", "a << 3"),
    ("shr", "a >> 2", "a >> 2"),
    ("band", "a & b", "a & b"),
    ("bor", "a | b", "a | b"),
    ("bxor", "a ^ b", "a ^ b"),
    ("bnot", "~a", "~a"),
    ("neg", "-a", "-a"),
    ("lt", "a < b", "a < b"),
    ("le", "a <= b", "a <= b"),
    ("gt", "a > b", "a > b"),
    ("eq", "a == b", "a == b"),
    ("ne", "a != b", "a != b"),
    ("land", "a && b", "a && b"),
    ("lor", "a || 0", "a || 0"),
    ("ternary", "a>b ? a : b", "a > b ? a : b"),
    ("preinc", "++c", "++c"),
    ("postinc", "c++", "c++"),
    ("predec", "--c", "--c"),
    ("assign_add", "c += a", "c += a"),
    ("assign_mul", "c *= b", "c *= b"),
    ("assign_mod", "c %= b", "c %= b"),
    ("comma", "a, b, a+b", "a, b, a + b"),
    ("nested", "((a+b)*(a-b))", "(a + b) * (a - b)"),
    ("func_free_mix", "mixed chain", "a * b + a % b - (a << 2)"),
]

SETUP = "a=17; b=5; c=3"


def cases() -> list:
    out = []
    for suffix, title, expr in OPS:
        out.append(Case(
            id="arith.expand_%s" % suffix, title="arith $(( )): " + title,
            category="arith", tags=("arith", "generated"),
            setup=SETUP, body="x=$(( %s ))" % expr, iters=8000))
        out.append(Case(
            id="arith.cmd_%s" % suffix, title="arith (( )): " + title,
            category="arith", tags=("arith", "generated"),
            setup=SETUP, body="(( x = %s ))" % expr, iters=8000))
    extra = [
        ("arith.let_chain", "let chain", "let 'x=a+b' 'y=x*2' 'z=y-a'", 5000),
        ("arith.for_header", "for((;;)) header arithmetic",
         "for ((j=0; j<10; j++)); do :; done", 2000),
        ("arith.subscript_expr", "array subscript expression",
         "x=${arr[a+b-2]}", 5000),
        ("arith.base2", "base#n literal 2#1010", "x=$(( 2#1010 + 16#ff ))", 5000),
        ("arith.octal_hex", "octal/hex literals", "x=$(( 077 + 0xff - 0b101 ))", 5000),
        ("arith.big", "64-bit multiply", "x=$(( 123456789 * 987654321 ))", 5000),
        ("arith.shift_chain", "shift chain", "x=$(( (a << 8 | b) >> 3 ))", 8000),
    ]
    setups = {"arith.subscript_expr": SETUP + "; arr=(0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22)"}
    for cid, title, body, iters in extra:
        out.append(Case(id=cid, title="arith: " + title, category="arith",
                        tags=("arith", "generated"),
                        setup=setups.get(cid, SETUP), body=body, iters=iters))
    return out
