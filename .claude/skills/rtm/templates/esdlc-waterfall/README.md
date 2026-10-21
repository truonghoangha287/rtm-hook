# Template: esdlc-waterfall

Waterfall / gated delivery with separate high-level and low-level design.

```
Source ─► BR ─► FR/NFR ─► Story ─► AC ─────────────────► Test (Verifies: STORY-x/ACn | BR-x)
                  │                                        ▲
                  ├────► HLD (CMP/ADR/INT/SD)              │
                  └────► LLD (TASK: must cite HLD + FR) ─► Code (TASK-### in Javadoc)
```

| Step | Produces (output) | Defined in | Consumes (input) |
|---|---|---|---|
| br | `BR-###` | `{spec}/01-requirements/brd.md` table | Source column in the RTM index |
| req | `FR-###` / `NFR-###` | `frd-srs.md` headings / `nfr-spec.md` table | a BR, or a Source |
| story | `STORY-###` (+ `AC<n>` children) | stories file headings | an FR/NFR |
| hld | `CMP-`, `ADR-`, `INT-`, `SD-` | solution-architecture tables/headings | an FR/NFR (or another HLD element) |
| lld | `TASK-###` | technical-task-breakdown table | **both** an HLD element **and** an FR/NFR |
| code | one node per `src/main/**/*.java` | file | a `TASK-###` (or its `package-info.java`) |
| test | one node per `src/test/**/*.java` | file | `Verifies:` line naming ACs and/or BRs |

Vars: `spec` (feature spec dir), `code` (code module dir).
Install: `rtm.py init --template esdlc-waterfall --set spec=specs/001-x --set code=payment-hub --title "My system"`
