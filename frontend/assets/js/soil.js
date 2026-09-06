/**
 * CropPulse – Soil Prediction Page JS
 * Handles soil form submission, result display, and chart rendering.
 */

document.addEventListener("DOMContentLoaded", () => {
  Auth.requireAuth();
  loadFarms();
  setupSoilTypeVisual();

  document.getElementById("soil-form")?.addEventListener("submit", handleSubmit);
  document.getElementById("get-location-btn")?.addEventListener("click", getLocation);
});

async function loadFarms() {
  try {
    const res = await CropPulseAPI.auth.getMyFarms();
    const sel = document.getElementById("farm-select");
    if (!sel) return;
    sel.innerHTML = '<option value="">No specific farm</option>';
    (res.farms || []).forEach(f => {
      const opt = document.createElement("option");
      opt.value = f.farm_id;
      opt.textContent = f.name;
      sel.appendChild(opt);
    });
  } catch (e) { console.warn("Could not load farms", e); }
}

function setupSoilTypeVisual() {
  // Highlight selected soil type card
  document.querySelectorAll(".soil-type-card").forEach(card => {
    card.addEventListener("click", () => {
      document.querySelectorAll(".soil-type-card").forEach(c => c.classList.remove("selected"));
      card.classList.add("selected");
      const input = document.getElementById("soil-type-input");
      if (input) input.value = card.dataset.type;
    });
  });
}

async function handleSubmit(e) {
  e.preventDefault();

  const btn = document.getElementById("predict-btn");
  btn.disabled = true;
  btn.innerHTML = '<span class="ag-spinner ag-spinner-sm"></span> Predicting...';

  const payload = {
    temperature:       parseFloat(document.getElementById("temperature")?.value || 0),
    humidity:          parseFloat(document.getElementById("humidity")?.value || 0),
    rainfall:          parseFloat(document.getElementById("rainfall")?.value || 0),
    wind_speed:        parseFloat(document.getElementById("wind-speed")?.value || 0),
    soil_type:         document.getElementById("soil-type-input")?.value || "loamy",
    previous_moisture: parseFloat(document.getElementById("prev-moisture")?.value || 40),
    farm_id:           document.getElementById("farm-select")?.value || null,
    latitude:          parseFloat(document.getElementById("lat-input")?.value) || null,
    longitude:         parseFloat(document.getElementById("lon-input")?.value) || null,
  };

  // Basic validation
  if (!payload.soil_type) {
    Utils.showToast("Please select a soil type.", "warning");
    btn.disabled = false;
    btn.innerHTML = "🌱 Predict Soil Moisture";
    return;
  }

  try {
    Utils.showLoading("Analyzing soil conditions...");
    const result = await CropPulseAPI.soil.predict(payload);
    Utils.hideLoading();
    sessionStorage.setItem("ag_soil_result", JSON.stringify(result));
    displayResults(result);
    Utils.showToast("Soil analysis complete!", "success");
  } catch (err) {
    Utils.hideLoading();
    Utils.showToast(err.message || "Prediction failed.", "error");
    btn.disabled = false;
    btn.innerHTML = "🌱 Predict Soil Moisture";
  }
}

function displayResults(r) {
  const resultsSection = document.getElementById("results-section");
  if (!resultsSection) return;
  resultsSection.classList.remove("hidden");
  resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });

  // Moisture gauge
  const pct = r.predicted_moisture || 0;
  const gaugeEl = document.getElementById("moisture-gauge-fill");
  const gaugeVal = document.getElementById("moisture-gauge-value");
  if (gaugeEl) {
    gaugeEl.style.width = "0%";
    setTimeout(() => {
      gaugeEl.style.width = `${pct}%`;
      gaugeEl.className = `ag-progress-bar ${pct > 60 ? "green" : pct > 35 ? "blue" : "amber"}`;
    }, 100);
  }
  if (gaugeVal) Utils.animateCounter(gaugeVal, pct, 1200, "%");

  // Irrigation status
  const irrigEl = document.getElementById("irrigation-status");
  if (irrigEl) {
    irrigEl.innerHTML = r.irrigation_recommended
      ? `<div class="badge-severity moderate" style="font-size:0.95rem;padding:0.5rem 1rem;">💧 Irrigation Recommended</div>`
      : `<div class="badge-severity healthy" style="font-size:0.95rem;padding:0.5rem 1rem;">✅ Soil Moisture Adequate</div>`;
  }

  // Key metrics
  setMetric("water-req", `${r.water_requirement_mm?.toFixed(1)} mm`);
  setMetric("irrig-type", r.irrigation_type?.replace(/^\w/, c => c.toUpperCase()) || "None");
  setMetric("next-irrig", r.next_irrigation_hours ? `In ${r.next_irrigation_hours}h` : "Not required");
  setMetric("field-capacity", `${r.field_capacity}%`);
  setMetric("wilting-point", `${r.wilting_point}%`);
  setMetric("avail-water", `${r.available_water_content?.toFixed(1)}%`);

  // Recommendation text
  const recEl = document.getElementById("recommendation-text");
  if (recEl) recEl.textContent = r.recommendation_text || "";

  // Render moisture trend chart with single point
  renderSoilChart(r);

  // Generate report button
  const rptBtn = document.getElementById("generate-report-btn");
  if (rptBtn) {
    rptBtn.classList.remove("hidden");
    rptBtn.onclick = () => generateReport(r.prediction_id);
  }
}

function setMetric(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function renderSoilChart(result) {
  const ctx = document.getElementById("soil-result-chart");
  if (!ctx || !window.Chart) return;
  if (ctx._chartInstance) ctx._chartInstance.destroy();

  const isDark = !document.body.classList.contains("light-mode");
  const colors = { text: isDark ? "#94a3b8" : "#475569", grid: isDark ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)" };

  ctx._chartInstance = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Previous Moisture", "Predicted Moisture", "Field Capacity", "Wilting Point"],
      datasets: [{
        label: "Soil Moisture (%)",
        data: [
          result.input_features?.previous_moisture || 0,
          result.predicted_moisture || 0,
          result.field_capacity || 0,
          result.wilting_point || 0,
        ],
        backgroundColor: ["#3b82f6aa", "#16a34aaa", "#f59e0baa", "#dc2626aa"],
        borderColor:     ["#3b82f6",  "#16a34a",   "#f59e0b",   "#dc2626"],
        borderWidth: 2, borderRadius: 8,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { min: 0, max: 100, grid: { color: colors.grid }, ticks: { color: colors.text } },
        x: { grid: { display: false }, ticks: { color: colors.text } },
      },
    },
  });
}

async function generateReport(predId) {
  try {
    Utils.showLoading("Generating PDF report...");
    const res = await CropPulseAPI.reports.generate({ report_type: "soil" });
    Utils.hideLoading();
    if (res.file_url) {
      Utils.showToast("Report ready! Downloading...", "success");
      Utils.downloadURL(res.file_url, `soil_report_${predId}.pdf`);
    }
  } catch (e) {
    Utils.hideLoading();
    Utils.showToast("Report generation failed.", "error");
  }
}

function getLocation() {
  if (!navigator.geolocation) { Utils.showToast("Geolocation not supported.", "warning"); return; }
  navigator.geolocation.getCurrentPosition(
    pos => {
      const latEl = document.getElementById("lat-input");
      const lonEl = document.getElementById("lon-input");
      if (latEl) latEl.value = pos.coords.latitude.toFixed(6);
      if (lonEl) lonEl.value = pos.coords.longitude.toFixed(6);
      Utils.showToast("Location captured!", "success");
    },
    () => Utils.showToast("Could not get location.", "error")
  );
}
