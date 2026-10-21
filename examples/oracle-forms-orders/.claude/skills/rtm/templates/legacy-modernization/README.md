# Template: legacy-modernization

Re-platforming an Oracle Forms / PL/SQL application. Every requirement is traced back to the legacy
object it was recovered from.

```
Oracle Form (FRM), PL/SQL (PLS) ─► BR ─┬─► Test case (TC) ─► Test code (Verifies: TC-###)
                                       │
                                       └─► LLD ─► Code (LLD-### in Javadoc)
                                            ▲
Fact (FACT), Constraint (CON) ─► HLD ───────┘     LLD must cite a BR and an HLD element
```

| Step | Produces (output) | Defined in | Consumes (input) |
|---|---|---|---|
| legacy | `FRM-###` / `PLS-###` | `{docs}/00-legacy/legacy-inventory.md` table | (root) |
| fact | `FACT-###` / `CON-###` | `{docs}/02-context/facts-constraints.md` table | (root) |
| br | `BR-###` | `{docs}/01-requirements/brd.md` table | an FRM or PLS |
| hld | `CMP-###` / `ADR-###` | `{docs}/03-hld/hld.md` table | a FACT or CON |
| lld | `LLD-###` | `{docs}/04-lld/lld.md` table | **both** a BR **and** an HLD element |
| code | one node per `{src}/**/*.java` | file | an `LLD-###` |
| tc | `TC-###` | `{docs}/05-test/test-cases.md` table | a BR |
| test | one node per `{tests}/**/*.java` | file | `Verifies:` line naming TCs |

Coverage (P3 progress signals): legacy objects with no BR yet, BRs with no test case yet, and test
cases with no test code yet.

Vars: `docs` (docs dir), `src` (main source dir), `tests` (test source dir).
Install: `rtm.py init --template legacy-modernization --set docs=docs --set src=src/main/java --set tests=src/test/java --title "My system"`
Example: `examples/oracle-forms-orders` in the rtm-kit repo.
