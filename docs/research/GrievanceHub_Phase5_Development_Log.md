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
- **Finding:** real-looking mobile numbers (for example, `98806 09192`) are still in the working dataset. The upstream privacy manifest's pattern didn't allow a space inside the number, so it missed them. Such records will be quarantined unless reviewed.
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
