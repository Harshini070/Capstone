import unittest

from src.grievancehub.nlp.classification import classify_complaint


ALLOWED = {
    "SOLID_WASTE", "ROAD_INFRASTRUCTURE", "WATER_SUPPLY",
    "STREETLIGHT", "SEWERAGE_DRAINAGE", "TRAFFIC_SAFETY",
}


class RuleClassifierTests(unittest.TestCase):
    def test_garbage_complaint(self):
        result = classify_complaint(
            "మా వీధిలో చెత్త పేరుకుపోయింది",
            "చెత్తను తొలగించడం లేదు. దుర్వాసన వస్తోంది.",
            ALLOWED,
        )
        self.assertEqual(result["predicted_category"], "SOLID_WASTE")
        self.assertEqual(result["prediction_status"], "PROVISIONAL_RULE_MATCH")
        self.assertIsNone(result["confidence"])

    def test_road_complaint(self):
        result = classify_complaint(
            "మా రోడ్డుపై పెద్ద గుంతలు ఉన్నాయి",
            "రోడ్డు మరమ్మతు చేయండి",
            ALLOWED,
        )
        self.assertEqual(result["predicted_category"], "ROAD_INFRASTRUCTURE")

    def test_unknown_text_abstains(self):
        result = classify_complaint(
            "నాకు ఒక సమస్య ఉంది",
            "దయచేసి సహాయం చేయండి",
            ALLOWED,
        )
        self.assertEqual(result["predicted_category"], "UNCLASSIFIED")
        self.assertEqual(result["prediction_status"], "REVIEW_REQUIRED")

    def test_category_must_be_in_taxonomy(self):
        result = classify_complaint(
            "మా వీధిలో చెత్త పేరుకుపోయింది",
            "చెత్తను తొలగించండి",
            {"ROAD_INFRASTRUCTURE"},
        )
        self.assertEqual(result["predicted_category"], "UNCLASSIFIED")

    def test_nested_phrase_not_double_counted(self):
        # "మురుగు నీరు" (5) contains "మురుగు" (4); only the longer phrase
        # should score.
        result = classify_complaint("మురుగు నీరు", "", ALLOWED)
        self.assertEqual(result["predicted_category"], "SEWERAGE_DRAINAGE")
        self.assertEqual(result["rule_score"], 5)
        self.assertEqual(result["matched_terms"], ["మురుగు నీరు"])

    def test_short_phrase_still_counts_outside_longer_match(self):
        # Title "చెత్త" stands alone; the "చెత్త" inside "చెత్తను తొలగించ"
        # is absorbed by the longer phrase.
        result = classify_complaint(
            "మా వీధిలో చెత్త పేరుకుపోయింది",
            "చెత్తను తొలగించడం లేదు. దుర్వాసన వస్తోంది.",
            ALLOWED,
        )
        self.assertEqual(result["rule_score"], 3 + 4 + 2)
        self.assertEqual(
            result["matched_terms"], ["చెత్త", "చెత్తను తొలగించ", "దుర్వాసన"]
        )

    def test_longer_phrase_wins_across_categories(self):
        # "రోడ్డు ప్రమాదం" is TRAFFIC_SAFETY; the embedded "రోడ్డు" must not
        # also score ROAD_INFRASTRUCTURE.
        result = classify_complaint("రోడ్డు ప్రమాదం జరిగింది", "", ALLOWED)
        self.assertEqual(result["predicted_category"], "TRAFFIC_SAFETY")
        self.assertEqual(result["alternatives"], [])

    def test_tied_scores_abstain_as_ambiguous(self):
        result = classify_complaint("చెత్త", "రోడ్డు", ALLOWED)
        self.assertEqual(result["predicted_category"], "UNCLASSIFIED")
        self.assertEqual(result["abstention_reason"], "AMBIGUOUS_RULE_MATCH")


if __name__ == "__main__":
    unittest.main()
