# oracle-forms-insurance (mock)

A motor-insurance policy admin system on Oracle Forms 12c / PL/SQL, being moved to Java 21 / Spring
Boot. It shows the `legacy-modernization` template on an insurance domain, starting from the forms
and recovering the business requirements from them. Every file is a mock: the forms are short
frmf2xml-style exports and the Java doesn't build.

## Legacy sources (`legacy/`)

| ID | Object | What's in it |
|---|---|---|
| FRM-001 | `forms/POLICY_ISSUE.xml` | Blocks POLICY_HDR, INSURED, VEHICLE, COVERAGE; age and start-date validation; Issue button calls rating + referral; policy number in PRE-INSERT |
| FRM-002 | `forms/CLAIM_FNOL.xml` | Loss-date check against the policy period; duplicate alert; routing above 10,000 |
| PLS-001 | `plsql/pkg_rating.pkb` | 3.5% base rate, +30% under 25, 10% NCD per year capped at 50%, minimum 300 |
| PLS-002 | `plsql/pkg_underwriting.pkb` | Refer when vehicle > 100,000 or licence < 2 years |
| PLS-003 | `plsql/pkg_renewal.pkb` | Nightly renewal quotes 30 days before expiry |

## Business requirements from the forms

[`docs/01-requirements/brd.md`](docs/01-requirements/brd.md) has 10 BRs. Each row cites the legacy ID
and the exact form element it was read from, for example:

| BR | Legacy source | Derived from |
|---|---|---|
| BR-002 holder ≥ 18 on start date | FRM-001 | `INSURED.DOB` · `WHEN-VALIDATE-ITEM` |
| BR-005 refer high-value / new drivers | PLS-002 · FRM-001 | `pkg_underwriting.needs_referral`; `STATUS := 'REFERRED'` |
| BR-009 duplicate claim warning | FRM-002 | `CLAIM` · `PRE-INSERT`, alert `ALR_DUPLICATE` |

The BRD also lists two open questions found while reading the source. For example, the form checks
the holder's age on the start date, but `pkg_rating` checks it on today's date.

## The rest of the chain

| Step | Artifact | Items |
|---|---|---|
| Fact / Constraint | `docs/02-context/facts-constraints.md` | FACT-001..003, CON-001..003 |
| HLD | `docs/03-hld/hld.md` | CMP-001..004, ADR-001..002 |
| LLD | `docs/04-lld/lld.md` | LLD-001..007 (each cites BR + HLD) |
| Code | `src/main/java/**` | 9 classes |
| Test case | `docs/05-test/test-cases.md` | TC-001..012 |
| Test code | `src/test/java/**` | 6 JUnit classes |

Try it from the kit root:

```bash
python3 skills/rtm/scripts/rtm.py --root examples/oracle-forms-insurance why FRM-001
python3 skills/rtm/scripts/rtm.py --root examples/oracle-forms-insurance why BR-004
python3 skills/rtm/scripts/rtm.py --root examples/oracle-forms-insurance check
```

The generated matrix is committed in `docs/rtm.md` and `docs/rtm/*.md`.

**Expected findings:** one gap, left in on purpose. The renewal job is designed and implemented, and
TC-012 is written, but there's no test code for it yet:

```
P3 NOT-COVERED docs/05-test/test-cases.md:16 TC-012 has no Test code yet
```
