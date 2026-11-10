
"""Unicode-aware Telugu token extraction."""

import unicodedata

from .normalization import normalize_text


def is_telugu_letter_or_mark(character: str) -> bool:
    """Check whether a character is a Telugu letter or combining mark."""
    codepoint = ord(character)
    category = unicodedata.category(character)

    return (
        0x0C00 <= codepoint <= 0x0C7F
        and category[0] in {"L", "M"}
    )


def tokenize_telugu(text: str) -> list[str]:
    """
    Extract contiguous Telugu letter/mark sequences.

    This is a lightweight Unicode tokenizer, not a
    linguistically validated Telugu morphological tokenizer.
    """
    normalized = normalize_text(text)

    tokens = []
    current_token = []

    for character in normalized:
        if is_telugu_letter_or_mark(character):
            current_token.append(character)
        elif current_token:
            tokens.append("".join(current_token))
            current_token = []

    if current_token:
        tokens.append("".join(current_token))

    return tokens


def unique_telugu_tokens(text: str) -> list[str]:
    """Return unique tokens while preserving their first occurrence."""
    return list(dict.fromkeys(tokenize_telugu(text)))
