# GrievanceHub EDA and Preprocessing Milestone v2

## 1. Purpose

This milestone records the comparative exploratory data analysis (EDA), baseline text normalization audit (P1), and punctuation/anomaly audit (P2) conducted for GrievanceHub.

The work establishes measurable characteristics of the available experimental corpus and documents preprocessing risks before model development.

## 2. Dataset provenance and scope

The source dataset is the *I Change My City Complaints Log (2019–2022)*, associated with Bengaluru and the BBMP context.

It is not a Hyderabad/GHMC complaint dataset and is not an authentic Telugu municipal corpus. Telugu text in the experimental derivative was generated through machine translation from the Bengaluru-origin English source.

Consequently:
- The dataset is suitable for controlled experimental analysis, subject to governance restrictions.
- Its taxonomy mappings are provisional and are not approved ground-truth labels.
- Results must not be presented as representative of Hyderabad residents or GHMC complaint patterns.
- Collection and validation of an authentic Telugu Hyderabad/GHMC corpus remain necessary research work.

## 3. Comparative EDA

The comparative analysis covered the original source, reconstructed translated dataset, experimental mapped dataset, and text-only unflagged derivative.

| Measure | Result |
|---|---:|
| Original source records | 16,071 |
| Reconstructed translated records | 16,071 |
| Experimental mapped records | 16,071 |
| Text-only unflagged records | 15,374 |
| Text-only retention | 95.66% |

The text-only derivative excludes 239 records held by the preliminary privacy regex screening and removes selected location and ward fields. It is not privacy-cleared.

### 3.1 Text characteristics

- Reconstructed Telugu title rows with Telugu-script presence: 99.66%.
- Reconstructed Telugu description rows with Telugu-script presence: 99.58%.
- Text-only rows were selected using Telugu-script presence criteria in both text fields.
- Latin characters remain in some selected rows: 216 title rows and 845 description rows contain Latin characters.
- Telugu-script presence does not establish that the complete text is Telugu or linguistically correct.

### 3.2 Translation length comparison

| Field | Mean English length | Mean Telugu length | Median expansion ratio |
|---|---:|---:|---:|
| Title | 44.12 | 237.73 | 4.848 |
| Description | 223.02 | 341.43 | 1.613 |

The expansion ratios describe character-length differences, not translation quality. The substantial title expansion warrants additional linguistic and formatting evaluation.

### 3.3 Duplicate and uniqueness observations

- Original title unique values: 13,579.
- Telugu title unique values: 13,052.
- Original description unique values: 15,346.
- Telugu description unique values: 15,240.

These counts describe exact text uniqueness under the analysis procedure. They do not establish semantic duplication.

Whole-row duplicate counts and text-pair duplicate excess are different measures and must not be conflated. Missing-cell percentages across datasets with different column counts are also not directly comparable.

## 4. P1 — baseline normalization audit

P1 applied an audit-only normalization procedure:
- Unicode NFC normalization.
- Removal of selected invisible formatting characters.
- Whitespace collapsing and trimming.

Observed changed-cell counts:
- English title: 759.
- English description: 5,034.
- Telugu title: 0.
- Telugu description: 0.

The procedure was applied in memory for measurement. It did not overwrite the source datasets or perform semantic correction, translation correction, punctuation deletion, or complaint removal.

## 5. P2 — punctuation and anomaly audit

P2 is a detection-only audit of the reconstructed Telugu text. It identifies suspicious patterns for further investigation; it does not automatically repair or delete text.

### 5.1 Corrected punctuation-density metrics

The v2 report distinguishes mean punctuation density from the fraction of rows exceeding the high-density threshold.

| Field | Mean punctuation density | High-density row fraction |
|---|---:|---:|
| Telugu title | 0.6699 (66.99%) | 0.7938 (79.38%) |
| Telugu description | 0.3591 (35.91%) | 0.4206 (42.06%) |

These are separate statistics. The high-density row fraction must not be described as mean punctuation density.

### 5.2 Other anomaly observations

| Indicator | Telugu title | Telugu description |
|---|---:|---:|
| Rows with repeated punctuation | 13,432 | 8,946 |
| Rows with long period runs | 12,744 | 8,432 |
| Rows dominated by periods | 12,731 | 6,641 |
| Rows with high punctuation density | 12,757 | 6,760 |
| Rows with repeated word sequences | 34 | 68 |
| Rows containing URLs | 3 | 32 |
| Rows longer than 500 characters | 8 | 1,876 |

Across the two fields:
- 14,546 records were flagged in at least one field.
- 9,243 records were flagged in both fields.
- 1,525 records were flagged in neither field.

A flagged record is an audit candidate, not automatically an invalid complaint. These heuristic indicators require interpretation and further validation.

## 6. Interpretation and limitations

1. The experimental corpus originates from Bengaluru, not Hyderabad.
2. Machine translation does not establish linguistic fidelity, local terminology coverage, or suitability for supervised training.
3. Telugu-script presence is not equivalent to fully Telugu text.
4. Punctuation heuristics identify patterns but do not establish the cause of an anomaly.
5. The audit does not establish that every record is free of personally identifiable information.
6. Regex screening can miss contextual identifiers and other sensitive information.
7. Taxonomy mappings remain provisional and require review.
8. No complaint-level data has been approved for model training or public release.

## 7. Governance and training status

The text-only derivative contains 15,374 records after preliminary regex-based exclusion. Its screening status remains `NO_REGEX_MATCH_PENDING_MANUAL_REVIEW`, and its training eligibility remains `PROVISIONAL_NOT_CLEARED`.

Privacy clearance has not been granted. Approved training records: 0.

The P1 and P2 procedures are audit-only. They do not modify the source data or grant privacy, release, or training approval.

## 8. Reproducibility artifacts

The following scripts and aggregate outputs support this milestone:

- `scripts/preprocess_text_audit.py`
- `reports/aggregate/preprocessing_audit_v1/`
- `scripts/compare_dataset_eda_v2.py`
- `reports/aggregate/comparative_eda_v2/`
- `scripts/preprocess_p2_anomaly_audit_v2.py`
- `reports/aggregate/preprocessing_p2_v2/`

The aggregate reports contain summary metrics rather than complaint-level text. The comparative EDA v2 output was checked against v1 for metric equality. The v2 P2 report separately records mean punctuation density and high-density row fraction.

## 9. Research conclusion and next work

The EDA and preprocessing audits establish a reproducible baseline and identify substantial punctuation and text-quality concerns in the machine-translated experimental data.

The next research priorities are:
- Obtain and document an authentic Telugu Hyderabad/GHMC complaint corpus with appropriate permissions.
- Establish Telugu linguistic validation and local terminology coverage.
- Resolve privacy and data-governance requirements before training or release.
- Review provisional taxonomy mappings before treating labels as ground truth.
- Define and validate preprocessing rules against approved data.
- Proceed to model training only after data and label eligibility are established.

**Milestone status:** EDA and preprocessing audits completed for the experimental Bengaluru-derived corpus. Authentic Telugu GHMC corpus acquisition, privacy clearance, linguistic validation, and training approval remain outstanding.

---

## 10. Phase 3 — Experimental Dataset Quality and Preprocessing

**Dataset version:** `translated_bengaluru_preprocessed_v1.csv`
**Input:** `translated_bengaluru_text_only_unflagged_v1.csv`
**Records:** 15,374
**Phase 3 status:** Quality and preprocessing audits completed

### 10.1 Final preprocessing methodology

The Phase 3 preprocessing script applies:

- Unicode NFC normalization.
- Whitespace normalization and trimming.

It deliberately does not perform punctuation deletion, digit deletion, Latin-script deletion, automatic truncation, automatic complaint deletion, or label merging.

| Validation | Result |
|---|---:|
| Records before preprocessing | 15,374 |
| Records after preprocessing | 15,374 |
| Unique record IDs | 15,374 |
| Duplicate record IDs | 0 |
| Missing Telugu titles | 0 |
| Missing Telugu descriptions | 0 |
| Telugu title cells changed | 0 |
| Telugu description cells changed | 0 |

No Telugu text changes were expected because the preceding Unicode audit found no NFC or selected invisible-character changes in the retained title and description fields.

### 10.2 Corrected Unicode punctuation audit

A corrected Unicode-category procedure was used to distinguish punctuation (P), symbols (S), combining marks (M), letters (L), and digits (N). This avoids incorrectly treating Telugu vowel signs and combining marks as punctuation.

| Metric | Telugu title | Telugu description |
|---|---:|---:|
| Mean punctuation density | 0.6723 | 0.3628 |
| Median punctuation density | 0.8060 | 0.3928 |
| 95th percentile | 0.9401 | 0.8889 |
| Rows containing punctuation | 13,723 | 14,804 |
| Total punctuation characters | 2,942,178 | 1,893,775 |
| Combining marks | 273,718 | 1,229,465 |
| Symbols | 47 | 394 |
| Letters | 364,882 | 1,634,374 |
| Digits | 4,329 | 21,833 |

These figures apply to the 15,374-record text-only derivative. They are not interchangeable with the earlier P2 metrics, which were calculated on the 16,071-record reconstructed dataset using a different procedure.

Punctuation density is an audit indicator, not proof of invalid text. Automatic punctuation deletion is not justified by these results.

### 10.3 Duplicate title-description pair investigation

| Metric | Result |
|---|---:|
| Total records | 15,374 |
| Unique Telugu title-description pairs | 14,733 |
| Repeated pair groups | 236 |
| Records in repeated groups | 877 |
| Excess repeated records | 641 |
| Largest repeated group | 74 |

Of the 236 repeated groups:
- 208 groups had one provisional target category.
- 28 groups had multiple provisional target categories.
- The 28 mixed-category groups contained 190 records.

No automatic deduplication was performed.

### 10.4 Translation collisions and source-label disagreements

The 28 mixed-category groups were traced to their English source pairs and original category metadata.

| Finding | Groups | Records |
|---|---:|---:|
| Multiple English source pairs collapsed into one Telugu pair | 7 | 118 |
| One English source pair with multiple target categories | 21 | 72 |
| Total mixed-category groups | 28 | 190 |

The largest translation-collision group contained 74 records derived from 11 distinct English source pairs. Its original source-category distribution included Street lighting, Streetlights, Electricity and Power Supply, and Traffic and Road Safety.

The provisional mapping retained 72 STREETLIGHT records, one ELECTRICITY record, and one TRAFFIC_SAFETY record.

The 21 single-source conflict groups indicate source-category disagreement, taxonomy ambiguity, or both. These records require human adjudication.

No records were automatically deleted or relabelled.

### 10.5 Taxonomy mapping consistency

| Validation | Result |
|---|---:|
| Source ID-title combinations | 41 |
| Combinations mapping to multiple target categories | 0 |
| Records in inconsistent ID-title mappings | 0 |
| Source IDs associated with multiple source titles | 2 |
| Source titles mapping to multiple target categories | 0 |

The mapping implementation is deterministic for the observed source ID-title combinations. This does not establish semantic correctness of the taxonomy.

**Source ID 15:**
- 4,996 records: Mobility - Roads, Footpaths and Infrastructure → ROAD_INFRASTRUCTURE.
- 12 records: Mobility - Roads, Public transport → PUBLIC_TRANSPORT.

The two titles map cleanly to separate target categories. The shared ID is documented as a source metadata inconsistency.

**Source ID 470:**
- 1,470 records.
- Source titles: Street lighting and Streetlights.
- Both map to STREETLIGHT.

This is treated as a naming variation.

### 10.6 Source provenance validation

The reconstructed dataset and final preprocessed derivative were compared using source record IDs. The comparison was restricted to the 15,374 retained records.

| Field | Mismatches |
|---|---:|
| English source title | 0 |
| English source description | 0 |
| Original source category ID | 0 |
| Original source category title | 0 |

**Result: PASS.**

All retained records preserve their original source text and source-category metadata. The 697 records absent from the final derivative are expected exclusions from the earlier experimental-candidate and privacy-screening selection process.

### 10.7 Phase 3 report validation

The consolidated Phase 3 report was checked against the preprocessed dataset using 15 independent numerical and governance checks.

**Result: 15/15 checks passed.**

This validates the selected reported figures and status fields. It does not establish translation quality, semantic label correctness, privacy clearance, or training eligibility.

## 11. Updated governance and experimental status

| Governance item | Status |
|---|---|
| Privacy clearance | NOT_GRANTED |
| Training approval | NOT_GRANTED |
| Model training eligibility | NOT_CLEARED |
| Human translation review | PENDING |
| Taxonomy approval | PROVISIONAL_NOT_APPROVED |
| Dataset release | HOLD |

The preliminary regex privacy screen does not establish that the dataset is free of personal or sensitive information. Faculty approval to continue using the translated corpus does not automatically grant privacy clearance or public-release permission.

## 12. Updated research direction

Faculty has approved continuing experimental work using the existing Bengaluru-derived, machine-translated Telugu corpus.

Accordingly:
- Continue dataset quality analysis and controlled experimental development using the existing corpus.
- Preserve the Bengaluru source provenance and machine-translation limitations in all research reporting.
- Do not describe the corpus as naturally collected Telugu GHMC data.
- Treat authentic Hyderabad/GHMC corpus collection as a separate future research and external-validity improvement, rather than a prerequisite for continuing the current experimental pipeline.
- Complete translation and taxonomy human review before treating labels as validated ground truth.
- Obtain appropriate privacy and training clearance before model training or release.

## 13. Phase 3 reproducibility artifacts

- `scripts/preprocess_experimental_dataset_v1.py`
- `reports/aggregate/preprocessing_final_v1/preprocessing_report_v1.json`
- `reports/aggregate/phase3_quality_v1/phase3_dataset_quality_report_v1.md`

The report contains aggregate metrics and audit findings rather than complaint-level text.

## 14. Updated milestone conclusion

The comparative EDA, P1 normalization audit, P2 anomaly audit, and Phase 3 experimental dataset quality and preprocessing work have been completed for the Bengaluru-derived translated Telugu corpus.

The final 15,374-record derivative preserves its retained source provenance and passes the selected structural, duplicate-analysis, taxonomy-consistency, and report-validation checks.

Translation collisions, source-label disagreements, human linguistic review, taxonomy semantic approval, and privacy clearance remain outstanding.

**Current milestone status:** Phase 1–3 data analysis and preprocessing completed for the experimental corpus. The dataset remains experimental and is not approved for model training or public release.

**Release decision:** HOLD.
