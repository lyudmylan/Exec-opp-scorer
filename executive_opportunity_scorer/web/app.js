let uiSpec = null;
let demoPayload = null;

const form = document.getElementById("dynamic-form");
const scoreButton = document.getElementById("score-button");
const statusBox = document.getElementById("status");
const resultCard = document.getElementById("result-card");
const normalizedBox = document.getElementById("normalized-json");
const resultBox = document.getElementById("result-json");
const loadTemplateButton = document.getElementById("load-template");
const loadSampleButton = document.getElementById("load-sample");

async function init() {
  const [specResponse, sampleResponse] = await Promise.all([
    fetch("/api/ui-spec"),
    fetch("/api/demo").catch(() => null)
  ]);

  uiSpec = await specResponse.json();
  renderForm(uiSpec);

  if (sampleResponse && sampleResponse.ok) {
    demoPayload = await sampleResponse.json();
  }

  loadTemplateButton.addEventListener("click", loadBlankTemplate);
  loadSampleButton.addEventListener("click", loadDemoValues);
  scoreButton.addEventListener("click", submitScore);
}

function renderForm(spec) {
  form.innerHTML = "";
  spec.sections.forEach((section) => {
    const visibleFields = section.fields.filter((field) => !field.ui_hidden);
    if (!visibleFields.length) {
      return;
    }

    const sectionNode = document.createElement("section");
    sectionNode.className = "section";

    const heading = document.createElement("h3");
    heading.textContent = section.title;
    sectionNode.appendChild(heading);

    const grid = document.createElement("div");
    grid.className = "section-grid";

    visibleFields.forEach((field) => {
      const fieldNode = document.createElement("div");
      fieldNode.className = "field";
      fieldNode.dataset.fieldId = field.id;

      const label = document.createElement("label");
      label.setAttribute("for", field.id);
      label.textContent = field.label;
      fieldNode.appendChild(label);

      const input = buildFieldInput(field);
      fieldNode.appendChild(input);

      const help = document.createElement("div");
      help.className = "field-help";
      help.textContent = field.help || "";
      fieldNode.appendChild(help);

      grid.appendChild(fieldNode);
    });

    sectionNode.appendChild(grid);

    const evidenceFields = visibleFields.filter((field) => field.evidence_key);
    if (evidenceFields.length) {
      const evidenceWrap = document.createElement("div");
      evidenceWrap.className = "section";
      const header = document.createElement("div");
      header.className = "evidence-header";
      header.innerHTML = `<div><h4>Evidence</h4><p>Add evidence only for the fields you know something about.</p></div>`;
      evidenceWrap.appendChild(header);

      evidenceFields.forEach((field) => {
        evidenceWrap.appendChild(buildEvidenceBlock(field));
      });
      sectionNode.appendChild(evidenceWrap);
    }

    form.appendChild(sectionNode);
  });
}

function buildFieldInput(field) {
  if (field.type === "select") {
    const select = document.createElement("select");
    select.id = field.id;
    field.options.forEach((option) => {
      const optionNode = document.createElement("option");
      optionNode.value = option;
      optionNode.textContent = option === "" ? "Unknown" : option;
      select.appendChild(optionNode);
    });
    if (field.default !== undefined && field.default !== null) {
      select.value = String(field.default);
    }
    return select;
  }

  if (field.type === "multiselect") {
    const wrap = document.createElement("div");
    wrap.id = field.id;
    wrap.className = "multi-select";
    field.options.forEach((option) => {
      const label = document.createElement("label");
      label.className = "multi-select-option";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.value = option;
      input.dataset.multiValue = option;
      label.appendChild(input);
      label.appendChild(document.createTextNode(option));
      wrap.appendChild(label);
    });
    return wrap;
  }

  if (field.type === "textarea") {
    const textarea = document.createElement("textarea");
    textarea.id = field.id;
    textarea.placeholder = field.placeholder || "";
    textarea.value = field.default || "";
    return textarea;
  }

  const input = document.createElement("input");
  input.id = field.id;
  input.type = field.type === "number" ? "number" : field.type === "date" ? "date" : "text";
  input.placeholder = field.placeholder || "";
  if (field.type === "number") {
    input.step = "any";
  }

  if (field.type === "boolean") {
    const select = document.createElement("select");
    select.id = field.id;
    [
      { value: "", label: "Unknown" },
      { value: "true", label: "True" },
      { value: "false", label: "False" }
    ].forEach((option) => {
      const optionNode = document.createElement("option");
      optionNode.value = option.value;
      optionNode.textContent = option.label;
      select.appendChild(optionNode);
    });
    if (field.default === true) {
      select.value = "true";
    } else if (field.default === false) {
      select.value = "false";
    }
    return select;
  }

  if (field.default !== null && field.default !== undefined) {
    input.value = field.default;
  }
  return input;
}

function buildEvidenceBlock(field) {
  const block = document.createElement("div");
  block.className = "evidence-block";
  block.dataset.evidenceKey = field.evidence_key;

  const header = document.createElement("div");
  header.className = "evidence-header";
  header.innerHTML = `<div><strong>${field.label}</strong><p>${field.evidence_key}</p></div>`;

  const addButton = document.createElement("button");
  addButton.type = "button";
  addButton.className = "link-button";
  addButton.textContent = "Add evidence";
  addButton.addEventListener("click", () => addEvidenceItem(block, {}));
  header.appendChild(addButton);

  const list = document.createElement("div");
  list.className = "evidence-list";

  block.appendChild(header);
  block.appendChild(list);
  return block;
}

function addEvidenceItem(block, value) {
  const item = document.createElement("div");
  item.className = "evidence-item";

  uiSpec.evidence_entry.fields.forEach((field) => {
    const label = document.createElement("label");
    label.textContent = field.label;
    const input = field.type === "textarea" ? document.createElement("textarea") : document.createElement("input");
    input.dataset.evidenceField = field.id;
    input.type = field.type === "date" ? "date" : "text";
    input.placeholder = field.placeholder || "";
    input.value = value[field.id] || "";
    item.appendChild(label);
    item.appendChild(input);
  });

  const removeButton = document.createElement("button");
  removeButton.type = "button";
  removeButton.className = "remove-evidence";
  removeButton.textContent = "Remove evidence";
  removeButton.addEventListener("click", () => item.remove());
  item.appendChild(removeButton);

  block.querySelector(".evidence-list").appendChild(item);
}

function collectPayload() {
  const payload = { evidence: {} };

  uiSpec.sections.forEach((section) => {
    section.fields.forEach((field) => {
      const element = document.getElementById(field.id);
      if (!element) {
        return;
      }
      payload[field.id] = readFieldValue(field, element);

      if (field.evidence_key) {
        const block = document.querySelector(`[data-evidence-key="${field.evidence_key}"]`);
        const items = [];
        block.querySelectorAll(".evidence-item").forEach((item) => {
          const evidenceItem = {};
          item.querySelectorAll("[data-evidence-field]").forEach((input) => {
            evidenceItem[input.dataset.evidenceField] = input.value;
          });
          items.push(evidenceItem);
        });
        payload.evidence[field.evidence_key] = items;
      }
    });
  });

  return payload;
}

function readFieldValue(field, element) {
  if (field.type === "number") {
    return element.value === "" ? null : Number(element.value);
  }
  if (field.type === "boolean") {
    if (element.value === "") return null;
    return element.value === "true";
  }
  if (field.type === "multiselect") {
    return Array.from(element.querySelectorAll('input[type="checkbox"]:checked')).map((input) => input.value);
  }
  return element.value;
}

async function submitScore() {
  statusBox.className = "status muted";
  statusBox.textContent = "Scoring...";
  resultCard.classList.add("hidden");

  try {
    const response = await fetch("/api/score", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(collectPayload())
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Request failed.");
    }

    normalizedBox.textContent = JSON.stringify(data.input, null, 2);
    resultBox.textContent = JSON.stringify(data.result, null, 2);
    renderResult(data.result);
    statusBox.textContent = "Score computed successfully.";
  } catch (error) {
    statusBox.className = "status error";
    statusBox.textContent = error.message;
  }
}

function renderResult(result) {
  resultCard.classList.remove("hidden");
  resultCard.innerHTML = `
    <div class="result-summary">
      <div class="metric"><span>Fit</span><strong>${result.fit_score}</strong></div>
      <div class="metric"><span>Risk</span><strong>${result.risk_score}</strong></div>
      <div class="metric"><span>Confidence</span><strong>${result.confidence}</strong></div>
      <div class="metric"><span>Recommendation</span><strong>${result.recommendation}</strong></div>
    </div>
    <div class="badges">
      ${(result.top_positive_signals || []).map((item) => `<span class="badge">${item}</span>`).join("")}
    </div>
    <p>${result.explanation}</p>
  `;
}

async function loadBlankTemplate() {
  const response = await fetch("/api/template");
  const template = await response.json();
  applyPayload(template);
  statusBox.textContent = "Loaded blank template from the UI spec.";
}

function loadDemoValues() {
  if (!demoPayload) {
    statusBox.className = "status error";
    statusBox.textContent = "Demo payload is unavailable.";
    return;
  }
  applyPayload(demoPayload);
  statusBox.className = "status muted";
  statusBox.textContent = "Loaded demo values from the sample dataset.";
}

function applyPayload(payload) {
  uiSpec.sections.forEach((section) => {
    section.fields.forEach((field) => {
      const element = document.getElementById(field.id);
      if (!element) {
        return;
      }
      const value = payload[field.id];
      if (field.type === "boolean") {
        element.value = value === null || value === undefined ? "" : String(value);
      } else if (field.type === "multiselect") {
        const selected = new Set(value || []);
        element.querySelectorAll('input[type="checkbox"]').forEach((input) => {
          input.checked = selected.has(input.value);
        });
      } else {
        element.value = value ?? "";
      }

      if (field.evidence_key) {
        const block = document.querySelector(`[data-evidence-key="${field.evidence_key}"]`);
        const list = block.querySelector(".evidence-list");
        list.innerHTML = "";
        (payload.evidence?.[field.evidence_key] || []).forEach((item) => addEvidenceItem(block, item));
      }
    });
  });
}

init().catch((error) => {
  statusBox.className = "status error";
  statusBox.textContent = error.message;
});
