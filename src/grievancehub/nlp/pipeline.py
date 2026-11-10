
"""Integrated, non-destructive Telugu NLP processing pipeline."""

from collections.abc import Iterable, Mapping

from .feature_extraction import extract_text_features
from .normalization import normalize_record
from .quality_checks import check_text_quality


PIPELINE_VERSION = "telugu_nlp_pipeline_v1"


def process_record(record: Mapping) -> dict:
    """
    Process one complaint record.

    Original fields are retained in memory.
    Normalized text and derived features are added separately.
    """
    if "record_id" not in record:
        raise ValueError("record_id is required")

    if "telugu_title" not in record:
        raise ValueError("telugu_title is required")

    if "telugu_description" not in record:
        raise ValueError("telugu_description is required")

    title = record["telugu_title"]
    description = record["telugu_description"]

    if not isinstance(title, str) or not isinstance(description, str):
        raise TypeError("Telugu title and description must be strings")

    if not record["record_id"]:
        raise ValueError("record_id cannot be empty")

    # Normalize into separate derived fields.
    normalized = normalize_record(title, description)

    # Extract individual text features.
    title_features = extract_text_features(title, "title")
    description_features = extract_text_features(
        description, "description"
    )

    # Run quality checks.
    quality = check_text_quality(title, description)

    # Preserve original record fields.
    result = dict(record)

    # Add normalized text.
    result.update(normalized)

    # Add numerical features.
    result.update(title_features)
    result.update(description_features)

    # Add quality indicators.
    result.update(quality)

    # Colab-compatible title and description flags.
    result["title_long_period_flag"] = int(
        quality["title_long_period_run"]
    )

    result["title_low_telugu_coverage_flag"] = int(
        quality["title_low_telugu_coverage"]
    )

    result["description_long_period_flag"] = int(
        quality["description_long_period_run"]
    )

    result["description_low_telugu_coverage_flag"] = int(
        quality["description_low_telugu_coverage"]
    )

    # Combined title and description features.
    result["combined_telugu_tokens"] = (
        title_features["title_telugu_token_count"]
        + description_features["description_telugu_token_count"]
    )

    result["combined_char_count"] = (
        title_features["title_char_count"]
        + description_features["description_char_count"]
    )

    result["combined_long_period_flag"] = int(
        quality["title_long_period_run"]
        or quality["description_long_period_run"]
    )

    result["combined_low_telugu_coverage_flag"] = int(
        quality["title_low_telugu_coverage"]
        or quality["description_low_telugu_coverage"]
    )

    # Pipeline provenance.
    result["nlp_pipeline_version"] = PIPELINE_VERSION

    return result


def process_records(records: Iterable[Mapping]) -> list[dict]:
    """
    Process multiple records.

    Rejects duplicate record IDs to prevent accidental
    duplication in downstream datasets.
    """
    results = []
    seen_ids = set()

    for record in records:
        result = process_record(record)
        record_id = result["record_id"]

        if record_id in seen_ids:
            raise ValueError(f"Duplicate record_id: {record_id}")

        seen_ids.add(record_id)
        results.append(result)

    return results
