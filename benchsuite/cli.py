"""benchsuite command line.

  bench.py list   [--category C] [--tag T]           -- enumerate cases
  bench.py run    --shell PATH [--out DIR] [filters] -- time one shell
  bench.py compare NEW.json --baseline OLD.json      -- regression diff
  bench.py gap    SUBJECT.json REFERENCE.json        -- tiered gap table

``run`` writes <stamp>-<shellname>.{json,csv,md} into the output dir.
"""

from __future__ import annotations

import argparse
import datetime
import os
import re
import sys

from . import __version__
from .report import (compare, dump_csv, dump_json, dump_markdown, flag_rows,
                     gap_tiers, load_json)
from .runner import Runner, host_meta, shell_version


def load_cases() -> list:
    from cases import CASES  # top-level package next to benchsuite/
    seen, out = set(), []
    for c in CASES:
        if c.id in seen:
            raise SystemExit("duplicate case id: %s" % c.id)
        seen.add(c.id)
        out.append(c)
    return out


def _filter(cases, args):
    if getattr(args, "category", None):
        cases = [c for c in cases if c.category == args.category]
    if getattr(args, "tag", None):
        cases = [c for c in cases if args.tag in c.tags]
    if getattr(args, "filter", None):
        rx = re.compile(args.filter)
        cases = [c for c in cases if rx.search(c.id)]
    return cases


def cmd_list(args) -> int:
    cases = _filter(load_cases(), args)
    by_cat = {}
    for c in cases:
        by_cat.setdefault(c.category, []).append(c)
    for cat in sorted(by_cat):
        print("%s (%d)" % (cat, len(by_cat[cat])))
        for c in sorted(by_cat[cat], key=lambda x: x.id):
            print("  %-46s %-7s %s" % (c.id, c.kind, c.title))
    print("total: %d cases" % len(cases))
    return 0


def cmd_run(args) -> int:
    cases = _filter(load_cases(), args)
    if args.limit:
        cases = cases[:args.limit]
    shell = os.path.abspath(args.shell)
    if not os.path.isfile(shell):
        print("shell not found: %s" % shell, file=sys.stderr)
        return 2
    name = args.name or os.path.basename(shell)
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    meta = {"tool": "benchsuite %s" % __version__, "shell": shell,
            "shell_name": name, "shell_version": shell_version(shell),
            "started": datetime.datetime.now().isoformat(timespec="seconds"),
            "reps": args.reps, "warmup": args.warmup, **host_meta()}
    runner = Runner(shell, reps=args.reps, warmup=args.warmup)
    if args.verify_only:
        bad = 0
        for i, case in enumerate(cases, 1):
            r = runner.verify_case(case)
            if r.status != "ok":
                bad += 1
                print("[%d/%d] %-46s %-13s %s" % (i, len(cases), r.id,
                      r.status, r.error), flush=True)
        print("verify-only: %d ok / %d total" % (len(cases) - bad,
                                                 len(cases)))
        return 1 if bad else 0
    results = []
    for i, case in enumerate(cases, 1):
        r = runner.run_case(case)
        results.append(r)
        print("[%d/%d] %-46s %-13s %s" % (
            i, len(cases), r.id, r.status,
            ("%.0f ns/op" % r.ns_per_op) if r.status == "ok" else r.error),
            flush=True)
    os.makedirs(args.out, exist_ok=True)
    base = os.path.join(args.out, "%s-%s" % (stamp, name))
    with open(base + ".json", "w", encoding="utf-8") as f:
        f.write(dump_json(meta, results))
    with open(base + ".csv", "w", encoding="utf-8") as f:
        f.write(dump_csv(results))
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write(dump_markdown(meta, results))
    ok = sum(1 for r in results if r.status == "ok")
    print("wrote %s.{json,csv,md}  (%d ok / %d total)" % (base, ok, len(results)))
    if args.save_baseline:
        with open(args.save_baseline, "w", encoding="utf-8") as f:
            f.write(dump_json(meta, results))
        print("baseline saved: %s" % args.save_baseline)
    return 0 if ok else 1


def _load(path):
    with open(path, encoding="utf-8") as f:
        return load_json(f.read())


def cmd_compare(args) -> int:
    rows = flag_rows(compare(_load(args.new), _load(args.baseline)),
                     args.threshold)
    bad = [r for r in rows if r["flag"] == "REGRESSION"]
    print("| case | baseline | new | delta | flag |")
    print("|---|---|---|---|---|")
    for r in sorted(rows, key=lambda x: -(x["delta_pct"] or 0)):
        print("| %s | %s | %s | %s | %s |" % (
            r["id"],
            "-" if r["base_ns"] is None else "%.0f" % r["base_ns"],
            "-" if r["new_ns"] is None else "%.0f" % r["new_ns"],
            "-" if r["delta_pct"] is None else "%+.1f%%" % r["delta_pct"],
            r["flag"]))
    print("regressions beyond %.1f%%: %d" % (args.threshold, len(bad)))
    return 1 if bad else 0


def cmd_gap(args) -> int:
    subj, ref = _load(args.subject), _load(args.reference)
    rows = compare(subj, ref)
    text = gap_tiers(rows, subj["meta"].get("shell_name", "subject"),
                     ref["meta"].get("shell_name", "reference"))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        print("wrote %s" % args.out)
    else:
        print(text)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="benchsuite")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("list")
    p.add_argument("--category")
    p.add_argument("--tag")
    p.set_defaults(fn=cmd_list)

    p = sub.add_parser("run")
    p.add_argument("--shell", required=True)
    p.add_argument("--name")
    p.add_argument("--out", default="results")
    p.add_argument("--reps", type=int, default=5)
    p.add_argument("--warmup", type=int, default=1)
    p.add_argument("--category")
    p.add_argument("--tag")
    p.add_argument("--filter")
    p.add_argument("--limit", type=int)
    p.add_argument("--verify-only", action="store_true",
                   help="run each case once, check status/output, no timing")
    p.add_argument("--save-baseline")
    p.set_defaults(fn=cmd_run)

    p = sub.add_parser("compare")
    p.add_argument("new")
    p.add_argument("--baseline", required=True)
    p.add_argument("--threshold", type=float, default=5.0)
    p.set_defaults(fn=cmd_compare)

    p = sub.add_parser("gap")
    p.add_argument("subject")
    p.add_argument("reference")
    p.add_argument("--out")
    p.set_defaults(fn=cmd_gap)

    args = ap.parse_args(argv)
    return args.fn(args)
