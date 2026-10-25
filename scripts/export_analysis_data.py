"""Export only the structured fields needed to reproduce the review analyses.

Usage: python scripts/export_analysis_data.py source.csv data/analysis_studies.json
The source CSV is not redistributed. This explicit allowlist excludes reviewer
assignments, article text, evidence excerpts, paths, and extraction diagnostics.
"""
import argparse
import csv
import json
from pathlib import Path

FIELDS = [
    "record_id", "title", "year", "doi", "model_paradigm",
    "primary_application", "medical_specialties", "tasks", "modalities",
    "datasets", "expert_specialization", "moe_functional_role", "routing_gating",
    "routing_density", "routing_granularity", "routing_signal", "backbones",
    "adaptation_methods", "evaluation_dimensions", "ethics_safety_themes",
    "privacy_security_methods", "reproducibility_signals", "model_access",
    "data_provenance", "evidence_tier_audited", "fairness_analysis",
    "clinician_or_human_evaluation", "interpretable_reported", "peer_reviewed",
    "has_routing_detail", "has_expert_detail", "has_architecture_detail",
    "has_baseline", "has_quant_results", "retrieval_augmented", "agent_tool_use",
    "statistical_inference", "class_imbalance", "input_dependent_routing_audited",
    "non_moe_comparator_audited", "external_evaluation_audited",
    "multicentre_evaluation_audited", "prospective_evaluation_audited",
    "reporting_completeness_pct",
]


def export(source, destination):
    with source.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    studies = []
    for row in rows:
        if row["model_paradigm"] != "LLM/VLM/foundation-model MoE":
            continue
        study = {field: row[field] for field in FIELDS}
        if row["non_moe_comparator_audited"].strip().lower() in {"1", "true", "yes", "y"}:
            category = "At least 1 non-MoE comparator"
        elif "another MoE configuration" in row["non_moe_comparator_rationale"]:
            category = "Comparison limited to another MoE configuration"
        else:
            category = "No clearly reported non-MoE comparator"
        study["comparator_category"] = category
        studies.append(study)
    # Stable study-ID order also makes equal-frequency category ordering reproducible.
    studies.sort(key=lambda study: study["record_id"])
    assert len(studies) == len({s["record_id"] for s in studies}) == 90
    payload = {
        "title": "Structured analysis data for Mixture-of-experts in medical foundation models",
        "version": "jamia-round2-2026-10-25",
        "study_count": len(studies),
        "note": "Structured classifications and bibliographic identifiers only. Original field names and category labels are preserved. Semicolons separate multiple labels. No abstracts, full-text evidence excerpts, reviewer assignments, or local workflow fields are included.",
        "studies": studies,
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Exported {len(studies)} studies and {len(studies[0])} fields per study.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    export(args.source, args.destination)
