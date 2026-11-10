# GrievanceHub — Phase 4 EDA and Telugu NLP Pipeline

## 1. Objective

Phase 4 extends the completed corpus preparation and preprocessing work by conducting refined linguistic analysis and implementing a reusable Telugu NLP feature-engineering pipeline.

The objective is to establish reproducible text-quality analysis and modular NLP processing without modifying the original complaint records or bypassing existing privacy and training restrictions.

## 2. Dataset

- Dataset: Translated Bengaluru municipal complaints (experimental corpus)
- Records: 15,374
- Categories: 20
- Language: Telugu-translated text
- Input file: `translated_bengaluru_preprocessed_v1.csv`
- Original source: Bengaluru/BBMP-origin complaint dataset

This dataset is an experimental benchmark. It is not an authenticated Hyderabad/GHMC complaint corpus.

## 3. Refined EDA findings

### Missing values

- 15,246 missing values in `mapping_rationale` (99.17%).
- All other 24 columns contain no missing values.
- Telugu title and description fields are complete.

### Telugu linguistic analysis

| Metric | Title | Description |
|---|---:|---:|
| Mean Telugu-letter ratio | 99.65% | 99.46% |
| Mean Latin-letter ratio | 0.35% | 0.54% |
| Mean Telugu tokens | 6.37 | 28.19 |
| Mean unique Telugu tokens | 6.17 | 25.00 |
| Mean lexical diversity | 0.9855 | 0.9333 |
| Mean punctuation ratio | 67.23% | 36.28% |

Records with Telugu-letter coverage below 50%:
- Titles: 25 (0.16%).
- Descriptions: 13 (0.08%).

These are screening indicators and do not establish translation correctness.

### Text-quality anomalies

| Indicator | Records |
|---|---:|
| Titles with period runs of at least 10 | 12,244 |
| Descriptions with period runs of at least 10 | 8,218 |
| Records flagged in either field | 13,106 |
| Records with low Telugu coverage in either field | 31 |

Repeated punctuation is retained in the original text. No automatic complaint deletion or punctuation removal is performed.

## 4. NLP pipeline implementation

Implemented modules:

- `normalization.py`: Unicode NFC and whitespace normalization.
- `tokenization.py`: Unicode-aware Telugu token extraction.
- `feature_extraction.py`: character, token, script, punctuation and repetition features.
- `quality_checks.py`: non-destructive text-quality indicators.
- `pipeline.py`: integrated record-level and batch processing.

Pipeline version: `telugu_nlp_pipeline_v1`.

The implementation uses Python standard-library functionality and does not require an additional NLP package.

## 5. Feature engineering

The pipeline generates 26 derived features:

- Title: 11 features.
- Description: 11 features.
- Combined title and description: 4 features.

Features include text length, Telugu token counts, unique token counts, lexical diversity, Telugu and Latin letter ratios, punctuation ratios, maximum repeated-period runs, repeated-character runs and quality flags.

The generated CSV contains 32 columns:
- 6 metadata and provenance columns.
- 26 derived feature columns.

Complaint text is not included in this output.

## 6. Automated testing

Nine automated tests passed.

Tests cover:
- Unicode normalization.
- Telugu tokenization.
- Feature extraction.
- Repeated-period detection.
- Quality flags.
- Original text preservation.
- Pipeline versioning.
- Duplicate record rejection.
- Missing record ID rejection.

## 7. Full-dataset validation

| Validation | Result |
|---|---:|
| Input records | 15,374 |
| Output records | 15,374 |
| Output columns | 32 |
| Derived features | 26 |
| Unique record IDs | 15,374 |
| Duplicate IDs | 0 |
| Missing output cells | 0 |
| Categories | 20 |
| Training-eligible records | 0 |

The local pipeline reproduced the six principal anomaly counts from the Colab feature-engineering analysis.

This establishes aggregate-level reproducibility. Row-level feature equivalence has not yet been independently established.

## 8. Privacy and data governance

All 15,374 records remain:
- Release status: `HOLD`.
- Training eligibility: `NOT_CLEARED`.

No training dataset is approved by this milestone. The feature pipeline is an analytical and engineering artifact, not authorization to train or publish complaint data.

## 9. Limitations

- The corpus originates from Bengaluru, not Hyderabad.
- The taxonomy remains provisional.
- Unicode-based tokenization is not a linguistically validated Telugu morphological tokenizer.
- Automated script checks cannot establish translation quality.
- Repeated punctuation requires further investigation and controlled normalization experiments.
- No supervised model training is claimed.
- Human privacy review and data-release clearance remain pending.

## 10. Next phase

The next implementation phase will focus on integrating the reusable NLP pipeline into the modular GrievanceHub backend, establishing API contracts, complaint ingestion, validation, taxonomy-based routing and storage interfaces.

The initial application remains Telugu-first and text-only. Voice AI is outside the current implementation scope.