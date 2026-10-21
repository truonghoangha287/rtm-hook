"""Check rules over the trace graph. Each rule yields Findings; see RULES for the registry."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .graph import Graph

RULES: dict[str, tuple[str, str]] = {}  # id -> (default severity, summary)


def rule(rid: str, severity: str, summary: str):
    def deco(fn):
        RULES[rid] = (severity, summary)
        fn.rid = rid
        _FUNCS.append(fn)
        return fn
    return deco


_FUNCS: list = []


@dataclass
class Finding:
    rule: str
    severity: str
    subject: str  # node key / file the finding is about
    file: str
    line: int
    msg: str
    detail: str = ""  # extra fingerprint component (e.g. the dangling ID)

    @property
    def fingerprint(self) -> str:
        return f"{self.rule}|{self.subject}|{self.detail}"

    def text(self) -> str:
        return f"{self.severity} {self.rule} {self.file}:{self.line} {self.msg}"


@rule("DANGLING", "P0", "An artifact cites an ID that is defined nowhere")
def dangling(g: Graph):
    for n in g.nodes.values():
        seen = set()
        for k, ln in n.mentions:
            if k in g.nodes or k in seen or g.scanner.layer_of(k) is None:
                continue
            if any(s.startswith(k + "/") for s in seen):  # STORY-099/AC1 already covers STORY-099
                continue
            seen.add(k)
            yield Finding("DANGLING", "P0", n.key, n.file, ln,
                          f"{g.show(n.key)} cites {g.syntax.show(k)}, which is not defined", k)


@rule("MISSING-UPSTREAM", "layer", "A node lacks a required upstream link (layer 'require')")
def missing_upstream(g: Graph):
    for lid, layer in g.cfg.layers.items():
        for group in layer.require:
            labels = " or ".join(
                x[1:] if x.startswith("@") else g.cfg.layers[x].label for x in group)
            for n in g.layer_nodes(lid):
                ok = any(
                    (n.attrs.get(x[1:]) if x.startswith("@")
                     else any(k in g.nodes for k in n.refs.get(x, ())))
                    for x in group)
                if not ok:
                    hint = f" (add a '{layer.ref_marker}' line)" if layer.ref_marker else ""
                    yield Finding("MISSING-UPSTREAM", layer.severity, n.key, n.file, n.line,
                                  f"{g.show(n.key)} has no {labels} reference{hint}",
                                  "+".join(group))


@rule("NOT-COVERED", "config", "A node has no downstream node in a target layer ('coverage')")
def not_covered(g: Graph):
    for c in g.cfg.coverage:
        target = g.cfg.layers[c["to"]].label
        for n in g.layer_nodes(c["from"]):
            if not g.descendants(n.key).get(c["to"]):
                yield Finding("NOT-COVERED", c.get("severity", "P3"), n.key, n.file, n.line,
                              f"{g.show(n.key)} has no {target} yet", c["to"])


def run(g: Graph, extra: list[Finding] | None = None) -> list[Finding]:
    out = list(extra or [])
    for fn in _FUNCS:
        out.extend(fn(g))
    order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    out.sort(key=lambda f: (order.get(f.severity, 9), f.file, f.line, f.rule))
    return out


# -- baseline -------------------------------------------------------------------
def baseline_path(root: Path) -> Path:
    return root / ".rtm" / "baseline.json"


def load_baseline(root: Path) -> set[str]:
    try:
        return set(json.loads(baseline_path(root).read_text())["fingerprints"])
    except (FileNotFoundError, KeyError, json.JSONDecodeError):
        return set()


def save_baseline(root: Path, findings: list[Finding]) -> Path:
    p = baseline_path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"fingerprints": sorted({f.fingerprint for f in findings})},
                            indent=1) + "\n")
    return p


def summary(findings: list[Finding]) -> dict[str, int]:
    out = {s: 0 for s in ("P0", "P1", "P2", "P3")}
    for f in findings:
        out[f.severity] = out.get(f.severity, 0) + 1
    return out


def as_json(findings: list[Finding], gate_fail: bool) -> str:
    return json.dumps({"pass": not gate_fail, "counts": summary(findings),
                       "findings": [asdict(f) | {"fingerprint": f.fingerprint} for f in findings]},
                      indent=1)
