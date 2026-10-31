# GrievanceHub Research Pipeline Status

**Last updated:** 2026-10-31
**Project status:** Experimental data preparation completed; research validation ongoing.

## 1. Project objective

GrievanceHub is a modular, Telugu-first framework for municipal complaint management. The intended target domain is Hyderabad and GHMC. The initial implementation is text-only.

The current experimental source is Bengaluru-origin data translated from English into Telugu. It is not authentic Hyderabad/GHMC complaint data.

## 2. Source and translation

- Source: I Change My City Complaints Log (2019–2022), OpenCity.
- Geographic origin: Bengaluru.
- Original records: 16,071.
- Original fields: 17.
- Unique English title/description strings translated: 28,959.
- Model: AI4Bharat IndicTrans2 (`ai4bharat/indictrans2-en-indic-dist-200M`).
- Direction: English (`eng_Latn`) to Telugu (`tel_Telu`).
- Reconstructed records: 16,071.
- Structurally matched title/description cells: 32,142.
- Original source-field mismatches: 0.

Structural reconstruction does not establish semantic translation accuracy.

## 3. Translation-quality review

- Translation review queue: 28,959 entries.
- Flagged entries: 826.
- Quarantine entries: 44.
- Quarantine entries affect 43 unique complaints: 43 descriptions and one title, with one complaint having both fields quarantined.
- The earlier severe trace of 38 description entries is fully contained in the 43 quarantined descriptions.
- Records with no Telugu script in at least one text field: 69.

These are automated screening results. Human semantic review remains pending.

## 4. Taxonomy mapping

The provisional registry contains:

- 45 source-category mappings.
- 16,039 records covered by proposed mappings.
- 32 records with unknown source categories.
- 42 mappings pending human review.
- 3 mappings requiring manual review.
- 358 records affected by manual-review mappings.
- 237 subcategory mappings pending review.

Registry status: `PROVISIONAL_NOT_APPROVED`.

Category-level mapping proposals are not validated ground truth. The 32 unknown records remain unclassified.

## 5. Experimental corpus

The experimental corpus contains 16,071 records.

| Measure | Count |
|---|---:|
| Proposed mapped records | 16,039 |
| Unknown source category | 32 |
| Manual-review mapping records | 358 |
| Provisional candidates before privacy hold | 15,613 |
| Translation quarantine complaints | 43 |
| Records with no Telugu script in at least one field | 69 |

Exclusion groups overlap. Their counts must not be added to calculate unique excluded records.

All records remain on release hold.

## 6. Privacy screening

Regex screening covered source and Telugu titles/descriptions, location, and address.

- Unique affected records: 257.
- Affected provisional candidates: 239.
- Candidate IDs placed on manual-review hold: 239.
- Privacy clearance granted: 0.

Regex matches are not confirmed personal information. No regex match does not establish anonymization.

## 7. Text-only derivative

Output: `data/processed/translated_bengaluru_text_only_unflagged_v1.csv`

- Records: 15,374.
- Columns: 22.
- English and Telugu title/description retained.
- Ward identifiers, ward names, location, address, latitude, and longitude excluded.
- Privacy-held candidate IDs excluded.
- Records with no configured regex matches: 15,374.
- Manual privacy clearance: 0.
- Approved training records: 0.
- Release status: `HOLD`.

The derivative is a provisional research artifact, not an approved training or public-release dataset.

## 8. Validation status

The experimental corpus validator passed its recorded structural checks.

The text-only derivative validator passed its recorded checks for row count, unique IDs, source traceability, privacy exclusions, text preservation, absence of location metadata, pending mapping status, and release holds.

These checks do not prove translation correctness, label validity, complete privacy protection, or legal permission.

## 9. Outstanding work

1. Human semantic review of translations.
2. Human review and approval of taxonomy mappings.
3. Contextual privacy review of candidate records.
4. Source licence and derivative redistribution assessment.
5. Research ethics and supervisor/project approval assessment.
6. Authentic Telugu municipal complaint acquisition relevant to Hyderabad/GHMC.
7. Define an approved research subset before model training.
8. Conduct leakage-resistant baseline experiments only after the required review gates.

## 10. Current decision

- Experimental data preparation: completed.
- Structural validation: passed.
- Translation semantic validation: pending.
- Taxonomy approval: pending.
- Privacy clearance: not granted.
- Training approval: not granted.
- Public release: not approved.

The current work demonstrates a reproducible experimental preparation pipeline. It does not establish deployment readiness or performance on authentic GHMC complaints.

## 11. Source attribution

Dataset: I Change My City Complaints Log (2019–2022)
Platform: OpenCity
Underlying source: Janaagraha I Change My City
Resource: https://data.opencity.in/dataset/i-change-my-city-data/resource/a60abf5c-3a15-4967-af32-c3074248580f
Listed licence: Creative Commons Attribution-ShareAlike 2.0 Generic
Listed credits: Vivek Mathew and Haji Shariefullah

Licence obligations and derivative redistribution permissions remain subject to review.
