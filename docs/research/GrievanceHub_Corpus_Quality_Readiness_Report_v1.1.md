# GrievanceHub Corpus Quality and Readiness Report

**Version:** 1.0
**Generated (UTC):** 2026-10-31T15:57:08.288274+00:00
**Project:** GrievanceHub: A Modular AI Framework for Telugu Municipal Complaint Management

## 1. Executive Summary

The current research dataset consists of 16,071 Bengaluru-origin municipal
complaints whose English titles and descriptions were machine-translated
into Telugu.

The translation pipeline processed 28,959 unique text entries and
reconstructed 16,071 complaint records.

Structural reconstruction is complete. However, semantic translation
validation, contextual privacy review, licensing assessment and
human approval remain outstanding.

**Release decision: BLOCKED_PENDING_REVIEW.**

This dataset must not be represented as an authentic Hyderabad or GHMC
Telugu complaint corpus.

## 2. Source Provenance

- Dataset: I Change My City Complaints Log (2019–2022)
- Publisher platform: OpenCity
- Underlying source: Janaagraha I Change My City
- Geographic origin: Bengaluru
- Original records: 16,071
- Original fields: 17
- Listed licence: Creative Commons Attribution-ShareAlike 2.0 Generic
- Listed credits: Vivek Mathew and Haji Shariefullah
- Source resource:
  https://data.opencity.in/dataset/i-change-my-city-data/resource/a60abf5c-3a15-4967-af32-c3074248580f

The source is not verified GHMC or Hyderabad-origin complaint data.
Taxonomy mapping does not change geographic provenance.

## 3. Translation Methodology

- Provider: AI4Bharat
- Model: ai4bharat/indictrans2-en-indic-dist-200M
- Direction: English (eng_Latn) to Telugu (tel_Telu)
- Unique translation records: 28,959
- Completed translation records: 28,959
- Empty translations: 0
- Human review pending: 28,959

Machine translation completion does not establish semantic accuracy.

## 4. Reconstruction Integrity

- Reconstructed complaints: 16,071
- Records with both fields matched: 16,071
- Empty Telugu titles: 0
- Empty Telugu descriptions: 0

The previous local integrity audit also established:
- All 17 original source fields were preserved.
- All 17 source fields had zero mismatches.
- Source row identifiers were unique.

These checks establish structural integrity, not semantic correctness.

## 5. Translation Quality Assessment

- Translation entries flagged: 826
- Unique flagged source strings: 796
- Entries without rule-based flags: 28,133
- Quarantined entries: 44
- Unique quarantined strings: 43

The previous remediation manifest identified:
- 44 all-question-mark outputs.
- 120 entries without Telugu script.
- 93 high question-mark-density entries.
- 103 long question-mark-run entries.
- 141 repeated-question-mark entries.

These categories overlap and must not be summed as independent failures.

## 6. Complaint-Level Quality Impact

- Total complaints: 16,071
- Complaints with at least one flagged field: 734
- Complaints without flagged fields: 15,337
- Complaints with both fields flagged: 105
- Complaints with at least one quarantined field: 43
- Complaints without quarantined fields: 16,028

The quarantine consists of 44 translation entries: 43 description entries
and one title entry. These affect 43 unique complaints, with one complaint
having both its title and description quarantined. The 38 severe description
translations identified in the earlier provenance trace are a subset of the
43 quarantined description entries.

Records without rule-based flags are unvalidated candidates for controlled
experimental evaluation. They must not be treated as semantically validated
translations or automatically approved training data.

## 7. Quarantine Provenance Reconciliation

The earlier provenance trace identified 38 severely malformed description
translations. The remediation manifest identified 44 quarantined translation
entries: 43 descriptions and one title.

Record-level comparison confirmed that all 38 severe trace IDs are included
in the 44 quarantined entries. All 38 severe descriptions were matched to
the reconstructed corpus.

The 44 translation entries affect 43 unique complaints because one
complaint has both its title and description quarantined. The difference
between the earlier 38-record trace and the 43-complaint reconciliation is
therefore explained by the broader quarantine scope.

## 8. Data Inclusion Policy

Provisional treatment:

1. Entries without rule-based flags may proceed to controlled experimental
   evaluation, subject to further checks.
2. Flagged entries require contextual human review.
3. All-question-mark translations must remain quarantined until corrected
   and reviewed.
4. Original source records must be preserved.
5. Exclusion must be implemented through explicit flags, not destructive
   deletion.

## 9. Privacy, Licensing and Governance

Outstanding blockers:

- Human semantic review of Telugu translations.
- Contextual privacy review of names, addresses, landmarks and indirect
  identifiers.
- Confirmation of licence and translated-derivative redistribution
  obligations.
- Ethics, consent and data-governance assessment.
- Documented team or supervisor approval.

Regex-based PII detection does not prove anonymization.

## 10. Research Limitations

- The source corpus originates from Bengaluru.
- Telugu text is machine-translated, not verified original Telugu submissions.
- Structural matching does not prove translation accuracy.
- Automated script and punctuation flags are heuristics.
- Unflagged records are not necessarily correct.
- The current evidence does not establish suitability for unrestricted
  model training or public release.

## 11. Final Readiness Decision

**Status: BLOCKED_PENDING_REVIEW**

The earlier 38-versus-43 discrepancy has been reconciled at the record-mapping
level. Semantic translation validation, privacy review, licensing assessment,
ethics review and approval remain outstanding.

The corpus is suitable for continued controlled research, audit development
and methodology evaluation, subject to the stated limitations.

It is not approved for public release or claims of authentic GHMC Telugu
complaint data.

## 12. Reproducibility

The report is based on the recovered translation dataset, reconstructed
corpus, translation remediation manifest and prior provenance/audit records.

Raw complaint data and row-level review artifacts must remain in controlled
storage and must not be committed to GitHub.
