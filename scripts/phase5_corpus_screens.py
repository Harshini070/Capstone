"""S2 - Automated corpus screens over every record of the working dataset.

Input : data/processed/translated_bengaluru_preprocessed_v2_cleaning_candidate.csv
Output: data/interim/review/corpus_screens.csv        (record level, Git-ignored)
        reports/phase5_review/screens_summary.json     (aggregate counts only)

Every flag here is a screening signal that sets review priority. No flag
clears a record, and a regex match is not proof that personal data is (or
is not) present. The input dataset is never modified.

Checks
------
1. Privacy regex (source English + cleaned Telugu fields)
2. Exact duplicates (SHA-256 of normalised cleaned Telugu text) and near
   duplicates (character 5-gram MinHash + LSH, verified Jaccard >= 0.90),
   combined into a stable dedup_group_id with union-find
3. Translation artifacts (dot runs, repeated punctuation/tokens, question-
   mark-only text, empty or near-empty fields)
4. Text quality (Telugu-script ratio via the project NLP quality checks)
5. Translation-quality signal: LaBSE cross-language similarity if the
   optional dependency is installed; otherwise NOT_EVALUATED. Length and
   number heuristics are reported separately and are never treated as
   semantic validation.
6. Missing/added information heuristics (numbers, length ratio). Named-
   entity omission is NOT_EVALUATED: reliable English->Telugu
   transliteration matching is not available, so the AI review covers it.
7. Category preservation: English keyword signal on the source text versus
   the Telugu rule-classifier output and the given (mapped) category.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import phase5_review_common as common

sys.path.insert(0, str(common.ROOT))
from src.grievancehub.nlp.classification import classify_complaint  # noqa: E402
from src.grievancehub.nlp.feature_extraction import extract_text_features  # noqa: E402

SCREEN_VERSION = "phase5_screens_v1"

# ---------------------------------------------------------------------------
# 1. Privacy patterns
# ---------------------------------------------------------------------------

PII_PATTERNS = {
    "EMAIL": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "INDIAN_MOBILE": re.compile(
        r"(?<![\d])(?:\+?91[\s-]?|0)?[6-9]\d{4}[\s-]?\d{5}(?![\d])"
    ),
    "AADHAAR_LIKE_12_DIGIT": re.compile(r"(?<!\d)\d{4}[\s-]?\d{4}[\s-]?\d{4}(?!\d)"),
    "VEHICLE_REGISTRATION": re.compile(
        r"\b[A-Z]{2}[\s-]?\d{1,2}[\s-]?[A-Z]{1,3}[\s-]?\d{4}\b"
    ),
    "PIN_CODE": re.compile(r"(?<![\d\-/])[1-9]\d{2}\s?\d{3}(?![\d\-/])"),
    "DOOR_NUMBER": re.compile(
        r"(?:#\s?\d+[A-Za-z]?(?:[/-]\d+)*"
        r"|\b(?:door|house|h|flat|plot|site)\.?\s?(?:no|number|num)\.?\s?[:\-]?\s?\d+[A-Za-z]?(?:[/-]\d+)*"
        r"|ఇంటి\s?(?:నెం|నంబర్|సంఖ్య)\.?\s?\d+"
        r"|డోర్\s?(?:నెం|నంబర్)\.?\s?\d+"
        r"|ఫ్లాట్\s?(?:నెం|నంబర్)\.?\s?\d+)",
        re.I,
    ),
    "ADDRESS_PATTERN": re.compile(
        r"\b\d+(?:st|nd|rd|th)\s+(?:cross|main|block|stage|phase)\b"
        r"|\d+\s?(?:వ|వ\s)?\s?(?:క్రాస్|మెయిన్|బ్లాక్|స్టేజ్)",
        re.I,
    ),
    "NAME_CUE": re.compile(
        r"\b(?:Mr|Mrs|Ms|Miss|Sri|Shri|Smt|Dr)\.?\s+[A-Z][a-z]+"
        r"|(?:శ్రీమతి|శ్రీ)\s+[ఀ-౿]+"
        r"|[ఀ-౿]+\s+గారు"
    ),
}

PII_FIELDS = (
    "source_title", "source_description",
    "telugu_title_cleaned", "telugu_description_cleaned",
)


def detect_pii(fields: dict) -> list[dict]:
    """Return regex hits as [{type, field, text, method}]."""
    hits = []
    for field, text in fields.items():
        if not text:
            continue
        for kind, pattern in PII_PATTERNS.items():
            for match in pattern.finditer(text):
                value = match.group(0).strip()
                if kind == "PIN_CODE" and not _plausible_pin(value):
                    continue
                hits.append({"type": kind, "field": field, "text": value,
                             "method": "regex_v1"})
    return _drop_nested(hits)


def _plausible_pin(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    # Karnataka/Telangana/AP PIN prefixes; avoids flagging arbitrary
    # six-digit amounts or IDs.
    return len(digits) == 6 and digits[:2] in {"50", "51", "52", "53", "56", "57", "58", "59"}


def _drop_nested(hits: list[dict]) -> list[dict]:
    """A 10-digit mobile number also matches nothing else; but a 12-digit
    Aadhaar-like run must not additionally produce a PIN hit inside it."""
    kept = []
    for hit in hits:
        if hit["type"] == "PIN_CODE" and any(
            other is not hit and other["field"] == hit["field"]
            and hit["text"] in other["text"] and other["type"] != "PIN_CODE"
            for other in hits
        ):
            continue
        kept.append(hit)
    return kept


# ---------------------------------------------------------------------------
# 2. Duplicates
# ---------------------------------------------------------------------------


class UnionFind:
    def __init__(self, items):
        self.parent = {item: item for item in items}

    def find(self, item):
        root = item
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[item] != root:
            self.parent[item], item = root, self.parent[item]
        return root

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            # Smallest id becomes the root, so group ids are stable.
            if rb < ra:
                ra, rb = rb, ra
            self.parent[rb] = ra


def char_shingles(text: str, k: int = 5) -> set[str]:
    text = common.normalize_text_for_hash(text)
    if len(text) < k:
        return {text} if text else set()
    return {text[i:i + k] for i in range(len(text) - k + 1)}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


_MERSENNE = (1 << 61) - 1


def minhash_signatures(shingle_sets: list[set], num_perm: int = 128,
                       seed: int = common.RANDOM_SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    # a, b < 2^32 and x < 2^32, so a*x + b < 2^64: exact uint64 arithmetic
    # for the universal hash (a*x + b) mod p with p = 2^61 - 1.
    a = rng.integers(1, 1 << 32, size=num_perm, dtype=np.uint64)
    b = rng.integers(0, 1 << 32, size=num_perm, dtype=np.uint64)
    signatures = np.full((len(shingle_sets), num_perm), np.iinfo(np.uint64).max, dtype=np.uint64)
    for row, shingles in enumerate(shingle_sets):
        if not shingles:
            continue
        x = np.fromiter((zlib.crc32(s.encode("utf-8")) for s in shingles),
                        dtype=np.uint64, count=len(shingles))
        hashed = (np.multiply.outer(x, a) + b) % np.uint64(_MERSENNE)
        signatures[row] = hashed.min(axis=0)
    return signatures


def near_duplicate_pairs(shingle_sets: list[set], threshold: float = 0.90,
                         bands: int = 16, rows: int = 8) -> set[tuple[int, int]]:
    """LSH candidate generation, then exact Jaccard verification."""
    signatures = minhash_signatures(shingle_sets, num_perm=bands * rows)
    candidates = set()
    for band in range(bands):
        buckets = defaultdict(list)
        block = signatures[:, band * rows:(band + 1) * rows]
        for idx in range(len(shingle_sets)):
            if shingle_sets[idx]:
                buckets[block[idx].tobytes()].append(idx)
        for members in buckets.values():
            if 1 < len(members) <= 500:
                for i in range(len(members)):
                    for j in range(i + 1, len(members)):
                        candidates.add((members[i], members[j]))
    return {
        (i, j) for i, j in candidates
        if jaccard(shingle_sets[i], shingle_sets[j]) >= threshold
    }


def assign_dedup_groups(record_ids: list[str], titles: list[str],
                        descriptions: list[str], threshold: float = 0.90):
    """Return (exact_group_ids, dedup_group_ids, near_pair_count)."""
    hashes = [common.text_hash(t, d) for t, d in zip(titles, descriptions)]
    uf = UnionFind(record_ids)
    by_hash = defaultdict(list)
    for rid, h in zip(record_ids, hashes):
        by_hash[h].append(rid)
    exact_group = {}
    for members in by_hash.values():
        root = min(members)
        for rid in members:
            exact_group[rid] = f"EG-{root}"
            uf.union(root, rid)
    shingles = [char_shingles(f"{t} {d}") for t, d in zip(titles, descriptions)]
    pairs = near_duplicate_pairs(shingles, threshold=threshold)
    for i, j in pairs:
        uf.union(record_ids[i], record_ids[j])
    exact_ids = [exact_group[rid] for rid in record_ids]
    dedup_ids = [f"DG-{uf.find(rid)}" for rid in record_ids]
    return exact_ids, dedup_ids, len(pairs)


def chained_groups(screens: pd.DataFrame, titles: list[str],
                   descriptions: list[str], threshold: float = 0.90) -> list[str]:
    """Group ids whose minimum pairwise Jaccard is below the threshold."""
    shingles = {
        rid: char_shingles(f"{t} {d}")
        for rid, t, d in zip(screens["record_id"], titles, descriptions)
    }
    chained = []
    for group_id, ids in screens.groupby("dedup_group_id")["record_id"]:
        ids = list(ids)
        if len(ids) < 2:
            continue
        if any(
            jaccard(shingles[ids[i]], shingles[ids[j]]) < threshold
            for i in range(len(ids)) for j in range(i + 1, len(ids))
        ):
            chained.append(group_id)
    return chained


# ---------------------------------------------------------------------------
# 3-4. Artifacts and text quality
# ---------------------------------------------------------------------------

DOT_RUN = re.compile(r"\.{5,}")
REPEATED_PUNCT = re.compile(r"([!?,;:\-_*])\1{2,}")
QUESTION_ONLY = re.compile(r"^[\s?]+$")
TELUGU_LETTER = re.compile(r"[ఀ-౿]")


def repeated_token_run(text: str, run: int = 3) -> bool:
    tokens = text.split()
    count = 1
    for previous, current in zip(tokens, tokens[1:]):
        count = count + 1 if current == previous else 1
        if count >= run:
            return True
    return False


def artifact_flags(title: str, description: str) -> list[str]:
    flags = []
    for name, text in (("title", title), ("description", description)):
        if DOT_RUN.search(text):
            flags.append(f"{name}_residual_dot_run")
        if REPEATED_PUNCT.search(text):
            flags.append(f"{name}_repeated_punctuation")
        if repeated_token_run(text):
            flags.append(f"{name}_repeated_token_run")
        if QUESTION_ONLY.match(text or "?"):
            flags.append(f"{name}_empty_or_question_marks")
        elif len(TELUGU_LETTER.findall(text)) < 3:
            flags.append(f"{name}_near_empty")
    return flags


# ---------------------------------------------------------------------------
# 5-6. Translation-quality signals
# ---------------------------------------------------------------------------

TELUGU_DIGITS = str.maketrans("౦౧౨౩౪౫౬౭౮౯", "0123456789")
NUMBER = re.compile(r"\d+")


def numbers_in(text: str) -> Counter:
    return Counter(NUMBER.findall(str(text).translate(TELUGU_DIGITS)))


def number_mismatch(source: str, telugu: str) -> bool:
    return numbers_in(source) != numbers_in(telugu)


def semantic_similarity(sources: list[str], targets: list[str]):
    """LaBSE cosine similarity if sentence-transformers and the model are
    available locally; otherwise (None, 'NOT_EVALUATED', reason)."""
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError:
        return None, "NOT_EVALUATED", "sentence-transformers not installed"
    try:
        model = SentenceTransformer("sentence-transformers/LaBSE")
    except Exception as error:  # model not downloaded / offline
        return None, "NOT_EVALUATED", f"LaBSE unavailable: {type(error).__name__}"
    src = model.encode(sources, batch_size=64, normalize_embeddings=True)
    tgt = model.encode(targets, batch_size=64, normalize_embeddings=True)
    return (src * tgt).sum(axis=1), "EVALUATED", "LaBSE cosine similarity"


# ---------------------------------------------------------------------------
# 7. Category preservation
# ---------------------------------------------------------------------------

# Deliberately small, transparent English keyword lexicon (whole words).
ENGLISH_CATEGORY_KEYWORDS = {
    "SOLID_WASTE": ["garbage", "waste", "trash", "dump", "dumping", "litter", "debris", "dustbin"],
    "ROAD_INFRASTRUCTURE": ["pothole", "potholes", "road", "roads", "footpath", "pavement", "asphalt", "tar"],
    "STREETLIGHT": ["streetlight", "streetlights", "street light", "street lights", "lamp"],
    "WATER_SUPPLY": ["water supply", "drinking water", "tap", "pipeline", "borewell"],
    "SEWERAGE_DRAINAGE": ["sewage", "sewer", "drain", "drainage", "manhole"],
    "STORMWATER": ["storm water", "stormwater", "flood", "flooding", "rainwater", "waterlogging"],
    "TRAFFIC_SAFETY": ["traffic", "signal", "parking", "speed breaker", "zebra crossing", "junction"],
    "ANIMAL_SERVICES": ["dog", "dogs", "stray", "cattle", "cow", "cows", "monkey", "animal"],
    "POLLUTION": ["pollution", "smoke", "noise", "dust", "burning"],
    "ELECTRICITY": ["electricity", "power cut", "transformer", "electric", "bescom", "current"],
    "PARKS_GREENSPACE": ["park", "tree", "trees", "garden", "playground"],
    "PUBLIC_SANITATION": ["toilet", "toilets", "urinal", "urination", "defecation", "yellow spot"],
    "PUBLIC_SAFETY": ["theft", "crime", "harassment", "unsafe", "security"],
    "PUBLIC_TRANSPORT": ["bus", "bus stop", "bmtc", "metro"],
    "LAKES_WATERBODIES": ["lake", "lakes", "pond", "tank"],
    "CIVIC_DOCUMENTS": ["certificate", "khata", "property tax", "birth certificate", "death certificate"],
    "PUBLIC_INFRASTRUCTURE": ["encroachment", "building", "community hall", "public property"],
}
_KEYWORD_PATTERNS = {
    code: [re.compile(rf"\b{re.escape(w)}\b", re.I) for w in words]
    for code, words in ENGLISH_CATEGORY_KEYWORDS.items()
}


def english_category_signal(text: str) -> str:
    """Return the single best-matching category, or '' if none/tied."""
    counts = {
        code: sum(1 for p in patterns if p.search(text))
        for code, patterns in _KEYWORD_PATTERNS.items()
    }
    best = max(counts.values())
    if best == 0:
        return ""
    winners = [c for c, n in counts.items() if n == best]
    return winners[0] if len(winners) == 1 else ""


def category_signals(source_text: str, title: str, description: str,
                     given: str, allowed: frozenset) -> dict:
    english = english_category_signal(source_text)
    prediction = classify_complaint(title, description, allowed)
    telugu = (
        prediction["predicted_category"]
        if prediction["prediction_status"] == "PROVISIONAL_RULE_MATCH" else ""
    )
    flags = []
    if english and telugu and english != telugu:
        flags.append("source_vs_translation_category_conflict")
    if english and telugu and english == telugu and english != given:
        flags.append("both_signals_disagree_with_given_label")
    return {"english_category_signal": english,
            "telugu_rule_signal": telugu,
            "category_flags": ";".join(flags)}


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run(semantic: bool = True) -> dict:
    df = common.read_csv(common.CANDIDATE_PATH)
    if not df["record_id"].is_unique:
        raise AssertionError("record_id must be unique")
    taxonomy_hash_before = common.file_sha256(common.TAXONOMY_PATH)
    allowed = frozenset(df["target_category_code"].unique()) - common.NON_ASSIGNABLE_CODES

    titles = df["telugu_title_cleaned"].tolist()
    descriptions = df["telugu_description_cleaned"].tolist()
    exact_ids, dedup_ids, near_pairs = assign_dedup_groups(
        df["record_id"].tolist(), titles, descriptions
    )

    rows = []
    for rec, exact_id, dedup_id in zip(df.to_dict("records"), exact_ids, dedup_ids):
        title, description = rec["telugu_title_cleaned"], rec["telugu_description_cleaned"]
        source_text = f"{rec['source_title']} {rec['source_description']}"
        pii = detect_pii({f: rec[f] for f in PII_FIELDS})
        t_feat = extract_text_features(title, "title")
        d_feat = extract_text_features(description, "description")
        telugu_len = len(title) + len(description)
        source_len = max(len(source_text.strip()), 1)
        row = {
            "record_id": rec["record_id"],
            "given_category": rec["target_category_code"],
            "source_category_title": rec["source_category_title"],
            "exact_dup_group": exact_id,
            "dedup_group_id": dedup_id,
            "regex_pii_flag": bool(pii),
            "pii_types": ";".join(sorted({h["type"] for h in pii})),
            "pii_spans": json.dumps(pii, ensure_ascii=False),
            "artifact_flags": ";".join(artifact_flags(title, description)),
            "raw_dot_run": bool(DOT_RUN.search(rec["telugu_title"]) or DOT_RUN.search(rec["telugu_description"])),
            "residual_dot_run": bool(DOT_RUN.search(title) or DOT_RUN.search(description)),
            "empty_title": not title.strip(),
            "empty_description": not description.strip(),
            "title_description_identical": common.normalize_text_for_hash(title) == common.normalize_text_for_hash(description),
            "title_telugu_ratio": round(t_feat["title_telugu_letter_ratio"], 4),
            "description_telugu_ratio": round(d_feat["description_telugu_letter_ratio"], 4),
            "low_telugu_ratio": min(t_feat["title_telugu_letter_ratio"], d_feat["description_telugu_letter_ratio"]) < 0.5,
            "very_short_text": len(TELUGU_LETTER.findall(title + description)) < 15,
            "number_mismatch_flag": number_mismatch(source_text, f"{title} {description}"),
            "telugu_to_source_length_ratio": round(telugu_len / source_len, 4),
            "entity_check_status": "NOT_EVALUATED",
        }
        row.update(category_signals(source_text, title, description,
                                    rec["target_category_code"], allowed))
        rows.append(row)
    screens = pd.DataFrame(rows)

    low, high = screens["telugu_to_source_length_ratio"].quantile([0.01, 0.99])
    screens["length_ratio_flag"] = ~screens["telugu_to_source_length_ratio"].between(low, high)

    if semantic:
        scores, status, note = semantic_similarity(
            (df["source_title"] + " " + df["source_description"]).tolist(),
            (df["telugu_title_cleaned"] + " " + df["telugu_description_cleaned"]).tolist(),
        )
    else:
        scores, status, note = None, "NOT_EVALUATED", "disabled by --no-semantic"
    screens["semantic_signal_status"] = status
    screens["semantic_similarity"] = (
        np.round(scores, 4) if scores is not None else ""
    )
    # Threshold is calibrated later (S7) on the reviewed sample; none applied here.
    screens["low_similarity_flag"] = ""

    flag_cols = ["regex_pii_flag", "residual_dot_run", "low_telugu_ratio",
                 "very_short_text", "number_mismatch_flag", "length_ratio_flag"]
    screens["screen_flag_count"] = (
        screens[flag_cols].sum(axis=1)
        + screens["artifact_flags"].ne("").astype(int)
        + screens["category_flags"].ne("").astype(int)
    )
    screens["screen_version"] = SCREEN_VERSION
    common.write_csv(screens, common.SCREENS_PATH)

    if common.file_sha256(common.TAXONOMY_PATH) != taxonomy_hash_before:
        raise AssertionError("Taxonomy file changed during screening.")

    chained = chained_groups(screens, titles, descriptions)
    group_sizes = screens["dedup_group_id"].value_counts()
    exact_sizes = screens["exact_dup_group"].value_counts()
    pii_type_counts = Counter(
        t for types in screens["pii_types"] if types for t in types.split(";")
    )
    artifact_counts = Counter(
        f for flags in screens["artifact_flags"] if flags for f in flags.split(";")
    )
    category_flag_counts = Counter(
        f for flags in screens["category_flags"] if flags for f in flags.split(";")
    )
    summary = {
        "stage": "S2_corpus_screens",
        "screen_version": SCREEN_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_file": str(common.CANDIDATE_PATH.relative_to(common.ROOT)),
        "records": int(len(screens)),
        "notice": "Aggregate counts only. Flags prioritise review; none clears a record.",
        "privacy": {
            "records_with_regex_flag": int(screens["regex_pii_flag"].sum()),
            "flag_occurrences_by_type": dict(sorted(pii_type_counts.items())),
            "note": "Regex flags are neither proof of PII nor of its absence. 239 records were already held out upstream by experimental_privacy_exclusion_manifest.csv and are not in this input.",
        },
        "duplicates": {
            "exact_groups_size_gt_1": int((exact_sizes > 1).sum()),
            "records_in_exact_groups": int(exact_sizes[exact_sizes > 1].sum()),
            "near_duplicate_pairs_verified": int(near_pairs),
            "dedup_groups_total": int(len(group_sizes)),
            "dedup_groups_size_gt_1": int((group_sizes > 1).sum()),
            "records_in_dedup_groups_size_gt_1": int(group_sizes[group_sizes > 1].sum()),
            "largest_dedup_group": int(group_sizes.max()),
            "groups_with_min_pairwise_jaccard_below_0_90": len(chained),
            "chaining_note": "Union-find can chain dissimilar texts transitively; this counts groups where any pair falls below the threshold.",
            "method": "SHA-256 of NFC/whitespace/casefold-normalised cleaned title+description; character 5-gram MinHash (128 perms, 16 bands x 8 rows), Jaccard >= 0.90 verified exactly; union-find",
        },
        "artifacts": {
            "records_with_raw_dot_run": int(screens["raw_dot_run"].sum()),
            "records_with_residual_dot_run_after_cleaning": int(screens["residual_dot_run"].sum()),
            "flag_counts": dict(sorted(artifact_counts.items())),
        },
        "text_quality": {
            "empty_title": int(screens["empty_title"].sum()),
            "empty_description": int(screens["empty_description"].sum()),
            "title_description_identical": int(screens["title_description_identical"].sum()),
            "low_telugu_ratio_lt_0_5": int(screens["low_telugu_ratio"].sum()),
            "very_short_text_lt_15_telugu_letters": int(screens["very_short_text"].sum()),
        },
        "translation_signals": {
            "semantic_signal_status": status,
            "semantic_signal_note": note,
            "number_mismatch_flag": int(screens["number_mismatch_flag"].sum()),
            "length_ratio_flag": int(screens["length_ratio_flag"].sum()),
            "length_ratio_bounds_p01_p99": [round(float(low), 4), round(float(high), 4)],
            "entity_check_status": "NOT_EVALUATED",
            "note": "Number and length heuristics are quality indicators, not semantic validation.",
        },
        "category_preservation": {
            "flag_counts": dict(sorted(category_flag_counts.items())),
            "records_with_english_signal": int(screens["english_category_signal"].ne("").sum()),
            "records_with_telugu_rule_signal": int(screens["telugu_rule_signal"].ne("").sum()),
            "note": "Signals only; the taxonomy and mappings are never changed automatically.",
        },
        "records_with_any_flag": int((screens["screen_flag_count"] > 0).sum()),
        "taxonomy_sha256_unchanged": True,
    }
    common.write_json(summary, common.REPORT_DIR / "screens_summary.json")
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--no-semantic", action="store_true",
                        help="Skip the optional LaBSE signal (recorded as NOT_EVALUATED).")
    args = parser.parse_args(argv)
    summary = run(semantic=not args.no_semantic)
    print(json.dumps({k: summary[k] for k in ("records", "privacy", "duplicates", "artifacts")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.exit(main())
