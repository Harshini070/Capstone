import csv
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/processed/translated_bengaluru_experimental_v1.csv"

def check(condition, message, errors):
    print(f"{'PASS' if condition else 'FAIL'} | {message}")
    if not condition:
        errors.append(message)

def main():
    if not CORPUS.exists():
        raise FileNotFoundError(CORPUS)

    with CORPUS.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        headers = reader.fieldnames or []

    errors = []

    required = [
        "record_id", "source_record_id", "source_city",
        "target_category_code", "mapping_status",
        "telugu_title", "telugu_description",
        "title_has_telugu_script", "description_has_telugu_script",
        "title_all_question_marks", "description_all_question_marks",
        "experimental_candidate", "exclusion_reason", "release_status"
    ]

    check(len(rows) == 16071, "16,071 records retained", errors)
    check(len(headers) == len(set(headers)), "Unique column names", errors)
    check(all(c in headers for c in required), "Required columns present", errors)
    check(
        len({r["record_id"] for r in rows}) == len(rows),
        "Unique record IDs", errors
    )
    check(
        all(r["release_status"] == "HOLD" for r in rows),
        "All records remain on HOLD", errors
    )
    check(
        all(r["source_city"] == "Bengaluru" for r in rows),
        "Source provenance retained", errors
    )

    candidates = [r for r in rows if r["experimental_candidate"] == "True"]
    unknown = [r for r in rows if r["mapping_status"] == "UNCLASSIFIED"]
    manual = [r for r in rows if r["mapping_status"] == "MANUAL_REVIEW_REQUIRED"]
    pending = [r for r in rows if r["mapping_status"] == "PENDING_HUMAN_REVIEW"]

    quarantine = [
        r for r in rows
        if r["title_all_question_marks"] == "True"
        or r["description_all_question_marks"] == "True"
    ]

    script_review = [
        r for r in rows
        if r["title_has_telugu_script"] != "True"
        or r["description_has_telugu_script"] != "True"
    ]

    check(len(unknown) == 32, "32 unknown-category records", errors)
    check(len(manual) == 358, "358 manual-review records", errors)
    check(len(pending) == 15681, "15,681 pending-review records", errors)
    check(len(quarantine) == 43, "43 complaints with quarantined translations", errors)
    check(len(script_review) == 69, "69 complaints requiring Telugu-script review", errors)
    check(len(candidates) == 15613, "15,613 provisional candidates", errors)

    check(
        all(r["mapping_status"] == "PENDING_HUMAN_REVIEW" for r in candidates),
        "Candidates have pending-review mappings only", errors
    )
    check(
        all(
            r["title_has_telugu_script"] == "True"
            and r["description_has_telugu_script"] == "True"
            for r in candidates
        ),
        "Candidates contain Telugu script in both fields", errors
    )
    check(
        all(
            r["title_all_question_marks"] != "True"
            and r["description_all_question_marks"] != "True"
            for r in candidates
        ),
        "No quarantined translations in candidate pool", errors
    )
    check(
        all(r["exclusion_reason"] == "" for r in candidates),
        "Candidates have no exclusion reasons", errors
    )

    print("\n=== CORPUS STATUS SUMMARY ===")
    print("Total:", len(rows))
    print("Candidates:", len(candidates))
    print("Unknown:", len(unknown))
    print("Manual review:", len(manual))
    print("Pending mapping:", len(pending))
    print("Translation quarantine:", len(quarantine))
    print("Telugu-script review:", len(script_review))

    print("\n=== EXCLUSION REASON FREQUENCIES ===")
    reasons = Counter(
        reason
        for row in rows
        for reason in row["exclusion_reason"].split(";")
        if reason
    )
    for reason, count in sorted(reasons.items()):
        print(f"{reason}: {count}")

    print("\n=== FINAL RESULT ===")
    print("PASS" if not errors else f"FAIL: {len(errors)} validation errors")

    if errors:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
