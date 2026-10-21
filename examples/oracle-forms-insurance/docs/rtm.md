# Requirements Traceability Matrix (RTM) — Motor Policy Admin modernization

| Field | Value |
|---|---|
| Document | Requirements Traceability Matrix (legacy modernization) |
| Owner | Business Analyst — hand sections; generated sections by `rtm sync` |
| Status | Draft (living document) |
| Traces | Oracle Form/PLSQL → BR → LLD → Code · Fact/Constraint → HLD → LLD · BR → Test case → Test code |
| Flow | `rtm.config.json` (template `legacy-modernization`) — run `rtm.py flow show` |

> Generated sections live between `<!-- rtm:begin … -->` markers here and in the files listed under
> *Matrix sections*. Don't edit them — change the source artifact; hooks re-sync automatically.
> Ask questions with `rtm.py why <ID>` / `rtm.py query …` instead of reading the matrix.

## 1. Migration scope (hand-maintained)

| Legacy object | Decision | Note |
|---|---|---|
| FRM-001 | migrate | POLICY_ISSUE becomes the policy service (`/quotes`) |
| FRM-002 | migrate | CLAIM_FNOL becomes the claims service (`/claims`); duplicate alert becomes a 409 + confirm |
| PLS-001 | migrate | rating moves to a pure Java module; factors move to `rating.yml` |
| PLS-002 | migrate | referral rules move into the policy service |
| PLS-003 | replace | DBMS_SCHEDULER job replaced by a scheduled Spring job |

## Coverage summary

<!-- rtm:begin summary sha=e5f5311841 -->
<!-- generated — edit the source artifacts, not this block -->
| Check | Result |
|---|---|
| Legacy source defined | 5 |
| Fact/Constraint defined | 6 |
| BR with required upstream links | 10 / 10 |
| HLD with required upstream links | 6 / 6 |
| LLD with required upstream links | 7 / 7 |
| Code with required upstream links | 9 / 9 |
| Test case with required upstream links | 12 / 12 |
| Test code with required upstream links | 6 / 6 |
| Legacy source reaching ≥ 1 BR | 5 / 5 |
| BR reaching ≥ 1 Test case | 10 / 10 |
| Test case reaching ≥ 1 Test code | 11 / 12 |
| Findings (P0 / P1 / P2 / P3) | 0 / 0 / 0 / 1 |

Ask with `rtm.py why <ID>` / `rtm.py query …`; itemised findings: `rtm.py check`.
<!-- rtm:end summary -->

## Matrix sections

<!-- rtm:begin toc sha=9a00c6b71b -->
<!-- generated — edit the source artifacts, not this block -->
| Section | File | Rows |
|---|---|---|
| Forward traceability — Legacy source → BR → LLD → Code → Test case → Test code | [rtm/forward-legacy.md](rtm/forward-legacy.md) | 5 |
| Forward traceability — Fact/Constraint → HLD → LLD → Code | [rtm/forward-fact.md](rtm/forward-fact.md) | 6 |
| LLD justification — each cites BR + HLD | [rtm/justify-lld.md](rtm/justify-lld.md) | 7 |
| Backward traceability — Test code → need | [rtm/backward-test.md](rtm/backward-test.md) | 6 |
<!-- rtm:end toc -->
