# Legacy inventory — Order Entry (Oracle Forms 12c / PL/SQL)

Every Oracle Form and PL/SQL object in scope gets an ID here. Business requirements cite these IDs.

| ID | Object | Type | Path | Purpose |
|---|---|---|---|---|
| FRM-001 | ORDERS | Oracle Form | `legacy/forms/ORDERS.xml` | Order entry: header + lines, commit runs credit check |
| FRM-002 | CUSTOMERS | Oracle Form | `legacy/forms/CUSTOMERS.xml` | Read-only customer lookup with credit limit |
| PLS-001 | PKG_ORDER_PRICING | PL/SQL package | `legacy/plsql/pkg_order_pricing.pkb` | Line and order totals, volume discount |
| PLS-002 | PKG_CREDIT_CHECK | PL/SQL package | `legacy/plsql/pkg_credit_check.pkb` | Rejects orders over the customer's credit limit |
| PLS-003 | TRG_ORDER_AUDIT | PL/SQL trigger | `legacy/plsql/trg_order_audit.trg` | Audit row for every insert/update/delete on ORDERS |
