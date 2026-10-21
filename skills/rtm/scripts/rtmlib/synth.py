"""Build a synthetic mini-repo that satisfies any flow, for the generated contract tests.

For every step it writes artifacts in the format the step declares (table rows, headings with
child lines, or files with marker lines), and makes each node cite upstream nodes so that its
consumes rule holds. Options create precise defects:

  drop=(step, group)   node 0 of `step` omits that require-group  -> MISSING-UPSTREAM expected
  alt=(step, group)    node 0 satisfies the group with its LAST member (proves `any`)
  dangle=step          node 0 of `step` also mentions an undefined ID -> DANGLING expected

Children: tests cite only child 1 of each parent, so child 2 is always uncovered.
"""
from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import CONFIG_NAME, Config, Layer

N = 2  # nodes per prefix / files per files-step


def synth_vars(raw: dict) -> dict:
    """Fill <placeholder> vars with their 'e.g.' example, else a safe default."""
    raw = copy.deepcopy(raw)
    out = {}
    for k, v in (raw.get("vars") or {}).items():
        v = str(v)
        if v.startswith("<") and v.endswith(">"):
            m = re.search(r"e\.g\.\s*([^\s>]+)", v)
            v = m.group(1) if m else f"syn/{k}"
        out[k] = v
    raw["vars"] = out
    return raw


def concrete(pattern: str, i: int = 1) -> str:
    p = pattern.replace("**/", "").replace("**", "x").replace("?", "x")
    return p.replace("*", f"Synth{i}")


@dataclass
class Synth:
    root: Path
    cfg: Config
    keys: dict[str, list[str]] = field(default_factory=dict)  # step -> display ids / file paths
    where: dict[str, str] = field(default_factory=dict)  # step -> file its nodes are written to
    dangling: dict[str, str] = field(default_factory=dict)  # step -> undefined id injected

    def node0(self, step: str) -> str:
        return self.keys[step][0]


def build(raw: dict, root: Path, drop=None, alt=None, dangle=None) -> Synth:
    raw = synth_vars(raw)
    root.mkdir(parents=True, exist_ok=True)
    (root / CONFIG_NAME).write_text(json.dumps(raw, indent=1))
    cfg = Config(root, raw)
    s = Synth(root, cfg)
    L = cfg.layers

    # 1. allocate node keys
    for sid in cfg.order:
        l = L[sid]
        if l.parent:
            parent = L[l.parent]
            s.keys[sid] = [f"{p}/{parent.children.suffix}{k}" for p in s.keys[l.parent] for k in (1, 2)]
        elif l.kind == "ids":
            s.keys[sid] = [f"{p}-{i:03d}" for p in l.prefixes for i in range(1, N + 1)]
        else:
            s.keys[sid] = [concrete(l.files[0], i) for i in range(1, N + 1)]

    def cites(l: Layer, i: int) -> tuple[list[str], set[str]]:
        """IDs node i must cite, and attr names it must carry."""
        ids, attrs = [], set()
        for gi, g in enumerate(l.require):
            if drop == (l.id, gi) and i == 0:
                continue
            member = g[-1] if (alt == (l.id, gi) and i == 0) else g[0]
            if member.startswith("@"):
                attrs.add(member[1:])
                continue
            pool = s.keys[member]
            if L[member].parent:  # child step: cite only child 1 -> child 2 stays uncovered
                pool = [k for k in pool if re.search(rf"{L[L[member].parent].children.suffix}1$", k)]
            if member == l.id:  # self-loop: cite a sibling
                pool = [k for k in pool if k != s.keys[l.id][i]] or pool
            ids.append(pool[i % len(pool)])
        return ids, attrs

    def bad_id(sid: str) -> str:
        l = L[sid]
        if l.parent:
            return f"{s.keys[l.parent][0]}/{L[l.parent].children.suffix}99"
        return f"{l.prefixes[0]}-999" if l.prefixes else ""

    # 2. write artifacts
    tables: dict[str, list[str]] = {}
    headings: dict[str, list[str]] = {}
    index_attr_rows: dict[tuple[str, str], list[str]] = {}
    for sid in cfg.order:
        l = L[sid]
        if l.parent:
            continue
        extra = ""
        if dangle == sid:
            bid = bad_id(sid)
            extra = f" see {bid}" if bid else ""
            s.dangling[sid] = bid
        child_dangle = next((c for c in cfg.order if L[c].parent == sid and dangle == c), None)
        if child_dangle:
            s.dangling[child_dangle] = bad_id(child_dangle)
        if l.kind == "files":
            for i, path in enumerate(s.keys[sid]):
                ids, _ = cites(l, i)
                lead = f"{l.ref_marker} " if l.ref_marker else "implements "
                body = f"// synthetic {l.label} {i + 1}\n"
                if ids:
                    body += f"// {lead}{', '.join(ids)}\n"
                if i == 0 and extra:
                    body += f"// note{extra}\n"
                p = root / path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(body)
            s.where[sid] = s.keys[sid][0]
            continue
        nodes = s.keys[sid]
        for i, k in enumerate(nodes):
            d = l.define[l.prefixes.index(k.rsplit("-", 1)[0]) % len(l.define)]
            path = concrete(d.files[0])
            s.where.setdefault(sid, path)
            ids, attrs = cites(l, i)
            refs = ", ".join(ids) or "—"
            note = extra if i == 0 else ""
            if d.how == "table":
                tables.setdefault(path, [])
                tables[path].append(f"| {k} | Synthetic {l.label} {i + 1} | {refs}{note} |")
            else:
                sec = [f"## {k} — Synthetic {l.label} {i + 1}", "", f"Traces: {refs}{note}", ""]
                if l.children:
                    ex = l.children.example or f"- **{l.children.suffix}{{n}}:** synthetic"
                    sec += [ex.replace("{n}", str(n)) for n in (1, 2)]
                    if child_dangle and i == 0:
                        sec.append(f"Related: {s.dangling[child_dangle]}")
                    sec.append("")
                headings.setdefault(path, []).extend(sec)
            for a in l.attrs:
                required = any("@" + a.name in g for g in l.require)
                if a.name in attrs or not required or i > 0:
                    index_attr_rows.setdefault((a.file, f"{a.key_col}|{a.value_col}"), []).append(
                        f"| {k} | Synthetic source {i + 1} |")
    for path, rows in tables.items():
        tables[path] = ["| ID | Title | Traces |", "|---|---|---|"] + rows + [""]
    files: dict[str, list[str]] = {}
    for path in set(tables) | set(headings) | {cfg.rtm} | {f for f, _ in index_attr_rows}:
        files[path] = [f"# Synthetic {Path(path).stem}", ""]
    for (path, cols), rows in index_attr_rows.items():
        kc, vc = cols.split("|")
        files[path] += [f"| {kc} | {vc} |", "|---|---|"] + rows + [""]
    for path, lines in tables.items():
        files[path] += lines
    for path, lines in headings.items():
        files[path] += lines
    for sid in cfg.order:  # every declared input file exists, even if it holds no synthetic node
        for d in L[sid].define:
            for f in d.files:
                files.setdefault(concrete(f), [f"# Synthetic {Path(f).stem}", ""])
    for path, lines in files.items():
        p = root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("\n".join(lines) + "\n")
    return s
