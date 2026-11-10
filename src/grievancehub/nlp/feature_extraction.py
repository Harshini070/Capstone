
"""Telugu complaint text feature extraction."""

import unicodedata

from .normalization import normalize_text
from .tokenization import tokenize_telugu


def extract_text_features(text: str, prefix: str) -> dict:
    """Extract reproducible linguistic and text-quality features."""
    if not prefix or not prefix.replace("_", "").isalnum():
        raise ValueError("prefix must contain only letters, digits or underscores")

    normalized = normalize_text(text)
    tokens = tokenize_telugu(normalized)
    unique_tokens = set(tokens)

    letters = [
        ch for ch in normalized
        if unicodedata.category(ch).startswith("L")
    ]

    telugu_letters = sum(
        1 for ch in letters if 0x0C00 <= ord(ch) <= 0x0C7F
    )

    latin_letters = sum(
        1 for ch in letters
        if "LATIN" in unicodedata.name(ch, "")
    )

    punctuation_count = sum(
        1 for ch in normalized
        if unicodedata.category(ch).startswith("P")
    )

    nonspace_count = sum(
        1 for ch in normalized if not ch.isspace()
    )

    max_period_run = max(
        (len(run) for run in _period_runs(normalized)),
        default=0,
    )

    max_repeated_character_run = max(
        (
            len(normalized[i:j])
            for i, j in _repeated_character_spans(normalized)
        ),
        default=1,
    )

    total_letters = len(letters)

    features = {
        "char_count": len(normalized),
        "telugu_token_count": len(tokens),
        "unique_token_count": len(unique_tokens),
        "lexical_diversity": (
            len(unique_tokens) / len(tokens) if tokens else 0.0
        ),
        "telugu_letter_ratio": (
            telugu_letters / total_letters if total_letters else 0.0
        ),
        "latin_letter_ratio": (
            latin_letters / total_letters if total_letters else 0.0
        ),
        "punctuation_ratio": (
            punctuation_count / nonspace_count if nonspace_count else 0.0
        ),
        "max_period_run": max_period_run,
        "max_repeated_character_run": max_repeated_character_run,
    }

    return {f"{prefix}_{key}": value for key, value in features.items()}


def _period_runs(text: str) -> list[str]:
    """Find consecutive ASCII full stops."""
    runs = []
    current = ""

    for character in text:
        if character == ".":
            current += character
        else:
            if current:
                runs.append(current)
                current = ""

    if current:
        runs.append(current)

    return runs


def _repeated_character_spans(text: str) -> list[tuple[int, int]]:
    """Find spans of three or more identical consecutive characters."""
    spans = []
    start = 0

    while start < len(text):
        end = start + 1
        while end < len(text) and text[end] == text[start]:
            end += 1

        if end - start >= 3:
            spans.append((start, end))

        start = end

    return spans
