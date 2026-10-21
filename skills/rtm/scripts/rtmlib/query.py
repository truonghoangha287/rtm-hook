"""Answer questions from the trace graph so nobody has to read the matrix files.

  gaps    --step S --to T     nodes of S with no downstream node in T
  missing --step S            nodes of S failing their consumes rule
  list    --step S [--grep X] nodes of S (label / key / file matches X)

Every query returns rows of dicts; the CLI prints them as text or JSON with a limit.
"""
from __future__ import annotations

import re

from .checks import Finding
from .graph import Graph


def _row(g: Graph, k: str, **extra) -> dict:
    n = g.nodes[k]
    return {"id": g.show(k), "step": n.layer, "file": n.file, "line": n.line,
            "label": n.label[:80], **extra}


def gaps(g: Graph, step: str, to: str) -> list[dict]:
    return [_row(g, n.key) for n in g.layer_nodes(step) if not g.descendants(n.key).get(to)]


def missing(g: Graph, step: str, findings: list[Finding]) -> list[dict]:
    want = {n.key for n in g.layer_nodes(step)}
    out, seen = [], set()
    for f in findings:
        if f.rule == "MISSING-UPSTREAM" and f.subject in want and f.subject not in seen:
            seen.add(f.subject)
            out.append(_row(g, f.subject, problem=f.msg, severity=f.severity))
    return out


def list_(g: Graph, step: str, grep: str | None = None) -> list[dict]:
    rx = re.compile(grep, re.I) if grep else None
    out = []
    for n in g.layer_nodes(step):
        if rx and not (rx.search(n.label) or rx.search(g.show(n.key)) or rx.search(n.file)):
            continue
        ups = sorted(g.parents(n), key=g.show)
        out.append(_row(g, n.key, traces=", ".join(g.show(k) for k in ups)))
    return out
