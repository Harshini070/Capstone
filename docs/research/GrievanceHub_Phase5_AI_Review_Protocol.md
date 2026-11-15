# GrievanceHub Phase 5: AI-Assisted Corpus Review Protocol

| Item | Value |
|---|---|
| Protocol version | `ai_review_protocol_v1` |
| Review method | `AI_ASSISTED` (no human annotation) |
| Default reviewer model | `claude-opus-5-5` (each pass records the model that actually ran it) |
| Taxonomy | `configs/taxonomy_mapping_provisional_v1.json`, version 1.0, `PROVISIONAL_NOT_APPROVED` |
| Dataset under review | `translated_bengaluru_preprocessed_v2_cleaning_candidate.csv` (15,374 records) |
| Written | 2026-11-15, before any review decision was made |

## 1. Disclosures (must accompany any use of the results)

1. Every review decision is made by an AI model. **There is no human annotation** in this phase.
2. Two AI passes measure **self-consistency only**. Agreement between them is not inter-annotator reliability and is not ground truth.
3. The corpus is **a translated experimental corpus derived from Bengaluru/BBMP municipal complaint data** (machine-translated with `ai4bharat/indictrans2-en-indic-dist-200M`). It is not authentic Hyderabad/GHMC citizen complaint data. Results do not establish performance on authentic Telugu complaints.
4. The taxonomy stays provisional. A review may *recommend* a mapping change, but it never applies one.

## 2. What the reviewer sees

Each batch input row contains only:

- `record_id`
- `given_category`: the provisional target label, mapped from the citizen's Bengaluru source category
- `source_category_title`: the citizen's original Bengaluru category
- `source_title`, `source_description`: the original English text
- `telugu_title_cleaned`, `telugu_description_cleaned`: the Telugu translation after artifact cleaning

The reviewer is **not** shown:

- S3 model suggestions or probabilities, to avoid anchoring;
- any earlier pass's answers (pass 2 is blind);
- the reason a record was selected (random sample or flag).

## 3. Category definitions for the review

These definitions describe how the provisional categories are applied *during review*. They are review conventions, not taxonomy changes.

| Code | Name | Use for | Typical confusions and how to resolve them |
|---|---|---|---|
| ROAD_INFRASTRUCTURE | Roads and Footpaths | Potholes, damaged or unfinished roads, footpath damage or obstruction, road repair or digging | Water standing on a road because a **drain** is blocked → STORMWATER or SEWERAGE_DRAINAGE. Encroachment of a **public road by buildings** → PUBLIC_INFRASTRUCTURE only if the complaint is about public property rather than the road surface |
| SOLID_WASTE | Solid Waste Management | Garbage not collected, dumping, burning of waste, overflowing bins, debris | Open urination or defecation, or public toilets → PUBLIC_SANITATION. Smoke from burning garbage: SOLID_WASTE if the complaint is about the waste, POLLUTION if it is about the smoke or air |
| PUBLIC_SANITATION | Public Sanitation and Hygiene | Public toilets, open urination or defecation ("yellow spot"), general unhygienic public spaces | Garbage heaps → SOLID_WASTE. Sewage overflow → SEWERAGE_DRAINAGE |
| STREETLIGHT | Street Lighting | Streetlights not working, damaged or missing; lights on during the day | Power cuts, transformers, hanging wires → ELECTRICITY |
| ELECTRICITY | Electricity and Power | Power supply, outages, transformers, electric poles, dangerous wires | Streetlights → STREETLIGHT |
| WATER_SUPPLY | Water Supply | Drinking-water supply, no water, contaminated supply, pipeline leaks | Sewage or wastewater → SEWERAGE_DRAINAGE |
| SEWERAGE_DRAINAGE | Sewerage and Drainage | Sewage overflow, blocked sewers or drains carrying wastewater, manholes | Rainwater flooding or storm drains → STORMWATER |
| STORMWATER | Stormwater and Flood Management | Storm-water drains, rainwater flooding, waterlogging after rain | Sewage → SEWERAGE_DRAINAGE |
| TRAFFIC_SAFETY | Traffic and Road Safety | Signals, parking, congestion, speed breakers, zebra crossings, dangerous driving | Road surface damage → ROAD_INFRASTRUCTURE |
| ANIMAL_SERVICES | Animal Control and Services | Stray dogs, cattle, monkeys, dog bites, animal carcasses | — |
| POLLUTION | Pollution and Environmental Nuisance | Air, noise or dust pollution, smoke, industrial emissions | See SOLID_WASTE |
| PARKS_GREENSPACE | Parks and Green Spaces | Parks, playgrounds, trees (falling, cutting, planting), gardens | — |
| PUBLIC_SAFETY | Public Safety and Crime | Theft, harassment, anti-social activity, unsafe areas | Traffic danger → TRAFFIC_SAFETY |
| PUBLIC_INFRASTRUCTURE | Community and Public Infrastructure | Public buildings, community halls, encroachment of public property, public works (PWD) | Road surface → ROAD_INFRASTRUCTURE |
| PUBLIC_TRANSPORT | Public Transport | Buses, bus stops and shelters, metro | — |
| LAKES_WATERBODIES | Lakes and Water Bodies | Lakes, tanks, ponds: pollution, encroachment, maintenance | — |
| CIVIC_DOCUMENTS | Certificates and Civic Documentation | Birth or death certificates, khata, property tax documents | — |
| FIRE_EMERGENCY | Fire Safety and Emergency Response | Fire incidents and fire safety (rare class, excluded from ML) | — |
| EMPLOYEE_GRIEVANCES | Employee Grievances | Grievances of municipal employees (rare class, excluded from ML) | — |
| SOCIAL_WELFARE | Social Welfare and Benefits | Pensions, ration cards (rare class, excluded from ML) | — |

The taxonomy also contains PUBLIC_HEALTH and REGULATORY_ENFORCEMENT. They are valid relabel targets but have no records in this dataset. `OTHER_REVIEW` and `UNKNOWN_SOURCE_CATEGORY` are placeholders and are **never** valid review outcomes.

**Primary-issue rule.** Judge the category by the complaint's main issue, as the citizen describes it in the English source. If two issues carry equal weight, use `AMBIGUOUS` and record the second issue in `secondary_category`. Do not guess the "real" department from outside knowledge.

## 4. Field guidance

| Field | Guidance |
|---|---|
| `translation_fidelity` | Compare the Telugu with the English source. PASS: the meaning is preserved. PARTIAL: the main complaint is preserved but some details are lost or garbled. FAIL: the main complaint is lost, changed or reversed. UNCERTAIN: cannot judge (for example, the source is unintelligible) |
| `telugu_grammar` | Readability for a Telugu reader. Transliterated English words such as రోడ్డు or స్ట్రీట్ లైట్ are acceptable |
| `translation_completeness` | Was the whole source translated? Truncation, or a description replaced by the title, counts as PARTIAL or INCOMPLETE |
| `missing_information` / `added_information` | NONE, MINOR (a detail) or MAJOR (changes what is being complained about, or where) |
| `category_correctness` | Is `given_category` right for the main issue? INCORRECT requires a clear, different main issue |
| `corrected_category` | Only with RELABEL. Must be an assignable code that differs from `given_category` |
| `geography_assessment` | SOURCE_REFERENCE_VALID if Bengaluru places are carried over correctly. **Never** replace Bengaluru places with Hyderabad ones, and never invent places |
| `privacy_assessment` | See section 5 |
| `pii_spans` | JSON list `[{"type", "field", "text"}]` for every personal identifier noticed. Required when PII_IDENTIFIED |
| `review_decision` | See section 6 |
| `error_type` | The main reason when the decision is not a clean ACCEPT |
| `evidence_source`, `evidence_telugu` | **Short verbatim quotes** (at most 300 characters) copied from the English source and the Telugu text that support the decision. The validator rejects quotes that do not appear in the text |
| `explanation` | 1–3 sentences, required for every decision except ACCEPT |

## 5. Privacy rules

| Situation | Assessment |
|---|---|
| Phone number, email address, a private individual's full name, house or door number with a street, vehicle registration of a private vehicle, Aadhaar-like number | PII_IDENTIFIED (list the spans) |
| A partial identifier that could identify a private person in context (for example, a first name plus a specific house) | POTENTIAL_PII |
| Public landmarks, roads, cross/main numbers, layouts, wards, businesses, temples, government offices, officials named in their official role | NO_OBVIOUS_PII |
| Cannot tell | UNCERTAIN |

POTENTIAL_PII, PII_IDENTIFIED and UNCERTAIN all **quarantine** the record (`QUARANTINED_PRIVACY`). Only an explicit NO_OBVIOUS_PII can let a record into the ML dataset. A regex miss is never clearance.

## 6. Decision rules

| Decision | When |
|---|---|
| ACCEPT | Category correct, translation PASS, no meaningful problems. `error_type` = NONE |
| ACCEPT_WITH_MINOR_ISSUES | Category correct; minor translation, grammar or artifact issues that do not change the complaint |
| RELABEL | Translation usable (PASS or PARTIAL) and the main issue clearly belongs to another category. Requires `corrected_category` and an `error_type` of SOURCE_LABEL_NOISE (the citizen picked the wrong category) or CATEGORY_MAPPING_ERROR (the source category itself maps wrongly) |
| AMBIGUOUS | Two or more issues of equal weight, or the category boundary is genuinely unclear |
| REJECT | Translation FAIL, meaning shift, out-of-scope text, junk, or unusable content |
| ESCALATE | Evidence insufficient for a reliable decision. Excluded from the primary dataset |

**Distinguish the error sources.** A wrong label caused by a bad translation is `TRANSLATION_MEANING_SHIFT`, not a relabel. A citizen choosing the wrong category is `SOURCE_LABEL_NOISE`. Many records from one source category that should all map elsewhere point to `CATEGORY_MAPPING_ERROR`, which is a recommendation only.

**Never:**
- rewrite or "fix" the complaint text;
- invent a location, ward, person or municipal context;
- approve a taxonomy change;
- fabricate a decision to finish a batch faster.

If a batch cannot be reviewed reliably, use a smaller batch size.

## 7. Workflow (`scripts/phase5_review_batches.py`)

1. `build-queue`: build the queue (done once; 1,972 records on 2026-11-15).
2. `export --pass 1 --size 25`: write `data/interim/review/batches/pass1/P1-B0001_input.csv`.
3. The reviewer writes `P1-B0001_output.json`: a JSON list with one object per input record, holding every field in `REVIEW_FIELDS` (`scripts/phase5_review_common.py`), with `batch_id`, `review_pass`, `review_method=AI_ASSISTED`, `reviewer_model`, `protocol_version` and an ISO-8601 `review_timestamp`.
4. `validate --pass 1 --batch-id P1-B0001`: schema, enums, cross-field rules, verbatim evidence, same record set. A validated batch is frozen: if its output changes afterwards, validation fails.
5. Repeat until the queue is empty, then `merge --pass 1` → `review_pass1.csv`.
6. Pass 2 (blind): `export --pass 2` produces batches in a seeded shuffled order. Each batch is reviewed by a **fresh subagent session** that receives only this protocol and its batch input file. It must not read `review_pass1.csv` or other batch outputs. Then `merge --pass 2`.
7. `phase5_review_consistency.py compare` → adjudication queue (records that disagree on any of `review_decision`, `category_correctness`, `corrected_category`, `privacy_assessment`, `translation_fidelity`).
8. `export --pass ADJUDICATION`: the adjudicator sees both pass summaries, re-reads the source and the Telugu text, and decides. It uses ESCALATE when it still cannot decide reliably; agreement is never forced. Then `merge --pass ADJUDICATION` and `phase5_review_consistency.py finalize`.

**Resuming.** `status` reports the last validated batch and how many records are pending. Export never repeats a record that is already in a batch for that pass.
