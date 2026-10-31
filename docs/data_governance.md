# GrievanceHub Data Governance

**Last updated:** 2026-10-31
**Governance status:** Review pending
**Public release:** Not approved

## 1. Purpose

This document defines data-handling requirements for the GrievanceHub research project, which aims to develop a modular, Telugu-first municipal complaint management framework for Hyderabad and GHMC.

The current experimental dataset originates from Bengaluru and contains English complaints translated into Telugu. It must not be represented as authentic Hyderabad/GHMC complaint data.

## 2. Data classification and handling

| Data class | Examples | Handling |
|---|---|---|
| Raw source data | Original Bengaluru complaint CSV | Keep outside Git |
| Translation data | Completed English-to-Telugu translations | Keep outside Git |
| Experimental derivatives | Reconstructed and text-only datasets | Keep outside Git |
| Review data | Translation queues, privacy queues, exclusion manifests | Keep outside Git |
| Aggregate research outputs | Non-sensitive counts and summaries | Review before committing |
| Source code and methodology | Scripts, protocols, validation logic | May be committed after review |

Do not commit raw complaint records, translated complaint-level text, addresses, coordinates, privacy queues, or row-level audit files.

## 3. Source provenance and permitted use

The current experimental source is the I Change My City Complaints Log (2019–2022), published through OpenCity and associated with Janaagraha.

- Geographic origin: Bengaluru.
- Original records: 16,071.
- Translation direction: English to Telugu.
- Listed licence: Creative Commons Attribution-ShareAlike 2.0 Generic.
- Listed credits: Vivek Mathew and Haji Shariefullah.

The listed licence does not by itself establish that every proposed use or redistribution of the translated derivative has been approved. Licence obligations, attribution, share-alike requirements, and derivative redistribution conditions must be reviewed before release.

## 4. Privacy screening controls

Automated screening examined source and Telugu titles/descriptions, source location, and source address for:

- Email-like patterns.
- Indian mobile-like patterns.
- URLs.
- Aadhaar-like 12-digit patterns.

The screening identified 257 unique affected records, including 239 provisional experimental candidates.

A metadata-only review queue and exclusion manifest were created. All 239 affected candidates are held for manual privacy review.

The text-only derivative excludes these 239 candidate IDs and removes ward identifiers, ward names, locations, addresses, latitude, and longitude.

The resulting derivative contains 15,374 records. All remain pending manual privacy review.

## 5. Interpretation of screening results

Regex screening is a limited detection mechanism.

- A pattern match is not proof that the matched value is personal information.
- No pattern match is not proof that a record contains no personal information.
- Removing direct location fields does not eliminate contextual or indirect identification risks.
- Names, distinctive incidents, combinations of attributes, and other contextual identifiers may remain.

Therefore, `NO_REGEX_MATCH_PENDING_MANUAL_REVIEW` must never be interpreted as anonymized, privacy-cleared, or approved for release.

## 6. Access, storage, and retention

- Keep complaint-level data in controlled local or approved research storage.
- Restrict access to authorized project members.
- Do not place complaint text or detected personal values in logs, screenshots, issue trackers, or public repositories.
- Keep review queues metadata-only wherever possible.
- Do not transfer data to external services unless the applicable source terms, privacy requirements, and project approvals permit it.
- Define retention and deletion procedures before any public or external release.

## 7. Research and release approval gates

The following gates remain outstanding:

1. Human semantic review of machine-translated text.
2. Human review of proposed taxonomy mappings.
3. Contextual privacy review beyond regex screening.
4. Source licence and derivative redistribution assessment.
5. Assessment of applicable research ethics, consent, and institutional requirements.
6. Appropriate supervisor or project approval.
7. A documented decision specifying permitted research use and access.

No model-training or public-release approval is granted by structural validation or automated screening.

## 8. Release decision

**Current status: NOT APPROVED FOR PUBLIC RELEASE.**

- Privacy clearance: not granted.
- Taxonomy approval: not granted.
- Translation semantic approval: pending.
- Training approval: not granted.
- Derivative redistribution approval: pending.

The 15,374-record text-only derivative is a provisional research artifact. It is not an anonymized or approved public dataset.

## 9. Git and repository controls

Before every commit:

1. Inspect `git status`.
2. Stage only explicitly reviewed source code and documentation.
3. Inspect the staged file list.
4. Inspect the staged diff.
5. Confirm that no raw data, complaint text, translated corpus, privacy queue, exclusion manifest, or generated row-level audit file is staged.

Never use `git add .` for project milestone commits.

## 10. Governance review record

Governance decisions must be documented with the decision date, reviewer, evidence, scope, and any restrictions.

Until the required approvals are documented, all complaint-level derivatives remain restricted research artifacts and must retain their release hold.
