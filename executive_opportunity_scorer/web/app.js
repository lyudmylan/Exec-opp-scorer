/* ─── Constants ───────────────────────────────────────────────────────────── */
const TIMING_CSS = {
  optimal: "timing-optimal",
  good:    "timing-good",
  early:   "timing-early",
  late:    "timing-late",
  blocked: "timing-blocked",
};

/* ─── State ───────────────────────────────────────────────────────────────── */
let uiSpec = null;
let lastResult = null;
let lastInput  = null;

/* ─── DOM refs ────────────────────────────────────────────────────────────── */
const form         = document.getElementById("dynamic-form");
const scoreBtn     = document.getElementById("score-button");
const enrichBtn    = document.getElementById("enrich-btn");
const loadSampleBtn= document.getElementById("load-sample");
const statusBox    = document.getElementById("status");
const resultCard   = document.getElementById("result-card");
const enrichStatus = document.getElementById("enrich-status");

/* ─── Init ────────────────────────────────────────────────────────────────── */
async function init() {
  const [specRes, sampleRes] = await Promise.all([
    fetch("/api/ui-spec"),
    fetch("/api/demo").catch(() => null),
  ]);
  uiSpec = await specRes.json();
  renderForm(uiSpec);

  if (sampleRes && sampleRes.ok) {
    const demo = await sampleRes.json();
    loadSampleBtn.addEventListener("click", () => applyPayload(demo));
  } else {
    loadSampleBtn.disabled = true;
  }

  scoreBtn.addEventListener("click", submitScore);
  enrichBtn.addEventListener("click", enrichFromUrl);

  // Tab switching
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => switchView(tab.dataset.view));
  });

  document.getElementById("refresh-pipeline").addEventListener("click", loadPipeline);

  await refreshPipelineBadge();
}

/* ─── View switching ──────────────────────────────────────────────────────── */
function switchView(view) {
  document.querySelectorAll(".tab").forEach((t) => {
    t.classList.toggle("is-active", t.dataset.view === view);
    t.setAttribute("aria-selected", t.dataset.view === view ? "true" : "false");
  });
  document.getElementById("view-score").classList.toggle("hidden", view !== "score");
  document.getElementById("view-pipeline").classList.toggle("hidden", view !== "pipeline");
  if (view === "pipeline") loadPipeline();
}

/* ─── Form rendering ──────────────────────────────────────────────────────── */
function renderForm(spec) {
  form.innerHTML = "";
  spec.sections.forEach((section) => {
    const visible = section.fields.filter((f) => !f.ui_hidden);
    if (!visible.length) return;

    const sec = document.createElement("div");
    sec.className = "form-section";

    const label = document.createElement("div");
    label.className = "section-title";
    label.textContent = section.title;
    sec.appendChild(label);

    const grid = document.createElement("div");
    grid.className = "field-grid";

    const evidenceFields = [];

    visible.forEach((field) => {
      if (field.id === "company_url") {
        // URL field gets an inline enrich button wrapper
        const wrapper = document.createElement("div");
        wrapper.className = "field";
        wrapper.dataset.fieldId = field.id;
        const lbl = document.createElement("label");
        lbl.setAttribute("for", field.id);
        lbl.textContent = field.label;
        const row = document.createElement("div");
        row.className = "field-url-row";
        row.appendChild(buildFieldInput(field));
        wrapper.appendChild(lbl);
        wrapper.appendChild(row);
        if (field.help) {
          const help = document.createElement("div");
          help.className = "field-help";
          help.textContent = field.help;
          wrapper.appendChild(help);
        }
        grid.appendChild(wrapper);
      } else {
        grid.appendChild(buildFieldWrapper(field));
      }
      if (field.evidence_key) evidenceFields.push(field);
    });

    sec.appendChild(grid);

    if (evidenceFields.length) {
      const evSec = document.createElement("div");
      evSec.className = "evidence-section";
      const evLabel = document.createElement("div");
      evLabel.className = "section-title";
      evLabel.textContent = "Evidence";
      evSec.appendChild(evLabel);
      evidenceFields.forEach((f) => evSec.appendChild(buildEvidenceBlock(f)));
      sec.appendChild(evSec);
    }

    form.appendChild(sec);
  });
}

function buildFieldWrapper(field) {
  const wrapper = document.createElement("div");
  wrapper.className = "field";
  wrapper.dataset.fieldId = field.id;
  const lbl = document.createElement("label");
  lbl.setAttribute("for", field.id);
  lbl.textContent = field.label;
  wrapper.appendChild(lbl);
  wrapper.appendChild(buildFieldInput(field));
  if (field.help) {
    const help = document.createElement("div");
    help.className = "field-help";
    help.textContent = field.help;
    wrapper.appendChild(help);
  }
  return wrapper;
}

function buildFieldInput(field) {
  if (field.type === "multiselect") {
    const wrap = document.createElement("div");
    wrap.id = field.id;
    wrap.className = "multi-select";
    field.options.forEach((opt) => {
      const lbl = document.createElement("label");
      lbl.className = "multi-select-option";
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.value = opt;
      cb.dataset.multiValue = opt;
      lbl.appendChild(cb);
      lbl.appendChild(document.createTextNode(opt));
      wrap.appendChild(lbl);
    });
    return wrap;
  }

  if (field.type === "select") {
    const sel = document.createElement("select");
    sel.id = field.id;
    field.options.forEach((opt) => {
      const o = document.createElement("option");
      o.value = opt;
      o.textContent = opt === "" ? "Unknown" : opt;
      sel.appendChild(o);
    });
    if (field.default != null) sel.value = String(field.default);
    return sel;
  }

  if (field.type === "boolean") {
    const sel = document.createElement("select");
    sel.id = field.id;
    [{ value: "", label: "Unknown" }, { value: "true", label: "Yes" }, { value: "false", label: "No" }].forEach(({ value, label }) => {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = label;
      sel.appendChild(o);
    });
    if (field.default === true) sel.value = "true";
    else if (field.default === false) sel.value = "false";
    return sel;
  }

  if (field.type === "textarea") {
    const ta = document.createElement("textarea");
    ta.id = field.id;
    ta.placeholder = field.placeholder || "";
    ta.value = field.default || "";
    return ta;
  }

  const input = document.createElement("input");
  input.id = field.id;
  input.type = field.type === "number" ? "number" : "text";
  input.placeholder = field.placeholder || "";
  if (field.type === "number") input.step = "any";
  if (field.default != null) input.value = field.default;
  return input;
}

function buildEvidenceBlock(field) {
  const block = document.createElement("div");
  block.className = "evidence-block";
  block.dataset.evidenceKey = field.evidence_key;

  const head = document.createElement("div");
  head.className = "evidence-block-head";
  const headLabel = document.createElement("strong");
  headLabel.textContent = field.label;
  const addBtn = document.createElement("button");
  addBtn.type = "button";
  addBtn.className = "link-btn";
  addBtn.textContent = "+ Add evidence";
  addBtn.addEventListener("click", () => addEvidenceItem(block, {}));
  head.appendChild(headLabel);
  head.appendChild(addBtn);

  const list = document.createElement("div");
  list.className = "evidence-list";

  block.appendChild(head);
  block.appendChild(list);
  return block;
}

function addEvidenceItem(block, value) {
  const item = document.createElement("div");
  item.className = "evidence-item";

  const fields = document.createElement("div");
  fields.className = "evidence-item-fields";

  uiSpec.evidence_entry.fields.forEach((f) => {
    const col = document.createElement("div");
    col.className = "field";
    const lbl = document.createElement("label");
    lbl.textContent = f.label;
    const input = f.type === "textarea" ? document.createElement("textarea") : document.createElement("input");
    input.dataset.evidenceField = f.id;
    input.type = f.type === "date" ? "date" : "text";
    input.placeholder = f.placeholder || "";
    input.value = value[f.id] || "";
    col.appendChild(lbl);
    col.appendChild(input);
    fields.appendChild(col);
  });

  const footer = document.createElement("div");
  footer.className = "evidence-item-footer";
  const removeBtn = document.createElement("button");
  removeBtn.type = "button";
  removeBtn.className = "remove-btn";
  removeBtn.textContent = "Remove";
  removeBtn.addEventListener("click", () => item.remove());
  footer.appendChild(removeBtn);

  item.appendChild(fields);
  item.appendChild(footer);
  block.querySelector(".evidence-list").appendChild(item);
}

/* ─── Collect payload ─────────────────────────────────────────────────────── */
function collectPayload() {
  const payload = { evidence: {} };
  uiSpec.sections.forEach((section) => {
    section.fields.forEach((field) => {
      const el = document.getElementById(field.id);
      if (!el) return;
      payload[field.id] = readFieldValue(field, el);
      if (field.evidence_key) {
        const block = document.querySelector(`[data-evidence-key="${field.evidence_key}"]`);
        if (block) {
          const items = [];
          block.querySelectorAll(".evidence-item").forEach((item) => {
            const ev = {};
            item.querySelectorAll("[data-evidence-field]").forEach((inp) => {
              ev[inp.dataset.evidenceField] = inp.value;
            });
            items.push(ev);
          });
          payload.evidence[field.evidence_key] = items;
        }
      }
    });
  });
  return payload;
}

function readFieldValue(field, el) {
  if (field.type === "number") return el.value === "" ? null : Number(el.value);
  if (field.type === "boolean") return el.value === "" ? null : el.value === "true";
  if (field.type === "multiselect") {
    return Array.from(el.querySelectorAll('input[type="checkbox"]:checked')).map((i) => i.value);
  }
  return el.value;
}

/* ─── Submit score ────────────────────────────────────────────────────────── */
async function submitScore() {
  setStatus("Scoring…", false);
  resultCard.classList.add("hidden");

  try {
    const res = await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectPayload()),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed.");

    lastResult = data.result;
    lastInput  = data.input;
    renderResult(data.result);
    statusBox.classList.add("hidden");
    await refreshPipelineBadge();
  } catch (err) {
    setStatus(err.message, true);
  }
}

/* ─── Render result ───────────────────────────────────────────────────────── */
function renderResult(r) {
  resultCard.classList.remove("hidden");

  const fit   = r.fit_score;
  const risk  = r.risk_score;
  const conf  = r.confidence;
  const rec   = r.recommendation;
  const angle = r.approach_angle || "";
  const timing= r.timing_window  || "Unclear";

  const riskClass   = risk >= 60 ? "risk-high" : risk >= 40 ? "risk-med" : "risk-low";
  const timingClass = TIMING_CSS[timing.toLowerCase()] || "timing-unclear";
  const recClass    = rec === "Pursue now" ? "rec-pursue" : rec === "Monitor" ? "rec-monitor" : "rec-low";

  const posHtml = (r.top_positive_signals || []).map((s) =>
    `<span class="signal-pill signal-pos">${esc(s)}</span>`).join("");
  const negHtml = (r.top_risk_signals || []).map((s) =>
    `<span class="signal-pill signal-neg">${esc(s)}</span>`).join("");
  const stepsHtml = (r.next_steps || []).map((s) =>
    `<div class="next-step">${esc(s)}</div>`).join("");

  resultCard.innerHTML = `
    <div class="result-header">
      <div>
        <div class="result-company">${esc(r.company_name)}</div>
        <div class="result-date">${esc(r.snapshot_date)}</div>
      </div>
      <span class="rec-pill ${recClass}">${esc(rec)}</span>
    </div>

    <div class="metrics-row">
      <div class="metric">
        <div class="metric-label">Fit</div>
        <div class="metric-value fit">${fit}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Risk</div>
        <div class="metric-value ${riskClass}">${risk}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Confidence</div>
        <div class="metric-value conf">${conf}</div>
      </div>
      <div class="metric">
        <div class="metric-label">Timing</div>
        <div class="metric-value" style="font-size:13px;padding-top:4px">
          <span class="timing-badge ${timingClass}">${esc(timing)}</span>
        </div>
      </div>
    </div>

    ${angle ? `
    <div class="approach-callout">
      <div class="approach-label">Approach angle</div>
      <div class="approach-text">${esc(angle)}</div>
    </div>` : ""}

    ${posHtml ? `
    <div>
      <div class="result-section-label">Top signals</div>
      <div class="signals-row">${posHtml}</div>
    </div>` : ""}

    ${negHtml ? `
    <div>
      <div class="result-section-label">Risk signals</div>
      <div class="signals-row">${negHtml}</div>
    </div>` : ""}

    <div>
      <div class="result-section-label">Summary</div>
      <p class="explanation">${esc(r.explanation)}</p>
    </div>

    ${stepsHtml ? `
    <div>
      <div class="result-section-label">Next steps</div>
      <div class="next-steps">${stepsHtml}</div>
    </div>` : ""}

    <div class="result-actions">
      <button id="save-pipeline-btn" class="btn-save" type="button">Save to pipeline</button>
    </div>
  `;

  document.getElementById("save-pipeline-btn").addEventListener("click", saveToP);
}

/* ─── Save to pipeline ────────────────────────────────────────────────────── */
async function saveToP() {
  if (!lastResult) return;
  try {
    const res = await fetch("/api/pipeline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ result: lastResult, input: lastInput }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Save failed.");
    const btn = document.getElementById("save-pipeline-btn");
    if (btn) { btn.textContent = "Saved ✓"; btn.disabled = true; }
    await refreshPipelineBadge();
  } catch (err) {
    alert("Could not save: " + err.message);
  }
}

/* ─── Enrich from URL ─────────────────────────────────────────────────────── */
async function enrichFromUrl() {
  const urlEl  = document.getElementById("company_url");
  const nameEl = document.getElementById("company_name");
  const url    = urlEl ? urlEl.value.trim() : "";
  const name   = nameEl ? nameEl.value.trim() : "";

  if (!url) {
    showEnrichStatus("Enter a company URL first.", "err");
    return;
  }

  enrichBtn.disabled = true;
  enrichBtn.textContent = "Enriching…";
  showEnrichStatus("", null);

  try {
    const res = await fetch("/api/enrich", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ company_url: url, company_name: name }),
    });
    const data = await res.json();
    if (!res.ok || data.error) throw new Error(data.error || "Enrichment failed.");

    applyPartialPayload(data);
    showEnrichStatus("Fields updated from URL. Review and adjust as needed.", "ok");
  } catch (err) {
    showEnrichStatus(err.message, "err");
  } finally {
    enrichBtn.disabled = false;
    enrichBtn.textContent = "Enrich from URL";
  }
}

function showEnrichStatus(msg, type) {
  enrichStatus.textContent = msg;
  enrichStatus.className = "enrich-status" + (type ? ` ${type}` : " hidden");
}

/* ─── Apply payload ───────────────────────────────────────────────────────── */
function applyPayload(payload) {
  uiSpec.sections.forEach((section) => {
    section.fields.forEach((field) => {
      const el = document.getElementById(field.id);
      if (!el) return;
      const val = payload[field.id];
      setFieldValue(field, el, val);
      if (field.evidence_key) {
        const block = document.querySelector(`[data-evidence-key="${field.evidence_key}"]`);
        if (block) {
          block.querySelector(".evidence-list").innerHTML = "";
          (payload.evidence?.[field.evidence_key] || []).forEach((item) => addEvidenceItem(block, item));
        }
      }
    });
  });
}

function applyPartialPayload(partial) {
  uiSpec.sections.forEach((section) => {
    section.fields.forEach((field) => {
      if (!(field.id in partial)) return;
      const el = document.getElementById(field.id);
      if (!el) return;
      setFieldValue(field, el, partial[field.id]);
    });
  });
  // source_urls_text may come as a separate key
  if (partial.source_urls_text) {
    const el = document.getElementById("source_urls_text");
    if (el) el.value = partial.source_urls_text;
  }
}

function setFieldValue(field, el, val) {
  if (field.type === "boolean") {
    el.value = val == null ? "" : String(val);
  } else if (field.type === "multiselect") {
    const selected = new Set(val || []);
    el.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
      cb.checked = selected.has(cb.value);
    });
  } else {
    el.value = val ?? "";
  }
}

/* ─── Pipeline ────────────────────────────────────────────────────────────── */
async function loadPipeline() {
  const list = document.getElementById("pipeline-list");
  list.innerHTML = `<div class="status-msg muted">Loading…</div>`;
  try {
    const res = await fetch("/api/pipeline");
    const data = await res.json();
    renderPipeline(data.entries || []);
  } catch {
    list.innerHTML = `<div class="status-msg error">Could not load pipeline.</div>`;
  }
}

function renderPipeline(entries) {
  const list = document.getElementById("pipeline-list");
  if (!entries.length) {
    list.innerHTML = `<div class="pipeline-empty">No companies saved yet. Score a company and save it to track it here.</div>`;
    return;
  }
  list.innerHTML = "";
  entries.forEach((e) => list.appendChild(buildPipelineEntry(e)));
}

function buildPipelineEntry(e) {
  const risk = e.risk_score || 0;
  const riskChipClass = risk >= 60 ? "chip-risk-high" : risk >= 40 ? "chip-risk-med" : "chip-risk-low";
  const timingClass   = TIMING_CSS[(e.timing_window || "").toLowerCase()] || "timing-unclear";
  const recClass      = e.recommendation === "Pursue now" ? "rec-pursue" : e.recommendation === "Monitor" ? "rec-monitor" : "rec-low";
  const date = (e.created_at || "").slice(0, 10);

  const entry = document.createElement("div");
  entry.className = "pipeline-entry";

  const row = document.createElement("div");
  row.className = "pipeline-row";
  row.innerHTML = `
    <div>
      <div class="pipeline-name">${esc(e.company_name)}</div>
      <div class="pipeline-date">${esc(date)}</div>
    </div>
    <span class="score-chip chip-fit">Fit ${e.fit_score ?? "—"}</span>
    <span class="score-chip ${riskChipClass}">Risk ${e.risk_score ?? "—"}</span>
    <span class="timing-badge ${timingClass}">${esc(e.timing_window || "Unclear")}</span>
    <span class="rec-pill ${recClass}" style="font-size:12px;padding:4px 10px">${esc(e.recommendation || "—")}</span>
    <button class="btn-danger" data-id="${e.id}" type="button">Delete</button>
  `;

  const expand = document.createElement("div");
  expand.className = "pipeline-expand hidden";

  if (e.approach_angle) {
    expand.innerHTML += `
      <div class="approach-callout">
        <div class="approach-label">Approach angle</div>
        <div class="approach-text">${esc(e.approach_angle)}</div>
      </div>`;
  }

  entry.appendChild(row);
  entry.appendChild(expand);

  // Toggle expand on row click (not delete button)
  row.addEventListener("click", (ev) => {
    if (ev.target.matches(".btn-danger")) return;
    expand.classList.toggle("hidden");
  });

  // Delete
  row.querySelector(".btn-danger").addEventListener("click", async (ev) => {
    ev.stopPropagation();
    const id = ev.target.dataset.id;
    await fetch(`/api/pipeline/${id}`, { method: "DELETE" });
    entry.remove();
    await refreshPipelineBadge();
  });

  return entry;
}

async function refreshPipelineBadge() {
  try {
    const res = await fetch("/api/pipeline");
    const data = await res.json();
    const count = (data.entries || []).length;
    const badge = document.getElementById("pipeline-badge");
    if (count > 0) {
      badge.textContent = count;
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  } catch { /* ignore */ }
}

/* ─── Status helper ───────────────────────────────────────────────────────── */
function setStatus(msg, isError) {
  statusBox.classList.remove("hidden");
  statusBox.className = "status-msg" + (isError ? " error" : " muted");
  statusBox.textContent = msg;
}

/* ─── Escape ──────────────────────────────────────────────────────────────── */
function esc(str) {
  if (str == null) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* ─── Boot ────────────────────────────────────────────────────────────────── */
init().catch((err) => setStatus(err.message, true));
