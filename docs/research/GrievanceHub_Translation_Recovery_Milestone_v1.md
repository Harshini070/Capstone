# GrievanceHub: Translation Recovery Milestone

**Version:** 1.0
**Date:** 9 November 2026
**Status:** Experimental validation completed; training not approved.

## 1. Objective

Recover a small experimental translation checkpoint containing records that
previously failed mechanical translation validation. Preserve successful
translations and verify record-level lineage.

## 2. Experimental checkpoint composition

The final experimental checkpoint contains 232 records:

- 180 previously successful translations retained from the corrected candidate.
- 52 failed records recovered using greedy decoding.
- 232 unique text IDs.
- 232 non-empty translations.
- All records remain pending human review.

The source dataset is Bengaluru-origin. This experimental translation
checkpoint is not an authentic Telugu GHMC complaint corpus.

## 3. Recovery methodology

The recovery experiment used AI4Bharat IndicTrans2
(`ai4bharat/indictrans2-en-indic-dist-200M`).

- Source language: English (`eng_Latn`)
- Target language: Telugu (`tel_Telu`)
- Decoding strategy: Greedy decoding
- Number of beams: 1
- Sampling: Disabled
- Batch size: 4
- Title maximum generation length: 64
- Description maximum generation length: 128

The recovery experiment generated 52 replacement translations:
33 titles and 19 descriptions.

All 52 outputs reached the end-of-sequence token and passed the
experiment's mechanical validation checks.

## 4. Record-level lineage verification

The following checks passed:

- Source record identity preserved across the original, corrected, and
  recovered checkpoints.
- All 180 previously successful corrected translations remained unchanged.
- The 52 failed record IDs matched the validated greedy recovery outputs.
- All 52 recovered translation texts matched their corresponding greedy
  outputs.
- The final checkpoint contains 232 translated records.

The corrected candidate, rather than the original checkpoint, was used as
the preservation baseline for the 180 successful translations.

## 5. Punctuation validation

A source-aware punctuation audit covered all 232 records:

- 201 records had no repeated trailing periods.
- 31 records preserved source ellipses exactly.
- Zero records had unexplained translation-only excessive trailing periods.

Source punctuation must be distinguished from punctuation introduced by
translation generation.

## 6. Limitations

- The exact model revision used in the recovery experiment was not pinned.
- Historical package versions are not fully established.
- EOS completion and mechanical validation do not establish semantic
  translation accuracy.
- Human review remains pending for all 232 records.
- Privacy clearance has not been granted.
- The checkpoint is not approved for model training or production.
- Telugu translation of Bengaluru complaints does not establish a
  representative Hyderabad/GHMC Telugu corpus.

## 7. Research disposition

**Decision:** Structurally validated experimental checkpoint;
not approved for training.

Further translation scaling must remain subject to data governance,
privacy clearance, reproducible model configuration, and an appropriate
semantic validation process.
