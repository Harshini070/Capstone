# GrievanceHub: Taxonomy v1.0 vs proposed v1.1

**Status:** for decision. v1.1 is **not applied**. `configs/taxonomy_mapping_provisional_v1.json` (v1.0) is unchanged.
**Proposal file:** `configs/taxonomy_mapping_proposed_v1.1_PENDING.json` (`registry_status: PENDING_USER_APPROVAL`, `applied: false`).
**Prepared:** 2026-11-15, during pass 1 of the AI-assisted review (425 of 522 random-sample records reviewed).

## 1. What changes and what does not

- **What changes.** v1.0 maps each Bengaluru source category, as a whole, to one target category. v1.1 keeps every v1.0 row and adds **subcategory-level overrides for three source categories only**.
- **What does not change.**
  - All other source categories keep their v1.0 mapping.
  - The target category list is unchanged; no category is added or removed.
  - The category definitions in the review protocol are unchanged.

Override matching uses `(source_category_id, source_category_title, sub_category_title)`, with titles compared after stripping whitespace. Two facts make this necessary:

- Subcategory IDs are not unique inside "Yellow Spot". ID 714 is used for both "Require A New Footpath" and "2C- Remove Garbage or Debris on Footpath".
- One raw title, `2A- Require New Footpath`, ends in a newline character.

## 2. Every changed mapping

Counts are records in the experimental corpus (15,374 records). The raw source file has slightly more: 600 changing records instead of 589, because some raw records were excluded earlier in the pipeline.

| Source category (id) | Source subcategory | Corpus records | v1.0 target | v1.1 target | Reason |
|---|---|---|---|---|---|
| Yellow Spot (708) | Report A Broken Footpath | 172 | PUBLIC_SANITATION | ROAD_INFRASTRUCTURE | Footpath damage is ROAD_INFRASTRUCTURE by the protocol definition |
| Yellow Spot (708) | Require A New Footpath | 103 | PUBLIC_SANITATION | ROAD_INFRASTRUCTURE | Same as above |
| Yellow Spot (708) | 2B- Repair Broken Footpath | 29 | PUBLIC_SANITATION | ROAD_INFRASTRUCTURE | Same as above |
| Yellow Spot (708) | 2A- Require New Footpath | 8 | PUBLIC_SANITATION | ROAD_INFRASTRUCTURE | Same as above |
| Yellow Spot (708) | Report Garbage or Debris on Footpath | 192 | PUBLIC_SANITATION | SOLID_WASTE | Garbage and debris are SOLID_WASTE; the protocol says "garbage heaps → SOLID_WASTE" |
| Yellow Spot (708) | 2C- Remove Garbage or Debris on Footpath | 58 | PUBLIC_SANITATION | SOLID_WASTE | Same as above |
| Yellow Spot (708) | 3A- Require Playing and Gym Equipment | 4 | PUBLIC_SANITATION | PARKS_GREENSPACE | Playground equipment belongs to PARKS_GREENSPACE |
| PWD (564) | Repair of Potholes on Roads | 5 | PUBLIC_INFRASTRUCTURE | ROAD_INFRASTRUCTURE | Potholes are road-surface damage |
| Mobility - Roads, Public transport (**15**) | Repair Of Existing Footpaths | 12 | PUBLIC_TRANSPORT | ROAD_INFRASTRUCTURE | Category id 15 is the roads category; these records carry a variant title, and v1.0 keyed on the title (see §4) |
| Mobility - Roads, Public transport (202) | Installation of traffic lights | 2 | PUBLIC_TRANSPORT | TRAFFIC_SAFETY | Signals are TRAFFIC_SAFETY by definition |
| Mobility - Roads, Public transport (202) | Construction of skywalks | 1 | PUBLIC_TRANSPORT | TRAFFIC_SAFETY | Pedestrian crossing infrastructure |
| Mobility - Roads, Public transport (202) | Construction of flyovers/ underpass | 3 | PUBLIC_TRANSPORT | MANUAL_REVIEW_REQUIRED | Split between congestion (TRAFFIC_SAFETY) and road works; decided per record |
| **Total changing** | | **589** | | | |

These subcategories keep their v1.0 target (shown for completeness, 369 records):

- Yellow Spot sanitation subcategories → PUBLIC_SANITATION: Report A Public Urination or Yellow Spot (250), 1A- Address Public Urination or Yellow Spots (8), Require A New Public Toilet (87), 1B- Require New Public Toilet (3), Report A Dirty or Unusable Public Toilet (18), 1C- Repair Dirty or Unusable Public Toilet (1), Report A Dirty or Unusable Mobile Public Toilet (1).
- Mobility (202) "Introduction of new bus routes" (1) → PUBLIC_TRANSPORT.

## 3. Supporting examples (pass-1 reviewed records, no PII)

| Group | Record | Source title (truncated) | Pass-1 judgement |
|---|---|---|---|
| Yellow Spot / Broken Footpath | BG-TEL-11429, 11728, 11745 | "Broken Footpath" | RELABEL → ROAD_INFRASTRUCTURE |
| Yellow Spot / New Footpath | BG-TEL-11372, 11510 | "New Footpath" | RELABEL → ROAD_INFRASTRUCTURE |
| Yellow Spot / New Footpath | BG-TEL-11405 | "…Ranka Colony Road, Bilekahalli, need footpath…" | RELABEL → ROAD_INFRASTRUCTURE |
| Yellow Spot / Garbage on Footpath | BG-TEL-11736, 12088 | "Garbage or Debris on Footpath" | RELABEL → SOLID_WASTE |
| Yellow Spot / Garbage on Footpath | BG-TEL-12045 | "Debris On Footpath" | RELABEL → SOLID_WASTE |
| PWD / Potholes | BG-TEL-10169 | "Pothole" | RELABEL → ROAD_INFRASTRUCTURE |
| PWD / Potholes | BG-TEL-10135 | "Mud Roads" | RELABEL → ROAD_INFRASTRUCTURE |
| Mobility (15) / Footpaths | BG-TEL-00904 | "Footpath in Charles Campbell road is full of gaps and broken slab…" | RELABEL → ROAD_INFRASTRUCTURE |
| Mobility (15) / Footpaths | BG-TEL-02332 | "Please repair the footpath on both sides of the road…" | RELABEL → ROAD_INFRASTRUCTURE |
| Mobility (202) / Skywalks | BG-TEL-15791 | "Kottigepalya Bus stand requires a sky Walker…" | AMBIGUOUS (PUBLIC_TRANSPORT vs TRAFFIC_SAFETY) |

**Counter-evidence (so the change is not overstated):**

- Inside a footpath subcategory, some texts are not footpath complaints. BG-TEL-15502 ("Repair street ligh…") was relabelled to STREETLIGHT.
- Some sanitation-subcategory texts contain only the jargon "yellow spot", which the Telugu renders as "yellow-coloured spots". Pass 1 rejected these as INSUFFICIENT_CONTEXT.

Subcategory mapping fixes the systematic error, but record-level review is still needed for individual mismatches.

## 4. Why v1.0 got these wrong

1. **Category-level mapping of a mixed source category.** "Yellow Spot" is a programme name, not a complaint type. In the corpus, 61% of its records are footpath or garbage complaints.
2. **Title-keyed mapping.** Category id 15 appears under two titles: "Mobility - Roads, Footpaths and Infrastructure" (5,072 records) and "Mobility - Roads, Public transport" (12 footpath records). Because v1.0 mapped by title, those 12 records went to PUBLIC_TRANSPORT. Category id 470 also has two titles ("Street lighting" / "Streetlights"), but both map to STREETLIGHT, so nothing changes there.
3. **Why the automated check missed it.** The out-of-fold label-noise check (S3) cannot detect an error shared by hundreds of records, because the model learns the wrong label consistently. S3 flagged PWD (80% concentration) but not Yellow Spot.

## 5. Effect on class sizes (corpus, 15,374 records)

| Category | v1.0 | v1.1 | Change |
|---|---|---|---|
| PUBLIC_SANITATION | 1,032 | 466 | −566 (−55%) |
| ROAD_INFRASTRUCTURE | 5,108 | 5,437 | +329 |
| SOLID_WASTE | 3,870 | 4,120 | +250 |
| PUBLIC_TRANSPORT | 63 | 45 | −18 |
| PUBLIC_INFRASTRUCTURE | 136 | 131 | −5 |
| PARKS_GREENSPACE | 225 | 229 | +4 |
| TRAFFIC_SAFETY | 958 | 961 | +3 |
| MANUAL_REVIEW_REQUIRED | 0 | 3 | +3 (record-level decision) |

- PUBLIC_SANITATION remains a usable class (466 records) but becomes much smaller.
- PUBLIC_TRANSPORT (45) gets close to rare-class size. The rare-class policy (currently FIRE_EMERGENCY, EMPLOYEE_GRIEVANCES, SOCIAL_WELFARE) does not change automatically; any change there would be a separate decision.

## 6. Effect on the review so far

- **Random sample.** 29 of the 522 sample records change label. All 29 are already reviewed in pass 1:
  - 17 in the PUBLIC_SANITATION stratum;
  - 9 in PUBLIC_TRANSPORT;
  - 3 in PUBLIC_INFRASTRUCTURE.
- **Flagged-only set.** 205 of the 1,450 flagged-only records would carry a different given label. None of them are reviewed yet.

### The 29 affected pass-1 records

| Consequence under v1.1 | Records | Detail |
|---|---|---|
| Pass-1 category already equals the v1.1 target | 24 | RELABEL (CATEGORY_MAPPING_ERROR) to the same target that v1.1 assigns. Under v1.1 the given label becomes correct, so these turn into ACCEPT or ACCEPT_WITH_MINOR_ISSUES with no corrected category. The category judgement itself does not change. |
| Rejected, unaffected | 2 | BG-TEL-02502, 02504: rejected as INSUFFICIENT_CONTEXT whatever the label. |
| Still a relabel, but for a different reason | 1 | BG-TEL-15502: a streetlight text under "2B- Repair Broken Footpath". It stays RELABEL → STREETLIGHT, but the error type becomes SOURCE_LABEL_NOISE (the citizen chose the wrong subcategory) instead of CATEGORY_MAPPING_ERROR. |
| Mapped to MANUAL_REVIEW_REQUIRED | 1 | BG-TEL-15132 (flyover congestion): pass 1 relabelled it to TRAFFIC_SAFETY. Under v1.1 the record-level decision stands, and pass 1 already made it. |
| Was AMBIGUOUS | 1 | BG-TEL-15791 (skywalk at a bus stand): pass 1 judged it AMBIGUOUS between PUBLIC_TRANSPORT and TRAFFIC_SAFETY. v1.1 assigns TRAFFIC_SAFETY, which would make it ACCEPT_WITH_MINOR_ISSUES or keep it AMBIGUOUS. This needs a fresh judgement. |

The record-level list is in `data/interim/review/taxonomy_v11_affected_pass1.csv`, which is Git-ignored.

**No pass-1 category judgement contradicts v1.1.** The 24 consistent relabels are where the proposal came from, so this agreement is expected and is not independent support for v1.1.

## 7. Statistical consequences

- The 522-record sample was **stratified on v1.0 labels**. The design strata, inclusion probabilities and weights stay as drawn; changing the taxonomy does not change how the sample was selected.
- Under v1.1, category-level estimates become **domain estimates** across v1.0 strata. For example, the v1.1 PUBLIC_SANITATION domain draws only from the v1.0 PUBLIC_SANITATION stratum, but the v1.1 ROAD_INFRASTRUCTURE domain draws from three v1.0 strata. The estimator in `phase5_review_statistics.py` must handle this; it will be checked during the statistics validation step.
- Label-error estimates will differ by version. Under v1.0, the 24 mapping relabels count as label errors; under v1.1 they do not. The report would state which version each figure uses.

## 8. If v1.1 is approved, the plan is:

1. Copy the proposal to `configs/taxonomy_mapping_provisional_v1.1.json` as a separate versioned registry (`version: "1.1"`, `base_version: "1.0"`). v1.0 stays byte-for-byte unchanged, and its SHA-256 is recorded.
2. Add a resolver that returns the v1.1 target for a record (subcategory override, otherwise the v1.0 category mapping). Unit tests cover the duplicate subcategory IDs, the trailing-newline title and the id-15 title variant.
3. Point the review tooling at v1.1:
   - `given_category` in every new batch input comes from v1.1;
   - every manifest records `taxonomy_version` and `taxonomy_sha256` (already implemented);
   - export preflight refuses to mix versions.
4. Add a `taxonomy_version` field to every review decision record. The validator requires it to match the batch manifest. The 17 pass-1 batches already done were reviewed under v1.0, and their manifests record this.
5. **Reassess the 29 affected pass-1 records** in a dedicated reassessment batch (`P1R-B0001`). It shows the record under its v1.1 given label, records the new decision with `supersedes = <original batch>`, and leaves the original frozen batch untouched. The merge uses the reassessment row for those 29 records and keeps the original row in the audit trail.
6. The remaining 97 sample records are reviewed under v1.1, and pass 2 for all 522 runs under v1.1, so both passes use the same frozen version.
7. Log every step in the development log.

## 9. If v1.1 is not approved

- v1.0 stays the frozen taxonomy for both passes.
- Pass 1 keeps relabelling affected records one at a time (`CATEGORY_MAPPING_ERROR`). Pass 2 judges against v1.0.
- The three mapping problems are reported as a known dataset limitation in the milestone report, with the counts in §2.
- The proposal file stays in the repository as a recommendation, marked not applied.

## 10. Decision needed

Approve v1.1 as specified (§2 and §8), approve it with changes (for example, a different target for the flyover or skywalk rows), or reject it (§9). Pass 2 does not start until this is decided.
