"""Compile a Case into an executable script / argv."""

from __future__ import annotations

from .model import Case


def render_script(case: Case) -> str:
    """Full script text for loop and script kinds (and process+{script})."""
    parts = []
    if case.setup:
        parts.append(case.setup.rstrip("\n"))
    if case.kind == "loop":
        parts.append(
            "for ((__bs_i=0; __bs_i<%d; __bs_i++)); do" % case.iters
        )
        if case.body:
            parts.append(case.body.rstrip("\n"))
        parts.append("done")
        parts.append("unset __bs_i")
    elif case.body:
        parts.append(case.body.rstrip("\n"))
    if case.epilogue:
        parts.append(case.epilogue.rstrip("\n"))
    text = "\n".join(parts) + "\n"
    return text.replace("{iters}", str(case.iters))


def render_argv(case: Case, script_path: str | None, workdir: str) -> list:
    argv = []
    for a in case.argv:
        a = a.replace("{work}", workdir)
        if a == "{script}":
            argv.append(script_path)
        else:
            argv.append(a.replace("{iters}", str(case.iters)))
    return argv
