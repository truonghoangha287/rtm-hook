# Test cases

| TC | Scenario | Expected | Requirement |
|---|---|---|---|
| TC-001 | Submit an order for an existing customer with two lines | Order and both lines are saved, 201 returned | BR-001 |
| TC-002 | A line of 100 units at 2.50 | Line total is 225.00 | BR-002 |
| TC-003 | A line of 99 units at 2.50 | Line total is 247.50 (no discount) | BR-002 |
| TC-004 | Customer with limit 1,000 and 900 open; new order of 200 | Order is rejected with "Credit limit exceeded" | BR-003 |
| TC-005 | Change an order's quantity | Audit row holds user, timestamp and old/new value | BR-004 |
| TC-006 | Delete an order | Audit row records the delete with user and timestamp; order is gone | BR-004 |
