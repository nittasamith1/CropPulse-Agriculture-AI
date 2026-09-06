/**
 * CropPulse – Frontend Authentication Module
 * JWT-based Authentication.
 * Handles login, register, logout, password reset,
 * route protection, and user session management via localStorage.
 */

const Auth = (() => {
  const API = () => window.CropPulseAPI;

  // ── Local Storage Keys ──────────────────────────────────────────────────
  const ACCESS_TOKEN_KEY = "ag_access_token";
  const REFRESH_TOKEN_KEY = "ag_refresh_token";
  const USER_KEY         = "ag_user";
  const ROLE_KEY         = "ag_role";

  // ── Store Session ───────────────────────────────────────────────────────
  function setSession(accessToken, refreshToken, user) {
    localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    localStorage.setItem(ROLE_KEY, user.role || "farmer");
  }

  function clearSession() {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(ROLE_KEY);
  }

  // ── Getters ─────────────────────────────────────────────────────────────
  function getToken()        { return localStorage.getItem(ACCESS_TOKEN_KEY); }
  function getRefreshToken() { return localStorage.getItem(REFRESH_TOKEN_KEY); }
  function getUser()         { const u = localStorage.getItem(USER_KEY); try { return u ? JSON.parse(u) : null; } catch { return null; } }
  function getRole()         { return localStorage.getItem(ROLE_KEY) || "farmer"; }
  function isLoggedIn()      { return !!getToken(); }
  function isAdmin()         { return getRole() === "admin"; }

  // ── Decode JWT (Client-side helper) ──────────────────────────────────────
  const decodeJwt = (token) => {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(atob(base64).split('').map((c) => {
        return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
      }).join(''));
      return JSON.parse(jsonPayload);
    } catch (e) {
      return null;
    }
  };

  // ── Get Fresh ID Token (JWT Refresh flow) ────────────────────────────────
  async function getFreshToken() {
    const refreshToken = getRefreshToken();
    if (!refreshToken) return null;
    try {
      const res = await fetch(`${window.API_BASE}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      if (res.ok) {
        const data = await res.json();
        // Fetch profile
        const profileRes = await fetch(`${window.API_BASE}/api/v1/auth/me`, {
          headers: { "Authorization": `Bearer ${data.access_token}` }
        });
        const profile = profileRes.ok ? await profileRes.json() : getUser();
        setSession(data.access_token, data.refresh_token, profile);
        return data.access_token;
      } else {
        clearSession();
        return null;
      }
    } catch (e) {
      console.error("Token refresh failed:", e);
      return null;
    }
  }

  // ── Register ────────────────────────────────────────────────────────────
  async function register(name, email, password, role = "farmer", phone = null, state = null, district = null) {
    try {
      const res = await fetch(`${window.API_BASE}/api/v1/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, name, role, phone, state, district }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Registration failed.");
      }

      return { success: true, message: data.message };
    } catch (err) {
      return { success: false, message: err.message };
    }
  }

  // ── Login ───────────────────────────────────────────────────────────────
  async function login(email, password) {
    try {
      const res = await fetch(`${window.API_BASE}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Incorrect email or password.");
      }

      // Fetch user profile
      const profileRes = await fetch(`${window.API_BASE}/api/v1/auth/me`, {
        headers: { "Authorization": `Bearer ${data.access_token}` },
      });
      const userProfile = profileRes.ok ? await profileRes.json() : { uid: "temp", email, name: data.name, role: data.role };

      setSession(data.access_token, data.refresh_token, userProfile);
      return { success: true, user: userProfile };
    } catch (err) {
      return { success: false, message: err.message };
    }
  }

  // ── Logout ──────────────────────────────────────────────────────────────
  async function logout() {
    try {
      const token = getRefreshToken();
      if (token) {
        await fetch(`${window.API_BASE}/api/v1/auth/logout`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: token }),
        });
      }
    } catch (e) {
      console.warn("Logout request failed:", e);
    }
    clearSession();
    window.location.href = "/pages/login.html";
  }

  // ── Forgot Password ─────────────────────────────────────────────────────
  async function forgotPassword(email) {
    try {
      const res = await fetch(`${window.API_BASE}/api/v1/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Forgot password process failed.");
      return { success: true, message: data.message };
    } catch (err) {
      return { success: false, message: err.message };
    }
  }

  // ── Reset Password ──────────────────────────────────────────────────────
  async function resetPassword(token, newPassword) {
    try {
      const res = await fetch(`${window.API_BASE}/api/v1/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: newPassword }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Password reset failed.");
      return { success: true, message: data.message };
    } catch (err) {
      return { success: false, message: err.message };
    }
  }

  // ── Verify Email ────────────────────────────────────────────────────────
  async function verifyEmail(token) {
    try {
      const res = await fetch(`${window.API_BASE}/api/v1/auth/verify-email?token=${token}`, {
        method: "GET"
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Verification failed.");
      return { success: true, message: data.message };
    } catch (err) {
      return { success: false, message: err.message };
    }
  }

  // ── Route Protection ────────────────────────────────────────────────────
  function requireAuth() {
    if (!isLoggedIn()) {
      window.location.href = "/pages/login.html";
      return;
    }
    
    // Check if token is expired, try refreshing it
    const decoded = decodeJwt(getToken());
    if (decoded && decoded.exp * 1000 < Date.now()) {
      getFreshToken().then(token => {
        if (!token) {
          window.location.href = "/pages/login.html";
        } else {
          updateNavbarUser();
        }
      });
    } else {
      updateNavbarUser();
    }
  }

  function requireAdmin() {
    if (!isLoggedIn()) {
      window.location.href = "/pages/login.html";
      return;
    }
    if (!isAdmin()) {
      alert("Access Denied. Admins only.");
      window.location.href = "/pages/dashboard.html";
      return;
    }
    updateNavbarUser();
  }

  // ── Update Navbar ───────────────────────────────────────────────────────
  function updateNavbarUser() {
    const user = getUser();
    if (!user) return;
    const nameEl = document.getElementById("nav-user-name");
    const avatarEl = document.getElementById("nav-user-avatar");
    if (nameEl) nameEl.textContent = user.name || user.email;
    if (avatarEl) {
      if (user.profile_picture_url) {
        avatarEl.src = user.profile_picture_url;
      } else {
        // If it is an image element, change source or build a fallback text avatar
        if (avatarEl.tagName.toLowerCase() === "img") {
          avatarEl.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(user.name || user.email)}&background=2E7D32&color=fff`;
        } else {
          avatarEl.textContent = (user.name || "U").charAt(0).toUpperCase();
        }
      }
    }
  }

  // Periodic token refresh every 15 minutes if user is logged in
  setInterval(() => {
    if (isLoggedIn()) {
      getFreshToken();
    }
  }, 15 * 60 * 1000);

  return {
    register, login, logout, forgotPassword, resetPassword, verifyEmail,
    requireAuth, requireAdmin,
    getToken, getRefreshToken, getUser, getRole, isLoggedIn, isAdmin,
    getFreshToken, updateNavbarUser, clearSession,
  };
})();

window.Auth = Auth;
