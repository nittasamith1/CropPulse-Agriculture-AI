/**
 * CropPulse – Leaflet.js Map Module
 * GIS map with farm markers, disease heatmap, marker clustering,
 * color-coded severity, and search/filter functionality.
 */

const AgriMap = (() => {
  let map = null;
  let markerCluster = null;
  let heatLayer = null;
  let currentMarkers = [];

  // ── Severity Color Map ──────────────────────────────────────────────────
  const SEVERITY_COLORS = {
    healthy: "#16a34a",
    mild:    "#f59e0b",
    moderate:"#f97316",
    severe:  "#dc2626",
    unknown: "#64748b",
    grey:    "#64748b",
    green:   "#16a34a",
    yellow:  "#f59e0b",
    orange:  "#f97316",
    red:     "#dc2626",
    blue:    "#2563eb",
  };

  // ── Initialize Map ──────────────────────────────────────────────────────
  function init(containerId = "ag-map", center = [20.5937, 78.9629], zoom = 5) {
    if (map) { map.remove(); }

    map = L.map(containerId, {
      center, zoom,
      zoomControl: false,
      attributionControl: true,
    });

    // Add tile layer (OpenStreetMap)
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: '© <a href="https://www.openstreetmap.org/">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    // Custom zoom control
    L.control.zoom({ position: "topright" }).addTo(map);

    // Marker cluster group
    if (window.L.MarkerClusterGroup) {
      markerCluster = L.markerClusterGroup({
        chunkedLoading: true,
        maxClusterRadius: 60,
        iconCreateFunction: (cluster) => {
          const count = cluster.getChildCount();
          const size = count < 10 ? 36 : count < 50 ? 44 : 52;
          return L.divIcon({
            html: `<div style="
              width:${size}px;height:${size}px;
              background:rgba(22,163,74,0.85);
              border:2px solid #22c55e;
              border-radius:50%;
              display:flex;align-items:center;justify-content:center;
              color:#fff;font-weight:700;font-size:${size < 44 ? 12 : 14}px;
              box-shadow:0 0 15px rgba(22,163,74,0.4);
            ">${count}</div>`,
            className: "",
            iconSize: [size, size],
          });
        },
      });
      map.addLayer(markerCluster);
    }

    return map;
  }

  // ── Create Custom Marker Icon ───────────────────────────────────────────
  function createMarkerIcon(color = "#16a34a", size = 32) {
    return L.divIcon({
      html: `<div style="
        width:${size}px;height:${size}px;
        background:${color};
        border:2px solid rgba(255,255,255,0.8);
        border-radius:50% 50% 50% 0;
        transform:rotate(-45deg);
        box-shadow:0 3px 12px rgba(0,0,0,0.3);
        position:relative;
      ">
        <div style="
          position:absolute;
          width:10px;height:10px;
          background:rgba(255,255,255,0.7);
          border-radius:50%;
          top:6px;left:6px;
        "></div>
      </div>`,
      className: "",
      iconSize: [size, size],
      iconAnchor: [size / 2, size],
      popupAnchor: [0, -size],
    });
  }

  // ── Add Farm Markers ────────────────────────────────────────────────────
  function addMarkers(markers, onClick = null) {
    clearMarkers();

    markers.forEach(m => {
      const color = SEVERITY_COLORS[m.marker_color] || SEVERITY_COLORS.grey;
      const icon = createMarkerIcon(color);
      const marker = L.marker([m.latitude, m.longitude], { icon });

      // Popup content
      const severity = m.last_severity || "unknown";
      const severityColor = SEVERITY_COLORS[severity] || "#64748b";
      const popupHTML = `
        <div style="font-family:Inter,sans-serif;min-width:220px;max-width:280px;">
          <div style="background:${color};color:#fff;padding:10px 12px;border-radius:8px 8px 0 0;margin:-10px -10px 0;">
            <strong style="font-size:1rem;">🌾 ${m.name || "Farm"}</strong>
          </div>
          <div style="padding:10px 4px;">
            ${m.district ? `<div style="color:#64748b;font-size:0.8rem;margin-bottom:6px;">📍 ${m.district}, ${m.state || ""}</div>` : ""}
            ${m.last_disease && m.last_disease !== "No data" ? `
              <div style="margin:6px 0;padding:6px 10px;background:rgba(0,0,0,0.05);border-radius:6px;">
                <div style="font-size:0.78rem;color:#64748b;">Last Disease Scan</div>
                <div style="font-weight:600;font-size:0.88rem;">${m.last_disease}</div>
                <span style="display:inline-block;padding:2px 8px;border-radius:20px;font-size:0.72rem;font-weight:700;background:${severityColor}22;color:${severityColor};border:1px solid ${severityColor}44;">
                  ${severity}
                </span>
              </div>` : ""}
            ${m.last_moisture != null ? `<div style="font-size:0.82rem;margin-top:6px;">💧 Last Moisture: <strong>${m.last_moisture?.toFixed(1)}%</strong></div>` : ""}
            ${m.crop_types?.length ? `<div style="font-size:0.78rem;color:#64748b;margin-top:4px;">Crops: ${m.crop_types.join(", ")}</div>` : ""}
          </div>
        </div>
      `;

      marker.bindPopup(popupHTML, { maxWidth: 300 });
      if (onClick) marker.on("click", () => onClick(m));
      currentMarkers.push(marker);

      if (markerCluster) {
        markerCluster.addLayer(marker);
      } else {
        marker.addTo(map);
      }
    });
  }

  // ── Heatmap Layer ───────────────────────────────────────────────────────
  function addHeatmap(points) {
    if (heatLayer) { map.removeLayer(heatLayer); }
    if (!window.L.heatLayer) {
      console.warn("Leaflet.heat plugin not loaded. Heatmap unavailable.");
      return;
    }
    heatLayer = L.heatLayer(points, {
      radius: 30, blur: 20, maxZoom: 14,
      gradient: { 0.1: "#22c55e", 0.3: "#f59e0b", 0.6: "#f97316", 1.0: "#dc2626" },
    });
    map.addLayer(heatLayer);
  }

  function removeHeatmap() {
    if (heatLayer) { map.removeLayer(heatLayer); heatLayer = null; }
  }

  // ── Clear Markers ───────────────────────────────────────────────────────
  function clearMarkers() {
    currentMarkers.forEach(m => m.remove());
    currentMarkers = [];
    if (markerCluster) markerCluster.clearLayers();
  }

  // ── Fit to Markers ──────────────────────────────────────────────────────
  function fitToMarkers() {
    if (!currentMarkers.length) return;
    const group = L.featureGroup(currentMarkers);
    map.fitBounds(group.getBounds().pad(0.15));
  }

  // ── Add Location Search ─────────────────────────────────────────────────
  function addLocationSearch() {
    // Simple nominatim geocoder search control
    const searchControl = L.Control.extend({
      options: { position: "topleft" },
      onAdd: () => {
        const div = L.DomUtil.create("div", "leaflet-search-control");
        div.innerHTML = `
          <div style="display:flex;gap:6px;background:rgba(15,23,36,0.95);padding:8px;border-radius:10px;border:1px solid rgba(255,255,255,0.1);">
            <input id="map-search-input" placeholder="Search location..." style="
              background:transparent;border:none;outline:none;color:#f1f5f9;
              font-size:0.85rem;width:200px;font-family:Inter,sans-serif;
            " />
            <button id="map-search-btn" style="
              background:#16a34a;border:none;border-radius:6px;
              color:#fff;padding:4px 10px;cursor:pointer;font-size:0.8rem;
            ">Go</button>
          </div>`;
        L.DomEvent.disableClickPropagation(div);
        return div;
      },
    });
    new searchControl().addTo(map);

    document.addEventListener("click", async (e) => {
      if (e.target.id !== "map-search-btn") return;
      const q = document.getElementById("map-search-input")?.value?.trim();
      if (!q) return;
      const res = await fetch(`https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(q)}&format=json&limit=1`);
      const data = await res.json();
      if (data.length) {
        map.setView([data[0].lat, data[0].lon], 12);
      } else {
        Utils.showToast("Location not found.", "warning");
      }
    });
  }

  // ── Filter Markers by Severity ──────────────────────────────────────────
  function filterBySeverity(markers, severity) {
    if (severity === "all") return markers;
    return markers.filter(m => m.last_severity === severity || m.marker_color === severity);
  }

  // ── Get Map Instance ────────────────────────────────────────────────────
  function getMap() { return map; }

  return {
    init, addMarkers, addHeatmap, removeHeatmap,
    clearMarkers, fitToMarkers, addLocationSearch,
    filterBySeverity, getMap, SEVERITY_COLORS,
  };
})();

window.AgriMap = AgriMap;
