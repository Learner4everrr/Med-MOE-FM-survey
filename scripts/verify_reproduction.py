"""Check every fixed numeric series and matrix in Figures 3-5 against the data."""
import json
from pathlib import Path

import pandas as pd
import revision_round2_figures as figure

ROOT = Path(__file__).resolve().parents[1]
records = json.loads((ROOT / "data/analysis_studies.json").read_text(encoding="utf-8"))["studies"]
data = pd.DataFrame(records)


def labels(value):
    return {item.strip() for item in str(value).split(";") if item.strip()}


def count(field, value):
    return sum(value in labels(row[field]) for row in records)


def boolean_count(field):
    return sum(str(row[field]).lower() in {"1", "true", "yes", "y"} for row in records)


def matrix(row_field, row_order, column_field, column_order):
    return [[sum(a in labels(row[row_field]) and b in labels(row[column_field])
                 for row in records) for b in column_order] for a in row_order]


experts = ["Adapter/parameter experts", "Clinical-domain experts",
           "Generic/unclear specialization", "Modality experts", "Model/scale experts",
           "Patient/subpopulation experts", "Task experts"]
applications = ["Medical foundation models and LLM platforms",
                "Clinical diagnosis, prognosis and decision support",
                "Multimodal clinical intelligence", "Evaluation, robustness and implementation",
                "Clinical NLP, documentation and question answering",
                "Treatment, recommendation and causal inference",
                "EHR, patient trajectories and risk prediction"]
modalities = ["medical imaging", "image + text / vision-language", "omics / molecular",
              "clinical text / notes", "physiological / wearable signals",
              "knowledge graph / medical knowledge", "EHR structured/tabular"]
units = ["Modality", "Task", "Feature patch or voxel", "Token", "Decision or model",
         "Patient or sample", "Not clearly reported"]
roles = ["Multimodal/data fusion", "Heterogeneity/stratification",
         "Parameter-efficient adaptation", "Feature or decision specialization",
         "Conditional computation/scaling", "Multi-task sharing", "Decision/model collaboration"]
tiers = ["Level 1: benchmark, synthetic, or non-patient evaluation",
         "Level 2: internal retrospective patient-data evaluation",
         "Level 3: independent or multicentre evaluation"]

assert len(records) == len(set(data.record_id)) == figure.N == 90
assert [count("year", str(year)) for year in figure.YEARS] == figure.ANNUAL
assert list(pd.Series(figure.ANNUAL).cumsum()) == figure.CUMULATIVE
assert [count("primary_application", value) for value in applications] == figure.APP_COUNTS
assert matrix("primary_application", applications, "expert_specialization", experts) == figure.APP_MATRIX
assert matrix("modalities", modalities, "expert_specialization", experts) == figure.MOD_MATRIX
assert matrix("routing_granularity", units, "expert_specialization", experts) == figure.UNIT_MATRIX
assert [count("evidence_tier_audited", value) for value in tiers] == figure.EVIDENCE
assert matrix("moe_functional_role", roles, "evidence_tier_audited", tiers) == figure.ROLE_MATRIX
signal_counts = [boolean_count("external_evaluation_audited"),
                 boolean_count("multicentre_evaluation_audited"),
                 boolean_count("prospective_evaluation_audited"),
                 boolean_count("interpretable_reported"), boolean_count("fairness_analysis"),
                 boolean_count("clinician_or_human_evaluation"),
                 sum("code or repository" in row["reproducibility_signals"].lower()
                     for row in records)]
assert signal_counts == [value for _, value in figure.SIGNALS]
detail = [float(pd.to_numeric(data.reporting_completeness_pct).median()),
          round(100 * boolean_count("has_routing_detail") / len(records), 1),
          round(100 * boolean_count("has_expert_detail") / len(records), 1)]
assert detail == [value for _, value in figure.DETAIL]
for field in ["expert_specialization", "moe_functional_role", "routing_density",
              "routing_signal", "adaptation_methods"]:
    for category, n, percent in figure.counts(field):
        expected = count(field, category)
        assert n == expected and percent == round(100 * expected / len(records), 1)
print("Verified all fixed figure values and input count tables against 90 structured study records.")
