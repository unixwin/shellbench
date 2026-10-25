"""Result I/O: JSON (canonical), CSV, Markdown; baseline comparison."""

from __future__ import annotations

import csv
import io
import json
import math


def dump_json(meta: dict, results: list) -> str:
    payload = {"meta": meta, "results": [r.to_dict() for r in results]}
    return json.dumps(payload, indent=1, ensure_ascii=False)


def load_json(text: str) -> dict:
    return json.loads(text)


def dump_csv(results: list) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "category", "title", "kind", "iters", "status",
                "min_ns", "median_ns", "p95_ns", "ns_per_op", "ops_per_s"])
    for r in results:
        d = r.to_dict() if hasattr(r, "to_dict") else r
        w.writerow([d["id"], d["category"], d["title"], d["kind"], d["iters"],
                    d["status"], _n(d["min_ns"]), _n(d["median_ns"]),
                    _n(d["p95_ns"]), _n(d["ns_per_op"]), _n(d["ops_per_s"])])
    return buf.getvalue()


def _n(x) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return ""
    return "%.1f" % x if isinstance(x, float) else str(x)


def _fmt_ns(ns: float) -> str:
    if ns != ns:
        return "-"
    if ns >= 1e6:
        return "%.2f ms" % (ns / 1e6)
    if ns >= 1e3:
        return "%.2f us" % (ns / 1e3)
    return "%.0f ns" % ns


def dump_markdown(meta: dict, results: list) -> str:
    lines = ["# benchsuite run", ""]
    for k in ("shell", "shell_version", "started", "platform", "reps",
              "warmup", "loadavg_at_start"):
        if k in meta:
            lines.append("- %s: %s" % (k, meta[k]))
    lines.append("")
    by_cat = {}
    for r in results:
        d = r.to_dict() if hasattr(r, "to_dict") else r
        by_cat.setdefault(d["category"], []).append(d)
    for cat in sorted(by_cat):
        lines.append("## %s" % cat)
        lines.append("")
        lines.append("| case | kind | iters | median | p95 | per-op | ops/s | status |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for d in sorted(by_cat[cat], key=lambda x: x["id"]):
            lines.append("| %s | %s | %s | %s | %s | %s | %s | %s |" % (
                d["id"], d["kind"], d["iters"], _fmt_ns(d["median_ns"]),
                _fmt_ns(d["p95_ns"]), _fmt_ns(d["ns_per_op"]),
                ("%.0f" % d["ops_per_s"]) if d["ops_per_s"] == d["ops_per_s"]
                else "-", d["status"]))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Baseline comparison / gap analysis
# ---------------------------------------------------------------------------

def compare(new: dict, base: dict) -> list:
    """Row per case present in either run, keyed on ns_per_op medians."""
    nmap = {r["id"]: r for r in new["results"]}
    bmap = {r["id"]: r for r in base["results"]}
    rows = []
    for cid in sorted(set(nmap) | set(bmap)):
        n, b = nmap.get(cid), bmap.get(cid)
        row = {"id": cid,
               "category": (n or b)["category"],
               "new_ns": n["ns_per_op"] if n else None,
               "base_ns": b["ns_per_op"] if b else None,
               "new_status": n["status"] if n else "missing",
               "base_status": b["status"] if b else "missing"}
        if n and b and n["status"] == "ok" and b["status"] == "ok":
            row["ratio"] = n["ns_per_op"] / b["ns_per_op"]
            row["delta_pct"] = (row["ratio"] - 1.0) * 100.0
        else:
            row["ratio"] = None
            row["delta_pct"] = None
        rows.append(row)
    return rows


def flag_rows(rows: list, threshold_pct: float = 5.0) -> list:
    """Annotate compare rows with regression/improvement flags."""
    for r in rows:
        if r["delta_pct"] is None:
            r["flag"] = "n/a"
        elif r["delta_pct"] > threshold_pct:
            r["flag"] = "REGRESSION"
        elif r["delta_pct"] < -threshold_pct:
            r["flag"] = "IMPROVED"
        else:
            r["flag"] = "same"
    return rows


def gap_tiers(rows: list, subject: str, reference: str,
              lead: float = 0.98, close: float = 1.10) -> str:
    """Tiered gap table: rows are compare(subject vs reference) rows where
    ratio = subject_time / reference_time (<1 means subject is faster)."""
    buckets = {"lead": [], "close": [], "behind": [], "na": []}
    for r in rows:
        if r["ratio"] is None:
            buckets["na"].append(r)
        elif r["ratio"] <= lead:
            buckets["lead"].append(r)
        elif r["ratio"] <= close:
            buckets["close"].append(r)
        else:
            buckets["behind"].append(r)
    total = sum(1 for r in rows if r["ratio"] is not None)
    lines = ["# Gap table: %s vs %s" % (subject, reference), "",
             "ratio = %s time / %s time (per-op median). <1.00 = %s faster."
             % (subject, reference, subject), "",
             "- **leading** (ratio <= %.2f): %d" % (lead, len(buckets["lead"])),
             "- **close** (%.2f < ratio <= %.2f): %d" % (lead, close, len(buckets["close"])),
             "- **behind** (ratio > %.2f): %d" % (close, len(buckets["behind"])),
             "- compared cases: %d, unmeasurable: %d" % (total, len(buckets["na"])),
             ""]
    # category rollup: median ratio per category
    from statistics import median
    by_cat = {}
    for r in rows:
        if r["ratio"] is not None:
            by_cat.setdefault(r["category"], []).append(r["ratio"])
    lines.append("## By category (median ratio)")
    lines.append("")
    lines.append("| category | cases | median ratio | reading |")
    lines.append("|---|---|---|---|")
    for cat in sorted(by_cat):
        m = median(by_cat[cat])
        reading = "leading" if m <= lead else ("close" if m <= close else "behind")
        lines.append("| %s | %d | %.3f | %s |" % (cat, len(by_cat[cat]), m, reading))
    lines.append("")
    for name, title in (("behind", "Behind (worst first)"),
                        ("close", "Close"),
                        ("lead", "Leading (best first)")):
        items = sorted(buckets[name],
                       key=lambda r: -r["ratio"] if name != "lead" else r["ratio"])
        lines.append("## %s" % title)
        lines.append("")
        lines.append("| case | category | %s | %s | ratio |" % (subject, reference))
        lines.append("|---|---|---|---|---|")
        for r in items:
            lines.append("| %s | %s | %s | %s | %.3f |" % (
                r["id"], r["category"], _fmt_ns(r["new_ns"]),
                _fmt_ns(r["base_ns"]), r["ratio"]))
        lines.append("")
    if buckets["na"]:
        lines.append("## Unmeasurable")
        lines.append("")
        for r in buckets["na"]:
            lines.append("- %s (%s: %s / %s: %s)" % (
                r["id"], subject, r["new_status"], reference, r["base_status"]))
        lines.append("")
    return "\n".join(lines)
