
"""Automated tests for the GrievanceHub Telugu NLP pipeline."""

import unittest

from src.grievancehub.nlp.normalization import normalize_text
from src.grievancehub.nlp.tokenization import tokenize_telugu
from src.grievancehub.nlp.feature_extraction import extract_text_features
from src.grievancehub.nlp.quality_checks import check_text_quality
from src.grievancehub.nlp.pipeline import (
    PIPELINE_VERSION,
    process_record,
    process_records,
)


class TestTeluguNLP(unittest.TestCase):

    def test_normalization(self):
        self.assertEqual(
            normalize_text("  హైదరాబాద్   నగరం  "),
            "హైదరాబాద్ నగరం",
        )

    def test_tokenization(self):
        self.assertEqual(
            tokenize_telugu("హైదరాబాద్ నగరంలో రోడ్డు సమస్య"),
            ["హైదరాబాద్", "నగరంలో", "రోడ్డు", "సమస్య"],
        )

    def test_feature_extraction(self):
        features = extract_text_features(
            "హైదరాబాద్ నగరం",
            "title",
        )
        self.assertEqual(features["title_telugu_token_count"], 2)
        self.assertEqual(features["title_telugu_letter_ratio"], 1.0)

    def test_period_detection(self):
        features = extract_text_features(
            "రోడ్డు సమస్య...............",
            "title",
        )
        self.assertEqual(features["title_max_period_run"], 15)

    def test_quality_flags(self):
        quality = check_text_quality(
            "హైదరాబాద్ నగరం",
            "రోడ్డు సమస్య...............",
        )
        self.assertFalse(quality["empty_title"])
        self.assertTrue(quality["description_long_period_run"])

    def test_source_text_is_preserved(self):
        record = {
            "record_id": "TEST-001",
            "telugu_title": "  రోడ్డు   సమస్య  ",
            "telugu_description": "రోడ్డు పాడైపోయింది",
        }

        result = process_record(record)

        self.assertEqual(result["telugu_title"], "  రోడ్డు   సమస్య  ")
        self.assertEqual(
            result["normalized_title"],
            "రోడ్డు సమస్య",
        )

    def test_pipeline_version(self):
        record = {
            "record_id": "TEST-002",
            "telugu_title": "రోడ్డు సమస్య",
            "telugu_description": "మా ప్రాంతంలో రోడ్డు పాడైంది",
        }

        result = process_record(record)
        self.assertEqual(
            result["nlp_pipeline_version"],
            PIPELINE_VERSION,
        )

    def test_duplicate_record_ids_rejected(self):
        record = {
            "record_id": "DUP-001",
            "telugu_title": "రోడ్డు సమస్య",
            "telugu_description": "రోడ్డు పాడైంది",
        }

        with self.assertRaises(ValueError):
            process_records([record, record])

    def test_missing_record_id_rejected(self):
        record = {
            "telugu_title": "రోడ్డు సమస్య",
            "telugu_description": "రోడ్డు పాడైంది",
        }

        with self.assertRaises(ValueError):
            process_record(record)


if __name__ == "__main__":
    unittest.main()
