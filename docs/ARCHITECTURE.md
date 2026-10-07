# Architecture

Radar is a modular monolith.

The backend owns auth, tenant scoping, import normalization, comparisons, impact detection, review workflow, and exports. PostgreSQL stores normalized snapshots rather than raw uploaded files. Workspace IDs are enforced on project access and all customer data flows through project ownership.

FREE plan import behavior:

- Multiple requirement versions are permitted in a project.
- Each individual import is limited to 250 normalized requirements.

Impact scoring:

- Explicit relation: +60
- Reverse relation: +50
- Identifier reference: +45
- Same parent: +20
- High text similarity: +10 to +30

Scores become HIGH, MEDIUM, or LOW through configurable thresholds.
