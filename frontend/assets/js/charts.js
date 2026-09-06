/**
 * CropPulse – Charts Module
 * Chart.js chart builders for dashboard and analytics pages.
 */

const Charts = (() => {

  // ── Shared default options ──────────────────────────────────────────────
  const isDark = () => !document.body.classList.contains("light-mode");

  function gridColor()  { return isDark() ? "rgba(255,255,255,0.06)" : "rgba(0,0,0,0.06)"; }
  function textColor()  { return isDark() ? "#94a3b8" : "#475569"; }
  function tickColor()  { return isDark() ? "#64748b" : "#94a3b8"; }

  const baseFont = { family: "Inter, sans-serif", size: 12 };

  function baseOptions(title = "") {
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 900, easing: "easeInOutQuart" },
      plugins: {
        legend: { labels: { color: textColor(), font: baseFont, padding: 16 } },
        title: {
          display: !!title,
          text: title,
          color: isDark() ? "#f1f5f9" : "#0f172a",
          font: { size: 14, weight: "600", family: "Space Grotesk, sans-serif" },
          padding: { bottom: 12 },
        },
        tooltip: {
          backgroundColor: isDark() ? "#1a2640" : "#ffffff",
          titleColor: isDark() ? "#f1f5f9" : "#0f172a",
          bodyColor: textColor(),
          borderColor: "rgba(22,163,74,0.3)",
          borderWidth: 1,
          padding: 12,
          cornerRadius: 10,
        },
      },
      scales: {
        x: {
          grid: { color: gridColor(), drawBorder: false },
          ticks: { color: tickColor(), font: baseFont },
        },
        y: {
          grid: { color: gridColor(), drawBorder: false },
          ticks: { color: tickColor(), font: baseFont },
        },
      },
    };
  }

  // ── Color Palettes ──────────────────────────────────────────────────────
  const PALETTE = {
    green:  "#16a34a", greenLight: "#22c55e", greenAlpha: "rgba(22,163,74,0.2)",
    blue:   "#2563eb", blueLight:  "#3b82f6", blueAlpha:  "rgba(37,99,235,0.2)",
    amber:  "#f59e0b", amberAlpha: "rgba(245,158,11,0.2)",
    red:    "#dc2626", redAlpha:   "rgba(220,38,38,0.2)",
    cyan:   "#06b6d4", purple:     "#7c3aed",
    multiColors: ["#16a34a","#2563eb","#f59e0b","#dc2626","#06b6d4","#7c3aed","#10b981","#f97316"],
  };

  // ── Severity Donut Chart ────────────────────────────────────────────────
  function renderSeverityDonut(canvasId, data) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (ctx._chartInstance) ctx._chartInstance.destroy();

    ctx._chartInstance = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Healthy", "Mild", "Moderate", "Severe"],
        datasets: [{
          data: [data.healthy || 0, data.mild || 0, data.moderate || 0, data.severe || 0],
          backgroundColor: [PALETTE.green, PALETTE.amber, "#f97316", PALETTE.red],
          borderWidth: 0,
          hoverOffset: 8,
        }],
      },
      options: {
        ...baseOptions(),
        cutout: "70%",
        plugins: {
          ...baseOptions().plugins,
          legend: { position: "right", labels: { color: textColor(), padding: 14, font: baseFont } },
        },
      },
    });
  }

  // ── Monthly Predictions Bar Chart ───────────────────────────────────────
  function renderMonthlyBar(canvasId, diseaseData, soilData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (ctx._chartInstance) ctx._chartInstance.destroy();

    const labels = Object.keys(diseaseData || {}).reverse();
    const diseaseVals = labels.map(k => diseaseData[k] || 0);
    const soilVals    = labels.map(k => (soilData || {})[k] || 0);

    ctx._chartInstance = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Disease Scans",
            data: diseaseVals,
            backgroundColor: PALETTE.greenAlpha,
            borderColor: PALETTE.green,
            borderWidth: 2,
            borderRadius: 6,
          },
          {
            label: "Soil Predictions",
            data: soilVals,
            backgroundColor: PALETTE.blueAlpha,
            borderColor: PALETTE.blue,
            borderWidth: 2,
            borderRadius: 6,
          },
        ],
      },
      options: { ...baseOptions("Monthly Predictions"), barPercentage: 0.6 },
    });
  }

  // ── Healthy vs Diseased Pie ─────────────────────────────────────────────
  function renderHealthPie(canvasId, healthy, diseased) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (ctx._chartInstance) ctx._chartInstance.destroy();

    ctx._chartInstance = new Chart(ctx, {
      type: "pie",
      data: {
        labels: ["Healthy", "Diseased"],
        datasets: [{
          data: [healthy, diseased],
          backgroundColor: [PALETTE.green, PALETTE.red],
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: { ...baseOptions("Crop Health Distribution") },
    });
  }

  // ── Soil Moisture Line Chart ────────────────────────────────────────────
  function renderMoistureLine(canvasId, predictions) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (ctx._chartInstance) ctx._chartInstance.destroy();

    const sorted = [...(predictions || [])].sort((a, b) =>
      new Date(a.created_at) - new Date(b.created_at)
    ).slice(-20);

    const labels = sorted.map(p => {
      const d = new Date(p.created_at);
      return isNaN(d) ? "" : d.toLocaleDateString("en-IN", { month: "short", day: "numeric" });
    });
    const values = sorted.map(p => p.predicted_moisture || 0);

    ctx._chartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: [{
          label: "Soil Moisture %",
          data: values,
          borderColor: PALETTE.blue,
          backgroundColor: PALETTE.blueAlpha,
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointHoverRadius: 7,
          pointBackgroundColor: PALETTE.blue,
        }],
      },
      options: {
        ...baseOptions("Soil Moisture Trend"),
        scales: {
          ...baseOptions().scales,
          y: { ...baseOptions().scales.y, min: 0, max: 100 },
        },
      },
    });
  }

  // ── Top Diseases Horizontal Bar ─────────────────────────────────────────
  function renderTopDiseases(canvasId, topDiseases) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (ctx._chartInstance) ctx._chartInstance.destroy();

    const top = (topDiseases || []).slice(0, 8);
    const labels = top.map(d => (d.name || "Unknown").replace(" – ", "\n").split(" – ").pop() || d.name);
    const values = top.map(d => d.count || 0);

    ctx._chartInstance = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [{
          label: "Occurrences",
          data: values,
          backgroundColor: PALETTE.multiColors.slice(0, top.length),
          borderWidth: 0,
          borderRadius: 6,
        }],
      },
      options: {
        ...baseOptions("Top Diseases"),
        indexAxis: "y",
        scales: {
          x: { ...baseOptions().scales.x },
          y: { ...baseOptions().scales.y, ticks: { color: textColor(), font: { size: 11 } } },
        },
      },
    });
  }

  // ── Water Usage Radar ───────────────────────────────────────────────────
  function renderWaterRadar(canvasId, soilTypes, waterReqs) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (ctx._chartInstance) ctx._chartInstance.destroy();

    ctx._chartInstance = new Chart(ctx, {
      type: "radar",
      data: {
        labels: soilTypes || ["Sandy", "Loamy", "Clay", "Silt", "Peaty"],
        datasets: [{
          label: "Avg Water Req (mm)",
          data: waterReqs || [35, 22, 15, 20, 12],
          borderColor: PALETTE.cyan,
          backgroundColor: "rgba(6,182,212,0.15)",
          pointBackgroundColor: PALETTE.cyan,
          pointRadius: 5,
        }],
      },
      options: {
        ...baseOptions("Water Requirement by Soil Type"),
        scales: {
          r: {
            grid: { color: gridColor() },
            angleLines: { color: gridColor() },
            pointLabels: { color: textColor(), font: baseFont },
            ticks: { color: tickColor(), backdropColor: "transparent" },
          },
        },
      },
    });
  }

  // ── Crop Statistics Polar ───────────────────────────────────────────────
  function renderCropStats(canvasId, cropData) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return;
    if (ctx._chartInstance) ctx._chartInstance.destroy();

    const entries = Object.entries(cropData || {}).slice(0, 8);
    ctx._chartInstance = new Chart(ctx, {
      type: "polarArea",
      data: {
        labels: entries.map(([k]) => k),
        datasets: [{
          data: entries.map(([, v]) => v),
          backgroundColor: PALETTE.multiColors.map(c => c + "88"),
          borderColor: PALETTE.multiColors,
          borderWidth: 1,
        }],
      },
      options: {
        ...baseOptions("Disease by Crop Type"),
        scales: { r: { ticks: { backdropColor: "transparent", color: tickColor() } } },
      },
    });
  }

  return {
    renderSeverityDonut, renderMonthlyBar, renderHealthPie,
    renderMoistureLine, renderTopDiseases, renderWaterRadar, renderCropStats,
  };
})();

window.Charts = Charts;
