# Facts and constraints

| ID | Kind | Statement | Source |
|---|---|---|---|
| FACT-001 | Fact | The Oracle 19c database stays in place during the transition; Forms and the new service run side by side | Infrastructure roadmap |
| FACT-002 | Fact | Peak load is about 2,000 orders per day, 30 lines per order at most | Production AWR reports |
| CON-001 | Constraint | The new service runs on Java 21 and Spring Boot 3 | Enterprise architecture standard |
| CON-002 | Constraint | No schema changes in phase 1: the new service uses the existing tables | Migration plan, phase 1 |
