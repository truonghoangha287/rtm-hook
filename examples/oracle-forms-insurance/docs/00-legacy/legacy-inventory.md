# Legacy inventory — Motor Policy Admin (Oracle Forms 12c / PL/SQL)

Every Oracle Form and PL/SQL object in scope gets an ID here. Business requirements cite these IDs.

| ID | Object | Type | Path | Purpose |
|---|---|---|---|---|
| FRM-001 | POLICY_ISSUE | Oracle Form | `legacy/forms/POLICY_ISSUE.xml` | Motor quote and policy issue: holder, vehicle, covers, premium, issue/refer |
| FRM-002 | CLAIM_FNOL | Oracle Form | `legacy/forms/CLAIM_FNOL.xml` | First notice of loss: validate against the policy, duplicate alert, handler routing |
| PLS-001 | PKG_RATING | PL/SQL package | `legacy/plsql/pkg_rating.pkb` | Premium calculation (base rate, young-driver loading, NCD, minimum) |
| PLS-002 | PKG_UNDERWRITING | PL/SQL package | `legacy/plsql/pkg_underwriting.pkb` | Referral rules for high-value vehicles and new drivers |
| PLS-003 | PKG_RENEWAL | PL/SQL package (scheduler job) | `legacy/plsql/pkg_renewal.pkb` | Nightly renewal quotes 30 days before expiry |
