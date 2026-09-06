/**
 * CropPulse - Risk Assessment JS
 * Handles form submission, calls risk API, and renders risk score + breakdown.
 */

document.addEventListener("DOMContentLoaded", () => {
  Auth.requireAuth();

  // Load farms
  async function loadFarms() {
    try {
      const res = await CropPulseAPI.auth.getMyFarms();
      const farms = res.farms || [];
      const sel = document.getElementById("farm-select");
      if (!sel) return;
      farms.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f.farm_id;
        opt.textContent = f.name;
        sel.appendChild(opt);
      });
    } catch (e) { /* silent */ }
  }
  loadFarms();

  // Geolocation
  document.getElementById("get-location-btn")?.addEventListener("click", () => {
    if (!navigator.geolocation) { Utils.showToast("Geolocation not supported.", "warning"); return; }
    navigator.geolocation.getCurrentPosition(pos => {
      const latEl = document.getElementById("lat-input");
      const lonEl = document.getElementById("lon-input");
      if (latEl) latEl.value = pos.coords.latitude.toFixed(6);
      if (lonEl) lonEl.value = pos.coords.longitude.toFixed(6);
      Utils.showToast("Location captured!", "success");
    }, () => Utils.showToast("Could not get location.", "error"));
  });

  // Form submit
  document.getElementById("risk-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("assess-btn");
    btn.disabled = true;
    btn.innerHTML = '<span class="ag-spinner ag-spinner-sm"></span> Assessing...';

    const payload = {
      crop_type:            document.getElementById("crop-type")?.value,
      season:               document.getElementById("season")?.value,
      temperature:          parseFloat(document.getElementById("temperature")?.value),
      humidity:             parseFloat(document.getElementById("humidity")?.value),
      rainfall_mm:          parseFloat(document.getElementById("rainfall")?.value),
      recent_disease_count: parseInt(document.getElementById("recent-disease-count")?.value),
      latitude:             parseFloat(document.getElementById("lat-input")?.value) || null,
      longitude:            parseFloat(document.getElementById("lon-input")?.value) || null,
      farm_id:              document.getElementById("farm-select")?.value || null,
    };

    try {
      const result = await CropPulseAPI.risk.assess(payload);
      renderResult(result);
      Utils.showToast("Risk assessment complete!", "success");
    } catch (err) {
      Utils.showToast(err.message || "Assessment failed. Please try again.", "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = '&#9888;&#65039; Assess Crop Risk';
    }
  });
});

function renderResult(data) {
  const resultEl = document.getElementById("result-section");
  const emptyEl  = document.getElementById("empty-result");
  if (!resultEl) return;

  emptyEl?.classList.add("hidden");
  resultEl.classList.remove("hidden");
  resultEl.classList.add("animate-fade-up");

  // Score ring
  const score = data.risk_score ?? 0;
  const circumference = 408.4;
  const offset = circumference - (score / 100) * circumference;
  const circle = document.getElementById("risk-circle");
  const levelColors = { low: "#22c55e", moderate: "#eab308", high: "#f97316", critical: "#ef4444" };
  const level = data.risk_level || "moderate";
  setTimeout(() => {
    if (circle) {
      circle.style.strokeDashoffset = offset;
      circle.style.stroke = levelColors[level] || "#f97316";
    }
    const scoreEl = document.getElementById("risk-score-val");
    if (scoreEl) Utils.animateCounter(scoreEl, score, 1500);
  }, 200);

  // Level badge
  const badgeEl = document.getElementById("risk-level-badge");
  const badgeLabels = { low: "Low Risk", moderate: "Moderate Risk", high: "High Risk", critical: "Critical Risk" };
  const badgeIcons = { low: "&#127807;", moderate: "&#9888;&#65039;", high: "&#128293;", critical: "&#128680;" };
  if (badgeEl) {
    badgeEl.innerHTML = '<span class="risk-badge-xl risk-' + level + '">' +
      (badgeIcons[level] || "") + ' ' + (badgeLabels[level] || level.toUpperCase()) + '</span>';
  }

  // Summary
  const summaryEl = document.getElementById("risk-summary");
  if (summaryEl) summaryEl.textContent = data.summary || "Risk assessment completed.";

  // Factor breakdown
  const factorsEl = document.getElementById("risk-factors");
  if (factorsEl && data.factors) {
    factorsEl.innerHTML = Object.entries(data.factors).map(([key, val]) => {
      const pct = Math.min(100, Math.max(0, val));
      const barColor = pct > 70 ? "#ef4444" : pct > 40 ? "#f97316" : "#22c55e";
      const label = key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
      return '<div class="factor-row">' +
        '<div style="width:160px;font-size:0.82rem;color:var(--text-secondary);">' + label + '</div>' +
        '<div class="factor-bar-outer"><div class="factor-bar-inner" style="width:' + pct + '%;background:' + barColor + ';"></div></div>' +
        '<div style="width:40px;font-size:0.78rem;font-weight:600;text-align:right;color:var(--text-primary);">' + pct.toFixed(0) + '</div>' +
        '</div>';
    }).join("");
  }

  // Actions
  const actionsEl = document.getElementById("risk-actions");
  if (actionsEl && data.recommended_actions?.length) {
    actionsEl.innerHTML = data.recommended_actions.map((action, i) =>
      '<div class="d-flex gap-2 mb-2">' +
      '<span style="color:var(--primary-light);font-weight:700;flex-shrink:0;">' + (i + 1) + '.</span>' +
      '<div style="font-size:0.88rem;color:var(--text-secondary);">' + action + '</div>' +
      '</div>'
    ).join("");
  } else if (actionsEl) {
    actionsEl.innerHTML = '<p class="text-muted" style="font-size:0.85rem;">No specific actions required. Crop risk is within acceptable range.</p>';
  }
}
