# High-level design

| ID | Element | Description | Driven by |
|---|---|---|---|
| CMP-001 | Policy service | Spring Boot REST service for quotes, referral and policy issue | CON-001 · FACT-002 |
| CMP-002 | Rating engine | Pure domain module: premium from vehicle, holder and NCD; returns the factors used | CON-003 · FACT-003 |
| CMP-003 | Claims service | Spring Boot REST service for first notice of loss and handler routing | CON-001 · FACT-002 |
| CMP-004 | Renewal batch | Spring Batch job that replaces the nightly `RENEWAL_JOB` | CON-001 · FACT-002 |
| ADR-001 | Keep the Oracle schema, map it with JPA | Reuse POLICIES, POLICY_HOLDERS, CLAIMS, RENEWAL_QUOTES and the existing sequences | FACT-001 · CON-002 |
| ADR-002 | Rating factors in configuration, not code | Factors live in `rating.yml` so actuarial changes don't need a code change | FACT-003 · CON-003 |
