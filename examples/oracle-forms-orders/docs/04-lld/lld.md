# Low-level design

Each design item cites the requirement it implements **and** the high-level element it lives in.

| ID | Design | Requirement | HLD | Classes |
|---|---|---|---|---|
| LLD-001 | `POST /orders` validates the customer and lines, then saves header + lines in one transaction | BR-001 | CMP-001 · ADR-001 | `OrderController`, `OrderService` |
| LLD-002 | `DiscountCalculator.lineTotal(qty, unitPrice)`: 10% off when qty ≥ 100, rounded half-up to cents | BR-002 | CMP-002 | `DiscountCalculator` |
| LLD-003 | `CreditCheckService.assertWithinLimit` sums OPEN orders + the new total and compares with `CUSTOMERS.CREDIT_LIMIT` | BR-003 | CMP-001 · ADR-001 | `CreditCheckService` |
| LLD-004 | JPA entity listener writes an `ORDER_AUDIT` row on persist/update/remove | BR-004 | ADR-001 | `OrderAuditListener` |
