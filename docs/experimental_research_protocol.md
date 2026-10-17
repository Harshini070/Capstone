# GrievanceHub — Experimental Research Protocol

## 1. Research objective

Develop and evaluate a modular, Telugu-first framework for municipal complaint classification and analysis, initially supporting text-based inputs.

Because an authentic Hyderabad/GHMC Telugu complaint corpus is currently unavailable, the initial experiments will use the existing translated Bengaluru complaint dataset. Results will be reported as experimental findings and will not be presented as validation on authentic Hyderabad complaints.

## 2. Research questions

**RQ1 — Data quality:** What are the measurable characteristics and limitations of the translated experimental corpus?

**RQ2 — Classification:** How effectively can baseline NLP models categorize complaint text using the available source labels?

**RQ3 — Modular design:** Can preprocessing, taxonomy mapping, classification, and evaluation be implemented as independent, replaceable components?

**RQ4 — Translation limitations:** How do unresolved translation-quality issues affect the reliability of Telugu-text classification?

These questions may be refined after the initial EDA and baseline results.

## 3. Dataset and provenance

- Source: I Change My City Complaints Log (2019–2022), published on OpenCity.
- Geographic origin: Bengaluru.
- Source records: 16,071.
- Unique English title/description strings processed: 28,959.
- Translation direction: English to Telugu using AI4Bharat IndicTrans2.
- Structural reconstruction: 32,142 title/description cells matched to the source, including three whitespace-normalized matches.
- Translation-quality screening: 120 records flagged for human review.

The translated text is not an authentic Telugu-origin complaint corpus. Structural reconstruction does not establish semantic translation accuracy. Automated quality flags are not confirmed errors.

Raw, private, and release-candidate datasets must remain outside Git.

## 4. Experimental scope

The first implementation will focus on:

1. Corpus loading and schema validation.
2. Text normalization and duplicate analysis.
3. Category and taxonomy validation.
4. Complaint classification baselines.
5. Reproducible evaluation and error analysis.

Voice input, WhatsApp integration, and other communication channels are outside the initial experimental scope.

## 5. Data validation and EDA

Before modelling, record:

- Record and field counts.
- Missing and empty text values.
- Exact and normalized duplicate counts.
- Source category and subcategory distributions.
- Telugu-script coverage and non-Telugu text requiring review.
- Translation-review status.
- Privacy-review status.
- Label consistency and taxonomy mapping coverage.

EDA reports must distinguish source-language observations from observations made on machine-translated Telugu text.

## 6. Translation quality review

The 120 flagged translation records will be reviewed using the existing manual-review queue.

Each reviewed record should receive a documented decision, such as:

- Acceptable translation.
- Meaning altered or incorrect.
- Incomplete or corrupted source.
- Unclear and requiring further review.
- Not applicable to semantic translation assessment.

The reviewer must record the reason for the decision. Automated flags must not be treated as ground-truth error labels.

Human review of a sample of unflagged translations should also be considered to estimate whether the automated screening misses errors.

## 7. Taxonomy and labels

Preserve original source labels and provenance. Map them to the proposed GrievanceHub taxonomy using an explicit, versioned mapping table.

Each mapping should have:

- Original category and subcategory.
- Proposed target category.
- Mapping rationale.
- Review status.
- Reviewer decision, where available.

Do not silently force ambiguous or unmapped labels into a category. Report unresolved mappings separately.

The final classification label set must be frozen and documented before evaluation.

## 8. Train, validation, and test design

Prevent duplicate and near-duplicate complaint text from leaking across partitions.

1. Identify exact duplicates and normalized duplicates before splitting.
2. Group equivalent or near-duplicate records where appropriate.
3. Use a reproducible, stratified split when label distributions permit.
4. Keep the test set isolated from preprocessing choices, feature selection, and model tuning.
5. Record random seeds, split proportions, dataset version, and label version.

If grouped stratification is infeasible because of rare classes or insufficient records, document the chosen alternative and its limitations.

## 9. Baseline models

Start with simple, reproducible baselines before more complex neural models.

**Baseline A:** TF-IDF features with Logistic Regression.

**Baseline B:** TF-IDF features with Linear SVM.

Evaluate a pretrained Telugu-capable model only after establishing reliable labels and a baseline. Do not assume that model complexity guarantees better performance.

Fit vocabulary, feature selection, and other learned preprocessing exclusively on the training partition.

## 10. Evaluation

Report:

- Macro-F1 as a primary metric.
- Weighted-F1.
- Per-class precision, recall, and F1.
- Confusion matrix.
- Class distribution and test-set size.
- Performance variation or uncertainty where feasible.

Accuracy may be reported as a supplementary metric, but must not be the sole metric when classes are imbalanced.

Include error analysis for misclassified categories, ambiguous complaints, translated terminology, and unresolved label mappings.

## 11. Reproducibility and modularity

Implement independent components for:

- Dataset loading and schema validation.
- Text preprocessing.
- Taxonomy mapping.
- Dataset partitioning.
- Model training.
- Evaluation and error reporting.

Record configuration values, package versions, random seeds, input dataset version, label version, and experiment results.

Keep generated datasets, models, checkpoints, and complaint-level audit files out of Git unless an explicit, reviewed data-release decision permits otherwise.

## 12. Privacy, licensing, and governance

The existing redaction checks detected no remaining phone-like or email patterns, but they do not establish complete anonymization.

Contextual privacy review, semantic review, source-licence and derivative-redistribution review, and appropriate project or supervisor approval remain outstanding.

The experimental dataset is not approved for public release. Do not publish complaint-level records or claim that the dataset is anonymized solely because regex checks passed.

## 13. Limitations and research claims

The experimental corpus originates from Bengaluru and has been machine-translated into Telugu. It cannot establish the real-world performance of GrievanceHub on authentic Hyderabad/GHMC Telugu complaints.

The study must distinguish:

- Structural data validation from semantic correctness.
- Machine-translated Telugu from original Telugu.
- Source labels from reviewed target-taxonomy labels.
- Experimental benchmark performance from deployment readiness.
- Privacy-pattern screening from complete anonymization.

Authentic Hyderabad data acquisition remains a separate future dependency. Its unavailability does not justify misrepresenting the experimental corpus.

## 14. Immediate execution order

1. Validate the existing corpus schema and recorded EDA results.
2. Review translation-quality flags and taxonomy mapping issues.
3. Freeze the provisional label set and document unresolved labels.
4. Create a leakage-resistant train/validation/test split.
5. Run TF-IDF plus Logistic Regression and Linear SVM baselines.
6. Compare results, conduct error analysis, and document limitations.

**Current status:** Protocol drafted. Dataset quality review, final label freeze, and baseline experiments remain pending.
