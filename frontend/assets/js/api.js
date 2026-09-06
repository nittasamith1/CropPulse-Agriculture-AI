/**
 * CropPulse – API Client Module
 * Typed wrapper around all backend REST endpoints.
 * Automatically attaches Authorization header using Auth.getToken().
 * Handles automatic JWT token refresh on 401 Unauthorized errors.
 */
(function () {
  const hostname = window.location.hostname;

  // ── Production: always use the absolute Render backend URL ───────────────
  // Never allow API_BASE to be empty/relative in production — that causes 503s
  // when the Vercel proxy rewrite fails or Render is cold-starting.
  const RENDER_BACKEND = "https://croppulse-backend.onrender.com";

  if (hostname === "localhost" || hostname === "127.0.0.1" || hostname === "" || window.location.protocol === "file:") {
    window.API_BASE = "http://localhost:8000";
  } else {
    // Vercel, custom domain, or any other deployment host:
    // Use BACKEND_URL injected by meta tag, or hard Render URL as fallback.
    window.API_BASE = window.BACKEND_URL || RENDER_BACKEND;
  }
})();

const CropPulseAPI = (() => {
  const BASE = () => window.API_BASE;
  let isRefreshing = false;
  let refreshSubscribers = [];

  function subscribeTokenRefresh(cb) {
    refreshSubscribers.push(cb);
  }

  function onRefreshed(token) {
    refreshSubscribers.map(cb => cb(token));
    refreshSubscribers = [];
  }

  // ── Core Fetch Wrapper ──────────────────────────────────────────────────
  async function request(method, endpoint, body = null, isFormData = false, retried = false) {
    const token = window.Auth?.getToken();
    const headers = {};

    if (token) headers["Authorization"] = `Bearer ${token}`;
    if (!isFormData && body) headers["Content-Type"] = "application/json";

    const config = {
      method: method.toUpperCase(),
      headers,
      body: body
        ? (isFormData ? body : JSON.stringify(body))
        : undefined,
    };

    try {
      const url = `${BASE()}/api/v1${endpoint}`;
      const res = await fetch(url, config);

      if (res.status === 401 && !retried && window.Auth?.isLoggedIn()) {
        // Access token might be expired, attempt to refresh it
        if (!isRefreshing) {
          isRefreshing = true;
          try {
            const newToken = await window.Auth.getFreshToken();
            isRefreshing = false;
            if (newToken) {
              onRefreshed(newToken);
            } else {
              window.Auth.logout();
              throw new Error("Session expired. Please log in again.");
            }
          } catch (refreshErr) {
            isRefreshing = false;
            window.Auth.logout();
            throw refreshErr;
          }
        }

        // Return a promise that resolves with the retried request
        const retryRequest = new Promise((resolve) => {
          subscribeTokenRefresh((newToken) => {
            resolve(request(method, endpoint, body, isFormData, true));
          });
        });
        return retryRequest;
      }

      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        const errMsg = data?.detail || data?.message || `HTTP ${res.status}`;
        console.error(`[API] ${method} ${endpoint}: ${errMsg}`);
        throw new Error(errMsg);
      }
      return data;
    } catch (err) {
      console.error(`[API] ${method} ${endpoint}:`, err.message);
      throw err;
    }
  }

  const get = (ep) => request("GET", ep);
  const post = (ep, body) => request("POST", ep, body);
  const put = (ep, body) => request("PUT", ep, body);
  const del = (ep) => request("DELETE", ep);
  const postFD = (ep, formData) => request("POST", ep, formData, true);

  // ── Auth Endpoints ──────────────────────────────────────────────────────
  const auth = {
    register: (payload) => post("/auth/register", payload),
    login: (payload) => post("/auth/login", payload),
    verifyEmail: (token) => get(`/auth/verify-email?token=${token}`),
    resetPassword: (payload) => post("/auth/reset-password", payload),
    me: () => get("/auth/me"),
    updateProfile: (payload) => put("/auth/me", payload),
    forgotPassword: (email) => post("/auth/forgot-password", { email }),
    addFarm: (payload) => post("/auth/farms", payload),
    updateFarm: (id, payload) => put(`/auth/farms/${id}`, payload),
    deleteFarm: (id) => del(`/auth/farms/${id}`),
    getMyFarms: () => get("/auth/farms"),
  };

  // ── Disease Endpoints ───────────────────────────────────────────────────
  const disease = {
    predict: (formData) => postFD("/disease/predict", formData),
    getHistory: (page = 1, pageSize = 20) =>
      get(`/disease/history?page=${page}&page_size=${pageSize}`),
    getById: (id) => get(`/disease/${id}`),
  };

  // ── Soil Endpoints ──────────────────────────────────────────────────────
  const soil = {
    predict: (payload) => post("/soil/predict", payload),
    getHistory: (page = 1, pageSize = 20) =>
      get(`/soil/history?page=${page}&page_size=${pageSize}`),
    getById: (id) => get(`/soil/${id}`),
  };

  // ── Map Endpoints ───────────────────────────────────────────────────────
  const map = {
    getMarkers: (filters = {}) => {
      const params = new URLSearchParams(
        Object.fromEntries(Object.entries(filters).filter(([, v]) => v))
      ).toString();
      return get(`/map/markers${params ? "?" + params : ""}`);
    },
    getHeatmap: () => get("/map/heatmap"),
    getDiseaseHotspots: () => get("/map/disease-hotspots"),
    getMyFarms: () => get("/map/my-farms"),
  };

  // ── History Endpoints ───────────────────────────────────────────────────
  const history = {
    getCombined: (page = 1, pageSize = 20, type = "all") =>
      get(`/history/?page=${page}&page_size=${pageSize}&prediction_type=${type}`),
    getDashboard: () => get("/history/dashboard"),
  };

  // ── Notifications ───────────────────────────────────────────────────────
  const notifications = {
    list: (unreadOnly = false) => get(`/notifications/?unread_only=${unreadOnly}`),
    unreadCount: () => get("/notifications/unread-count"),
    markRead: (id) => post(`/notifications/${id}/read`),
    markAllRead: () => post("/notifications/read-all"),
  };

  // ── Reports ──────────────────────────────────────────────────────────
  const reports = {
    generate: (payload) => post("/reports/generate", payload),
    list: () => get("/reports/"),
    getById: (id) => get(`/reports/${id}`),
  };

  // ── Admin ───────────────────────────────────────────────────────────
  const admin = {
    getUsers: (page = 1, role = "all") => get(`/admin/users?page=${page}&role=${role}`),
    getUser: (uid) => get(`/admin/users/${uid}`),
    deleteUser: (uid) => del(`/admin/users/${uid}`),
    toggleStatus: (uid) => post(`/admin/users/${uid}/toggle-status`),
    getAnalytics: () => get("/admin/analytics"),
    getOutbreaks: (severity = "severe") => get(`/admin/disease-outbreaks?severity=${severity}`),
    getAllReports: (page = 1) => get(`/admin/reports?page=${page}`),
  };

  // ── Weather Endpoints ────────────────────────────────────────────────────
  const weather = {
    getCurrent: (lat, lon) => get(`/weather/current?lat=${lat}&lon=${lon}`),
    getForecast: (lat, lon, days = 7) => get(`/weather/forecast?lat=${lat}&lon=${lon}&days=${days}`),
    getAgri: (lat, lon) => get(`/weather/agricultural?lat=${lat}&lon=${lon}`),
    getAlerts: (lat, lon) => get(`/weather/alerts?lat=${lat}&lon=${lon}`),
  };

  // ── Risk Endpoints ───────────────────────────────────────────────────────
  const risk = {
    assess: (payload) => post("/risk/assess", payload),
    evaluate: (payload) => post("/risk/evaluate", payload),
    get: (farmId, crop, lat, lon) => {
      const q = new URLSearchParams();
      if (farmId) q.append("farm_id", farmId);
      if (crop) q.append("crop", crop);
      if (lat != null) q.append("lat", lat);
      if (lon != null) q.append("lon", lon);
      return get(`/risk?${q.toString()}`);
    },
    getHistory: (page = 1, pageSize = 10) => get(`/risk/history?page=${page}&page_size=${pageSize}`),
  };

  // ── Irrigation Endpoints ─────────────────────────────────────────────────
  const irrigation = {
    recommend: (payload) => post("/irrigation/recommend", payload),
    calculate: (payload) => post("/irrigation/calculate", payload),
    getRecommendation: (farmId, crop, growthStage, soilType, lat, lon) => {
      const q = new URLSearchParams();
      if (farmId) q.append("farm_id", farmId);
      if (crop) q.append("crop", crop);
      if (growthStage) q.append("growth_stage", growthStage);
      if (soilType) q.append("soil_type", soilType);
      if (lat != null) q.append("lat", lat);
      if (lon != null) q.append("lon", lon);
      return get(`/irrigation/recommendation?${q.toString()}`);
    },
    getSchedule: (farmId) => get(`/irrigation/schedule/${farmId}`),
    getHistory: (page = 1, pageSize = 10) => get(`/irrigation/history?page=${page}&page_size=${pageSize}`),
  };

  // ── Health Check ────────────────────────────────────────────────────────
  const health = () => fetch(`${BASE()}/api/health`).then(r => r.json()).catch(e => ({ status: "unhealthy", error: e.message }));

  return { auth, disease, soil, weather, risk, irrigation, map, history, notifications, reports, admin, health, request };
})();

window.CropPulseAPI = CropPulseAPI;
