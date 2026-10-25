# benchsuite

A cross-platform benchmark suite for Bash-style shells — the standard
yardstick every shell binary is measured with, the way redis-benchmark is
the yardstick for Redis. One corpus, one methodology, any binary:
rubash, GNU bash, a system shell — same cases, comparable numbers.

It exists to drive one goal: **beat GNU bash across the board**. The
suite's gap table is the optimisation queue; the baseline mode is the
regression gate.

Performance only — correctness regression testing lives in the shells'
own test suites, not here. Design: [DESIGN.md](DESIGN.md).

## Quick start

Requires Python 3.8+ (standard library only, nothing to install).

```sh
# enumerate the corpus
python3 bench.py list

# time a shell (writes results/<stamp>-<name>.{json,csv,md})
python3 bench.py run --shell /path/to/shell --name myshell

# tiered gap table: subject vs reference
python3 bench.py run --shell /path/to/gnu-bash --name gnu
python3 bench.py gap results/<stamp>-myshell.json results/<stamp>-gnu.json

# regression gate against a saved baseline (exit code != 0 on regressions)
python3 bench.py run --shell /path/to/shell --save-baseline base.json
python3 bench.py compare results/<new>.json --baseline base.json
```

Useful filters on `list`/`run`: `--category strings`, `--tag spawn`,
`--filter 'arrays\..*@1000'`, `--limit N`, `--reps N`, `--warmup N`.

## How it works

- **Cases are data** (`cases/`, one module per category): a shell
  snippet plus metadata — execution kind (`loop` / `process` / `script`),
  iteration count, fixtures, environment.
- **Generators** (`generators/`) expand compact spec tables into the
  bulk of the corpus: the full parameter-expansion matrix, one row per
  builtin, operators × evaluation contexts, data ladders
  (10 / 1k / 100k rows). Coverage grows by table rows, not by copying
  code.
- Every case is **verified before it is timed** (exit status + optional
  output regex): a fast wrong run is not data. Loop cases are
  auto-ranged toward ~200 ms per repetition; reports carry
  min / median / p95, ns-per-op and ops/s.
- Results record their own conditions (shell version string, platform,
  start-of-run load) — numbers without conditions are not quotable.

v1 corpus: **409 cases, 16 categories** — startup, parsing, parameter
expansion, arithmetic, builtins, strings, arrays, control flow,
functions, substitution, redirection, globbing, conditionals, jobs and
traps, big-data ladders, and realistic mixed scripts. The full taxonomy
and the growth roadmap live in [DESIGN.md](DESIGN.md).

## Discipline

Benchmark on a quiet machine (on this project's box: load < 2 and no
compiler running) or the numbers are noise. Never compare numbers
collected on different machines; re-baseline instead.
