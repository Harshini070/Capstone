
"""Non-destructive quality checks for Telugu complaint text."""

from .feature_extraction import extract_text_features


def check_text_quality(
    title: str,
    description: str,
    low_telugu_threshold: float = 0.50,
    long_period_threshold: int = 10,
) -> dict:
    """
    Return quality indicators without deleting or changing records.

    Thresholds are screening rules, not automatic rejection criteria.
    """
    if not 0 <= low_telugu_threshold <= 1:
        raise ValueError("low_telugu_threshold must be between 0 and 1")

    if long_period_threshold < 1:
        raise ValueError("long_period_threshold must be positive")

    title_features = extract_text_features(title, "title")
    description_features = extract_text_features(
        description, "description"
    )

    return {
        "empty_title": not bool(title.strip()),
        "empty_description": not bool(description.strip()),
        "title_low_telugu_coverage": (
            title_features["title_telugu_letter_ratio"]
            < low_telugu_threshold
        ),
        "description_low_telugu_coverage": (
            description_features["description_telugu_letter_ratio"]
            < low_telugu_threshold
        ),
        "title_long_period_run": (
            title_features["title_max_period_run"]
            >= long_period_threshold
        ),
        "description_long_period_run": (
            description_features["description_max_period_run"]
            >= long_period_threshold
        ),
    }
