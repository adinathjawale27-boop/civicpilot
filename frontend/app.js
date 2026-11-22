const state = {
  view: "landing",
  schemes: [],
  dashboard: null,
  applications: [],
  currentApplication: null,
  selectedSchemeId: "",
  selectedApplicationId: "",
  chatLanguage: "en",
  chatHistory: [],
  eligibilityResult: null,
  checklist: null,
  uploads: [],
  lastAsk: null,
  lastPrepare: null,
  lastApprove: null,
  loading: {},
  filterCategory: "all",
  searchQuery: "",
  isSimulating: false,
};

const DEMO_PROFILES = {
  eligible: {
    label: "Asha Patel (Eligible - MH, 78%, ₹1.8L)",
    scheme_id: "maha-merit-demo",
    name: "Asha Patel",
    email: "asha.patel@example.com",
    state: "Maharashtra",
    family_income: "180000",
    percentage: "78.2",
    current_level: "undergraduate",
    study_field: "Computer Science & Engineering (STEM)",
    gender: "female",
  },
  stem: {
    label: "Rahul Deshmukh (STEM Access - 84%, ₹2.4L)",
    scheme_id: "stem-access-demo",
    name: "Rahul Deshmukh",
    email: "rahul.stem@example.com",
    state: "Maharashtra",
    family_income: "240000",
    percentage: "84.5",
    current_level: "undergraduate",
    study_field: "Artificial Intelligence & Data Science (STEM)",
    gender: "male",
  },
  girls: {
    label: "Sneha Kulkarni (Pragati Girl - Diploma, 68%)",
    scheme_id: "pragati-girls-demo",
    name: "Sneha Kulkarni",
    email: "sneha.k@example.com",
    state: "Maharashtra",
    family_income: "160000",
    percentage: "68.0",
    current_level: "diploma",
    study_field: "Civil Engineering",
    gender: "female",
  },
  ineligible: {
    label: "Vikram Sharma (Ineligible - Income ₹5.2L)",
    scheme_id: "maha-merit-demo",
    name: "Vikram Sharma",
    email: "vikram@example.com",
    state: "Goa",
    family_income: "520000",
    percentage: "52.0",
    current_level: "12",
    study_field: "Commerce",
    gender: "male",
  },
};

const VIEWS = [
  { id: "landing", label: "Landing Page" },
  { id: "dashboard", label: "User Dashboard" },
  { id: "assistant", label: "AI Chat Assistant" },
  { id: "scholarships", label: "Scholarship Explorer" },
  { id: "eligibility", label: "Eligibility Checker" },
  { id: "documents", label: "Document Upload" },
  { id: "prepare", label: "Application Preparation" },
  { id: "automation", label: "Browser Automation Status" },
  { id: "tracking", label: "Application Tracking" },
  { id: "about", label: "About CivicPilot AI" },
];

function $(s, r = document) { return r.querySelector(s); }
function esc(v) { return String(v ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function fmtDate(v) { if (!v) return "—"; const d = new Date(v); return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString(); }
function toast(message, type = "info") {
  const region = $("#toast-region"); if (!region) return;
  const el = document.createElement("div"); el.className = `toast ${type}`;
  el.innerHTML = `<div><b>${esc(type === "error" ? "Error" : type === "success" ? "Success" : "Notice")}</b><p style="margin:2px 0 0">${esc(message)}</p></div><button onclick="this.parentElement.remove()" style="margin-left:auto;border:0;background:none;cursor:pointer">×</button>`;
  region.appendChild(el); setTimeout(() => el.remove(), 4500);
}
function setLoading(k, v) { state.loading[k] = v; render(); }
function progressPct(app) {
  if (!app) return 0;
  if (app.progress && typeof app.progress === "object") {
    const total = app.progress.total || 0; return total ? Math.round((app.progress.completed / total) * 100) : 0;
  }
  if (Array.isArray(app.steps) && app.steps.length) {
    const done = app.steps.filter(s => s.status === "completed").length; return Math.round((done / app.steps.length) * 100);
  }
  return 0;
}
function progressText(app) {
  if (app?.progress && typeof app.progress === "object") return `${app.progress.completed}/${app.progress.total} steps`;
  if (Array.isArray(app?.steps)) return `${app.steps.filter(s=>s.status==='completed').length}/${app.steps.length} steps`;
  return "—";
}
function getScheme(id) { return state.schemes.find(s => s.id === id) || null; }
function currentApp() { return state.currentApplication || state.applications.find(a => a.id === state.selectedApplicationId) || null; }

async function api(path, options = {}) {
  const opts = { ...options }; opts.headers = { ...(options.headers || {}) };
  if (opts.body && !(opts.body instanceof FormData) && !opts.headers["Content-Type"]) {
    opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(opts.body);
  }
  const res = await fetch(`/api${path}`, opts);
  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = data && typeof data === "object" ? (data.detail || data.error || data.message || JSON.stringify(data)) : String(data || res.statusText);
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

async function loadCore() {
  const [schemesRes, dashRes, appsRes] = await Promise.all([api("/schemes"), api("/dashboard"), api("/applications")]);
  state.schemes = schemesRes.schemes || [];
  state.dashboard = dashRes || null;
  state.applications = appsRes.applications || [];
  if (!state.selectedSchemeId && state.schemes.length) state.selectedSchemeId = state.schemes[0].id;
  if (state.selectedApplicationId) {
    try { await refreshApplication(state.selectedApplicationId, false); } catch (_) {}
  } else if (state.applications.length) {
    state.selectedApplicationId = state.applications[0].id;
  }
}

async function refreshApplication(id, rerender = true) {
  const res = await api(`/applications/${encodeURIComponent(id)}`);
  state.currentApplication = res.application || res;
  const idx = state.applications.findIndex(a => a.id === id);
  if (idx >= 0) {
    const a = state.currentApplication;
    state.applications[idx] = {
      ...state.applications[idx],
      id: a.id,
      scheme_id: a.scheme_id,
      scheme_name: a.scheme?.name || state.applications[idx].scheme_name,
      status: a.status,
      demo_reference: a.demo_reference,
      updated_at: a.updated_at,
      created_at: a.created_at,
      progress: progressFromSteps(a.steps),
      applicant_name: a.applicant?.name,
    };
  }
  if (rerender) render();
  return state.currentApplication;
}

function progressFromSteps(steps = []) {
  return { completed: steps.filter(s => s.status === 'completed').length, total: steps.length };
}

function navigate(view) {
  if (!VIEWS.some(v => v.id === view)) view = "landing";
  location.hash = `#${view}`;
}

function onHashChange() {
  const raw = (location.hash || "#landing").replace("#", "").trim();
  state.view = VIEWS.some(v => v.id === raw) ? raw : "landing";
  render();
}

function appShellMode() {
  const landing = state.view === "landing";
  $("#landing-root")?.classList.toggle("hidden", !landing);
  $("#app-shell")?.classList.toggle("hidden", landing);
}

function setBreadcrumb() {
  const meta = VIEWS.find(v => v.id === state.view) || VIEWS[0];
  const crumb = $("#breadcrumb-current");
  if (crumb) crumb.textContent = meta.label;
  document.querySelectorAll(".nav-item").forEach(el => {
    const active = el.dataset.view === state.view;
    el.classList.toggle("active", active);
    if (active) el.setAttribute("aria-current", "page");
    else el.removeAttribute("aria-current");
  });
}

function schemeOptions(selected = state.selectedSchemeId) {
  return state.schemes.map(s => `<option value="${esc(s.id)}" ${s.id === selected ? "selected" : ""}>${esc(s.name)}</option>`).join("");
}

function sourcesBlock(sources = []) {
  if (!sources || !sources.length) return `<p class="helper">No document references returned.</p>`;
  return `<div class="sources-drawer" style="margin-top:8px;padding:8px 10px;background:#eef4fb;border-radius:6px;border-left:3px solid var(--blue-600)"><b style="font-size:11px;color:var(--navy-800)">Verified Document Sources:</b><ul class="mini-list" style="margin:4px 0 0">${sources.map(s => `<li><b>${esc(s.reference || "Reference")}:</b> ${esc(String(s.content || "").slice(0, 220))}${String(s.content || "").length > 220 ? "…" : ""}</li>`).join("")}</ul></div>`;
}

function formObj(form) {
  const fd = new FormData(form);
  const o = {};
  for (const [k, v] of fd.entries()) o[k] = typeof v === 'string' ? v.trim() : v;
  return o;
}

function render() {
  setBreadcrumb();
  appShellMode();
  if (state.view === "landing") {
    $("#landing-root").innerHTML = renderLanding();
    bindViewEvents();
    return;
  }
  const root = $("#view-root");
  if (!root) return;
  const map = {
    dashboard: renderDashboard,
    assistant: renderAssistant,
    scholarships: renderScholarships,
    eligibility: renderEligibility,
    documents: renderDocuments,
    prepare: renderPrepare,
    automation: renderAutomation,
    tracking: renderTracking,
    about: renderAbout,
  };
  root.innerHTML = (map[state.view] || renderDashboard)();
  bindViewEvents();
}

function renderLanding() {
  const cards = state.schemes.map(s => `
    <article class="scheme-card card">
      <div class="scheme-card-top">
        <div class="scheme-seal"><svg><use href="#i-book"/></svg></div>
        <span class="chip ${s.category?.includes('Women') ? 'purple' : s.category?.includes('STEM') ? 'blue' : 'green'}">${esc(s.category || 'Scholarship')}</span>
      </div>
      <h2>${esc(s.name)}</h2>
      <p>${esc(s.short_description || '')}</p>
      <div class="scheme-meta">
        <div><label>Benefit</label><b>${esc(s.benefit || 'Grant')}</b></div>
        <div><label>Deadline</label><b>${esc(s.deadline || '2026-12-31')}</b></div>
      </div>
      <div class="button-row">
        <button class="button primary small" data-scheme="${esc(s.id)}" data-go="eligibility">Check Eligibility</button>
        <button class="button secondary small" data-scheme="${esc(s.id)}" data-go="assistant">Ask AI</button>
      </div>
    </article>
  `).join("") || `<div class="card card-pad">Loading demo schemes…</div>`;

  return `
    <div class="landing-nav">
      <a class="brand" href="#landing">
        <span class="brand-mark"><svg><use href="#i-spark"/></svg></span>
        <span>CivicPilot <b>AI</b></span>
      </a>
      <div class="landing-links">
        <button class="button secondary small" data-go="dashboard">Open Dashboard</button>
        <button class="button primary small" data-go="assistant"><svg><use href="#i-chat"/></svg> Ask AI Assistant</button>
      </div>
    </div>

    <section class="landing-hero">
      <div>
        <div class="hero-pill-badge">
          <span class="pulsing-dot"></span>
          <span>Civic Pulse · Next-Gen Digital Governance</span>
        </div>
        <h1>Your <span class="text-gradient">Intelligent Government Service</span> Assistant.</h1>
        <p>CivicPilot AI empowers students and citizens to understand public schemes, evaluate deterministic eligibility with mathematical precision, extract document certificates, and experience a safe local Playwright automation workflow.</p>
        
        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:24px">
          <button class="button primary" style="padding:0 24px;min-height:46px;font-size:14px" data-profile="eligible" data-go="eligibility">
            ⚡ Test Live Demo (Asha - 78%) <svg><use href="#i-arrow"/></svg>
          </button>
          <button class="button secondary" style="padding:0 22px;min-height:46px;font-size:14px" data-go="dashboard">
            Explore Dashboard
          </button>
        </div>

        <div style="margin-top:20px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <span style="font-size:11px;font-weight:700;color:#94a3b8">Instant 1-Click Test Profiles:</span>
          <button class="button secondary small" style="background:rgba(255,255,255,.1);color:#fff;border-color:rgba(255,255,255,.2)" data-profile="eligible" data-go="eligibility">🟢 Asha (Eligible)</button>
          <button class="button secondary small" style="background:rgba(255,255,255,.1);color:#fff;border-color:rgba(255,255,255,.2)" data-profile="stem" data-go="eligibility">🔵 Rahul (STEM)</button>
          <button class="button secondary small" style="background:rgba(255,255,255,.1);color:#fff;border-color:rgba(255,255,255,.2)" data-profile="girls" data-go="eligibility">🟣 Sneha (Pragati)</button>
        </div>

        <p class="helper" style="margin-top:16px;color:#94a3b8">
          🔒 Fictional demonstration only · Local simulated testbed · Two-step human review gates required before submission.
        </p>
      </div>

      <div class="landing-card">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px">
          <h3 style="color:#fff;margin:0;font-size:17px">End-to-End Governance Pipeline</h3>
          <span class="status-tag green" style="background:rgba(16,185,129,.2);color:#34d399"><i></i> Live Sandbox</span>
        </div>
        <ul class="mini-list" style="color:#e2e8f0;gap:12px">
          <li>
            <b style="color:#60a5fa">1. Grounded Multi-Lingual RAG:</b>
            <div style="color:#cbd5e1;font-size:11px">Conversational scheme assistant in English, हिन्दी, and मराठी with verified citations.</div>
          </li>
          <li>
            <b style="color:#34d399">2. Deterministic Eligibility Checker:</b>
            <div style="color:#cbd5e1;font-size:11px">Deterministic rule-by-rule visual checks for income caps, domicile, and academic thresholds.</div>
          </li>
          <li>
            <b style="color:#f472b6">3. Intelligent Document Extraction:</b>
            <div style="color:#cbd5e1;font-size:11px">PyMuPDF / OCR text extraction with instant sample generators & checklist reconciliation.</div>
          </li>
          <li>
            <b style="color:#a78bfa">4. Local Playwright Automation:</b>
            <div style="color:#cbd5e1;font-size:11px">Headless browser form pre-fill with strict 2-step explicit human sign-off gates.</div>
          </li>
        </ul>
      </div>
    </section>

    <section class="landing-stats">
      <div class="landing-stat"><b>${esc(state.schemes.length || 3)}</b><span>Seeded Demonstration Schemes</span></div>
      <div class="landing-stat"><b>3 Languages</b><span>English, हिन्दी & मराठी</span></div>
      <div class="landing-stat"><b>100% Deterministic</b><span>Rule-Based Decisions</span></div>
      <div class="landing-stat"><b>Playwright</b><span>Local Headless Simulation</span></div>
    </section>

    <section class="landing-sections">
      ${cards}
    </section>
  `;
}

function renderDashboard() {
  const d = state.dashboard || {};
  const apps = state.applications || [];
  const recent = (d.recent_activity || []).slice(0, 6);
  const pending = apps.filter(a => a.status !== 'demo_submitted');
  const submitted = apps.filter(a => a.status === 'demo_submitted');

  return `
  <section class="view">
    <div class="hero-panel">
      <div class="hero-content">
        <div class="hero-kicker"><svg><use href="#i-spark"/></svg> Intelligently Guided Public Services</div>
        <h1>Welcome to CivicPilot AI</h1>
        <p>Explore government schemes, evaluate deterministic eligibility, upload/extract documents, and safely test the local automated portal simulation.</p>
        <div class="hero-actions">
          <button class="button primary" data-profile="eligible" data-go="eligibility">⚡ Quick Test: Asha Patel (Eligible)</button>
          <button class="button secondary" data-go="documents"><svg><use href="#i-upload"/></svg> Test Sample Documents</button>
        </div>
      </div>
    </div>

    <div class="stat-grid">
      <article class="card stat-card" style="--stat-tint:var(--blue-50);--stat-color:var(--blue-600)">
        <div class="stat-icon"><svg><use href="#i-book"/></svg></div>
        <div class="stat-value">${esc(d.scheme_count ?? state.schemes.length)}</div>
        <div class="stat-label">Available Government Schemes</div>
      </article>
      <article class="card stat-card" style="--stat-tint:var(--amber-50);--stat-color:var(--amber-700)">
        <div class="stat-icon"><svg><use href="#i-file"/></svg></div>
        <div class="stat-value">${esc(d.pending_application_count ?? pending.length)}</div>
        <div class="stat-label">In-Progress / Draft Applications</div>
      </article>
      <article class="card stat-card" style="--stat-tint:var(--green-50);--stat-color:var(--green-700)">
        <div class="stat-icon"><svg><use href="#i-shield"/></svg></div>
        <div class="stat-value">${esc(d.submitted_application_count ?? submitted.length)}</div>
        <div class="stat-label">Simulated Acknowledged Submissions</div>
      </article>
      <article class="card stat-card" style="--stat-tint:var(--purple-100);--stat-color:var(--purple-700)">
        <div class="stat-icon"><svg><use href="#i-folder"/></svg></div>
        <div class="stat-value">${esc(d.document_count ?? 0)}</div>
        <div class="stat-label">Extracted & Verified Documents</div>
      </article>
    </div>

    <div class="card card-pad" style="margin-top:18px;background:#f8fafc;border:1px solid #cbd5e1;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap">
      <div style="display:flex;align-items:center;gap:10px">
        <div style="font-size:22px">⚡</div>
        <div>
          <b style="font-size:13px;color:var(--navy-800)">Interactive Demo Profiles (Instant 1-Click Evaluation):</b>
          <p class="helper" style="margin:2px 0 0">Test real-time deterministic eligibility checks for diverse student scenarios</p>
        </div>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button class="button secondary small" data-profile="eligible" data-go="eligibility">🟢 Asha (Eligible · 78%)</button>
        <button class="button secondary small" data-profile="stem" data-go="eligibility">🔵 Rahul (STEM · 84%)</button>
        <button class="button secondary small" data-profile="girls" data-go="eligibility">🟣 Sneha (Pragati · 68%)</button>
        <button class="button secondary small" data-profile="ineligible" data-go="eligibility">🔴 Vikram (Ineligible · ₹5.2L)</button>
      </div>
    </div>

    <div class="overview-grid">
      <article class="card progress-card">
        <div class="section-title">
          <div>
            <h2>Application Progress</h2>
            <p>Track your local draft applications and demo acknowledgements.</p>
          </div>
          <button class="button secondary small" data-go="tracking">View All Tracking</button>
        </div>
        <div>
          ${apps.slice(0, 4).map(a => `
            <div class="application-summary">
              <div class="app-emblem ${a.status === 'demo_submitted' ? 'green' : 'blue'}">
                <svg><use href="#i-file"/></svg>
              </div>
              <div class="app-main">
                <b>${esc(a.scheme_name || a.scheme_id)}</b>
                <small>${esc(a.applicant_name || 'Applicant')} · Reference: <span class="mono">${esc(a.demo_reference || 'Draft')}</span></small>
              </div>
              <div class="app-right">
                <span class="status-tag ${a.status === 'demo_submitted' ? 'green' : 'amber'}">
                  <i></i> ${esc(a.status === 'demo_submitted' ? 'Acknowledged' : a.status === 'demo_prepared' ? 'Demo Prepared' : 'Draft')}
                </span>
                <div class="progress-mini"><i style="width:${progressPct(a)}%"></i></div>
                <span>${progressPct(a)}% complete</span>
              </div>
            </div>
          `).join('') || '<p class="helper">No applications created yet. Start by checking eligibility or loading a demo profile.</p>'}
        </div>
      </article>

      <article class="card activity-card">
        <div class="section-title">
          <div>
            <h2>Recent Activity</h2>
            <p>Audit trail of local actions and verifications.</p>
          </div>
        </div>
        <ul class="activity-list">
          ${recent.map(a => `
            <li class="activity-item">
              <div class="activity-bullet ${a.action.includes('approved') || a.action.includes('submitted') ? 'green' : 'blue'}">
                <svg><use href="#i-check"/></svg>
              </div>
              <div>
                <b>${esc(a.action.replace(/_/g, ' ').toUpperCase())}</b>
                <p>${esc(typeof a.details === 'object' ? JSON.stringify(a.details).slice(0, 100) : a.details)}</p>
                <time>${esc(fmtDate(a.created_at))}</time>
              </div>
            </li>
          `).join('') || '<li class="helper">No recent activity logged yet.</li>'}
        </ul>
      </article>
    </div>

    <div class="card card-pad" style="margin-top:18px">
      <div class="section-title">
        <div>
          <h2>Available Scholarship Programs</h2>
          <p>Click any scheme to test deterministic rules or chat with the AI assistant.</p>
        </div>
        <button class="button secondary small" data-go="scholarships">Explore All</button>
      </div>
      <div class="scheme-grid">
        ${state.schemes.map(s => `
          <div class="card scheme-card">
            <div class="scheme-card-top">
              <div class="scheme-seal"><svg><use href="#i-book"/></svg></div>
              <span class="chip ${s.category?.includes('Women') ? 'purple' : s.category?.includes('STEM') ? 'blue' : 'green'}">${esc(s.category || 'Scholarship')}</span>
            </div>
            <h2>${esc(s.name)}</h2>
            <p>${esc(s.short_description || '')}</p>
            <div class="scheme-meta">
              <div><label>Benefit</label><b>${esc(s.benefit || 'Grant')}</b></div>
              <div><label>Authority</label><b>${esc(s.authority_name || 'Demonstration Cell')}</b></div>
            </div>
            <div class="button-row">
              <button class="button primary small" data-scheme="${esc(s.id)}" data-go="eligibility">Check Eligibility</button>
              <button class="button secondary small" data-scheme="${esc(s.id)}" data-go="assistant">Ask AI</button>
            </div>
          </div>
        `).join('')}
      </div>
    </div>
  </section>`;
}

function renderAssistant() {
  const scheme = getScheme(state.selectedSchemeId);
  return `
  <section class="view">
    <div class="page-heading">
      <div>
        <p class="eyebrow">Conversational Governance Assistant</p>
        <h1>AI Chat Assistant</h1>
        <p>Source-grounded guidance in English, Hindi, and Marathi. Uses retrieved official documents only; asks for missing information and never invents criteria.</p>
      </div>
      <div class="button-row">
        <div>
          <label class="label" for="chat-lang">Language</label>
          <select id="chat-lang" class="select-compact">
            <option value="en" ${state.chatLanguage === 'en' ? 'selected' : ''}>English</option>
            <option value="hi" ${state.chatLanguage === 'hi' ? 'selected' : ''}>हिन्दी (Hindi)</option>
            <option value="mr" ${state.chatLanguage === 'mr' ? 'selected' : ''}>मराठी (Marathi)</option>
          </select>
        </div>
        <div>
          <label class="label" for="chat-scheme">Scheme Context</label>
          <select id="chat-scheme" class="select-compact">
            <option value="">All Available Schemes</option>
            ${schemeOptions(state.selectedSchemeId)}
          </select>
        </div>
      </div>
    </div>

    <div class="assistant-layout">
      <article class="card chat-card">
        <header class="chat-header">
          <div class="ai-orb"><svg><use href="#i-spark"/></svg></div>
          <div>
            <h2>CivicPilot AI Grounded Assistant</h2>
            <p><i></i> Grounded in Seeded Rules & Uploaded Excerpts</p>
          </div>
        </header>

        <div id="chat-stream" class="chat-stream">
          ${state.chatHistory.length ? state.chatHistory.map(m => `
            <div class="message ${m.role === 'user' ? 'user' : ''}">
              <div class="message-avatar ${m.role === 'user' ? 'user' : ''}">
                ${m.role === 'user' ? 'You' : '<svg><use href="#i-spark"/></svg>'}
              </div>
              <div class="message-body">
                <div class="message-label">${m.role === 'user' ? 'You' : 'CivicPilot AI'} <time>${m.time || ''}</time></div>
                <div class="message-bubble">
                  <p style="white-space:pre-wrap">${esc(m.content)}</p>
                  ${m.sources?.length ? sourcesBlock(m.sources) : ''}
                  ${m.needs_more_information ? '<div style="margin-top:8px;font-size:11px;color:#b45309">⚠️ Additional applicant information is required to verify all conditions.</div>' : ''}
                </div>
              </div>
            </div>
          `).join('') : `
            <div class="message">
              <div class="message-avatar"><svg><use href="#i-spark"/></svg></div>
              <div class="message-body">
                <div class="message-label">CivicPilot AI</div>
                <div class="message-bubble">
                  <p>Hello! I am your Intelligent Government Service Assistant. Ask me any question regarding eligibility, required documents, or application procedures in English, Hindi, or Marathi.</p>
                </div>
              </div>
            </div>
          `}
        </div>

        <div class="chat-composer">
          <div class="quick-prompts">
            <button data-quick="What documents are required for Maharashtra Merit Scholarship?">What documents are required?</button>
            <button data-quick="What is the family income limit for STEM Access Grant?">Income limit for STEM Grant?</button>
            <button data-quick="Am I eligible if my family income is ₹1,80,000?">Income ₹1.8L eligibility?</button>
            <button data-quick="या योजनेसाठी कोणती कागदपत्रे लागतील?">कोणती कागदपत्रे लागतील? (MR)</button>
            <button data-quick="छात्रवृत्ति के लिए पात्रता नियम क्या हैं?">पात्रता नियम क्या हैं? (HI)</button>
          </div>
          <form id="chat-form" class="composer-box">
            <textarea id="chat-message" placeholder="Type your civic question (English, हिन्दी, मराठी)..." required rows="1"></textarea>
            <button class="send-button" type="submit" ${state.loading.chat ? 'disabled' : ''} aria-label="Send">
              <svg><use href="#i-arrow"/></svg>
            </button>
          </form>
        </div>
      </article>

      <aside class="chat-sidebar">
        <div class="card">
          <h3>Scheme Grounding</h3>
          <p class="helper" style="margin-bottom:12px">Current selected context:</p>
          <div class="panel" style="margin:0;background:#f8fafc">
            <b>${esc(scheme?.name || 'All Seeded Schemes')}</b>
            <p class="helper" style="margin-top:4px">${esc(scheme?.short_description || 'Synthesizing across all available demo scheme rules.')}</p>
          </div>
        </div>

        <div class="card">
          <h3>Safety Guarantees</h3>
          <div class="grounding-callout">
            <svg><use href="#i-shield"/></svg>
            <b>Source-Grounded Only:</b> Answers are derived strictly from supplied texts. When facts are unavailable, CivicPilot admits uncertainty rather than hallucinating official rules.
          </div>
        </div>
      </aside>
    </div>
  </section>`;
}

function renderScholarships() {
  const filtered = state.schemes.filter(s => {
    if (state.filterCategory !== 'all' && s.category !== state.filterCategory) return false;
    if (state.searchQuery && !s.name.toLowerCase().includes(state.searchQuery) && !s.short_description.toLowerCase().includes(state.searchQuery)) return false;
    return true;
  });

  return `
  <section class="view">
    <div class="page-heading">
      <div>
        <p class="eyebrow">Public Schemes & Grants Directory</p>
        <h1>Scholarship Explorer</h1>
        <p>Explore seeded demonstration schemes, inspect deterministic evaluation rules, and ask grounded questions.</p>
      </div>
    </div>

    <div class="toolbar">
      <div class="search-box">
        <svg><use href="#i-search"/></svg>
        <input id="scheme-search" placeholder="Search by scheme name or keywords..." value="${esc(state.searchQuery)}" />
      </div>
      <select id="scheme-category-filter" class="filter-select">
        <option value="all" ${state.filterCategory === 'all' ? 'selected' : ''}>All Categories</option>
        <option value="Merit & Means" ${state.filterCategory === 'Merit & Means' ? 'selected' : ''}>Merit & Means</option>
        <option value="STEM Education" ${state.filterCategory === 'STEM Education' ? 'selected' : ''}>STEM Education</option>
        <option value="Women Empowerment" ${state.filterCategory === 'Women Empowerment' ? 'selected' : ''}>Women Empowerment</option>
      </select>
    </div>

    <div class="scheme-grid">
      ${filtered.map(s => `
        <article class="card scheme-card">
          <div class="scheme-card-top">
            <div class="scheme-seal"><svg><use href="#i-book"/></svg></div>
            <span class="chip ${s.category?.includes('Women') ? 'purple' : s.category?.includes('STEM') ? 'blue' : 'green'}">${esc(s.category || 'Scholarship')}</span>
          </div>
          <h2>${esc(s.name)}</h2>
          <p>${esc(s.short_description || '')}</p>
          <div class="scheme-meta">
            <div><label>Benefit</label><b>${esc(s.benefit || 'Grant')}</b></div>
            <div><label>Deadline</label><b>${esc(s.deadline || '2026-12-31')}</b></div>
            <div style="grid-column:span 2"><label>Authority</label><b>${esc(s.authority_name || 'Demonstration Cell')}</b></div>
          </div>
          <div class="panel" style="margin:10px 0;background:#f8fafc">
            <b style="font-size:11px;color:var(--slate-700)">Required Documents:</b>
            <div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:6px">
              ${(s.required_documents || []).map(d => `<span class="chip" style="font-size:9px">${esc(d.label)}</span>`).join('')}
            </div>
          </div>
          <div class="button-row">
            <button class="button primary small" data-scheme="${esc(s.id)}" data-go="eligibility">Check Eligibility</button>
            <button class="button secondary small" data-scheme="${esc(s.id)}" data-go="assistant">Ask AI</button>
          </div>
        </article>
      `).join('') || `
        <div class="empty-search card">
          <p>No schemes matched your search query. Try clearing the filter or search term.</p>
          <button class="button secondary small" id="clear-search">Reset Filter</button>
        </div>
      `}
    </div>
  </section>`;
}

function renderEligibility() {
  const result = state.eligibilityResult;
  const scheme = getScheme(state.selectedSchemeId) || state.schemes[0];

  return `
  <section class="view">
    <div class="page-heading">
      <div>
        <p class="eyebrow">Deterministic Rule-Based Assessment</p>
        <h1>Eligibility Checker</h1>
        <p>100% transparent rule evaluation separated from generative AI. Instant feedback on income caps, state domicile, and academic thresholds.</p>
      </div>
      <div class="button-row">
        <span style="font-size:12px;font-weight:700;color:var(--navy-800)">Instant Test Profiles:</span>
        <button class="button secondary small" data-profile="eligible">🟢 Asha (Eligible)</button>
        <button class="button secondary small" data-profile="stem">🔵 Rahul (STEM)</button>
        <button class="button secondary small" data-profile="girls">🟣 Sneha (Pragati)</button>
        <button class="button secondary small" data-profile="ineligible">🔴 Vikram (Ineligible)</button>
      </div>
    </div>

    <div class="wizard-layout">
      <article class="card form-card">
        <form id="elig-form" class="form-grid">
          <div class="field full">
            <label for="elig-scheme">Select Scholarship Scheme <span>*</span></label>
            <select id="elig-scheme" name="scheme_id" class="input" required>
              ${schemeOptions(state.selectedSchemeId)}
            </select>
          </div>

          <div class="field">
            <label>Applicant Full Name <span>*</span></label>
            <input id="ef-name" name="name" class="input" placeholder="e.g. Asha Patel" required />
          </div>

          <div class="field">
            <label>State of Residence <span>*</span></label>
            <input id="ef-state" name="state" class="input" placeholder="e.g. Maharashtra" required />
          </div>

          <div class="field">
            <label>Annual Family Income (₹) <span>*</span></label>
            <input id="ef-income" name="family_income" class="input" inputmode="numeric" placeholder="e.g. 180000" required />
          </div>

          <div class="field">
            <label>Latest Percentage (%) <span>*</span></label>
            <input id="ef-percentage" name="percentage" class="input" inputmode="decimal" placeholder="e.g. 78.2" required />
          </div>

          <div class="field">
            <label>Current Study Level <span>*</span></label>
            <input id="ef-level" name="current_level" class="input" placeholder="e.g. undergraduate, 12, diploma" required />
          </div>

          <div class="field">
            <label>Course / Study Field</label>
            <input id="ef-field" name="study_field" class="input" placeholder="e.g. Computer Engineering, STEM" />
          </div>

          <div class="field full">
            <label>Gender Identification</label>
            <select id="ef-gender" name="gender" class="input">
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other / Prefer not to say</option>
            </select>
          </div>

          <div class="form-foot full">
            <p>Rules are computed deterministically on the backend. No hallucinated rules or dates.</p>
            <button class="button primary" type="submit" ${state.loading.elig ? 'disabled' : ''}>
              ${state.loading.elig ? 'Evaluating Rules…' : 'Run Eligibility Evaluation'}
            </button>
          </div>
        </form>
      </article>

      <article class="card result-card">
        <h3>Evaluation Result</h3>
        ${result ? `
          <div class="eligibility-result ${result.decision === 'eligible' ? '' : 'not-eligible'}" style="margin-top:12px">
            <div class="result-seal">
              <svg><use href="${result.decision === 'eligible' ? '#i-check' : '#i-alert'}"/></svg>
            </div>
            <div>
              <h2 style="font-size:16px">${result.decision === 'eligible' ? 'Eligible for Demonstration Scheme' : result.decision === 'needs_information' ? 'More Information Needed' : 'Does Not Meet Scheme Rules'}</h2>
              <p>${esc(result.summary)}</p>
            </div>
          </div>

          <div class="criteria-list">
            <b style="font-size:11px;color:var(--slate-700)">Rule-by-Rule Criteria Audit:</b>
            ${(result.checks || []).map(c => `
              <div class="criteria-row">
                <div class="criteria-status ${c.status === 'passed' ? '' : 'pending'}">
                  <svg><use href="${c.status === 'passed' ? '#i-check' : '#i-alert'}"/></svg>
                </div>
                <div>
                  <b>${esc(c.label || c.field)}: <span style="color:${c.status === 'passed' ? 'var(--green-700)' : 'var(--red-700)'}">${esc(c.status.toUpperCase())}</span></b>
                  <span>${esc(c.detail || c.rule)}</span>
                </div>
              </div>
            `).join('')}
          </div>

          ${result.decision === 'eligible' ? `
            <div style="margin-top:16px">
              <button class="button primary" style="width:100%" id="apply-with-eligibility">
                Proceed to Draft Application with these Details →
              </button>
            </div>
          ` : ''}
        ` : `
          <div class="panel" style="margin-top:12px;background:#f8fafc">
            <p class="helper">Enter your details or select one of the Quick Test Profiles above to view live deterministic evaluation results.</p>
          </div>
        `}
      </article>
    </div>
  </section>`;
}

function renderDocuments() {
  const scheme = getScheme(state.selectedSchemeId);
  const checklist = state.checklist;

  return `
  <section class="view">
    <div class="page-heading">
      <div>
        <p class="eyebrow">Intelligent Document Extraction</p>
        <h1>Document Processing & Checklist</h1>
        <p>Upload applicant certificates or generate verified demonstration samples. Extracts text with PyMuPDF/OCR and matches against scheme checklists.</p>
      </div>
      <div class="button-row">
        <span style="font-size:12px;font-weight:700;color:var(--navy-800)">Instant Test Documents:</span>
        <button class="button secondary small" data-sample="marksheet">📄 + Sample Marksheet (78%)</button>
        <button class="button secondary small" data-sample="income">💰 + Sample Income (₹1.8L)</button>
        <button class="button secondary small" data-sample="residence">🏠 + Sample Domicile (MH)</button>
        <button class="button secondary small" data-sample="admission">🎓 + Sample STEM Admission</button>
      </div>
    </div>

    <div class="document-layout">
      <div>
        <article class="card upload-card">
          <div class="drop-zone" id="drop-zone">
            <div class="upload-emblem"><svg><use href="#i-upload"/></svg></div>
            <h2>Drag & drop your document here, or browse</h2>
            <p>Upload PDF, PNG, JPG, JPEG, or WEBP up to 10 MB.</p>
            <input type="file" id="up-file" accept=".pdf,.png,.jpg,.jpeg,.webp" />
            <button class="button primary small" type="button" onclick="$('#up-file').click()">Select File from Computer</button>
            <div class="file-types">Text extraction is best-effort. Official documents are not legally authenticated.</div>
          </div>
        </article>

        <article class="card doc-list-card" style="margin-top:18px">
          <div class="section-title">
            <div>
              <h2>Uploaded & Extracted Documents</h2>
              <p>Session-attached documents for application draft.</p>
            </div>
          </div>
          <div>
            ${state.uploads.length ? state.uploads.map(u => `
              <div class="document-row">
                <div class="doc-icon photo"><svg><use href="#i-file"/></svg></div>
                <div>
                  <b>${esc(u.filename)}</b>
                  <span>Type: <span class="badge ${u.document_type === 'unclassified' ? 'amber' : 'green'}">${esc(u.document_type)}</span> · Extraction: ${esc(u.extraction_status)}</span>
                  <details style="margin-top:4px">
                    <summary style="font-size:10px;cursor:pointer;color:var(--blue-600)">View Extracted Text Excerpt</summary>
                    <pre class="codebox" style="margin-top:4px;max-height:120px">${esc(u.text_preview || 'No text extracted.')}</pre>
                  </details>
                </div>
                <div>
                  <span class="status-tag green">Attached</span>
                </div>
              </div>
            `).join('') : '<p class="helper">No documents uploaded in this session yet. Click one of the Instant Test Document buttons above!</p>'}
          </div>
        </article>
      </div>

      <aside>
        <article class="card checklist-card">
          <div class="section-title">
            <div>
              <h2>Required Documents</h2>
              <p>Checklist for: <b>${esc(scheme?.name || 'Selected Scheme')}</b></p>
            </div>
            <button class="button secondary small" id="refresh-checklist-btn"><svg><use href="#i-refresh"/></svg></button>
          </div>
          <div class="checklist-group">
            <h3>Mandatory Verification Items</h3>
            ${((checklist?.checklist) || (scheme?.required_documents) || []).map(i => {
              const hasDoc = state.uploads.some(u => u.document_type === i.type);
              return `
                <div class="doc-check">
                  <div class="check-circle ${hasDoc ? '' : 'missing'}">
                    <svg><use href="${hasDoc ? '#i-check' : '#i-alert'}"/></svg>
                  </div>
                  <div>
                    <b>${esc(i.label)}</b>
                    <span>${esc(i.reference || i.description || '')} · Status: <b>${hasDoc ? 'Provided in Session' : (i.required ? 'Missing' : 'Optional')}</b></span>
                  </div>
                </div>
              `;
            }).join('')}
          </div>
        </article>
      </aside>
    </div>
  </section>`;
}

function renderPrepare() {
  const app = currentApp();
  const uploadedIds = state.uploads.map(u => u.id).filter(Boolean);

  return `
  <section class="view">
    <div class="page-heading">
      <div>
        <p class="eyebrow">Application Draft & Preparation</p>
        <h1>Application Preparation</h1>
        <p>Save drafts, link processed documents, and review all applicant details before triggering safe local simulation.</p>
      </div>
      <div class="button-row">
        <span style="font-size:12px;font-weight:700;color:var(--navy-800)">Quick Fill Profile:</span>
        <button class="button secondary small" data-profile="eligible">🟢 Asha Patel</button>
        <button class="button secondary small" data-profile="stem">🔵 Rahul Deshmukh</button>
      </div>
    </div>

    <div class="application-layout">
      <article class="card form-card">
        <div class="form-intro">
          <h2>Application Draft Form</h2>
          <p>Fields marked with an asterisk are required to initiate a local draft.</p>
        </div>

        <form id="prep-form" class="form-grid">
          <div class="field full">
            <label>Target Scholarship Scheme <span>*</span></label>
            <select name="scheme_id" id="pf-scheme" class="input" required>
              ${schemeOptions(state.selectedSchemeId)}
            </select>
          </div>

          <div class="field">
            <label>Applicant Full Name <span>*</span></label>
            <input id="pf-name" name="name" class="input" placeholder="e.g. Asha Patel" required />
          </div>

          <div class="field">
            <label>Email Address <span>*</span></label>
            <input id="pf-email" name="email" type="email" class="input" placeholder="e.g. asha.patel@example.com" required />
          </div>

          <div class="field">
            <label>State of Residence</label>
            <input id="pf-state" name="state" class="input" placeholder="e.g. Maharashtra" />
          </div>

          <div class="field">
            <label>Annual Family Income (₹)</label>
            <input id="pf-income" name="family_income" class="input" inputmode="numeric" placeholder="e.g. 180000" />
          </div>

          <div class="field">
            <label>Latest Percentage (%)</label>
            <input id="pf-percentage" name="percentage" class="input" inputmode="decimal" placeholder="e.g. 78.2" />
          </div>

          <div class="field">
            <label>Education Level</label>
            <input id="pf-level" name="current_level" class="input" placeholder="e.g. undergraduate, 12, diploma" />
          </div>

          <div class="field full">
            <label>Course / Program Discipline</label>
            <input id="pf-field" name="study_field" class="input" placeholder="e.g. Computer Science & Engineering (STEM)" />
          </div>

          <div class="panel full" style="background:#f8fafc">
            <b>Session Documents Attached:</b>
            <span class="badge ${uploadedIds.length ? 'green' : 'amber'}">${uploadedIds.length} Document(s) Attached</span>
            <p class="helper" style="margin-top:4px">${state.uploads.map(u => u.filename).join(', ') || 'No documents attached in this session yet.'}</p>
          </div>

          <div class="form-foot full">
            <p>Creating a draft saves the record to local SQLite and initiates the verification workflow.</p>
            <button class="button primary" type="submit" ${state.loading.createApp ? 'disabled' : ''}>
              ${state.loading.createApp ? 'Saving Draft…' : 'Save Application Draft'}
            </button>
          </div>
        </form>
      </article>

      <aside class="review-side card">
        <h3>Step 1: Human Review Gate</h3>
        <p class="helper" style="margin-bottom:12px">Review saved draft before browser automation:</p>

        <div>
          <label class="label">Select Draft Application</label>
          <select id="prep-app-select" class="input">
            ${state.applications.map(a => `<option value="${esc(a.id)}" ${a.id === state.selectedApplicationId ? 'selected' : ''}>${esc(a.scheme_name || a.scheme_id)} · ${esc(a.applicant_name || 'Applicant')}</option>`).join('')}
          </select>
        </div>

        ${app ? `
          <div class="panel" style="margin-top:14px;background:#f8fafc">
            <div class="row-between">
              <b>${esc(app.scheme?.name || app.scheme_id)}</b>
              <span class="status-tag ${app.status === 'demo_submitted' ? 'green' : 'amber'}">${esc(app.status)}</span>
            </div>
            <ul class="mini-list" style="margin-top:8px">
              <li><b>Applicant:</b> ${esc(app.applicant?.name || '—')}</li>
              <li><b>Email:</b> ${esc(app.applicant?.email || '—')}</li>
              <li><b>Income:</b> ₹${esc(app.applicant?.family_income || '—')}</li>
              <li><b>Marks:</b> ${esc(app.applicant?.percentage || '—')}%</li>
              <li><b>Attached Docs:</b> ${app.uploaded_document_ids?.length || 0}</li>
            </ul>
          </div>

          <form id="prepare-demo-form" style="margin-top:16px">
            <label style="display:flex;gap:10px;align-items:flex-start;cursor:pointer">
              <input id="confirm-review-chk" type="checkbox" required style="margin-top:3px" />
              <span style="font-size:11px;color:var(--slate-700);line-height:1.4">
                I have explicitly reviewed this applicant draft and authorise pre-filling the <b>local simulated portal</b> in a headless Playwright test instance.
              </span>
            </label>
            <button class="button primary" style="width:100%;margin-top:14px" type="submit" ${state.loading.prepareDemo ? 'disabled' : ''}>
              ${state.loading.prepareDemo ? 'Launching Browser…' : 'Confirm Review & Launch Simulation'}
            </button>
          </form>
        ` : `
          <p class="helper" style="margin-top:14px">Save a draft to proceed to human review.</p>
        `}
      </aside>
    </div>
  </section>`;
}

function renderAutomation() {
  const app = currentApp();
  const prep = (state.lastPrepare?.application?.id === app?.id) ? state.lastPrepare : null;
  const payload = app?.demo_payload || prep?.application?.demo_payload || null;
  const portalUrl = prep?.portal_url || (app ? `/demo-portal/${app.id}` : null);
  const canApprove = app && (app.status === 'demo_prepared');
  const isSubmitted = app?.status === 'demo_submitted';
  const approvedRef = state.lastApprove?.acknowledgement?.reference || (isSubmitted ? app.demo_reference : null);

  return `
  <section class="view">
    <div class="page-heading">
      <div>
        <p class="eyebrow">Playwright Local Simulation Engine</p>
        <h1>Browser Automation Status</h1>
        <p>Headless browser automation executes strictly against local mock endpoints. Human approval is strictly required before recording an acknowledgement.</p>
      </div>
      <div class="button-row">
        <div>
          <select id="auto-app-select" class="select-compact">
            ${state.applications.map(a => `<option value="${esc(a.id)}" ${a.id === state.selectedApplicationId ? 'selected' : ''}>${esc(a.scheme_name || a.scheme_id)} · ${esc(a.applicant_name || 'Applicant')} (${esc(a.status)})</option>`).join('')}
          </select>
        </div>
      </div>
    </div>

    <div class="automation-layout">
      <article class="card portal-card">
        <div class="portal-bar">
          <div class="browser-dots"><i></i><i></i><i></i></div>
          <div class="browser-url">http://127.0.0.1:8000${esc(portalUrl || '/demo-portal/sample')}</div>
          <span class="chip green">Local Sandbox</span>
        </div>

        <div class="portal-status">
          <div class="portal-logo">
            <span><svg><use href="#i-shield"/></svg></span>
            CivicPilot Automated Simulation Harness
          </div>

          <h2>${esc(app?.scheme?.name || app?.scheme_id || 'Demonstration Scheme')}</h2>
          <p>Application ID: <span class="mono">${esc(app?.id || '—')}</span> · Engine: <span class="chip blue">${esc(payload?.browser_engine || 'Playwright Local')}</span></p>

          <div class="portal-fields">
            <div class="portal-field">
              <label>Applicant Full Name</label>
              <div class="portal-input">${esc(payload?.filled_fields?.name || app?.applicant?.name || '—')}</div>
              <svg><use href="#i-check"/></svg>
            </div>
            <div class="portal-field">
              <label>Email Address</label>
              <div class="portal-input">${esc(payload?.filled_fields?.email || app?.applicant?.email || '—')}</div>
              <svg><use href="#i-check"/></svg>
            </div>
            <div class="portal-field">
              <label>State of Residence</label>
              <div class="portal-input">${esc(payload?.filled_fields?.state || app?.applicant?.state || 'Maharashtra')}</div>
              <svg><use href="#i-check"/></svg>
            </div>
            <div class="portal-field">
              <label>Family Annual Income</label>
              <div class="portal-input">₹${esc(payload?.filled_fields?.family_income || app?.applicant?.family_income || '—')}</div>
              <svg><use href="#i-check"/></svg>
            </div>
            <div class="portal-field">
              <label>Academic Marks</label>
              <div class="portal-input">${esc(payload?.filled_fields?.percentage || app?.applicant?.percentage || '—')}%</div>
              <svg><use href="#i-check"/></svg>
            </div>
            <div class="portal-field">
              <label>Education Level</label>
              <div class="portal-input">${esc(payload?.filled_fields?.current_level || app?.applicant?.current_level || '—')}</div>
              <svg><use href="#i-check"/></svg>
            </div>
          </div>

          <div class="portal-disclaimer">
            🔒 Verification Notice: No external network connections were made. No government passwords, OTPs, or CAPTCHA bypasses were attempted.
          </div>

          ${portalUrl ? `
            <div style="margin-top:16px;display:flex;gap:10px">
              <a class="button secondary small" href="${esc(portalUrl)}" target="_blank" rel="noopener">
                <svg><use href="#i-external"/></svg> Open Full Local Portal in New Tab
              </a>
            </div>
          ` : ''}
        </div>
      </article>

      <aside class="automation-side">
        <div class="card">
          <h3>Simulation Lifecycle</h3>
          <div class="automation-progress">
            <div class="automation-step done">
              <i><svg><use href="#i-check"/></svg></i>
              <div>
                <b>Draft Validated</b>
                <span>Applicant record complete</span>
              </div>
            </div>
            <div class="automation-step ${payload ? 'done' : 'current'}">
              <i><svg><use href="${payload ? '#i-check' : '#i-clock'}"/></svg></i>
              <div>
                <b>Browser Injected</b>
                <span>${payload ? 'Playwright Chromium fill passed' : 'Awaiting confirmation'}</span>
              </div>
            </div>
            <div class="automation-step ${isSubmitted ? 'done' : (canApprove ? 'current' : '')}">
              <i><svg><use href="${isSubmitted ? '#i-check' : '#i-lock'}"/></svg></i>
              <div>
                <b>Human Sign-Off</b>
                <span>${isSubmitted ? 'Approved & Acknowledged' : 'Explicit approval required'}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <h3>Step 2: Final Human Approval</h3>
          <p class="helper">Autonomous scripts cannot submit applications. An explicit human signature is mandatory.</p>

          ${app ? `
            <form id="approve-form" style="margin-top:12px">
              <label style="display:flex;gap:10px;align-items:flex-start;cursor:pointer">
                <input id="approve-check" type="checkbox" ${canApprove ? '' : 'disabled'} ${isSubmitted ? 'checked disabled' : ''} required style="margin-top:3px" />
                <span style="font-size:11px;color:var(--slate-700);line-height:1.4">
                  I explicitly approve recording a <b>SIMULATED DEMO ACKNOWLEDGEMENT</b> for this local application.
                </span>
              </label>

              ${!isSubmitted ? `
                <button class="button primary" style="width:100%;margin-top:14px" type="submit" ${(!canApprove || state.loading.approve) ? 'disabled' : ''}>
                  ${state.loading.approve ? 'Recording Sign-Off…' : 'Approve Simulated Submission'}
                </button>
              ` : ''}
            </form>

            ${approvedRef ? `
              <div class="panel" style="margin-top:16px;background:#ecfdf3;border:1px solid #a7f3d0">
                <div class="row-between">
                  <b style="color:#065f46">Demo Acknowledged!</b>
                  <span class="chip green">Verified</span>
                </div>
                <div style="margin-top:6px;font-size:12px">
                  Reference: <b class="mono" style="color:#065f46">${esc(approvedRef)}</b>
                </div>
                <div style="margin-top:12px">
                  <a class="button primary small" href="/api/applications/${encodeURIComponent(app.id)}/slip" target="_blank" rel="noopener" style="width:100%;text-align:center">
                    📄 Print / Save Acknowledgment Slip
                  </a>
                </div>
              </div>
            ` : ''}
          ` : `
            <p class="helper">Select an application to manage approval.</p>
          `}
        </div>
      </aside>
    </div>
  </section>`;
}

function renderTracking() {
  const apps = state.applications || [];
  const app = currentApp();
  const submitted = apps.filter(a => a.status === 'demo_submitted').length;
  const prepared = apps.filter(a => a.status === 'demo_prepared').length;
  const drafts = apps.filter(a => a.status === 'draft').length;

  return `
  <section class="view">
    <div class="page-heading">
      <div>
        <p class="eyebrow">Real-Time Application Registry</p>
        <h1>Application Tracking</h1>
        <p>Live status registry, step-by-step audit progression, and printable simulated acknowledgment receipts.</p>
      </div>
      <div class="button-row">
        <button class="button secondary small" id="track-refresh"><svg><use href="#i-refresh"/></svg> Refresh Registry</button>
      </div>
    </div>

    <div class="tracking-stats">
      <div class="card tracking-stat"><b>${apps.length}</b><span>Total Registered Applications</span></div>
      <div class="card tracking-stat"><b>${drafts}</b><span>Active Drafts</span></div>
      <div class="card tracking-stat"><b>${prepared}</b><span>Prepared for Demo</span></div>
      <div class="card tracking-stat"><b>${submitted}</b><span>Simulated Submissions</span></div>
    </div>

    <div class="overview-grid">
      <article class="card tracking-table-card">
        <div class="table-toolbar">
          <h2>Registered Applications</h2>
          <span class="chip blue">${apps.length} records</span>
        </div>
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Scheme</th>
                <th>Applicant</th>
                <th>Status</th>
                <th>Progress</th>
                <th>Reference</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              ${apps.map(a => `
                <tr>
                  <td>
                    <div class="table-scheme">
                      <div class="scheme-seal"><svg><use href="#i-book"/></svg></div>
                      <b>${esc(a.scheme_name || a.scheme_id)}</b>
                    </div>
                  </td>
                  <td>${esc(a.applicant_name || 'Applicant')}</td>
                  <td>
                    <span class="status-tag ${a.status === 'demo_submitted' ? 'green' : 'amber'}">
                      <i></i> ${esc(a.status)}
                    </span>
                  </td>
                  <td>
                    <div style="display:flex;align-items:center;gap:6px">
                      <div class="progress-mini" style="width:60px"><i style="width:${progressPct(a)}%"></i></div>
                      <span style="font-size:10px">${progressPct(a)}%</span>
                    </div>
                  </td>
                  <td><span class="mono">${esc(a.demo_reference || '—')}</span></td>
                  <td>
                    <div style="display:flex;gap:4px">
                      <button class="table-action" data-app="${esc(a.id)}" title="Inspect details"><svg><use href="#i-search"/></svg></button>
                      <a class="table-action" href="/api/applications/${encodeURIComponent(a.id)}/slip" target="_blank" title="Print acknowledgment slip"><svg><use href="#i-file"/></svg></a>
                    </div>
                  </td>
                </tr>
              `).join('') || '<tr><td colspan="6" class="helper" style="text-align:center;padding:24px">No applications created yet.</td></tr>'}
            </tbody>
          </table>
        </div>
      </article>

      <aside class="card card-pad">
        <h3>Application Details & Audit Log</h3>
        ${app ? `
          <div class="panel" style="margin-top:10px;background:#f8fafc">
            <div class="row-between">
              <b>${esc(app.scheme?.name || app.scheme_id)}</b>
              <span class="status-tag ${app.status === 'demo_submitted' ? 'green' : 'amber'}">${esc(app.status)}</span>
            </div>
            <p class="helper" style="margin-top:4px">Reference: <b class="mono">${esc(app.demo_reference || 'Draft')}</b></p>
          </div>

          <div style="margin-top:16px">
            <b style="font-size:11px;color:var(--slate-700)">Workflow Step Status:</b>
            <div class="workflow">
              ${(app.steps || []).map(s => `
                <div class="workflow-step">
                  <div class="workflow-dot ${s.status === 'completed' ? 'done' : s.status === 'pending' ? 'current' : ''}">
                    <svg><use href="${s.status === 'completed' ? '#i-check' : '#i-clock'}"/></svg>
                  </div>
                  <div>
                    <b>${esc(s.label || s.step_key)}</b>
                    <span>${esc(s.status)}</span>
                  </div>
                  <time>${esc(fmtDate(s.updated_at))}</time>
                </div>
              `).join('')}
            </div>
          </div>

          <div style="margin-top:18px">
            <a class="button primary small" href="/api/applications/${encodeURIComponent(app.id)}/slip" target="_blank" rel="noopener" style="width:100%;text-align:center">
              📄 View Official Acknowledgment Slip
            </a>
          </div>
        ` : `
          <p class="helper" style="margin-top:12px">Select an application from the table to inspect details.</p>
        `}
      </aside>
    </div>
  </section>`;
}

function renderAbout() {
  return `
  <section class="view">
    <div class="about-hero">
      <div>
        <span class="badge" style="background:rgba(255,255,255,.14);color:#fff">Civic Pulse — Digital Governance & Public Information</span>
        <h1 style="color:#fff;margin:12px 0 8px;font-size:32px">About CivicPilot AI</h1>
        <p style="color:#d8e9fb;max-width:720px">CivicPilot AI transforms opaque government schemes into accessible digital pathways. Built with rigorous safety controls, deterministic eligibility, multi-lingual RAG, and safe local Playwright automation.</p>
      </div>
    </div>

    <div class="principle-grid">
      <article class="card principle">
        <div class="stat-icon" style="--stat-tint:var(--blue-50);--stat-color:var(--blue-600)"><svg><use href="#i-shield"/></svg></div>
        <h3>Separation of Concerns</h3>
        <p>Eligibility decisions are evaluated deterministically with strict mathematical comparison logic, completely isolated from generative AI outputs.</p>
      </article>
      <article class="card principle">
        <div class="stat-icon" style="--stat-tint:var(--green-50);--stat-color:var(--green-700)"><svg><use href="#i-check"/></svg></div>
        <h3>Two-Step Human Approval</h3>
        <p>Autonomous browser agents can only prepare local demo forms. Submitting an application requires two separate explicit human approvals.</p>
      </article>
      <article class="card principle">
        <div class="stat-icon" style="--stat-tint:var(--purple-100);--stat-color:var(--purple-700)"><svg><use href="#i-globe"/></svg></div>
        <h3>Multi-Lingual Inclusion</h3>
        <p>Supports English, हिन्दी (Hindi), and मराठी (Marathi) to bridge language barriers for students and rural citizens across India.</p>
      </article>
    </div>

    <div class="card architecture-card">
      <h2>System Architecture</h2>
      <div class="architecture-flow">
        <div class="architecture-node"><svg><use href="#i-user"/></svg> Citizen UI</div>
        <div class="architecture-arrow"><svg><use href="#i-arrow"/></svg></div>
        <div class="architecture-node"><svg><use href="#i-settings"/></svg> FastAPI Core</div>
        <div class="architecture-arrow"><svg><use href="#i-arrow"/></svg></div>
        <div class="architecture-node"><svg><use href="#i-spark"/></svg> Gemini RAG</div>
        <div class="architecture-arrow"><svg><use href="#i-arrow"/></svg></div>
        <div class="architecture-node"><svg><use href="#i-checklist"/></svg> Rules Engine</div>
        <div class="architecture-arrow"><svg><use href="#i-arrow"/></svg></div>
        <div class="architecture-node"><svg><use href="#i-automation"/></svg> Playwright Sandbox</div>
        <div class="architecture-arrow"><svg><use href="#i-arrow"/></svg></div>
        <div class="architecture-node"><svg><use href="#i-shield"/></svg> Human Approval Gate</div>
      </div>
    </div>
  </section>`;
}

function bindCommon() {
  if (state._bound) return;
  state._bound = true;
  window.addEventListener('hashchange', onHashChange);

  document.addEventListener('click', async (e) => {
    const go = e.target.closest('[data-go]');
    const schemeBtn = e.target.closest('[data-scheme]');
    const appBtn = e.target.closest('[data-app]');
    const profileBtn = e.target.closest('[data-profile]');
    const sampleBtn = e.target.closest('[data-sample]');
    const quickBtn = e.target.closest('[data-quick]');

    if (schemeBtn) state.selectedSchemeId = schemeBtn.getAttribute('data-scheme');

    if (appBtn) {
      state.selectedApplicationId = appBtn.getAttribute('data-app');
      try { await refreshApplication(state.selectedApplicationId, false); } catch (_) {}
    }

    if (profileBtn) {
      const pKey = profileBtn.getAttribute('data-profile');
      const p = DEMO_PROFILES[pKey];
      if (p) {
        state.selectedSchemeId = p.scheme_id;
        state._activeProfile = p;
        toast(`Loaded demo profile: ${p.name}`, 'info');
        if (state.view === 'eligibility') populateEligibilityForm(p);
        if (state.view === 'prepare') populatePrepareForm(p);
      }
    }

    if (sampleBtn) {
      const sType = sampleBtn.getAttribute('data-sample');
      try {
        setLoading('upload', true);
        const res = await api('/documents/sample', { method: 'POST', body: { sample_type: sType, scheme_id: state.selectedSchemeId || null } });
        state.uploads.unshift(res.document);
        toast(`Sample ${sType} generated and extracted!`, 'success');
        render();
      } catch (err) {
        toast(err.message, 'error');
      } finally {
        setLoading('upload', false);
      }
    }

    if (quickBtn) {
      const q = quickBtn.getAttribute('data-quick');
      state.chatHistory.push({ role: 'user', content: q, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
      render();
      await sendChat(q);
      return;
    }

    if (go) {
      navigate(go.getAttribute('data-go'));
      if (state._activeProfile) {
        setTimeout(() => {
          if (state.view === 'eligibility') populateEligibilityForm(state._activeProfile);
          if (state.view === 'prepare') populatePrepareForm(state._activeProfile);
        }, 50);
      }
      return;
    }

    if (schemeBtn || appBtn) render();
  });

  $('#menu-toggle')?.addEventListener('click', () => $('#sidebar')?.classList.add('open'));
  $('#sidebar-close')?.addEventListener('click', () => $('#sidebar')?.classList.remove('open'));
  $('#sidebar-scrim')?.addEventListener('click', () => $('#sidebar')?.classList.remove('open'));
  $('#refresh-button')?.addEventListener('click', async () => {
    try {
      await loadCore();
      render();
      toast('All records refreshed from database.', 'success');
    } catch (err) {
      toast(err.message, 'error');
    }
  });
}

function populateEligibilityForm(p) {
  if (!p) return;
  if ($('#elig-scheme')) $('#elig-scheme').value = p.scheme_id;
  if ($('#ef-name')) $('#ef-name').value = p.name;
  if ($('#ef-state')) $('#ef-state').value = p.state;
  if ($('#ef-income')) $('#ef-income').value = p.family_income;
  if ($('#ef-percentage')) $('#ef-percentage').value = p.percentage;
  if ($('#ef-level')) $('#ef-level').value = p.current_level;
  if ($('#ef-field')) $('#ef-field').value = p.study_field;
  if ($('#ef-gender')) $('#ef-gender').value = p.gender || 'female';
}

function populatePrepareForm(p) {
  if (!p) return;
  if ($('#pf-scheme')) $('#pf-scheme').value = p.scheme_id;
  if ($('#pf-name')) $('#pf-name').value = p.name;
  if ($('#pf-email')) $('#pf-email').value = p.email;
  if ($('#pf-state')) $('#pf-state').value = p.state;
  if ($('#pf-income')) $('#pf-income').value = p.family_income;
  if ($('#pf-percentage')) $('#pf-percentage').value = p.percentage;
  if ($('#pf-level')) $('#pf-level').value = p.current_level;
  if ($('#pf-field')) $('#pf-field').value = p.study_field;
}

function bindViewEvents() {
  $('#scheme-search')?.addEventListener('input', e => {
    state.searchQuery = e.target.value.toLowerCase().trim();
    render();
  });

  $('#scheme-category-filter')?.addEventListener('change', e => {
    state.filterCategory = e.target.value;
    render();
  });

  $('#clear-search')?.addEventListener('click', () => {
    state.searchQuery = '';
    state.filterCategory = 'all';
    render();
  });

  $('#chat-lang')?.addEventListener('change', e => { state.chatLanguage = e.target.value; });
  $('#chat-scheme')?.addEventListener('change', e => { state.selectedSchemeId = e.target.value; render(); });

  $('#chat-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const q = ($('#chat-message')?.value || '').trim();
    if (!q) return;
    $('#chat-message').value = '';
    state.chatHistory.push({ role: 'user', content: q, time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) });
    render();
    await sendChat(q);
  });

  $('#elig-scheme')?.addEventListener('change', e => { state.selectedSchemeId = e.target.value; });

  $('#elig-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const obj = formObj(e.target);
    state.selectedSchemeId = obj.scheme_id || state.selectedSchemeId;
    const applicant = {
      name: obj.name || '',
      state: obj.state || '',
      family_income: obj.family_income || '',
      percentage: obj.percentage || '',
      current_level: obj.current_level || '',
      study_field: obj.study_field || '',
      gender: obj.gender || '',
    };
    try {
      setLoading('elig', true);
      state.eligibilityResult = await api('/eligibility/check', { method: 'POST', body: { scheme_id: state.selectedSchemeId, applicant } });
      state._lastApplicantData = { ...applicant, scheme_id: state.selectedSchemeId };
      toast('Deterministic eligibility evaluated.', 'success');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setLoading('elig', false);
    }
  });

  $('#apply-with-eligibility')?.addEventListener('click', () => {
    if (state._lastApplicantData) {
      navigate('prepare');
      setTimeout(() => populatePrepareForm(state._lastApplicantData), 50);
    }
  });

  $('#up-file')?.addEventListener('change', async e => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    if (state.selectedSchemeId) fd.append('scheme_id', state.selectedSchemeId);
    try {
      setLoading('upload', true);
      const res = await api('/schemes/upload', { method: 'POST', body: fd });
      state.uploads.unshift(res.document);
      toast('Document uploaded & extracted successfully!', 'success');
      render();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setLoading('upload', false);
    }
  });

  $('#refresh-checklist-btn')?.addEventListener('click', async () => {
    if (!state.selectedSchemeId) return;
    try {
      state.checklist = await api(`/documents/checklist/${encodeURIComponent(state.selectedSchemeId)}`);
      toast('Checklist updated.', 'success');
      render();
    } catch (err) {
      toast(err.message, 'error');
    }
  });

  $('#prep-app-select')?.addEventListener('change', async e => {
    state.selectedApplicationId = e.target.value;
    if (state.selectedApplicationId) {
      try { await refreshApplication(state.selectedApplicationId); } catch (_) {}
    }
  });

  $('#prep-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const obj = formObj(e.target);
    if (!obj.name) return toast('Full name is required.', 'error');
    const applicant = {
      name: obj.name,
      email: obj.email || '',
      state: obj.state || '',
      family_income: obj.family_income || '',
      percentage: obj.percentage || '',
      current_level: obj.current_level || '',
      study_field: obj.study_field || '',
    };
    const uploaded_document_ids = state.uploads.map(u => u.id).filter(Boolean);
    try {
      setLoading('createApp', true);
      const res = await api('/applications', { method: 'POST', body: { scheme_id: obj.scheme_id, applicant, uploaded_document_ids } });
      const created = res.application || res;
      state.selectedApplicationId = created.id;
      state.selectedSchemeId = obj.scheme_id;
      await loadCore();
      await refreshApplication(created.id, false);
      toast('Application draft saved. Proceed to review.', 'success');
      render();
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setLoading('createApp', false);
    }
  });

  $('#prepare-demo-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const app = currentApp();
    if (!app) return toast('Select or save an application first.', 'error');
    if (!$('#confirm-review-chk')?.checked) return toast('Explicit review confirmation is required.', 'error');
    try {
      setLoading('prepareDemo', true);
      state.lastPrepare = await api(`/applications/${encodeURIComponent(app.id)}/prepare-demo`, { method: 'POST', body: { confirmed_review: true } });
      await loadCore();
      await refreshApplication(app.id, false);
      toast('Playwright simulation pre-fill complete.', 'success');
      navigate('automation');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setLoading('prepareDemo', false);
    }
  });

  $('#auto-app-select')?.addEventListener('change', async e => {
    state.selectedApplicationId = e.target.value;
    if (state.selectedApplicationId) {
      try { await refreshApplication(state.selectedApplicationId); } catch (_) {}
    }
  });

  $('#approve-form')?.addEventListener('submit', async e => {
    e.preventDefault();
    const app = currentApp();
    if (!app) return toast('Select an application.', 'error');
    if (!$('#approve-check')?.checked) return toast('Explicit approval required.', 'error');
    try {
      setLoading('approve', true);
      state.lastApprove = await api(`/applications/${encodeURIComponent(app.id)}/approve-demo`, {
        method: 'POST',
        body: { approved: true, acknowledgement: 'Approved via CivicPilot Human Review Gate' },
      });
      await loadCore();
      await refreshApplication(app.id, false);
      toast(`Simulated demo acknowledgement recorded: ${state.lastApprove?.acknowledgement?.reference || ''}`, 'success');
    } catch (err) {
      toast(err.message, 'error');
    } finally {
      setLoading('approve', false);
    }
  });

  $('#track-refresh')?.addEventListener('click', async () => {
    try {
      await loadCore();
      render();
      toast('Registry refreshed.', 'success');
    } catch (err) {
      toast(err.message, 'error');
    }
  });
}

async function sendChat(message) {
  try {
    setLoading('chat', true);
    const scheme_id = state.selectedSchemeId || null;
    const history = state.chatHistory.slice(-12).map(m => ({ role: m.role, content: m.content }));
    const res = await api('/chat', { method: 'POST', body: { message, scheme_id, language: state.chatLanguage || 'en', history } });
    state.chatHistory.push({
      role: 'assistant',
      content: res.answer || '',
      sources: res.sources || [],
      needs_more_information: res.needs_more_information,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    });
  } catch (err) {
    state.chatHistory.push({
      role: 'assistant',
      content: `I could not complete that request: ${err.message}`,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    });
  } finally {
    setLoading('chat', false);
  }
}

async function boot() {
  bindCommon();
  try {
    await loadCore();
  } catch (err) {
    console.error(err);
    toast(`Failed to load initial data: ${err.message}`, 'error');
  }
  onHashChange();
}

boot();
