# GrievanceHub EDA and Preprocessing Milestone v1

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
