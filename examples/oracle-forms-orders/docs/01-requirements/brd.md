# Business requirements

Each requirement names the legacy object(s) it was recovered from.

| BR | Requirement | Legacy source | Priority |
|---|---|---|---|
| BR-001 | A clerk can capture an order with a customer and one or more product lines | FRM-001 | MUST |
| BR-002 | Any order line of 100 units or more gets a 10% volume discount | PLS-001 | MUST |
| BR-003 | An order is rejected when it would push the customer's open orders over their credit limit | PLS-002 · FRM-002 | MUST |
| BR-004 | Every create, change or delete of an order is recorded with who did it and when | PLS-003 | SHOULD |
