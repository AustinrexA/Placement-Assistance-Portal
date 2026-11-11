"use strict";

const API = {
  jobs: "/api/jobs",
  sources: "/api/sources",
  companies: "/api/companies",
  salaryOptions: "/api/salary-options",
  careerSources: "/api/company-career-sources",
  locations: "/api/locations",
  health: "/api/health",
  dashboard: "/api/dashboard/stats",
};
const state = {
  page: 1,
  perPage: 10,
  total: 0,
  totalPages: 1,
  jobs: [],
  sources: [],
  selectedSourceIds: new Set(),
  sourcesInitialized: false,
  selectedCompanyNames: new Set(),
  companies: [],
  careerSources: [],
  selectedCareerSourceIds: new Set(),
  roleOptions: [],
  experienceOptions: [],
  locations: [],
  filters: {
    role: "",
    location: "",
    experience: "",
    source_id: "",
    source_ids: "",
    company: "",
    skills: "",
    posted_after: "",
    status: "",
    salary_min: "",
    salary_max: "",
    salary_currency: "INR",
    salary_period: "",
  },
  sortBy: "id",
  sortDirection: "desc",
  excludedJobs: new Set(),
  activeSourceName: "All websites",
};

const elements = {
  companiesToggle: document.getElementById("companiesToggle"),
  companyOptions: document.getElementById("companyOptions"),
  jobsPage: document.getElementById("jobsPage"),
  dashboardPage: document.getElementById("dashboardPage"),
  salaryFilterInput: document.getElementById("salaryFilterInput"),
  reportsPage: document.getElementById("reportsPage"),
  pageTitle: document.getElementById("pageTitle"),
  filterForm: document.getElementById("filterForm"),
  searchInput: document.getElementById("searchInput"),
  locationInput: document.getElementById("locationInput"),
  locationDropdownToggle: document.getElementById("locationDropdownToggle"),
  locationOptions: document.getElementById("locationOptions"),
  experienceInput: document.getElementById("experienceInput"),
  companyInput: document.getElementById("companyInput"),
  skillsInput: document.getElementById("skillsInput"),
  postedDateInput: document.getElementById("postedDateInput"),
  statusFilter: document.getElementById("statusFilter"),
  moreFilters: document.getElementById("moreFilters"),
  moreFiltersToggle: document.getElementById("moreFiltersToggle"),
  jobsTableBody: document.getElementById("jobsTableBody"),
  resultCount: document.getElementById("resultCount"),
  sourceSummary: document.getElementById("sourceSummary"),
  paginationInfo: document.getElementById("paginationInfo"),
  currentPageLabel: document.getElementById("currentPageLabel"),
  pageSizeSelect: document.getElementById("pageSizeSelect"),
  selectAllJobs: document.getElementById("selectAllJobs"),
  notification: document.getElementById("notification"),
  sourceOptions: document.getElementById("sourceOptions"),
  selectAllPortals: document.getElementById("selectAllPortals"),
  selectAllCareerSites: document.getElementById("selectAllCareerSites"),
  sourceMenu: document.getElementById("sourceMenu"),
  jobPortalToggle: document.getElementById("jobPortalToggle"),
  sidebar: document.getElementById("sidebar"),
};

let notificationTimeout = null;
let jobsRequestSequence = 0;

function escapeHTML(value) {
  return String(value ?? "").replace(
    /[&<>"']/g,
    (character) =>
      ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      })[character],
  );
}

function displayValue(value, fallback = "—") {
  if (value === null || value === undefined || value === "") {
    return fallback;
  }
  return escapeHTML(value);
}

function showNotification(message, isError = false) {
  elements.notification.textContent = message;
  elements.notification.className = "notification show";

  if (isError) {
    elements.notification.classList.add("error");
  }

  if (notificationTimeout) {
    clearTimeout(notificationTimeout);
  }

  notificationTimeout = setTimeout(() => {
    elements.notification.className = "notification";
  }, 3500);
}

async function apiGet(url) {
    const response = await fetch(url, {
        method: "GET",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
    });

  let result;

  try {
    result = await response.json();
  } catch {
    throw new Error("The server returned an invalid response.");
  }

  if (!response.ok) {
    throw new Error(
      result.error || `Request failed with status ${response.status}.`,
    );
  }

  return result;
}

/* Build the jobs API URL. */
function buildJobsURL() {
  const params = new URLSearchParams();

  params.set("page", state.page);
  params.set("per_page", state.perPage);
  params.set("source_ids", getSelectedSourceIds().join(","));

  const selectedRole = (state.filters.role || "").trim();

  if (selectedRole) {
    params.set("role", selectedRole);
  }

  if (state.filters.location) {
    params.set("location", state.filters.location);
  }

  if (state.filters.company) {
    params.set("company", state.filters.company);
  }

  state.selectedCompanyNames.forEach((name) =>
    params.append("companies", name),
  );

  if (state.filters.experience)
    params.set("experience", state.filters.experience);
  [
    "skills",
    "posted_after",
    "status",
    "salary_min",
    "salary_max",
    "salary_currency",
    "salary_period",
  ].forEach((key) => {
    if (state.filters[key] !== undefined && state.filters[key] !== "")
      params.set(key, state.filters[key]);
  });

  return `${API.jobs}?${params.toString()}`;
}

function showLoading() {
  elements.jobsTableBody.innerHTML = `
        <tr>
            <td colspan="8" class="empty-state">
                <div class="loading-indicator"></div>
                <p>Loading job listings...</p>
            </td>
        </tr>
    `;
}

function showTableMessage(message) {
  elements.jobsTableBody.innerHTML = `
        <tr>
            <td colspan="8" class="empty-state">
                ${escapeHTML(message)}
            </td>
        </tr>
    `;
}

function normalizeSkills(skills) {
  if (Array.isArray(skills)) {
    return skills.map((skill) => String(skill).trim()).filter(Boolean);
  }

  if (typeof skills === "string" && skills.trim()) {
    try {
      const parsed = JSON.parse(skills);

      if (Array.isArray(parsed)) {
        return parsed.map((skill) => String(skill).trim()).filter(Boolean);
      }
    } catch {
      return skills
        .split(/[,;|]/)
        .map((skill) => skill.trim())
        .filter(Boolean);
    }
  }

  return [];
}

function formatDate(value) {
  if (!value) {
    return "—";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return String(value);
  }

  return parsed.toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function getStatus(job) {
  return String(job.status || "active").toLowerCase();
}

function renderSkills(skills) {
  const list = normalizeSkills(skills);

  if (!list.length) {
    return "—";
  }

  return `
        <div class="skills-list">
            ${list
              .slice(0, 5)
              .map(
                (skill) => `
                <span class="skill-tag">${escapeHTML(skill)}</span>
            `,
              )
              .join("")}
            ${
              list.length > 5
                ? `<span class="skill-tag">+${list.length - 5}</span>`
                : ""
            }
        </div>
    `;
}

function safeJobURL(value) {
  if (!value) {
    return null;
  }

  try {
    const url = new URL(value);

    if (url.protocol === "https:" || url.protocol === "http:") {
      return url.href;
    }
  } catch {
    return null;
  }

  return null;
}

function renderJobRow(job) {
  const id = Number(job.id);
  const checked = state.excludedJobs.has(id) ? "checked" : "";
  const jobURL = safeJobURL(job.job_url);
  const salaryText =
    job.salary_min != null || job.salary_max != null
      ? `${job.salary_currency || "INR"} ${job.salary_min != null ? Number(job.salary_min).toLocaleString("en-IN") : "—"}–${job.salary_max != null ? Number(job.salary_max).toLocaleString("en-IN") : "—"}${job.salary_period ? ` / ${escapeHTML(job.salary_period)}` : ""}`
      : "Not disclosed";
  const isUser = (document.body.dataset.userRole || "").toLowerCase() === "user";
  const openURL = isUser && Number.isSafeInteger(id) ? `/api/credits/open-job/${id}` : jobURL;
  const jobLink = jobURL && openURL
    ? `<a class="job-link" href="${escapeHTML(openURL)}" target="_blank" rel="noopener noreferrer">Open ↗</a>`
    : "—";
  return `
        <tr>
            <td class="checkbox-column"><input type="checkbox" class="job-checkbox" data-job-id="${Number.isSafeInteger(id) ? id : ""}" aria-label="Exclude job ${Number.isSafeInteger(id) ? id : ""} from export" ${checked}></td>
            <td class="job-title-cell" title="View job details: ${escapeHTML(job.title || "—")}"><button type="button" class="job-title-button" data-job-details-id="${Number.isSafeInteger(id) ? id : ""}" aria-label="View details for ${escapeHTML(job.title || "job")}">${displayValue(job.title)}</button></td>
            <td class="company-cell">${displayValue(job.company)}</td>
            <td class="location-cell">${displayValue(job.location)}</td>
            <td>${displayValue(job.experience)}</td>
            <td class="salary-cell">${escapeHTML(salaryText)}</td>
            <td>${escapeHTML(formatDate(job.posted_at))}</td>
            <td class="admin-job-link-column">${jobLink}</td>
        </tr>`;
}

function detailText(value, fallback = "Not provided") {
  const text = String(value == null ? "" : value).trim();
  return text ? escapeHTML(text) : fallback;
}

function cleanJobDetailText(value) {
  return String(value == null ? "" : value)
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&amp;/gi, "&")
    .replace(/&nbsp;/gi, " ")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/\s+/g, " ")
    .trim();
}

function extractJobKeyPoints(rawDescription, rawSkills) {
  const source = cleanJobDetailText(rawDescription);
  const skills = cleanJobDetailText(rawSkills);
  const combined = [
    source,
    skills && !source.toLowerCase().includes(skills.toLowerCase())
      ? `Key skills: ${skills}`
      : "",
  ]
    .filter(Boolean)
    .join(" ");
  if (!combined) return [];

  // Split dense scraped descriptions into readable points instead of reproducing
  // the source portal's full paragraph verbatim.
  const chunks = combined
    .replace(/\s*[•●▪►]\s*/g, "\n")
    .replace(
      /\s+(?=(?:Responsibilities|Requirements|Qualifications|What you.ll do|What you will do|Skills|Minimum qualification|Preferred qualification)\s*:)/gi,
      "\n",
    )
    .split(/\n+|(?<=[.!?])\s+(?=[A-Z0-9])|;\s+/)
    .map((part) => part.replace(/^[\s\-–—:|]+|[\s\-–—|]+$/g, "").trim())
    .filter((part) => part.length >= 12);

  const points = [];
  const seen = new Set();
  for (let chunk of chunks) {
    chunk = chunk.replace(/\s+/g, " ").trim();
    if (!chunk) continue;
    // If a source provides one very long run-on line, divide it into useful
    // phrase-sized points without dropping the remaining information.
    if (chunk.length > 220) {
      const phrases = chunk.split(/,\s+(?=[A-Z])/);
      if (phrases.length > 1) {
        chunk = phrases.join(". ");
      }
    }
    const key = chunk
      .toLowerCase()
      .replace(/[^\w]+/g, " ")
      .trim();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    points.push(chunk);
  }
  return points.slice(0, 12);
}

function showJobDetails(jobId) {
  const job = state.jobs.find((item) => Number(item.id) === Number(jobId));
  if (!job) return;
  const modal = document.getElementById("jobDetailsModal");
  const url = safeJobURL(job.job_url);
  const salary =
    job.salary_min != null || job.salary_max != null
      ? `${job.salary_currency || "INR"} ${job.salary_min != null ? Number(job.salary_min).toLocaleString("en-IN") : "—"} – ${job.salary_max != null ? Number(job.salary_max).toLocaleString("en-IN") : "—"}${job.salary_period ? ` / ${job.salary_period}` : ""}`
      : "Not disclosed";
  document.getElementById("jobDetailsTitle").textContent =
    job.title || "Job details";
  document.getElementById("jobDetailsCompany").textContent =
    job.company || "Company not specified";
  document.getElementById("jobDetailsMeta").innerHTML = `
        <div class="job-detail-fact"><span>Location</span><strong>${detailText(job.location)}</strong></div>
        <div class="job-detail-fact"><span>Experience</span><strong>${detailText(job.experience)}</strong></div>
        <div class="job-detail-fact"><span>Salary</span><strong>${escapeHTML(salary)}</strong></div>
        <div class="job-detail-fact"><span>Posted</span><strong>${escapeHTML(formatDate(job.posted_at))}</strong></div>
        <div class="job-detail-fact"><span>Source</span><strong>${detailText(job.source_name)}</strong></div>`;
  const points = extractJobKeyPoints(job.description, job.skills);
  const descriptionElement = document.getElementById("jobDetailsDescription");
  descriptionElement.innerHTML = points.length
    ? `<ul class="job-details-key-points">${points.map((point) => `<li>${escapeHTML(point)}</li>`).join("")}</ul>`
    : `<p class="job-details-empty-description">The source did not provide enough description details for a summary. Use the original listing for the full requirements.</p>`;
  const link = document.getElementById("jobDetailsApplyLink");
  const isUser = (document.body.dataset.userRole || "").toLowerCase() === "user";
  const sourceLink = isUser ? `/api/credits/open-job/${Number(job.id)}` : url;
  // User accounts use the in-app credits flow and should not see the
  // direct "Open original listing" button. Admins retain the original link.
  link.hidden = isUser || !url;
  if (!isUser && url) link.href = url;
  modal.dataset.activeJobId = String(job.id);
  modal.hidden = false;
  document.body.classList.add("job-details-open");
  document.getElementById("jobDetailsClose").focus();
}

function closeJobDetails() {
  const modal = document.getElementById("jobDetailsModal");
  if (modal) modal.hidden = true;
  document.body.classList.remove("job-details-open");
}

function exportJobDetails() {
  const modal = document.getElementById("jobDetailsModal");
  if (!modal || modal.hidden) return;
  window.print();
}

function renderJobs() {
  if (!state.jobs.length) {
    showTableMessage(
      state.selectedSourceIds.size === 0 &&
        state.selectedCareerSourceIds.size === 0
        ? "No job sources selected. Select a job portal or company to display jobs."
        : "No jobs found for the selected source. Try refreshing or changing your filters.",
    );

    elements.selectAllJobs.checked = false;
    elements.selectAllJobs.indeterminate = false;
    return;
  }

  elements.jobsTableBody.innerHTML = state.jobs.map(renderJobRow).join("");
  updateSelectionCheckbox();
}

function updatePagination() {
  const start = state.total === 0 ? 0 : (state.page - 1) * state.perPage + 1;

  const end = Math.min(state.page * state.perPage, state.total);

  elements.resultCount.textContent = state.total.toLocaleString("en-IN");

  elements.paginationInfo.textContent = `Showing ${start}–${end} of ${state.total.toLocaleString("en-IN")} records`;

  elements.currentPageLabel.textContent = `Page ${state.page} of ${state.totalPages}`;

  document.getElementById("firstPageButton").disabled = state.page <= 1;
  document.getElementById("previousPageButton").disabled = state.page <= 1;
  document.getElementById("nextPageButton").disabled =
    state.page >= state.totalPages;
  document.getElementById("lastPageButton").disabled =
    state.page >= state.totalPages;
}

function updateSelectionCheckbox() {
  const visibleIds = state.jobs
    .map((job) => Number(job.id))
    .filter((id) => Number.isSafeInteger(id));

  const selectedVisible = visibleIds.filter((id) =>
    state.excludedJobs.has(id),
  ).length;

  elements.selectAllJobs.checked =
    visibleIds.length > 0 && selectedVisible === visibleIds.length;

  elements.selectAllJobs.indeterminate =
    selectedVisible > 0 && selectedVisible < visibleIds.length;
}
async function loadJobs() {
  const requestSequence = ++jobsRequestSequence;

  if (
    state.selectedSourceIds.size === 0 &&
    state.selectedCareerSourceIds.size === 0
  ) {
    state.jobs = [];
    state.total = 0;
    state.totalPages = 1;
    state.page = 1;

    renderJobs();
    updatePagination();
    return;
  }

  showLoading();

  try {
    const result = await apiGet(buildJobsURL());

    // An older response must not replace results for a newer filter selection.
    if (requestSequence !== jobsRequestSequence) {
      return;
    }

    state.jobs = Array.isArray(result.data) ? result.data : [];

    const pagination = result.pagination || {};

    state.total = Number(pagination.total) || 0;
    state.totalPages = Math.max(1, Number(pagination.total_pages) || 1);

    if (state.page > state.totalPages) {
      state.page = state.totalPages;
      return loadJobs();
    }

    state.jobs.sort((a, b) => {
      const first = a[state.sortBy] ?? "";
      const second = b[state.sortBy] ?? "";

      const comparison = String(first).localeCompare(
        String(second),
        undefined,
        { numeric: true, sensitivity: "base" },
      );

      return state.sortDirection === "asc" ? comparison : -comparison;
    });

    renderJobs();
    updatePagination();
  } catch (error) {
    if (requestSequence !== jobsRequestSequence) {
      return;
    }

    console.error("Unable to load jobs:", error);

    showTableMessage(
      "Unable to load jobs. Check that Flask is running and the database is connected.",
    );

    showNotification(error.message, true);

    state.jobs = [];
    state.total = 0;
    state.totalPages = 1;

    updatePagination();
  }
}

async function loadSources() {
  try {
    const result = await apiGet(API.sources);
    const previouslySelectedNames = new Set(
      state.sources
        .filter((source) => state.selectedSourceIds.has(Number(source.id)))
        .map((source) => source.name),
    );
    // The backend already filters this endpoint to the configured portal catalog.
    // Keep the full catalog instead of maintaining a second hard-coded source list.
    // Sort portals by the number of jobs currently stored, highest first.
    // This puts the most productive sources at the top of the sidebar.
    state.sources = (Array.isArray(result.data) ? result.data : []).slice().sort((a, b) => {
      const countDifference = (Number(b.job_count) || 0) - (Number(a.job_count) || 0);
      if (countDifference !== 0) return countDifference;
      return String(a.name || "").localeCompare(String(b.name || ""), "en", { sensitivity: "base" });
    });
    if (!state.sourcesInitialized) {
      // User portal: enable every available source automatically.
      // Admin retains the original opt-in source selection behavior.
      const userRole = String(document.body.dataset.userRole || "").toLowerCase();
      state.selectedSourceIds = userRole === "user"
        ? new Set(state.sources.map((source) => Number(source.id)))
        : new Set();
      state.sourcesInitialized = true;
    } else {
      state.selectedSourceIds = new Set(
        state.sources
          .filter((source) => previouslySelectedNames.has(source.name))
          .map((source) => Number(source.id)),
      );
    }
    syncSourceFilter();
    renderSourceOptions();
  } catch (error) {
    console.error("Unable to load sources:", error);
    showNotification("Unable to load job websites.", true);
  }
}

function renderSourceOptions() {
  if (!elements.sourceOptions) return;

  // Always render the canonical API source list stored in state.sources.
  const sortedSources = [...state.sources].sort((a, b) => {
    const countDifference = (Number(b.job_count) || 0) - (Number(a.job_count) || 0);
    if (countDifference !== 0) return countDifference;
    return String(a.name || "").localeCompare(String(b.name || ""), "en", {
      sensitivity: "base",
    });
  });

  const renderSource = (source) => {
    const id = Number(source.id);
    const sourceIds = Array.isArray(source.source_ids) ? source.source_ids : [id];
    const idsAttr = sourceIds.map(Number).filter(Number.isFinite).join(",");
    const checked = state.selectedSourceIds.has(id) ? "checked" : "";

    return `
      <label class="source-checkbox-item" title="${escapeHTML(source.name)} job count">
        <input type="checkbox" data-source-id="${id}" data-source-ids="${idsAttr}" ${checked}>
        <span class="source-label">${escapeHTML(source.name)}</span>
        <span class="source-count">${(Number(source.job_count) || 0).toLocaleString("en-IN")}</span>
      </label>`;
  };

  const allSelected = sortedSources.filter((source) =>
    state.selectedSourceIds.has(Number(source.id))
  ).length;

  elements.sourceOptions.innerHTML =
    `<label class="source-checkbox-item source-select-all-item"><input type="checkbox" data-select-all-sources><span class="source-label">Select all</span></label>` +
    sortedSources.map(renderSource).join("");

  syncMasterCheckbox(
    elements.sourceOptions.querySelector("[data-select-all-sources]"),
    allSelected,
    sortedSources.length,
  );
}

function syncMasterCheckbox(node, selectedCount, totalCount) {
  if (!node) return;
  node.checked = totalCount > 0 && selectedCount === totalCount;
  node.indeterminate = selectedCount > 0 && selectedCount < totalCount;
}

function getSelectedSourceIds() {
  // Sidebar portal rows may represent multiple database source records
  // (for example, LinkedIn/LinkedIn Jobs or CutShort/Cutshort).
  // Expand canonical portal selections to every underlying source ID.
  const expandedPortalIds = [...state.selectedSourceIds].flatMap((selectedId) => {
    const portal = state.sources.find((source) => Number(source.id) === Number(selectedId));
    const ids = Array.isArray(portal?.source_ids) ? portal.source_ids : [selectedId];
    return ids.map(Number).filter(Number.isFinite);
  });

  return [
    ...new Set(
      [...expandedPortalIds, ...state.selectedCareerSourceIds]
        .map(Number)
        .filter(Number.isFinite),
    ),
  ];
}

function syncSourceFilter() {
  const selectedIds = getSelectedSourceIds();
  state.filters.source_ids = selectedIds.join(",");
  const selectedPortalNames = state.sources
    .filter((source) => state.selectedSourceIds.has(Number(source.id)))
    .map((source) => source.name);
  const selectedCompanyNames = state.careerSources
    .filter((source) => state.selectedCareerSourceIds.has(Number(source.id)))
    .map(
      (source) =>
        source.company || source.name.replace(/ Careers$| Jobs$/i, ""),
    );
  const selectedNames = [...selectedPortalNames, ...selectedCompanyNames];
  state.activeSourceName = selectedNames.length
    ? selectedNames.join(", ")
    : "No sources selected";
  if (elements.sourceSummary)
    elements.sourceSummary.textContent = state.activeSourceName;
}

/* Faceted role, location, and experience dropdowns are backed by current database filters. */
function buildFacetParams(exclude = "") {
  const params = new URLSearchParams();
  const salaryLabel = elements.salaryFilterInput ? elements.salaryFilterInput.value : "";
  const salaryBand = elements.salaryFilterInput?.dataset.salaryValue || salaryLabel;
  const salaryParts = salaryBand ? salaryBand.split("-") : [];
  const values = {
    role: elements.searchInput.value.trim(),
    location: elements.locationInput.value.trim(),
    experience: elements.experienceInput.value.trim(),
    company: elements.companyInput ? elements.companyInput.value.trim() : "",
    posted_after: elements.postedDateInput ? elements.postedDateInput.value : "",
    source_ids: getSelectedSourceIds().join(","),
    salary_min: salaryParts[0] || "",
    salary_max: salaryParts.length > 1 ? salaryParts[1] : "",
    salary_currency: "INR",
    salary_period: "year",
  };
  Object.entries(values).forEach(([key, value]) => {
    if (key === "source_ids") params.set(key, value);
    else if (key !== exclude && value !== "") params.set(key, value);
  });
  state.selectedCompanyNames.forEach((name) =>
    params.append("companies", name),
  );
  return params;
}

async function loadSalaryFilterOptions() {
  if (!elements.salaryFilterInput) return;
  const fixedBands = [
    { label: "Up to ₹3 LPA", value: "0-300000" },
    { label: "₹3–5 LPA", value: "300000-500000" },
    { label: "₹5–8 LPA", value: "500000-800000" },
    { label: "₹8–12 LPA", value: "800000-1200000" },
    { label: "₹12–20 LPA", value: "1200000-2000000" },
    { label: "₹20 LPA+", value: "2000000-" },
  ];
  state.salaryOptions = fixedBands;
  renderGenericOptions("salary", fixedBands.map(b => b.label), fixedBands.map(b => b.value));
  const selected = fixedBands.find(b => b.value === (elements.salaryFilterInput.dataset.salaryValue || ""));
  if (selected) elements.salaryFilterInput.value = selected.label;
}


const genericFilterMap = {
  role: { input: elements.searchInput, options: document.getElementById("roleFilterOptions"), toggle: document.getElementById("roleDropdownToggle") },
  company: { input: elements.companyInput, options: document.getElementById("companyFilterOptions"), toggle: document.getElementById("companyDropdownToggle") },
  experience: { input: elements.experienceInput, options: document.getElementById("experienceFilterOptions"), toggle: document.getElementById("experienceDropdownToggle") },
  salary: { input: elements.salaryFilterInput, options: document.getElementById("salaryFilterOptions"), toggle: document.getElementById("salaryDropdownToggle") },
};
function canonicalJobRole(title) {
  const t = String(title || "").toLowerCase().replace(/[._]/g, " ").replace(/\s+/g, " ").trim();
  if (!t) return "";
  if (/\b(data scientist|data science)\b/.test(t)) return "Data Scientist";
  if (/\b(data analyst|business analyst|business intelligence)\b/.test(t)) return "Data Analyst";
  if (/\b(full.?stack|full stack)\b/.test(t)) return "Full Stack Developer";
  if (/\b(front.?end|frontend)\b/.test(t)) return "Frontend Developer";
  if (/\b(back.?end|backend)\b/.test(t)) return "Backend Developer";
  if (/\b(java)\b/.test(t) && /\b(developer|engineer)\b/.test(t)) return "Java Developer";
  if (/\b(python)\b/.test(t) && /\b(developer|engineer)\b/.test(t)) return "Python Developer";
  if (/\b(dotnet|\.net|c sharp|c#)\b/.test(t) && /\b(developer|engineer)\b/.test(t)) return ".NET Developer";
  if (/\b(software developer|application developer|programmer)\b/.test(t)) return "Software Developer";
  if (/\bsoftware engineer\b/.test(t)) return "Software Engineer";
  if (/\b(qa|quality assurance|sdet|test engineer|tester)\b/.test(t)) return "QA / Test Engineer";
  if (/\b(devops|site reliability)\b/.test(t)) return "DevOps Engineer";
  if (/\b(cloud engineer|cloud developer)\b/.test(t)) return "Cloud Engineer";
  if (/\b(ui.?ux|ux designer|ui designer)\b/.test(t)) return "UI / UX Designer";
  if (/\b(technical support|support engineer|it support)\b/.test(t)) return "IT Support Engineer";
  if (/\b(intern|internship)\b/.test(t)) return "Intern";
  return String(title).trim();
}
function renderGenericOptions(type, values, rawValues = []) {
  const cfg = genericFilterMap[type]; if (!cfg) return;
  const query = cfg.input.value.trim().toLowerCase();
  const filtered = values.filter(v => !query || String(v).toLowerCase().includes(query));
  cfg.options.innerHTML = filtered.length ? filtered.map(v => {
    const idx = values.indexOf(v); const raw = rawValues[idx] || v;
    return `<button type="button" class="location-option generic-option" role="option" data-generic-value="${escapeHTML(v)}" data-generic-raw="${escapeHTML(raw)}">${escapeHTML(v)}</button>`;
  }).join("") : '<div class="location-options-message">No matching options</div>';
}
function openGenericOptions(type) {
  const cfg = genericFilterMap[type]; if (!cfg) return;
  const all = type === "role" ? state.roleOptions : type === "experience" ? state.experienceOptions : type === "company" ? state.companyOptions || [] : type === "salary" ? (state.salaryOptions || []).map(b => b.label) : [];
  renderGenericOptions(type, all);
  cfg.options.hidden = false; cfg.input.setAttribute("aria-expanded","true"); cfg.toggle.setAttribute("aria-expanded","true");
}
function closeGenericOptions(type) {
  const cfg=genericFilterMap[type]; if(!cfg)return;
  cfg.options.hidden=true; cfg.input.setAttribute("aria-expanded","false"); cfg.toggle.setAttribute("aria-expanded","false");
}

async function loadFilterOptions() {
  const previousRole = elements.searchInput.value;
  const previousExperience = elements.experienceInput.value;
  try {
    const result = await apiGet(
      `/api/filter-options?${buildFacetParams().toString()}`,
    );
    state.roleOptions = [...new Set((Array.isArray(result.roles) ? result.roles : [])
      .map(canonicalJobRole).filter(Boolean))].sort((a,b)=>a.localeCompare(b));
    state.experienceOptions = Array.isArray(result.experiences)
      ? result.experiences
      : [];
    // /api/filter-options already returns locations using the same dependent
    // filters as /api/locations. Reuse that result instead of issuing a second
    // database request on every initial load/filter change.
    state.locations = extractLocationOptions(
      Array.isArray(result.locations) ? result.locations : [],
    );
    renderLocationOptions();

    renderGenericOptions("role", state.roleOptions);
    // Keep the active role selection stable while dependent facets refresh.
    // The role list excludes its own facet, so it may temporarily omit a
    // selected role when other filters narrow the result set.
    elements.searchInput.value = previousRole ? canonicalJobRole(previousRole) : "";
    state.filters.role = elements.searchInput.value;

    renderGenericOptions("experience", state.experienceOptions);
    elements.experienceInput.value = state.experienceOptions.includes(
      previousExperience,
    )
      ? previousExperience
      : "";
    state.filters.experience = elements.experienceInput.value;
  } catch (error) {
    console.error("Unable to load filter options:", error);
    showNotification("Unable to update role and experience options.", true);
  }
}

/* Location facets: expose clean city/country choices, not full street addresses. */
function normalizeLocationName(value) {
  const raw = String(value || "").trim().toLowerCase();
  const compact = raw.replace(/\b(rural|urban|local|city|area)\b/g, "")
    .replace(/[.,]/g, " ").replace(/\s+/g, " ").trim();
  const rules = [
    [/\b(bengaluru|bangalore|devanahalli|doddaballapur|hoskote|nelamangala|ramanagara)\b/, "Bangalore"],
    [/\bahmedabad\b/, "Ahmedabad"], [/\bbhubaneswar\b/, "Bhubaneswar"],
    [/\b(chennai|madras)\b/, "Chennai"], [/\bcoimbatore\b/, "Coimbatore"],
    [/\b(delhi|new delhi|delhi ncr|delhi ncr)\b/, "Delhi"],
    [/\b(hyderabad|secunderabad)\b/, "Hyderabad"], [/\bindore\b/, "Indore"],
    [/\b(kochi|cochin|aluva|alwaye|ernakulam)\b/, "Kochi"],
    [/\b(kolkata|calcutta)\b/, "Kolkata"], [/\blucknow\b/, "Lucknow"],
    [/\bmadurai\b/, "Madurai"], [/\b(mangaluru|mangalore)\b/, "Mangaluru"],
    [/\b(mumbai|bombay)\b/, "Mumbai"], [/\b(mysuru|mysore)\b/, "Mysuru"],
    [/\bpune\b/, "Pune"], [/\b(thiruvananthapuram|trivandrum)\b/, "Trivandrum"],
    [/\b(tiruchirappalli|trichy)\b/, "Tiruchirappalli"],
  ];
  for (const [pattern, canonical] of rules) if (pattern.test(compact)) return canonical;
  return String(value || "").trim();
}

function extractLocationOptions(rawLocations) {
  const options = new Map();
  const countries = new Map([
    ["india", "India"],
    ["united states", "United States"],
    ["usa", "United States"],
    ["united kingdom", "United Kingdom"],
    ["uk", "United Kingdom"],
    ["canada", "Canada"],
    ["australia", "Australia"],
    ["germany", "Germany"],
    ["singapore", "Singapore"],
    ["uae", "United Arab Emirates"],
    ["united arab emirates", "United Arab Emirates"],
  ]);
  const states = new Set([
    "andhra pradesh",
    "arunachal pradesh",
    "assam",
    "bihar",
    "chhattisgarh",
    "goa",
    "gujarat",
    "haryana",
    "himachal pradesh",
    "jharkhand",
    "karnataka",
    "kerala",
    "madhya pradesh",
    "maharashtra",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "odisha",
    "punjab",
    "rajasthan",
    "sikkim",
    "tamil nadu",
    "telangana",
    "tripura",
    "uttar pradesh",
    "uttarakhand",
    "west bengal",
    "jammu and kashmir",
    "delhi nct",
  ]);
  const addressTerms =
    /\b(street|road|lane|floor|building|tower|plot|block|sector|phase|unit|avenue|highway|pincode|pin code|cross road)\b/i;
  const adminCodes =
    /^(IN|US|UK|KA|TN|MH|TS|AP|KL|GJ|DL|HR|UP|WB|OH|CA|NY|TX)$/i;

  for (const raw of rawLocations || []) {
    if (typeof raw !== "string" || !raw.trim()) continue;

    // Semicolons usually separate multiple job locations.
    const groups = raw.split(/[;|]/);
    for (const group of groups) {
      const parts = group
        .split(",")
        .map((part) => part.trim())
        .filter(Boolean);
      if (!parts.length) continue;

      // Country is an independent filter option (e.g. India).
      for (const part of parts) {
        const country = countries.get(part.toLowerCase());
        if (country) options.set(country.toLowerCase(), country);
      }

      // A single clean location such as "India" or "Chennai" is itself useful.
      if (parts.length === 1) {
        const only = parts[0];
        if (!addressTerms.test(only) && !/\d/.test(only)) {
          const normalized = normalizeLocationName(only.replace(/\\b(rural|urban)\\b/ig, "").trim());
          if (
            !states.has(normalized.toLowerCase()) &&
            !adminCodes.test(normalized)
          ) {
            options.set(normalizeLocationName(normalized).toLowerCase(), normalizeLocationName(normalized));
          }
        }
        continue;
      }

      // For address-like strings, take the first plausible city before state/country.
      // Examples: "CHENNAI, Tamil Nadu, India" and "IN, KA, Bengaluru".
      let city = "";
      for (const part of parts) {
        const lower = part.toLowerCase();
        if (countries.has(lower) || states.has(lower) || adminCodes.test(part))
          continue;
        if (addressTerms.test(part) || /\d/.test(part)) continue;
        if (/^[A-Z]{2,3}$/.test(part)) continue;
        city = normalizeLocationName(part.replace(/\\b(rural|urban)\\b/ig, "").trim());
        break;
      }

      if (city && city.length >= 2) options.set(normalizeLocationName(city).toLowerCase(), normalizeLocationName(city));
    }
  }

  // Preserve every city found in current job results; only merge known aliases.
  return [...new Set(options.values())].sort((a,b)=>a.localeCompare(b));
}

async function loadLocations() {
  try {
    // The endpoint excludes the location filter itself, while retaining source,
    // company, role and other active facets. This prevents a selected city from
    // hiding all other available city/country choices.
    const params = buildFacetParams("location");
    const result = await apiGet(`${API.locations}?${params.toString()}`);
    const rawLocations = Array.isArray(result.data) ? result.data : [];
    state.locations = extractLocationOptions(rawLocations);
    renderLocationOptions();
  } catch (error) {
    console.error("Unable to load locations:", error);
    state.locations = [];
    if (elements.locationOptions) {
      elements.locationOptions.innerHTML =
        '<div class="location-options-message">Unable to load locations. Check the server connection.</div>';
    }
  }
}

function renderLocationOptions() {
  if (!elements.locationInput || !elements.locationOptions) return;

  const currentText = elements.locationInput.value.trim();
  const query = currentText.toLowerCase();
  const selected = currentText
    .split(",")
    .map((value) => normalizeLocationName(value.trim()).toLowerCase())
    .filter(Boolean);

  const available = state.locations.filter((location) => {
    const normalized = normalizeLocationName(location).toLowerCase();
    // When input is a selected token, show other options on focus, and match
    // the typed token when the user is actively searching.
    return (
      !selected.includes(normalized) && (!query || normalized.includes(query))
    );
  });

  if (!available.length) {
    // Empty text means show all choices; do not leave a misleading message
    // just because a previously selected value is still in the input.
    elements.locationOptions.innerHTML = query
      ? '<div class="location-options-message">No matching locations found.</div>'
      : "";
    return;
  }

  elements.locationOptions.innerHTML = available
    .map(
      (location) => `
        <button type="button" class="location-option" role="option"
            data-location="${escapeHTML(location)}">${escapeHTML(location)}</button>
    `,
    )
    .join("");
}

async function loadCompanyOptions() {
  if (!elements.companyOptions) return;
  try {
    const result = await apiGet(API.careerSources);
    // Only show company collectors the backend has marked configured.
    state.careerSources = (Array.isArray(result.data) ? result.data : []).filter((source) => source.collector_configured === true);
    renderCompanySidebar();
    syncSourceFilter();
  } catch (error) {
    console.error("Unable to load company career sources:", error);
    elements.companyOptions.innerHTML =
      '<div class="location-options-message">Unable to load company career sources.</div>';
  }
}

async function loadCompanyFilterOptions() {
  if (!elements.companyInput) return;
  // Keep a committed selection separate from autocomplete text while facets refresh.
  const selected = String(state.filters.company || "").trim();
  const previous = selected || elements.companyInput.value.trim();
  try {
    const result = await apiGet(
      `${API.companies}?${buildFacetParams("company").toString()}`,
    );
    const companies = Array.isArray(result.data)
      ? result.data.map((item) => String(item.name || "").trim()).filter(Boolean)
      : [];
    state.companyOptions = [...new Set(companies)].sort((a, b) => a.localeCompare(b));
    renderGenericOptions("company", state.companyOptions);
    // Never erase an exact selection merely because the refreshed facet list
    // is temporarily different or filtered by another facet.
    const chosen = selected || (state.companyOptions.includes(previous) ? previous : "");
    elements.companyInput.value = chosen;
    state.filters.company = chosen;
  } catch (error) {
    console.error("Unable to load company filter options:", error);
    if (selected) {
      elements.companyInput.value = selected;
      state.filters.company = selected;
    }
  }
}
function openLocationOptions() {
  renderLocationOptions();

  elements.locationOptions.hidden = false;
  elements.locationInput.setAttribute("aria-expanded", "true");
  elements.locationDropdownToggle.setAttribute("aria-expanded", "true");
}

function closeLocationOptions() {
  elements.locationOptions.hidden = true;
  elements.locationInput.setAttribute("aria-expanded", "false");
  elements.locationDropdownToggle.setAttribute("aria-expanded", "false");
}
async function applyFilters() {
  state.filters.role = elements.searchInput.value.trim();
  state.filters.location = elements.locationInput.value.trim();
  state.filters.experience = elements.experienceInput.value.trim();
  state.filters.company = elements.companyInput.value.trim();
  state.filters.skills = elements.skillsInput.value.trim();
  state.filters.posted_after = elements.postedDateInput.value;
  state.filters.status = elements.statusFilter.value;
  const salaryLabel = elements.salaryFilterInput ? elements.salaryFilterInput.value : "";
  const salaryBand = elements.salaryFilterInput?.dataset.salaryValue || salaryLabel;
  const salaryParts = salaryBand ? salaryBand.split("-") : [];
  state.filters.salary_min = salaryParts[0] || "";
  state.filters.salary_max = salaryParts.length > 1 ? salaryParts[1] : "";
  state.filters.salary_currency = "INR";
  state.filters.salary_period = "year";

  syncSourceFilter();
  renderSourceOptions();

  state.page = 1;
  state.excludedJobs.clear();

  closeLocationOptions();
  await loadJobs();
}

function clearFilters() {
  elements.filterForm.reset();
  if (elements.salaryFilterInput) elements.salaryFilterInput.value = "";
  closeLocationOptions();

  state.filters = {
    role: "",
    location: "",
    experience: "",
    source_id: "",
    source_ids: getSelectedSourceIds().join(","),
    company: "",
    skills: "",
    posted_after: "",
    status: "",
    salary_min: "",
    salary_max: "",
    salary_currency: "INR",
    salary_period: "",
  };
  state.selectedCompanyNames.clear();
  state.page = 1;
  state.excludedJobs.clear();
  state.sortBy = "id";
  state.sortDirection = "desc";

  syncSourceFilter();

  Promise.all([
    loadFilterOptions(),
    loadCompanyFilterOptions(),
    loadSalaryFilterOptions(),
  ]).then(() => loadJobs());
}

function setPage(page) {
  if (page < 1 || page > state.totalPages || page === state.page) {
    return;
  }

  state.page = page;
  loadJobs();
}
function renderCompanySidebar() {
  if (!elements.companyOptions) return;
  const matchingSources = state.careerSources || [];
  // Use the catalog's canonical company field so all 25 scoped companies can
  // appear without maintaining a second hard-coded whitelist in the frontend.
  const byCompany = new Map();
  for (const source of matchingSources) {
    const rawLabel = String(source.company || source.name || "")
      .replace(/ Careers$| Jobs$| India Careers$/i, "")
      .trim();
    if (!rawLabel) continue;
    const normalizedSource = { ...source, company: rawLabel };
    const key = rawLabel.toLowerCase();
    const existing = byCompany.get(key);
    if (
      !existing ||
      (Number(source.job_count) || 0) > (Number(existing.job_count) || 0)
    ) {
      byCompany.set(key, normalizedSource);
    }
  }
  // Keep only companies currently approved for display in the Companies UI.
  // These entries were requested to be hidden because they are not configured
  // for reliable collection in this project version.
  const hiddenCompanies = new Set(["accenture", "hcltech", "wipro"]);
  const sources = [...byCompany.values()]
    .filter((source) => !hiddenCompanies.has(String(source.company || source.name || "").trim().toLowerCase()))
    .sort((a, b) => {
      const countDifference = (Number(b.job_count) || 0) - (Number(a.job_count) || 0);
      if (countDifference !== 0) return countDifference;
      return String(a.company || a.name).localeCompare(String(b.company || b.name), "en", { sensitivity: "base" });
    });
  state.visibleCareerSources = sources;
  elements.companyOptions.innerHTML =
    `<label class="source-checkbox-item source-select-all-item"><input type="checkbox" data-select-all-companies><span class="source-label">Select all companies</span></label>` +
    (sources
      .map((source) => {
        const id = Number(source.id);
        const checked = state.selectedCareerSourceIds.has(id) ? "checked" : "";
        const count = (Number(source.job_count) || 0).toLocaleString("en-IN");
        const label = String(source.company || source.name || "").replace(
          / Careers$| Jobs$| India Careers$/i,
          "",
        );
        return `<label class="source-checkbox-item company-checkbox-item" title="${escapeHTML(label)} job count">
            <input type="checkbox" data-career-source-id="${id}" ${checked}>
            <span class="source-label">${escapeHTML(label)}</span>
            <span class="source-count">${count}</span>
        </label>`;
      })
      .join("") ||
      '<div class="location-options-message">No company career sources are available.</div>');
  const master = elements.companyOptions.querySelector(
    "[data-select-all-companies]",
  );
  syncMasterCheckbox(
    master,
    state.selectedCareerSourceIds.size,
    sources.length,
  );
}

async function loadCreditsAdminInline() {
  const host = document.getElementById("creditsAdminContent");
  if (!host || host.dataset.loaded === "1") return;
  const response = await fetch("/credits?partial=1");
  if (!response.ok) { host.textContent = "Unable to load credit management."; return; }
  host.innerHTML = await response.text();
  host.dataset.loaded = "1";
  // Execute inline scripts included in the partial template.
  host.querySelectorAll("script").forEach(old => { const s=document.createElement("script"); s.textContent=old.textContent; old.replaceWith(s); });
}
/* Page navigation: Companies is a filter group, not a separate career page. */
function showPage(pageName) {
  const dashboard = pageName === "dashboard";
  const reports = pageName === "reports";
  const credits = pageName === "credits";
  const userRole = document.body.dataset.userRole || "admin";
  const userDashboard = dashboard && userRole === "user";
  if (elements.dashboardPage)
    elements.dashboardPage.hidden = !dashboard || userDashboard;
  const userDashboardPage = document.getElementById("userDashboardPage");
  if (userDashboardPage) userDashboardPage.hidden = !userDashboard;
  elements.jobsPage.hidden = dashboard || reports || credits;
  if (elements.reportsPage) elements.reportsPage.hidden = !reports;
  const creditsPage = document.getElementById("creditsPage"); if (creditsPage) creditsPage.hidden = !credits;
  elements.pageTitle.textContent = dashboard
    ? "Dashboard"
    : reports
      ? "Reports"
      : credits ? "Credits & Subscription" : "Job Opportunities";
  document
    .querySelectorAll(".sidebar-nav > .nav-item[data-page]")
    .forEach((item) =>
      item.classList.toggle("active", item.dataset.page === pageName),
    );
  // Dropdown expansion and current-page highlighting are separate states.
  // Dashboard/Reports must clear both dropdown headings' active classes even
  // when a menu remains expanded to show its checkbox list.
  const onJobsPage = pageName === "jobs";
  const companiesExpanded =
    elements.companiesToggle?.getAttribute("aria-expanded") === "true";
  if (elements.jobPortalToggle) {
    elements.jobPortalToggle.classList.toggle(
      "active",
      onJobsPage && !companiesExpanded,
    );
  }
  if (elements.companiesToggle) {
    elements.companiesToggle.classList.toggle(
      "active",
      onJobsPage && companiesExpanded,
    );
  }
  const breadcrumb = document.querySelector(".breadcrumb");
  if (breadcrumb) breadcrumb.textContent = "";
  if (credits) loadCreditsAdmin();
  if (dashboard && userDashboard) loadUserDashboard();
  else if (dashboard) loadDashboard();
  if (reports) {
    if (!detailedReportState.loaded) {
      detailedReportState.loaded = true;
      Promise.all([loadReportOverview(), loadDetailedJobsReport()]);
    } else {
      loadDetailedJobsReport();
    }
  }
}

async function loadUserDashboard() {
  const render = (id, rows, empty) => {
    const node = document.getElementById(id);
    if (!node) return;
    node.innerHTML =
      rows && rows.length
        ? rows
            .map(
              (item) =>
                `<div class="user-insight-row"><span>${escapeHTML(item.label || "—")}</span><strong>${formatMetric(item.total)}</strong></div>`,
            )
            .join("")
        : `<p class="empty-state">${empty}</p>`;
  };
  try {
    const data = await apiGet("/api/user-dashboard");
    document.getElementById("userMetricJobs").textContent = formatMetric(
      data.active_jobs,
    );
    document.getElementById("userMetricRecentJobs").textContent = formatMetric(
      data.jobs_last_24h,
    );
    document.getElementById("userMetricRecentCompanies").textContent =
      formatMetric(data.companies_last_24h);
    document.getElementById("userMetricRecentLocations").textContent =
      formatMetric(data.locations_last_24h);
    render(
      "userLocations",
      data.locations,
      "No locations have new job records in the last 24 hours.",
    );
    render(
      "userCompanies",
      data.companies,
      "No companies have new job records in the last 24 hours.",
    );
    render(
      "userRoles",
      data.roles,
      "No roles have new job records in the last 24 hours.",
    );
    const recentBody = document.getElementById("userRecentJobsBody");
    if (recentBody)
      recentBody.innerHTML =
        data.recent_jobs && data.recent_jobs.length
          ? data.recent_jobs
              .map(
                (job) =>
                  `<tr><td>${escapeHTML(job.title || "—")}</td><td>${escapeHTML(job.company || "—")}</td><td>${escapeHTML(job.location || "—")}</td><td>${escapeHTML(formatTimestamp(job.created_at))}</td></tr>`,
              )
              .join("")
          : '<tr><td colspan="4" class="empty-state">No jobs were added in the last 24 hours.</td></tr>';
  } catch (error) {
    [
      "userLocations",
      "userCompanies",
      "userRoles",
      "userRecentJobsBody",
    ].forEach((id) => {
      const node = document.getElementById(id);
      if (node) node.textContent = "Unable to load insights.";
    });
  }
}

function formatMetric(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString("en-IN") : "0";
}
function formatTimestamp(value) {
  if (!value) return "Never";
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime())
    ? String(value)
    : parsed.toLocaleString("en-IN", {
        dateStyle: "medium",
        timeStyle: "short",
      });
}
function renderJobsTrend(series) {
  const chart = document.getElementById("jobsTrendChart");
  if (!chart) return;
  if (!series.length) {
    chart.innerHTML = '<p class="empty-state">No trend data available.</p>';
    return;
  }
  const max = Math.max(1, ...series.map((item) => Number(item.count) || 0));
  chart.innerHTML = `<div class="trend-bars">${series
    .map((item) => {
      const count = Math.max(0, Number(item.count) || 0);
      const height = Math.max(count ? 5 : 2, Math.round((count / max) * 100));
      const date = new Date(`${item.date}T12:00:00`);
      const label = date.toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
      });
      return `<div class="trend-day" title="${escapeHTML(label)}: ${count} jobs"><div class="trend-bar-track"><span class="trend-bar" style="height:${height}%"></span></div><strong>${count}</strong><small>${escapeHTML(label)}</small></div>`;
    })
    .join("")}</div>`;
}

async function loadLoginAudit() {
  const body = document.getElementById("loginAuditBody");
  if (!body) return;
  try {
    const result = await apiGet("/api/login-audit?limit=10");
    const rows = Array.isArray(result.data) ? result.data : [];
    body.innerHTML = rows.length ? rows.map((r) => {
      const role = String(r.role || "unknown");
      const status = String(r.status || "unknown");
      return `<tr><td>${escapeHTML(r.email || r.username || "—")}</td><td>${escapeHTML(role)}</td><td>${escapeHTML(r.event || "login")}</td><td>${escapeHTML(status)}</td><td>${escapeHTML(r.ip_address || "—")}</td><td>${escapeHTML(r.location || "Unknown")}</td><td>${escapeHTML(formatTimestamp(r.timestamp))}</td></tr>`;
    }).join("") : '<tr><td colspan="7" class="empty-state">No authentication activity recorded.</td></tr>';
  } catch (error) {
    console.error("Unable to load login audit:", error);
    body.innerHTML = '<tr><td colspan="7" class="empty-state">Login audit unavailable (Admin access required).</td></tr>';
  }
}

async function loadDashboard() {
  const runsBody = document.getElementById("dashboardRunsBody");
  // Load metrics and chart independently: a failure in one endpoint must not leave
  // the other dashboard panels stuck on their initial Loading placeholders.
  try {
    const result = await apiGet(API.dashboard);
    const m = result.metrics || {};
    const map = {
      metricJobsToday: m.jobs_added_today,
      metricTotalJobs: m.total_jobs,
      metricEnabledSources: m.enabled_sources,
      metricFailedToday: m.failed_runs_today,
    };
    Object.entries(map).forEach(([id, value]) => {
      const node = document.getElementById(id);
      if (node) node.textContent = formatMetric(value);
    });
    const runs = Array.isArray(result.recent_runs) ? result.recent_runs : [];
    if (runsBody) runsBody.innerHTML = runs.length
      ? runs.map((run) =>
          `<tr><td>${escapeHTML(run.source_name || "Unknown")}</td><td>${escapeHTML(formatTimestamp(run.started_at))}</td><td>${escapeHTML(run.status || "unknown")}</td><td>${formatMetric(run.records_found)}</td><td>${formatMetric(run.records_inserted)}</td></tr>`
        ).join("")
      : '<tr><td colspan="5" class="empty-state">No collection runs recorded yet.</td></tr>';
  } catch (error) {
    console.error("Unable to load dashboard metrics:", error);
    ["metricJobsToday","metricTotalJobs","metricEnabledSources","metricFailedToday"].forEach((id) => {
      const node = document.getElementById(id); if (node) node.textContent = "—";
    });
    if (runsBody) runsBody.innerHTML = '<tr><td colspan="5" class="empty-state">Collection activity could not load. Check /api/dashboard/stats.</td></tr>';
    showNotification("Dashboard metrics failed to load. Check Flask console for /api/dashboard/stats.", true);
  }
  try {
    const trendResult = await apiGet("/api/dashboard/trend");
    renderJobsTrend(Array.isArray(trendResult.data) ? trendResult.data : []);
  } catch (error) {
    console.error("Unable to load dashboard trend:", error);
    const chart = document.getElementById("jobsTrendChart");
    if (chart) chart.innerHTML = '<p class="empty-state">Chart could not load. Check /api/dashboard/trend.</p>';
  }
  await loadLoginAudit();
  await loadAdminAnalytics();
}

/* Professional, database-backed scraper report. */
const detailedReportState = {
  page: 1,
  perPage: 20,
  totalPages: 1,
  filtersApplied: false,
};

function reportFilterValues() {
  return {
    keyword: document.getElementById("reportKeyword")?.value.trim() || "",
    source_id: document.getElementById("reportSource")?.value.trim() || "",
    company: document.getElementById("reportCompany")?.value.trim() || "",
    location: document.getElementById("reportLocation")?.value.trim() || "",
    posted_from: document.getElementById("reportPostedFrom")?.value || "",
    posted_to: document.getElementById("reportPostedTo")?.value || "",
  };
}

function reportQueryParams(forExport = false) {
  const filters = reportFilterValues();
  const params = new URLSearchParams();
  if (forExport) {
    if (filters.keyword) params.set("search", filters.keyword);
    if (filters.source_id) params.set("source_id", filters.source_id);
    if (filters.company) params.set("company", filters.company);
    if (filters.location) params.set("location", filters.location);
    if (filters.posted_from) params.set("posted_after", filters.posted_from);
    if (filters.posted_to) params.set("posted_before", filters.posted_to);
  } else {
    if (filters.keyword) params.set("keyword", filters.keyword);
    if (filters.source_id) params.set("source_id", filters.source_id);
    if (filters.company) params.set("company", filters.company);
    if (filters.location) params.set("location", filters.location);
    if (filters.posted_from) params.set("posted_from", filters.posted_from);
    if (filters.posted_to) params.set("posted_to", filters.posted_to);
    params.set("page", String(detailedReportState.page));
    params.set("per_page", String(detailedReportState.perPage));
    params.set(
      "sort",
      document.getElementById("reportSort")?.value || "posted_date_desc",
    );
  }
  return params;
}

async function loadDetailedJobsReport() {
  const body = document.getElementById("reportTableBody");
  const summary = document.getElementById("reportResultSummary");
  const pageSummary = document.getElementById("reportPageSummary");
  if (!body) return;
  const params = reportQueryParams(false);
  body.innerHTML =
    '<tr><td colspan="9" class="empty-state">Loading report…</td></tr>';
  try {
    const result = await apiGet(`/api/reports/jobs?${params.toString()}`);
    const jobs = Array.isArray(result.data) ? result.data : [];
    const pagination = result.pagination || {};
    detailedReportState.totalPages = Math.max(
      1,
      Number(pagination.total_pages) || 1,
    );
    if (summary)
      summary.textContent = `${Number(pagination.total || 0).toLocaleString("en-IN")} matching jobs`;
    if (pageSummary)
      pageSummary.textContent = `Page ${pagination.page || 1} of ${detailedReportState.totalPages}`;
    const previous = document.getElementById("reportPreviousPage");
    const next = document.getElementById("reportNextPage");
    if (previous) previous.disabled = detailedReportState.page <= 1;
    if (next)
      next.disabled =
        detailedReportState.page >= detailedReportState.totalPages;
    body.innerHTML = jobs.length
      ? jobs
          .map((job, index) => {
            const salary =
              job.salary_min != null || job.salary_max != null
                ? `${job.salary_min ?? "—"} – ${job.salary_max ?? "—"} ${job.salary_currency || ""} ${job.salary_period || ""}`.trim()
                : "—";
            return `<tr>
                <td>${(detailedReportState.page - 1) * detailedReportState.perPage + index + 1}</td>
                <td>${escapeHTML(job.title || "—")}</td><td>${escapeHTML(job.company || "—")}</td>
                <td>${escapeHTML(job.location || "—")}</td><td>${escapeHTML(job.experience || "—")}</td>
                <td>${escapeHTML(salary)}</td><td><span class="report-source-pill">${escapeHTML(job.source_name || "—")}</span></td>
                <td>${escapeHTML(job.posted_at || "—")}</td>
                <td>${job.job_url && /^https?:\/\//i.test(job.job_url) ? `<a class="table-action report-open-link" href="${escapeHTML(job.job_url)}" target="_blank" rel="noopener noreferrer">Open</a>` : "—"}</td>
            </tr>`;
          })
          .join("")
      : '<tr><td colspan="9" class="empty-state">No jobs match these filters.</td></tr>';
  } catch (error) {
    console.error("Unable to load detailed Jobs report:", error);
    body.innerHTML =
      '<tr><td colspan="9" class="empty-state">Unable to load report. Check the Flask server and database connection.</td></tr>';
    if (summary) summary.textContent = "Report unavailable";
    showNotification("Unable to load the Jobs report.", true);
  }
}

async function loadReportOverview() {
  try {
    const [dashboard, portalResult, runResult] = await Promise.all([
      apiGet(API.dashboard),
      apiGet(API.sources),
      apiGet("/api/collection-runs?limit=8"),
    ]);
    const metrics = dashboard.metrics || {};
    // The API returns only configured portals; keep report options in sync with the sidebar.
    const visiblePortals = Array.isArray(portalResult.data) ? portalResult.data : [];
    const sourceCount = visiblePortals.length;
    const metricValues = {
      reportMetricTotalJobs: metrics.total_jobs,
      reportMetricAddedToday: metrics.jobs_added_today,
      reportMetricSources: sourceCount,
      reportMetricFailures: metrics.failed_runs_today,
    };
    Object.entries(metricValues).forEach(([id, value]) => {
      const node = document.getElementById(id);
      if (node) node.textContent = formatMetric(value);
    });
    const sourceSelect = document.getElementById("reportSource");
    if (sourceSelect) {
      const current = sourceSelect.value;
      const sources = visiblePortals
        .filter((source) => source && source.id != null)
        .sort((a, b) => String(a.name).localeCompare(String(b.name)));
      sourceSelect.innerHTML =
        '<option value="">All sources</option>' +
        sources
          .map(
            (source) =>
              `<option value="${Number(source.id)}">${escapeHTML(source.name)}</option>`,
          )
          .join("");
      if (sources.some((source) => String(source.id) === current))
        sourceSelect.value = current;
    }
    const runs = Array.isArray(runResult.data) ? runResult.data : [];
    const activityBody = document.getElementById("reportActivityBody");
    if (activityBody)
      activityBody.innerHTML = runs.length
        ? runs
            .map((run) => {
              const status = String(run.status || "unknown").toLowerCase();
              const message = run.error_message
                ? String(run.error_message)
                : "—";
              return `<tr><td>${escapeHTML(run.source_name || "Unknown")}</td><td>${escapeHTML(formatTimestamp(run.started_at))}</td><td><span class="run-status run-status-${escapeHTML(status.replace(/[^a-z0-9_-]/g, ""))}">${escapeHTML(run.status || "Unknown")}</span></td><td>${formatMetric(run.records_found)}</td><td>${formatMetric(run.records_inserted)}</td><td>${formatMetric(run.records_updated)}</td><td class="report-error-cell" title="${escapeHTML(message)}">${escapeHTML(message)}</td></tr>`;
            })
            .join("")
        : '<tr><td colspan="7" class="empty-state">No collection runs have been recorded yet.</td></tr>';
  } catch (error) {
    console.error("Unable to load report overview:", error);
    showNotification("Some report summary data could not be loaded.", true);
  }
}

async function downloadReport(format) {
  try {
    const params = reportQueryParams(true);
    params.set("format", format);
    const response = await fetch(`/api/jobs/export?${params.toString()}`);
    if (!response.ok) {
      let message = "Unable to export this report.";
      try {
        message = (await response.json()).error || message;
      } catch {
        /* use fallback */
      }
      throw new Error(message);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download =
      format === "csv"
        ? "v4career_scraper_report.csv"
        : "v4career_scraper_report.xlsx";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    showNotification(`${format.toUpperCase()} report downloaded.`);
  } catch (error) {
    showNotification(error.message || "Report export failed.", true);
  }
}

function initializeDetailedJobsReport() {
  const apply = document.getElementById("applyReportFilters");
  const reset = document.getElementById("resetReportFilters");
  const pageSize = document.getElementById("reportPageSize");
  const sort = document.getElementById("reportSort");
  const previous = document.getElementById("reportPreviousPage");
  const next = document.getElementById("reportNextPage");
  const refresh = document.getElementById("refreshReportsButton");
  if (apply && !apply.dataset.bound)
    apply.addEventListener("click", () => {
      detailedReportState.page = 1;
      detailedReportState.filtersApplied = true;
      loadDetailedJobsReport();
    });
  if (reset && !reset.dataset.bound)
    reset.addEventListener("click", () => {
      document
        .querySelectorAll("#reportFilters input, #reportFilters select")
        .forEach((node) => {
          node.value = "";
        });
      if (sort) sort.value = "posted_date_desc";
      detailedReportState.page = 1;
      detailedReportState.filtersApplied = false;
      loadDetailedJobsReport();
    });
  if (pageSize && !pageSize.dataset.bound)
    pageSize.addEventListener("change", () => {
      detailedReportState.perPage = Number(pageSize.value) || 20;
      detailedReportState.page = 1;
      loadDetailedJobsReport();
    });
  if (sort && !sort.dataset.bound)
    sort.addEventListener("change", () => {
      detailedReportState.page = 1;
      loadDetailedJobsReport();
    });
  if (previous && !previous.dataset.bound)
    previous.addEventListener("click", () => {
      if (detailedReportState.page > 1) {
        detailedReportState.page--;
        loadDetailedJobsReport();
      }
    });
  if (next && !next.dataset.bound)
    next.addEventListener("click", () => {
      if (detailedReportState.page < detailedReportState.totalPages) {
        detailedReportState.page++;
        loadDetailedJobsReport();
      }
    });
  if (refresh && !refresh.dataset.bound)
    refresh.addEventListener("click", async () => {
      await Promise.all([loadReportOverview(), loadDetailedJobsReport()]);
    });
  const excel = document.getElementById("reportExcelButton");
  const csv = document.getElementById("reportCsvButton");
  if (excel && !excel.dataset.bound)
    excel.addEventListener("click", () => downloadReport("xlsx"));
  if (csv && !csv.dataset.bound)
    csv.addEventListener("click", () => downloadReport("csv"));
}

document.addEventListener("DOMContentLoaded", initializeDetailedJobsReport, {
  once: true,
});

/* Table sorting. */
function sortJobs(key) {
  if (state.sortBy === key) {
    state.sortDirection = state.sortDirection === "asc" ? "desc" : "asc";
  } else {
    state.sortBy = key;
    state.sortDirection = key === "id" ? "desc" : "asc";
  }

  state.jobs.sort((a, b) => {
    const first = a[state.sortBy] ?? "";
    const second = b[state.sortBy] ?? "";

    const comparison = String(first).localeCompare(String(second), undefined, {
      numeric: true,
      sensitivity: "base",
    });

    return state.sortDirection === "asc" ? comparison : -comparison;
  });

  renderJobs();
}

/* Checked rows are excluded from the Excel export. */
function handleJobSelection(event) {
  const checkbox = event.target.closest(".job-checkbox");

  if (!checkbox) return;

  const id = Number(checkbox.dataset.jobId);

  if (!Number.isSafeInteger(id)) return;

  if (checkbox.checked) {
    state.excludedJobs.add(id);
  } else {
    state.excludedJobs.delete(id);
  }

  updateSelectionCheckbox();
}

function selectVisibleJobs(checked) {
  state.jobs.forEach((job) => {
    const id = Number(job.id);

    if (!Number.isSafeInteger(id)) return;

    if (checked) {
      state.excludedJobs.add(id);
    } else {
      state.excludedJobs.delete(id);
    }
  });

  renderJobs();
}
/* Excel export */
async function exportJobs() {
  try {
    const params = new URLSearchParams();

    const selectedSourceIds = getSelectedSourceIds();
    if (selectedSourceIds.length) {
      params.set("source_ids", selectedSourceIds.join(","));
    }
    state.selectedCompanyNames.forEach((name) =>
      params.append("companies", name),
    );

    for (const [key, value] of Object.entries(state.filters)) {
      if (value !== "" && key !== "source_ids") {
        params.set(key, value);
      }
    }

    if (state.excludedJobs.size) {
      params.set("exclude_job_ids", [...state.excludedJobs].join(","));
    }

    const response = await fetch(`/api/jobs/export?${params.toString()}`);

    if (!response.ok) {
      let message = "Unable to export job listings.";

      try {
        const result = await response.json();
        message = result.error || message;
      } catch {
        // Keep the default error message.
      }

      throw new Error(message);
    }

    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = downloadUrl;
    link.download = "v4career_job_listings.xlsx";

    document.body.appendChild(link);
    link.click();
    link.remove();

    URL.revokeObjectURL(downloadUrl);

    showNotification("Excel file downloaded successfully.");
  } catch (error) {
    console.error("Excel export failed:", error);
    showNotification(error.message, true);
  }
}

/* Logout and health check */
async function logout() {
  try {
    await fetch("/logout", { method: "POST" });
  } finally {
    window.location.href = "/login";
  }
}

function checkHealth() {
  fetch(API.health)
    .then((response) => {
      if (!response.ok) {
        throw new Error("Health check failed");
      }

      return response.json();
    })
    .then((result) => {
      if (result.status !== "healthy") {
        showNotification("Database connection is unavailable.", true);
      }
    })
    .catch(() => {
      showNotification("Cannot reach the Flask server.", true);
    });
}

/* Form submission */
elements.filterForm.addEventListener("submit", (event) => {
  event.preventDefault();
  applyFilters();
});

/* Scraper website checkbox selection */
elements.sourceOptions.addEventListener("change", async (event) => {
  const checkbox = event.target.closest("input[data-source-id]");

  if (!checkbox) return;

  const id = Number(checkbox.dataset.sourceId);

  if (checkbox.checked) {
    state.selectedSourceIds.add(id);
  } else {
    state.selectedSourceIds.delete(id);
  }

  syncSourceFilter();

  state.page = 1;
  state.excludedJobs.clear();

  // Keep experience if it exists in the newly selected portal set.
  // Fetch the new job result set first. Then refresh facets against the
  // committed filter state; avoid racing several option requests against jobs.
  await loadJobs();
  await Promise.all([
    loadFilterOptions(),
    loadCompanyFilterOptions(),
    loadSalaryFilterOptions(),
  ]);
});


/* Consistent searchable dropdown controls styled exactly like Location */
Object.entries(genericFilterMap).forEach(([type,cfg]) => {
  cfg.toggle.addEventListener("click", () => {
    if (cfg.options.hidden) { openGenericOptions(type); cfg.input.focus(); }
    else closeGenericOptions(type);
  });
  cfg.input.addEventListener("focus", () => openGenericOptions(type));
  cfg.input.addEventListener("input", () => {
    const values = type === "role" ? state.roleOptions : type === "experience" ? state.experienceOptions : type === "company" ? state.companyOptions || [] : [];
    renderGenericOptions(type, values);
    cfg.options.hidden = false;
  });
  cfg.options.addEventListener("click", async (event) => {
    const option=event.target.closest("[data-generic-value]"); if(!option)return;
    const selectedValue = option.dataset.genericValue;
    cfg.input.value = selectedValue;
    closeGenericOptions(type);
    if (type === "company") {
      // Commit the exact clicked company (not the autocomplete query) as the active filter.
      state.filters.company = selectedValue;
      elements.companyInput.value = selectedValue;
      state.page = 1;
      state.excludedJobs.clear();
      await Promise.all([loadFilterOptions(), loadSalaryFilterOptions()]);
      // Refresh company suggestions without allowing it to clear the committed value.
      await loadCompanyFilterOptions();
      state.filters.company = selectedValue;
      elements.companyInput.value = selectedValue;
      await loadJobs();
      return;
    }
    if(type==="salary") {
      const labels=[...document.querySelectorAll("#salaryFilterOptions .generic-option")];
      // map selected label to underlying band in currently loaded bands
      const bands=["0-300000","300000-500000","500000-800000","800000-1200000","1200000-2000000","2000000-"];
      const labelMap={"Up to ₹3 LPA":bands[0],"₹3–5 LPA":bands[1],"₹5–8 LPA":bands[2],"₹8–12 LPA":bands[3],"₹12–20 LPA":bands[4],"₹20 LPA+":bands[5],"₹20 LPA and above":bands[5]};
      cfg.input.dataset.salaryValue=labelMap[cfg.input.value]||"";
    }
    state.page = 1;
    state.excludedJobs.clear();
    await applyFilters(); // load filtered jobs before refreshing dependent facets
    await Promise.all([loadFilterOptions(), loadCompanyFilterOptions(), loadSalaryFilterOptions()]);
  });
});
document.addEventListener("click", (event) => {
  Object.entries(genericFilterMap).forEach(([type,cfg]) => {
    if(!cfg.options.hidden && !cfg.options.parentElement.contains(event.target)) closeGenericOptions(type);
  });
});

/* Location dropdown */
elements.locationDropdownToggle.addEventListener("click", () => {
  if (elements.locationOptions.hidden) {
    openLocationOptions();
    elements.locationInput.focus();
  } else {
    closeLocationOptions();
  }
});

elements.locationInput.addEventListener("focus", openLocationOptions);
elements.locationInput.addEventListener("input", openLocationOptions);

elements.locationOptions.addEventListener("click", async (event) => {
  const option = event.target.closest("[data-location]");

  if (!option) return;

  const picked = option.dataset.location;

  // Autocomplete text (e.g. "che") is only a search query, not a selected location.
  // Selecting Chennai should replace that query with the canonical option value.
  elements.locationInput.value = picked;
  state.filters.location = picked;
  // Keep the selected experience; loadFilterOptions will retain it when valid
  // and clear it only if the new role/location has no matching records.
  state.page = 1;

  closeLocationOptions();

  await Promise.all([
    loadFilterOptions(),
    loadCompanyFilterOptions(),
    loadSalaryFilterOptions(),
  ]);
  await loadJobs();

  elements.locationInput.focus();
});

document.addEventListener("click", (event) => {
  if (!event.target.closest(".location-filter-field")) {
    closeLocationOptions();
  }
});

elements.locationInput.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeLocationOptions();
  }

  if (event.key === "Enter") {
    event.preventDefault();
    applyFilters();
  }
});

/* Update experience options when role changes */
elements.searchInput.addEventListener("change", async () => {
  state.filters.role = elements.searchInput.value.trim();
  // Do not discard experience on role changes unless it becomes unavailable.
  state.page = 1;

  await loadJobs();
  await Promise.all([
    loadFilterOptions(),
    loadCompanyFilterOptions(),
    loadSalaryFilterOptions(),
  ]);
});

/* Update experience options when location is edited */
elements.locationInput.addEventListener("change", async () => {
  state.filters.location = elements.locationInput.value.trim();
  // Do not discard experience on location changes unless it becomes unavailable.
  state.page = 1;

  await Promise.all([
    loadFilterOptions(),
    loadCompanyFilterOptions(),
    loadSalaryFilterOptions(),
  ]);
  await loadJobs();
});

/* Update dependent filters when experience changes */
elements.experienceInput.addEventListener("change", async () => {
  state.filters.experience = elements.experienceInput.value.trim();
  state.page = 1;
  await Promise.all([
    loadFilterOptions(),
    loadCompanyFilterOptions(),
    loadSalaryFilterOptions(),
  ]);
  await loadJobs();
});

elements.companyInput.addEventListener("change", async () => {
  state.filters.company = elements.companyInput.value.trim();
  state.page = 1;
  await Promise.all([
    loadFilterOptions(),
    loadCompanyFilterOptions(),
    loadSalaryFilterOptions(),
  ]);
  await loadJobs();
});

elements.postedDateInput.addEventListener("change", async () => {
  applyFilters(); // sync all controls into state and reload with posted_after
  await Promise.all([loadFilterOptions(), loadCompanyFilterOptions(), loadSalaryFilterOptions()]);
});

document
  .getElementById("refreshUserDashboard")
  ?.addEventListener("click", loadUserDashboard);

elements.salaryFilterInput.addEventListener("change", async () => {
  state.page = 1;
  await applyFilters();
});

/* Clear filters */
document.getElementById("clearFilters").addEventListener("click", clearFilters);

/* Expand and collapse additional filters */
elements.moreFiltersToggle.addEventListener("click", () => {
  const isExpanded =
    elements.moreFiltersToggle.getAttribute("aria-expanded") === "true";

  elements.moreFilters.hidden = isExpanded;

  elements.moreFiltersToggle.setAttribute("aria-expanded", String(!isExpanded));

  elements.moreFiltersToggle.textContent = isExpanded
    ? "+ More filters"
    : "− Fewer filters";
});

/* Expand/collapse job portals and keep the two sidebar groups mutually exclusive. */
elements.jobPortalToggle.addEventListener("click", () => {
  if ((document.body.dataset.userRole || "").toLowerCase() === "user") { showPage("jobs"); loadJobs(); elements.sidebar.classList.remove("open"); return; }
  const expanded =
    elements.jobPortalToggle.getAttribute("aria-expanded") === "true";

  // Opening Job Portal closes Companies so stale expanded-state CSS cannot
  // leave both dropdown headings highlighted or make Job Portal look inactive.
  if (elements.companiesToggle && elements.companyOptions) {
    elements.companiesToggle.setAttribute("aria-expanded", "false");
    elements.companyOptions.hidden = true;
    const companiesGlyph = document.getElementById("companiesArrow");
    if (companiesGlyph) companiesGlyph.textContent = "+";
    elements.companiesToggle.classList.remove("active");
  }

  elements.jobPortalToggle.setAttribute("aria-expanded", String(!expanded));
  elements.sourceMenu.hidden = expanded;
  const portalGlyph = document.getElementById("dropdownArrow");
  if (portalGlyph) portalGlyph.textContent = expanded ? "+" : "−";

  // Recompute active navigation classes after updating both expanded states.
  showPage("jobs");
});
/* Pagination and page size */
elements.pageSizeSelect.addEventListener("change", () => {
  state.perPage = Number(elements.pageSizeSelect.value) || 10;
  state.page = 1;

  loadJobs();
});
/* Company Career Sites are scraper sources, never company-name filters. */
if (elements.companiesToggle && elements.companyOptions) {
  elements.companiesToggle.addEventListener("click", async () => {
    const expanded =
      elements.companiesToggle.getAttribute("aria-expanded") === "true";

    // Opening Companies closes Job Portal; only one source group can be open.
    elements.jobPortalToggle.setAttribute("aria-expanded", "false");
    elements.sourceMenu.hidden = true;
    const portalGlyph = document.getElementById("dropdownArrow");
    if (portalGlyph) portalGlyph.textContent = "+";

    elements.companiesToggle.setAttribute("aria-expanded", String(!expanded));
    elements.companyOptions.hidden = expanded;
    showPage("jobs");
    elements.jobPortalToggle.classList.remove("active");
    document
      .querySelectorAll(".sidebar-nav > .nav-item[data-page]")
      .forEach((item) => item.classList.remove("active"));
    elements.companiesToggle.classList.add("active");
    const glyph = document.getElementById("companiesArrow");
    if (glyph) glyph.textContent = expanded ? "+" : "−";
    if (!expanded) await loadCompanyOptions();
  });
  elements.companyOptions.addEventListener("change", async (event) => {
    const checkbox = event.target.closest("input[data-career-source-id]");
    if (!checkbox) return;
    const id = Number(checkbox.dataset.careerSourceId);
    if (checkbox.checked) {
      state.selectedCareerSourceIds.add(id);
      // Choosing a company from the Dashboard sidebar should open Job Portal.
      showPage("jobs");
    } else {
      state.selectedCareerSourceIds.delete(id);
    }
    syncMasterCheckbox(
      elements.selectAllCareerSites,
      state.selectedCareerSourceIds.size,
      (state.visibleCareerSources || state.careerSources).length,
    );
    syncSourceFilter();
    state.page = 1;
    state.excludedJobs.clear();
    await loadJobs();
    await Promise.all([
      loadFilterOptions(),
      loadCompanyFilterOptions(),
      loadSalaryFilterOptions(),
    ]);
  });
}

elements.sourceOptions.addEventListener("change", async (event) => {
  const target = event.target;
  if (target.matches("[data-select-all-sources]")) {
    state.selectedSourceIds = target.checked
      ? new Set(state.sources.map((source) => Number(source.id)))
      : new Set();
  } else {
    return;
  }
  renderSourceOptions();
  syncSourceFilter();
  state.page = 1;
  state.excludedJobs.clear();
  await loadJobs();
  await Promise.all([
    loadFilterOptions(),
    loadCompanyFilterOptions(),
    loadSalaryFilterOptions(),
  ]);
});
elements.companyOptions.addEventListener("change", async (event) => {
  if (!event.target.matches("[data-select-all-companies]")) return;
  state.selectedCareerSourceIds = event.target.checked
    ? new Set(
        (state.visibleCareerSources || state.careerSources || []).map(
          (source) => Number(source.id),
        ),
      )
    : new Set();
  renderCompanySidebar();
  syncSourceFilter();
  state.page = 1;
  state.excludedJobs.clear();
  await Promise.all([
    loadFilterOptions(),
    loadCompanyFilterOptions(),
    loadSalaryFilterOptions(),
  ]);
  await loadJobs();
});

elements.jobsTableBody.addEventListener("click", (event) => {
  const titleButton = event.target.closest("[data-job-details-id]");
  if (titleButton) showJobDetails(titleButton.dataset.jobDetailsId);
});

document
  .getElementById("jobDetailsClose")
  .addEventListener("click", closeJobDetails);
document
  .getElementById("jobDetailsExport")
  .addEventListener("click", exportJobDetails);
document
  .getElementById("jobDetailsModal")
  .addEventListener("click", (event) => {
    if (event.target.matches("[data-close-job-details]")) closeJobDetails();
  });
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeJobDetails();
});

elements.jobsTableBody.addEventListener("change", handleJobSelection);

elements.selectAllJobs.addEventListener("change", (event) => {
  selectVisibleJobs(event.target.checked);
});

/* Sort table columns */
document
  .querySelector(".jobs-table thead")
  .addEventListener("click", (event) => {
    const header = event.target.closest("th[data-sort]");

    if (header) {
      sortJobs(header.dataset.sort);
    }
  });

/* Pagination buttons */
document
  .getElementById("firstPageButton")
  .addEventListener("click", () => setPage(1));

document
  .getElementById("previousPageButton")
  .addEventListener("click", () => setPage(state.page - 1));

document
  .getElementById("nextPageButton")
  .addEventListener("click", () => setPage(state.page + 1));

document
  .getElementById("lastPageButton")
  .addEventListener("click", () => setPage(state.totalPages));

/* Refresh dashboard data */
const refreshDashboardButton = document.getElementById(
  "refreshDashboardButton",
);
if (refreshDashboardButton)
  refreshDashboardButton.addEventListener("click", loadDashboard);
document.getElementById("refreshButton").addEventListener("click", async () => {
  await loadSources();
  await Promise.all([
    loadFilterOptions(),
    loadCompanyFilterOptions(),
    loadSalaryFilterOptions(),
  ]);
  await loadJobs();

  checkHealth();
});

/* Export button */
document.getElementById("exportButton").addEventListener("click", exportJobs);

/* Logout button */
document.getElementById("logoutButton").addEventListener("click", logout);

/* Sidebar navigation */
document
  .querySelectorAll(".sidebar-nav > .nav-item[data-page]")
  .forEach((item) => {
    item.addEventListener("click", (event) => {
      event.preventDefault();

      showPage(item.dataset.page);

      elements.sidebar.classList.remove("open");
    });
  });

/* Animated sidebar collapse on desktop; slide-in navigation on mobile. */
const sidebarMenuButton = document.getElementById("mobileMenuButton");
if (sidebarMenuButton) sidebarMenuButton.addEventListener("click", () => {
  if (document.body.dataset.userRole === "user") return;
  if (window.matchMedia("(max-width: 760px)").matches) {
    elements.sidebar.classList.toggle("open");
    const isOpen = elements.sidebar.classList.contains("open");
    sidebarMenuButton.setAttribute("aria-expanded", String(isOpen));
    sidebarMenuButton.title = isOpen ? "Close navigation" : "Open navigation";
    return;
  }
  const collapsed = document
    .querySelector(".app-layout")
    .classList.toggle("sidebar-collapsed");
  sidebarMenuButton.setAttribute("aria-expanded", String(!collapsed));
  sidebarMenuButton.title = collapsed ? "Expand sidebar" : "Collapse sidebar";
});

/* Profile avatar reveals the existing logout action on hover or keyboard focus. */
const profileMenu = document.getElementById("profileMenu");
const profileButton = document.getElementById("profileButton");
const profileDropdown = document.getElementById("profileDropdown");
function setProfileMenu(open) {
  profileDropdown.hidden = !open;
  profileButton.setAttribute("aria-expanded", String(open));
}
profileButton.addEventListener("click", (event) => {
  event.stopPropagation();
  setProfileMenu(profileDropdown.hidden);
});
profileMenu.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    setProfileMenu(false);
    profileButton.focus();
  }
});
document.addEventListener("click", (event) => {
  if (!profileMenu.contains(event.target)) setProfileMenu(false);
});

/* Initial loading */
async function initializePortal() {
  const userRole = String(document.body.dataset.userRole || "admin").toLowerCase();
  // Users land directly on the job portal; dashboard initialization is admin-only.
  showPage(userRole === "user" ? "jobs" : "dashboard");
  await loadSources();
  await Promise.all([loadFilterOptions(), loadCompanyOptions(), loadSalaryFilterOptions(), loadCompanyFilterOptions()]);
  await loadJobs();
  checkHealth();
}

initializePortal();


// Phase 4: render Credits & Subscription within the main application workspace.
async function loadCreditsAdmin() {
  const usersNode = document.getElementById("creditsUsers");
  const historyNode = document.getElementById("creditsHistory");
  if (!usersNode || !historyNode) return;
  try {
    const response = await fetch("/api/admin/credits");
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Unable to load credit data");
    const allocation = document.getElementById("allocation");
    if (allocation) allocation.value = data.free_credits ?? 5;
    usersNode.innerHTML = `<div class="table-container"><table class="jobs-table credits-table"><thead><tr><th>User</th><th>Email</th><th>Balance</th><th>Status</th><th>Subscription</th><th>Actions</th></tr></thead><tbody>${(data.users||[]).map(u=>`<tr><td>${u.username}</td><td>${u.email||""}</td><td>${u.balance}</td><td>${u.account_status}</td><td>${u.subscription_plan} / ${u.subscription_status}</td><td><input type="number" min="0" value="5" id="credit-amt-${u.username}" style="width:65px"><button class="credit-action" data-action="add" data-user="${u.username}">Add</button><button class="credit-action" data-action="deduct" data-user="${u.username}">Deduct</button><button class="credit-action" data-action="reset" data-user="${u.username}">Reset</button><button class="credit-action" data-action="status" data-user="${u.username}" data-status="${u.account_status==='active'?'suspended':'active'}">${u.account_status==='active'?'Suspend':'Activate'}</button><button class="credit-action" data-action="subscription" data-user="${u.username}">Subscription</button></td></tr>`).join("")}</tbody></table></div>`;
    historyNode.innerHTML = `<div class="table-container"><table class="jobs-table credits-table"><thead><tr><th>Date</th><th>User</th><th>Action</th><th>Amount</th><th>Balance</th><th>Job</th></tr></thead><tbody>${(data.history||[]).map(h=>`<tr><td>${h.created_at||""}</td><td>${h.username}</td><td>${h.action}</td><td>${h.amount}</td><td>${h.balance_after}</td><td>${h.job_title||""}</td></tr>`).join("")}</tbody></table></div>`;
  } catch (error) { usersNode.innerHTML = `<p class="empty-state">${error.message}</p>`; }
}
async function submitCreditAdminAction(payload) {
  const response = await fetch("/api/admin/credits",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  const result = await response.json();
  if (!response.ok || result.error) { alert(result.error || "Action failed"); return; }
  await loadCreditsAdmin();
}
document.addEventListener("click", event => {
  const button = event.target.closest(".credit-action");
  if (button) {
    const username=button.dataset.user, action=button.dataset.action;
    const amount=document.getElementById(`credit-amt-${username}`)?.value || 0;
    let payload={action,username,amount};
    if(action==="status") payload.status=button.dataset.status;
    if(action==="subscription"){payload.plan=prompt("Subscription plan","premium")||"free";payload.subscription_status="active";}
    submitCreditAdminAction(payload);
  }
  if(event.target.id==="saveAllocation") submitCreditAdminAction({action:"allocation",amount:document.getElementById("allocation").value});
});

// User source links debit via JSON first, then update the badge before opening source.
document.addEventListener("click", async (event) => {
  const link = event.target.closest('a.job-link[href^="/api/credits/open-job/"], #jobDetailsApplyLink[href^="/api/credits/open-job/"]');
  if (!link || document.body.dataset.userRole !== "user") return;
  event.preventDefault();
  if (link.dataset.busy === "1") return;
  link.dataset.busy = "1";
  try {
    const response = await fetch(link.href + (link.href.includes("?") ? "&" : "?") + "json=1");
    const data = await response.json();
    if (!response.ok || !data.ok) { alert(data.error || (response.status === 402 ? "No credits remaining." : "Unable to open job.")); return; }
    const balance = document.getElementById("creditBalance");
    const badge = document.getElementById("userCreditBadge");
    if (balance) balance.textContent = data.balance;
    if (badge) { badge.hidden = false; badge.classList.toggle("credits-empty", Number(data.balance) <= 0); }
    window.open(data.url, "_blank", "noopener");
  } catch (err) { alert("Could not open job link. Please try again."); }
  finally { link.dataset.busy = "0"; }
});

// Phase 4 user credit balance
document.addEventListener("DOMContentLoaded", async () => {
  if (document.body.dataset.userRole !== "user") return;
  const badge=document.getElementById("userCreditBadge"), value=document.getElementById("creditBalance");
  try { const r=await fetch("/api/credits/me"); const d=await r.json(); if(r.ok&&badge){badge.hidden=false;value.textContent=d.balance; if(d.balance<=0)badge.classList.add("credits-empty");} } catch(e){console.warn("Credit balance unavailable",e);}
});


// Admin job-market analytics (aggregated from the database).
let adminAnalyticsData = null;
let activeAnalyticsKey = "portals";
const analyticsColors = ["#ff8617","#2580ef","#13a8d5","#8b5cf6","#f59e0b","#10b981","#ec4899","#64748b","#84cc16","#06b6d4"];
function analyticsNum(value){ return Number(value || 0).toLocaleString("en-IN"); }
function analyticsPct(value,total){ return total ? (value*100/total).toFixed(1)+"%" : "0.0%"; }
function analyticsSafeLabel(value){ return escapeHTML(String(value ?? "Unknown")); }
function renderAnalyticsDonut(node, rows, total, centerId){
  if(!node) return;
  let cumulative=0;
  const slices=rows.map((r,i)=>{const pct=total?Math.max(0,Number(r.total||0))*100/total:0;const start=cumulative;cumulative+=pct;return `${analyticsColors[i%analyticsColors.length]} ${start}% ${cumulative}%`;});
  node.style.background=`conic-gradient(${slices.join(",")})`;
  const center=node.querySelector("span"); if(center) center.innerHTML=`<strong>${analyticsNum(total)}</strong><small>Jobs</small>`;
}
function renderPortalAnalytics(rows,total){
  const donut=document.getElementById("portalDonut"), legend=document.getElementById("portalLegend");
  renderAnalyticsDonut(donut,rows,total);
  if(legend) legend.innerHTML=rows.slice(0,5).map((r,i)=>`<div class="analytics-legend-row"><i style="background:${analyticsColors[i%analyticsColors.length]}"></i><span title="${analyticsSafeLabel(r.label)}">${analyticsSafeLabel(r.label)}</span><b>${analyticsPct(Number(r.total||0),total)}</b></div>`).join("")+
    (rows.length>5?`<small class="analytics-more">${rows.length-5} more portals · View Details</small>`:"");
}
function renderExperienceAnalytics(data){
  const f=Number(data.fresher_jobs||0), e=Number(data.experienced_jobs||0), total=Number(data.total_jobs||0);
  const unknown=Math.max(0,total-f-e), donut=document.getElementById("experienceDonut");
  const expRows=[{total:f},{total:e},{total:unknown}];
  renderAnalyticsDonut(donut,expRows,total);
  if(donut) donut.style.background=`conic-gradient(#ff8617 0 ${total?f*100/total:0}%,#2580ef ${total?f*100/total:0}% ${total?(f+e)*100/total:0}%,#d7dce5 ${total?(f+e)*100/total:0}% 100%)`;
  const legend=document.getElementById("experienceLegend");
  if(legend) legend.innerHTML=`<div class="analytics-legend-row"><i style="background:#ff8617"></i><span>Freshers</span><b>${analyticsNum(f)} (${analyticsPct(f,total)})</b></div><div class="analytics-legend-row"><i style="background:#2580ef"></i><span>Experienced</span><b>${analyticsNum(e)} (${analyticsPct(e,total)})</b></div>${unknown?`<div class="analytics-legend-row"><i style="background:#d7dce5"></i><span>Unclassified</span><b>${analyticsNum(unknown)}</b></div>`:""}`;
}
function renderAnalyticsBars(targetId,rows,color){
  const target=document.getElementById(targetId); if(!target)return;
  const top=rows.slice(0,5), max=Math.max(1,...top.map(x=>Number(x.total||0)));
  target.innerHTML=top.length?top.map(r=>`<div class="analytics-bar-row"><span class="analytics-bar-label" title="${analyticsSafeLabel(r.label)}">${analyticsSafeLabel(r.label)}</span><div class="analytics-bar-track"><i style="width:${Math.max(2,Number(r.total||0)*100/max)}%;background:${color}"></i></div><b>${analyticsNum(r.total)}</b></div>`).join(""):'<p class="empty-state">No records found.</p>';
}
async function loadAdminAnalytics(){
  const section=document.getElementById("adminAnalytics"); if(!section)return;
  try{
    const data=await apiGet("/api/admin/analytics"); adminAnalyticsData=data;
    renderPortalAnalytics(data.portals||[],Number(data.total_jobs||0));
    renderExperienceAnalytics(data);
    renderAnalyticsBars("companyBars",data.companies||[],"linear-gradient(90deg,#ffb15d,#ff8617)");
    renderAnalyticsBars("locationBars",data.locations||[],"linear-gradient(90deg,#75b2ff,#2580ef)");
  }catch(err){
    console.error("Admin analytics unavailable",err);
    ["portalLegend","experienceLegend","companyBars","locationBars"].forEach(id=>{const el=document.getElementById(id);if(el)el.innerHTML='<p class="empty-state">Analytics could not load.</p>';});
  }
}
function openAnalyticsDetails(key){
  if(!adminAnalyticsData)return;
  activeAnalyticsKey=key;
  const modal=document.getElementById("analyticsModal"), title=document.getElementById("analyticsModalTitle"), search=document.getElementById("analyticsSearch");
  const titles={portals:"All Job Portals",experience:"Fresher & Experience Breakdown",companies:"All Companies",locations:"All Locations"};
  if(title)title.textContent=titles[key]||"Analytics Details";
  if(search){search.value="";search.hidden=key==="experience";}
  renderAnalyticsDetails();
  if(modal)modal.hidden=false;
}
function renderAnalyticsDetails(){
  const box=document.getElementById("analyticsDetailList");if(!box||!adminAnalyticsData)return;
  let rows=[];
  if(activeAnalyticsKey==="portals")rows=adminAnalyticsData.portals||[];
  if(activeAnalyticsKey==="companies")rows=adminAnalyticsData.companies||[];
  if(activeAnalyticsKey==="locations")rows=adminAnalyticsData.locations||[];
  if(activeAnalyticsKey==="experience")rows=[{label:"Freshers",total:adminAnalyticsData.fresher_jobs},{label:"Experienced",total:adminAnalyticsData.experienced_jobs},{label:"Unclassified",total:Math.max(0,adminAnalyticsData.total_jobs-adminAnalyticsData.fresher_jobs-adminAnalyticsData.experienced_jobs)}];
  const q=(document.getElementById("analyticsSearch")?.value||"").trim().toLowerCase();
  if(q)rows=rows.filter(r=>String(r.label||"").toLowerCase().includes(q));
  box.innerHTML=rows.map((r,i)=>`<div class="analytics-detail-row"><span>${i+1}. ${analyticsSafeLabel(r.label)}</span><strong>${analyticsNum(r.total)}${activeAnalyticsKey==="portals"?` · ${analyticsPct(Number(r.total||0),Number(adminAnalyticsData.total_jobs||0))}`:""}</strong></div>`).join("")||'<p class="empty-state">No matching records.</p>';
}
document.addEventListener("click",e=>{
  const trigger=e.target.closest("[data-analytics]");if(trigger){openAnalyticsDetails(trigger.dataset.analytics);return;}
  if(e.target.closest("[data-close-analytics]")){const modal=document.getElementById("analyticsModal");if(modal)modal.hidden=true;}
});
document.addEventListener("input",e=>{if(e.target.id==="analyticsSearch")renderAnalyticsDetails();});
