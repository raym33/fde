const state = {
  labs: [],
  allReports: [],
  reports: [],
  runs: [],
  changes: [],
  featureFlags: [],
  status: "",
  busy: false,
};

const els = {
  labsCount: document.querySelector("#labsCount"),
  proposedCount: document.querySelector("#proposedCount"),
  approvedCount: document.querySelector("#approvedCount"),
  implementedCount: document.querySelector("#implementedCount"),
  labsList: document.querySelector("#labsList"),
  reportsList: document.querySelector("#reportsList"),
  runsTable: document.querySelector("#runsTable"),
  changesList: document.querySelector("#changesList"),
  flagsList: document.querySelector("#flagsList"),
  runAllButton: document.querySelector("#runAllButton"),
  refreshButton: document.querySelector("#refreshButton"),
  statusFilter: document.querySelector("#statusFilter"),
  toast: document.querySelector("#toast"),
  reportDialog: document.querySelector("#reportDialog"),
  reportDetail: document.querySelector("#reportDetail"),
};

function labName(labId) {
  return state.labs.find((lab) => lab.id === labId)?.name || labId;
}

function formatDate(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("es-ES", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("visible");
  window.clearTimeout(showToast.timeout);
  showToast.timeout = window.setTimeout(() => {
    els.toast.classList.remove("visible");
  }, 2800);
}

function setBusy(isBusy) {
  state.busy = isBusy;
  els.runAllButton.disabled = isBusy;
  els.refreshButton.disabled = isBusy;
  document.querySelectorAll("[data-run-lab], [data-decision], [data-apply-change]").forEach((button) => {
    button.disabled = isBusy;
  });
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

async function loadData() {
  setBusy(true);
  try {
    const statusQuery = state.status ? `?status=${encodeURIComponent(state.status)}` : "";
    const [catalog, allReports, reports, runs, changes, featureFlags] = await Promise.all([
      api("/labs/catalog"),
      api("/labs/reports"),
      api(`/labs/reports${statusQuery}`),
      api("/labs/runs?limit=20"),
      api("/labs/changes"),
      api("/labs/feature-flags"),
    ]);
    state.labs = catalog.labs;
    state.allReports = allReports.reports;
    state.reports = reports.reports;
    state.runs = runs.runs;
    state.changes = changes.changes;
    state.featureFlags = featureFlags.feature_flags;
    render();
  } catch (error) {
    showToast(`Error: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

async function runLab(labId = null) {
  setBusy(true);
  try {
    const payload = { triggered_by: "admin_ui" };
    if (labId) payload.lab_id = labId;
    const result = await api("/labs/experiments/run", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showToast(`${result.runs.length} run(s), ${result.reports.length} report(s) proposed`);
    await loadData();
  } catch (error) {
    showToast(`Error: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

async function decide(reportId, decision) {
  const notesByDecision = {
    approve: "Approved from Labs admin UI.",
    reject: "Rejected from Labs admin UI.",
    implement: "Marked as implemented from Labs admin UI.",
  };
  setBusy(true);
  try {
    await api(`/labs/reports/${reportId}/decision`, {
      method: "POST",
      body: JSON.stringify({
        decision,
        decided_by: "admin_ui",
        notes: notesByDecision[decision],
      }),
    });
    showToast(`Report ${decision} completed`);
    await loadData();
  } catch (error) {
    showToast(`Error: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

async function applyChange(changeId) {
  setBusy(true);
  try {
    await api(`/labs/changes/${changeId}/apply`, {
      method: "POST",
      body: JSON.stringify({ applied_by: "admin_ui" }),
    });
    showToast("Core change applied");
    await loadData();
  } catch (error) {
    showToast(`Error: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

function render() {
  renderMetrics();
  renderLabs();
  renderReports();
  renderChanges();
  renderFeatureFlags();
  renderRuns();
}

function renderMetrics() {
  const reports = state.allReports;
  els.labsCount.textContent = state.labs.length;
  els.proposedCount.textContent = reports.filter((report) => report.status === "proposed").length;
  els.approvedCount.textContent = reports.filter((report) => report.status === "approved").length;
  els.implementedCount.textContent = reports.filter((report) => report.status === "implemented").length;
}

function renderLabs() {
  els.labsList.innerHTML = state.labs
    .map(
      (lab) => `
      <article class="lab-row">
        <div class="lab-row-header">
          <div>
            <h3>${escapeHtml(lab.name)}</h3>
            <p>${escapeHtml(lab.mission)}</p>
          </div>
          <button class="button small secondary" data-run-lab="${escapeHtml(lab.id)}">Run</button>
        </div>
        <div class="meta-line">
          <span class="pill">${escapeHtml(lab.cadence)}</span>
          <span class="pill">${escapeHtml(lab.capability)}</span>
          <span class="pill">${lab.threshold_pct}% threshold</span>
        </div>
      </article>
    `,
    )
    .join("");
}

function renderReports() {
  if (!state.reports.length) {
    els.reportsList.innerHTML = `<div class="empty">No reports for this filter.</div>`;
    return;
  }

  els.reportsList.innerHTML = state.reports
    .map((report) => {
      const improvement = getImprovement(report);
      const canApprove = report.status === "proposed";
      const canReject = report.status === "proposed";
      const canImplement = report.status === "approved";
      return `
        <article class="report-row">
          <div class="report-row-header">
            <div>
              <h3>${escapeHtml(report.title)}</h3>
              <p>${escapeHtml(report.summary)}</p>
            </div>
            <span class="pill ${escapeHtml(report.status)}">${escapeHtml(report.status)}</span>
          </div>
          <div class="meta-line" style="margin-top: 10px;">
            <span class="pill">${escapeHtml(labName(report.lab_id))}</span>
            <span class="pill">Risk: ${escapeHtml(report.risk_level)}</span>
            <span class="pill">${formatDate(report.created_at)}</span>
          </div>
          <div class="score-line">
            <div class="bar"><span style="width:${Math.min(100, Math.max(0, improvement))}%"></span></div>
            <strong>${improvement.toFixed(1)}%</strong>
          </div>
          <div class="report-actions">
            <button class="button small secondary" data-view-report="${escapeHtml(report.id)}">Details</button>
            <button class="button small success" data-decision="approve" data-report-id="${escapeHtml(report.id)}" ${canApprove ? "" : "disabled"}>Approve</button>
            <button class="button small danger" data-decision="reject" data-report-id="${escapeHtml(report.id)}" ${canReject ? "" : "disabled"}>Reject</button>
            <button class="button small primary" data-decision="implement" data-report-id="${escapeHtml(report.id)}" ${canImplement ? "" : "disabled"}>Implement</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderChanges() {
  if (!state.changes.length) {
    els.changesList.innerHTML = `<div class="empty">No staged changes yet. Approve a report first.</div>`;
    return;
  }

  els.changesList.innerHTML = state.changes
    .slice(0, 8)
    .map((change) => {
      const canApply = change.status === "staged";
      return `
        <article class="change-row">
          <div class="change-row-header">
            <div>
              <h3>${escapeHtml(change.target_key)}</h3>
              <p>${escapeHtml(change.feature_flag)}</p>
            </div>
            <span class="pill ${escapeHtml(change.status)}">${escapeHtml(change.status)}</span>
          </div>
          <div class="meta-line" style="margin-top: 10px;">
            <span class="pill">${escapeHtml(change.target_type)}</span>
            <span class="pill">${escapeHtml(labName(change.lab_id))}</span>
            <span class="pill">${formatDate(change.created_at)}</span>
          </div>
          <div class="report-actions">
            <button class="button small primary" data-apply-change="${escapeHtml(change.id)}" ${canApply ? "" : "disabled"}>Apply Flag</button>
            <button class="button small secondary" data-view-change="${escapeHtml(change.id)}">Payload</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderFeatureFlags() {
  if (!state.featureFlags.length) {
    els.flagsList.innerHTML = `<div class="empty">No feature flags yet.</div>`;
    return;
  }

  els.flagsList.innerHTML = state.featureFlags
    .map(
      (flag) => `
      <article class="flag-row">
        <div class="flag-row-header">
          <div>
            <h3>${escapeHtml(flag.feature_flag)}</h3>
            <p>${escapeHtml(flag.target_key)}</p>
          </div>
          <span class="pill ${flag.enabled ? "implemented" : "proposed"}">${flag.enabled ? "enabled" : "off"}</span>
        </div>
        <div class="meta-line" style="margin-top: 10px;">
          <span class="pill">${escapeHtml(flag.target_type)}</span>
          <span class="pill">applied: ${flag.applied_count || 0}</span>
          <span class="pill">staged: ${flag.staged_count || 0}</span>
        </div>
      </article>
    `,
    )
    .join("");
}

function renderRuns() {
  if (!state.runs.length) {
    els.runsTable.innerHTML = `<tr><td colspan="6">No lab runs yet.</td></tr>`;
    return;
  }
  els.runsTable.innerHTML = state.runs
    .map(
      (run) => `
      <tr>
        <td>${escapeHtml(labName(run.lab_id))}</td>
        <td><span class="pill">${escapeHtml(run.status)}</span></td>
        <td>${run.baseline_score.toFixed(2)}</td>
        <td>${run.new_score.toFixed(2)}</td>
        <td><strong>${run.improvement_pct.toFixed(2)}%</strong></td>
        <td>${formatDate(run.started_at)}</td>
      </tr>
    `,
    )
    .join("");
}

function showReport(reportId) {
  const report = state.reports.find((item) => item.id === reportId);
  if (!report) return;
  els.reportDetail.innerHTML = `
    <div class="detail-grid">
      <div>
        <p class="eyebrow">${escapeHtml(labName(report.lab_id))}</p>
        <h2>${escapeHtml(report.title)}</h2>
        <p>${escapeHtml(report.summary)}</p>
        <div class="meta-line">
          <span class="pill ${escapeHtml(report.status)}">${escapeHtml(report.status)}</span>
          <span class="pill">Risk: ${escapeHtml(report.risk_level)}</span>
          <span class="pill">${formatDate(report.created_at)}</span>
        </div>
      </div>
      <div class="detail-block">
        <h3>Recommendation</h3>
        <p>${escapeHtml(report.recommendation)}</p>
      </div>
      <div class="detail-block">
        <h3>Rollout Plan</h3>
        <p>${escapeHtml(report.rollout_plan)}</p>
      </div>
      <div class="detail-block">
        <h3>Rollback Plan</h3>
        <p>${escapeHtml(report.rollback_plan)}</p>
      </div>
      <div class="detail-block">
        <h3>Evidence</h3>
        <pre>${escapeHtml(JSON.stringify(report.evidence, null, 2))}</pre>
      </div>
      <div class="detail-block">
        <h3>Metrics</h3>
        <pre>${escapeHtml(JSON.stringify(report.metrics, null, 2))}</pre>
      </div>
    </div>
  `;
  els.reportDialog.showModal();
}

function showChange(changeId) {
  const change = state.changes.find((item) => item.id === changeId);
  if (!change) return;
  els.reportDetail.innerHTML = `
    <div class="detail-grid">
      <div>
        <p class="eyebrow">${escapeHtml(labName(change.lab_id))}</p>
        <h2>${escapeHtml(change.target_key)}</h2>
        <p>${escapeHtml(change.feature_flag)}</p>
        <div class="meta-line">
          <span class="pill ${escapeHtml(change.status)}">${escapeHtml(change.status)}</span>
          <span class="pill">${escapeHtml(change.target_type)}</span>
          <span class="pill">${formatDate(change.created_at)}</span>
        </div>
      </div>
      <div class="detail-block">
        <h3>Payload</h3>
        <pre>${escapeHtml(JSON.stringify(change.payload, null, 2))}</pre>
      </div>
      <div class="detail-block">
        <h3>Rollback</h3>
        <pre>${escapeHtml(JSON.stringify(change.rollback, null, 2))}</pre>
      </div>
    </div>
  `;
  els.reportDialog.showModal();
}

function getImprovement(report) {
  const baseline = report.metrics?.baseline;
  const candidate = report.metrics?.candidate;
  if (!baseline || !candidate) return 0;
  const baselineAvg = averageObjectNumbers(baseline);
  const candidateAvg = averageObjectNumbers(candidate);
  if (baselineAvg <= 0) return 0;
  return ((candidateAvg - baselineAvg) / baselineAvg) * 100;
}

function averageObjectNumbers(value) {
  const nums = Object.values(value).filter((item) => typeof item === "number");
  if (!nums.length) return 0;
  return nums.reduce((sum, item) => sum + item, 0) / nums.length;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

document.addEventListener("click", (event) => {
  const runButton = event.target.closest("[data-run-lab]");
  if (runButton) runLab(runButton.dataset.runLab);

  const decisionButton = event.target.closest("[data-decision]");
  if (decisionButton) decide(decisionButton.dataset.reportId, decisionButton.dataset.decision);

  const viewButton = event.target.closest("[data-view-report]");
  if (viewButton) showReport(viewButton.dataset.viewReport);

  const applyButton = event.target.closest("[data-apply-change]");
  if (applyButton) applyChange(applyButton.dataset.applyChange);

  const viewChangeButton = event.target.closest("[data-view-change]");
  if (viewChangeButton) showChange(viewChangeButton.dataset.viewChange);
});

els.runAllButton.addEventListener("click", () => runLab());
els.refreshButton.addEventListener("click", loadData);
els.statusFilter.addEventListener("change", (event) => {
  state.status = event.target.value;
  loadData();
});

loadData();
