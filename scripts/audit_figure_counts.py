import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "analysis"
EXPECTED_TOTAL = 90

EXCLUSIVE_TABLES = {
    "publication_year": "count_publication_year.csv",
    "primary_application": "count_primary_application.csv",
    "expert_specialization": "count_expert_specialization.csv",
    "moe_functional_role": "count_moe_functional_role.csv",
    "routing_density": "count_routing_density.csv",
    "evidence_tier": "count_evidence_tier_audited.csv",
}

def count_total(filename: str) -> int:
    with (ANALYSIS / filename).open(encoding="utf-8-sig", newline="") as handle:
        return sum(int(row["n"]) for row in csv.DictReader(handle))

results = {
    name: {
        "source": filename,
        "sum": count_total(filename),
        "expected": EXPECTED_TOTAL,
    }
    for name, filename in EXCLUSIVE_TABLES.items()
}
for result in results.values():
    result["matches_expected_total"] = result["sum"] == result["expected"]

audit = {
    "manuscript_included_studies": EXPECTED_TOTAL,
    "exclusive_figure_groups": results,
    "multilabel_note": (
        "Task-modality co-occurrences, routing granularity, training/adaptation methods, "
        "and independent evidence indicators permit repeated study counts and are not "
        "expected to sum to 90."
    ),
    "all_exclusive_groups_match": all(
        result["matches_expected_total"] for result in results.values()
    ),
}

output = ANALYSIS / "figure_count_audit.json"
output.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
print(json.dumps(audit, indent=2))

if not audit["all_exclusive_groups_match"]:
    raise SystemExit("Figure count audit failed")
