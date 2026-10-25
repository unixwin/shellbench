"""Timing runner: warmup + repetitions, autorange, sanity verification.

Methodology (see DESIGN.md): every timed repetition is one process launch
measured with a monotonic nanosecond clock around the subprocess. A single
untimed *verify* run with captured output runs first; if the case exits
with an unexpected status or its output fails the case's regex, the case is
marked ``verify-failed`` and never timed (a fast wrong run is not data).
Loop cases are autoranged: a probe run scales the iteration count toward
~200 ms so per-op figures are not dominated by timer resolution.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
import time

from .compile import render_argv, render_script
from .fixtures import materialize
from .model import Case, CaseResult

TARGET_RUN_NS = 200_000_000       # autorange target: ~200 ms per repetition
MAX_AUTORANGE_FACTOR = 1000


class Runner:
    def __init__(self, shell: str, reps: int = 5, warmup: int = 1,
                 root: str | None = None):
        self.shell = shell
        self.reps = reps
        self.warmup = warmup
        self.root = root or tempfile.mkdtemp(prefix="benchsuite-")

    # -- one process launch -------------------------------------------------
    def _launch(self, argv, cwd, env, timeout, capture=False):
        kw = dict(cwd=cwd, env=env, timeout=timeout)
        if capture:
            kw.update(stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        else:
            kw.update(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                      stdin=subprocess.DEVNULL)
        t0 = time.perf_counter_ns()
        try:
            p = subprocess.run(argv, **kw)
            dt = time.perf_counter_ns() - t0
            out = p.stdout if capture else None
            return dt, p.returncode, out, None
        except subprocess.TimeoutExpired as e:
            return None, None, e.output, "timeout"

    # -- prepare a case's workdir / script / argv ---------------------------
    def _prepare(self, case: Case, workdir: str):
        os.makedirs(workdir, exist_ok=True)
        for rel, content in case.files:
            dest = os.path.join(workdir, rel.replace("{work}", workdir))
            os.makedirs(os.path.dirname(dest) or workdir, exist_ok=True)
            with open(dest, "w", encoding="utf-8") as f:
                f.write(materialize(content))
        script_path = None
        if case.kind in ("loop", "script") or "{script}" in case.argv:
            script_path = os.path.join(workdir, "case.sh")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(render_script(case))
        if case.kind == "process":
            argv = [self.shell] + render_argv(case, script_path, workdir)
        else:
            argv = [self.shell, script_path]
        env = dict(os.environ)
        env.setdefault("LC_ALL", "C")
        for k, v in case.env:
            env[k] = v.replace("{work}", workdir)
        return argv, env

    # -- run one case ---------------------------------------------------------
    def run_case(self, case: Case) -> CaseResult:
        workdir = os.path.join(self.root, case.id.replace("/", "_"))
        res = CaseResult(id=case.id, title=case.title, category=case.category,
                         kind=case.kind, iters=case.iters, runs_ns=[])
        try:
            argv, env = self._prepare(case, workdir)
        except Exception as e:  # fixture/compile errors are data too
            res.status, res.error = "error", "prepare: %s" % e
            return res

        # verify run (untimed, captured)
        _, rc, out, err = self._launch(argv, workdir, env, case.timeout,
                                       capture=True)
        if err:
            res.status, res.error = err, "verify run %s" % err
            return res
        res.verified = True
        if rc != case.expect_rc:
            res.status = "verify-failed"
            res.error = "rc=%s expected %s" % (rc, case.expect_rc)
            return res
        if case.expect_out:
            text = (out or b"").decode("utf-8", "replace")
            if not re.search(case.expect_out, text):
                res.status = "verify-failed"
                res.error = "output does not match %r" % case.expect_out
                return res
        return self._time(case, argv, env, workdir, res)

    def verify_case(self, case: Case) -> CaseResult:
        """Single captured run, no timing: corpus hygiene check."""
        res = CaseResult(id=case.id, title=case.title,
                         category=case.category, kind=case.kind,
                         iters=case.iters, runs_ns=[])
        workdir = os.path.join(self.root, case.id.replace("/", "_"))
        try:
            argv, env = self._prepare(case, workdir)
        except Exception as e:
            res.status, res.error = "error", "prepare: %s" % e
            return res
        _, rc, out, err = self._launch(argv, workdir, env, case.timeout,
                                       capture=True)
        if err:
            res.status, res.error = err, "verify run %s" % err
            return res
        res.verified = True
        if rc != case.expect_rc:
            res.status = "verify-failed"
            res.error = "rc=%s expected %s" % (rc, case.expect_rc)
            return res
        if case.expect_out:
            text = (out or b"").decode("utf-8", "replace")
            if not re.search(case.expect_out, text):
                res.status = "verify-failed"
                res.error = "output does not match %r" % case.expect_out
                return res
        res.status = "ok"
        return res

    def _time(self, case, argv, env, workdir, res):
        # autorange loop cases toward the target run length
        if case.kind == "loop" and case.autorange:
            dt, _, _, err = self._launch(argv, workdir, env, case.timeout)
            if err:
                res.status, res.error = err, "probe run %s" % err
                return res
            if dt and dt < TARGET_RUN_NS:
                factor = min(MAX_AUTORANGE_FACTOR,
                             max(1, TARGET_RUN_NS // max(dt, 1)))
                if factor > 1:
                    case = case.with_iters(case.iters * factor)
                    res.iters = case.iters
                    argv, env = self._prepare(case, workdir)

        # warmup (untimed), then timed repetitions
        for _ in range(self.warmup):
            _, _, _, err = self._launch(argv, workdir, env, case.timeout)
            if err:
                res.status, res.error = err, "warmup %s" % err
                return res
        for _ in range(self.reps):
            dt, rc, _, err = self._launch(argv, workdir, env, case.timeout)
            if err:
                res.status, res.error = err, "rep %s" % err
                res.runs_ns = []
                return res
            if rc != case.expect_rc:
                res.status = "verify-failed"
                res.error = "timed run rc=%s" % rc
                res.runs_ns = []
                return res
            res.runs_ns.append(dt)
        return res


def shell_version(shell: str) -> str:
    try:
        p = subprocess.run([shell, "--version"], stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, timeout=15)
        line = p.stdout.decode("utf-8", "replace").splitlines()
        return line[0].strip() if line else "unknown"
    except Exception as e:
        return "unknown (%s)" % e


def host_meta() -> dict:
    import platform
    meta = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "cpu_count": os.cpu_count(),
    }
    try:
        with open("/proc/loadavg") as f:
            meta["loadavg_at_start"] = f.read().strip()
    except OSError:
        pass
    return meta
