# Test cases

| TC | Scenario | Expected | Requirement |
|---|---|---|---|
| TC-001 | Capture a quote with holder, vehicle and two covers | Quote saved with status QUOTE | BR-001 |
| TC-002 | Holder turns 18 the day after the start date | Rejected: "Policy holder must be at least 18 on the start date" | BR-002 |
| TC-003 | Start date yesterday; and start date 2027-03-01 | Rejected; end date 2028-02-29 (leap year) | BR-003 |
| TC-004 | Vehicle 20,000, holder 40, NCD 0 | Premium 700.00 | BR-004 |
| TC-005 | Vehicle 20,000, holder 22, NCD 3 | 700 × 1.30 × 0.70 = 637.00 | BR-004 |
| TC-006 | Vehicle 5,000, holder 40, NCD 6 | 175 × 0.50 = 87.50, raised to the minimum 300.00 | BR-004 |
| TC-007 | Vehicle 120,000; and licence held 1 year | Both referred (status REFERRED) | BR-005 |
| TC-008 | Issue the 123rd MOT policy in 2026 | Policy number MOT-2026-000123 | BR-006 |
| TC-009 | Claim with loss date after the policy end date | Rejected: "Loss date is outside an issued policy period" | BR-007 |
| TC-010 | Estimates 10,000.00 and 10,000.01 | STANDARD and SENIOR | BR-008 |
| TC-011 | Second claim, same policy and loss date, without confirmation | 409 Conflict; saved when confirmed | BR-009 |
| TC-012 | Policy ending in 30 days, claim-free, NCD 2 | Renewal quote with NCD 3 and re-rated premium | BR-010 |
