"""Scan artifacts into trace nodes.

Markdown docs define IDs in two ways:
  table   - an ID in the first cell of a table row; refs = IDs in the other cells.
  heading - a heading starting with an ID; refs = IDs in the heading and its section body
            (up to the next heading of the same or higher level).
Files layers (code/tests) become one node per file; refs = IDs mentioned in the file
(or only on lines containing `ref_marker`, e.g. "Verifies:").
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config, Layer
from .ids import IdSyntax, child_key, key

FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
COMMENT = re.compile(r"<!--.*?-->", re.S)
BLOCK = re.compile(r"<!-- rtm:begin (\S+)[^>]*-->.*?<!-- rtm:end \1 -->", re.S)


@dataclass
class Node:
    key: str
    layer: str
    file: str
    line: int
    label: str = ""
    refs: dict[str, set[str]] = field(default_factory=dict)  # layer -> keys (upstream)
    mentions: list[tuple[str, int]] = field(default_factory=list)  # (key, line) for dangling
    attrs: dict[str, str] = field(default_factory=dict)
    inherited: bool = False

    def add_ref(self, layer: str, k: str) -> None:
        self.refs.setdefault(layer, set()).add(k)


def read(cfg: Config, rel: str) -> str:
    try:
        return (cfg.root / rel).read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def doc_lines(text: str) -> list[tuple[int, str]]:
    """(lineno, text) for markdown prose: fences dropped, HTML comments blanked."""
    text = COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    out, fenced = [], False
    for i, line in enumerate(text.splitlines(), 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            out.append((i, line))
    return out


def split_row(line: str) -> list[str] | None:
    s = line.strip()
    if not s.startswith("|"):
        return None
    cells = re.split(r"(?<!\\)\|", s.strip("|"))
    return [c.strip().replace("\\|", "|") for c in cells]


def is_sep(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) for c in cells if c) and any(cells)


def tables(lines: list[tuple[int, str]]):
    """Yield (header_cells, [(lineno, cells), ...]) for each markdown table."""
    header, rows, prev = None, [], None
    for ln, line in lines + [(0, "")]:
        cells = split_row(line)
        if cells is None:
            if header is not None:
                yield header, rows
            header, rows, prev = None, [], None
            continue
        if header is None:
            if prev is not None and is_sep(cells):
                header = prev[1]
            else:
                prev = (ln, cells)
            continue
        rows.append((ln, cells))


def _col(header: list[str], name: str) -> int | None:
    name = name.lower()
    for i, h in enumerate(header):
        h = re.sub(r"[*_`]", "", h).strip().lower()
        if h == name or h.startswith(name):
            return i
    return None


class Scanner:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.syntax = IdSyntax(list(cfg.prefix_layer()), cfg.composites())
        self.prefix_layer = cfg.prefix_layer()
        self.nodes: dict[str, Node] = {}
        self.texts: dict[str, str] = {}

    def text(self, rel: str) -> str:
        if rel not in self.texts:
            t = read(self.cfg, rel)
            if rel == self.cfg.rtm:
                t = BLOCK.sub(lambda m: "\n" * m.group(0).count("\n"), t)  # never read our own output
            self.texts[rel] = t
        return self.texts[rel]

    # -- helpers ------------------------------------------------------------
    def layer_of(self, k: str) -> str | None:
        base, sep, _ = k.partition("/")
        lid = self.prefix_layer.get(self.syntax.prefix_of(base))
        if lid and sep:
            ch = self.cfg.layers[lid].children
            return ch.id if ch else None
        return lid

    def _collect(self, node: Node, text: str, line: int, layer: Layer, refs_ok=True) -> None:
        for hit in self.syntax.find(text):
            if hit.key == node.key:
                continue
            ln = line + text.count("\n", 0, hit.pos)
            node.mentions.append((hit.key, ln))
            target = self.layer_of(hit.key)
            if refs_ok and target in layer.upstream:
                node.add_ref(target, hit.key)

    def _define(self, layer: Layer, prefix: str, digits: str, rel: str, line: int, label: str) -> Node:
        self.syntax.learn(prefix, digits)
        k = key(prefix, int(digits))
        node = self.nodes.get(k)
        if node is None:
            node = self.nodes[k] = Node(k, layer.id, rel, line, label=label)
        return node

    # -- definitions --------------------------------------------------------
    def scan_layer(self, layer: Layer) -> None:
        if layer.kind == "files":
            return self.scan_files(layer)
        for d in layer.define:
            for rel in self.cfg.expand(d.files):
                lines = doc_lines(self.text(rel))
                if d.how == "table":
                    self._tables(layer, rel, lines)
                else:
                    self._headings(layer, rel, lines)

    def _owns(self, layer: Layer, first) -> bool:
        return bool(first) and first[0] in layer.prefixes

    def _tables(self, layer: Layer, rel: str, lines) -> None:
        for header, rows in tables(lines):
            for ln, cells in rows:
                if not cells:
                    continue
                first = self.syntax.first(cells[0])
                if not self._owns(layer, first):
                    continue
                label = cells[1] if len(cells) > 1 else ""
                node = self._define(layer, first[0], first[1], rel, ln, _plain(label))
                self._collect(node, " | ".join(cells[1:]), ln, layer)

    def _headings(self, layer: Layer, rel: str, lines) -> None:
        idx = [(i, HEADING.match(t)) for i, (_, t) in enumerate(lines)]
        idx = [(i, m) for i, m in idx if m]
        for n, (i, m) in enumerate(idx):
            level, title = len(m.group(1)), m.group(2)
            first = self.syntax.first(title)
            if not self._owns(layer, first):
                continue
            end = len(lines)
            for j, m2 in idx[n + 1:]:
                if len(m2.group(1)) <= level:
                    end = j
                    break
            ln = lines[i][0]
            label = re.sub(r"^[\s*_`]*[A-Z]+-\d+[\s*_`]*[—:–-]*\s*", "", title)
            node = self._define(layer, first[0], first[1], rel, ln, _plain(label))
            section = lines[i:end]
            for sln, stext in section:
                self._collect(node, stext, sln, layer)
                ch = layer.children
                if ch:
                    cm = ch.pattern.search(stext)
                    if cm:
                        ck = child_key(node.key, ch.suffix, int(cm.group(1)))
                        if ck not in self.nodes:
                            c = self.nodes[ck] = Node(ck, ch.id, rel, sln,
                                                      label=_plain(stext[cm.end():])[:80])
                            c.add_ref(layer.id, node.key)

    # -- files layers -------------------------------------------------------
    def scan_files(self, layer: Layer) -> None:
        for rel in self.cfg.expand(layer.files):
            text = self.text(rel)
            node = self.nodes[rel] = Node(rel, layer.id, rel, 1, label=Path(rel).stem)
            for ln, line in enumerate(text.splitlines(), 1):
                if layer.ref_marker and layer.ref_marker not in line:
                    self._collect(node, line, ln, layer, refs_ok=False)
                else:
                    self._collect(node, line, ln, layer)
        if layer.inherit_from:
            self._inherit(layer)

    def _inherit(self, layer: Layer) -> None:
        for rel, node in list(self.nodes.items()):
            if node.layer != layer.id or node.refs or rel.endswith("/" + layer.inherit_from):
                continue
            parent = self.nodes.get(str(Path(rel).parent / layer.inherit_from))
            if parent and parent.refs:
                node.refs = {k: set(v) for k, v in parent.refs.items()}
                node.inherited = True

    # -- attributes ---------------------------------------------------------
    def scan_attrs(self) -> None:
        for layer in self.cfg.layers.values():
            for a in layer.attrs:
                for rel in self.cfg.expand([a.file]):
                    for header, rows in tables(doc_lines(self.text(rel))):
                        kc, vc = _col(header, a.key_col), _col(header, a.value_col)
                        if kc is None or vc is None:
                            continue
                        for _, cells in rows:
                            if max(kc, vc) >= len(cells):
                                continue
                            value = _plain(cells[vc])
                            if not value or value.lower() in ("n/a", "-", "—", "tbd"):
                                continue
                            for hit in self.syntax.find(cells[kc]):
                                node = self.nodes.get(hit.key)
                                if node and node.layer == layer.id:
                                    node.attrs.setdefault(a.name, value)

    def run(self) -> dict[str, Node]:
        for layer in self.cfg.layers.values():
            if not layer.parent:
                self.scan_layer(layer)
        self.scan_attrs()
        return self.nodes


def _plain(s: str) -> str:
    s = re.sub(r"\*\*|__|`", "", s)
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()
