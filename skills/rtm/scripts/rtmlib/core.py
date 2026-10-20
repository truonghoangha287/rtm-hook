"""High-level operations shared by the CLI and the hooks."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from . import checks, render, state
from .checks import Finding
from .config import Config, load
from .graph import Graph


@dataclass
class Result:
    graph: Graph
    findings: list[Finding]
    changes: dict[str, tuple[int, int]] = field(default_factory=dict)  # block -> (+rows, -rows)
    discarded: list[str] = field(default_factory=list)  # hand-edited blocks overwritten
    wrote: bool = False


def _gen_edited(cfg: Config, text: str) -> list[Finding]:
    out = []
    for bid in render.edited_blocks(text):
        line = text[: text.find(f"rtm:begin {bid}")].count("\n") + 1
        out.append(Finding("GEN-EDITED", "P1", f"block:{bid}", cfg.rtm, line,
                           f"generated block '{bid}' was edited by hand; "
                           "change the source artifact and run `rtm sync`", bid))
    return out


def rtm_text(cfg: Config) -> str:
    p = cfg.root / cfg.rtm
    return p.read_text(encoding="utf-8") if p.exists() else ""


def check(cfg: Config) -> Result:
    g = Graph.build(cfg)
    return Result(g, checks.run(g, _gen_edited(cfg, rtm_text(cfg))))


def sync(cfg: Config, dry_run: bool = False) -> tuple[Result, str]:
    g = Graph.build(cfg)
    findings = checks.run(g)
    before = rtm_text(cfg)
    discarded = render.edited_blocks(before)
    bodies, titles = render.Renderer(g, findings).all()
    after, changes = render.splice(before, bodies, titles)
    wrote = False
    if after != before and not dry_run:
        path = cfg.root / cfg.rtm
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(after, encoding="utf-8")
        wrote = True
    if not dry_run:
        state.write_set(cfg.root, "last.json", {f.fingerprint for f in findings})
    return Result(g, findings, changes, discarded, wrote), after


def new_findings(root: Path, findings: list[Finding]) -> list[Finding]:
    base = checks.load_baseline(root)
    return [f for f in findings if f.fingerprint not in base]


def describe_changes(changes: dict[str, tuple[int, int]]) -> str:
    parts = [f"{b} +{a}/-{r}" for b, (a, r) in sorted(changes.items())]
    return ", ".join(parts)


__all__ = ["load", "check", "sync", "new_findings", "describe_changes", "Result"]
