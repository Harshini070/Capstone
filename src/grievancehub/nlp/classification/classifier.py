"""Taxonomy-constrained provisional rule classifier."""

from .rule_based import RULES

CLASSIFIER_VERSION = "telugu_rule_classifier_v1"


def classify_complaint(title, description, allowed_category_codes,
                       minimum_score=3, minimum_margin=1):
    """Return a provisional category or abstain.

    `score` is a deterministic rule-match score, NOT a probability.
    """
    if not isinstance(title, str) or not isinstance(description, str):
        raise TypeError("title and description must be strings")

    text = f"{title} {description}".strip().casefold()
    allowed = set(allowed_category_codes or [])
    scores = {}

    for category_code, phrase, weight in _select_matches(text, allowed):
        entry = scores.setdefault(
            category_code, {"score": 0, "matched_terms": []}
        )
        # Count each configured phrase once, even if repeated in text.
        if phrase not in entry["matched_terms"]:
            entry["score"] += weight
            entry["matched_terms"].append(phrase)

    if not scores:
        return _abstain("NO_RULE_MATCH", scores)

    ranked = sorted(
        scores.items(),
        key=lambda item: (-item[1]["score"], item[0])
    )
    top_code, top = ranked[0]
    second_score = ranked[1][1]["score"] if len(ranked) > 1 else 0
    margin = top["score"] - second_score

    if top["score"] < minimum_score:
        return _abstain("INSUFFICIENT_RULE_EVIDENCE", scores)

    if margin < minimum_margin:
        return _abstain("AMBIGUOUS_RULE_MATCH", scores)

    return {
        "predicted_category": top_code,
        "prediction_status": "PROVISIONAL_RULE_MATCH",
        "prediction_method": "RULE_BASED",
        "classifier_version": CLASSIFIER_VERSION,
        "rule_score": top["score"],
        "score_margin": margin,
        "matched_terms": top["matched_terms"],
        "confidence": None,
        "confidence_note": "Not calibrated; rule score is not a probability.",
        "alternatives": [
            {"category": code, "rule_score": data["score"]}
            for code, data in ranked[1:4]
        ],
    }


def _select_matches(text, allowed):
    """Find phrase occurrences using longest-match, non-overlapping spans.

    Plain substring matching double-counts nested phrases (for example
    "మురుగు" inside "మురుగు నీరు") and lets a short phrase from one category
    score inside a longer phrase from another ("రోడ్డు" inside
    "రోడ్డు ప్రమాదం"). Here every occurrence competes for its span of text:
    longer phrases claim their span first, and a shorter phrase only counts
    where it occurs outside every span already claimed.
    """
    occurrences = []
    for category_code, phrases in RULES.items():
        if category_code not in allowed:
            continue
        for phrase, weight in phrases.items():
            needle = phrase.casefold()
            start = text.find(needle)
            while start != -1:
                occurrences.append(
                    (start, start + len(needle), category_code, phrase, weight)
                )
                start = text.find(needle, start + 1)

    # Longest first; ties broken by position, then category for determinism.
    occurrences.sort(key=lambda o: (-(o[1] - o[0]), o[0], o[2]))

    claimed = []
    selected = []
    for start, end, category_code, phrase, weight in occurrences:
        if any(start < c_end and c_start < end for c_start, c_end in claimed):
            continue
        claimed.append((start, end))
        selected.append((start, category_code, phrase, weight))

    # Report matched terms in reading order.
    selected.sort(key=lambda s: s[0])
    return [(code, phrase, weight) for _, code, phrase, weight in selected]


def _abstain(reason, scores):
    ranked = sorted(
        scores.items(),
        key=lambda item: (-item[1]["score"], item[0])
    )
    return {
        "predicted_category": "UNCLASSIFIED",
        "prediction_status": "REVIEW_REQUIRED",
        "prediction_method": "RULE_BASED",
        "classifier_version": CLASSIFIER_VERSION,
        "abstention_reason": reason,
        "rule_score": ranked[0][1]["score"] if ranked else 0,
        "score_margin": None,
        "matched_terms": (
            ranked[0][1]["matched_terms"] if ranked else []
        ),
        "confidence": None,
        "confidence_note": "No calibrated probability is produced.",
        "alternatives": [
            {"category": code, "rule_score": data["score"]}
            for code, data in ranked[:3]
        ],
    }
