const API = "https://hemolink-api-tm3c.onrender.com";
const DEFAULT_HOSPITAL = {
  name: "RedSync General Hospital",
  latitude: 12.9716,
  longitude: 77.5946,
};

const pageTitles = {
  overview: "Overview",
  requests: "Emergency Requests",
  matches: "Donor Matches",
  responses: "Active Responses",
  history: "History",
  settings: "Settings",
  details: "Incident Center",
};

const state = {
  page: "overview",
  requests: [],
  acceptances: {},
  matches: {},
  selectedRequestId: null,
  requestFilter: "all",
  requestSearch: "",
  loading: true,
  refreshing: false,
  error: null,
  lastUpdated: null,
  map: null,
  hospital: loadHospital(),
};

const app = document.getElementById("app");
const dialog = document.getElementById("workspace-dialog");
const dialogTitle = document.getElementById("dialog-title");
const dialogEyebrow = document.getElementById("dialog-eyebrow");
const dialogContent = document.getElementById("dialog-content");
const toastRegion = document.getElementById("toast-region");

function loadHospital() {
  try {
    const saved = JSON.parse(localStorage.getItem("redsync_hospital_workspace"));
    if (saved && typeof saved.name === "string") return { ...DEFAULT_HOSPITAL, ...saved };
  } catch (_) {
    // A corrupt browser preference should not stop the hospital workspace.
  }
  return { ...DEFAULT_HOSPITAL };
}

function saveHospital() {
  localStorage.setItem("redsync_hospital_workspace", JSON.stringify(state.hospital));
}

function escapeHTML(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;",
  }[character]));
}

function escapeAttribute(value) {
  return escapeHTML(value).replace(/`/g, "&#96;");
}

function statusClass(status) {
  return `status-${String(status || "open").replace(/[^a-z_]/gi, "")}`;
}

function urgencyClass(urgency) {
  return `urgency-${String(urgency || "standard").replace(/[^a-z_]/gi, "")}`;
}

function isActiveRequest(request) {
  return request.status === "open" || request.status === "matching";
}

function toDate(value) {
  if (!value) return null;
  return new Date(value.endsWith("Z") ? value : `${value}Z`);
}

function formatDate(value) {
  const date = toDate(value);
  if (!date || Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(date);
}

function formatAge(value) {
  const date = toDate(value);
  if (!date || Number.isNaN(date.getTime())) return "—";
  const minutes = Math.max(0, Math.floor((Date.now() - date.getTime()) / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return hours < 24 ? `${hours}h ago` : `${Math.floor(hours / 24)}d ago`;
}

function formatDeadline(value) {
  const date = toDate(value);
  if (!date || Number.isNaN(date.getTime())) return "ETA not set";
  const minutes = Math.ceil((date.getTime() - Date.now()) / 60000);
  return minutes > 0 ? `${minutes} min remaining` : "ETA overdue";
}

function initials(name) {
  return String(name || "RH").split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "RH";
}

async function api(path, options = {}) {
  const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}) };
  const response = await fetch(`${API}${path}`, { ...options, headers });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (_) {
      // Keep a useful status-based error when a proxy returns non-JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

async function refreshData(showLoading = false) {
  if (state.refreshing) return;
  state.refreshing = true;
  if (showLoading && !state.requests.length) {
    state.loading = true;
    render();
  }

  try {
    const requests = await api("/requests/");
    state.requests = requests;
    const active = requests.filter(isActiveRequest);
    const needsAllAcceptances = state.page === "history" || state.page === "responses";
    const targetIds = new Set((needsAllAcceptances ? requests : active).map((request) => request.id));
    if (state.selectedRequestId) targetIds.add(state.selectedRequestId);

    await Promise.all([...targetIds].map(async (requestId) => {
      state.acceptances[requestId] = await api(`/requests/${encodeURIComponent(requestId)}/acceptances`);
    }));

    const needsMatchData = ["overview", "requests", "matches", "details"].includes(state.page);
    if (needsMatchData) {
      const matchIds = new Set(active.map((request) => request.id));
      if (state.selectedRequestId) matchIds.add(state.selectedRequestId);
      await Promise.all([...matchIds].map(async (requestId) => {
        state.matches[requestId] = await api(`/requests/${encodeURIComponent(requestId)}/matches`);
      }));
    }

    state.error = null;
    state.lastUpdated = new Date();
  } catch (error) {
    state.error = error.message || "The hospital workspace could not load its latest data.";
  } finally {
    state.loading = false;
    state.refreshing = false;
    render();
  }
}

function getAcceptances(requestId) {
  return state.acceptances[requestId] || [];
}

function getMatches(requestId) {
  return state.matches[requestId] || [];
}

function activeResponseCount() {
  return Object.values(state.acceptances).flat().filter((acceptance) => acceptance.status === "pending").length;
}

function matchingDonorCount() {
  return Object.values(state.matches).flat().filter((match) => match.is_available).length;
}

function navIcon(name) {
  const icons = {
    overview: '<svg viewBox="0 0 24 24"><rect x="4" y="4" width="6" height="6" rx="1"/><rect x="14" y="4" width="6" height="6" rx="1"/><rect x="4" y="14" width="6" height="6" rx="1"/><rect x="14" y="14" width="6" height="6" rx="1"/></svg>',
    requests: '<svg viewBox="0 0 24 24"><path d="M5 5h14v14H5z"/><path d="M8 9h8M8 13h8M8 17h5"/></svg>',
    matches: '<svg viewBox="0 0 24 24"><circle cx="9" cy="9" r="3"/><circle cx="17" cy="16" r="3"/><path d="M3.8 19c.7-2.7 2.6-4 5.2-4 1.1 0 2.1.2 2.9.7M14.5 6.7c.7-.5 1.5-.7 2.5-.7 2.2 0 3.7 1.2 4.2 3.4"/></svg>',
    responses: '<svg viewBox="0 0 24 24"><path d="M4 12h3l2-5 4 10 2-5h5"/></svg>',
    history: '<svg viewBox="0 0 24 24"><path d="M4 4v5h5"/><path d="M5.3 14A7 7 0 1 0 5 9"/><path d="M12 8v4l3 2"/></svg>',
    settings: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.1 2.1-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-3v-.2a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1-2.1-2.1.1-.1a1.7 1.7 0 0 0 .3-1.9 1.7 1.7 0 0 0-1.6-1H5v-3h.2a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9l-.1-.1L8.5 5l.1.1a1.7 1.7 0 0 0 1.9.3 1.7 1.7 0 0 0 1-1.6V3.5h3v.2a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1 2.1 2.1-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v3h-.2a1.7 1.7 0 0 0-1.4 2z"/></svg>',
  };
  return icons[name] || icons.overview;
}

function renderShell(content) {
  const navigation = [
    ["overview", "Overview"], ["requests", "Emergency Requests"], ["matches", "Donor Matches"],
    ["responses", "Active Responses"], ["history", "History"],
  ];
  const hospitalName = escapeHTML(state.hospital.name);
  const activePage = state.page === "details" ? "requests" : state.page;
  return `
    <div class="app-shell">
      <aside class="sidebar">
        <a class="brand" href="#" data-action="page" data-page="overview" aria-label="RedSync overview">
          <span class="brand-mark"></span><span class="brand-copy"><span class="brand-name">Red<span>Sync</span></span><span class="brand-caption">HOSPITAL OPERATIONS</span></span>
        </a>
        <p class="sidebar-label">WORKSPACE</p>
        <nav class="nav-list" aria-label="Hospital navigation">
          ${navigation.map(([id, label]) => `<button class="nav-button ${activePage === id ? "active" : ""}" type="button" data-action="page" data-page="${id}"><span class="nav-icon">${navIcon(id)}</span>${label}</button>`).join("")}
        </nav>
        <div class="nav-spacer"></div>
        <p class="sidebar-label">PREFERENCES</p>
        <button class="nav-button ${state.page === "settings" ? "active" : ""}" type="button" data-action="page" data-page="settings"><span class="nav-icon">${navIcon("settings")}</span>Settings</button>
        <section class="hospital-card" aria-label="Hospital identity">
          <div class="hospital-card-top"><span class="hospital-avatar">${escapeHTML(initials(state.hospital.name))}</span><div><strong>${hospitalName}</strong><span>Demo hospital workspace</span></div></div>
          <div class="connection ${state.error ? "offline" : ""}"><span class="connection-dot"></span>${state.error ? "API needs attention" : "API connection monitored"}</div>
        </section>
      </aside>
      <section class="main-area">
        <header class="topbar">
          <div class="breadcrumb"><span>Hospital Operations</span><span class="crumb-separator">/</span><strong>${escapeHTML(pageTitles[state.page] || "Workspace")}</strong></div>
          <div class="top-actions">
            <span class="live-chip">System monitored</span>
            <button class="icon-button" type="button" data-action="notifications" aria-label="Open system notifications">⌁</button>
            <button class="profile-chip" type="button" data-action="page" data-page="settings"><span class="hospital-avatar">${escapeHTML(initials(state.hospital.name))}</span><span class="profile-copy">${hospitalName}</span></button>
          </div>
        </header>
        <main class="page-wrap">${content}</main>
      </section>
    </div>`;
}

function pageHeading(eyebrow, title, copy, action = "") {
  return `<div class="page-heading"><div><p class="eyebrow">${eyebrow}</p><h1>${title}</h1><p class="heading-copy">${copy}</p></div><div>${action}</div></div>`;
}

function errorBanner() {
  if (!state.error) return "";
  return `<div class="error-banner"><div><strong>Unable to refresh live operations data</strong>${escapeHTML(state.error)}</div><button class="secondary-button" type="button" data-action="retry">Retry</button></div>`;
}

function emptyState(title, copy, actionLabel = "Create request") {
  return `<section class="empty-state"><div><div class="empty-mark">+</div><h2>${title}</h2><p>${copy}</p><button class="primary-button" type="button" data-action="create-request">${actionLabel}</button></div></section>`;
}

function statusPill(value) {
  return `<span class="status-pill ${statusClass(value)}">${escapeHTML(String(value || "open").replace("_", " "))}</span>`;
}

function urgencyPill(value) {
  const title = value === "standard" ? "normal" : value;
  return `<span class="urgency-pill ${urgencyClass(value)}">${escapeHTML(title)}</span>`;
}

function renderLoading() {
  return `${pageHeading("CONNECTING TO OPERATIONS", "Emergency Response Center", "Loading live emergency requests and donor response data.")}<div class="loading-grid"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>`;
}

function metricCard(tone, icon, label, value, caption) {
  return `<article class="metric-card ${tone}"><div class="metric-top"><span>${label}</span><span class="metric-icon">${icon}</span></div><div class="metric-number">${value}</div><div class="metric-caption">${caption}</div></article>`;
}

function renderOverview() {
  const active = state.requests.filter(isActiveRequest);
  const fulfilled = state.requests.filter((request) => request.status === "fulfilled");
  const selected = active.slice(0, 4);
  return `${pageHeading("LIVE OPERATIONS", "Emergency Response Center", "Monitor blood requests, compatible donor availability, and verified donation responses from one focused workspace.", '<button class="primary-button" type="button" data-action="create-request"><span class="button-icon">+</span>Create emergency request</button>')}
    ${errorBanner()}
    <section class="metric-grid">
      ${metricCard("red", "◉", "ACTIVE REQUESTS", active.length, active.length ? "Emergency requests in progress" : "No incidents need attention")}
      ${metricCard("blue", "⌁", "MATCHING DONORS", matchingDonorCount(), "Eligible matches at active radii")}
      ${metricCard("amber", "↗", "ACTIVE RESPONSES", activeResponseCount(), "Accepted donors still pending")}
      ${metricCard("green", "✓", "FULFILLED REQUESTS", fulfilled.length, "Completed donation requests")}
    </section>
    <section class="overview-grid">
      <article class="panel">
        <header class="panel-header"><div><div class="panel-title-row"><h2>Priority request queue</h2><span class="count-pill">${active.length}</span></div><p class="panel-kicker">Requests needing active operational attention</p></div><button class="quiet-button" type="button" data-action="page" data-page="requests">View all →</button></header>
        <div class="panel-body">${selected.length ? `<div class="request-stack">${selected.map(renderRequestRow).join("")}</div>` : emptyState("No active emergency requests", "Create a blood request to begin matching compatible nearby donors.")}</div>
      </article>
      <aside class="panel pulse-panel">
        <p class="eyebrow">OPERATIONS PULSE</p><h2>Response readiness</h2><p class="panel-kicker">A lightweight hospital workspace designed around confirmed backend data.</p>
        <div class="system-list"><div class="system-row"><span>Request service</span><strong class="system-state">${state.error ? "CHECK" : "MONITORED"}</strong></div><div class="system-row"><span>Donor matching</span><strong class="system-state">${active.length ? "ACTIVE" : "READY"}</strong></div><div class="system-row"><span>Journey updates</span><strong class="system-state">PENDING API</strong></div></div>
        <button class="primary-button quick-create" type="button" data-action="create-request">Create emergency request</button>
        <p class="compliance-note">Travel stages are shown only when confirmed by the backend. The current mobile donor journey remains protected.</p>
      </aside>
    </section>`;
}

function renderRequestRow(request) {
  const acceptances = getAcceptances(request.id);
  return `<button class="request-row" type="button" data-action="open-details" data-request-id="${escapeAttribute(request.id)}"><span class="blood-badge">${escapeHTML(request.blood_group_needed)}</span><span class="request-row-main"><span class="request-row-title"><strong>${escapeHTML(request.hospital_name)}</strong>${urgencyPill(request.urgency)}</span><span class="request-row-meta">${escapeHTML(request.units_needed)} unit${request.units_needed === 1 ? "" : "s"} · ${escapeHTML(request.current_radius_km)} km search radius · ${acceptances.filter((item) => item.status === "pending").length} response${acceptances.filter((item) => item.status === "pending").length === 1 ? "" : "s"}</span></span><span class="request-row-tail">${statusPill(request.status)}<small>${formatAge(request.created_at)}</small></span></button>`;
}

function filteredRequests() {
  const search = state.requestSearch.trim().toLowerCase();
  return state.requests.filter((request) => {
    const matchesFilter = state.requestFilter === "all" || request.status === state.requestFilter || request.urgency === state.requestFilter;
    const searchText = `${request.hospital_name} ${request.blood_group_needed} ${request.id}`.toLowerCase();
    return matchesFilter && (!search || searchText.includes(search));
  });
}

function renderRequestCard(request) {
  const acceptances = getAcceptances(request.id);
  const matches = getMatches(request.id);
  const accepted = acceptances.filter((item) => item.status === "pending" || item.status === "fulfilled").length;
  return `<article class="request-card"><div class="request-card-top"><div class="request-title"><span class="blood-badge">${escapeHTML(request.blood_group_needed)}</span><div><h3>${escapeHTML(request.hospital_name)}</h3><span class="muted">Emergency blood request</span></div></div><div>${urgencyPill(request.urgency)} ${statusPill(request.status)}</div></div><div class="request-card-meta"><span>${escapeHTML(request.units_needed)} UNIT${request.units_needed === 1 ? "" : "S"}</span><span>${escapeHTML(request.current_radius_km)} KM RADIUS</span><span>${matches.length} ELIGIBLE MATCH${matches.length === 1 ? "" : "ES"}</span><span>${accepted} ACCEPTED</span><span>ETA ${escapeHTML(request.eta_window_minutes)} MIN</span></div><div class="request-card-footer"><span class="response-summary">Created ${formatDate(request.created_at)} · ID ${escapeHTML(request.id.slice(0, 8))}</span><button class="secondary-button" type="button" data-action="open-details" data-request-id="${escapeAttribute(request.id)}">View details</button></div></article>`;
}

function renderRequests() {
  const filters = [["all", "All"], ["critical", "Critical"], ["urgent", "Urgent"], ["open", "Open"], ["matching", "Matching"], ["fulfilled", "Fulfilled"]];
  const requests = filteredRequests();
  return `${pageHeading("REQUEST COMMAND", "Emergency Requests", "Search, prioritise, and open the incident workspace for every emergency blood request.", '<button class="primary-button" type="button" data-action="create-request">+ Create request</button>')}${errorBanner()}<div class="toolbar"><div class="filters">${filters.map(([id, label]) => `<button class="filter-button ${state.requestFilter === id ? "active" : ""}" type="button" data-action="filter" data-filter="${id}">${label}</button>`).join("")}</div><label class="search-box"><input type="search" data-search="requests" value="${escapeAttribute(state.requestSearch)}" placeholder="Search hospital, blood group, or ID" aria-label="Search requests" /></label></div><section id="request-results" class="request-grid">${requests.length ? requests.map(renderRequestCard).join("") : emptyState("No requests match this view", "Try another filter or create a new emergency request.")}</section>`;
}

function renderMatches() {
  const active = state.requests.filter(isActiveRequest);
  return `${pageHeading("MATCHING DESK", "Donor Matches", "Privacy-minimized, real-time eligible donor matches at each request’s active search radius.")}${errorBanner()}${active.length ? `<section class="request-grid">${active.map((request) => { const matches = getMatches(request.id); return `<article class="panel"><header class="panel-header compact"><div class="panel-title-row"><span class="blood-badge">${escapeHTML(request.blood_group_needed)}</span><div><h2>${escapeHTML(request.hospital_name)}</h2><p class="panel-kicker">${escapeHTML(request.current_radius_km)} km radius · ${matches.length} eligible donor match${matches.length === 1 ? "" : "es"}</p></div></div><button class="secondary-button" type="button" data-action="open-details" data-request-id="${escapeAttribute(request.id)}">Incident center</button></header><div class="match-list">${matches.length ? matches.map(renderMatchCard).join("") : '<p class="muted">No eligible donors are currently available at this request’s matching radius.</p>'}</div></article>`; }).join("")}</section>` : emptyState("No donor matches yet", "Create an emergency request to calculate compatible nearby donor matches.")}`;
}

function renderMatchCard(match) {
  return `<div class="match-card"><div class="match-identity"><span class="match-avatar">${escapeHTML(match.blood_group)}</span><div><strong>${escapeHTML(match.donor_label)}</strong><span>${escapeHTML(match.distance_km)} km away · ${match.is_verified ? "Verified donor" : "Donor verification pending"} · ${Math.round(match.reliability_score)}% reliability</span></div></div><span class="match-score">${Math.round(match.score * 100)}% MATCH</span></div>`;
}

function renderResponses() {
  const responseGroups = state.requests.filter(isActiveRequest).map((request) => ({ request, items: getAcceptances(request.id).filter((item) => item.status === "pending") })).filter((group) => group.items.length);
  return `${pageHeading("RESPONSE MONITOR", "Active Responses", "Track accepted donors and confirm a completed donation only when the hospital has verified it.")}${errorBanner()}${responseGroups.length ? `<section class="request-grid">${responseGroups.map(({ request, items }) => `<article class="panel"><header class="panel-header compact"><div><div class="panel-title-row"><span class="blood-badge">${escapeHTML(request.blood_group_needed)}</span><h2>${escapeHTML(request.hospital_name)}</h2></div><p class="panel-kicker">${items.length} pending accepted response${items.length === 1 ? "" : "s"}</p></div><button class="secondary-button" type="button" data-action="open-details" data-request-id="${escapeAttribute(request.id)}">Open incident</button></header><div class="response-list">${items.map((item) => renderResponseCard(item, request)).join("")}</div></article>`).join("")}</section>` : emptyState("No active donor responses", "Accepted donor responses will appear here as soon as the backend confirms them.")}`;
}

function renderResponseCard(acceptance, request) {
  return `<div class="response-card"><div class="response-identity"><span class="response-avatar">↗</span><div><strong>Accepted donor response</strong><span>${escapeHTML(request.blood_group_needed)} compatible donor · ${formatDeadline(acceptance.eta_deadline)}</span></div></div><div class="response-actions">${statusPill(acceptance.status)}${acceptance.status === "pending" ? `<button class="tiny-action" type="button" data-action="fulfill" data-acceptance-id="${escapeAttribute(acceptance.id)}" data-request-id="${escapeAttribute(request.id)}">Confirm donation</button>` : ""}</div></div>`;
}

function renderHistory() {
  const fulfilled = state.requests.filter((request) => request.status === "fulfilled");
  return `${pageHeading("COMPLETED CARE", "Request History", "Review completed emergency requests and their backend-confirmed donation outcomes.")}${errorBanner()}${fulfilled.length ? `<section class="request-grid">${fulfilled.map((request) => { const acceptances = getAcceptances(request.id); const completed = acceptances.filter((item) => item.status === "fulfilled").length; return `<article class="request-card"><div class="request-card-top"><div class="request-title"><span class="blood-badge">${escapeHTML(request.blood_group_needed)}</span><div><h3>${escapeHTML(request.hospital_name)}</h3><span class="muted">Completed ${formatDate(request.fulfilled_at || request.created_at)}</span></div></div>${statusPill("fulfilled")}</div><div class="request-card-meta"><span>${escapeHTML(request.units_needed)} UNIT${request.units_needed === 1 ? "" : "S"}</span><span>${escapeHTML(request.urgency).toUpperCase()}</span><span>${completed} CONFIRMED DONATION${completed === 1 ? "" : "S"}</span><span>ID ${escapeHTML(request.id.slice(0, 8))}</span></div><div class="request-card-footer"><span class="response-summary">Completed request record</span><button class="secondary-button" type="button" data-action="open-details" data-request-id="${escapeAttribute(request.id)}">View record</button></div></article>`; }).join("")}</section>` : emptyState("No fulfilled requests yet", "Completed donor confirmations will appear here after the hospital confirms the donation.")}`;
}

function journeyState(request, acceptances) {
  if (request.status === "fulfilled") return 5;
  if (acceptances.some((item) => item.status === "pending")) return 3;
  if (request.status === "matching") return 2;
  return 1;
}

function timelineStep(index, current, title, copy) {
  const status = index < current ? "complete" : index === current ? "current" : "";
  const symbol = index < current ? "✓" : index === current ? "•" : index;
  return `<div class="timeline-step ${status}"><span class="timeline-dot">${symbol}</span><div><h3>${title}</h3><p>${copy}</p></div></div>`;
}

function renderDetails() {
  const request = state.requests.find((item) => item.id === state.selectedRequestId);
  if (!request) return `${pageHeading("INCIDENT CENTER", "Request unavailable", "The selected request could not be found in the latest data.")}${emptyState("Request unavailable", "Return to emergency requests and choose another incident.", "View requests")}`;
  const acceptances = getAcceptances(request.id);
  const matches = getMatches(request.id);
  const pending = acceptances.filter((item) => item.status === "pending");
  const phase = journeyState(request, acceptances);
  return `<button class="back-link" type="button" data-action="page" data-page="requests">← Back to emergency requests</button><section class="details-header"><div class="details-title-row"><div class="details-title"><span class="blood-badge">${escapeHTML(request.blood_group_needed)}</span><div><p class="eyebrow">EMERGENCY REQUEST</p><h1>${escapeHTML(request.units_needed)} unit${request.units_needed === 1 ? "" : "s"} of ${escapeHTML(request.blood_group_needed)}</h1><p class="details-subtitle">${escapeHTML(request.hospital_name)} · Request ID ${escapeHTML(request.id.slice(0, 8))}</p></div></div><div class="details-actions"><button class="secondary-button" type="button" data-action="rematch" data-request-id="${escapeAttribute(request.id)}">Rematch donors</button>${request.status !== "fulfilled" ? `<button class="primary-button" type="button" data-action="open-responses" data-request-id="${escapeAttribute(request.id)}">View responses</button>` : ""}</div></div><div class="details-info"><span>${urgencyPill(request.urgency)}</span><span>${statusPill(request.status)}</span><span>${escapeHTML(request.current_radius_km)} KM SEARCH RADIUS</span><span>${escapeHTML(request.eta_window_minutes)} MIN RESPONSE ETA</span><span>CREATED ${escapeHTML(formatDate(request.created_at))}</span></div></section><section class="details-grid"><article class="panel"><header class="panel-header"><div><h2>Incident timeline</h2><p class="panel-kicker">Only backend-confirmed milestones are marked active.</p></div></header><div class="incident-stats"><div class="incident-stat"><strong>${matches.length}</strong><span>ELIGIBLE MATCHES</span></div><div class="incident-stat"><strong>${pending.length}</strong><span>ACTIVE RESPONSES</span></div><div class="incident-stat"><strong>${request.eta_window_minutes}m</strong><span>RESPONSE ETA</span></div></div><div class="timeline">${timelineStep(1, phase, "Request created", formatDate(request.created_at))}${timelineStep(2, phase, "Matching donors", `${matches.length} eligible compatible donor match${matches.length === 1 ? "" : "es"} in the current radius`)}${timelineStep(3, phase, "Donor accepted", pending.length ? `${pending.length} confirmed response${pending.length === 1 ? "" : "s"} awaiting hospital confirmation` : "Awaiting an eligible donor response")}${timelineStep(4, phase, "On the way", "Awaiting a backend-connected donor journey update")}${timelineStep(5, phase, "Arrived / completed", request.status === "fulfilled" ? "Donation confirmed by the hospital" : "Completion has not been confirmed")}</div><p class="journey-note">The locked mobile app currently keeps On the way and Arrived as local UI state. This dashboard deliberately does not present them as confirmed hospital data.</p></article><article class="panel map-panel"><header class="panel-header"><div><h2>Request location</h2><p class="panel-kicker">Hospital request point and active search radius</p></div></header><div id="request-map" class="map-canvas"><div class="map-fallback">Loading location preview…</div></div><div class="map-caption"><span>Coordinates stored with request</span><strong>${Number(request.latitude).toFixed(4)}, ${Number(request.longitude).toFixed(4)}</strong></div></article><article class="panel"><header class="panel-header"><div><h2>Eligible donor matches</h2><p class="panel-kicker">Privacy-minimized current matching pool</p></div><span class="count-pill">${matches.length}</span></header><div class="match-list">${matches.length ? matches.map(renderMatchCard).join("") : '<p class="muted">No eligible donors are currently available at this request’s active search radius.</p>'}</div></article><article class="panel"><header class="panel-header"><div><h2>Accepted responses</h2><p class="panel-kicker">Confirm a donation only after in-person verification.</p></div><span class="count-pill">${acceptances.length}</span></header><div class="response-list">${acceptances.length ? acceptances.map((item) => renderResponseCard(item, request)).join("") : '<p class="muted">No donor has accepted this request yet.</p>'}</div></article></section>`;
}

function renderSettings() {
  return `${pageHeading("WORKSPACE PREFERENCES", "Hospital Settings", "Set the lightweight demo identity used when creating requests. This is not production authentication.")}${errorBanner()}<section class="overview-grid"><article class="panel"><header class="panel-header"><div><h2>Hospital profile</h2><p class="panel-kicker">Saved locally in this browser for the demo workspace.</p></div></header><form id="settings-form" class="form-grid"><div class="form-field full"><label for="settings-name">HOSPITAL NAME</label><input id="settings-name" name="name" required minlength="2" maxlength="160" value="${escapeAttribute(state.hospital.name)}" /></div><div class="form-field"><label for="settings-lat">DEFAULT LATITUDE</label><input id="settings-lat" name="latitude" required type="number" min="-90" max="90" step="0.0001" value="${escapeAttribute(state.hospital.latitude)}" /></div><div class="form-field"><label for="settings-lng">DEFAULT LONGITUDE</label><input id="settings-lng" name="longitude" required type="number" min="-180" max="180" step="0.0001" value="${escapeAttribute(state.hospital.longitude)}" /></div><div class="dialog-footer form-field full"><button class="primary-button" type="submit">Save workspace preferences</button></div></form></article><aside class="panel pulse-panel"><p class="eyebrow">DEMO STATUS</p><h2>Identity is local</h2><p class="panel-kicker">The current FastAPI backend does not have hospital accounts or authorization.</p><div class="system-list"><div class="system-row"><span>Hospital identity</span><strong class="system-state">LOCAL</strong></div><div class="system-row"><span>Request API</span><strong class="system-state">REUSED</strong></div><div class="system-row"><span>Production authentication</span><strong class="system-state">FUTURE</strong></div></div><p class="compliance-note">No credentials or secrets are stored in the frontend.</p></aside></section>`;
}

function renderPage() {
  if (state.loading) return renderLoading();
  if (state.page === "requests") return renderRequests();
  if (state.page === "matches") return renderMatches();
  if (state.page === "responses") return renderResponses();
  if (state.page === "history") return renderHistory();
  if (state.page === "settings") return renderSettings();
  if (state.page === "details") return renderDetails();
  return renderOverview();
}

function render() {
  app.innerHTML = renderShell(renderPage());
  if (state.page === "details" && !state.loading) setTimeout(initRequestMap, 0);
}

function openDialog(title, content, eyebrow = "REDSYNC OPERATIONS") {
  dialogEyebrow.textContent = eyebrow;
  dialogTitle.textContent = title;
  dialogContent.innerHTML = content;
  if (!dialog.open) dialog.showModal();
}

function closeDialog() {
  if (dialog.open) dialog.close();
}

function showToast(title, message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast ${type === "error" ? "error" : ""}`;
  toast.innerHTML = `<span class="toast-icon">${type === "error" ? "!" : "✓"}</span><div><strong>${escapeHTML(title)}</strong><span>${escapeHTML(message)}</span></div>`;
  toastRegion.append(toast);
  setTimeout(() => toast.remove(), 4800);
}

function openRequestForm() {
  openDialog("Create emergency request", `<form id="request-form"><div class="form-grid"><div class="form-field"><label for="request-blood">BLOOD GROUP</label><select id="request-blood" name="blood_group_needed" required>${["O-", "O+", "A-", "A+", "B-", "B+", "AB-", "AB+"].map((group) => `<option value="${group}">${group}</option>`).join("")}</select></div><div class="form-field"><label for="request-units">UNITS REQUIRED</label><input id="request-units" name="units_needed" type="number" min="1" max="100" value="1" required /></div><div class="form-field"><label for="request-urgency">URGENCY</label><select id="request-urgency" name="urgency" required><option value="critical">Critical — immediate</option><option value="urgent" selected>Urgent — within hours</option><option value="standard">Normal — planned</option></select></div><div class="form-field"><label for="request-eta">RESPONSE ETA WINDOW (MIN)</label><input id="request-eta" name="eta_window_minutes" type="number" min="5" max="1440" value="45" required /></div><div class="form-field full"><label for="request-hospital">HOSPITAL NAME</label><input id="request-hospital" name="hospital_name" minlength="2" maxlength="160" required value="${escapeAttribute(state.hospital.name)}" /></div><div class="form-field"><label for="request-lat">LATITUDE</label><div class="location-inline"><input id="request-lat" name="latitude" type="number" min="-90" max="90" step="0.0001" required value="${escapeAttribute(state.hospital.latitude)}" /><button class="secondary-button" type="button" data-action="locate">Use GPS</button></div></div><div class="form-field"><label for="request-lng">LONGITUDE</label><input id="request-lng" name="longitude" type="number" min="-180" max="180" step="0.0001" required value="${escapeAttribute(state.hospital.longitude)}" /></div><div class="form-field full"><label for="request-notes">CLINICAL NOTES (OPTIONAL)</label><textarea id="request-notes" name="notes" maxlength="2000" placeholder="Relevant request details for the response team"></textarea></div></div><p class="form-helper">Search radius is managed by the existing matching engine: 5 km, then 10 km, then 20 km if needed. Creating this request immediately begins matching.</p><div class="dialog-footer"><button class="secondary-button" type="button" data-action="close-dialog">Cancel</button><button class="primary-button" type="submit">Create request & find donors</button></div></form>`, "NEW EMERGENCY");
}

function showRequestCreated(request) {
  openDialog("Request created", `<div class="success-state"><div class="success-mark">✓</div><p class="eyebrow">REQUEST CREATED</p><h3>Matching has started.</h3><div class="success-request">${escapeHTML(request.blood_group_needed)} · ${escapeHTML(request.units_needed)} UNIT${request.units_needed === 1 ? "" : "S"}</div><p>Finding compatible nearby donors through the configured matching radius. The incident workspace will refresh as backend-confirmed responses arrive.</p><div class="dialog-footer"><button class="primary-button" type="button" data-action="view-created" data-request-id="${escapeAttribute(request.id)}">Open incident center</button></div></div>`, "EMERGENCY CREATED");
}

function openNotifications() {
  openDialog("Operations notifications", `<div class="success-state"><div class="success-mark">⌁</div><p class="eyebrow">SYSTEM MONITORING</p><h3>Data refresh is active.</h3><p>The dashboard refreshes active requests, donor matches, and acceptances every 12 seconds while the workspace is open. SMS/push delivery is not configured in the current backend.</p><div class="dialog-footer"><button class="primary-button" type="button" data-action="close-dialog">Continue</button></div></div>`, "REDSYNC STATUS");
}

async function submitRequest(form) {
  const data = new FormData(form);
  const payload = {
    hospital_name: String(data.get("hospital_name") || "").trim(),
    blood_group_needed: data.get("blood_group_needed"),
    units_needed: Number(data.get("units_needed")),
    urgency: data.get("urgency"),
    latitude: Number(data.get("latitude")),
    longitude: Number(data.get("longitude")),
    eta_window_minutes: Number(data.get("eta_window_minutes")),
    notes: String(data.get("notes") || "").trim() || null,
  };
  const submit = form.querySelector('button[type="submit"]');
  submit.disabled = true;
  submit.textContent = "Creating request…";
  try {
    const request = await api("/requests/", { method: "POST", body: JSON.stringify(payload) });
    state.selectedRequestId = request.id;
    state.page = "details";
    await refreshData(false);
    showToast("Emergency request created", `${request.blood_group_needed} · ${request.units_needed} unit${request.units_needed === 1 ? "" : "s"} is now matching donors.`);
    showRequestCreated(request);
  } catch (error) {
    showToast("Request could not be created", error.message || "Please review the request details and try again.", "error");
    submit.disabled = false;
    submit.textContent = "Create request & find donors";
  }
}

async function rematch(requestId) {
  const request = state.requests.find((item) => item.id === requestId);
  if (!request || !window.confirm(`Run the matching engine again for ${request.blood_group_needed} at ${request.hospital_name}? Eligible donors may be notified again.`)) return;
  try {
    const candidates = await api(`/requests/${encodeURIComponent(requestId)}/rematch`, { method: "POST" });
    state.matches[requestId] = [];
    await refreshData(false);
    showToast("Donor rematch completed", `${candidates.length} eligible candidate${candidates.length === 1 ? "" : "s"} found at the active radius.`);
  } catch (error) {
    showToast("Rematch could not run", error.message || "Please try again.", "error");
  }
}

async function fulfillAcceptance(acceptanceId) {
  if (!window.confirm("Confirm that this donor arrived and completed the donation? This fulfills the request and stands down other pending responses.")) return;
  try {
    await api(`/acceptances/${encodeURIComponent(acceptanceId)}/fulfill`, { method: "POST" });
    await refreshData(false);
    showToast("Donation confirmed", "The request is fulfilled and other pending responses were stood down.");
  } catch (error) {
    showToast("Donation could not be confirmed", error.message || "Please try again.", "error");
  }
}

function locateRequest() {
  if (!navigator.geolocation) {
    showToast("Location unavailable", "This browser does not provide location services.", "error");
    return;
  }
  navigator.geolocation.getCurrentPosition((position) => {
    const latitude = document.getElementById("request-lat");
    const longitude = document.getElementById("request-lng");
    if (latitude) latitude.value = position.coords.latitude.toFixed(6);
    if (longitude) longitude.value = position.coords.longitude.toFixed(6);
    showToast("Location updated", "The emergency request will use this browser location.");
  }, () => showToast("Location unavailable", "Use the stored hospital coordinates or enter a location manually.", "error"), { enableHighAccuracy: true, timeout: 8000 });
}

function saveSettings(form) {
  const data = new FormData(form);
  const name = String(data.get("name") || "").trim();
  const latitude = Number(data.get("latitude"));
  const longitude = Number(data.get("longitude"));
  if (name.length < 2 || !Number.isFinite(latitude) || latitude < -90 || latitude > 90 || !Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
    showToast("Settings need attention", "Enter a hospital name and valid latitude/longitude values.", "error");
    return;
  }
  state.hospital = { name, latitude, longitude };
  saveHospital();
  showToast("Workspace preferences saved", "The hospital identity is stored locally in this browser.");
  render();
}

function initRequestMap() {
  const mapElement = document.getElementById("request-map");
  const request = state.requests.find((item) => item.id === state.selectedRequestId);
  if (!mapElement || !request) return;
  if (state.map) {
    try { state.map.remove(); } catch (_) { /* A removed map is safe to ignore. */ }
    state.map = null;
  }
  if (!window.L) {
    mapElement.innerHTML = '<div class="map-fallback">Map tiles are unavailable. Request location remains available in the incident record.</div>';
    return;
  }
  try {
    const lat = Number(request.latitude);
    const lng = Number(request.longitude);
    state.map = window.L.map(mapElement, { zoomControl: false, scrollWheelZoom: false }).setView([lat, lng], 12);
    window.L.control.zoom({ position: "bottomright" }).addTo(state.map);
    window.L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "© OpenStreetMap contributors" }).addTo(state.map);
    window.L.circle([lat, lng], { radius: Number(request.current_radius_km) * 1000, color: "#c92636", weight: 2, fillColor: "#c92636", fillOpacity: .08 }).addTo(state.map);
    window.L.marker([lat, lng]).addTo(state.map).bindPopup(`<strong>${escapeHTML(request.hospital_name)}</strong><br>Emergency request location`).openPopup();
  } catch (_) {
    mapElement.innerHTML = '<div class="map-fallback">Location preview could not be displayed. The incident workspace remains available.</div>';
  }
}

document.addEventListener("click", async (event) => {
  const control = event.target.closest("[data-action]");
  if (!control) return;
  const action = control.dataset.action;
  if (action === "page") {
    event.preventDefault();
    state.page = control.dataset.page;
    if (state.page !== "details") state.selectedRequestId = null;
    await refreshData(false);
  } else if (action === "create-request") openRequestForm();
  else if (action === "close-dialog") closeDialog();
  else if (action === "retry") refreshData(true);
  else if (action === "filter") { state.requestFilter = control.dataset.filter; render(); }
  else if (action === "open-details") { state.selectedRequestId = control.dataset.requestId; state.page = "details"; await refreshData(false); }
  else if (action === "view-created") { state.selectedRequestId = control.dataset.requestId; state.page = "details"; closeDialog(); await refreshData(false); }
  else if (action === "rematch") rematch(control.dataset.requestId);
  else if (action === "fulfill") fulfillAcceptance(control.dataset.acceptanceId);
  else if (action === "open-responses") { state.selectedRequestId = control.dataset.requestId; state.page = "responses"; await refreshData(false); }
  else if (action === "locate") locateRequest();
  else if (action === "notifications") openNotifications();
});

document.addEventListener("input", (event) => {
  if (event.target.matches("[data-search='requests']")) {
    state.requestSearch = event.target.value;
    const results = document.getElementById("request-results");
    if (results) {
      const requests = filteredRequests();
      results.innerHTML = requests.length ? requests.map(renderRequestCard).join("") : emptyState("No requests match this view", "Try another filter or create a new emergency request.");
    }
  }
});

document.addEventListener("submit", (event) => {
  if (event.target.id === "request-form") { event.preventDefault(); submitRequest(event.target); }
  if (event.target.id === "settings-form") { event.preventDefault(); saveSettings(event.target); }
});

dialog.addEventListener("click", (event) => {
  if (event.target === dialog) closeDialog();
});

render();
refreshData(true);
setInterval(() => {
  const typing = document.activeElement && document.activeElement.matches("input, textarea, select");
  if (!dialog.open && !typing) refreshData(false);
}, 12000);
