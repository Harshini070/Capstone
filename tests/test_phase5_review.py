"""Tests for the Phase 5 AI-assisted review pipeline (scripts/phase5_*.py).

Run from the project root:
    python -m unittest discover -s tests -t .

Most tests use small synthetic fixtures. Tests that need the local
(Git-ignored) datasets are skipped automatically when those files are absent.
"""

import json
import math
import sys
import tempfile
import unittest
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import phase5_review_common as common  # noqa: E402
import phase5_build_review_sample_v2 as s1  # noqa: E402
import phase5_corpus_screens as s2  # noqa: E402
import phase5_label_noise_detection as s3  # noqa: E402
import phase5_review_batches as batches  # noqa: E402
import phase5_review_consistency as consistency  # noqa: E402
import phase5_apply_review_decisions as apply  # noqa: E402
import phase5_review_statistics as stats  # noqa: E402
import phase5_training_eligibility_audit as audit  # noqa: E402

ASSIGNABLE = frozenset({"SOLID_WASTE", "ROAD_INFRASTRUCTURE", "STREETLIGHT",
                        "SEWERAGE_DRAINAGE", "STORMWATER", "FIRE_EMERGENCY"})
SOURCE = "Garbage not cleared for a week near the bus stop"
TELUGU = "చెత్త ఒక వారం నుండి తొలగించలేదు"


def valid_review(**overrides):
    row = {
        "record_id": "R1", "batch_id": "P1-B0001", "review_pass": "1",
        "review_method": "AI_ASSISTED", "reviewer_model": "claude-opus-5-5",
        "protocol_version": common.PROTOCOL_VERSION,
        "review_timestamp": "2026-11-15T10:00:00+00:00",
        "translation_fidelity": "PASS", "telugu_grammar": "GOOD",
        "translation_completeness": "COMPLETE", "missing_information": "NONE",
        "added_information": "NONE", "category_correctness": "CORRECT",
        "corrected_category": "", "secondary_category": "",
        "geography_assessment": "NO_GEOGRAPHY_REFERENCE",
        "privacy_assessment": "NO_OBVIOUS_PII", "pii_spans": "[]",
        "review_decision": "ACCEPT", "error_type": "NONE",
        "evidence_source": "Garbage not cleared", "evidence_telugu": "చెత్త",
        "explanation": "",
    }
    row.update(overrides)
    return row


def eligibility_record(**overrides):
    rec = {
        "reviewed": True, "final_category": "SOLID_WASTE", "review_decision": "ACCEPT",
        "privacy_assessment": "NO_OBVIOUS_PII", "consistency_status": "CONSISTENT",
        "translation_fidelity": "PASS", "missing_information": "NONE",
        "added_information": "NONE", "residual_dot_run": False, "empty_title": False,
        "empty_description": False, "evidence_present": True, "regex_pii_flag": False,
    }
    rec.update(overrides)
    return rec


# 1 -------------------------------------------------------------------------
class SampleRebuildTests(unittest.TestCase):
    def setUp(self):
        rng = np.random.default_rng(0)
        cats = ["A"] * 100 + ["B"] * 12 + ["C"] * 1
        self.pop = pd.DataFrame({
            "record_id": [f"R{i:04d}" for i in range(len(cats))],
            "target_category_code": cats,
            "telugu_title_cleaned": [f"t{i}" for i in range(len(cats))],
            "telugu_description_cleaned": [str(rng.integers(1e9)) for _ in cats],
        })

    def test_sizes_weights_and_probabilities(self):
        sample = s1.draw_stratified_sample(self.pop)
        sizes = sample.groupby("sampling_stratum").size().to_dict()
        self.assertEqual(sizes, {"A": 30, "B": 12, "C": 1})
        a = sample[sample.sampling_stratum == "A"].iloc[0]
        self.assertAlmostEqual(a.sampling_weight, 100 / 30)
        self.assertAlmostEqual(a.inclusion_probability, 30 / 100)
        self.assertTrue((sample[sample.sampling_stratum == "B"].sampling_weight == 1).all())

    def test_seed_42_is_deterministic(self):
        first = s1.draw_stratified_sample(self.pop)["record_id"].tolist()
        second = s1.draw_stratified_sample(self.pop)["record_id"].tolist()
        self.assertEqual(first, second)

    @unittest.skipUnless(common.RECORD_LEVEL_QUALITY_PATH.exists() and common.OLD_SAMPLE_PATH.exists(),
                         "local record-level data not present")
    def test_reproduces_original_522_sample(self):
        population = common.read_csv(common.RECORD_LEVEL_QUALITY_PATH)
        sample = s1.draw_stratified_sample(population)
        old = common.read_csv(common.OLD_SAMPLE_PATH)
        self.assertEqual(len(sample), 522)
        self.assertEqual(s1.text_keys(sample), s1.text_keys(old))


# 2 -------------------------------------------------------------------------
class DuplicateGroupingTests(unittest.TestCase):
    long_text = "మా వీధిలో చెత్త పేరుకుపోయింది దుర్వాసన వస్తోంది దయచేసి వెంటనే చర్య తీసుకోండి " * 3

    def group(self, titles, descriptions):
        ids = [f"R{i}" for i in range(len(titles))]
        return s2.assign_dedup_groups(ids, titles, descriptions)

    def test_unicode_and_whitespace_normalisation(self):
        nfd = unicodedata.normalize("NFD", "café road")
        self.assertEqual(common.text_hash(nfd, "x"), common.text_hash("café   road", " x "))

    def test_exact_duplicates_grouped(self):
        exact, dedup, _ = self.group(["a", "a "], ["same text", "same  text"])
        self.assertEqual(exact[0], exact[1])
        self.assertEqual(dedup[0], dedup[1])

    def test_near_duplicates_grouped_and_different_not(self):
        t = self.long_text
        exact, dedup, pairs = self.group(["x", "x", "y"],
                                         [t, t.replace("దయచేసి", "దయచేసీ", 1), "రోడ్డుపై పెద్ద గుంతలు ఉన్నాయి"])
        self.assertNotEqual(exact[0], exact[1])
        self.assertEqual(dedup[0], dedup[1])
        self.assertNotEqual(dedup[0], dedup[2])
        self.assertGreaterEqual(pairs, 1)

    def test_group_id_is_stable_smallest_record_id(self):
        _, dedup, _ = self.group(["a", "a"], ["t", "t"])
        self.assertEqual(dedup, ["DG-R0", "DG-R0"])

    def test_chaining_diagnostic(self):
        screens = pd.DataFrame({"record_id": ["R0", "R1"], "dedup_group_id": ["G", "G"]})
        self.assertEqual(s2.chained_groups(screens, ["a", "z"], ["completely different", "nothing alike here"]), ["G"])


# 3 -------------------------------------------------------------------------
class PIIDetectionTests(unittest.TestCase):
    def types(self, text, field="source_description"):
        return {h["type"] for h in s2.detect_pii({field: text})}

    def test_flags_identifiers(self):
        self.assertIn("INDIAN_MOBILE", self.types("call me on 98765 43210 please"))
        self.assertIn("INDIAN_MOBILE", self.types("+91 9876543210"))
        self.assertIn("EMAIL", self.types("mail abc.def@example.com"))
        self.assertIn("VEHICLE_REGISTRATION", self.types("car KA 01 AB 1234 parked"))
        self.assertIn("DOOR_NUMBER", self.types("near #15, 4th cross"))
        self.assertIn("DOOR_NUMBER", self.types("house no.332 opposite"))
        self.assertIn("DOOR_NUMBER", self.types("ఇంటి నెం 45 దగ్గర", "telugu_description_cleaned"))
        self.assertIn("PIN_CODE", self.types("Bangalore 560058"))

    def test_years_and_ward_numbers_are_not_phones(self):
        for text in ("since 2023 nothing done", "Ward 150 Jakkur", "ward number 198", "from 2019 to 2022"):
            self.assertNotIn("INDIAN_MOBILE", self.types(text), text)
            self.assertNotIn("AADHAAR_LIKE_12_DIGIT", self.types(text), text)

    def test_arbitrary_six_digits_not_pin(self):
        self.assertNotIn("PIN_CODE", self.types("amount 123456 spent"))

    def test_output_is_flag_with_method(self):
        hit = s2.detect_pii({"source_title": "98765 43210"})[0]
        self.assertEqual(set(hit), {"type", "field", "text", "method"})


# 4 -------------------------------------------------------------------------
class FoldTests(unittest.TestCase):
    def data(self):
        y, groups = [], []
        for cls, n_groups in (("A", 40), ("B", 30), ("C", 25)):
            for g in range(n_groups):
                for _ in range(2):
                    y.append(cls)
                    groups.append(f"{cls}{g}")
        return np.array(y), np.array(groups)

    def test_no_group_leakage_and_full_coverage(self):
        y, groups = self.data()
        folds = s3.make_folds(y, groups)
        report = s3.validate_folds(y, groups, folds)
        self.assertEqual(report["group_leakage"], [])
        self.assertTrue(report["every_record_predicted_exactly_once"])
        self.assertTrue(report["valid"])
        self.assertEqual(sum(report["per_class_fold_counts"]["A"]["validation"]), 80)

    def test_unsupported_class_reported_not_forced(self):
        y, groups = self.data()
        y = np.append(y, ["D"] * 6)
        groups = np.append(groups, ["D0"] * 3 + ["D1"] * 3)  # only 2 groups
        mask, folds, reports, dropped = s3.supported_folds(y, groups, ["A", "B", "C", "D"])
        self.assertIn("D", dropped)
        self.assertFalse(mask[-6:].any())
        self.assertTrue(reports[-1]["valid"])


# 5 -------------------------------------------------------------------------
class LabelNoiseRuleTests(unittest.TestCase):
    def test_threshold_logic(self):
        classes = ["A", "B"]
        y = np.array(["A", "A", "B", "B"])
        probs = np.array([[0.9, 0.1], [0.3, 0.7], [0.2, 0.8], [0.4, 0.6]])
        flags, thresholds = s3.flag_label_noise(probs, y, classes)
        self.assertAlmostEqual(thresholds["A"], 0.6)
        self.assertAlmostEqual(thresholds["B"], 0.7)
        # record 1: p(B)=0.7 >= t_B and > p(A)=0.3 -> flagged toward B
        self.assertEqual(flags["flagged"].tolist(), [False, True, False, False])
        self.assertEqual(flags.loc[1, "suggested_category"], "B")
        self.assertAlmostEqual(flags.loc[1, "margin"], 0.4)
        # record 3: p(A)=0.4 < t_A=0.6 -> not flagged even though uncertain

    def test_rare_classes_excluded_from_model(self):
        labels = ["SOLID_WASTE", "FIRE_EMERGENCY", "SOCIAL_WELFARE", "EMPLOYEE_GRIEVANCES", "STREETLIGHT"]
        self.assertEqual(s3.primary_classes(labels), ["SOLID_WASTE", "STREETLIGHT"])

    def test_injected_flips_copy_only(self):
        y = np.array(["A"] * 40 + ["B"] * 40)
        flipped_y, mask = s3.inject_flips(y, ["A", "B"], rate=0.05)
        self.assertEqual(mask.sum(), 4)
        self.assertEqual((y == "A").sum(), 40)  # original untouched
        self.assertTrue((flipped_y[mask] != y[mask]).all())


# 6 -------------------------------------------------------------------------
class MappingConcentrationTests(unittest.TestCase):
    def test_45_percent_triggers_investigate_and_taxonomy_unchanged(self):
        before = common.file_sha256(common.TAXONOMY_PATH)
        source = pd.Series(["X"] * 20 + ["Y"] * 10)
        flags = pd.DataFrame({
            "flagged": [True] * 9 + [False] * 11 + [True] + [False] * 9,
            "suggested_category": ["S"] * 9 + [""] * 11 + ["T"] + [""] * 9,
        })
        table = s3.mapping_concentration(source, flags).set_index("source_category_title")
        self.assertEqual(table.loc["X", "status"], "INVESTIGATE")
        self.assertAlmostEqual(table.loc["X", "share"], 0.45)
        self.assertEqual(table.loc["Y", "status"], "OK")
        self.assertEqual(common.file_sha256(common.TAXONOMY_PATH), before)


# 7 -------------------------------------------------------------------------
class SchemaValidationTests(unittest.TestCase):
    def errors(self, **overrides):
        return common.validate_review_record(valid_review(**overrides), "SOLID_WASTE", ASSIGNABLE,
                                             source_text=SOURCE, telugu_text=TELUGU)

    def test_valid_row_passes(self):
        self.assertEqual(self.errors(), [])

    def test_invalid_enum_rejected(self):
        self.assertTrue(self.errors(translation_fidelity="GOODISH"))

    def test_relabel_without_category_rejected(self):
        errs = self.errors(review_decision="RELABEL", category_correctness="INCORRECT",
                           error_type="SOURCE_LABEL_NOISE", explanation="Wrong label.")
        self.assertTrue(any("requires corrected_category" in e for e in errs))

    def test_missing_explanation_rejected(self):
        errs = self.errors(review_decision="REJECT", error_type="TRANSLATION_MEANING_SHIFT",
                           category_correctness="CORRECT")
        self.assertTrue(any("explanation is required" in e for e in errs))

    def test_corrected_equal_to_given_rejected(self):
        errs = self.errors(review_decision="RELABEL", category_correctness="INCORRECT",
                           corrected_category="SOLID_WASTE", error_type="SOURCE_LABEL_NOISE",
                           explanation="x")
        self.assertTrue(any("equals the given" in e for e in errs))

    def test_non_verbatim_evidence_rejected(self):
        self.assertTrue(any("verbatim" in e for e in self.errors(evidence_source="invented quote")))

    def test_pii_identified_requires_spans(self):
        errs = self.errors(privacy_assessment="PII_IDENTIFIED", review_decision="REJECT",
                           error_type="PII", explanation="Phone number.")
        self.assertTrue(any("pii_spans" in e for e in errs))

    def test_valid_relabel_passes(self):
        self.assertEqual(self.errors(review_decision="RELABEL", category_correctness="INCORRECT",
                                     corrected_category="ROAD_INFRASTRUCTURE",
                                     error_type="SOURCE_LABEL_NOISE",
                                     explanation="Describes a pothole."), [])


# 8 -------------------------------------------------------------------------
class BatchAndOverlapTests(unittest.TestCase):
    def test_sample_and_flag_overlap_deduplicated(self):
        sample = pd.DataFrame({
            "record_id": ["R1", "R2"], "sample_order": ["1", "2"], "sampling_stratum": ["A", "A"],
            "stratum_population": ["10", "10"], "stratum_sample_size": ["2", "2"],
            "inclusion_probability": ["0.2", "0.2"], "sampling_weight": ["5.0", "5.0"],
        })
        flags = pd.DataFrame({"record_id": ["R2", "R3"], "label_noise_status": ["EVALUATED"] * 2,
                              "flagged": ["True", "True"], "flag_rank": ["1", "2"]})
        screens = pd.DataFrame({"record_id": ["R1", "R2", "R3", "R4"],
                                "category_flags": ["", "", "", "both_signals_disagree_with_given_label"]})
        queue = batches.build_queue(sample, flags, screens).set_index("record_id")
        self.assertEqual(sorted(queue.index), ["R1", "R2", "R3", "R4"])
        self.assertEqual(queue.loc["R2", "review_origin"], common.ORIGIN_SAMPLE)
        self.assertTrue(queue.loc["R2", "also_flagged"])
        self.assertEqual(queue.loc["R2", "sampling_weight"], "5.0")
        self.assertEqual(queue.loc["R3", "review_origin"], common.ORIGIN_FLAG)
        self.assertEqual(queue.loc["R3", "sampling_weight"], "")
        self.assertEqual(queue.loc["R4", "review_inclusion_reason"], "S2_CATEGORY_SIGNAL_CONFLICT")

    def test_batch_validation_detects_missing_extra_and_duplicates(self):
        batch_input = pd.DataFrame({
            "record_id": ["R1", "R2"], "given_category": ["SOLID_WASTE"] * 2,
            "source_title": [SOURCE] * 2, "source_description": [""] * 2,
            "telugu_title_cleaned": [TELUGU] * 2, "telugu_description_cleaned": [""] * 2,
        })
        rows = [valid_review(record_id="R1"), valid_review(record_id="R1"), valid_review(record_id="R9")]
        errs = batches.validate_batch_rows(rows, batch_input, "P1-B0001", "1", ASSIGNABLE)
        joined = " ".join(errs)
        self.assertIn("duplicate record_id", joined)
        self.assertIn("missing records", joined)
        self.assertIn("not in this batch", joined)

    def test_compile_psv_expands_codes_and_validates(self):
        psv = ("record_id|fid|gram|comp|miss|add|cat|corr|sec|geo|priv|dec|err|ev_src|ev_tel|expl|pii\n"
               "R1|P|G|C|N|N|I|ROAD_INFRASTRUCTURE||N|N|RL|SLN|Garbage not cleared|చెత్త|Pothole complaint.|\n")
        rows = batches.compile_psv(psv, "P1-B0001", "1", "claude-opus-5-5", "2026-11-15T10:00:00+00:00")
        self.assertEqual(rows[0]["review_decision"], "RELABEL")
        self.assertEqual(rows[0]["corrected_category"], "ROAD_INFRASTRUCTURE")
        self.assertEqual(rows[0]["pii_spans"], [])
        self.assertEqual(common.validate_review_record(rows[0], "SOLID_WASTE", ASSIGNABLE,
                                                       source_text=SOURCE, telugu_text=TELUGU), [])
        with self.assertRaises(ValueError):
            batches.compile_psv(psv.replace("|RL|", "|XX|"), "P1-B0001", "1", "m", "t")
        spans = batches.parse_pii_cell("INDIAN_MOBILE~source_description~98765 43210")
        self.assertEqual(spans[0]["type"], "INDIAN_MOBILE")

    def _queue(self):
        return pd.DataFrame({
            "record_id": ["S1", "S2", "S3", "F1", "F2"],
            "in_random_sample": ["True", "True", "True", "False", "False"],
            "in_flagged_set": ["False", "True", "False", "True", "True"],
            "review_priority": ["1", "2", "3", "4", "5"],
        })

    def test_subset_filter_never_spills_into_flagged(self):
        queue = self._queue()
        prior = [{"batch_id": "P1-B0001", "record_ids": ["S1", "S2"],
                  "protocol_version": common.PROTOCOL_VERSION}]
        ids = batches.next_batch_ids("1", 25, "sample", queue, prior)
        self.assertEqual(ids, ["S3"])
        self.assertEqual(batches.next_batch_ids("1", 25, "flagged", queue, prior), ["F1", "F2"])
        self.assertEqual(batches.membership(queue)["S2"], "SAMPLE_AND_FLAG")
        self.assertIn("S2", batches.subset_ids(queue, "sample"))
        self.assertNotIn("S2", batches.subset_ids(queue, "flagged"))

    def test_preflight_catches_duplicates_subset_and_versions(self):
        queue = self._queue()
        prior = [{"batch_id": "P1-B0001", "record_ids": ["S1"], "protocol_version": common.PROTOCOL_VERSION},
                 {"batch_id": "P1-B0002", "record_ids": ["S1"], "protocol_version": "old",
                  "taxonomy_version": "9.9"}]
        joined = " ".join(batches.preflight("1", "sample", ["S1", "F1"], queue, prior))
        self.assertIn("already in P1-B0001 and P1-B0002", joined)
        self.assertIn("already reviewed", joined)
        self.assertIn("outside subset 'sample'", joined)
        self.assertIn("used protocol old", joined)
        self.assertIn("used taxonomy 9.9", joined)
        ok = batches.preflight("1", "sample", ["S2"], queue, prior[:1])
        self.assertEqual(ok, [])
        gate = batches.preflight("2", "sample", ["S1"], queue, [], pass1_done={"S1"})
        self.assertIn("no validated pass-1 review", " ".join(gate))

    def test_pass2_order_is_seeded_permutation(self):
        ids = [f"R{i}" for i in range(50)]
        order = batches.pass2_order(ids)
        self.assertEqual(sorted(order), sorted(ids))
        self.assertNotEqual(order, sorted(ids))
        self.assertEqual(order, batches.pass2_order(list(reversed(ids))))


# 9 -------------------------------------------------------------------------
class ConsistencyTests(unittest.TestCase):
    def passes(self):
        p1 = pd.DataFrame([valid_review(record_id="R1"), valid_review(record_id="R2"),
                           valid_review(record_id="R3")])
        p2 = p1.copy()
        p2.loc[1, "privacy_assessment"] = "POTENTIAL_PII"
        p2.loc[2, "review_decision"] = "REJECT"
        return p1, p2

    def test_matching_and_disagreement(self):
        p1, p2 = self.passes()
        comp = consistency.compare_passes(p1, p2).set_index("record_id")
        self.assertEqual(comp.loc["R1", "consistency_status"], "CONSISTENT")
        self.assertEqual(comp.loc["R2", "consistency_status"], "AI_DISAGREEMENT")
        self.assertEqual(comp.loc["R2", "differing_fields"], "privacy_assessment")

    def test_adjudication_and_unresolved(self):
        p1, p2 = self.passes()
        comp = consistency.compare_passes(p1, p2)
        adj = pd.DataFrame([valid_review(record_id="R2", review_pass="ADJUDICATION")])
        final = consistency.finalize(p1, comp, adj).set_index("record_id")
        self.assertEqual(final.loc["R1", "consistency_status"], "CONSISTENT")
        self.assertEqual(final.loc["R2", "consistency_status"], "RESOLVED_BY_ADJUDICATION")
        self.assertEqual(final.loc["R3", "consistency_status"], "UNRESOLVED")
        self.assertEqual(final.loc["R3", "review_decision"], "ESCALATE")

    def test_adjudicated_escalate_is_unresolved(self):
        p1, p2 = self.passes()
        comp = consistency.compare_passes(p1, p2)
        adj = pd.DataFrame([valid_review(record_id="R3", review_pass="ADJUDICATION",
                                         review_decision="ESCALATE")])
        final = consistency.finalize(p1, comp, adj).set_index("record_id")
        self.assertEqual(final.loc["R3", "consistency_status"], "UNRESOLVED_ESCALATED")

    def test_semantic_calibration(self):
        self.assertEqual(consistency.calibrate_semantic_threshold([], [])["status"], "NOT_EVALUATED")
        scores = [0.1, 0.2, 0.3, 0.8, 0.85, 0.9, 0.95, 0.7]
        labels = ["FAIL", "FAIL", "FAIL", "PASS", "PASS", "PASS", "PASS", "PASS"]
        result = consistency.calibrate_semantic_threshold(scores, labels)
        self.assertEqual(result["selected"]["threshold"], 0.3)
        self.assertFalse(result["weak_signal"])
        weak = consistency.calibrate_semantic_threshold([0.9, 0.1, 0.8, 0.2], ["FAIL", "FAIL", "PASS", "PASS"])
        self.assertTrue(weak["weak_signal"])
        self.assertFalse(weak["use_in_eligibility"])


# 10 ------------------------------------------------------------------------
class EligibilityTests(unittest.TestCase):
    def state(self, **overrides):
        return common.assign_eligibility(eligibility_record(**overrides))

    def test_every_state(self):
        self.assertEqual(self.state()[0], common.STATE_ACCEPTED)
        self.assertEqual(self.state(review_decision="RELABEL")[0], common.STATE_RELABELLED)
        self.assertEqual(self.state(review_decision="REJECT")[0], common.STATE_REJECTED)
        self.assertEqual(self.state(review_decision="ESCALATE")[0], common.STATE_REJECTED)
        self.assertEqual(self.state(review_decision="AMBIGUOUS")[0], common.STATE_AMBIGUOUS)
        self.assertEqual(self.state(reviewed=False)[0], common.STATE_SCREENED)
        self.assertEqual(self.state(final_category="FIRE_EMERGENCY")[0], common.STATE_RARE)

    def test_privacy_quarantine(self):
        for privacy, reason in (("PII_IDENTIFIED", "PII_IDENTIFIED"),
                                ("POTENTIAL_PII", "POTENTIAL_PII"),
                                ("UNCERTAIN", "PRIVACY_UNCERTAIN")):
            self.assertEqual(self.state(privacy_assessment=privacy),
                             (common.STATE_QUARANTINED_PRIVACY, reason))
        self.assertEqual(self.state(reviewed=False, regex_pii_flag=True),
                         (common.STATE_QUARANTINED_PRIVACY, "REGEX_PII_FLAG_UNREVIEWED"))
        # privacy outranks the rare-class exclusion
        self.assertEqual(self.state(final_category="FIRE_EMERGENCY", privacy_assessment="POTENTIAL_PII")[0],
                         common.STATE_QUARANTINED_PRIVACY)

    def test_quality_gates_block(self):
        self.assertEqual(self.state(missing_information="MAJOR"),
                         (common.STATE_QUALITY_BLOCKED, "MAJOR_MISSING_INFORMATION"))
        self.assertEqual(self.state(translation_fidelity="FAIL")[0], common.STATE_QUALITY_BLOCKED)
        self.assertEqual(self.state(residual_dot_run=True)[0], common.STATE_QUALITY_BLOCKED)
        self.assertEqual(self.state(evidence_present=False)[0], common.STATE_QUALITY_BLOCKED)

    def test_unresolved_disagreement_excluded(self):
        self.assertEqual(self.state(consistency_status="UNRESOLVED")[0], common.STATE_REJECTED)
        self.assertEqual(self.state(consistency_status="RESOLVED_BY_ADJUDICATION")[0], common.STATE_ACCEPTED)


# 11 ------------------------------------------------------------------------
class AuditPolicyTests(unittest.TestCase):
    def test_ai_assisted_v1_counts_only_eligible_states(self):
        df = pd.DataFrame({
            "record_id": list("ABCDEF"),
            "eligibility_state": ["AI_REVIEWED_ACCEPTED", "AI_REVIEWED_RELABELLED", "SCREENED_NOT_REVIEWED",
                                  "QUARANTINED_PRIVACY", "AI_REVIEWED_ACCEPTED", "AI_REVIEWED_ACCEPTED"],
            "final_category": ["SOLID_WASTE", "STREETLIGHT", "SOLID_WASTE", "SOLID_WASTE",
                               "FIRE_EMERGENCY", "SOLID_WASTE"],
            "review_method": ["AI_ASSISTED"] * 6,
            "review_privacy_assessment": ["NO_OBVIOUS_PII"] * 5 + ["POTENTIAL_PII"],
            "dedup_group_id": list("ABCDEF"),
        })
        self.assertEqual(audit.ai_assisted_v1_eligible(df).tolist(), [True, True, False, False, False, False])

    def test_default_policy_unchanged_and_zero(self):
        fixture = pd.DataFrame({
            "telugu_title": ["శీర్షిక"], "telugu_description": ["వివరణ"],
            "target_category_code": ["SOLID_WASTE"],
            "privacy_screening_status": ["NO_REGEX_MATCH_PENDING_MANUAL_REVIEW"],
            "training_eligibility": ["PROVISIONAL_NOT_CLEARED"], "release_status": ["HOLD"],
            "model_training_eligibility": ["NOT_CLEARED"],
        })
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.csv"
            fixture.to_csv(path, index=False, encoding="utf-8-sig")
            old_input, old_dir = audit.INPUT_FILE, audit.REPORT_DIR
            try:
                audit.INPUT_FILE, audit.REPORT_DIR = path, Path(tmp)
                from contextlib import redirect_stdout
                import io
                with redirect_stdout(io.StringIO()):
                    audit.run_default_policy()
            finally:
                audit.INPUT_FILE, audit.REPORT_DIR = old_input, old_dir
            report = json.loads((Path(tmp) / "phase5_training_eligibility_audit.json").read_text(encoding="utf-8"))
        self.assertEqual(report["eligible_records"], 0)
        self.assertEqual(audit.APPROVED_PRIVACY_STATES, {"CLEARED", "APPROVED", "PRIVACY_CLEARED"})


# 12 ------------------------------------------------------------------------
class StatisticsTests(unittest.TestCase):
    def test_hand_calculated_estimator(self):
        checks = stats.hand_calculated_checks()
        self.assertTrue(all(checks.values()), checks)

    def test_census_stratum_zero_variance_and_fixed_replicates(self):
        strata = [(10, np.array([1, 0, 1, 0, 1, 0, 0, 0, 0, 0]))]
        self.assertEqual(stats.stratified_estimate(strata)["variance"], 0.0)
        reps = stats.rao_wu_replicates(strata, 50, np.random.default_rng(1))
        self.assertTrue(np.allclose(reps, 0.3))

    def test_rao_wu_replicates_centre_on_estimate(self):
        rng = np.random.default_rng(3)
        strata = [(200, rng.integers(0, 2, 30)), (80, rng.integers(0, 2, 30))]
        est = stats.stratified_estimate(strata)
        reps = stats.rao_wu_replicates(strata, 4000, np.random.default_rng(4))
        self.assertAlmostEqual(reps.mean(), est["estimate"], delta=0.01)
        self.assertAlmostEqual(reps.std(), est["se"], delta=0.25 * est["se"])

    def test_wilson_fpc_reference(self):
        lo, hi = stats.wilson_fpc(5, 30, 10 ** 12)  # FPC negligible -> plain Wilson
        z, n, p = stats.Z95, 30, 5 / 30
        c = (p + z * z / (2 * n)) / (1 + z * z / n)
        h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
        self.assertAlmostEqual(lo, c - h, places=6)
        self.assertAlmostEqual(hi, c + h, places=6)
        self.assertEqual(stats.wilson_fpc(3, 10, 10), (0.3, 0.3))
        narrow = stats.wilson_fpc(5, 30, 40)
        self.assertLess(narrow[1] - narrow[0], hi - lo)

    def test_korn_graubard_interval(self):
        lo, hi = stats.korn_graubard_interval(0.0, 0.0, 30, 1)
        self.assertEqual(lo, 0.0)
        self.assertGreater(hi, 0.0)
        # With an SRS-like variance it should contain the estimate and be
        # wider than the Taylor interval for a rare proportion.
        p, n = 0.05, 200
        var = p * (1 - p) / (n - 1)
        klo, khi = stats.korn_graubard_interval(p, var, n, 1)
        tlo, thi = stats.taylor_interval(p, math.sqrt(var))
        self.assertLess(klo, p)
        self.assertGreater(khi, p)
        self.assertGreater(khi - klo, thi - tlo)

    def test_reduced_synthetic_simulation(self):
        design = [("A", 500, 30), ("B", 120, 30), ("C", 10, 10)]
        result = stats.simulate(design, [0.3, 0.1, 0.5], sims=200, reps=200, seed=7)
        self.assertLess(abs(result["bias"]), 0.01)
        self.assertGreaterEqual(result["coverage_korn_graubard"], 0.88)
        self.assertGreaterEqual(result["coverage_taylor"], 0.85)
        self.assertGreaterEqual(result["coverage_rao_wu_bootstrap"], 0.88)
        self.assertLessEqual(result["coverage_rao_wu_bootstrap"], 0.99)

    def test_flagged_rows_rejected(self):
        final = pd.DataFrame({"record_id": ["R1", "R2"]})
        queue = pd.DataFrame({"record_id": ["R1", "R2"],
                              "review_origin": [common.ORIGIN_SAMPLE, common.ORIGIN_FLAG]})
        with self.assertRaises(ValueError):
            stats.sample_rows(final, queue)


# 13 ------------------------------------------------------------------------
class DataIntegrityTests(unittest.TestCase):
    def fixtures(self):
        data = pd.DataFrame({
            "record_id": ["R1", "R2", "R3"],
            "target_category_code": ["SOLID_WASTE", "SOLID_WASTE", "FIRE_EMERGENCY"],
            "source_title": ["Garbage  pile", "Road", "Fire"],
            "telugu_title": ["చెత్త..... ", "రోడ్డు", "మంటలు"],
            "telugu_title_cleaned": ["చెత్త", "రోడ్డు", "మంటలు"],
            "telugu_description_cleaned": ["వివరణ", "వివరణ", "వివరణ"],
        })
        screens = pd.DataFrame({"record_id": data.record_id, "regex_pii_flag": ["False"] * 3,
                                "residual_dot_run": ["False"] * 3, "empty_title": ["False"] * 3,
                                "empty_description": ["False"] * 3, "dedup_group_id": ["DG-R1", "DG-R2", "DG-R3"]})
        flags = pd.DataFrame({"record_id": data.record_id, "label_noise_status": ["EVALUATED"] * 3,
                              "flagged": ["False"] * 3})
        queue = pd.DataFrame({"record_id": ["R1"], "review_origin": [common.ORIGIN_SAMPLE],
                              "in_random_sample": [True]})
        final = pd.DataFrame([dict(valid_review(record_id="R1"), consistency_status="CONSISTENT",
                                   final_review_pass="1")])
        return data, screens, flags, queue, final

    def test_v3_appends_only_and_text_identical(self):
        data, screens, flags, queue, final = self.fixtures()
        v3 = apply.build_v3(data, screens, flags, queue, final)
        self.assertEqual(apply.verify_integrity(data, v3), [])
        self.assertEqual(list(v3.columns[:len(data.columns)]), list(data.columns))
        states = v3.set_index("record_id")["eligibility_state"].to_dict()
        self.assertEqual(states, {"R1": common.STATE_ACCEPTED, "R2": common.STATE_SCREENED,
                                  "R3": common.STATE_RARE})

    def test_integrity_check_detects_changed_text(self):
        data, *_ = self.fixtures()
        changed = data.copy()
        changed.loc[0, "telugu_title_cleaned"] = "మార్చబడింది"
        self.assertTrue(apply.verify_integrity(data, changed))

    def test_round_trip_through_csv_is_byte_identical(self):
        data, screens, flags, queue, final = self.fixtures()
        v3 = apply.build_v3(data, screens, flags, queue, final)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v3.csv"
            common.write_csv(v3, path)
            self.assertEqual(apply.verify_integrity(data, common.read_csv(path)), [])


if __name__ == "__main__":
    unittest.main()
