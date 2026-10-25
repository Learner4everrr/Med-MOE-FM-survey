"""Reproduce study counts and cross-tabulations from public structured data.

The analysis logic is retained from the manuscript workflow. Original article
text and internal workflow fields are not needed and are not distributed.
"""
from __future__ import annotations

import json
from pathlib import Path
import pandas as pd

PAPER_DIR = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = PAPER_DIR / "analysis"
ANALYSIS_DIR.mkdir(exist_ok=True)
SOURCE = PAPER_DIR / "data" / "analysis_studies.json"

def multi_values(series: pd.Series) -> list[str]:
    values: list[str] = []
    for raw in series.fillna("").astype(str):
        values.extend([x.strip() for x in raw.split(";") if x.strip()])
    return values


def count_multi(df: pd.DataFrame, field: str, drop_unclear: bool = False) -> pd.DataFrame:
    counts = pd.Series(multi_values(df[field])).value_counts()
    if drop_unclear:
        counts = counts[~counts.index.str.contains("not clearly|not reported|unclear", case=False, regex=True)]
    out = counts.rename_axis("category").reset_index(name="n")
    out["percent"] = (100 * out["n"] / len(df)).round(1)
    return out


def as_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


df = pd.DataFrame(json.loads(SOURCE.read_text(encoding="utf-8"))["studies"]).fillna("")
df = df[df["model_paradigm"] == "LLM/VLM/foundation-model MoE"].copy()

for field in [
    "fairness_analysis",
    "clinician_or_human_evaluation",
    "interpretable_reported",
    "peer_reviewed",
    "has_routing_detail",
    "has_expert_detail",
    "has_architecture_detail",
    "has_baseline",
    "has_quant_results",
    "retrieval_augmented",
    "agent_tool_use",
    "statistical_inference",
    "class_imbalance",
    "input_dependent_routing_audited",
    "non_moe_comparator_audited",
]:
    df[field + "_bool"] = df[field].map(as_bool)

df["new_external_bool"] = df["external_evaluation_audited"].map(as_bool)
df["new_multicentre_bool"] = df["multicentre_evaluation_audited"].map(as_bool)
df["new_prospective_bool"] = df["prospective_evaluation_audited"].map(as_bool)
df["year_num"] = pd.to_numeric(df["year"], errors="coerce")
df["reporting_completeness_pct"] = pd.to_numeric(df["reporting_completeness_pct"], errors="coerce")

df.to_csv(ANALYSIS_DIR / "foundation_model_studies_audited.csv", index=False, encoding="utf-8-sig")

fields = [
    "primary_application",
    "medical_specialties",
    "tasks",
    "modalities",
    "datasets",
    "expert_specialization",
    "moe_functional_role",
    "routing_gating",
    "routing_density",
    "routing_granularity",
    "routing_signal",
    "backbones",
    "adaptation_methods",
    "evaluation_dimensions",
    "ethics_safety_themes",
    "privacy_security_methods",
    "reproducibility_signals",
    "model_access",
    "data_provenance",
    "evidence_tier_audited",
]
counts: dict[str, pd.DataFrame] = {}
CATEGORY_ORDERS = {
    "primary_application": [
        "Medical foundation models and LLM platforms",
        "Clinical diagnosis, prognosis and decision support",
        "Multimodal clinical intelligence",
        "Evaluation, robustness and implementation",
        "Clinical NLP, documentation and question answering",
        "Treatment, recommendation and causal inference",
        "EHR, patient trajectories and risk prediction",
    ],
    "moe_functional_role": [
        "Multimodal/data fusion",
        "Heterogeneity/stratification",
        "Parameter-efficient adaptation",
        "Feature or decision specialization",
        "Conditional computation/scaling",
        "Multi-task sharing",
        "Decision/model collaboration",
    ],
}
for field in fields:
    counts[field] = count_multi(df, field)
    if field in CATEGORY_ORDERS:
        order = {category: index for index, category in enumerate(CATEGORY_ORDERS[field])}
        counts[field] = counts[field].sort_values(
            "category", key=lambda values: values.map(order).fillna(len(order))
        ).reset_index(drop=True)
    counts[field].to_csv(ANALYSIS_DIR / f"count_{field}.csv", index=False, encoding="utf-8-sig")

year_counts = df.groupby("year_num").size().reindex(range(2022, 2027), fill_value=0).rename("n").reset_index().sort_values("year_num")
year_counts["percent"] = (100 * year_counts["n"] / len(df)).round(1)
year_counts.to_csv(ANALYSIS_DIR / "count_publication_year.csv", index=False, encoding="utf-8-sig")

indicators = [
    ("Peer reviewed", "peer_reviewed_bool"),
    ("Independent external evaluation", "new_external_bool"),
    ("Multicentre data evaluation", "new_multicentre_bool"),
    ("Prospective/workflow evaluation", "new_prospective_bool"),
    ("Interpretability reported", "interpretable_reported_bool"),
    ("Explicit fairness analysis", "fairness_analysis_bool"),
    ("Clinician/human evaluation", "clinician_or_human_evaluation_bool"),
    ("Routing detail reported", "has_routing_detail_bool"),
    ("Expert detail reported", "has_expert_detail_bool"),
    ("Code/repository signal", None),
    ("Retrieval augmentation", "retrieval_augmented_bool"),
    ("Agent/tool use", "agent_tool_use_bool"),
]
indicator_rows = []
repro_code_ids = set(df.loc[df["reproducibility_signals"].str.contains("Code or repository", case=False, na=False), "record_id"])
for label, field in indicators:
    n = len(repro_code_ids) if field is None else int(df[field].sum())
    indicator_rows.append({"indicator": label, "n": n, "percent": round(100 * n / len(df), 1)})
indicator_df = pd.DataFrame(indicator_rows)
indicator_df.to_csv(ANALYSIS_DIR / "evidence_indicators_strict.csv", index=False, encoding="utf-8-sig")

def crosstab_multi(row_field: str, col_field: str, row_limit: int = 12, col_limit: int = 12) -> pd.DataFrame:
    top_rows = count_multi(df, row_field).head(row_limit)["category"].tolist()
    top_cols = count_multi(df, col_field).head(col_limit)["category"].tolist()
    matrix = pd.DataFrame(0, index=top_rows, columns=top_cols, dtype=int)
    for _, row in df.iterrows():
        rv = [x.strip() for x in str(row[row_field]).split(";") if x.strip()]
        cv = [x.strip() for x in str(row[col_field]).split(";") if x.strip()]
        for r in set(rv).intersection(top_rows):
            for c in set(cv).intersection(top_cols):
                matrix.loc[r, c] += 1
    return matrix


task_modality = crosstab_multi("tasks", "modalities", 10, 8)
task_modality.to_csv(ANALYSIS_DIR / "crosstab_task_by_modality.csv", encoding="utf-8-sig")
application_expert = crosstab_multi("primary_application", "expert_specialization", 10, 10)
application_expert.to_csv(ANALYSIS_DIR / "crosstab_application_by_expert.csv", encoding="utf-8-sig")
role_tier = crosstab_multi("moe_functional_role", "evidence_tier_audited", 10, 10)
role_tier.to_csv(ANALYSIS_DIR / "crosstab_role_by_evidence_tier.csv", encoding="utf-8-sig")
expert_tier = crosstab_multi("expert_specialization", "evidence_tier_audited", 10, 10)
expert_tier.to_csv(ANALYSIS_DIR / "crosstab_expert_by_evidence_tier.csv", encoding="utf-8-sig")
routing_expert = crosstab_multi("routing_granularity", "expert_specialization", 20, 10)
routing_expert.to_csv(ANALYSIS_DIR / "crosstab_routing_unit_by_expert.csv", encoding="utf-8-sig")

sensitivity = df[df["input_dependent_routing_audited_bool"]].copy()
pd.DataFrame([
    {"measure": "Studies with explicit input-dependent routing", "n": len(sensitivity), "denominator": len(df)},
    {"measure": "Modality experts within sensitivity subset", "n": int((sensitivity["expert_specialization"] == "Modality experts").sum()), "denominator": len(sensitivity)},
    {"measure": "Multimodal/data fusion within sensitivity subset", "n": int((sensitivity["moe_functional_role"] == "Multimodal/data fusion").sum()), "denominator": len(sensitivity)},
]).to_csv(ANALYSIS_DIR / "sensitivity_input_dependent_summary.csv", index=False, encoding="utf-8-sig")

def comparator_category(row: pd.Series) -> str:
    if row["non_moe_comparator_audited_bool"]:
        return "At least 1 non-MoE comparator"
    if row["comparator_category"] == "Comparison limited to another MoE configuration":
        return "Comparison limited to another MoE configuration"
    return "No clearly reported non-MoE comparator"

comparator = df.apply(comparator_category, axis=1).value_counts().rename_axis("category").reset_index(name="n")
comparator["percent"] = (100 * comparator["n"] / len(df)).round(1)
comparator.to_csv(ANALYSIS_DIR / "comparator_audit_summary.csv", index=False, encoding="utf-8-sig")

# Representative studies are selected transparently by reporting completeness within each expert family.
representative = (
    df.sort_values(["expert_specialization", "reporting_completeness_pct", "year_num"], ascending=[True, False, False])
    .groupby("expert_specialization", as_index=False)
    .head(3)
    [[
        "record_id", "title", "year", "primary_application", "expert_specialization",
        "moe_functional_role", "routing_gating", "backbones", "evidence_tier_audited",
        "reporting_completeness_pct", "doi"
    ]]
)
representative.to_csv(ANALYSIS_DIR / "representative_studies.csv", index=False, encoding="utf-8-sig")

summary = {
    "n": int(len(df)),
    "year_counts": {str(int(r.year_num)): int(r.n) for r in year_counts.itertuples() if not pd.isna(r.year_num)},
    "peer_reviewed": int(df["peer_reviewed_bool"].sum()),
    "external": int(df["new_external_bool"].sum()),
    "multicentre": int(df["new_multicentre_bool"].sum()),
    "prospective": int(df["new_prospective_bool"].sum()),
    "interpretability": int(df["interpretable_reported_bool"].sum()),
    "fairness": int(df["fairness_analysis_bool"].sum()),
    "human_evaluation": int(df["clinician_or_human_evaluation_bool"].sum()),
    "routing_detail": int(df["has_routing_detail_bool"].sum()),
    "expert_detail": int(df["has_expert_detail_bool"].sum()),
    "code_repository": int(len(repro_code_ids)),
    "median_reporting_completeness": float(df["reporting_completeness_pct"].median()),
    "top_applications": counts["primary_application"].head(10).to_dict(orient="records"),
    "top_tasks": counts["tasks"].head(12).to_dict(orient="records"),
    "top_modalities": counts["modalities"].head(12).to_dict(orient="records"),
    "expert_specialization": counts["expert_specialization"].to_dict(orient="records"),
    "functional_role": counts["moe_functional_role"].to_dict(orient="records"),
    "routing_density": counts["routing_density"].to_dict(orient="records"),
    "evidence_tiers": counts["evidence_tier_audited"].to_dict(orient="records"),
}
(ANALYSIS_DIR / "analysis_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

print(f"Analyzed {len(df)} studies. Outputs: {ANALYSIS_DIR.name}/")
