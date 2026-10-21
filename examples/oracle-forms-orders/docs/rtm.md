# Requirements Traceability Matrix (RTM) — Order Entry modernization

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
| FRM-001 | migrate | ORDERS form becomes `POST /orders` |
| FRM-002 | replace | lookup screen retired; the credit limit is read by the service |
| PLS-001 | migrate | pricing rules move to a pure Java module |
| PLS-002 | migrate | credit check moves into the order service |
| PLS-003 | migrate | trigger replaced by a JPA entity listener |

## Coverage summary

<!-- rtm:begin summary sha=ad6097da99 -->
<!-- generated — edit the source artifacts, not this block -->
| Check | Result |
|---|---|
| Legacy source defined | 5 |
| Fact/Constraint defined | 4 |
| BR with required upstream links | 4 / 4 |
| HLD with required upstream links | 3 / 3 |
| LLD with required upstream links | 4 / 4 |
| Code with required upstream links | 5 / 5 |
| Test case with required upstream links | 6 / 6 |
| Test code with required upstream links | 3 / 3 |
| Legacy source reaching ≥ 1 BR | 5 / 5 |
| BR reaching ≥ 1 Test case | 4 / 4 |
| Test case reaching ≥ 1 Test code | 4 / 6 |
| Findings (P0 / P1 / P2 / P3) | 0 / 0 / 0 / 2 |

Ask with `rtm.py why <ID>` / `rtm.py query …`; itemised findings: `rtm.py check`.
<!-- rtm:end summary -->

## Matrix sections

<!-- rtm:begin toc sha=ee2d1c418d -->
<!-- generated — edit the source artifacts, not this block -->
| Section | File | Rows |
|---|---|---|
| Forward traceability — Legacy source → BR → LLD → Code → Test case → Test code | [rtm/forward-legacy.md](rtm/forward-legacy.md) | 5 |
| Forward traceability — Fact/Constraint → HLD → LLD → Code | [rtm/forward-fact.md](rtm/forward-fact.md) | 4 |
| LLD justification — each cites BR + HLD | [rtm/justify-lld.md](rtm/justify-lld.md) | 4 |
| Backward traceability — Test code → need | [rtm/backward-test.md](rtm/backward-test.md) | 3 |
<!-- rtm:end toc -->
