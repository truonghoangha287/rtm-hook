# Low-level design

Each design item cites the requirement(s) it implements **and** the high-level element it lives in.

| ID | Design | Requirement | HLD | Classes |
|---|---|---|---|---|
| LLD-001 | `POST /quotes`: validate holder age on the start date, start date not in the past, end = start + 12 months − 1 day; save with status QUOTE | BR-001 · BR-002 · BR-003 | CMP-001 · ADR-001 | `QuoteController`, `QuoteValidator` |
| LLD-002 | `PremiumCalculator.annualPremium(vehicleValue, ageAtStart, ncdYears)` using `RatingFactors`; returns premium + factors applied | BR-004 | CMP-002 · ADR-002 | `PremiumCalculator`, `RatingFactors` |
| LLD-003 | `UnderwritingRules.needsReferral(vehicleValue, licenceYears)`; `POST /quotes/{id}/issue` sets REFERRED or ISSUED | BR-005 | CMP-001 | `UnderwritingRules` |
| LLD-004 | `PolicyNumberGenerator.next(product, year)` reads `POLICY_SEQ` and formats `MOT-2026-000123` | BR-006 | CMP-001 · ADR-001 | `PolicyNumberGenerator` |
| LLD-005 | `POST /claims`: policy must be ISSUED and loss date in period; duplicate (policy + loss date) returns 409 unless `confirmDuplicate=true` | BR-007 · BR-009 | CMP-003 · ADR-001 | `FnolService` |
| LLD-006 | `ClaimRouter.handlerGroup(estimate)`: SENIOR above 10,000, else STANDARD | BR-008 | CMP-003 | `ClaimRouter` |
| LLD-007 | Spring Batch `RenewalJob`: select ISSUED policies ending in 30 days, NCD +1 if claim-free else 0, rate with `PremiumCalculator`, write `RENEWAL_QUOTES` | BR-010 | CMP-004 · CMP-002 | `RenewalJob` |
