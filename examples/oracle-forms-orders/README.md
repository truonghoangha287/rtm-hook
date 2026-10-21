# oracle-forms-orders (mock)

A small Oracle Forms order-entry app being moved to Java 21 / Spring Boot. It shows the
`legacy-modernization` template end to end. Every file is a mock: the legacy sources are short
stand-ins and the Java doesn't build.

```
Oracle Form (FRM), PL/SQL (PLS) ─► BR ─┬─► Test case (TC) ─► Test code (Verifies: TC-###)
                                       │
                                       └─► LLD ─► Code (LLD-### in Javadoc)
                                            ▲
Fact (FACT), Constraint (CON) ─► HLD ───────┘     LLD must cite a BR and an HLD element
```

| Step | Artifact | Items |
|---|---|---|
| Legacy source | `docs/00-legacy/legacy-inventory.md` (points at `legacy/`) | FRM-001..002, PLS-001..003 |
| Fact / Constraint | `docs/02-context/facts-constraints.md` | FACT-001..002, CON-001..002 |
| BR | `docs/01-requirements/brd.md` | BR-001..004 |
| HLD | `docs/03-hld/hld.md` | CMP-001..002, ADR-001 |
| LLD | `docs/04-lld/lld.md` | LLD-001..004 |
| Code | `src/main/java/**` | 5 classes |
| Test case | `docs/05-test/test-cases.md` | TC-001..004 |
| Test code | `src/test/java/**` | 3 JUnit classes |

Created with:

```bash
python3 skills/rtm/scripts/rtm.py --root examples/oracle-forms-orders init --template legacy-modernization \
  --set docs=docs --set src=src/main/java --set tests=src/test/java --title "Order Entry modernization"
```

Try it from the kit root:

```bash
python3 skills/rtm/scripts/rtm.py --root examples/oracle-forms-orders flow show
python3 skills/rtm/scripts/rtm.py --root examples/oracle-forms-orders why FRM-001
python3 skills/rtm/scripts/rtm.py --root examples/oracle-forms-orders check
python3 skills/rtm/scripts/rtm.py --root examples/oracle-forms-orders selftest
```

The generated matrix is committed: `docs/rtm.md` (index, with a hand-written *Migration scope*) and
`docs/rtm/*.md` (forward from legacy, forward from facts, LLD justification, backward from tests).

**Expected findings:** one gap, left in on purpose. BR-004 (audit trail, from `TRG_ORDER_AUDIT`) is
designed and implemented but has no test case yet:

```
P3 NOT-COVERED docs/01-requirements/brd.md:10 BR-004 has no Test case yet
```
