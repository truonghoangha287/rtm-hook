# Facts and constraints

| ID | Kind | Statement | Source |
|---|---|---|---|
| FACT-001 | Fact | The Oracle 19c database stays in place during the transition; Forms and the new services run side by side | Infrastructure roadmap |
| FACT-002 | Fact | About 40,000 live motor policies, ~3,500 renewals and ~300 claims a month | Production reports |
| FACT-003 | Fact | Rating factors are set by the actuarial team and change about twice a year | Actuarial pricing committee |
| CON-001 | Constraint | New services run on Java 21 and Spring Boot 3 | Enterprise architecture standard |
| CON-002 | Constraint | No schema changes in phase 1: new services use the existing tables and sequences | Migration plan, phase 1 |
| CON-003 | Constraint | Premium and referral decisions must be explainable to the regulator: the inputs and factors used are kept with the quote | Insurance conduct regulation |
