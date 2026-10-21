"""Templates (init), flow diagram (show) and the doctor (check against the real repo)."""
from __future__ import annotations

import json
from pathlib import Path

from .config import CONFIG_NAME, VAR, Config, ConfigError, is_glob
from .graph import Graph

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"


def templates() -> dict[str, str]:
    out = {}
    for d in sorted(TEMPLATES.iterdir()) if TEMPLATES.is_dir() else []:
        if (d / "flow.json").is_file():
            meta = json.loads((d / "flow.json").read_text()).get("template", {})
            out[d.name] = meta.get("description", "")
    return out


def init(root: Path, template: str, sets: dict[str, str], title: str, force: bool = False) -> list[str]:
    src = TEMPLATES / template
    if not (src / "flow.json").is_file():
        raise ConfigError(f"unknown template '{template}' (have: {', '.join(templates())})")
    target = root / CONFIG_NAME
    if target.exists() and not force:
        raise ConfigError(f"{target} exists — edit it, or pass --force to overwrite")
    raw = json.loads((src / "flow.json").read_text())
    unknown = set(sets) - set(raw.get("vars", {}))
    if unknown:
        raise ConfigError(f"unknown var(s) {sorted(unknown)}; template vars: {sorted(raw.get('vars', {}))}")
    raw["vars"] = {**raw.get("vars", {}), **sets}
    cfg = Config(root, raw)  # validates (fails on unset <placeholder> vars)
    msgs = []
    target.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + "\n")
    msgs.append(f"wrote {CONFIG_NAME} from template '{template}'")
    index = root / cfg.rtm
    if index.exists():
        msgs.append(f"kept existing index {cfg.rtm} (generated blocks are appended on sync)")
    elif (src / "index.md.tmpl").is_file():
        text = (src / "index.md.tmpl").read_text()
        text = text.replace("{title}", title)
        text = VAR.sub(lambda m: cfg.vars.get(m.group(1), m.group(0)), text)
        index.parent.mkdir(parents=True, exist_ok=True)
        index.write_text(text)
        msgs.append(f"wrote index skeleton {cfg.rtm}")
    return msgs


def _inputs(layer) -> list[str]:
    if layer.kind == "files":
        return layer.files
    return [f"{f} ({d.how})" for d in layer.define for f in d.files]


def show(cfg: Config, g: Graph | None = None) -> str:
    lines = [f"flow: {cfg.raw.get('template', {}).get('name', 'custom')}  "
             f"(index {cfg.rtm}{', sections ' + cfg.rtm_dir if cfg.rtm_dir else ''})", ""]
    for i, sid in enumerate(cfg.order):
        l = cfg.layers[sid]
        produces = (", ".join(f"{p}-###" for p in l.prefixes) if l.kind == "ids"
                    else "one node per file") if not l.parent else \
            f"{cfg.layers[l.parent].children.suffix}<n> inside each {cfg.layers[l.parent].label}"
        count = f"  [{len(g.layer_nodes(sid))} found]" if g else ""
        lines.append(f"[{sid}] {l.label}{count}")
        lines.append(f"   output : {produces}")
        if not l.parent:
            for inp in _inputs(l):
                lines.append(f"   from   : {inp}")
        if l.require:
            groups = [" or ".join(x for x in grp) for grp in l.require]
            rule = " AND ".join(f"({x})" if " or " in x else x for x in groups)
            lines.append(f"   input  : must cite {rule}"
                         + (f"  via '{l.ref_marker}' lines" if l.ref_marker else "")
                         + f"  [{l.severity}]")
        if l.trace_via != l.upstream:
            lines.append(f"   walks  : {', '.join(l.trace_via)}")
        if i < len(cfg.order) - 1:
            lines.append("   │")
    for c in cfg.coverage:
        lines.append(f"coverage: every {c['from']} should reach a {c['to']} [{c.get('severity', 'P3')}]")
    return "\n".join(lines)


def doctor(cfg: Config, g: Graph) -> list[str]:
    """Warnings about a flow that validates but doesn't match the repo."""
    warn = []
    if not (cfg.root / cfg.rtm).exists():
        warn.append(f"index {cfg.rtm} does not exist yet (sync will create it)")
    for sid in cfg.order:
        l = cfg.layers[sid]
        if l.parent:
            if not g.layer_nodes(sid) and g.layer_nodes(l.parent):
                warn.append(f"[{sid}] no children found in any {cfg.layers[l.parent].label} — "
                            f"check children.pattern")
            continue
        pats = l.files if l.kind == "files" else [f for d in l.define for f in d.files]
        for p in pats:
            if not cfg.expand([p]):
                warn.append(f"[{sid}] {'glob' if is_glob(p) else 'file'} '{p}' matches no files")
        nodes = g.layer_nodes(sid)
        if not nodes and all(cfg.expand([p]) for p in pats):
            warn.append(f"[{sid}] files exist but no {', '.join(l.prefixes) or 'nodes'} were found "
                        f"— check produces.in.how / the ID prefix")
        if l.ref_marker and nodes:
            has = sum(1 for n in nodes if l.ref_marker in g.scanner.text(n.file))
            if not has:
                warn.append(f"[{sid}] marker '{l.ref_marker}' appears in none of {len(nodes)} files")
        for a in l.attrs:
            if nodes and not any(n.attrs.get(a.name) for n in nodes):
                warn.append(f"[{sid}] attr '{a.name}': no '{a.key_col}'/'{a.value_col}' table rows "
                            f"found in {a.file}")
    return warn
