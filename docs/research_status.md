# GrievanceHub â€” Research Status

Generated (UTC): 2026-10-17T10:39:09+00:00

## Research objective

GrievanceHub is a modular, Telugu-first research framework for
municipal complaint management. The initial implementation focuses
on text-based complaint processing.

## Experimental corpus

- Source: I Change My City Complaints Log (2019â€“2022), published on OpenCity.
- Source geography: Bengaluru; this is not authenticated Hyderabad/GHMC data.
- Original records: 16,071.
- Original fields: 17.
- Unique English title/description strings processed: 28,959.
- Translation model: AI4Bharat IndicTrans2
  (`ai4bharat/indictrans2-en-indic-dist-200M`).
- Translation direction: English (`eng_Latn`) to Telugu (`tel_Telu`).

## Recorded validation results

- All 16,071 source records were reconstructed.
- All 32,142 title/description cells were structurally matched,
  including three whitespace-normalized matches.
- Automated translation-quality screening flagged 120 records
  for human review.
- Recorded phone/email pattern checks passed on the redacted candidate.

Structural matching does not establish semantic translation accuracy.
Automated flags are review indicators, not confirmed errors.
Regex checks do not establish complete anonymization.

## Research limitations and governance

- Human semantic review remains pending.
- Contextual privacy review remains pending.
- Source licence and derivative redistribution obligations remain
  under review.
- Appropriate ethics, consent, and data-governance requirements
  must be assessed.
- Responsible project/supervisor approval has not been documented.
- Authentic Telugu municipal complaint acquisition relevant to
  Hyderabad/GHMC remains a separate research requirement.

## Release decision

**NOT APPROVED FOR PUBLIC RELEASE.**

The translated Bengaluru corpus is an experimental research artifact.
It must not be represented as authentic Hyderabad/GHMC complaint data.
The current evidence does not establish translation accuracy,
complete anonymization, or permission to redistribute the derivative.

## Data-handling rules

- Do not commit raw, private, translated, or candidate complaint CSVs.
- Do not commit row-level privacy or translation-review queues.
- Commit only reviewed code and non-sensitive documentation.
- Recheck staged files before every commit.

## Source attribution record

Dataset: I Change My City Complaints Log (2019â€“2022)
Platform: OpenCity
Underlying source: Janaagraha I Change My City
Source URL: https://data.opencity.in/dataset/i-change-my-city-data/resource/a60abf5c-3a15-4967-af32-c3074248580f
Listed licence: Creative Commons Attribution-ShareAlike 2.0 Generic
Listed credits: Vivek Mathew and Haji Shariefullah

The listed licence and the specific derivative's redistribution permissions
still require review before publication.
