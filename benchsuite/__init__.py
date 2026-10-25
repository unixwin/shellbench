"""benchsuite - a cross-platform benchmark suite for POSIX/Bash-style shells.

Zero-dependency (Python standard library only). The suite treats benchmark
cases as data, expands them through generators, and times any shell binary
with the same corpus: startup cost, parser throughput, expansions, builtins,
control flow, pipelines, substitutions, big-data ladders and mixed loads.

This package measures *performance only*. Correctness regression testing is
a separate concern and lives in the shells' own test suites.
"""

__version__ = "0.1.0"
