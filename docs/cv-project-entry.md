# CV Project Entry

## MITRA Audit Framework — Python / Data Integrity / Observability

Built a read-only Python framework for auditing multi-source data quality with a fail-closed design. The system evaluates evidence in a fixed `REAL -> SYNC -> STAKEABILITY -> COSTS -> DB` pipeline and preserves explicit `PASS`, `PARTIAL`, `FAILED`, and `UNPROVEN` states rather than converting missing evidence into success.

Key engineering work:

- Designed deterministic stage-by-stage audit logic for event identity, synchronisation, staleness, data availability, explicit costs, and database consistency.
- Implemented conservative timing grades that separate measured freshness from proof of simultaneous executability.
- Added reproducible synthetic examples and unit tests covering stale data, missing timestamps, mismatched events, invalid odds, and database disagreement.
- Separated the public portfolio edition from private production infrastructure so no credentials, live endpoints, databases, or execution capability are exposed.
- Added automated GitHub Actions testing across multiple Python versions.

Evidence from one anonymised read-only observation window included 150 intervals, 283 retained samples, and 48 selected multi-source samples, with zero positive retained margins. The framework retained the negative result rather than manufacturing a positive conclusion.

### Short CV version

**MITRA Audit Framework — Python project**  
Built a fail-closed, read-only multi-source data audit framework covering synchronisation, staleness, evidence quality and database consistency. Implemented explicit uncertainty states, reproducible tests, synthetic examples and automated CI while keeping production infrastructure and credentials isolated from the public repository.
