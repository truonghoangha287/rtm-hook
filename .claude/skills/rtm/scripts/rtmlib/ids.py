"""ID syntax: finding, expanding and normalising trace IDs in free text.

Handles the compressed forms real artifacts use:
  FR-009/010      -> FR-009, FR-010
  FR-001..013     -> FR-001 .. FR-013   (also FR-001..FR-013, FR-001…013)
  FR-009-011      -> FR-009 .. FR-011   (dash range, equal digit width only)
  ADR-5 == ADR-05 (keys ignore zero padding)
  STORY-001/AC4, STORY-001 AC4 -> composite child ID
"""
from __future__ import annotations

import re
from dataclasses import dataclass

MAX_RANGE = 300


def key(prefix: str, num: int) -> str:
    return f"{prefix}-{num}"


def child_key(parent: str, suffix: str, num: int) -> str:
    return f"{parent}/{suffix}{num}"


def split_key(k: str) -> tuple[str, int]:
    p, _, n = k.rpartition("-")
    return p, int(n)


def sort_key(k: str):
    """Natural sort: prefix, number, then child number."""
    base, _, child = k.partition("/")
    p, n = split_key(base)
    c = int(re.sub(r"\D", "", child) or 0) if child else -1
    return (p, n, c)


@dataclass(frozen=True)
class Hit:
    key: str
    pos: int  # char offset of the first ID in the run


class IdSyntax:
    def __init__(self, prefixes: list[str], composites: dict[str, str] | None = None):
        self.prefixes = sorted(set(prefixes), key=len, reverse=True)
        self.composites = composites or {}  # parent prefix -> child suffix (e.g. STORY -> AC)
        alt = "|".join(map(re.escape, self.prefixes)) or r"(?!x)x"
        self._id = re.compile(rf"(?<![A-Za-z0-9])({alt})-(\d+)(?![0-9])")
        self._cont = re.compile(
            rf"(?:\s*/\s*(\d+)(?![0-9A-Za-z])"  # /010
            rf"|\s*(?:\.\.|…)\s*(?:(?:{alt})-)?(\d+)(?![0-9])"  # ..013 / ..FR-013
            rf"|-(\d+)(?![0-9A-Za-z]))"  # -011 (no whitespace)
        )
        self._comp = None
        if self.composites:
            calt = "|".join(map(re.escape, self.composites))
            sfx = "|".join(map(re.escape, set(self.composites.values())))
            self._comp = re.compile(
                rf"(?<![A-Za-z0-9])({calt})-(\d+)\s*(?:/|\s)\s*({sfx})(\d+)(?![0-9])"
            )
        self.width: dict[str, int] = {}  # display padding learnt from definitions

    # -- display ---------------------------------------------------------
    def learn(self, prefix: str, digits: str) -> None:
        self.width.setdefault(prefix, len(digits))

    def show(self, k: str) -> str:
        base, sep, child = k.partition("/")
        p, n = split_key(base)
        s = f"{p}-{n:0{self.width.get(p, 3)}d}"
        return f"{s}/{child}" if sep else s

    # -- parsing ---------------------------------------------------------
    def first(self, text: str) -> tuple[str, str] | None:
        """(prefix, digits) of an ID at the very start of text (after markup)."""
        m = re.match(r"[\s*_`\[]*", text)
        m = self._id.match(text, m.end() if m else 0)
        return (m.group(1), m.group(2)) if m else None

    def find(self, text: str) -> list[Hit]:
        hits: list[Hit] = []
        if self._comp:
            for m in self._comp.finditer(text):
                parent = key(m.group(1), int(m.group(2)))
                hits.append(Hit(child_key(parent, m.group(3), int(m.group(4))), m.start()))
        pos = 0
        while m := self._id.search(text, pos):
            prefix, digits = m.group(1), m.group(2)
            nums = [int(digits)]
            end = m.end()
            while True:
                c = self._cont.match(text, end)
                if not c:
                    break
                if c.group(1):
                    nums.append(int(c.group(1)))
                elif c.group(2):
                    lo, hi = nums[-1], int(c.group(2))
                    if not (lo < hi <= lo + MAX_RANGE):
                        break
                    nums.extend(range(lo + 1, hi + 1))
                elif c.group(3):
                    if len(c.group(3)) != len(digits):
                        break
                    lo, hi = nums[-1], int(c.group(3))
                    if not (lo < hi <= lo + MAX_RANGE):
                        break
                    nums.extend(range(lo + 1, hi + 1))
                end = c.end()
            hits.extend(Hit(key(prefix, n), m.start()) for n in nums)
            pos = end
        return hits

    def prefix_of(self, k: str) -> str:
        return split_key(k.partition("/")[0])[0]
