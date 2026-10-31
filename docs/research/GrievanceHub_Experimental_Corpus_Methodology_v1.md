# GrievanceHub Experimental Corpus Methodology v1

**Document status:** Research methodology record
**Dataset status:** Provisional experimental derivative — HOLD
**Release status:** Not approved
**Last updated:** 2026-10-31

## 1. Research objective

GrievanceHub is a modular, Telugu-first research framework for municipal complaint management, initially designed for text-based complaint processing.

The intended application context is Hyderabad and the Greater Hyderabad Municipal Corporation (GHMC). The current experimental dataset, however, originates from Bengaluru. It is used only to evaluate data-processing, taxonomy-mapping, and Telugu-text experimentation workflows. It does not establish performance on authentic Hyderabad or GHMC complaints.

## 2. Research questions

- **RQ1 — Corpus quality:** What are the structural, linguistic, translation, privacy, and label-quality characteristics of the experimental corpus?
- **RQ2 — Classification:** Can reproducible baseline NLP models classify the provisional complaint categories using the available Telugu text?
- **RQ3 — Modularity:** Can data validation, preprocessing, taxonomy mapping, classification, and evaluation operate as independent components?
- **RQ4 — Translation effects:** How do machine-translation limitations affect the reliability of Telugu complaint classification?
- **RQ5 — Data readiness:** What additional human review, privacy assessment, licensing review, and provenance evidence are required before model training or release?

## 3. Source dataset and provenance

The source is the *I Change My City Complaints Log (2019–2022)* published through OpenCity and associated with Janaagraha's I Change My City initiative.

- Geographic origin: Bengaluru.
- Original records: 16,071.
- Original fields: 17.
- Unique English title and description strings processed: 28,959.
- Original source encoding: cp1252.
- Translation direction: English (`eng_Latn`) to Telugu (`tel_Telu`).
- Translation model: AI4Bharat IndicTrans2 (`ai4bharat/indictrans2-en-indic-dist-200M`).

The source resource lists Creative Commons Attribution-ShareAlike 2.0 Generic and credits Vivek Mathew and Haji Shariefullah. The precise licence obligations and permission to redistribute the derivative remain subject to review.

The dataset is not an authentic Telugu-origin complaint corpus and is not a Hyderabad/GHMC dataset. Translating its text or mapping its labels to a proposed GHMC taxonomy does not change its geographic provenance.

## 4. Translation reconstruction and integrity

The completed translation output was recovered from the existing translation workflow and used to reconstruct the experimental corpus. The stale translation queue containing pending entries was not used as the source of completed translations.

Recorded reconstruction results:

- Reconstructed source records: 16,071.
- Structurally matched title and description cells: 32,142.
- Original source fields preserved and compared: 17.
- Source-field mismatches: 0.
- Translation reconstruction status: all 16,071 records reported as both fields matched.

Structural matching verifies record reconstruction and alignment. It does not establish semantic translation accuracy, grammatical quality, or preservation of complaint meaning.

## 5. Translation-quality screening

The translation review queue contains 28,959 unique text entries, of which 826 were flagged for review.

The recorded review-priority groups include:

- 706 entries flagged for question-mark patterns.
- 76 entries without Telugu script.
- 44 entries consisting entirely of question marks.

The remediation manifest contains 44 entries recommended for quarantine, 76 entries recommended for human review due to missing Telugu script, and other lower-priority review groups. These flags can overlap.

Record-level reconciliation established:

- 44 quarantine translation entries: 43 description entries and one title entry.
- These entries affect 43 unique complaint records because one complaint has both fields quarantined.
- The earlier severe trace contains 38 description entries.
- All 38 severe trace entries are included among the 43 quarantined description entries.

The experimental corpus builder excludes the 43 affected complaint records. It also identifies 69 complaint records with no Telugu script in at least one text field. These counts overlap and must not be added as though they were disjoint groups.

Automated flags are review indicators, not confirmed semantic translation errors. Human semantic review remains outstanding.

## 6. Taxonomy mapping methodology

A provisional mapping registry was constructed from the reviewed source-category inventory.

- Source category mapping entries: 45.
- Proposed mapped source records: 16,039.
- Records with unknown source category: 32.
- Mapping entries pending human review: 42.
- Mapping entries requiring manual review: 3.
- Records affected by the three manual-review mappings: 358.

The mapping uses a composite key consisting of normalized source category ID and normalized source category title. This is necessary because some source IDs are reused for different category titles.

The 32 records with unknown source categories remain unclassified. The three manual-review mappings are:

1. `Others` — 346 records; catch-all category.
2. `Covid 19` — 11 records; provisional public-health proposal.
3. `Proibition & Sale of Tobacco products, Plastic carry bags` — 1 record; mixed-label proposal.

The registry status is `PROVISIONAL_NOT_APPROVED`. The 237 source subcategory mappings remain pending. Initial experiments must use category-level labels only, and no proposed mapping should be described as validated ground truth.

## 7. Experimental corpus construction

The experimental corpus builder uses the reconstructed Bengaluru Telugu dataset and the provisional taxonomy registry.

The resulting experimental corpus contains 16,071 records and retains source provenance, Telugu and English text, mapping rationale, translation-quality indicators, candidate status, exclusion reasons, and release status.

Recorded construction counts:

| Measure | Records |
|---|---:|
| Total source records retained | 16,071 |
| Records with proposed category mappings | 16,039 |
| Unknown source category | 32 |
| Manual-review mapping records | 358 |
| Translation quarantine complaints | 43 |
| Records with no Telugu script in at least one field | 69 |
| Provisional experimental candidates before privacy hold | 15,613 |

The counts for exclusion reasons overlap. They must not be summed to derive a total number of excluded records.

All records remain on release hold. Candidate status indicates eligibility for further review, not approval for training.

## 8. Privacy screening and text-only derivative

A regex-based screening process examined six fields:

- Source title and description.
- Telugu title and description.
- Source location and address.

The patterns included email addresses, Indian mobile-like numbers, URLs, and Aadhaar-like 12-digit numbers.

The screening identified 257 unique affected complaint records, including 239 provisional experimental candidates. Pattern matches are not confirmed personal information, and regex screening cannot identify every form of personal or contextual information.

A metadata-only review queue and privacy exclusion manifest were created. The manifest places all 239 affected candidates on manual-review hold.

A text-only derivative was then constructed using the original experimental corpus and the privacy exclusion manifest.

Recorded derivative characteristics:

- Records: 15,374.
- Columns: 22.
- English and Telugu title/description retained.
- Ward identifiers, ward names, source locations, addresses, latitude, and longitude excluded.
- The 239 privacy-held candidate IDs excluded.
- Records with no regex matches: 15,374.
- Manual privacy clearance: 0.
- Approved training records: 0.
- Release status: `HOLD`.

`NO_REGEX_MATCH_PENDING_MANUAL_REVIEW` means only that the configured patterns did not match. It does not mean that a record is anonymized or privacy-cleared.

## 9. Validation and quality assurance

The experimental corpus validator passed its recorded structural checks, including record counts, unique identifiers, required columns, source provenance, mapping status, exclusion reasons, and release holds.

The text-only derivative validation passed its recorded checks:

- 15,374 rows.
- Unique record identifiers.
- All records traceable to the original candidate pool.
- No privacy-held identifiers included.
- No ward, address, location, latitude, or longitude columns.
- English and Telugu title/description preserved.
- Mapping status remains pending human review.
- No record marked privacy-cleared.
- All records remain on release hold.

These checks establish structural consistency against the specified validation rules. They do not establish semantic translation correctness, label validity, legal permission, or complete privacy protection.

## 10. Experimental scope and model-training gate

The intended initial NLP experiments are:

1. Corpus loading and schema validation.
2. Text normalization and duplicate analysis.
3. Category-level taxonomy validation.
4. Leakage-resistant dataset partitioning.
5. TF-IDF with Logistic Regression.
6. TF-IDF with Linear SVM.
7. Reproducible evaluation and error analysis.

Model training must not begin on the current derivative as though its labels and text were validated ground truth. Before a defensible baseline experiment, the team must define and document an acceptable reviewed subset, resolve label decisions, assess privacy, and establish the permitted research use of the source and derivative.

Any later experimental results must clearly identify the dataset version, language origin, translation status, label status, exclusions, split strategy, random seeds, and limitations.

## 11. Modularity and reproducibility

The implementation should retain independent components for:

- Dataset loading and schema validation.
- Text normalization and preprocessing.
- Taxonomy mapping.
- Quality and privacy screening.
- Dataset partitioning.
- Model training.
- Evaluation and error analysis.

Record configuration values, package versions, random seeds, input dataset version, taxonomy version, and experiment results.

Raw data, translated complaint-level datasets, privacy queues, exclusion manifests, and generated row-level audit files must remain outside Git. Only reviewed code and non-sensitive documentation should be committed.

## 12. Governance and release restrictions

The following requirements remain outstanding:

- Human semantic review of translations.
- Human review of provisional category mappings and unresolved labels.
- Contextual privacy review beyond regex screening.
- Source licence and derivative redistribution review.
- Assessment of applicable research ethics, consent, and data-governance requirements.
- Appropriate project or supervisor approval.
- Acquisition and validation of authentic Telugu municipal complaints relevant to Hyderabad/GHMC.

The current experimental corpus and its text-only derivative are not approved for public release. The 15,374-record derivative is not approved training data.

## 13. Limitations and interpretation

The current experimental corpus has several material limitations:

1. It originates from Bengaluru, not Hyderabad.
2. Its Telugu text is machine-translated from English rather than collected as original Telugu complaints.
3. Structural reconstruction does not demonstrate semantic translation accuracy.
4. Proposed taxonomy mappings have not received final human approval.
5. Regex screening does not establish anonymization.
6. The listed source licence and derivative redistribution conditions have not been cleared.
7. No records have been approved for model training or public release.

The work completed so far establishes a reproducible experimental data-preparation and validation pipeline. It does not establish deployment readiness or performance on authentic GHMC complaints.

## 14. Current decision

**Dataset status:** Provisional experimental derivative — HOLD.
**Privacy clearance:** Not granted.
**Taxonomy approval:** Not granted.
**Training approval:** Not granted.
**Public release:** Not approved.

The next research milestone is controlled human review and governance assessment, followed by a documented decision on whether a restricted experimental subset can be used for baseline evaluation.
