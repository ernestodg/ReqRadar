# Architecture

Radar is a modular monolith.

The backend owns auth, tenant scoping, import normalization, comparisons, impact detection, review workflow, and exports. PostgreSQL stores normalized snapshots rather than raw uploaded files. Workspace IDs are enforced on project access and all customer data flows through project ownership.

Impact scoring:

- Explicit relation: +60
- Reverse relation: +50
- Identifier reference: +45
- Same parent: +20
- High text similarity: +10 to +30

Scores become HIGH, MEDIUM, or LOW through configurable thresholds.
