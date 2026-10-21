# High-level design

| ID | Element | Description | Driven by |
|---|---|---|---|
| CMP-001 | Order service | Spring Boot REST service that owns order capture, credit check and audit | CON-001 · FACT-002 |
| CMP-002 | Pricing module | Pure domain module for line totals and discounts, no I/O | CON-001 |
| ADR-001 | Keep the Oracle schema, map it with JPA | Reuse ORDERS, ORDER_LINES, CUSTOMERS and ORDER_AUDIT as they are | FACT-001 · CON-002 |
