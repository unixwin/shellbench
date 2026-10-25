"""Benchmark case model.

A case is *data*: a shell snippet plus metadata. Three execution kinds:

- ``loop``    -- the body is wrapped in an in-shell counting loop and run
                 ``iters`` times inside one process; the metric is ns/op.
                 Setup runs once before the loop (inside the timed process,
                 but O(1) next to the loop).
- ``process`` -- each repetition launches the shell with ``argv`` (startup
                 family); the metric is wall time per launch.
- ``script``  -- setup+body are written to a file and run once per
                 repetition; ``iters`` is then the number of operations
                 the script performs (lines processed, elements touched),
                 used to derive throughput.

Placeholders substituted at compile time: ``{iters}``, ``{i}`` is *not*
available; loop bodies can read the loop counter as ``$__bs_i``.
File fixtures and env values may use ``{work}`` for the case workdir.
Fixture contents starting with ``@gen:`` are produced host-side by
:mod:`benchsuite.fixtures` (e.g. ``@gen:lines:100000``).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Case:
    id: str                       # unique, dotted: category.sub.name
    title: str
    category: str                 # top-level taxonomy node, e.g. "expand"
    body: str = ""                # shell snippet (the timed work)
    kind: str = "loop"            # loop | process | script
    setup: str = ""               # shell code run before the timed region
    epilogue: str = ""            # shell code run after (e.g. checksum echo)
    iters: int = 1000             # loop iterations / ops for script kind
    argv: tuple = ()              # process kind: argument template
    env: tuple = ()               # ((key, value), ...) extra environment
    files: tuple = ()             # ((relpath, content), ...) fixtures
    tags: tuple = ()
    timeout: float = 180.0        # per-repetition timeout, seconds
    expect_rc: int = 0            # sanity guard: expected exit status
    expect_out: str = ""          # optional regex checked on a verify run
    autorange: bool = True        # loop kind: scale iters toward ~200 ms

    def with_iters(self, iters: int) -> "Case":
        return Case(**{**self.__dict__, "iters": iters})


@dataclass
class CaseResult:
    id: str
    title: str
    category: str
    kind: str
    iters: int                    # final iterations/ops actually timed
    runs_ns: list                 # wall time per repetition, nanoseconds
    status: str = "ok"            # ok | error | timeout | verify-failed
    error: str = ""
    verified: bool = False

    @property
    def median_ns(self) -> float:
        import statistics
        return statistics.median(self.runs_ns) if self.runs_ns else float("nan")

    @property
    def min_ns(self) -> float:
        return min(self.runs_ns) if self.runs_ns else float("nan")

    @property
    def p95_ns(self) -> float:
        if not self.runs_ns:
            return float("nan")
        s = sorted(self.runs_ns)
        import math
        return s[max(0, math.ceil(0.95 * len(s)) - 1)]

    @property
    def ns_per_op(self) -> float:
        if self.kind == "process":
            return self.median_ns
        return self.median_ns / self.iters if self.iters else float("nan")

    @property
    def ops_per_s(self) -> float:
        npo = self.ns_per_op
        return 1e9 / npo if npo and npo == npo and npo > 0 else float("nan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "kind": self.kind,
            "iters": self.iters,
            "status": self.status,
            "error": self.error,
            "verified": self.verified,
            "runs_ns": self.runs_ns,
            "min_ns": self.min_ns,
            "median_ns": self.median_ns,
            "p95_ns": self.p95_ns,
            "ns_per_op": self.ns_per_op,
            "ops_per_s": self.ops_per_s,
        }
