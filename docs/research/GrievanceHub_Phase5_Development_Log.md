# GrievanceHub Phase 5: Development Log

A running record of every major step, decision and result in Phase 5. Entries are added as work happens. All figures are actual outputs of the scripts named; nothing is estimated or invented.

**Standing disclosures**
- The corpus is a translated experimental corpus derived from Bengaluru/BBMP municipal complaint data. It is not authentic Hyderabad/GHMC data.
- Phase 5 corpus review is AI-assisted. There is no human annotation.
- The taxonomy remains `PROVISIONAL_NOT_APPROVED`.

---

## 2026-11-15: Gate 1, repository and methodology audit (read-only)

**What was done:** a read-only inspection of the repository, the datasets, the taxonomy, the eligibility audit, the NLP code, the tests and Git. The figures were recomputed with a scratchpad script; nothing in the project changed.

**Findings**

*Historical figures reproduced*
- The historical Phase 5 baseline reproduces exactly from `translated_bengaluru_preprocessed_v1.csv`:
  - 15,374 records;
  - 13,107 with dot runs of 5 or more;
  - 2,475 with an identical title and description;
  - 877 records in 236 duplicate groups;
  - 0 eligible.
- The category counts match too: ROAD_INFRASTRUCTURE 5,108; SOLID_WASTE 3,870; FIRE_EMERGENCY 10; EMPLOYEE_GRIEVANCES 1; SOCIAL_WELFARE 1.

*Original source data*
- 16,071 × 17, cp1252 encoding; 0 Telugu-script and 16,038 Latin-script records; 43 categories.
- Two historical figures were reconciled by definition:
  - 220 subcategories counts titles (there are 211 subcategory ids);
  - 626 duplicate rows is case- and space-insensitive (586 case-sensitive).

*Translation*
- It was **completed**, which contradicts the brief's assumption that it never finished. All 28,959 queue strings are `TRANSLATED` by `ai4bharat/indictrans2-en-indic-dist-200M`; 120 strings contain no Telugu script.
- Translation quality has never been reviewed.

*From 16,071 to 15,374 records*
- 458 excluded:
  - 357 manual-review mappings;
  - 32 unknown category;
  - 43 question-mark-only translations;
  - 26 with no Telugu script.
- 239 held back by the regex privacy manifest.

*Review sample and taxonomy*
- The 522-record sample can be **rebuilt exactly** from `reports/phase5_telugu_quality_record_level.csv` (seed 42), with the same texts in the same order.
- The taxonomy has 45 mappings (42 pending, 3 manual-review) and 23 target codes, of which 20 occur in the working dataset.

**Decisions approved by the user (2026-11-15)**
- **C1:** add the eligibility states `QUARANTINED_PRIVACY` (first in precedence) and `AI_REVIEWED_QUALITY_BLOCKED`, so that a reviewed but privacy-quarantined or quality-failed record is never mislabelled `SCREENED_NOT_REVIEWED`.
- **C2:** pass 2 runs as a fresh subagent per batch, which sees only the protocol and its batch.
- **C3 (LaBSE):** not explicitly approved. Under the rule against installing large dependencies without approval, it was not installed, so the semantic signal is `NOT_EVALUATED`.
- Proceed with Gate 2.

---

## 2026-11-15: Gate 2, Phase 5 engineering

### Dependencies
- Installed `scikit-learn==1.9.1` into `.venv`. This pulled in `scipy==1.17.1`, `joblib==1.6.0` and `threadpoolctl==3.8.0`.
- Pinned scikit-learn and scipy in `requirements.txt`.
- Created `requirements-quality.txt`, which lists sentence-transformers as optional and not installed.

### Files created
| File | Purpose |
|---|---|
| `scripts/phase5_review_common.py` | Paths, review schema, allowed values, eligibility states, `validate_review_record`, `assign_eligibility` |
| `scripts/phase5_build_review_sample_v2.py` | S1 sample rebuild with verification |
| `scripts/phase5_corpus_screens.py` | S2 screens: privacy regex, exact and near duplicates, artifacts, text quality, translation signals, category preservation |
| `scripts/phase5_label_noise_detection.py` | S3 out-of-fold label-noise heuristic, fold validation, mapping concentration, flip self-check |
| `scripts/phase5_review_batches.py` | Review queue; batch export, validation, merge and status |
| `scripts/phase5_review_consistency.py` | S7 comparison, adjudication, final table, LaBSE threshold calibration |
| `scripts/phase5_apply_review_decisions.py` | S8 dataset v3 with an integrity check |
| `scripts/phase5_review_statistics.py` | S9 estimators, interval methods, synthetic validation |
| `docs/research/GrievanceHub_Phase5_AI_Review_Protocol.md` | Review protocol, written before any review |
| `tests/test_phase5_review.py` | 49 tests in 13 groups |

### Files modified
- `scripts/phase5_training_eligibility_audit.py`:
  - `main()` was renamed to `run_default_policy()`, with its logic unchanged;
  - a new `main()` adds `--policy {default, ai_assisted_v1}`;
  - `ai_assisted_v1` reads dataset v3 and re-checks the critical gates;
  - verified: the default policy's report is identical apart from its timestamp, and still shows 0 eligible.
- `requirements.txt`, `.gitignore` (record-level patterns for `reports/phase5_review/`) and `README.md` (status and a Phase 5 section).

### S1: review sample v2 (`phase5_build_review_sample_v2.py`)
- **522 records in 20 strata.** They match the original sample's cleaned texts **exactly and in order**, `record_id` is unique, and the candidate dataset's text equals the record-level text.
- Fully enumerated strata: EMPLOYEE_GRIEVANCES (1), FIRE_EMERGENCY (10), SOCIAL_WELFARE (1).
- Design: stratified SRSWOR by given label, `n_h = min(30, N_h)`, seed 42, inclusion probability `n_h/N_h`, weight `N_h/n_h`.
- Output: `data/interim/review/phase5_review_sample_v2.csv`, plus `reports/phase5_review/sample_v2_summary.json`.

### S2: automated screens (`phase5_corpus_screens.py`, 31 s)
**Privacy:** 2,264 records have at least one regex flag.

| Type | Matches |
|---|---|
| ADDRESS_PATTERN | 1,708 |
| PIN_CODE | 335 |
| VEHICLE_REGISTRATION | 260 |
| NAME_CUE | 149 |
| DOOR_NUMBER | 145 |
| INDIAN_MOBILE | 19 |

These numbers count records per type; the figures counted per field are larger.
- **Finding:** real mobile numbers written with a space (for example `98XXX XXXXX`; the real example is redacted here) are still in the working dataset. The upstream privacy manifest's pattern didn't allow a space inside the number, so it missed them. Such records will be quarantined unless reviewed.
- A spot-check showed that most ADDRESS_PATTERN and "Sri" NAME_CUE matches are locations or place names. As designed, they only set review priority.

**Duplicates:**
- 235 exact groups (880 records);
- 5,231 verified near-duplicate pairs;
- 14,683 dedup groups, of which 276 have more than one member (967 records); the largest has 76 records (an identical "street light not working" text).
- **Chaining check:** 0 groups have any pair below Jaccard 0.90, so union-find did not merge dissimilar texts.

**Artifacts:** 13,107 records had dot runs in the raw text; **6** still do after cleaning. There are 83 descriptions and 28 titles with repeated punctuation.

**Text quality:**
- 0 empty fields;
- 2,481 identical title and description. This differs from the historical 2,475 because S2 compares the *cleaned* text after NFC and whitespace normalisation, while the historical audit compared the raw text with case-folding only.
- 31 records with a Telugu ratio below 0.5; 6 very short.

**Translation signals:**
- Semantic (LaBSE): **NOT_EVALUATED** (not installed).
- Number mismatch: 936. Length-ratio flag: 307 (bounds p01–p99 = 0.710–1.716).
- Named-entity check: NOT_EVALUATED.

**Category preservation:**
- 1,152 records where the English source signal and the Telugu rule signal conflict;
- 816 where both signals agree with each other but disagree with the given label.

4,774 records have at least one flag. The taxonomy file's hash was unchanged.

### S3: label-noise detection (`phase5_label_noise_detection.py`, 208 s)
- **Folds:** 17 primary classes; the 12 rare-class records were not evaluated. StratifiedGroupKFold k=5 was **valid**: no group leakage, every record predicted exactly once, every class present in every fold. **No unsupported classes.**
- **Flags:** 977 records (42 in the random sample, 935 outside it).

  | Given category | Flagged |
  |---|---|
  | ROAD_INFRASTRUCTURE | 408 |
  | SOLID_WASTE | 163 |
  | PUBLIC_SANITATION | 121 |

  The most common given→suggested pairs are all from ROAD_INFRASTRUCTURE: to STORMWATER (87), SEWERAGE_DRAINAGE (73) and PUBLIC_INFRASTRUCTURE (63).
- **Mapping concentration:** 1 investigation. Source category "PWD" has 5 records, 4 of them (80%) flagged toward ROAD_INFRASTRUCTURE. The taxonomy was not changed; this is an AI investigation item for Gate 3.
- **Synthetic flip self-check:** 763 labels flipped on a copy. Recall of the injected flips was **0.612**; precision@763 was **0.434**. This is synthetic only, and real label noise in the data also produces flags.

### Review queue (`phase5_review_batches.py build-queue`)
**1,972 records:**
- 480 random-sample only;
- 42 both sample and flagged (reviewed once, origin `STRATIFIED_SAMPLE`, original weight kept);
- 935 S3 flags;
- 515 S2 conflicts where both signals disagree with the given label (all of those available).

The flagged-only total is 1,450, under the 1,500 cap. No review batches have been exported yet.

### S9 preparation: statistics validation (`phase5_review_statistics.py validate`)
The synthetic populations used the real S1 design, with 1,000 simulations per population and 500 bootstrap replicates.

- **First run, failed honestly.** At a true rate of 5%, the planned intervals under-covered: Taylor 0.896 and Rao–Wu percentile bootstrap 0.913, against a target of 0.93–0.97. The cause is that strata whose sample has 0 events contribute zero estimated variance.
- **Correction.** The primary interval was changed to **Korn–Graubard (1998)**: Clopper–Pearson at the design effective sample size, with a degrees-of-freedom adjustment. Taylor and Rao–Wu are kept as reported cross-checks.
- **Second run, passed.**

  | Population | Bias | Korn–Graubard coverage |
  |---|---|---|
  | 5% | −0.0003 | 0.935 |
  | 30% | +0.0013 | 0.957 |
  | Mixed 0–100% | −0.0007 | 0.947 |
  | All zero | 0 | 1.0 |

  - Wilson-with-correction per-stratum mean coverage: 0.945–0.963.
  - All hand-calculated checks pass.
  - Monte Carlo error on a coverage figure is about ±0.007 at 1,000 simulations, so 0.935 is close to the lower bound.

### Tests
`python -m unittest discover -s tests -t .` → **66 tests, all passing** (17 existing plus 49 new). Backend `npm test` → 11 passing.

### Not done in Gate 2 (by design)
- No AI review decisions (Gate 3).
- No dataset v3 (Gate 4).
- No real population estimates (Gate 4).
- No ML training (Gate 5).
- The milestone report `GrievanceHub_Phase5_AI_Review_Milestone.md` will be written at S9 from actual results, to avoid placeholder figures.

### Open items for the user
1. Approve Gate 3: running the AI review, starting with pass-1 batches of the 522-record sample.
2. LaBSE (about 1.8 GB): install, or keep `NOT_EVALUATED`.
3. Commit the Gate 2 work. Nothing is committed yet.

---

## 2026-11-15: Gate 2 committed; Gate 3 (AI review, pass 1) started

### Commit
- Gate 2 was committed to `main` as `0edb11a`: 23 files, staged by name, with a guard confirming no `.env`, `data/` or record-level files. Not pushed; pushing needs separate approval.
- The commit has no Claude attribution.

### User decisions
- Gate 3 approved.
- LaBSE: no explicit choice was given, so it was not installed and the semantic signal stays `NOT_EVALUATED`.

### Tooling change: `phase5_review_batches.py compile`
- The reviewer writes one line per record in `<BATCH>_review.psv`, a pipe-separated file of short codes (for example `PA` = PARTIAL, `AM` = ACCEPT_WITH_MINOR_ISSUES).
- Every judgement field is written explicitly for every record; there are no defaults.
- `compile` expands the codes into the JSON schema and fills in the identity fields (`batch_id`, `review_pass`, `review_method=AI_ASSISTED`, `reviewer_model=claude-opus-5-5`, `protocol_version`, UTC timestamp).
- The `.psv` file is kept beside each batch as the authored record.
- New test `test_compile_psv_expands_codes_and_validates`.

### Review conventions applied (consistent with the protocol)
- **Privacy is judged separately from content.** A record with personal identifiers gets its content decision (for example ACCEPT_WITH_MINOR_ISSUES) together with `error_type=PII` and privacy `PII_IDENTIFIED` or `POTENTIAL_PII`. The eligibility rules then quarantine it automatically. The content judgement is kept in case the record is redacted later.
- **What counts as an identifier:**
  - personal names, voter EPIC numbers and flat or door numbers → `PII_IDENTIFIED`;
  - property-tax SAS application numbers, PIDs and khata numbers → `POTENTIAL_PII` (they can be linked to an owner).
- **Detail-level mistranslations** that keep the main complaint (for example "spay" → "hunt", or past tense for a request) are recorded as fidelity `PARTIAL` with `TRANSLATION_MEANING_SHIFT`. Untranslated run-on fragments are recorded as `TRANSLATION_ARTIFACT`.
- **Artifacts noticed in the translation:**
  - "sterilise" is rendered as క్రిమిరహితం ("disinfect"), which loses the animal-sterilisation sense;
  - some property IDs are replaced by a `<ఐడీ1>` placeholder.

### Progress
| Batch | Records | Status |
|---|---|---|
| P1-B0001 | 25 (ANIMAL_SERVICES sample) | VALIDATED on the first attempt |
| P1-B0002 | 25 (ANIMAL_SERVICES / CIVIC_DOCUMENTS sample) | VALIDATED on the first attempt |
| P1-B0003 | 25 (CIVIC_DOCUMENTS / ELECTRICITY) | VALIDATED |
| P1-B0004 | 25 (ELECTRICITY / EMPLOYEE_GRIEVANCES / FIRE_EMERGENCY) | VALIDATED |
| P1-B0005 | 25 (FIRE_EMERGENCY / LAKES_WATERBODIES) | VALIDATED |
| P1-B0006 | 25 (LAKES_WATERBODIES / PARKS_GREENSPACE) | VALIDATED |
| P1-B0007 | 25 (PARKS_GREENSPACE / POLLUTION) | VALIDATED |
| P1-B0008 | 25 (POLLUTION / PUBLIC_INFRASTRUCTURE) | VALIDATED |

All 8 batches passed validation on the first attempt, including the verbatim-evidence check.

### Additional review conventions (2026-11-15)
- **Sensitive health disclosures** (for example, depression or self-harm statements by the complainant) are not identifiers, but they are special-category personal data. Privacy is recorded as `UNCERTAIN`, so the record is quarantined and never enters ML data. First case: BG-TEL-13706.
- **A first name alone**, or a commercial vehicle plate → `POTENTIAL_PII`. A name combined with property identifiers, a full address or a phone number → `PII_IDENTIFIED`.
- **Category definitions from the protocol are applied as written, even when the citizen's source category differs.** Examples:
  - public urination → PUBLIC_SANITATION;
  - a single streetlight → STREETLIGHT;
  - a bus-shelter design complaint → PUBLIC_TRANSPORT;
  - sewage into a well → SEWERAGE_DRAINAGE;
  - contaminated supply water → WATER_SUPPLY.
- **Texts with no usable complaint** are rejected with `INSUFFICIENT_CONTEXT`. Examples: "Not sterilised", "Rat, catterpillar and snake mess", a bare park name.
- **Recurring translation failure modes:**
  - typos translated literally ("lakh" → lakhs of people, "in vein" → a blood vessel, "nigh time" → near time);
  - place-name parts translated (Silk Board → silk board, Dodda → big);
  - degenerate repetition (BG-TEL-08743 "R. R. R. …", BG-TEL-06603);
  - inverted negations (BG-TEL-08774, BG-TEL-11265, BG-TEL-10573).

### Interim tally after 200 pass-1 reviews (sample records only; descriptive, not a population estimate)
- **Decisions:** ACCEPT_WITH_MINOR_ISSUES 114, ACCEPT 57, RELABEL 11, REJECT 10, AMBIGUOUS 8.
- **Translation fidelity:** PASS 117, PARTIAL 79, FAIL 4.
- **Privacy:** NO_OBVIOUS_PII 172, POTENTIAL_PII 15, PII_IDENTIFIED 12, UNCERTAIN 1.
- **Category correctness:** CORRECT 176, INCORRECT 12, AMBIGUOUS 8, UNCERTAIN 4.

These are pass-1 decisions only. The sample strata are reviewed in sorted category order, so these counts are not representative of the whole dataset. Population estimates come only from S9, after pass 2 and adjudication.

### Mapping investigation finding: "Yellow Spot" (2026-11-15, during P1-B0011)
- **What the review found.** Pass-1 review of the PUBLIC_SANITATION sample found that many records from the source category "Yellow Spot" are footpath or garbage complaints.
- **Source subcategories** (`data/external/bengaluru_complaints.csv`, all 948 "Yellow Spot" records):

  | Group | Subcategories (records) | Total |
  |---|---|---|
  | Sanitation | Public Urination or Yellow Spot (253 + 8); New Public Toilet (87 + 3); Dirty or Unusable Public Toilet (18 + 1 + 1) | 371 |
  | Footpath | Broken Footpath (175 + 29); New Footpath (103 + 8) | 315 |
  | Garbage | Garbage or Debris on Footpath (196 + 62) | 258 |
  | Other | Playing and Gym Equipment | 4 |

- **Conclusion.** About 61% of "Yellow Spot" records are not sanitation complaints. The provisional taxonomy maps at **category** level, so all 948 records were labelled PUBLIC_SANITATION.
- **Methodological limitation.** The S3 out-of-fold heuristic did not flag this mapping (S3 top concentration: Sanitation 31%, Yellow Spot below the threshold). Because hundreds of footpath records share the same wrong label, the model learns the error consistently. **Confident-learning-style heuristics cannot detect systematic mapping errors.** Category-level mapping errors need subcategory-level audits.
- **Recommendation (NOT applied; needs user approval and a new taxonomy version):** map "Yellow Spot" by subcategory:
  - footpath subcategories → ROAD_INFRASTRUCTURE;
  - garbage or debris on footpath → SOLID_WASTE;
  - urination and toilet subcategories → PUBLIC_SANITATION;
  - playing and gym equipment → PARKS_GREENSPACE.
- **Until a decision is made,** affected reviewed records are relabelled individually with `error_type=CATEGORY_MAPPING_ERROR`. Records whose only Telugu content is the literal jargon "yellow spot" (rendered as "yellow-coloured spots") are rejected as `INSUFFICIENT_CONTEXT`.
- **The same pattern was seen for "PWD".** All 3 PWD records reviewed so far are road complaints (BG-TEL-10120, 10135, 10169). This matches the S3 mapping-concentration flag (PWD: 4 of 5 flagged toward ROAD_INFRASTRUCTURE).

| Batch | Records | Status |
|---|---|---|
| P1-B0009 | 25 (PUBLIC_INFRASTRUCTURE / PUBLIC_SAFETY) | VALIDATED |
| P1-B0010 | 25 (PUBLIC_SAFETY) | VALIDATED |
| P1-B0011 | 25 (PUBLIC_SAFETY / PUBLIC_SANITATION) | VALIDATED |
| P1-B0012 | 25 (PUBLIC_SANITATION / PUBLIC_TRANSPORT) | VALIDATED |

### Second category-level mapping pattern: "Mobility - Roads, Public transport"
- This source category is mapped to PUBLIC_TRANSPORT, but it contains footpath and road complaints (BG-TEL-03735, 01496, 02332). These were relabelled to ROAD_INFRASTRUCTURE as `CATEGORY_MAPPING_ERROR`.
- A subcategory-level audit, like the one for Yellow Spot, is recommended before the taxonomy is revised. It is not applied.

### Checkpoint: 300 pass-1 reviews (12 batches, all VALIDATED on the first attempt)
- 222 random-sample records and 1,450 flagged records remain for pass 1. Pass 2 and adjudication have not started.
- Resume with:
  ```
  python scripts/phase5_review_batches.py export --pass 1 --size 25
  ```

---

## 2026-11-15 (continued): pass 1 resumed at P1-B0013; mapping proposal v1.1 drafted

### Commit
- The `compile` step, its test and the log were committed locally as `2425703`, with no attribution. 67 unit tests pass. Not pushed; pushing still needs explicit approval.

### Progress
| Batch | Records | Status |
|---|---|---|
| P1-B0013 | 25 (PUBLIC_TRANSPORT / ROAD_INFRASTRUCTURE) | VALIDATED after one fix: two AMBIGUOUS rows used `error_type=NONE`, which the validator rejects; corrected to MULTI_ISSUE |
| P1-B0014 | 25 (ROAD_INFRASTRUCTURE / SEWERAGE_DRAINAGE) | VALIDATED |
| P1-B0015 | 25 (SEWERAGE_DRAINAGE / SOCIAL_WELFARE / SOLID_WASTE) | VALIDATED |
| P1-B0016 | 25 (SOLID_WASTE) | VALIDATED |

Pass 1 now covers **400 records**. In the 100 new reviews: ACCEPT 24, ACCEPT_WITH_MINOR_ISSUES 50, RELABEL 15, REJECT 6, AMBIGUOUS 5. Fidelity: PASS 48, PARTIAL 51, FAIL 1. Privacy: NO_OBVIOUS_PII 89, POTENTIAL_PII 5, PII_IDENTIFIED 5, UNCERTAIN 1. These are descriptive pass-1 counts, not population estimates.

### Conventions added
- **Religious-affiliation disclosure** is treated like a health disclosure: special-category personal data, privacy `UNCERTAIN`, so the record is quarantined. The span type is `RELIGION_DISCLOSURE`. First case: BG-TEL-09169, which also calls for police violence against lockdown crowds; its content is relabelled PUBLIC_SAFETY.
- **A street-level address without a door or flat number**, given alone, is not treated as PII. A door number, or a name together with an apartment address, is `PII_IDENTIFIED`, as before.
- **A staff member's name** (for example a BWSSB contact) and **earlier complaint or request numbers** → `POTENTIAL_PII`.
- **Specific relabels in this session:**
  - parking, speed humps and medians against overtaking → TRAFFIC_SAFETY;
  - storm-drain flooding → STORMWATER;
  - a road blocked or left incomplete after sewer work → ROAD_INFRASTRUCTURE;
  - dirty public washrooms at a bus stand → PUBLIC_SANITATION.

### More recurring translation failures
- "pot holes" → కుండ రంధ్రాలు ("holes in a cooking pot"), found in 6+ records.
- Place-name parts translated: "9th Cross" → ninth crucifix (శిలువ); "Tiny Bees school" → small honeybees; "Naidu farm road" → Naidu's farm; "Vijayanagar" → Vizianagaram; "Doddakannahalli" → పెద్ద…
- Titles turned into imperatives: "Open manhole" → "open the manhole"; "Reverse from manhole" → "go back from the manhole".
- Invented content: a river added to "Overflowing at SP Raod"; a temple added to a truncated title.
- Typo-driven reversals: "Now one has fixed it" (no one) → "now they fixed it"; "Ration not issues" → "no ration issues".

### Subcategory audit and proposed taxonomy v1.1 (NOT applied)
- File: `configs/taxonomy_mapping_proposed_v1.1_PENDING.json`, status `PENDING_USER_APPROVAL`, `applied: false`. The v1.0 registry is unchanged.
- **The overrides match on (category_id, category_title, sub_category_title):**
  - Subcategory ids are not unique inside Yellow Spot. For example, 714 is used for both "Require A New Footpath" and "2C- Remove Garbage or Debris on Footpath".
  - One raw title ends in a newline (`2A- Require New Footpath\n`), so titles must be compared after stripping whitespace.
- **New finding (title-variant mapping error).** The 12 "Repair Of Existing Footpaths" records labelled "Mobility - Roads, Public transport" carry `category_id` **15**, which is the roads category, not 202. The v1.0 registry has a separate row for (15, "Mobility - Roads, Public transport") that maps to PUBLIC_TRANSPORT because it keyed on the title. Category id 470 also has two titles ("Street lighting" / "Streetlights"), but both map to the same target.
- **Proposed changes** (all counts checked against `data/external/bengaluru_complaints.csv`):
  - **Yellow Spot (948):** 371 stay PUBLIC_SANITATION; 258 → SOLID_WASTE; 315 → ROAD_INFRASTRUCTURE; 4 → PARKS_GREENSPACE.
  - **PWD (5):** all → ROAD_INFRASTRUCTURE.
  - **Mobility - Roads, Public transport (19):**
    - 12 → ROAD_INFRASTRUCTURE;
    - 3 → TRAFFIC_SAFETY (traffic lights, skywalk);
    - 1 stays PUBLIC_TRANSPORT;
    - 3 (flyovers/underpass) → per-record manual review.
  - In total, 600 records would change target.
- **Until approved,** affected records keep being relabelled one at a time during review (`CATEGORY_MAPPING_ERROR`).

### Resume
```
python scripts/phase5_review_batches.py export --pass 1 --size 25   # next: P1-B0017
```
Remaining for pass 1: 122 sample records and 1,450 flagged records.

---

## 2026-11-15 (continued): Option B approved; subset-aware tooling; P1-B0017; taxonomy comparison; isolation check

### User decisions (2026-11-15)
- **Option B (sample first) approved.** The order is:
  1. Finish pass 1 on the 522-record sample.
  2. Freeze the taxonomy.
  3. Blind pass 2 on the 522.
  4. Compare and adjudicate.
  5. Sample statistics.
  6. Flagged records: pass 1, pass 2, adjudication.
  7. Dataset v3.
  8. Gate 4 audit and milestone report.
  9. **Stop before ML.**
- **Taxonomy v1.1.** Not applied; a detailed v1.0 vs v1.1 comparison was requested first. v1.0 must stay unchanged, and both passes must use the same frozen version.
- **Pass 2 with fresh subagents.** Conditionally approved, provided context isolation is verified first. Agreement is to be reported as AI self-consistency, never as human inter-annotator reliability.
- **Statistics.** The implementation must be validated on synthetic populations before any estimate. Only the 522-record sample feeds population estimates; flagged results are reported separately, with no double counting.
- **LaBSE.** Not installed; semantic evaluation stays `NOT_EVALUATED`. The number, length and artifact checks are not semantic validation.
- **Process.** Batch size stays 25. Commits stay local; pushing needs explicit approval. Any ML training step must be flagged to the user first so it can run in Google Colab.

### Tooling: subset-aware export and preflight (`phase5_review_batches.py`)
- **`export --subset {sample,flagged,all}` is now required.**
  - A batch never mixes the random sample with flagged-only records. Sample records that were also flagged stay in `sample`.
  - Without this, the final sample batch would have taken 3 flagged records (122 = 4×25 + 22).
  - Pass-2 order is a seeded shuffle within the subset.
- **Every export runs `preflight` and refuses on any failure.** The checks:
  - queue IDs are unique;
  - no record appears in two batches of the same pass;
  - no candidate record is already reviewed;
  - every candidate belongs to the requested subset;
  - all earlier manifests used the current protocol version and taxonomy version (manifests from before this change count as v1.0, the only registry that existed then);
  - for pass 2, every record in the subset has a validated pass-1 review.
- **Manifests now record** `taxonomy_version`, `taxonomy_sha256`, `subset` and per-record `membership` (SAMPLE / SAMPLE_AND_FLAG / FLAGGED).
- **`status` reports** progress by subset, plus the taxonomy and protocol versions.
- **Tests.** `test_subset_filter_never_spills_into_flagged` and `test_preflight_catches_duplicates_subset_and_versions` were added. The suite has **69 tests, all passing**.

### Progress
| Batch | Records | Subset / membership | Taxonomy | Reviewer model | Status |
|---|---|---|---|---|---|
| P1-B0017 | 25 (SOLID_WASTE / STORMWATER) | sample: 22 SAMPLE, 3 SAMPLE_AND_FLAG | 1.0 | claude-opus-5-5 | VALIDATED on the first attempt |

- Pass 1 on the sample now stands at **425 of 522**. All 17 pass-1 batches are sample records, and none are flagged-only.
- **Conventions used in P1-B0017:**
  - "Drinage" translated as drinking water (తాగునీరు) throughout a record → REJECT with TRANSLATION_MEANING_SHIFT;
  - a site (plot) number in a layout counts as a door number → PII_IDENTIFIED;
  - a stinking lake (kere) filed under storm drains → relabelled LAKES_WATERBODIES;
  - debris left after storm-drain repair → AMBIGUOUS (SOLID_WASTE as secondary).

### Taxonomy v1.0 vs v1.1 comparison
- Written to `docs/research/GrievanceHub_Taxonomy_v1.0_vs_v1.1_Comparison.md`.
- **Corpus.** 589 corpus records would change target (600 in the raw file). PUBLIC_SANITATION would go from 1,032 to 466 records, and PUBLIC_TRANSPORT from 63 to 45.
- **Join method.** Records were linked to the raw data with `raw row = source_record_id − 1`; titles matched for 100% of records.
- **Sample.** 29 sample records would change label, all already reviewed:
  - 24 have a pass-1 category equal to the v1.1 target;
  - 2 are rejected and unaffected;
  - 3 need reassessment (BG-TEL-15502, 15132, 15791).
- **Flagged-only set.** 205 records would carry a different given label; none are reviewed yet.
- **The remaining 97 sample records are unaffected by v1.1,** so pass 1 can continue under v1.0 while the decision is pending.
- The record-level impact list is at `data/interim/review/taxonomy_v11_affected_pass1.csv` (Git-ignored).
- **Waiting for an explicit user decision.**

### Isolation check for pass-2 subagents
- **Test.** One fresh general-purpose subagent was given a canary prompt: no tools allowed, and questions about earlier history, the last validated batch and a pass-1 decision.
- **Result.**
  - It reported no earlier conversation history.
  - It answered UNKNOWN for the batch ID and the record decision.
  - It echoed the canary token correctly.
  - A transcript audit found exactly one tool call, `SubagentHandback` (delivering the report), and no file, search or shell calls.
- **Limitations found.**
  1. **Auto-injected context.** Each subagent automatically receives the session's git status with recent commit messages and the user's memory index. Neither contains record-level decisions, but commit messages mention process facts (for example "pending taxonomy v1.1 subcategory proposal"). The canary picked up exactly this.
  2. **File access is not technically blocked.** A general-purpose subagent could read pass-1 outputs or this log, which names some record IDs with their decisions. Isolation therefore relies on: (a) putting the protocol, taxonomy and records directly in the prompt so no tool is needed; (b) an instruction forbidding tools; (c) a **mandatory transcript audit after every batch**, where any tool call other than `SubagentHandback` invalidates the batch and it is redone.
  3. **Same model.** Pass 2 uses the same model (`claude-opus-5-5`), so agreement measures AI self-consistency across isolated sessions.
- **Waiting for the user** to accept this verified-by-audit isolation or require something stronger.

### Remaining workload
- Pass 1, sample: 97 records (P1-B0018 to P1-B0021; the last batch has 22 records).
- Pass 1, flagged: 1,450 records.
- Pass 2 and adjudication: not started.

### Privacy fix: a real phone number in tracked files
- **Found by** the pre-commit PII scan. A real mobile number from the source dataset was used as a test fixture in `tests/test_phase5_review.py` (3 places) and quoted as an example in this log.
- **Exposure.** It entered the history in `0edb11a` and `2425703`, both pushed to `origin/main`.
- **Fix in this commit.**
  - The test fixtures now use the synthetic `98765 43210`, which still exercises the spaced-number pattern.
  - The log example is redacted.
  - Tests still pass.
- **Still open.** The number remains in **Git history on GitHub**. Removing it needs a history rewrite (for example `git filter-repo` plus a force push) or deleting and recreating the repository. That is a destructive, outward-facing action and needs the user's decision.
- **New rule.** Test fixtures use synthetic identifiers only, never values copied from the data.
