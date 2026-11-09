# GrievanceHub — Phase 3 Dataset Quality and Preprocessing Report

**Version:** 1.0
**Date:** 9 November 2026
**Dataset:** translated_bengaluru_preprocessed_v1.csv
**Status:** Experimental dataset; release HOLD

## 1. Objective

Phase 3 evaluates the structural integrity, text quality, taxonomy consistency, translation-related anomalies, source provenance, and preprocessing integrity of the experimental Telugu complaint dataset.

The objective is to prepare a reproducible, auditable dataset derivative without assuming that translated text or provisional labels are fully validated.

## 2. Dataset lineage

| Dataset | Records |
|---|---:|
| Original Bengaluru source dataset | 16,071 |
| Reconstructed Telugu dataset | 16,071 |
| Experimental translated dataset | 16,071 |
| Text-only unflagged derivative | 15,374 |
| Final preprocessed derivative | 15,374 |

The final derivative retains 95.66% of the reconstructed records. The 697 excluded records were removed during the earlier experimental-candidate and privacy-screening selection process.

**Provenance limitation:** The corpus originates from Bengaluru/BBMP complaints translated from English into Telugu. It is not a naturally collected Telugu GHMC complaint corpus.

## 3. Preprocessing methodology

The final preprocessing pipeline applies:

- Unicode NFC normalization.
- Whitespace normalization and trimming.

The following operations were deliberately not performed:

- Punctuation deletion.
- Digit deletion.
- Latin-script deletion.
- Automatic text truncation.
- Automatic complaint deletion.
- Label merging.

The pipeline preserves the original 22 dataset fields and adds preprocessing and governance metadata.

### Preprocessing validation

| Check | Result |
|---|---:|
| Records before | 15,374 |
| Records after | 15,374 |
| Unique record IDs | 15,374 |
| Duplicate record IDs | 0 |
| Missing Telugu titles | 0 |
| Missing Telugu descriptions | 0 |
| Telugu title text changed | 0 |
| Telugu description text changed | 0 |

No text changes were expected because the preceding Unicode audit found no NFC or selected invisible-character normalization changes in the Telugu title and description fields.

## 4. Unicode and text-quality audit

Corrected Unicode-category analysis was used to distinguish punctuation from combining marks and symbols.

| Metric | Telugu title | Telugu description |
|---|---:|---:|
| Mean punctuation density | 0.6723 | 0.3628 |
| Median punctuation density | 0.8060 | 0.3928 |
| 95th percentile | 0.9401 | 0.8889 |
| Rows containing punctuation | 13,723 | 14,804 |
| Punctuation characters | 2,942,178 | 1,893,775 |
| Combining marks | 273,718 | 1,229,465 |
| Symbols | 47 | 394 |
| Letters | 364,882 | 1,634,374 |
| Digits | 4,329 | 21,833 |

The earlier regular-expression-based punctuation audit incorrectly included Telugu combining marks and vowel signs. Its density figures are superseded by this corrected Unicode-category audit.

Punctuation density is an anomaly indicator, not proof of corruption. Automatic punctuation removal is therefore not justified.

### Text length observations

- 1,724 descriptions exceed 500 characters.
- 45 descriptions exceed 1,000 characters.
- Long descriptions were found to contain potentially meaningful complaint details.
- Automatic truncation was not performed.

## 5. Duplicate-pair analysis

| Metric | Result |
|---|---:|
| Total records | 15,374 |
| Unique Telugu title-description pairs | 14,733 |
| Repeated pair groups | 236 |
| Records in repeated groups | 877 |
| Excess repeated records | 641 |
| Largest repeated group | 74 records |

Of the 236 repeated groups:

- 208 groups had one provisional target category.
- 28 groups had multiple provisional target categories.
- The 28 mixed-category groups contained 190 records.

Duplicate complaint text does not necessarily imply duplicate source records. No automatic deduplication was performed.

## 6. Mixed-category investigation

The 28 mixed-category groups were investigated against their English source text and original category metadata.

| Finding | Groups | Records |
|---|---:|---:|
| Multiple English source pairs collapsed into one Telugu pair | 7 | 118 |
| One English source pair with multiple target categories | 21 | 72 |
| Total mixed-category groups | 28 | 190 |

### 6.1 Translation collisions

Seven groups contained different English source pairs that became identical Telugu title-description pairs.

The largest collision group contained 74 records derived from 11 distinct English source pairs.

Its original source-category distribution was:

- Street lighting: 46
- Streetlights: 26
- Electricity and Power Supply: 1
- Traffic and Road Safety: 1

The provisional target mapping retained 72 STREETLIGHT records, one ELECTRICITY record, and one TRAFFIC_SAFETY record.

This demonstrates that translation collisions can obscure source-level distinctions.

### 6.2 Source-label disagreement

Twenty-one groups contained one English source pair but multiple original category labels and multiple provisional target categories.

These conflicts originate in the source-category assignments, taxonomy ambiguity, or both. They require human adjudication.

No automatic label correction was performed.

## 7. Taxonomy mapping consistency

| Validation | Result |
|---|---:|
| Source ID-title combinations | 41 |
| Combinations mapping to multiple targets | 0 |
| Records in inconsistent ID-title mappings | 0 |
| Source IDs with multiple source titles | 2 |
| Source titles mapping to multiple target categories | 0 |

The mapping implementation is deterministic for all observed source ID-title combinations. This does not establish semantic correctness of the proposed categories.

### Source ID 15

- 4,996 records: Mobility - Roads, Footpaths and Infrastructure → ROAD_INFRASTRUCTURE.
- 12 records: Mobility - Roads, Public transport → PUBLIC_TRANSPORT.

The split is cleanly separated by source title. The shared ID should remain documented as a source metadata inconsistency.

### Source ID 470

- 1,470 records.
- Source titles: Street lighting and Streetlights.
- Both map to STREETLIGHT.

This is treated as a naming variation.

## 8. Source provenance validation

The reconstructed dataset and final preprocessed derivative were compared using source record IDs.

The comparison was restricted to the 15,374 retained records.

| Field | Mismatches |
|---|---:|
| English source title | 0 |
| English source description | 0 |
| Original source category ID | 0 |
| Original source category title | 0 |

**Result: PASS.**

All retained records preserve their original source text and source-category metadata. The 697 records not present in the final derivative are expected exclusions from the earlier filtering process.

## 9. Dataset governance and release restrictions

The dataset remains subject to the following restrictions:

| Governance item | Status |
|---|---|
| Privacy clearance | NOT_GRANTED |
| Training approval | NOT_GRANTED |
| Model training eligibility | NOT_CLEARED |
| Human translation review | PENDING |
| Taxonomy approval | PROVISIONAL_NOT_APPROVED |
| Release status | HOLD |

A preliminary privacy regex screen is not equivalent to manual privacy clearance. Faculty approval to use the translated corpus does not by itself establish privacy clearance or permission for public release.

## 10. Outstanding work

1. Complete human review of translation quality, including the 232 recovered translation records.
2. Review the 28 mixed-category duplicate groups.
3. Resolve the 21 source-label disagreement groups through documented adjudication.
4. Review the seven translation-collision groups.
5. Investigate source ID 15 metadata inconsistency.
6. Obtain and document the required privacy and training approvals.
7. Validate the provisional taxonomy semantically before supervised training.
8. Establish a versioned, approved training split only after governance clearance.

## 11. Phase 3 conclusion

Phase 3 produced a structurally validated, Unicode-normalized, text-only experimental Telugu dataset containing 15,374 records.

Source provenance is preserved for every retained record. Taxonomy mapping is deterministic across the observed source ID-title combinations. However, translation collisions, source-label disagreements, pending human review, and outstanding privacy and training approvals remain unresolved.

The dataset is suitable for continued controlled quality analysis and preparation of validation workflows. It is **not yet approved for model training or public release**.

---

**Report version:** 1.0
**Dataset version:** translated_bengaluru_preprocessed_v1
**Release decision:** HOLD
