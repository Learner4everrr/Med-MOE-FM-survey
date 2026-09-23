const state = {
  data: null,
  filtered: [],
  visible: 12,
};

const el = (id) => document.getElementById(id);

const cleanTier = (value) => value?.replace(/^Level\s*\d+\s*:\s*/i, "") || "Not reported";
const label = (value) => value || "Not reported";
const doiUrl = (doi) => doi ? `https://doi.org/${doi.replace(/^https?:\/\/(dx\.)?doi\.org\//i, "")}` : null;

function escapeHtml(value = "") {
  return String(value).replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  })[character]);
}

function unique(field) {
  return [...new Set(state.data.studies.map((study) => study[field]).filter(Boolean))]
    .sort((a, b) => String(a).localeCompare(String(b)));
}

function fillSelect(id, values) {
  const select = el(id);
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  });
}

function countBy(field) {
  return state.data.studies.reduce((counts, study) => {
    const value = study[field] || "Not reported";
    counts[value] = (counts[value] || 0) + 1;
    return counts;
  }, {});
}

function renderMetrics() {
  const studies = state.data.studies;
  const recent = studies.filter((study) => study.year >= 2025).length;
  el("metricStudies").textContent = studies.length;
  el("metricRecent").textContent = `${Math.round((recent / studies.length) * 100)}%`;
  el("metricRouting").textContent = studies.filter((study) => study.inputDependentRouting).length;
  el("metricExternal").textContent = studies.filter((study) => study.externalValidation).length;
  el("dataVersion").textContent = state.data.version;
  el("lastUpdated").textContent = state.data.generated;
}

function renderYearChart() {
  const counts = countBy("year");
  const years = Object.keys(counts).filter((year) => year !== "Not reported").sort();
  const maximum = Math.max(...years.map((year) => counts[year]));
  el("yearChart").innerHTML = years.map((year) => `
    <div class="year-bar" title="${counts[year]} studies in ${year}">
      <strong>${counts[year]}</strong>
      <i style="height:${Math.max(4, (counts[year] / maximum) * 180)}px"></i>
      <span>${year}</span>
    </div>
  `).join("");
}

function renderEvidenceChart() {
  const counts = countBy("evidenceTier");
  const colors = ["#5548d9", "#3d7edb", "#1f9d8b"];
  const rows = Object.entries(counts)
    .filter(([name]) => name !== "Not reported")
    .sort(([a], [b]) => a.localeCompare(b));
  const maximum = Math.max(...rows.map(([, count]) => count));
  el("evidenceChart").innerHTML = rows.map(([name, count], index) => `
    <div class="evidence-row">
      <div><span>${escapeHtml(cleanTier(name))}</span><strong>${count}</strong></div>
      <div class="evidence-track"><i style="width:${(count / maximum) * 100}%;background:${colors[index % colors.length]}"></i></div>
    </div>
  `).join("");
}

function renderApplicationChart() {
  const counts = countBy("application");
  const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const maximum = rows[0]?.[1] || 1;
  el("applicationChart").innerHTML = rows.map(([name, count]) => `
    <button class="application-row" type="button" data-application="${escapeHtml(name)}">
      <span class="application-label"><span>${escapeHtml(name)}</span><strong>${count}</strong></span>
      <span class="application-track"><i style="width:${(count / maximum) * 100}%"></i></span>
    </button>
  `).join("");
  document.querySelectorAll("[data-application]").forEach((button) => {
    button.addEventListener("click", () => {
      el("applicationFilter").value = button.dataset.application;
      applyFilters();
      el("studies").scrollIntoView({ behavior: "smooth" });
    });
  });
}

function studyCard(study) {
  const tags = [study.application, study.expertOrganization, study.moeFunction].filter(Boolean).slice(0, 3);
  const completeness = study.reportingCompleteness ?? 0;
  const doi = doiUrl(study.doi);
  return `
    <article class="study-card">
      <div class="card-top"><span class="study-id">${escapeHtml(study.id)}</span><span class="year-pill">${study.year || "Year NR"}</span></div>
      <h3>${escapeHtml(study.title || "Untitled study")}</h3>
      <p class="authors">${escapeHtml(study.authors.join(", ") || "Authors not reported")}</p>
      <div class="tags">
        ${tags.map((tag, index) => `<span class="tag ${index === 1 ? "teal" : index === 2 ? "blue" : ""}">${escapeHtml(tag)}</span>`).join("")}
      </div>
      <div class="card-details">
        <div><span>Routing</span><strong>${study.inputDependentRouting ? "Input-dependent" : "Author-defined / unclear"}</strong></div>
        <div><span>Evidence</span><strong>${escapeHtml(cleanTier(study.evidenceTier))}</strong></div>
        <div><span>Modality</span><strong>${escapeHtml(study.modalities[0] || "Not reported")}</strong></div>
        <div><span>Peer reviewed</span><strong>${study.peerReviewed ? "Yes" : "No / preprint"}</strong></div>
      </div>
      <div class="card-footer">
        <div class="completeness"><span>Reporting completeness ${completeness.toFixed(1)}%</span><div class="mini-track"><i style="width:${completeness}%"></i></div></div>
        ${doi ? `<a class="doi-link" href="${escapeHtml(doi)}" target="_blank" rel="noopener">DOI ↗</a>` : ""}
      </div>
    </article>
  `;
}

function renderStudies() {
  const visible = state.filtered.slice(0, state.visible);
  el("resultCount").textContent = state.filtered.length;
  el("studyGrid").innerHTML = visible.length
    ? visible.map(studyCard).join("")
    : '<div class="empty-state"><strong>No matching studies</strong><p>Try removing one or more filters.</p></div>';
  el("loadMore").hidden = state.visible >= state.filtered.length;
}

function applyFilters() {
  const query = el("searchInput").value.trim().toLowerCase();
  const application = el("applicationFilter").value;
  const expert = el("expertFilter").value;
  const functionValue = el("functionFilter").value;
  const evidence = el("evidenceFilter").value;
  const year = el("yearFilter").value;
  const routingOnly = el("routingFilter").checked;
  const externalOnly = el("externalFilter").checked;

  state.filtered = state.data.studies.filter((study) => {
    const haystack = [study.id, study.title, study.authors.join(" "), study.doi].filter(Boolean).join(" ").toLowerCase();
    return (!query || haystack.includes(query))
      && (!application || study.application === application)
      && (!expert || study.expertOrganization === expert)
      && (!functionValue || study.moeFunction === functionValue)
      && (!evidence || study.evidenceTier === evidence)
      && (!year || String(study.year) === year)
      && (!routingOnly || study.inputDependentRouting)
      && (!externalOnly || study.externalValidation);
  });
  state.visible = 12;
  renderStudies();
}

function resetFilters() {
  ["searchInput", "applicationFilter", "expertFilter", "functionFilter", "evidenceFilter", "yearFilter"]
    .forEach((id) => { el(id).value = ""; });
  el("routingFilter").checked = false;
  el("externalFilter").checked = false;
  applyFilters();
}

async function initialize() {
  try {
    const response = await fetch("./data/studies.json");
    if (!response.ok) throw new Error(`Data request failed: ${response.status}`);
    state.data = await response.json();
    state.filtered = [...state.data.studies];

    fillSelect("applicationFilter", unique("application"));
    fillSelect("expertFilter", unique("expertOrganization"));
    fillSelect("functionFilter", unique("moeFunction"));
    fillSelect("evidenceFilter", unique("evidenceTier"));
    fillSelect("yearFilter", unique("year").sort((a, b) => b - a));

    renderMetrics();
    renderYearChart();
    renderEvidenceChart();
    renderApplicationChart();
    renderStudies();

    ["searchInput", "applicationFilter", "expertFilter", "functionFilter", "evidenceFilter", "yearFilter", "routingFilter", "externalFilter"]
      .forEach((id) => el(id).addEventListener(id === "searchInput" ? "input" : "change", applyFilters));
    el("resetFilters").addEventListener("click", resetFilters);
    el("loadMore").addEventListener("click", () => { state.visible += 12; renderStudies(); });
  } catch (error) {
    console.error(error);
    el("studyGrid").innerHTML = '<div class="empty-state"><strong>Unable to load the evidence map.</strong><p>Please refresh the page or view the repository status.</p></div>';
  }
}

initialize();
