/**
 * CropPulse – Utility Module
 * Toast notifications, loading overlays, formatters, and shared helpers.
 */

const Utils = (() => {

  // ── Toast Notifications ─────────────────────────────────────────────────
  function showToast(message, type = "info", title = null, duration = 4000) {
    let container = document.getElementById("ag-toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "ag-toast-container";
      container.className = "ag-toast-container";
      document.body.appendChild(container);
    }

    const icons = { success: "✅", error: "❌", warning: "⚠️", info: "ℹ️" };
    const defaultTitles = { success: "Success", error: "Error", warning: "Warning", info: "Info" };

    const toast = document.createElement("div");
    toast.className = `ag-toast ${type}`;
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || "ℹ️"}</span>
      <div style="flex:1">
        <div class="toast-title">${title || defaultTitles[type]}</div>
        <div class="toast-msg">${message}</div>
      </div>
      <span class="toast-close" onclick="this.closest('.ag-toast').remove()">✕</span>
    `;

    container.appendChild(toast);

    // Auto-dismiss
    setTimeout(() => {
      toast.style.animation = "slideOutRight 0.3s ease forwards";
      setTimeout(() => toast.remove(), 300);
    }, duration);

    return toast;
  }

  // ── Loading Overlay ─────────────────────────────────────────────────────
  let loadingEl = null;

  function showLoading(message = "Processing...") {
    if (loadingEl) return;
    loadingEl = document.createElement("div");
    loadingEl.className = "loading-overlay";
    loadingEl.innerHTML = `
      <div class="ag-spinner ag-spinner-lg"></div>
      <span class="load-text">${message}</span>
    `;
    document.body.appendChild(loadingEl);
  }

  function hideLoading() {
    if (loadingEl) { loadingEl.remove(); loadingEl = null; }
  }

  // ── Skeleton Loader ─────────────────────────────────────────────────────
  function showSkeleton(containerId, count = 3, height = "80px") {
    const el = document.getElementById(containerId);
    if (!el) return;
    el.innerHTML = Array.from({ length: count }, () =>
      `<div class="skeleton mb-3" style="height:${height};border-radius:12px;"></div>`
    ).join("");
  }

  // ── Formatters ──────────────────────────────────────────────────────────
  function formatDate(dateStr) {
    if (!dateStr) return "N/A";
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? dateStr : d.toLocaleDateString("en-IN", {
      day: "2-digit", month: "short", year: "numeric"
    });
  }

  function formatDateTime(dateStr) {
    if (!dateStr) return "N/A";
    const d = new Date(dateStr);
    return isNaN(d.getTime()) ? dateStr : d.toLocaleString("en-IN", {
      day: "2-digit", month: "short", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  }

  function formatRelativeTime(dateStr) {
    if (!dateStr) return "N/A";
    const d = new Date(dateStr);
    const now = new Date();
    const diff = now - d;
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours   = Math.floor(minutes / 60);
    const days    = Math.floor(hours / 24);
    if (seconds < 60)  return "just now";
    if (minutes < 60)  return `${minutes}m ago`;
    if (hours < 24)    return `${hours}h ago`;
    if (days < 7)      return `${days}d ago`;
    return formatDate(dateStr);
  }

  function formatConfidence(value) {
    return `${(value * 100).toFixed(1)}%`;
  }

  function formatMoisture(value) {
    return `${value?.toFixed(1) ?? "N/A"}%`;
  }

  function formatBytes(bytes) {
    if (bytes < 1024)         return `${bytes} B`;
    if (bytes < 1024 * 1024)  return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  // ── Severity Badge HTML ─────────────────────────────────────────────────
  function severityBadge(severity) {
    const icons = { healthy: "🌿", mild: "🟡", moderate: "🟠", severe: "🔴" };
    return `<span class="badge-severity ${severity}">${icons[severity] || "⚪"} ${severity}</span>`;
  }

  // ── Pagination Renderer ─────────────────────────────────────────────────
  function renderPagination(containerId, total, page, pageSize, onPageChange) {
    const totalPages = Math.ceil(total / pageSize);
    if (totalPages <= 1) return;
    const el = document.getElementById(containerId);
    if (!el) return;

    let html = '<div class="ag-pagination">';
    html += `<button class="ag-page-btn" ${page <= 1 ? "disabled" : ""} onclick="(${onPageChange.toString()})(${page - 1})">‹</button>`;

    for (let i = 1; i <= totalPages; i++) {
      if (i === 1 || i === totalPages || (i >= page - 2 && i <= page + 2)) {
        html += `<button class="ag-page-btn ${i === page ? "active" : ""}" onclick="(${onPageChange.toString()})(${i})">${i}</button>`;
      } else if (i === page - 3 || i === page + 3) {
        html += `<span class="ag-page-btn" style="cursor:default">…</span>`;
      }
    }

    html += `<button class="ag-page-btn" ${page >= totalPages ? "disabled" : ""} onclick="(${onPageChange.toString()})(${page + 1})">›</button>`;
    html += '</div>';
    el.innerHTML = html;
  }

  // ── Animate Counter ─────────────────────────────────────────────────────
  function animateCounter(el, target, duration = 1200, suffix = "") {
    if (!el) return;
    const start = 0;
    const startTime = performance.now();
    const isFloat = target % 1 !== 0;

    function update(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = start + (target - start) * ease;
      el.textContent = (isFloat ? current.toFixed(1) : Math.floor(current)) + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  }

  // ── Intersection Observer for entrance animations ───────────────────────
  function initEntranceAnimations() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.remove("anim-hidden");
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1 });

    document.querySelectorAll(".anim-hidden").forEach(el => observer.observe(el));
  }

  // ── Dark/Light Mode Toggle ──────────────────────────────────────────────
  function initThemeToggle() {
    const saved = localStorage.getItem("ag_theme") || "dark";
    if (saved === "light") document.body.classList.add("light-mode");

    const toggle = document.getElementById("theme-toggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        document.body.classList.toggle("light-mode");
        const theme = document.body.classList.contains("light-mode") ? "light" : "dark";
        localStorage.setItem("ag_theme", theme);
      });
    }
  }

  // ── Copy to Clipboard ───────────────────────────────────────────────────
  async function copyToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      showToast("Copied to clipboard!", "success");
    } catch {
      showToast("Could not copy to clipboard.", "error");
    }
  }

  // ── Download Helper ─────────────────────────────────────────────────────
  function downloadURL(url, filename) {
    const a = document.createElement("a");
    a.href = url; a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  // ── Debounce ────────────────────────────────────────────────────────────
  function debounce(fn, delay = 300) {
    let t;
    return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), delay); };
  }

  // ── Sanitize HTML ───────────────────────────────────────────────────────
  function sanitizeHTML(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ── Auto-init on DOM ready ──────────────────────────────────────────────
  document.addEventListener("DOMContentLoaded", () => {
    initThemeToggle();
    setTimeout(initEntranceAnimations, 100);
  });

  return {
    showToast, showLoading, hideLoading, showSkeleton,
    formatDate, formatDateTime, formatRelativeTime,
    formatConfidence, formatMoisture, formatBytes,
    severityBadge, renderPagination, animateCounter,
    initEntranceAnimations, initThemeToggle,
    copyToClipboard, downloadURL, debounce, sanitizeHTML,
  };
})();

window.Utils = Utils;
