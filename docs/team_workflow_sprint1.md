# Sprint 1 — Team Workflow (4 Members)

## Roles (rotate if needed)
- **A1 — Corpus lead:** maintains source register, provenance, collection dates, and corpus version.
- **A2 — Collection lead:** gathers eligible public Telugu examples and manages voluntary submission workflow/consent records.
- **A3 — Annotation lead:** applies taxonomy and annotation guidelines; tracks disagreements.
- **A4 — Quality/privacy lead:** validates schema, checks duplicates, reviews privacy flags, and maintains audit logs.

## Collection rules
1. Every record must have a source register entry.
2. Do not copy content from restricted/private groups or accounts without permission.
3. For voluntary submissions, obtain explicit informed consent before research use.
4. Remove/hold direct identifiers; do not store contact details in the complaint CSV.
5. Keep translated BBMP examples in a separate experimental dataset.
6. Never fabricate records to meet the target count.

## First target
Aim for 300–500 eligible records as an initial pilot target, not as a claim of statistical representativeness. If only 100–200 valid records can be collected, report the actual number and limitations rather than padding the dataset.

## Daily handoff
- A1 records source and provenance.
- A2 adds source-eligible complaint examples.
- A3 labels category, subcategory, relevance, and priority.
- A4 validates, screens privacy, and returns issues.
- All changes are versioned; raw/private data is not committed to Git.

## Exit criteria
- Every row has a unique record_id and source reference.
- Source type, language/script, Hyderabad relevance, and consent/terms are recorded.
- No known direct identifiers in any release candidate.
- Uncertain labels remain UNASSIGNED or DISAGREEMENT.
- Dataset and audit report can be reproduced from documented steps.
