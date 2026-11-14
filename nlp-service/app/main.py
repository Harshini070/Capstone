from pathlib import Path
import json
import logging
import sys

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.grievancehub.nlp.pipeline import (
    PIPELINE_VERSION,
    process_record,
)
from src.grievancehub.nlp.classification import classify_complaint

TAXONOMY_PATH = PROJECT_ROOT / "configs" / "taxonomy_mapping_provisional_v1.json"

logger = logging.getLogger("grievancehub.nlp_service")

# Parsed taxonomy, keyed by the file's modification time so edits are
# picked up without re-reading the file on every request.
_taxonomy_cache = {"mtime": None, "value": None}

app = FastAPI(
    title="GrievanceHub Telugu NLP Service",
    description="Telugu preprocessing, quality analysis and provisional classification API",
    version="1.1.0",
)


class ComplaintText(BaseModel):
    record_id: str = Field(min_length=1)
    telugu_title: str
    telugu_description: str


def load_assignable_category_codes():
    """Load category codes from the existing provisional taxonomy (cached)."""
    if not TAXONOMY_PATH.exists():
        raise FileNotFoundError(f"Taxonomy not found: {TAXONOMY_PATH}")

    mtime = TAXONOMY_PATH.stat().st_mtime
    if _taxonomy_cache["mtime"] == mtime:
        return _taxonomy_cache["value"]

    with TAXONOMY_PATH.open("r", encoding="utf-8") as file:
        taxonomy = json.load(file)

    codes = set()
    for mapping in taxonomy.get("mappings", []):
        code = mapping.get("proposed_target_category_code")
        status = mapping.get("mapping_status")
        if (
            isinstance(code, str)
            and code.strip()
            and code not in {"UNKNOWN_SOURCE_CATEGORY"}
            and status != "UNCLASSIFIED"
        ):
            codes.add(code.strip().upper())

    _taxonomy_cache["mtime"] = mtime
    _taxonomy_cache["value"] = (frozenset(codes), taxonomy)
    return _taxonomy_cache["value"]


def _internal_error(operation):
    """Log the full traceback server-side; return a generic error to callers."""
    logger.exception("%s failed", operation)
    return HTTPException(
        status_code=500,
        detail=f"{operation} failed due to an internal error.",
    )


@app.get("/health")
def health_check():
    return {
        "service": "GrievanceHub Telugu NLP",
        "status": "healthy",
        "pipeline_version": PIPELINE_VERSION,
        "classifier_version": "telugu_rule_classifier_v1",
    }


@app.post("/api/v1/nlp/process")
def process_complaint(complaint: ComplaintText):
    """Existing preprocessing endpoint; response contract preserved."""
    try:
        result = process_record(complaint.model_dump())

        metadata_keys = {
            "record_id", "telugu_title", "telugu_description",
            "normalized_title", "normalized_description",
            "nlp_pipeline_version",
        }

        quality_flags = {
            key: value for key, value in result.items()
            if isinstance(value, bool)
        }

        features = {
            key: value for key, value in result.items()
            if key not in metadata_keys
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        }

        return {
            "record_id": result["record_id"],
            "pipeline_version": result["nlp_pipeline_version"],
            "normalized_title": result["normalized_title"],
            "normalized_description": result["normalized_description"],
            "features": features,
            "quality_flags": quality_flags,
        }

    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise _internal_error("NLP preprocessing") from error


@app.post("/api/v1/nlp/classify")
def classify_complaint_endpoint(complaint: ComplaintText):
    """Preprocess and produce a provisional, taxonomy-constrained prediction."""
    try:
        processed = process_record(complaint.model_dump())
        allowed_codes, taxonomy = load_assignable_category_codes()

        prediction = classify_complaint(
            title=processed["normalized_title"],
            description=processed["normalized_description"],
            allowed_category_codes=allowed_codes,
        )

        return {
            "record_id": processed["record_id"],
            "pipeline_version": processed["nlp_pipeline_version"],
            "taxonomy_version": str(taxonomy.get("version", "unknown")),
            "taxonomy_status": taxonomy.get("registry_status", "UNKNOWN"),
            "normalized_title": processed["normalized_title"],
            "normalized_description": processed["normalized_description"],
            "prediction": prediction,
            "notice": (
                "Provisional rule-based result only. This is not an ML "
                "prediction, calibrated confidence, or validated category."
            ),
        }

    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        raise _internal_error("NLP classification") from error
