import fs from "node:fs";
import path from "node:path";

const [inputArg, outputArg = "data/studies.json"] = process.argv.slice(2);

if (!inputArg) {
  console.error("Usage: node scripts/build-public-data.mjs <source.csv> [data/studies.json]");
  process.exit(1);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (quoted) {
      if (char === '"' && next === '"') {
        field += '"';
        index += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
    } else if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field.replace(/\r$/, ""));
      rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }

  if (field.length || row.length) {
    row.push(field.replace(/\r$/, ""));
    rows.push(row);
  }

  const headers = rows
    .shift()
    .map((header, index) => (index === 0 ? header.replace(/^\uFEFF/, "") : header));
  return rows
    .filter((values) => values.some((value) => value.trim()))
    .map((values) => Object.fromEntries(headers.map((header, i) => [header, values[i] ?? ""])));
}

const missingValues = new Set([
  "",
  "not clearly reported",
  "not applicable",
  "not applicable/not reported",
  "status not established",
]);

function clean(value) {
  const normalized = String(value ?? "").trim();
  return missingValues.has(normalized.toLowerCase()) ? null : normalized;
}

function list(value) {
  const normalized = clean(value);
  if (!normalized) return [];
  return normalized
    .split(";")
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item) => !missingValues.has(item.toLowerCase()));
}

function authors(value) {
  const normalized = clean(value);
  if (!normalized) return [];
  const separator = normalized.includes(";") ? /\s*;\s*/ : /\s+and\s+/i;
  return normalized
    .split(separator)
    .map((item) => item.trim())
    .filter(Boolean)
    .filter((item) => !/^Association for (the Advancement of )?Artificial Intelligence\b/i.test(item));
}

function title(value) {
  return clean(value)?.replace(/\$\^4\$/g, "⁴") ?? null;
}

function bool(value) {
  return String(value ?? "").trim().toLowerCase() === "true";
}

function number(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

const source = parseCsv(fs.readFileSync(inputArg, "utf8"));
const studies = source.map((row) => ({
  id: clean(row.record_id),
  title: title(row.title),
  authors: authors(row.authors),
  year: number(row.year),
  doi: clean(row.doi),
  documentType: clean(row.document_type),
  application: clean(row.primary_application),
  paradigm: clean(row.model_paradigm),
  expertOrganization: clean(row.expert_specialization),
  moeFunction: clean(row.moe_functional_role),
  modalities: list(row.modalities),
  tasks: list(row.tasks),
  specialties: list(row.medical_specialties),
  datasets: list(row.datasets),
  backbones: list(row.backbones),
  routingDensity: clean(row.routing_density),
  routingGranularity: list(row.routing_granularity),
  routingSignal: list(row.routing_signal),
  inputDependentRouting: bool(row.input_dependent_routing_audited),
  evidenceTier: clean(row.evidence_tier_audited),
  validationDesign: clean(row.validation_design),
  externalValidation: bool(row.external_evaluation_audited),
  multicentreEvaluation: bool(row.multicentre_evaluation_audited),
  prospectiveEvaluation: bool(row.prospective_evaluation_audited),
  fairnessAnalysis: bool(row.fairness_analysis),
  humanEvaluation: bool(row.clinician_or_human_evaluation),
  nonMoeComparator: bool(row.non_moe_comparator_audited),
  peerReviewed: bool(row.peer_reviewed),
  modelAccess: clean(row.model_access),
  reportingCompleteness: number(row.reporting_completeness_pct),
}));

const publicData = {
  title: "Mixture-of-Experts in Medical Foundation Models",
  description: "Public, study-level evidence map derived from a scoping review of medical foundation-model MoE systems.",
  version: "1.0.0",
  generated: new Date().toISOString().slice(0, 10),
  studyCount: studies.length,
  note: "Only bibliographic metadata and structured study characteristics are included. Abstracts, full-text evidence snippets, local workflow fields, and copyrighted source text are excluded.",
  studies,
};

fs.mkdirSync(path.dirname(outputArg), { recursive: true });
fs.writeFileSync(outputArg, `${JSON.stringify(publicData, null, 2)}\n`, "utf8");
console.log(`Wrote ${studies.length} studies to ${outputArg}`);
