import csv
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]

SOURCE = ROOT / "data/processed/bengaluru_complaints_telugu_reconstructed.csv"
REGISTRY = ROOT / "configs/taxonomy_mapping_provisional_v1.json"
OUTPUT = ROOT / "data/processed/translated_bengaluru_experimental_v1.csv"

def norm(value):
    return " ".join(str(value or "").strip().casefold().split())

def norm_id(value):
    value = str(value or "").strip()
    if not value:
        return ""
    try:
        number = float(value)
        if number.is_integer():
            return str(int(number))
    except ValueError:
        pass
    return value

def has_telugu(value):
    return any("\u0c00" <= ch <= "\u0c7f" for ch in str(value or ""))

def all_question_marks(value):
    value = str(value or "").strip()
    return bool(value) and all(ch == "?" for ch in value)

def main():
    for path in (SOURCE, REGISTRY):
        if not path.exists():
            raise FileNotFoundError(path)

    if OUTPUT.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing output: {OUTPUT}"
        )

    with SOURCE.open("r", encoding="utf-8-sig", newline="") as f:
        source_rows = list(csv.DictReader(f))

    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    mappings = registry["mappings"]

    lookup = {
        (
            norm_id(m["source_category_id"]),
            norm(m["source_category_title"])
        ): m
        for m in mappings
    }

    output_fields = [
        "record_id",
        "source_record_id",
        "source_city",
        "target_city",
        "dataset_type",
        "source_title",
        "source_description",
        "telugu_title",
        "telugu_description",
        "source_category_id",
        "source_category_title",
        "target_category_code",
        "target_category",
        "mapping_status",
        "mapping_rationale",
        "source_ward_id",
        "source_ward_title",
        "source_location",
        "source_address",
        "source_latitude",
        "source_longitude",
        "title_translation_match_status",
        "description_translation_match_status",
        "translation_reconstruction_status",
        "title_has_telugu_script",
        "description_has_telugu_script",
        "title_all_question_marks",
        "description_all_question_marks",
        "translation_quality_status",
        "experimental_candidate",
        "exclusion_reason",
        "human_review_required",
        "release_status"
    ]

    counts = {
        "total": 0,
        "mapped": 0,
        "unknown": 0,
        "manual": 0,
        "pending": 0,
        "translation_quarantine": 0,
        "no_telugu_script": 0,
        "candidates": 0
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields)
        writer.writeheader()

        for index, row in enumerate(source_rows, start=1):
            title_te = str(row.get("title_telugu") or "").strip()
            desc_te = str(row.get("description_telugu") or "").strip()

            key = (
                norm_id(row.get("category_id")),
                norm(row.get("category_title"))
            )
            mapping = lookup.get(key)

            title_bad = all_question_marks(title_te)
            desc_bad = all_question_marks(desc_te)

            title_script = has_telugu(title_te)
            desc_script = has_telugu(desc_te)

            if mapping:
                counts["mapped"] += 1
                status = mapping["mapping_status"]
                target_code = mapping["proposed_target_category_code"]
                target_name = mapping["proposed_target_category"]
                rationale = mapping["reviewer_notes"]

                if status == "PENDING_HUMAN_REVIEW":
                    counts["pending"] += 1
                elif status == "MANUAL_REVIEW_REQUIRED":
                    counts["manual"] += 1
            else:
                counts["unknown"] += 1
                status = "UNCLASSIFIED"
                target_code = "UNKNOWN_SOURCE_CATEGORY"
                target_name = "Unknown Source Category"
                rationale = "Missing source category; no inference performed."

            reasons = []

            if not mapping:
                reasons.append("UNKNOWN_SOURCE_CATEGORY")
            elif status == "MANUAL_REVIEW_REQUIRED":
                reasons.append("MANUAL_REVIEW_REQUIRED")

            if title_bad:
                reasons.append("TITLE_ALL_QUESTION_MARKS")
            if desc_bad:
                reasons.append("DESCRIPTION_ALL_QUESTION_MARKS")

            if title_bad or desc_bad:
                counts["translation_quarantine"] += 1

            if not title_script or not desc_script:
                reasons.append("TELUGU_SCRIPT_REVIEW_REQUIRED")
                counts["no_telugu_script"] += 1

            candidate = (
                mapping is not None
                and status == "PENDING_HUMAN_REVIEW"
                and title_script
                and desc_script
                and not title_bad
                and not desc_bad
            )

            if candidate:
                counts["candidates"] += 1

            if title_bad or desc_bad:
                quality = "QUARANTINE_INVALID_TRANSLATION"
            elif not title_script or not desc_script:
                quality = "HUMAN_REVIEW_NO_TELUGU_SCRIPT"
            else:
                quality = "SCRIPT_CHECK_PASSED_PENDING_HUMAN_REVIEW"

            counts["total"] += 1

            writer.writerow({
                "record_id": f"BG-TEL-{index:05d}",
                "source_record_id": row.get("source_row_id", ""),
                "source_city": "Bengaluru",
                "target_city": "Hyderabad (intended application context; not source geography)",
                "dataset_type": "TRANSLATED_BENGALURU_EXPERIMENTAL_BENCHMARK",
                "source_title": row.get("title", ""),
                "source_description": row.get("description", ""),
                "telugu_title": title_te,
                "telugu_description": desc_te,
                "source_category_id": row.get("category_id", ""),
                "source_category_title": row.get("category_title", ""),
                "target_category_code": target_code,
                "target_category": target_name,
                "mapping_status": status,
                "mapping_rationale": rationale,
                "source_ward_id": row.get("ward_id", ""),
                "source_ward_title": row.get("ward_title", ""),
                "source_location": row.get("location", ""),
                "source_address": row.get("address", ""),
                "source_latitude": row.get("latitude", ""),
                "source_longitude": row.get("longitude", ""),
                "title_translation_match_status": row.get("title_translation_match_status", ""),
                "description_translation_match_status": row.get("description_translation_match_status", ""),
                "translation_reconstruction_status": row.get("translation_reconstruction_status", ""),
                "title_has_telugu_script": title_script,
                "description_has_telugu_script": desc_script,
                "title_all_question_marks": title_bad,
                "description_all_question_marks": desc_bad,
                "translation_quality_status": quality,
                "experimental_candidate": candidate,
                "exclusion_reason": ";".join(reasons),
                "human_review_required": True,
                "release_status": "HOLD"
            })

    print("=== EXPERIMENTAL CORPUS BUILD ===")
    print(f"Output: {OUTPUT.relative_to(ROOT)}")
    for key, value in counts.items():
        print(f"{key}: {value}")

    print("\nAll records retained.")
    print("No source records modified.")
    print("No records approved for public or production release.")
    print("Experimental candidates are provisional, not validated training data.")

if __name__ == "__main__":
    main()
