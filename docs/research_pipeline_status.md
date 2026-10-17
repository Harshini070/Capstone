# GrievanceHub Research Pipeline Status

## Project objective

GrievanceHub is a modular research framework for Telugu-language
municipal complaint management. The intended target is authentic
Telugu complaint data relevant to Hyderabad and GHMC.

## Experimental source dataset

The current experimental source is the I Change My City dataset
(2019–2022), obtained through OpenCity. The source contains
Bengaluru-related civic complaints.

Source resource:
https://data.opencity.in/dataset/i-change-my-city-data/resource/a60abf5c-3a15-4967-af32-c3074248580f

The resource lists Creative Commons Attribution-ShareAlike 2.0.
Redistribution and derivative-work obligations still require review.

The experimental dataset must not be described as authentic
Hyderabad/GHMC Telugu complaint data.

## Translation pipeline

- Model: AI4Bharat IndicTrans2
- Model identifier: ai4bharat/indictrans2-en-indic-dist-200M
- Language direction: English (eng_Latn) to Telugu (tel_Telu)
- Unique source strings processed: 28,959
- Source records reconstructed: 16,071
- Title and description cells structurally matched: 32,142
- Translation semantic review: pending

Structural matching verifies reconstruction, not translation accuracy.

## Quality and privacy controls

Automated translation screening flagged 120 records for review.
These are heuristic flags, not confirmed translation errors.

A separate public-release candidate was created with selected
location and source-identification fields excluded. Regex-based
phone and email screening passed after masking.

Regex screening does not prove anonymization. Contextual privacy
review, semantic review, source-permission assessment, and release
approval remain outstanding.

## Local research scripts

The repository contains scripts for:
- Source dataset inspection
- Taxonomy inventory construction
- Taxonomy mapping proposals and review finalization
- Translation queue preparation and validation
- Telugu translation
- Experimental corpus reconstruction

The scripts compile successfully under the currently tested
Python 3.11.9 environment. Compilation does not establish runtime
correctness or reproducibility.

The local IndicTransToolkit import currently fails with the installed
Transformers package. Local translation inference is therefore not
verified. The completed Colab translation output should not be
overwritten or regenerated as part of this repository review.

## Data handling

- Keep raw, interim, processed, and private research data out of Git.
- Do not commit complaint-level translation files or review queues.
- Commit reusable source code and reviewed documentation only.
- Inspect staged files and the staged diff before committing.

## Current release decision

Public release: NOT APPROVED.

Outstanding requirements:
1. Human semantic review of translations.
2. Contextual privacy review.
3. Confirmation of source licence and derivative redistribution terms.
4. Documented project or supervisor approval.
5. Acquisition and validation of authentic Telugu municipal complaints
   before making claims about GHMC Telugu corpus coverage.
