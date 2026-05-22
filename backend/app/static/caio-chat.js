const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const messages = document.querySelector("#messages");
const sendButton = document.querySelector("#sendButton");
const statePill = document.querySelector("#connectionState");
const tenantId = document.querySelector("#tenantId");
const clientName = document.querySelector("#clientName");
const toolsStatus = document.querySelector("#toolsStatus");
const quickIntakeForm = document.querySelector("#quickIntakeForm");
const quickSector = document.querySelector("#quickSector");
const quickEmployeeBand = document.querySelector("#quickEmployeeBand");
const quickPain = document.querySelector("#quickPain");
const quickSensitivity = document.querySelector("#quickSensitivity");
const quickGoal = document.querySelector("#quickGoal");
const opportunityForm = document.querySelector("#opportunityForm");
const opportunityQuestion = document.querySelector("#opportunityQuestion");
const opportunityEmployeeCount = document.querySelector("#opportunityEmployeeCount");
const opportunityButton = document.querySelector("#opportunityButton");
const opportunityResult = document.querySelector("#opportunityResult");
const uploadForm = document.querySelector("#uploadForm");
const documentFile = document.querySelector("#documentFile");
const uploadButton = document.querySelector("#uploadButton");
const uploadResult = document.querySelector("#uploadResult");
const runtimeMode = document.querySelector("#runtimeMode");
const salesSummary = document.querySelector("#salesSummary");
const runtimePolicyForm = document.querySelector("#runtimePolicyForm");
const runtimePremiumProvider = document.querySelector("#runtimePremiumProvider");
const runtimeEscalationEnabled = document.querySelector("#runtimeEscalationEnabled");
const runtimeAllowSensitive = document.querySelector("#runtimeAllowSensitive");
const runtimeAllowedIntents = document.querySelector("#runtimeAllowedIntents");
const runtimePolicyButton = document.querySelector("#runtimePolicyButton");
const runtimePolicyResult = document.querySelector("#runtimePolicyResult");
const knowledgeForm = document.querySelector("#knowledgeForm");
const knowledgeFile = document.querySelector("#knowledgeFile");
const knowledgeTitle = document.querySelector("#knowledgeTitle");
const knowledgeSourceUrl = document.querySelector("#knowledgeSourceUrl");
const knowledgeButton = document.querySelector("#knowledgeButton");
const knowledgeResult = document.querySelector("#knowledgeResult");
const knowledgeSearchForm = document.querySelector("#knowledgeSearchForm");
const knowledgeSearchInput = document.querySelector("#knowledgeSearchInput");
const knowledgeSearchButton = document.querySelector("#knowledgeSearchButton");
const knowledgeSearchMeta = document.querySelector("#knowledgeSearchMeta");
const knowledgeSearchResults = document.querySelector("#knowledgeSearchResults");
const intelBlockTabs = document.querySelector("#intelBlockTabs");
const intelBlocksMeta = document.querySelector("#intelBlocksMeta");
const intelExplorerCards = document.querySelector("#intelExplorerCards");
const processScannerForm = document.querySelector("#processScannerForm");
const scannerObjective = document.querySelector("#scannerObjective");
const scannerArtifacts = document.querySelector("#scannerArtifacts");
const scannerRisk = document.querySelector("#scannerRisk");
const scannerButton = document.querySelector("#scannerButton");
const scannerResult = document.querySelector("#scannerResult");

let knowledgeBlocks = [];
let selectedIntelBlock = null;
let lastKnowledgeQuery = "";
let lastOpportunityDiagnosis = null;
let runtimePolicyLoadedForTenant = null;

const DEFAULT_SCANNER_ARTIFACTS = `Procedimiento facturas | procedure | ERP | 300/mes
Administración recibe facturas de proveedores por email, descarga PDF, copia importe, IVA, NIF e IBAN en Excel y valida manualmente en ERP.

Emails repetitivos | email_sample | Outlook | 450/mes
Clientes escriben al buzón de soporte preguntando por horarios, precios, estado de pedido y documentación. El equipo copia respuestas desde una FAQ.

Export CRM | csv_export | CRM | 1200/mes
CSV con clientes, pedidos, estado, fecha, comercial y notas. Se prepara un informe semanal en Excel con KPIs y anomalías.`;

function tenantHeaders(extra = {}) {
  return {
    "X-Tenant-Id": tenantId.value || "demo-tenant",
    "X-User-Id": "web-user",
    "X-Client-Name": clientName.value || tenantId.value || "Demo SL",
    ...extra,
  };
}

function setBusy(isBusy) {
  sendButton.disabled = isBusy;
  statePill.textContent = isBusy ? "Thinking" : "Ready";
  statePill.classList.toggle("busy", isBusy);
}

function addMessage(role, html) {
  const article = document.createElement("article");
  article.className = `message ${role}`;
  article.innerHTML = `
    <div class="avatar">${role === "user" ? "Tú" : "IA"}</div>
    <div class="bubble">${html}</div>
  `;
  messages.append(article);
  messages.scrollTop = messages.scrollHeight;
  return article.querySelector(".bubble");
}

function addStatus(text) {
  const line = document.createElement("div");
  line.className = "status-line";
  line.textContent = text;
  messages.append(line);
  messages.scrollTop = messages.scrollHeight;
  return line;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderMarkdownLite(text) {
  let html = escapeHtml(text);
  html = html.replace(/^## (.*)$/gm, "<h2>$1</h2>");
  html = html.replace(/^### (.*)$/gm, "<h3>$1</h3>");
  html = html.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/^\d+\. (.*)$/gm, "<p>$&</p>");
  html = html.replace(/^- (.*)$/gm, "<p>• $1</p>");
  html = html.replace(/\n\n/g, "</p><p>");
  html = `<p>${html}</p>`;
  return html.replaceAll("<p></p>", "");
}

function formatDate(dateValue) {
  if (!dateValue) return "sin fecha";
  try {
    return new Date(dateValue).toLocaleDateString("es-ES", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateValue;
  }
}

function buildBlockPrompt(blockId, brief) {
  const title = brief?.title || "esta inteligencia";
  const mapping = {
    intel: `resume lo más útil para una pyme a partir de ${title} y conviértelo en recomendaciones accionables`,
    dolores: `a partir de ${title}, dime qué dolores reales de pyme debería atacar primero y cómo vender la solución`,
    roadmaps: `convierte ${title} en un roadmap de 90 días con quick wins, riesgos y ROI`,
    stack: `explica el stack recomendado en ${title} y cuándo conviene local, cloud o híbrido`,
    sector_publico_salud: `adapta ${title} a un plan de IA para hospital o ayuntamiento en España con riesgos y quick wins`,
    otros: `analiza ${title} y extrae las mejores decisiones para VirtuDirector IA`,
  };
  return mapping[blockId] || mapping.otros;
}

function blockLabel(blockId) {
  const mapping = {
    fundamentos: "Fundamentos base",
    intel: "Intel IA diaria",
    dolores: "Dolores detectados",
    roadmaps: "Roadmaps",
    stack: "Stack y runtime",
    sector_publico_salud: "Salud y sector publico",
    otros: "Otros",
  };
  return mapping[blockId] || blockId || "Otros";
}

function intentLabel(intentId) {
  const mapping = {
    general: "General",
    diagnostico: "Diagnostico",
    local_cloud: "Local vs cloud",
    roi: "ROI",
    roadmap: "Roadmap",
    gobierno: "Gobierno y riesgo",
    sector_salud: "Sector salud",
    sector_legal: "Sector legal",
    stack: "Stack",
  };
  return mapping[intentId] || intentId || "General";
}

function parseScannerArtifacts(rawText) {
  return rawText
    .split(/\n\s*\n/)
    .map((block, index) => {
      const lines = block.split("\n").map((line) => line.trim()).filter(Boolean);
      if (!lines.length) return null;
      const header = lines[0].split("|").map((part) => part.trim());
      const text = lines.slice(1).join(" ") || lines[0];
      const volumeMatch = (header[3] || "").match(/(\d+)/);
      return {
        name: header[0] || `Artefacto ${index + 1}`,
        artifact_type: header[1] || "other",
        system: header[2] || null,
        volume_per_month: volumeMatch ? Number(volumeMatch[1]) : null,
        text,
      };
    })
    .filter(Boolean);
}

function renderScannerResult(payload) {
  const result = payload?.result;
  if (!result) {
    scannerResult.textContent = "Sin resultado.";
    return;
  }
  const candidates = (result.candidates || []).slice(0, 3);
  scannerResult.innerHTML = `
    <div class="scanner-summary">
      <strong>${escapeHtml(result.readiness_label)}</strong>
      <p>Sistemas: ${escapeHtml((result.process_map.systems || []).join(", ") || "no detectados")}</p>
      <p>Procesos: ${escapeHtml((result.process_map.primary_processes || []).join(", ") || "no detectados")}</p>
    </div>
    ${candidates
      .map(
        (candidate) => `
          <article class="scanner-candidate">
            <div class="scanner-candidate-header">
              <h3>${escapeHtml(candidate.title)}</h3>
              <span class="scanner-score">${escapeHtml(candidate.score.total)}</span>
            </div>
            <p>${escapeHtml(candidate.problem)}</p>
            <div class="scanner-pill-row">
              <span class="scanner-pill">${escapeHtml(candidate.mode)}</span>
              <span class="scanner-pill">${escapeHtml(candidate.recommended_phase)}</span>
              <span class="scanner-pill">riesgo ${escapeHtml(candidate.score.risk)}</span>
            </div>
            <p>Sandbox: ${escapeHtml(candidate.first_sandbox.dataset)}</p>
            <div class="scanner-actions">
              <button type="button" data-prompt="${escapeHtml(`convierte el candidato ${candidate.title} en un plan de sandbox con métricas, riesgos y owners para ${clientName.value || "la empresa"}`)}">Plan sandbox</button>
            </div>
          </article>
        `
      )
      .join("")}
  `;
}

function eurosRange(range) {
  if (!Array.isArray(range) || range.length !== 2) return "n/a";
  return `${Number(range[0]).toLocaleString("en-IE")} - ${Number(range[1]).toLocaleString("en-IE")} EUR`;
}

function eurosValue(value) {
  return `${Number(value).toLocaleString("en-IE")} EUR`;
}

function rangeMidpoint(range) {
  if (!Array.isArray(range) || range.length !== 2) return 0;
  return Math.round((Number(range[0]) + Number(range[1])) / 2);
}

function rangeSum(ranges) {
  return ranges.reduce(
    (acc, range) => [
      acc[0] + Number(Array.isArray(range) ? range[0] || 0 : 0),
      acc[1] + Number(Array.isArray(range) ? range[1] || 0 : 0),
    ],
    [0, 0]
  );
}

function deploymentRecommendation() {
  const sensitivity = quickSensitivity?.value || "medium";
  const sector = quickSector?.value || "general";
  if (sensitivity === "high" || sector === "clinic" || sector === "legal" || sector === "public") {
    return "Local-first con opción híbrida controlada";
  }
  if (sensitivity === "medium") {
    return "Híbrido con local para datos internos";
  }
  return "Cloud o híbrido según coste y velocidad";
}

function opportunityLabels(ids, diagnosis) {
  const items = diagnosis?.top_opportunities || [];
  return (ids || [])
    .map((id) => items.find((item) => item.id === id)?.title || id)
    .slice(0, 3);
}

function pilotWindow(opportunity) {
  if (!opportunity) return "2-4 semanas";
  if ((opportunity.score?.effort || 0) <= 2) return "2-4 semanas";
  if ((opportunity.score?.effort || 0) === 3) return "4-6 semanas";
  return "6-10 semanas";
}

function buildQuestionFromQuickIntake() {
  const sectorMap = {
    general: "a Spanish SME",
    clinic: "a clinic",
    legal: "a legal or advisory practice",
    "real-estate": "a real estate business",
    industrial: "an industrial SME",
    public: "a Spanish local public-sector organisation",
  };
  const painMap = {
    support: "repetitive support requests and many recurring emails",
    invoices: "manual invoice processing and administrative bottlenecks",
    documents: "too much time spent searching internal documents and procedures",
    sales: "sales effort wasted on low-priority leads and follow-up",
    governance: "no clear AI roadmap and too many disconnected experiments",
  };
  const goalMap = {
    quickwins: "deliver quick wins in the first 30 days",
    savings: "save hours and reduce operating cost quickly",
    private: "keep sensitive data inside the company whenever possible",
    roadmap: "produce a realistic 90-day roadmap with clear priorities",
  };
  const sensitivityMap = {
    low: "low-sensitivity business data",
    medium: "internal business data with moderate sensitivity",
    high: "highly sensitive or regulated data",
  };

  return `Where should we implement AI first in ${sectorMap[quickSector.value] || "an SME"} with ${painMap[quickPain.value] || "manual internal processes"}, where the goal is to ${goalMap[quickGoal.value] || "deliver practical ROI"} and the company handles ${sensitivityMap[quickSensitivity.value] || "internal data"}?`;
}

function renderSalesSummaryFromDiagnosis(diagnosis, opportunities) {
  if (!salesSummary) return;
  const top = opportunities[0];
  const totalBenefit = rangeSum(opportunities.map((item) => item.annual_benefit_eur));
  const firstPilot = pilotWindow(top);
  const setupMidpoint = rangeMidpoint(top?.setup_cost_eur);
  const monthlyMidpoint = rangeMidpoint(top?.monthly_cost_eur);
  const quickWinCount = (diagnosis.quick_wins || []).length;
  const strategicCount = (diagnosis.strategic_bets || []).length;
  const commercialCopy = top
    ? `${clientName.value || "La empresa"} debería empezar por ${top.title.toLowerCase()} porque combina valor claro, esfuerzo razonable y un primer experimento medible. El primer piloto puede lanzarse en ${firstPilot} con un enfoque ${deploymentRecommendation().toLowerCase()}.`
    : "VirtuDirector IA prioriza oportunidades con ahorro medible, riesgo controlado y un primer piloto claro.";

  salesSummary.innerHTML = `
    <article class="sales-card sales-card-hero">
      <strong>Recomendación inicial</strong>
      <p>${escapeHtml(top?.title || "Diagnóstico en curso")}</p>
      <div class="executive-grid">
        <div class="executive-metric">
          <span>Beneficio anual potencial</span>
          <strong>${escapeHtml(eurosRange(totalBenefit))}</strong>
        </div>
        <div class="executive-metric">
          <span>Primer piloto</span>
          <strong>${escapeHtml(firstPilot)}</strong>
        </div>
      </div>
    </article>
    <article class="sales-card">
      <strong>Modo recomendado</strong>
      <p>${escapeHtml(deploymentRecommendation())}</p>
      <p>Setup inicial estimado: ${escapeHtml(eurosValue(setupMidpoint || 0))}</p>
      <p>Coste mensual estimado: ${escapeHtml(eurosValue(monthlyMidpoint || 0))}</p>
    </article>
    <article class="sales-card">
      <strong>Prioridad comercial</strong>
      <p>${quickWinCount} quick wins y ${strategicCount} apuestas estratégicas detectadas.</p>
      <p>${escapeHtml(opportunityLabels(diagnosis.quick_wins, diagnosis).join(" · ") || "Quick wins pendientes de concretar.")}</p>
      <div class="sales-copy">
        <strong>Cómo venderlo</strong>
        <p>${escapeHtml(commercialCopy)}</p>
      </div>
    </article>
  `;
}

function renderOpportunityResult(payload) {
  const diagnosis = payload?.diagnosis;
  if (!diagnosis) {
    opportunityResult.textContent = "No diagnosis returned.";
    return;
  }
  lastOpportunityDiagnosis = diagnosis;
  const opportunities = (diagnosis.top_opportunities || []).slice(0, 3);
  renderSalesSummaryFromDiagnosis(diagnosis, opportunities);
  opportunityResult.innerHTML = `
    <div class="scanner-summary executive">
      <strong>Resumen ejecutivo</strong>
      <p>Empresa: ${escapeHtml(clientName.value || "Cliente")}</p>
      <p>Tamaño estimado: ${escapeHtml(diagnosis.company_size)}</p>
      <p>Quick wins: ${escapeHtml(opportunityLabels(diagnosis.quick_wins, diagnosis).join(", ") || "ninguno detectado todavía")}</p>
      <p>Despliegue sugerido: ${escapeHtml(deploymentRecommendation())}</p>
    </div>
    ${opportunities
      .map(
        (item) => `
          <article class="scanner-candidate opportunity-card">
            <div class="scanner-candidate-header">
              <h3>${escapeHtml(item.title)}</h3>
              <span class="scanner-score">${escapeHtml(item.score.total)}</span>
            </div>
            <p>${escapeHtml(item.problem)}</p>
            <div class="scanner-pill-row">
              <span class="scanner-pill">${escapeHtml(item.area)}</span>
              <span class="scanner-pill">${escapeHtml(item.recommended_phase)}</span>
              <span class="scanner-pill">riesgo ${escapeHtml(item.score.risk)}</span>
            </div>
            <p>Beneficio anual estimado: ${escapeHtml(eurosRange(item.annual_benefit_eur))}</p>
            <p>Primer experimento: ${escapeHtml(item.first_experiment)}</p>
            <div class="scanner-actions">
              <button type="button" data-prompt="${escapeHtml(`Crea un roadmap de 90 días para ${item.title} con ROI, riesgos y responsables para ${clientName.value || "el cliente"}`)}">Usar en chat</button>
              <button type="button" data-opportunity-bundle="${escapeHtml(item.id)}">Generar bundle</button>
            </div>
          </article>
        `
      )
      .join("")}
  `;
}

async function generateImplementationBundle(opportunityId) {
  if (!lastOpportunityDiagnosis?.question) {
    opportunityResult.textContent = "Run an opportunity diagnosis first.";
    return;
  }
  const buttons = opportunityResult.querySelectorAll("[data-opportunity-bundle]");
  buttons.forEach((button) => {
    button.disabled = true;
  });
  try {
    const response = await fetch("/opportunities/implementation-bundle", {
      method: "POST",
      headers: tenantHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        question: lastOpportunityDiagnosis.question,
        employee_count: Number(opportunityEmployeeCount.value || "0") || null,
        opportunity_id: opportunityId,
        top_k: 8,
        review: true,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    const bundle = payload.bundle;
    const card = opportunityResult.querySelector(`[data-opportunity-bundle="${CSS.escape(opportunityId)}"]`)?.closest(".opportunity-card");
    if (card) {
      const detail = document.createElement("div");
      detail.className = "bundle-result";
      detail.innerHTML = `
        <p><strong>Bundle created.</strong></p>
        <p>Output: ${escapeHtml(bundle.output_dir)}</p>
        <p>Skills: ${escapeHtml((bundle.skill_names || []).join(", ") || "none")}</p>
        <p>Service file: ${escapeHtml(bundle.service_file)}</p>
      `;
      const existing = card.querySelector(".bundle-result");
      if (existing) existing.remove();
      card.append(detail);
    }
  } catch (error) {
    opportunityResult.insertAdjacentHTML(
      "afterbegin",
      `<div class="status-line">Bundle generation error: ${escapeHtml(error.message)}</div>`
    );
  } finally {
    buttons.forEach((button) => {
      button.disabled = false;
    });
  }
}

async function runOpportunityDiagnosis(question) {
  const trimmedQuestion = question.trim();
  if (!trimmedQuestion) {
    opportunityResult.textContent = "Escribe una situación o usa el diagnóstico rápido.";
    return;
  }
  opportunityButton.disabled = true;
  opportunityResult.textContent = "Analizando oportunidades y quick wins...";
  try {
    const response = await fetch("/opportunities/diagnose", {
      method: "POST",
      headers: tenantHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        question: trimmedQuestion,
        employee_count: Number(opportunityEmployeeCount.value || "0") || null,
        top_k: 6,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    renderOpportunityResult(payload);
  } catch (error) {
    opportunityResult.textContent = `Error: ${error.message}`;
  } finally {
    opportunityButton.disabled = false;
  }
}

function renderIntelExplorer() {
  if (!intelBlockTabs || !intelExplorerCards || !intelBlocksMeta) return;
  if (!knowledgeBlocks.length) {
    intelBlockTabs.innerHTML = "";
    intelExplorerCards.innerHTML = "";
    intelBlocksMeta.textContent = "Todavía no hay bloques curados cargados.";
    return;
  }

  const activeBlock =
    knowledgeBlocks.find((block) => block.id === selectedIntelBlock) || knowledgeBlocks[0];
  selectedIntelBlock = activeBlock.id;

  intelBlockTabs.innerHTML = knowledgeBlocks
    .map(
      (block) => `
        <button type="button" data-intel-block="${escapeHtml(block.id)}" aria-pressed="${block.id === activeBlock.id}">
          ${escapeHtml(block.label)} (${block.count})
        </button>
      `
    )
    .join("");

  intelBlocksMeta.textContent = `${activeBlock.label}: ${activeBlock.count} fichas disponibles. Mostrando las más recientes y compactadas.`;
  intelExplorerCards.innerHTML = activeBlock.briefs
    .map((brief) => {
      const summary = escapeHtml((brief.summary || "").slice(0, 240));
      const tags = Array.isArray(brief.tags) ? brief.tags.slice(0, 4) : [];
      const prompt = escapeHtml(buildBlockPrompt(activeBlock.id, brief));
      return `
        <article class="intel-card">
          <div class="intel-card-header">
            <strong>${escapeHtml(brief.title)}</strong>
            <span class="intel-card-meta">${escapeHtml(brief.source_type || "curated")} · ${escapeHtml(formatDate(brief.uploaded_at))}</span>
          </div>
          <p>${summary}</p>
          <div class="intel-tags">
            ${tags.map((tag) => `<span class="intel-tag">${escapeHtml(tag)}</span>`).join("")}
          </div>
          <div class="intel-card-actions">
            <button type="button" data-prompt="${prompt}">Usar en chat</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderKnowledgeSearchResults(briefs, query) {
  if (!knowledgeSearchMeta || !knowledgeSearchResults) return;
  if (!query.trim()) {
    knowledgeSearchMeta.textContent = "Busca en la base curada y verás bloque, intención detectada y por qué salió arriba.";
    knowledgeSearchResults.innerHTML = "";
    return;
  }

  if (!briefs.length) {
    knowledgeSearchMeta.textContent = `Sin resultados para “${query}”. Prueba con local vs cloud, quick wins clínica, despacho o ROI.`;
    knowledgeSearchResults.innerHTML = "";
    return;
  }

  const firstIntent = briefs[0].query_intent || "general";
  knowledgeSearchMeta.textContent = `${briefs.length} resultados para “${query}”. Intención detectada: ${intentLabel(firstIntent)}.`;
  knowledgeSearchResults.innerHTML = briefs
    .map((brief) => {
      const tags = Array.isArray(brief.tags) ? brief.tags.slice(0, 4) : [];
      const reasons = Array.isArray(brief.reasons) ? brief.reasons.slice(0, 4) : [];
      const prompt = escapeHtml(buildBlockPrompt(brief.block, brief));
      return `
        <article class="intel-card intel-search-card">
          <div class="intel-card-header">
            <strong>${escapeHtml(brief.title)}</strong>
            <span class="intel-card-meta">${escapeHtml(blockLabel(brief.block))} · intención ${escapeHtml(intentLabel(brief.query_intent))}</span>
          </div>
          <p>${escapeHtml((brief.summary || "").slice(0, 260))}</p>
          <div class="intel-tags">
            ${tags.map((tag) => `<span class="intel-tag">${escapeHtml(tag)}</span>`).join("")}
            <span class="intel-tag intel-tag-strong">score ${escapeHtml((brief.score || 0).toFixed(1))}</span>
          </div>
          <div class="intel-reasons">
            ${reasons.map((reason) => `<span class="intel-reason">${escapeHtml(reason)}</span>`).join("")}
          </div>
          <div class="intel-card-actions">
            <button type="button" data-prompt="${prompt}">Usar en chat</button>
          </div>
        </article>
      `;
    })
    .join("");
}

async function searchKnowledge(query) {
  if (!knowledgeSearchMeta || !knowledgeSearchResults) return;
  const trimmed = query.trim();
  lastKnowledgeQuery = trimmed;
  if (!trimmed) {
    renderKnowledgeSearchResults([], "");
    return;
  }

  knowledgeSearchButton.disabled = true;
  knowledgeSearchMeta.textContent = `Buscando “${trimmed}”...`;
  try {
    const response = await fetch(`/knowledge/briefs?q=${encodeURIComponent(trimmed)}&limit=6&explain=true`);
    const payload = await response.json();
    renderKnowledgeSearchResults(payload.briefs || [], trimmed);
  } catch (error) {
    knowledgeSearchMeta.textContent = `No disponible: ${error.message}`;
    knowledgeSearchResults.innerHTML = "";
  } finally {
    knowledgeSearchButton.disabled = false;
  }
}

async function loadKnowledgeBlocks() {
  if (!intelBlocksMeta) return;
  intelBlocksMeta.textContent = "Cargando bloques curados...";
  try {
    const response = await fetch("/knowledge/blocks?limit_per_block=4");
    const payload = await response.json();
    knowledgeBlocks = payload.blocks || [];
    renderIntelExplorer();
  } catch (error) {
    intelBlockTabs.innerHTML = "";
    intelExplorerCards.innerHTML = "";
    intelBlocksMeta.textContent = `No disponible: ${error.message}`;
  }
}

async function sendMessage(message) {
  addMessage("user", `<p>${escapeHtml(message)}</p>`);
  const assistantBubble = addMessage("assistant", "<p></p>");
  let accumulated = "";
  setBusy(true);

  try {
    const response = await fetch("/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Tenant-Id": tenantId.value || "demo-tenant",
        "X-User-Id": "web-user",
        "X-Client-Name": clientName.value || tenantId.value || "Demo SL",
      },
      body: JSON.stringify({ message }),
    });

    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() || "";

      for (const event of events) {
        const line = event.split("\n").find((item) => item.startsWith("data: "));
        if (!line) continue;
        const payload = JSON.parse(line.slice(6));
        if (payload.type === "status") {
          addStatus(payload.data);
        } else if (payload.type === "token") {
          accumulated += payload.data;
          assistantBubble.innerHTML = renderMarkdownLite(accumulated);
          messages.scrollTop = messages.scrollHeight;
        } else if (payload.type === "citation") {
          addStatus(`Fuente: ${payload.data}`);
        } else if (payload.type === "final" && payload.meta) {
          const executionPath = payload.meta.escalated ? "premium" : "local";
          addStatus(
            `Answer path: ${executionPath} · intent ${payload.meta.intent || "general"} · verified ${payload.meta.verified ? "yes" : "no"}`
          );
        } else if (payload.type === "error") {
          addStatus(`Error: ${payload.data}`);
        }
      }
    }
  } catch (error) {
    assistantBubble.innerHTML = `<p>Error: ${escapeHtml(error.message)}</p>`;
  } finally {
    setBusy(false);
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const value = input.value.trim();
  if (!value) return;
  input.value = "";
  sendMessage(value);
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-prompt]");
  if (!button) return;
  input.value = button.dataset.prompt;
  input.focus();
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-intel-block]");
  if (!button) return;
  selectedIntelBlock = button.dataset.intelBlock;
  renderIntelExplorer();
});

document.addEventListener("click", (event) => {
  const button = event.target.closest("[data-opportunity-bundle]");
  if (!button) return;
  generateImplementationBundle(button.dataset.opportunityBundle);
});

function hydrateRuntimePolicyForm(payload) {
  if (!runtimePolicyForm) return;
  const effective = payload?.effective || {};
  runtimePremiumProvider.value = effective.premium_provider || "lmstudio";
  runtimeEscalationEnabled.checked = Boolean(effective.escalation_enabled);
  runtimeAllowSensitive.checked = Boolean(effective.escalation_allow_sensitive);
  runtimeAllowedIntents.value =
    effective.escalation_allowed_intents || "strategy,grc,solution,opportunity,deliverable";
  runtimePolicyLoadedForTenant = tenantId.value || "demo-tenant";

  const stored = payload?.stored;
  runtimePolicyResult.innerHTML = stored
    ? `<div class="tool-line"><span>Override</span><strong>saved by ${escapeHtml(stored.updated_by || "unknown")}</strong></div>
       <div class="tool-line stacked"><span>Updated</span><strong>${escapeHtml(stored.updated_at || "unknown")}</strong></div>`
    : `<div class="tool-line"><span>Override</span><strong>using defaults</strong></div>`;
}

async function loadToolsStatus() {
  try {
    const [searchResponse, documentResponse, lmStudioResponse, premiumResponse, knowledgeResponse, policyResponse] = await Promise.all([
      fetch("/tools/web-search/status", { headers: tenantHeaders() }),
      fetch("/documents/status", { headers: tenantHeaders() }),
      fetch("/tools/lm-studio/status", { headers: tenantHeaders() }),
      fetch("/tools/premium/status", { headers: tenantHeaders() }),
      fetch("/knowledge/updates/status"),
      fetch("/tools/runtime-policy", { headers: tenantHeaders() }),
    ]);
    const status = await searchResponse.json();
    const docs = await documentResponse.json();
    const lmStudio = await lmStudioResponse.json();
    const premium = await premiumResponse.json();
    const knowledge = await knowledgeResponse.json();
    const runtimePolicy = await policyResponse.json();
    const activeNodes = (lmStudio.nodes || []).filter((node) => node.available);
    const firstNode = activeNodes[0];
    const localModel = lmStudio.enabled
      ? lmStudio.chat_model || "configurado"
      : "desactivado";
    runtimeMode.textContent = lmStudio.enabled && firstNode
      ? `LM Studio local active with ${localModel}. Premium path: ${premium.provider || "unknown"} (${premium.policy_source || "default"}).`
      : "Demo mode active: deterministic responses are used when no local model or external key is available.";
    toolsStatus.innerHTML = `
      <div class="tool-line"><span>LM Studio</span><strong>${lmStudio.enabled && firstNode ? "activo" : "inactivo"}</strong></div>
      <div class="tool-line stacked"><span>Modelo chat</span><strong>${escapeHtml(localModel)}</strong></div>
      <div class="tool-line stacked"><span>Nodo local</span><strong>${escapeHtml(firstNode?.base_url || "sin nodo disponible")}</strong></div>
      <div class="tool-line stacked"><span>Modelos LAN</span><strong>${escapeHtml(activeNodes.flatMap((node) => node.models || []).join(", ") || "ninguno")}</strong></div>
      <div class="tool-line"><span>Premium</span><strong>${escapeHtml(premium.provider || "unknown")}</strong></div>
      <div class="tool-line stacked"><span>Premium status</span><strong>${escapeHtml(premium.available ? "available" : "unavailable")} · ${escapeHtml(premium.mode || "unknown")}</strong></div>
      <div class="tool-line stacked"><span>Policy source</span><strong>${escapeHtml(premium.policy_source || "default")}</strong></div>
      <div class="tool-line"><span>Web search</span><strong>${escapeHtml(status.provider)}</strong></div>
      <div class="tool-line"><span>Estado</span><strong>${status.available ? "conectado" : "demo"}</strong></div>
      <div class="tool-line"><span>Caché</span><strong>${status.cache_entries}</strong></div>
      <div class="tool-line"><span>PDF/DOCX</span><strong>${docs.pdf_text && docs.docx ? "activo" : "parcial"}</strong></div>
      <div class="tool-line"><span>OCR</span><strong>${docs.ocr.available ? "activo" : "opcional"}</strong></div>
      <div class="tool-line"><span>Intel IA</span><strong>${knowledge.briefs} fichas</strong></div>
    `;
    hydrateRuntimePolicyForm(runtimePolicy);
  } catch (error) {
    toolsStatus.textContent = `No disponible: ${error.message}`;
  }
}

loadToolsStatus();
loadKnowledgeBlocks();
renderKnowledgeSearchResults([], "");

if (scannerArtifacts && !scannerArtifacts.value.trim()) {
  scannerArtifacts.value = DEFAULT_SCANNER_ARTIFACTS;
}

uploadForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = documentFile.files?.[0];
  if (!file) {
    uploadResult.textContent = "Selecciona un archivo.";
    return;
  }

  uploadButton.disabled = true;
  uploadResult.textContent = "Extrayendo e indexando...";
  try {
    const body = new FormData();
    body.append("file", file);
    body.append("title", file.name);
    const response = await fetch("/documents", {
      method: "POST",
      headers: tenantHeaders(),
      body,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    uploadResult.innerHTML = `
      <div class="tool-line"><span>Parser</span><strong>${escapeHtml(payload.parser)}</strong></div>
      <div class="tool-line"><span>Chunks</span><strong>${payload.chunks}</strong></div>
      <div>${escapeHtml((payload.text_preview || "").slice(0, 180))}</div>
    `;
  } catch (error) {
    uploadResult.textContent = `Error: ${error.message}`;
  } finally {
    uploadButton.disabled = false;
    documentFile.value = "";
  }
});

knowledgeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const file = knowledgeFile.files?.[0];
  if (!file) {
    knowledgeResult.textContent = "Selecciona un archivo.";
    return;
  }

  knowledgeButton.disabled = true;
  knowledgeResult.textContent = "Compactando e indexando novedad...";
  try {
    const body = new FormData();
    body.append("file", file);
    if (knowledgeTitle.value.trim()) body.append("title", knowledgeTitle.value.trim());
    if (knowledgeSourceUrl.value.trim()) body.append("source_url", knowledgeSourceUrl.value.trim());
    body.append("source_type", "daily_ai_update");
    body.append("scope", "global");
    const response = await fetch("/knowledge/updates", {
      method: "POST",
      headers: tenantHeaders({ "X-User-Id": "web-technician" }),
      body,
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    knowledgeResult.innerHTML = `
      <div class="tool-line"><span>Estado</span><strong>${escapeHtml(payload.status)}</strong></div>
      <div class="tool-line stacked"><span>Título</span><strong>${escapeHtml(payload.brief.title)}</strong></div>
      <div class="tool-line stacked"><span>Tags</span><strong>${escapeHtml((payload.brief.tags || []).join(", "))}</strong></div>
      <div class="tool-line"><span>Chunks RAG</span><strong>${payload.rag_chunks}</strong></div>
      <div>${escapeHtml((payload.brief.summary || "").slice(0, 260))}</div>
    `;
    loadToolsStatus();
    loadKnowledgeBlocks();
    if (lastKnowledgeQuery) searchKnowledge(lastKnowledgeQuery);
  } catch (error) {
    knowledgeResult.textContent = `Error: ${error.message}`;
  } finally {
    knowledgeButton.disabled = false;
    knowledgeFile.value = "";
  }
});

knowledgeSearchForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await searchKnowledge(knowledgeSearchInput.value);
});

processScannerForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const artifacts = parseScannerArtifacts(scannerArtifacts.value);
  if (!artifacts.length) {
    scannerResult.textContent = "Añade al menos un artefacto de proceso.";
    return;
  }

  scannerButton.disabled = true;
  scannerResult.textContent = "Analizando proceso y preparando sandbox...";
  try {
    const response = await fetch("/process-scanner/analyze", {
      method: "POST",
      headers: tenantHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        company_name: clientName.value || "Demo SL",
        employee_count: 500,
        objective: scannerObjective.value || "Detectar automatizaciones seguras",
        risk_tolerance: scannerRisk.value || "medium",
        artifacts,
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    renderScannerResult(payload);
  } catch (error) {
    scannerResult.textContent = `Error: ${error.message}`;
  } finally {
    scannerButton.disabled = false;
  }
});

opportunityForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  await runOpportunityDiagnosis(opportunityQuestion.value);
});

quickIntakeForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const generatedQuestion = buildQuestionFromQuickIntake();
  opportunityQuestion.value = generatedQuestion;
  opportunityEmployeeCount.value = quickEmployeeBand.value || "250";
  await runOpportunityDiagnosis(generatedQuestion);
});

runtimePolicyForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  runtimePolicyButton.disabled = true;
  runtimePolicyResult.textContent = "Saving runtime policy...";
  try {
    const response = await fetch("/tools/runtime-policy", {
      method: "POST",
      headers: tenantHeaders({ "Content-Type": "application/json" }),
      body: JSON.stringify({
        premium_provider: runtimePremiumProvider.value,
        escalation_enabled: runtimeEscalationEnabled.checked,
        escalation_allow_sensitive: runtimeAllowSensitive.checked,
        escalation_allowed_intents: runtimeAllowedIntents.value.trim(),
      }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
    hydrateRuntimePolicyForm(payload);
    await loadToolsStatus();
  } catch (error) {
    runtimePolicyResult.textContent = `Error: ${error.message}`;
  } finally {
    runtimePolicyButton.disabled = false;
  }
});

tenantId?.addEventListener("change", () => {
  runtimePolicyLoadedForTenant = null;
  loadToolsStatus();
});

clientName?.addEventListener("change", () => {
  if (runtimePolicyLoadedForTenant !== (tenantId.value || "demo-tenant")) {
    loadToolsStatus();
  }
});
