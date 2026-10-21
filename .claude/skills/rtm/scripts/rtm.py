#!/usr/bin/env python3
"""rtm — a Requirements Traceability Matrix generated from, and checked against, your artifacts.

Ask (cheap — never read the matrix files to answer questions):
  why ID|PATH                         full chain up and down for one item
  query gaps    --step S --to T       items of S with nothing downstream in T
  query missing --step S              items of S failing their consumes rule
  query list    --step S [--grep RE]  items of S (+ what they trace to)
  stats                               counts per step
Maintain:
  sync [--dry-run|--diff]             rebuild the generated sections
  check [--json] [--gate] [--new] [--file PATH] [--limit N]
  baseline                            accept current findings as known debt
Flow:
  templates                           list shipped flow templates
  init --template T --set k=v … [--title X] [--force]
  flow show | flow check | flow apply [--yes] [--baseline]
  selftest [--json]                   run the generated contract suite against this flow

Root = --root, else nearest dir with rtm.config.json above cwd, else $CLAUDE_PROJECT_DIR.
Exit: 0 ok · 1 gate/selftest/flow-check failed · 2 usage or config error.
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rtmlib import checks, core, flow, query  # noqa: E402
from rtmlib.config import ConfigError, find_root, load, read_raw  # noqa: E402
from rtmlib.graph import Graph  # noqa: E402


def resolve_root(arg: str | None, must_exist: bool = True) -> Path:
    if arg:
        return Path(arg).resolve()
    starts = [Path.cwd()] + ([Path(os.environ["CLAUDE_PROJECT_DIR"])]
                             if os.environ.get("CLAUDE_PROJECT_DIR") else [])
    for start in starts:
        if r := find_root(start.resolve()):
            return r
    if not must_exist:
        return Path.cwd()
    raise ConfigError("no rtm.config.json found — run `rtm.py init --template …` or pass --root")


def emit(rows: list[dict], a, cols: list[str]) -> int:
    total = len(rows)
    rows = rows[: a.limit] if a.limit else rows
    if a.json:
        print(json.dumps({"total": total, "rows": rows}, indent=1, ensure_ascii=False))
        return 0
    for r in rows:
        print("  ".join(str(r.get(c, "")) for c in cols if r.get(c, "") != ""))
    if total > len(rows):
        print(f"… {total - len(rows)} more (use --limit 0 for all, or narrow with --grep)")
    print(f"{total} item(s)")
    return 0


# -- ask ---------------------------------------------------------------------------
def cmd_why(cfg, a) -> int:
    g = Graph.build(cfg)
    k = a.id
    if k not in g.nodes:
        rel = cfg.rel(k)
        hits = g.syntax.find(k)
        k = rel if rel in g.nodes else (max(hits, key=lambda h: h.key.count("/")).key if hits else k)
    n = g.nodes.get(k)
    if not n:
        print(f"{a.id}: not defined in any artifact of this flow")
        return 2
    print(f"{g.show(k)}  [{cfg.layers[n.layer].label}]  {n.file}:{n.line}  {n.label[:70]}")
    if src := g.source(n):
        print(f"  source: {src}")
    for title, groups in (("upstream", g.ancestors(k)), ("downstream", g.descendants(k))):
        print(f"  {title}:")
        if not groups:
            print("    (none)")
        for lid in cfg.order:
            ks = groups.get(lid)
            if ks:
                shown = [g.show(x) for x in ks]
                more = f" (+{len(shown) - a.limit})" if a.limit and len(shown) > a.limit else ""
                print(f"    {cfg.layers[lid].label:<8} {', '.join(shown[: a.limit or None])}{more}")
    return 0


def cmd_query(cfg, a) -> int:
    if a.step not in cfg.layers:
        print(f"unknown step '{a.step}' (steps: {', '.join(cfg.order)})", file=sys.stderr)
        return 2
    if a.kind == "gaps":
        if a.to not in cfg.layers:
            print(f"--to: unknown step '{a.to}'", file=sys.stderr)
            return 2
        return emit(query.gaps(Graph.build(cfg), a.step, a.to), a, ["id", "label", "file"])
    if a.kind == "missing":
        res = core.check(cfg)
        return emit(query.missing(res.graph, a.step, res.findings), a, ["id", "problem", "file", "line"])
    return emit(query.list_(Graph.build(cfg), a.step, a.grep), a, ["id", "label", "traces"])


def cmd_stats(cfg, a) -> int:
    g = Graph.build(cfg)
    for lid in cfg.order:
        nodes = g.layer_nodes(lid)
        links = sum(len(g.parents(n)) for n in nodes)
        print(f"{cfg.layers[lid].label:<10} {len(nodes):>5} items  {links:>6} upstream links")
    return 0


# -- maintain ----------------------------------------------------------------------
def cmd_sync(cfg, a) -> int:
    res, diffs = core.sync(cfg, dry_run=a.dry_run or a.diff)
    if a.diff:
        for rel, (old, new) in diffs.items():
            sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                                       rel, rel + " (synced)"))
        return 0
    verb = "would change" if a.dry_run else "updated"
    if diffs:
        print(f"{verb} {len(diffs)} file(s): {core.describe_changes(res.changes, 12)}")
        if res.removed:
            print(f"removed stale section file(s): {', '.join(res.removed)}")
    else:
        print("RTM already up to date")
    if res.discarded:
        print(f"note: overwrote hand edits in generated block(s): {', '.join(res.discarded)}")
    c = checks.summary(res.findings)
    print("findings: " + ", ".join(f"{k}={v}" for k, v in c.items()) + "  (rtm.py check for details)")
    return 0


def cmd_check(cfg, a) -> int:
    fs = core.check(cfg).findings
    if a.new:
        fs = core.new_findings(cfg.root, fs)
    if a.file:
        rel = cfg.rel(a.file) or a.file
        fs = [f for f in fs if f.file == rel]
    gate_fail = any(f.severity in ("P0", "P1") for f in fs)
    if a.json:
        print(checks.as_json(fs, gate_fail))
    else:
        for f in fs[: a.limit] if a.limit else fs:
            print(f.text())
        if a.limit and len(fs) > a.limit:
            print(f"… {len(fs) - a.limit} more")
        c = checks.summary(fs)
        print(("FAIL" if gate_fail else "PASS") + ": " + ", ".join(f"{k}={v}" for k, v in c.items()))
    return 1 if (a.gate and gate_fail) else 0


def cmd_baseline(cfg, a) -> int:
    fs = core.check(cfg).findings
    p = checks.save_baseline(cfg.root, fs)
    print(f"baseline: {len(fs)} finding(s) recorded in {p.relative_to(cfg.root)}")
    return 0


# -- flow --------------------------------------------------------------------------
def cmd_templates(a) -> int:
    for name, desc in flow.templates().items():
        print(f"{name:<18} {desc}")
    return 0


def cmd_init(a) -> int:
    root = resolve_root(a.root, must_exist=False)
    sets = dict(kv.split("=", 1) for kv in a.set)
    for m in flow.init(root, a.template, sets, a.title or root.name, a.force):
        print(m)
    cfg = load(root)
    warn = flow.doctor(cfg, Graph.build(cfg))
    for w in warn:
        print(f"warning: {w}")
    print("next: rtm.py flow show · rtm.py sync --diff · rtm.py sync · rtm.py baseline")
    return 0


def cmd_flow(cfg, a) -> int:
    g = Graph.build(cfg)
    if a.action == "show":
        print(flow.show(cfg, g))
        return 0
    warn = flow.doctor(cfg, g)
    for w in warn:
        print(f"warning: {w}")
    if a.action == "check":
        print("flow OK" + (f" with {len(warn)} warning(s)" if warn else ""))
        return 1 if warn and a.strict else 0
    # apply: preview -> confirm -> sync -> optional baseline
    res, diffs = core.sync(cfg, dry_run=True)
    print(f"would change {len(diffs)} file(s): {core.describe_changes(res.changes, 12) or '—'}")
    new = core.new_findings(cfg.root, res.findings)
    print(f"findings not in baseline: {len(new)}")
    if not a.yes and input("apply? [y/N] ").strip().lower() != "y":
        print("not applied")
        return 0
    core.sync(cfg)
    print("applied")
    if a.baseline:
        checks.save_baseline(cfg.root, res.findings)
        print(f"baseline updated ({len(res.findings)} findings)")
    return 0


def cmd_selftest(a) -> int:
    from rtmlib import contract
    root = resolve_root(a.root)
    cases = contract.run(read_raw(root))
    failed = [c for c in cases if not c.ok]
    if a.json:
        print(json.dumps({"pass": not failed, "cases": [c.__dict__ for c in cases]}, indent=1))
    else:
        for c in cases:
            print(f"{'PASS' if c.ok else 'FAIL'}  {c.name}" + (f"\n      {c.detail}" if not c.ok and c.detail else ""))
        print(f"{len(cases) - len(failed)}/{len(cases)} contract cases passed")
    return 1 if failed else 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="rtm", description=__doc__.split("\n")[1],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--root")
    sub = ap.add_subparsers(dest="cmd", required=True)
    w = sub.add_parser("why")
    w.add_argument("id")
    w.add_argument("--limit", type=int, default=30)
    q = sub.add_parser("query")
    q.add_argument("kind", choices=["gaps", "missing", "list"])
    q.add_argument("--step", required=True)
    q.add_argument("--to")
    q.add_argument("--grep")
    q.add_argument("--limit", type=int, default=20)
    q.add_argument("--json", action="store_true")
    sub.add_parser("stats")
    s = sub.add_parser("sync")
    s.add_argument("--dry-run", action="store_true")
    s.add_argument("--diff", action="store_true", help="print the unified diff, write nothing")
    c = sub.add_parser("check")
    c.add_argument("--json", action="store_true")
    c.add_argument("--gate", action="store_true", help="exit 1 on any P0/P1")
    c.add_argument("--new", action="store_true", help="hide findings recorded in the baseline")
    c.add_argument("--file", help="only findings located in this file")
    c.add_argument("--limit", type=int, default=0)
    sub.add_parser("baseline")
    sub.add_parser("templates")
    i = sub.add_parser("init")
    i.add_argument("--template", required=True)
    i.add_argument("--set", action="append", default=[], metavar="VAR=VALUE")
    i.add_argument("--title")
    i.add_argument("--force", action="store_true")
    f = sub.add_parser("flow")
    f.add_argument("action", choices=["show", "check", "apply"])
    f.add_argument("--yes", action="store_true")
    f.add_argument("--baseline", action="store_true", help="apply: also re-baseline")
    f.add_argument("--strict", action="store_true", help="check: exit 1 on warnings")
    t = sub.add_parser("selftest")
    t.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "templates":
            return cmd_templates(a)
        if a.cmd == "init":
            return cmd_init(a)
        if a.cmd == "selftest":
            return cmd_selftest(a)
        cfg = load(resolve_root(a.root))
        return {"why": cmd_why, "query": cmd_query, "stats": cmd_stats, "sync": cmd_sync,
                "check": cmd_check, "baseline": cmd_baseline, "flow": cmd_flow}[a.cmd](cfg, a)
    except ConfigError as e:
        print(f"rtm: config error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
