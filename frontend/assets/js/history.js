/**
 * CropPulse – History Page JS
 * Displays paginated disease + soil prediction history with filters.
 */

let currentPage = 1;
let currentType = "all";
const PAGE_SIZE = 10;

document.addEventListener("DOMContentLoaded", () => {
  Auth.requireAuth();
  setupFilters();
  loadHistory();
});

function setupFilters() {
  document.querySelectorAll(".history-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".history-filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      currentType = btn.dataset.type || "all";
      currentPage = 1;
      loadHistory();
    });
  });

  // Search
  const searchInput = document.getElementById("history-search");
  if (searchInput) {
    searchInput.addEventListener("input", Utils.debounce(() => {
      const term = searchInput.value.trim().toLowerCase();
      filterRows(term);
    }, 400));
  }
}

async function loadHistory() {
  const container = document.getElementById("history-container");
  if (!container) return;
  Utils.showSkeleton("history-container", 5, "80px");

  try {
    const data = await CropPulseAPI.history.getCombined(currentPage, PAGE_SIZE, currentType);
    renderHistory(data);
  } catch (e) {
    container.innerHTML = `<div class="text-center py-5 text-muted">Failed to load history. <button onclick="loadHistory()" class="btn-ag-secondary ms-2">Retry</button></div>`;
    Utils.showToast("Could not load prediction history.", "error");
  }
}

function renderHistory(data) {
  const container = document.getElementById("history-container");
  if (!container) return;

  const diseaseRows = (data.disease_predictions || []).map(p => renderDiseaseRow(p));
  const soilRows    = (data.soil_predictions || []).map(p => renderSoilRow(p));

  let rows = [];
  if (currentType === "all")     rows = [...diseaseRows, ...soilRows].sort((a, b) => b.ts - a.ts);
  else if (currentType === "disease") rows = diseaseRows;
  else rows = soilRows;

  if (!rows.length) {
    container.innerHTML = `
      <div class="text-center py-5">
        <div style="font-size:3rem;margin-bottom:1rem;">📂</div>
        <h5 style="color:var(--text-muted);">No predictions found</h5>
        <p class="text-muted">Start by uploading a leaf image or running a soil analysis.</p>
        <div class="d-flex gap-3 justify-content-center mt-3">
          <a href="/upload.html" class="btn-ag-primary">🌿 Detect Disease</a>
          <a href="/soil-prediction.html" class="btn-ag-secondary">💧 Soil Analysis</a>
        </div>
      </div>`;
    return;
  }

  container.innerHTML = `
    <div class="ag-table-wrapper">
      <table class="ag-table" id="history-table">
        <thead>
          <tr>
            <th>Type</th>
            <th>Result</th>
            <th>Status / Severity</th>
            <th>Confidence / Moisture</th>
            <th>Date</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          ${rows.map(r => r.html).join("")}
        </tbody>
      </table>
    </div>`;

  // Update total count
  const totalEl = document.getElementById("history-total");
  if (totalEl) totalEl.textContent = `${data.total || rows.length} predictions`;

  // Pagination
  Utils.renderPagination("history-pagination", data.total || rows.length, currentPage, PAGE_SIZE, (p) => {
    currentPage = p;
    loadHistory();
  });
}

function renderDiseaseRow(p) {
  const ts = new Date(p.created_at).getTime();
  const html = `
    <tr data-search="${(p.disease_name || "").toLowerCase()} ${(p.crop_type || "").toLowerCase()}">
      <td><span style="background:rgba(220,38,38,0.15);color:#ef4444;padding:3px 8px;border-radius:20px;font-size:0.75rem;font-weight:600;">🦠 Disease</span></td>
      <td>
        <div class="d-flex align-items-center gap-2">
          <img src="${p.image_url || ''}" alt="" style="width:36px;height:36px;border-radius:6px;object-fit:cover;" onerror="this.style.display='none'">
          <div>
            <div class="truncate" style="max-width:200px;font-weight:600;font-size:0.85rem;color:var(--text-primary);">${p.disease_name || "Unknown"}</div>
            <small class="text-muted">${p.crop_type || "—"}</small>
          </div>
        </div>
      </td>
      <td>${Utils.severityBadge(p.severity || "unknown")}</td>
      <td><strong style="color:var(--primary-light);">${Utils.formatConfidence(p.confidence || 0)}</strong></td>
      <td><small class="text-muted">${Utils.formatDateTime(p.created_at)}</small></td>
      <td>
        <a href="/disease-result.html?id=${p.prediction_id}" class="btn-ag-icon" title="View Details">👁️</a>
      </td>
    </tr>`;
  return { html, ts };
}

function renderSoilRow(p) {
  const ts = new Date(p.created_at).getTime();
  const html = `
    <tr data-search="soil moisture ${p.irrigation_type || ""}">
      <td><span style="background:rgba(37,99,235,0.15);color:#3b82f6;padding:3px 8px;border-radius:20px;font-size:0.75rem;font-weight:600;">💧 Soil</span></td>
      <td>
        <div>
          <div class="fw-600" style="font-size:0.85rem;color:var(--text-primary);">Moisture: ${Utils.formatMoisture(p.predicted_moisture)}</div>
          <small class="text-muted">Water req: ${p.water_requirement_mm?.toFixed(1) || 0} mm</small>
        </div>
      </td>
      <td>
        <span class="badge-severity ${p.irrigation_recommended ? 'moderate' : 'healthy'}">
          ${p.irrigation_recommended ? "💧 Irrigate" : "✅ OK"}
        </span>
      </td>
      <td><span style="text-transform:capitalize;font-size:0.85rem;">${p.irrigation_type || "none"}</span></td>
      <td><small class="text-muted">${Utils.formatDateTime(p.created_at)}</small></td>
      <td>
        <span class="btn-ag-icon" title="No detail view for soil" style="opacity:0.4;cursor:default;">👁️</span>
      </td>
    </tr>`;
  return { html, ts };
}

function filterRows(term) {
  if (!term) {
    document.querySelectorAll("#history-table tbody tr").forEach(r => r.style.display = "");
    return;
  }
  document.querySelectorAll("#history-table tbody tr").forEach(r => {
    const searchData = r.dataset.search || "";
    r.style.display = searchData.includes(term) ? "" : "none";
  });
}

// Export CSV
document.getElementById("export-csv-btn")?.addEventListener("click", async () => {
  try {
    const data = await CropPulseAPI.history.getCombined(1, 500, "all");
    const rows = [["Type","Result","Severity/Status","Value","Date"]];
    (data.disease_predictions || []).forEach(p => {
      rows.push(["Disease", p.disease_name, p.severity, `${(p.confidence*100).toFixed(1)}%`, p.created_at]);
    });
    (data.soil_predictions || []).forEach(p => {
      rows.push(["Soil", `Moisture ${p.predicted_moisture?.toFixed(1)}%`, p.irrigation_recommended?"Irrigate":"OK", p.irrigation_type, p.created_at]);
    });
    const csv = rows.map(r => r.map(v => `"${v}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    Utils.downloadURL(URL.createObjectURL(blob), `CropPulse_history_${Date.now()}.csv`);
    Utils.showToast("CSV exported!", "success");
  } catch { Utils.showToast("Export failed.", "error"); }
});
