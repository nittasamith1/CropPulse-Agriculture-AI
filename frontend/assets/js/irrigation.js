/**
 * CropPulse – Precision Irrigation JS Module
 * Handles form interactions, farm selection, geolocation auto-detect,
 * API communication, and rendering of irrigation recommendations.
 */

document.addEventListener("DOMContentLoaded", () => {
  Auth.requireAuth();

  // Load farms dropdown
  async function loadFarms() {
    try {
      const res = await CropPulseAPI.auth.getMyFarms();
      const farms = res.farms || [];
      const sel = document.getElementById("farm-select");
      if (!sel) return;
      farms.forEach(f => {
        const opt = document.createElement("option");
        opt.value = f.farm_id;
        opt.textContent = `${f.name} (${f.crop_types ? f.crop_types.join(", ") : "Crop"})`;
        sel.appendChild(opt);
      });

      // When farm is selected, autofill coordinates and crop if present
      sel.addEventListener("change", () => {
        const selected = farms.find(f => f.farm_id === sel.value);
        if (selected) {
          if (selected.latitude) document.getElementById("lat-input").value = selected.latitude;
          if (selected.longitude) document.getElementById("lon-input").value = selected.longitude;
          if (selected.soil_type) document.getElementById("soil-type").value = selected.soil_type.toLowerCase();
          if (selected.crop_types && selected.crop_types[0]) {
            const cropVal = selected.crop_types[0];
            const cropSel = document.getElementById("crop-type");
            for (let i = 0; i < cropSel.options.length; i++) {
              if (cropSel.options[i].value.toLowerCase() === cropVal.toLowerCase()) {
                cropSel.selectedIndex = i;
                break;
              }
            }
          }
        }
      });
    } catch (e) {
      // Non-blocking fallback
    }
  }
  loadFarms();

  // Geolocation button
  document.getElementById("get-location-btn")?.addEventListener("click", () => {
    if (!navigator.geolocation) {
      Utils.showToast("Geolocation is not supported by your browser.", "warning");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      pos => {
        const latEl = document.getElementById("lat-input");
        const lonEl = document.getElementById("lon-input");
        if (latEl) latEl.value = pos.coords.latitude.toFixed(6);
        if (lonEl) lonEl.value = pos.coords.longitude.toFixed(6);
        Utils.showToast("GPS coordinates acquired!", "success");
      },
      () => Utils.showToast("Unable to detect GPS position.", "error")
    );
  });

  // Form Submission
  const form = document.getElementById("irrigation-form");
  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = document.getElementById("calculate-btn");
    btn.disabled = true;
    btn.innerHTML = '<span class="ag-spinner ag-spinner-sm"></span> Analyzing field data...';

    const farmId = document.getElementById("farm-select")?.value || null;
    const crop = document.getElementById("crop-type")?.value || "Tomato";
    const growthStage = document.getElementById("growth-stage")?.value || "mid";
    const soilType = document.getElementById("soil-type")?.value || "loamy";
    const moistureInput = document.getElementById("soil-moisture")?.value;
    const lat = parseFloat(document.getElementById("lat-input")?.value) || null;
    const lon = parseFloat(document.getElementById("lon-input")?.value) || null;

    const payload = {
      farm_id: farmId,
      crop_type: crop,
      growth_stage: growthStage,
      soil_type: soilType,
      latitude: lat,
      longitude: lon,
    };
    if (moistureInput !== "" && !isNaN(parseFloat(moistureInput))) {
      payload.soil_moisture = parseFloat(moistureInput);
    }

    try {
      const result = await CropPulseAPI.irrigation.recommend(payload);
      renderIrrigationResult(result);
      Utils.showToast("Precision irrigation advisory computed!", "success");
    } catch (err) {
      Utils.showToast(err.message || "Failed to calculate irrigation schedule.", "error");
    } finally {
      btn.disabled = false;
      btn.innerHTML = '🚜 Generate Irrigation Recommendation';
    }
  });

  function renderIrrigationResult(data) {
    document.getElementById("empty-result")?.classList.add("hidden");
    const resSec = document.getElementById("result-section");
    resSec?.classList.remove("hidden");
    resSec?.scrollIntoView({ behavior: "smooth", block: "start" });

    // Action Badge
    const badgeContainer = document.getElementById("action-badge-container");
    const action = (data.action || "MONITOR").toUpperCase();
    let badgeClass = "action-monitor";
    let icon = "💧";
    if (action === "IRRIGATE") {
      badgeClass = "action-irrigate";
      icon = "🚿";
    } else if (action === "WAIT") {
      badgeClass = "action-wait";
      icon = "⏳";
    } else if (action === "REDUCE IRRIGATION") {
      badgeClass = "action-reduce";
      icon = "🛑";
    }

    if (badgeContainer) {
      badgeContainer.innerHTML = `<span class="action-badge-xl ${badgeClass}">${icon} ${action}</span>`;
    }

    // Reason & Priority
    const reasonEl = document.getElementById("action-reason");
    if (reasonEl) reasonEl.textContent = data.reason || "Recommendation calculated based on crop water requirements.";

    const priorityBadge = document.getElementById("priority-badge");
    if (priorityBadge) {
      const p = (data.priority || "low").toLowerCase();
      let pBg = "#22c55e";
      if (p === "urgent") pBg = "#ef4444";
      else if (p === "high") pBg = "#f97316";
      else if (p === "medium") pBg = "#eab308";
      priorityBadge.style.backgroundColor = pBg;
      priorityBadge.style.color = "#fff";
      priorityBadge.textContent = `Priority: ${p.toUpperCase()}`;
    }

    const confEl = document.getElementById("confidence-text");
    if (confEl) confEl.textContent = `Confidence: ${Math.round((data.confidence || 0.8) * 100)}%`;

    // Metrics
    const depthEl = document.getElementById("water-depth-val");
    if (depthEl) depthEl.innerHTML = `${(data.water_amount_mm || 0).toFixed(1)} <span style="font-size:1rem;font-weight:500;">mm</span>`;

    const volEl = document.getElementById("water-volume-val");
    if (volEl) volEl.innerHTML = `${(data.litres_per_hectare || 0).toLocaleString()} <span style="font-size:1rem;font-weight:500;">L/ha</span>`;

    const methodEl = document.getElementById("water-method-val");
    if (methodEl) methodEl.textContent = data.recommended_method || "Drip";

    // Soil Moisture vs Field Capacity
    const curMoist = data.soil_moisture_level != null ? data.soil_moisture_level : 35;
    const fc = data.field_capacity_reference != null ? data.field_capacity_reference : 35;
    const ratio = Math.min(100, Math.round((curMoist / fc) * 100));

    const capBar = document.getElementById("capacity-bar");
    if (capBar) {
      capBar.style.width = `${Math.min(100, ratio)}%`;
      if (ratio < 50) capBar.style.background = "#f97316";
      else if (ratio > 100) capBar.style.background = "#a855f7";
      else capBar.style.background = "#0ea5e9";
    }

    const capText = document.getElementById("capacity-percentage-text");
    if (capText) capText.textContent = `${ratio}% of Field Capacity`;

    const moistLabel = document.getElementById("current-moisture-label");
    if (moistLabel) moistLabel.textContent = `Current Moisture: ${curMoist.toFixed(1)}%`;

    const fcLabel = document.getElementById("field-capacity-label");
    if (fcLabel) fcLabel.textContent = `Target Field Capacity: ${fc.toFixed(1)}%`;

    // Weather Context
    const wf = data.weather_forecast_summary || {};
    const rainProbEl = document.getElementById("forecast-rain-prob");
    if (rainProbEl) rainProbEl.textContent = `${wf.rain_probability_24h != null ? Math.round(wf.rain_probability_24h) : 0}%`;

    const rainMmEl = document.getElementById("forecast-rain-mm");
    if (rainMmEl) rainMmEl.textContent = `${wf.precipitation_forecast_24h != null ? wf.precipitation_forecast_24h.toFixed(1) : 0.0} mm`;

    // Disclaimer
    const discEl = document.getElementById("irrigation-disclaimer");
    if (discEl && data.disclaimer) discEl.textContent = data.disclaimer;
  }
});
