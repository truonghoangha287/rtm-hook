# Template: agile

```
Epic ─► Story ─► AC ─► Test (Verifies: STORY-x/ACn)
          └──────────► Code (mentions STORY-###)
```

| Step | Produces (output) | Defined in | Consumes (input) |
|---|---|---|---|
| epic | `EPIC-##` | `{docs}/epics.md` table (`ID`, `Goal`, …) | its Goal column (source) |
| story | `STORY-###` + `AC<n>` | `{docs}/stories/*.md` headings `## STORY-012 — …` | an EPIC id in the section |
| code | one node per file under `{src}` | file | a `STORY-###` mention (commit-style comment) |
| test | one node per file under `{tests}` | file | `Verifies: STORY-012/AC2` |

Vars: `docs`, `src`, `tests`.
