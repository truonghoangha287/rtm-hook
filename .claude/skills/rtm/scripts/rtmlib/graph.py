"""Trace graph over scanned nodes: up/down walks restricted to each layer's trace_via."""
from __future__ import annotations

from collections import defaultdict, deque

from .config import Config
from .ids import sort_key
from .scan import Node, Scanner


class Graph:
    def __init__(self, cfg: Config, scanner: Scanner):
        self.cfg = cfg
        self.scanner = scanner
        self.syntax = scanner.syntax
        self.nodes: dict[str, Node] = scanner.nodes
        self.down: dict[str, set[str]] = defaultdict(set)  # parent -> children
        for n in self.nodes.values():
            for parent in self.parents(n):
                self.down[parent].add(n.key)

    @classmethod
    def build(cls, cfg: Config) -> "Graph":
        sc = Scanner(cfg)
        sc.run()
        return cls(cfg, sc)

    def layer_nodes(self, layer: str) -> list[Node]:
        nodes = [n for n in self.nodes.values() if n.layer == layer]
        files = self.cfg.layers[layer].kind == "files"
        return sorted(nodes, key=(lambda n: n.key) if files else (lambda n: sort_key(n.key)))

    def parents(self, n: Node) -> set[str]:
        """Defined upstream keys along this node's trace_via layers."""
        via = self.cfg.layers[n.layer].trace_via
        return {k for l in via for k in n.refs.get(l, ()) if k in self.nodes}

    def descendants(self, k: str) -> dict[str, list[str]]:
        seen, q = {k}, deque([k])
        while q:
            for c in self.down.get(q.popleft(), ()):
                if c not in seen:
                    seen.add(c)
                    q.append(c)
        return self._group(seen - {k})

    def ancestors(self, k: str) -> dict[str, list[str]]:
        seen, q = {k}, deque([k])
        while q:
            for p in self.parents(self.nodes[q.popleft()]):
                if p not in seen:
                    seen.add(p)
                    q.append(p)
        return self._group(seen - {k})

    def _group(self, keys) -> dict[str, list[str]]:
        out: dict[str, list[str]] = defaultdict(list)
        for k in keys:
            out[self.nodes[k].layer].append(k)
        for l, ks in out.items():
            files = self.cfg.layers[l].kind == "files"
            ks.sort(key=(lambda x: x) if files else sort_key)
        return out

    def show(self, k: str) -> str:
        n = self.nodes.get(k)
        if n and self.cfg.layers[n.layer].kind == "files":
            if n.label == "package-info":
                return n.key.rsplit("/", 2)[-2] + "/package-info"
            return n.label
        return self.syntax.show(k)

    def source(self, n: Node) -> str:
        """Nearest 'source' attribute walking up the chain."""
        if n.attrs.get("source"):
            return n.attrs["source"]
        anc = self.ancestors(n.key)
        for l in self.cfg.layers:
            for k in anc.get(l, []):
                s = self.nodes[k].attrs.get("source")
                if s:
                    return s
        return ""
