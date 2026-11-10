
"""Conservative, reproducible text normalization for GrievanceHub."""

import unicodedata


def normalize_text(text: str) -> str:
    """
    Apply Unicode NFC and collapse whitespace.

    Does not remove punctuation, digits, Telugu combining marks,
    Latin characters, or meaningful words.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    text = unicodedata.normalize("NFC", text)
    return " ".join(text.split())


def normalize_record(title: str, description: str) -> dict:
    """Normalize title and description without modifying source fields."""
    return {
        "normalized_title": normalize_text(title),
        "normalized_description": normalize_text(description),
    }
