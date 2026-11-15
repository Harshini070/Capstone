"""Shared definitions for the GrievanceHub Phase 5 AI-assisted corpus review.

Single source of truth for paths, the review schema, allowed values,
eligibility states and validation rules. Every Phase 5 script and test
imports from here so the rules cannot drift between stages.

Research-integrity notes
------------------------
* The corpus is a translated experimental corpus derived from
  Bengaluru/BBMP municipal complaint data. It is not authentic
  Hyderabad/GHMC citizen complaint data.
* All review decisions are AI-assisted (review_method = AI_ASSISTED).
  There is no human annotation. Two AI passes measure self-consistency,
  not ground truth.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

CANDIDATE_PATH = (
    ROOT / "data" / "processed"
    / "translated_bengaluru_preprocessed_v2_cleaning_candidate.csv"
)
# Source of the original stratified sample (Git-ignored, record level).
RECORD_LEVEL_QUALITY_PATH = (
    ROOT / "reports" / "phase5_telugu_quality_record_level.csv"
)
OLD_SAMPLE_PATH = (
    ROOT / "data" / "interim" / "human_review"
    / "phase5_telugu_human_review_sample.csv"
)
PRIVACY_MANIFEST_PATH = (
    ROOT / "data" / "interim" / "experimental_privacy_exclusion_manifest.csv"
)
TAXONOMY_PATH = ROOT / "configs" / "taxonomy_mapping_provisional_v1.json"

# Record-level outputs: under data/interim/, which is Git-ignored.
REVIEW_DIR = ROOT / "data" / "interim" / "review"
BATCH_DIR = REVIEW_DIR / "batches"
SAMPLE_V2_PATH = REVIEW_DIR / "phase5_review_sample_v2.csv"
SCREENS_PATH = REVIEW_DIR / "corpus_screens.csv"
LABEL_NOISE_FLAGS_PATH = REVIEW_DIR / "label_noise_flags.csv"
REVIEW_QUEUE_PATH = REVIEW_DIR / "review_queue.csv"
REVIEW_FINAL_PATH = REVIEW_DIR / "review_final.csv"
DATASET_V3_PATH = (
    ROOT / "data" / "processed" / "translated_bengaluru_reviewed_v3.csv"
)

# Aggregate-only outputs (safe to commit after inspection).
REPORT_DIR = ROOT / "reports" / "phase5_review"


def review_pass_path(review_pass: str) -> Path:
    return REVIEW_DIR / f"review_pass{review_pass}.csv"


# ---------------------------------------------------------------------------
# Protocol constants
# ---------------------------------------------------------------------------

PROTOCOL_VERSION = "ai_review_protocol_v1"
REVIEW_METHOD = "AI_ASSISTED"
# Default model identifier for this project's review sessions. Each pass
# records the model that actually produced it.
DEFAULT_REVIEWER_MODEL = "claude-opus-5-5"
RANDOM_SEED = 42
SAMPLE_PER_CATEGORY = 30


def taxonomy_version(taxonomy_path: Path = TAXONOMY_PATH) -> str:
    """Version string of the frozen taxonomy registry used for review."""
    return str(json.loads(Path(taxonomy_path).read_text(encoding="utf-8"))["version"])

REVIEW_PASSES = ("1", "2", "ADJUDICATION")

RARE_CLASSES = frozenset(
    {"EMPLOYEE_GRIEVANCES", "SOCIAL_WELFARE", "FIRE_EMERGENCY"}
)

# Placeholder codes that are never valid review outcomes.
NON_ASSIGNABLE_CODES = frozenset(
    {"UNKNOWN_SOURCE_CATEGORY", "OTHER_REVIEW", "UNCLASSIFIED", ""}
)

ORIGIN_SAMPLE = "STRATIFIED_SAMPLE"
ORIGIN_FLAG = "LABEL_NOISE_FLAG"

# ---------------------------------------------------------------------------
# Review schema
# ---------------------------------------------------------------------------

ENUMS = {
    "translation_fidelity": ("PASS", "PARTIAL", "FAIL", "UNCERTAIN"),
    "telugu_grammar": ("GOOD", "MINOR_ISSUES", "MAJOR_ISSUES", "UNCERTAIN"),
    "translation_completeness": (
        "COMPLETE", "PARTIAL", "INCOMPLETE", "UNCERTAIN"
    ),
    "missing_information": ("NONE", "MINOR", "MAJOR"),
    "added_information": ("NONE", "MINOR", "MAJOR"),
    "category_correctness": (
        "CORRECT", "INCORRECT", "AMBIGUOUS", "UNCERTAIN"
    ),
    "geography_assessment": (
        "SOURCE_REFERENCE_VALID",
        "REQUIRES_CONTEXTUAL_REVIEW",
        "INCORRECT_OR_MISTRANSLATED",
        "NO_GEOGRAPHY_REFERENCE",
    ),
    "privacy_assessment": (
        "NO_OBVIOUS_PII", "POTENTIAL_PII", "PII_IDENTIFIED", "UNCERTAIN"
    ),
    "review_decision": (
        "ACCEPT",
        "ACCEPT_WITH_MINOR_ISSUES",
        "RELABEL",
        "AMBIGUOUS",
        "REJECT",
        "ESCALATE",
    ),
    "error_type": (
        "NONE",
        "SOURCE_LABEL_NOISE",
        "CATEGORY_MAPPING_ERROR",
        "TRANSLATION_MEANING_SHIFT",
        "TRANSLATION_ARTIFACT",
        "INSUFFICIENT_CONTEXT",
        "MULTI_ISSUE",
        "OUT_OF_SCOPE",
        "PII",
    ),
}

IDENTITY_FIELDS = (
    "record_id",
    "batch_id",
    "review_pass",
    "review_method",
    "reviewer_model",
    "protocol_version",
    "review_timestamp",
)

JUDGEMENT_FIELDS = (
    "translation_fidelity",
    "telugu_grammar",
    "translation_completeness",
    "missing_information",
    "added_information",
    "category_correctness",
    "corrected_category",
    "secondary_category",
    "geography_assessment",
    "privacy_assessment",
    "pii_spans",
    "review_decision",
    "error_type",
    "evidence_source",
    "evidence_telugu",
    "explanation",
)

REVIEW_FIELDS = IDENTITY_FIELDS + JUDGEMENT_FIELDS

# Fields compared between pass 1 and pass 2 (S7).
DECISION_FIELDS = (
    "review_decision",
    "category_correctness",
    "corrected_category",
    "privacy_assessment",
    "translation_fidelity",
)

MAX_EVIDENCE_CHARS = 300
MAX_EXPLANATION_CHARS = 600

# ---------------------------------------------------------------------------
# Eligibility states (precedence order; first match wins)
# ---------------------------------------------------------------------------

STATE_QUARANTINED_PRIVACY = "QUARANTINED_PRIVACY"
STATE_RARE = "EXCLUDED_RARE_CLASS"
STATE_REJECTED = "AI_REVIEWED_REJECTED"
STATE_AMBIGUOUS = "AI_REVIEWED_AMBIGUOUS"
STATE_QUALITY_BLOCKED = "AI_REVIEWED_QUALITY_BLOCKED"
STATE_RELABELLED = "AI_REVIEWED_RELABELLED"
STATE_ACCEPTED = "AI_REVIEWED_ACCEPTED"
STATE_SCREENED = "SCREENED_NOT_REVIEWED"

ELIGIBILITY_STATES = (
    STATE_QUARANTINED_PRIVACY,
    STATE_RARE,
    STATE_REJECTED,
    STATE_AMBIGUOUS,
    STATE_QUALITY_BLOCKED,
    STATE_RELABELLED,
    STATE_ACCEPTED,
    STATE_SCREENED,
)

# Only these states may enter the primary ML dataset.
ELIGIBLE_STATES = frozenset({STATE_RELABELLED, STATE_ACCEPTED})

BLOCKING_PRIVACY = {
    "PII_IDENTIFIED": "PII_IDENTIFIED",
    "POTENTIAL_PII": "POTENTIAL_PII",
    "UNCERTAIN": "PRIVACY_UNCERTAIN",
}

RESOLVED_CONSISTENCY = frozenset({"CONSISTENT", "RESOLVED_BY_ADJUDICATION"})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def normalize_text_for_hash(text) -> str:
    """NFC, collapse whitespace, casefold. Used only for duplicate keys."""
    if text is None or (isinstance(text, float) and pd.isna(text)):
        return ""
    text = unicodedata.normalize("NFC", str(text))
    return " ".join(text.split()).casefold()


def text_hash(title, description) -> str:
    key = normalize_text_for_hash(title) + "\x1f" + normalize_text_for_hash(
        description
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_csv(path: Path, **kwargs) -> pd.DataFrame:
    return pd.read_csv(
        path, encoding="utf-8-sig", low_memory=False, keep_default_na=False,
        dtype=str, **kwargs,
    )


def write_csv(df: pd.DataFrame, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, encoding="utf-8-sig")


def write_json(data, path: Path) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )


def load_assignable_codes(taxonomy_path: Path = TAXONOMY_PATH) -> frozenset:
    """Category codes a review may assign: every proposed target code in the
    provisional taxonomy except placeholder codes. Read-only."""
    taxonomy = json.loads(Path(taxonomy_path).read_text(encoding="utf-8"))
    codes = {
        str(m.get("proposed_target_category_code", "")).strip().upper()
        for m in taxonomy.get("mappings", [])
    }
    return frozenset(codes - NON_ASSIGNABLE_CODES)


def _blank(value) -> bool:
    return value is None or str(value).strip() == "" or (
        isinstance(value, float) and pd.isna(value)
    )


def _squash(text) -> str:
    return " ".join(unicodedata.normalize("NFC", str(text or "")).split())


def parse_pii_spans(value):
    """Return (spans, error). spans is a list of {type, field, text}."""
    if _blank(value):
        return [], None
    if isinstance(value, list):
        spans = value
    else:
        try:
            spans = json.loads(value)
        except (TypeError, ValueError):
            return None, "pii_spans is not valid JSON"
    if not isinstance(spans, list):
        return None, "pii_spans must be a JSON list"
    for span in spans:
        if not isinstance(span, dict) or not {"type", "field", "text"} <= set(
            span
        ):
            return None, "each pii_spans item needs type, field and text"
    return spans, None


def validate_review_record(
    row: dict,
    given_category: str,
    assignable_codes: frozenset,
    source_text: str | None = None,
    telugu_text: str | None = None,
) -> list[str]:
    """Validate one review row. Returns a list of error messages (empty = valid).

    When source_text / telugu_text are supplied, evidence quotes must appear
    verbatim (after whitespace normalisation) in them. This guards against
    fabricated evidence.
    """
    errors = []
    rid = row.get("record_id", "?")

    for field in REVIEW_FIELDS:
        if field not in row:
            errors.append(f"{rid}: missing field {field}")
    if errors:
        return errors

    for field in ("record_id", "batch_id", "reviewer_model"):
        if _blank(row[field]):
            errors.append(f"{rid}: {field} is empty")
    if row["review_pass"] not in REVIEW_PASSES:
        errors.append(f"{rid}: invalid review_pass {row['review_pass']!r}")
    if row["review_method"] != REVIEW_METHOD:
        errors.append(f"{rid}: review_method must be {REVIEW_METHOD}")
    if row["protocol_version"] != PROTOCOL_VERSION:
        errors.append(f"{rid}: protocol_version must be {PROTOCOL_VERSION}")
    try:
        datetime.fromisoformat(str(row["review_timestamp"]).replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{rid}: review_timestamp is not ISO-8601")

    for field, allowed in ENUMS.items():
        if row[field] not in allowed:
            errors.append(f"{rid}: {field}={row[field]!r} not in {allowed}")
    if errors:
        return errors

    decision = row["review_decision"]
    correctness = row["category_correctness"]
    corrected = str(row["corrected_category"] or "").strip().upper()
    secondary = str(row["secondary_category"] or "").strip().upper()
    given = str(given_category or "").strip().upper()

    if decision == "RELABEL":
        if not corrected:
            errors.append(f"{rid}: RELABEL requires corrected_category")
        elif corrected not in assignable_codes:
            errors.append(f"{rid}: corrected_category {corrected} is not assignable")
        elif corrected == given:
            errors.append(f"{rid}: corrected_category equals the given category")
        if correctness != "INCORRECT":
            errors.append(f"{rid}: RELABEL requires category_correctness=INCORRECT")
    elif corrected:
        errors.append(f"{rid}: corrected_category is only allowed with RELABEL")

    if decision in ("ACCEPT", "ACCEPT_WITH_MINOR_ISSUES") and correctness != "CORRECT":
        errors.append(f"{rid}: {decision} requires category_correctness=CORRECT")
    if decision == "ACCEPT" and row["error_type"] != "NONE":
        errors.append(f"{rid}: ACCEPT requires error_type=NONE")
    if decision != "ACCEPT" and row["error_type"] == "NONE" and decision not in (
        "ACCEPT_WITH_MINOR_ISSUES",
    ):
        errors.append(f"{rid}: {decision} requires a specific error_type")

    if secondary:
        final_category = corrected or given
        if secondary not in assignable_codes:
            errors.append(f"{rid}: secondary_category {secondary} is not assignable")
        elif secondary == final_category:
            errors.append(f"{rid}: secondary_category equals the final category")

    spans, span_error = parse_pii_spans(row["pii_spans"])
    if span_error:
        errors.append(f"{rid}: {span_error}")
    elif row["privacy_assessment"] == "PII_IDENTIFIED" and not spans:
        errors.append(f"{rid}: PII_IDENTIFIED requires pii_spans")

    for field in ("evidence_source", "evidence_telugu"):
        value = str(row[field] or "")
        if not value.strip():
            errors.append(f"{rid}: {field} is required")
        elif len(value) > MAX_EVIDENCE_CHARS:
            errors.append(f"{rid}: {field} exceeds {MAX_EVIDENCE_CHARS} characters")
    if source_text is not None and str(row["evidence_source"]).strip():
        if _squash(row["evidence_source"]) not in _squash(source_text):
            errors.append(f"{rid}: evidence_source is not a verbatim quote")
    if telugu_text is not None and str(row["evidence_telugu"]).strip():
        if _squash(row["evidence_telugu"]) not in _squash(telugu_text):
            errors.append(f"{rid}: evidence_telugu is not a verbatim quote")

    explanation = str(row["explanation"] or "").strip()
    if decision != "ACCEPT" and not explanation:
        errors.append(f"{rid}: explanation is required for {decision}")
    if len(explanation) > MAX_EXPLANATION_CHARS:
        errors.append(f"{rid}: explanation exceeds {MAX_EXPLANATION_CHARS} characters")

    return errors


def assign_eligibility(record: dict) -> tuple[str, str]:
    """Assign exactly one eligibility state. Returns (state, reason).

    Expected keys (missing keys are treated conservatively):
      reviewed (bool), final_category, review_decision, privacy_assessment,
      consistency_status, translation_fidelity, missing_information,
      added_information, residual_dot_run (bool), empty_title (bool),
      empty_description (bool), evidence_present (bool), regex_pii_flag (bool)
    """
    reviewed = bool(record.get("reviewed"))
    category = str(record.get("final_category") or "").strip().upper()

    # 1. Privacy quarantine always comes first.
    if reviewed:
        privacy = record.get("privacy_assessment")
        if privacy in BLOCKING_PRIVACY:
            return STATE_QUARANTINED_PRIVACY, BLOCKING_PRIVACY[privacy]
        if privacy != "NO_OBVIOUS_PII":
            return STATE_QUARANTINED_PRIVACY, "PRIVACY_NOT_CONFIRMED"
    elif record.get("regex_pii_flag"):
        return STATE_QUARANTINED_PRIVACY, "REGEX_PII_FLAG_UNREVIEWED"

    # 2. Rare classes stay in the taxonomy but are excluded from ML.
    if category in RARE_CLASSES:
        return STATE_RARE, category

    if not reviewed:
        return STATE_SCREENED, "AUTOMATED_SCREENS_ONLY"

    decision = record.get("review_decision")
    consistency = record.get("consistency_status")

    # 3-4. Final review decisions that exclude the record.
    if decision in ("REJECT", "ESCALATE"):
        return STATE_REJECTED, decision
    if consistency not in RESOLVED_CONSISTENCY:
        return STATE_REJECTED, "UNRESOLVED_AI_DISAGREEMENT"
    if decision == "AMBIGUOUS":
        return STATE_AMBIGUOUS, "AMBIGUOUS"

    # 5. Quality gates for ACCEPT / RELABEL.
    failed = []
    if record.get("translation_fidelity") not in ("PASS", "PARTIAL"):
        failed.append("TRANSLATION_FIDELITY")
    if record.get("missing_information") == "MAJOR":
        failed.append("MAJOR_MISSING_INFORMATION")
    if record.get("added_information") == "MAJOR":
        failed.append("MAJOR_ADDED_INFORMATION")
    if record.get("residual_dot_run", True):
        failed.append("RESIDUAL_DOT_RUN")
    if record.get("empty_title", True):
        failed.append("EMPTY_TITLE")
    if record.get("empty_description", True):
        failed.append("EMPTY_DESCRIPTION")
    if not record.get("evidence_present"):
        failed.append("MISSING_EVIDENCE")
    if decision not in ("ACCEPT", "ACCEPT_WITH_MINOR_ISSUES", "RELABEL"):
        failed.append(f"UNEXPECTED_DECISION_{decision}")
    if failed:
        return STATE_QUALITY_BLOCKED, ";".join(failed)

    if decision == "RELABEL":
        return STATE_RELABELLED, "RELABEL"
    return STATE_ACCEPTED, decision
