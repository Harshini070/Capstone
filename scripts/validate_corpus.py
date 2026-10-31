#!/usr/bin/env python3
"""Structural and policy screening validator for GrievanceHub."""

import csv
import re
import sys
from datetime import date
from pathlib import Path

REQUIRED = [
    "record_id",
    "complaint_text_te",
    "source_type",
    "source_name",
    "collection_date",
    "language_label",
    "script_label",
    "hyderabad_relevance",
    "consent_status",
    "license_or_terms",
    "release_status",
]

ALLOWED = {
    "source_type": {
        "PUBLIC_WEB", "VOLUNTARY_SUBMISSION",
        "SYNTHETIC_TEST", "TRANSLATED_BENCHMARK"
    },
    "language_label": {
        "TELUGU", "MIXED_TELUGU", "OTHER", "UNCERTAIN"
    },
    "script_label": {
        "TELUGU_SCRIPT", "LATIN_SCRIPT",
        "MIXED_SCRIPT", "OTHER"
    },
    "hyderabad_relevance": {
        "CONFIRMED", "LIKELY", "UNKNOWN", "NOT_HYDERABAD"
    },
    "consent_status": {
        "NOT_APPLICABLE_PUBLIC", "NOT_APPLICABLE_SYNTHETIC", "CONSENT_RECORDED",
        "CONSENT_MISSING", "WITHDRAWN"
    },
    "annotation_status": {
        "UNANNOTATED", "ANNOTATED",
        "DISAGREEMENT", "ADJUDICATED"
    },
    "priority_label": {
        "LOW", "MEDIUM", "HIGH", "URGENT", "UNASSIGNED"
    },
    "release_status": {
        "HOLD", "INTERNAL_ONLY", "APPROVED_FOR_RESEARCH"
    },
    "split": {"UNASSIGNED", "TRAIN", "VALIDATION", "TEST"},
}

PII_PATTERNS = {
    "email_like": re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I
    ),
    "india_mobile_like": re.compile(
        r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)"
    ),
    "url_like": re.compile(r"\bhttps?://\S+", re.I),
}


def validate(path):
    errors = []
    warnings = []
    pii_rows = []
    hold_rows = []

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)
            headers = reader.fieldnames or []

            if not headers:
                print("ERROR: CSV has no header row.")
                return 1

            if len(headers) != len(set(headers)):
                errors.append("Duplicate column names detected.")

            for column in REQUIRED:
                if column not in headers:
                    errors.append(f"Missing required column: {column}")

            if errors:
                for error in errors:
                    print("ERROR:", error)
                return 1

            rows = list(reader)

    except (OSError, UnicodeError, csv.Error) as exc:
        print(f"ERROR: Could not read CSV: {exc}")
        return 1

    seen_ids = set()

    for line, row in enumerate(rows, start=2):
        record_id = row.get("record_id", "").strip()
        source_type = row.get("source_type", "").strip()
        release = row.get("release_status", "").strip()
        consent = row.get("consent_status", "").strip()
        annotation = row.get("annotation_status", "UNANNOTATED").strip()
        personal_data = row.get("contains_personal_data", "").strip().upper()

        if not record_id:
            errors.append(f"Line {line}: blank record_id.")
        elif record_id in seen_ids:
            errors.append(f"Line {line}: duplicate record_id '{record_id}'.")
        else:
            seen_ids.add(record_id)

        for column in REQUIRED:
            if not row.get(column, "").strip():
                errors.append(f"Line {line}: blank required field '{column}'.")

        for column, allowed in ALLOWED.items():
            value = row.get(column, "").strip()
            if value and value not in allowed:
                errors.append(
                    f"Line {line}: invalid {column} value '{value}'."
                )

        text = row.get("complaint_text_te", "").strip()
        if not text:
            errors.append(f"Line {line}: complaint text is empty.")

        date_value = row.get("collection_date", "").strip()
        try:
            parsed = date.fromisoformat(date_value)
            if parsed.isoformat() != date_value:
                raise ValueError
        except ValueError:
            errors.append(
                f"Line {line}: collection_date must use YYYY-MM-DD."
            )

        if source_type == "PUBLIC_WEB":
            if consent != "NOT_APPLICABLE_PUBLIC":
                errors.append(
                    f"Line {line}: PUBLIC_WEB must use "
                    "NOT_APPLICABLE_PUBLIC consent status."
                )
            if not row.get("source_url_or_reference", "").strip():
                warnings.append(
                    f"Line {line}: public source URL/reference is missing."
                )

        if source_type == "VOLUNTARY_SUBMISSION":
            if consent != "CONSENT_RECORDED":
                if release == "APPROVED_FOR_RESEARCH":
                    errors.append(
                        f"Line {line}: voluntary submission cannot be "
                        "release-approved without recorded consent."
                    )
                warnings.append(
                    f"Line {line}: voluntary submission requires "
                    "consent verification."
                )

        if source_type in {"SYNTHETIC_TEST", "TRANSLATED_BENCHMARK"}:
            warnings.append(
                f"Line {line}: {source_type} is not part of the "
                "primary authentic Telugu corpus."
            )

        if annotation in {"ANNOTATED", "DISAGREEMENT", "ADJUDICATED"}:
            for column in ("category_id", "priority_label"):
                if not row.get(column, "").strip():
                    errors.append(
                        f"Line {line}: {column} required after annotation."
                    )

        combined_text = " ".join([
            row.get("complaint_text_te", ""),
            row.get("complaint_text_normalized_te", ""),
        ])

        hits = [
            name for name, pattern in PII_PATTERNS.items()
            if pattern.search(combined_text)
        ]

        if hits:
            pii_rows.append((line, hits))
            hold_rows.append(line)

        if personal_data in {"TRUE", "UNKNOWN"}:
            if release == "APPROVED_FOR_RESEARCH":
                errors.append(
                    f"Line {line}: personal data is TRUE/UNKNOWN "
                    "but release is approved."
                )
            hold_rows.append(line)

        if consent in {"CONSENT_MISSING", "WITHDRAWN"}:
            if release == "APPROVED_FOR_RESEARCH":
                errors.append(
                    f"Line {line}: missing/withdrawn consent "
                    "cannot be release-approved."
                )
            hold_rows.append(line)

        if release == "APPROVED_FOR_RESEARCH":
            if not row.get("source_name", "").strip():
                errors.append(
                    f"Line {line}: approved record has no source name."
                )
            if not row.get("license_or_terms", "").strip():
                errors.append(
                    f"Line {line}: approved record has no terms reference."
                )

    print(f"Rows checked: {len(rows)}")
    print(f"Columns: {len(rows[0]) if rows else 0}")
    print(f"Structural/policy errors: {len(errors)}")

    for error in errors:
        print("ERROR:", error)

    print(f"Warnings: {len(warnings)}")
    for warning in warnings:
        print("WARNING:", warning)

    print(f"Possible PII rows: {len(pii_rows)}")
    for line, hits in pii_rows[:100]:
        print(f"  CSV line {line}: {', '.join(hits)}")

    print(f"Rows requiring release hold/review: {len(set(hold_rows))}")

    print(
        "\nLIMITATION: This validator does not certify source authenticity, "
        "legal permission, consent authenticity, complete PII absence, "
        "Telugu linguistic correctness, or annotation quality."
    )

    return 1 if errors else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python validate_corpus.py path/to/complaints.csv")
        sys.exit(2)

    sys.exit(validate(Path(sys.argv[1])))
