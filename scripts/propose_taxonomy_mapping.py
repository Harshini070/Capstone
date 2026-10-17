import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "interim" / "source_category_inventory.csv"
OUTPUT = ROOT / "data" / "interim" / "category_mapping_review_v2.csv"

# Project-defined taxonomy proposals, not official GHMC category IDs.
RULES = [
    ("TRAFFIC_SAFETY", "Traffic and Road Safety",
     ["traffic and road safety", "traffic safety", "road safety"]),
    ("PUBLIC_TRANSPORT", "Public Transport",
     ["public transport", "bmtc", "ksrtc", "metro"]),
    ("SOLID_WASTE", "Solid Waste Management",
     ["solid waste", "garbage", "waste management", "garbage and unsanitary",
      "plastic carry bags", "litter", "rubbish"]),
    ("PUBLIC_SANITATION", "Public Sanitation and Hygiene",
     ["yellow spot", "public toilet", "public toilets", "sanitation",
      "unsanitary practices"]),
    ("ANIMAL_SERVICES", "Animal Control and Services",
     ["animal husbandry", "animal catcher", "stray animal", "animal control"]),
    ("STREETLIGHT", "Street Lighting",
     ["street lighting", "streetlights", "street light"]),
    ("WATER_SUPPLY", "Water Supply",
     ["water supply", "water supply and services"]),
    ("SEWERAGE_DRAINAGE", "Sewerage and Drainage",
     ["sewerage", "sewage", "drainage", "storm water drains"]),
    ("STORMWATER", "Stormwater and Flood Management",
     ["storm water", "stormwater", "flooding", "waterlogging"]),
    ("ELECTRICITY", "Electricity and Power",
     ["electricity", "power supply", "electricity and power"]),
    ("POLLUTION", "Pollution and Environmental Nuisance",
     ["pollution", "fire pollution", "noise pollution"]),
    ("ROAD_INFRASTRUCTURE", "Roads and Footpaths",
     ["mobility - roads", "roads and footpaths", "road infrastructure",
      "footpaths"]),
    ("PARKS_GREENSPACE", "Parks and Green Spaces",
     ["parks and recreation", "parks & recreation", "parks & garden",
      "playgrounds", "trees and saplings"]),
    ("LAKES_WATERBODIES", "Lakes and Water Bodies",
     ["lakes", "water bodies"]),
    ("PUBLIC_INFRASTRUCTURE", "Community and Public Infrastructure",
     ["community infrastructure", "pwd"]),
    ("PUBLIC_SAFETY", "Public Safety and Crime",
     ["crime and safety", "safety and crime"]),
    ("FIRE_EMERGENCY", "Fire Safety and Emergency Response",
     ["fire safety"]),
    ("CIVIC_DOCUMENTS", "Certificates and Civic Documentation",
     ["certificates"]),
    ("SOCIAL_WELFARE", "Social Welfare and Benefits",
     ["pension", "ration card"]),
    ("EMPLOYEE_GRIEVANCES", "Employee Grievances",
     ["emp grievance redressal"]),
    ("REGULATORY_ENFORCEMENT", "Regulatory and Enforcement Services",
     ["proibition", "prohibition", "sale of tobacco"]),
    ("OTHER_REVIEW", "Other / Needs Review", ["others", "other"]),
]

def propose(label):
    text = " ".join(str(label or "").casefold().split())

    if not text:
        return None

    for code, name, phrases in RULES:
        if any(phrase in text for phrase in phrases):
            return code, name, "PHRASE_MATCH"

    return "OTHER_REVIEW", "Other / Needs Review", "NO_RULE_MATCH"

def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing {INPUT}. Generate the source category inventory first."
        )

    with INPUT.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames or []

    id_col = (
        "source_category_id" if "source_category_id" in fields
        else "category_id"
    )
    title_col = (
        "source_category_title" if "source_category_title" in fields
        else "category_title"
    )

    if title_col not in fields:
        raise ValueError(f"Missing category title column. Found: {fields}")

    count_col = (
        "record_count" if "record_count" in fields else "source_record_count"
    )

    output_fields = [
        "source_category_id",
        "source_category_title",
        "source_record_count",
        "proposed_target_category_code",
        "proposed_target_category",
        "proposal_basis",
        "mapping_status",
        "reviewer_notes",
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    processed = 0
    skipped = 0

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=output_fields)
        writer.writeheader()

        for row in rows:
            label = str(row.get(title_col) or "").strip()

            if not label:
                skipped += 1
                continue

            result = propose(label)
            code, target, basis = result

            writer.writerow({
                "source_category_id": row.get(id_col, ""),
                "source_category_title": label,
                "source_record_count": row.get(count_col, ""),
                "proposed_target_category_code": code,
                "proposed_target_category": target,
                "proposal_basis": basis,
                "mapping_status": "PENDING_HUMAN_REVIEW",
                "reviewer_notes": "",
            })
            processed += 1

    print(f"Created: {OUTPUT.relative_to(ROOT)}")
    print(f"Categories processed: {processed}")
    print(f"Blank rows skipped: {skipped}")
    print("All proposals still require human review.")

if __name__ == "__main__":
    main()
