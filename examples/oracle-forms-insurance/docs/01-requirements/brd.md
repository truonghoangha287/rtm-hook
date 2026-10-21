# Business requirements — Motor Policy Admin

Recovered from the legacy Oracle Forms and PL/SQL. Each row names the legacy object (ID) and the
exact form element or code it was read from, so the rule can be checked against the source.

| BR | Requirement | Legacy source | Derived from | Priority |
|---|---|---|---|---|
| BR-001 | An agent can capture a motor quote with the policy holder, one vehicle and one or more covers; a new quote has status QUOTE | FRM-001 | Blocks `POLICY_HDR`, `INSURED`, `VEHICLE`, `COVERAGE`; `STATUS` initial value `QUOTE` | MUST |
| BR-002 | The policy holder must be at least 18 years old on the cover start date | FRM-001 | `INSURED.DOB` · `WHEN-VALIDATE-ITEM` | MUST |
| BR-003 | Cover cannot start in the past and always runs for 12 months (end date = start + 12 months − 1 day) | FRM-001 | `POLICY_HDR.START_DATE` · `WHEN-VALIDATE-ITEM`; `END_DATE` not editable | MUST |
| BR-004 | Annual premium = 3.5% of vehicle value; +30% if the holder is under 25 on the start date; minus 10% per no-claims year, capped at 50%; never below 300.00; rounded to cents | PLS-001 · FRM-001 | `pkg_rating.calc_premium`, called from `BTN_ISSUE` · `WHEN-BUTTON-PRESSED` | MUST |
| BR-005 | A quote is referred to an underwriter instead of issued when the vehicle is worth more than 100,000 or the driver has held a licence for under 2 years | PLS-002 · FRM-001 | `pkg_underwriting.needs_referral`; `STATUS := 'REFERRED'` in `WHEN-BUTTON-PRESSED` | MUST |
| BR-006 | An issued policy gets a number `<product>-<year>-<6-digit sequence>`, e.g. `MOT-2026-000123` | FRM-001 | `POLICY_HDR` · `PRE-INSERT` (`policy_seq`) | MUST |
| BR-007 | A claim can only be registered for an issued policy, with a loss date inside the policy period | FRM-002 | `CLAIM.LOSS_DATE` · `WHEN-VALIDATE-ITEM` | MUST |
| BR-008 | Claims with an estimate above 10,000 are routed to the senior handler group; others to standard | FRM-002 | `CLAIM` · `PRE-INSERT` (`HANDLER_GROUP`) | MUST |
| BR-009 | When a claim already exists for the same policy and loss date, the user is warned and may cancel or save anyway | FRM-002 | `CLAIM` · `PRE-INSERT`, alert `ALR_DUPLICATE` | SHOULD |
| BR-010 | 30 days before expiry, each issued policy gets a renewal quote; a claim-free year adds one no-claims year, any claim resets it to 0 | PLS-003 | `pkg_renewal.create_renewal_quotes` (nightly job) | MUST |

## Open questions found while reading the source

| # | Question | Where |
|---|---|---|
| Q1 | The form checks age on the **start date**, but `pkg_rating` checks "under 25" on **today's date**. BR-004 keeps the start-date reading; confirm with the business. | `INSURED.DOB` vs `pkg_rating.calc_premium` |
| Q2 | The duplicate-claim alert allows saving anyway. Should a duplicate be blocked outright in the new system? | `ALR_DUPLICATE` |
