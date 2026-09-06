/**
 * CropPulse – Admin Panel JS
 * Handles admin dashboard analytics, user management, and outbreak monitoring.
 */

document.addEventListener("DOMContentLoaded", () => {
  Auth.requireAdmin();
  const page = document.body.dataset.adminPage || "dashboard";
  if (page === "dashboard")  initAdminDashboard();
  if (page === "users")      initUserManagement();
  if (page === "analytics")  initAnalytics();
  if (page === "reports")    initAdminReports();
});

// ── Admin Dashboard ─────────────────────────────────────────────────────────
async function initAdminDashboard() {
  try {
    Utils.showLoading("Loading admin dashboard...");
    const data = await CropPulseAPI.admin.getAnalytics();
    Utils.hideLoading();
    renderAdminStats(data);
    renderAdminCharts(data);
    loadOutbreaks();
  } catch (e) {
    Utils.hideLoading();
    Utils.showToast("Failed to load admin dashboard.", "error");
  }
}

function renderAdminStats(data) {
  const users = data.users || {};
  const dp    = data.disease_predictions || {};
  const sp    = data.soil_predictions || {};
  const farms = data.farms || {};

  setEl("admin-total-users",       users.total || 0);
  setEl("admin-active-users",      users.active || 0);
  setEl("admin-total-disease",     dp.total || 0);
  setEl("admin-total-soil",        sp.total || 0);
  setEl("admin-total-farms",       farms.total || 0);
  setEl("admin-total-predictions", data.platform_totals?.total_predictions || 0);

  ["admin-total-users","admin-active-users","admin-total-disease","admin-total-soil",
   "admin-total-farms","admin-total-predictions"].forEach(id => {
    const el = document.getElementById(id);
    if (el) { const v = parseInt(el.textContent); el.textContent = 0; Utils.animateCounter(el, v, 1000); }
  });
}

function setEl(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function renderAdminCharts(data) {
  const dp = data.disease_predictions || {};
  Charts.renderSeverityDonut("admin-severity-chart",  dp.severity_breakdown || {});
  Charts.renderTopDiseases("admin-top-diseases-chart", dp.top_diseases || []);
  Charts.renderCropStats("admin-crop-stats-chart", Object.fromEntries((dp.top_crops || []).map(c => [c.crop, c.count])));
}

async function loadOutbreaks() {
  const el = document.getElementById("outbreak-list");
  if (!el) return;
  try {
    const data = await CropPulseAPI.admin.getOutbreaks("severe");
    if (!data.hotspots?.length && !data.outbreaks?.length) {
      el.innerHTML = '<div class="text-muted text-center py-3">No severe outbreaks detected.</div>';
      return;
    }
    const outbreaks = data.outbreaks || data.hotspots || [];
    el.innerHTML = outbreaks.slice(0, 8).map(o => `
      <div class="d-flex align-items-center gap-3 p-3 mb-2" style="background:rgba(220,38,38,0.08);border:1px solid rgba(220,38,38,0.2);border-radius:10px;">
        <div style="font-size:1.3rem;">🔴</div>
        <div style="flex:1;min-width:0;">
          <div class="fw-600 truncate" style="font-size:0.88rem;">${o.disease_name || "Unknown Disease"}</div>
          <small class="text-muted">${[o.district, o.state].filter(Boolean).join(", ") || "Location unknown"}</small>
        </div>
        <div>${Utils.severityBadge(o.severity || "severe")}</div>
      </div>
    `).join("");
  } catch { el.innerHTML = '<div class="text-muted text-center py-3">Failed to load outbreaks.</div>'; }
}

// ── User Management ─────────────────────────────────────────────────────────
let usersPage = 1;
let usersRole = "all";

async function initUserManagement() {
  loadUsers();
  document.querySelectorAll(".role-filter-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".role-filter-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      usersRole = btn.dataset.role || "all";
      usersPage = 1;
      loadUsers();
    });
  });
  document.getElementById("user-search")?.addEventListener("input", Utils.debounce(e => {
    filterUserRows(e.target.value.toLowerCase());
  }, 400));
}

async function loadUsers() {
  Utils.showSkeleton("users-table-body", 5, "50px");
  try {
    const data = await CropPulseAPI.admin.getUsers(usersPage, usersRole);
    renderUsersTable(data);
  } catch { Utils.showToast("Failed to load users.", "error"); }
}

function renderUsersTable(data) {
  const tbody = document.getElementById("users-table-body");
  if (!tbody) return;

  const totalEl = document.getElementById("users-total");
  if (totalEl) totalEl.textContent = `${data.total || 0} users`;

  if (!data.users?.length) {
    tbody.innerHTML = '<tr><td colspan="6" class="text-center py-4 text-muted">No users found.</td></tr>';
    return;
  }

  tbody.innerHTML = data.users.map(u => `
    <tr id="user-row-${u.uid}">
      <td>
        <div class="d-flex align-items-center gap-2">
          <div style="width:36px;height:36px;border-radius:50%;background:var(--primary-glow);display:flex;align-items:center;justify-content:center;font-weight:700;color:var(--primary-light);flex-shrink:0;">
            ${(u.name || "U").charAt(0).toUpperCase()}
          </div>
          <div>
            <div class="fw-600" style="font-size:0.88rem;">${Utils.sanitizeHTML(u.name || "—")}</div>
            <small class="text-muted">${u.uid?.slice(0,8)}...</small>
          </div>
        </div>
      </td>
      <td><small>${Utils.sanitizeHTML(u.email || "—")}</small></td>
      <td><span style="background:${u.role==='admin'?'rgba(245,158,11,0.15)':'rgba(22,163,74,0.15)'};color:${u.role==='admin'?'#f59e0b':'#22c55e'};padding:3px 8px;border-radius:20px;font-size:0.75rem;font-weight:600;">${u.role || "farmer"}</span></td>
      <td><span class="badge-severity ${u.is_active ? 'healthy' : 'severe'}">${u.is_active ? '✅ Active' : '❌ Inactive'}</span></td>
      <td><small class="text-muted">${Utils.formatDate(u.created_at)}</small></td>
      <td>
        <div class="d-flex gap-2">
          <button class="btn-ag-icon" title="Toggle Status" onclick="toggleUserStatus('${u.uid}')">
            ${u.is_active ? '🔒' : '🔓'}
          </button>
          <button class="btn-ag-icon" title="Delete User" onclick="deleteUser('${u.uid}', '${Utils.sanitizeHTML(u.name || u.email)}')" style="color:var(--danger-light);">
            🗑️
          </button>
        </div>
      </td>
    </tr>
  `).join("");

  Utils.renderPagination("users-pagination", data.total, usersPage, 20, (p) => {
    usersPage = p; loadUsers();
  });
}

function filterUserRows(term) {
  document.querySelectorAll("#users-table-body tr").forEach(row => {
    row.style.display = row.textContent.toLowerCase().includes(term) ? "" : "none";
  });
}

async function toggleUserStatus(uid) {
  try {
    const res = await CropPulseAPI.admin.toggleStatus(uid);
    Utils.showToast(res.message, "success");
    loadUsers();
  } catch { Utils.showToast("Failed to update user status.", "error"); }
}

async function deleteUser(uid, name) {
  if (!confirm(`Are you sure you want to delete user "${name}"?\nThis action cannot be undone.`)) return;
  try {
    await CropPulseAPI.admin.deleteUser(uid);
    document.getElementById(`user-row-${uid}`)?.remove();
    Utils.showToast(`User "${name}" deleted.`, "success");
  } catch (e) { Utils.showToast(e.message || "Delete failed.", "error"); }
}

// ── Analytics ───────────────────────────────────────────────────────────────
async function initAnalytics() {
  try {
    Utils.showLoading("Loading analytics...");
    const data = await CropPulseAPI.admin.getAnalytics();
    Utils.hideLoading();
    renderAdminStats(data);
    renderAdminCharts(data);
    // Load soil-specific charts
    Charts.renderMoistureLine("admin-moisture-chart", []);
    Charts.renderWaterRadar("admin-water-radar", null, null);
  } catch { Utils.hideLoading(); Utils.showToast("Failed to load analytics.", "error"); }
}

// ── Admin Reports ───────────────────────────────────────────────────────────
async function initAdminReports() {
  try {
    const data = await CropPulseAPI.admin.getAllReports();
    const tbody = document.getElementById("reports-table-body");
    if (!tbody) return;
    if (!data.reports?.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="text-center py-4 text-muted">No reports generated yet.</td></tr>';
      return;
    }
    tbody.innerHTML = data.reports.map(r => `
      <tr>
        <td><small class="text-muted">${r.report_id?.slice(0,12)}...</small></td>
        <td><span style="text-transform:capitalize;">${r.report_type || "—"}</span></td>
        <td><small class="text-muted">${r.user_id?.slice(0,12)}...</small></td>
        <td><small>${Utils.formatDateTime(r.created_at)}</small></td>
        <td>
          <a href="${r.file_url}" target="_blank" class="btn-ag-primary" style="font-size:0.78rem;padding:0.35rem 0.75rem;">
            📥 Download
          </a>
        </td>
      </tr>
    `).join("");
  } catch { Utils.showToast("Failed to load reports.", "error"); }
}

window.toggleUserStatus = toggleUserStatus;
window.deleteUser = deleteUser;
