const form = document.querySelector("#chatForm");
const input = document.querySelector("#messageInput");
const messages = document.querySelector("#messages");
const sendButton = document.querySelector("#sendButton");
const statePill = document.querySelector("#connectionState");
const tenantId = document.querySelector("#tenantId");
const clientName = document.querySelector("#clientName");
const toolsStatus = document.querySelector("#toolsStatus");
const uploadForm = document.querySelector("#uploadForm");
const documentFile = document.querySelector("#documentFile");
const uploadButton = document.querySelector("#uploadButton");
const uploadResult = document.querySelector("#uploadResult");
const runtimeMode = document.querySelector("#runtimeMode");
const knowledgeForm = document.querySelector("#knowledgeForm");
const knowledgeFile = document.querySelector("#knowledgeFile");
const knowledgeTitle = document.querySelector("#knowledgeTitle");
const knowledgeSourceUrl = document.querySelector("#knowledgeSourceUrl");
const knowledgeButton = document.querySelector("#knowledgeButton");
const knowledgeResult = document.querySelector("#knowledgeResult");

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

async function loadToolsStatus() {
  try {
    const [searchResponse, documentResponse, lmStudioResponse, knowledgeResponse] = await Promise.all([
      fetch("/tools/web-search/status"),
      fetch("/documents/status"),
      fetch("/tools/lm-studio/status"),
      fetch("/knowledge/updates/status"),
    ]);
    const status = await searchResponse.json();
    const docs = await documentResponse.json();
    const lmStudio = await lmStudioResponse.json();
    const knowledge = await knowledgeResponse.json();
    const activeNodes = (lmStudio.nodes || []).filter((node) => node.available);
    const firstNode = activeNodes[0];
    const localModel = lmStudio.enabled
      ? lmStudio.chat_model || "configurado"
      : "desactivado";
    runtimeMode.textContent = lmStudio.enabled && firstNode
      ? `LM Studio local activo con ${localModel}. Modo demo mantiene búsqueda externa simulada si no hay claves.`
      : "Modo demo activo: sin LLM local conectado, respuestas deterministas cuando aplica.";
    toolsStatus.innerHTML = `
      <div class="tool-line"><span>LM Studio</span><strong>${lmStudio.enabled && firstNode ? "activo" : "inactivo"}</strong></div>
      <div class="tool-line stacked"><span>Modelo chat</span><strong>${escapeHtml(localModel)}</strong></div>
      <div class="tool-line stacked"><span>Nodo local</span><strong>${escapeHtml(firstNode?.base_url || "sin nodo disponible")}</strong></div>
      <div class="tool-line stacked"><span>Modelos LAN</span><strong>${escapeHtml(activeNodes.flatMap((node) => node.models || []).join(", ") || "ninguno")}</strong></div>
      <div class="tool-line"><span>Web search</span><strong>${escapeHtml(status.provider)}</strong></div>
      <div class="tool-line"><span>Estado</span><strong>${status.available ? "conectado" : "demo"}</strong></div>
      <div class="tool-line"><span>Caché</span><strong>${status.cache_entries}</strong></div>
      <div class="tool-line"><span>PDF/DOCX</span><strong>${docs.pdf_text && docs.docx ? "activo" : "parcial"}</strong></div>
      <div class="tool-line"><span>OCR</span><strong>${docs.ocr.available ? "activo" : "opcional"}</strong></div>
      <div class="tool-line"><span>Intel IA</span><strong>${knowledge.briefs} fichas</strong></div>
    `;
  } catch (error) {
    toolsStatus.textContent = `No disponible: ${error.message}`;
  }
}

loadToolsStatus();

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
      headers: {
        "X-Tenant-Id": tenantId.value || "demo-tenant",
        "X-User-Id": "web-user",
        "X-Client-Name": clientName.value || tenantId.value || "Demo SL",
      },
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
      headers: {
        "X-Tenant-Id": tenantId.value || "demo-tenant",
        "X-User-Id": "web-technician",
        "X-Client-Name": clientName.value || tenantId.value || "Demo SL",
      },
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
  } catch (error) {
    knowledgeResult.textContent = `Error: ${error.message}`;
  } finally {
    knowledgeButton.disabled = false;
    knowledgeFile.value = "";
  }
});
