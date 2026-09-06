/**
 * CropPulse – Notifications Page JS
 */

let currentPage = 1;
const PAGE_SIZE = 20;

document.addEventListener("DOMContentLoaded", () => {
  Auth.requireAuth();
  loadNotifications();
  document.getElementById("mark-all-btn")?.addEventListener("click", markAllRead);
  document.getElementById("unread-only-toggle")?.addEventListener("change", () => {
    currentPage = 1; loadNotifications();
  });
});

async function loadNotifications() {
  Utils.showSkeleton("notifications-list", 5, "80px");
  const unreadOnly = document.getElementById("unread-only-toggle")?.checked || false;
  try {
    const data = await CropPulseAPI.notifications.list(unreadOnly ? 1 : 0);
    renderNotifications(data.notifications || [], data.unread_count || 0);
  } catch {
    Utils.showToast("Failed to load notifications.", "error");
  }
}

function renderNotifications(notifications, unreadCount) {
  const list = document.getElementById("notifications-list");
  if (!list) return;

  const badge = document.getElementById("unread-badge");
  if (badge) badge.textContent = unreadCount;

  if (!notifications.length) {
    list.innerHTML = `
      <div class="text-center py-5">
        <div style="font-size:3rem;">🔔</div>
        <h5 class="mt-3" style="color:var(--text-muted);">No notifications</h5>
        <p class="text-muted">You're all caught up!</p>
      </div>`;
    return;
  }

  const icons = { disease_alert: "🦠", soil_alert: "💧", system: "🌱", report_ready: "📄" };
  list.innerHTML = notifications.map(n => `
    <div class="ag-card mb-2 d-flex align-items-start gap-3 ${!n.is_read ? 'unread-notif' : ''}"
         id="notif-${n.notification_id}"
         style="${!n.is_read ? 'border-left:3px solid var(--primary);' : ''}cursor:pointer;"
         onclick="markRead('${n.notification_id}', this)">
      <div style="font-size:1.5rem;flex-shrink:0;">${icons[n.type] || "📢"}</div>
      <div style="flex:1;min-width:0;">
        <div class="d-flex align-items-center justify-content-between gap-2">
          <div class="fw-600" style="font-size:0.9rem;color:var(--text-primary);">${Utils.sanitizeHTML(n.title)}</div>
          ${!n.is_read ? '<span style="width:8px;height:8px;background:var(--primary);border-radius:50%;flex-shrink:0;"></span>' : ''}
        </div>
        <div class="text-muted mt-1" style="font-size:0.83rem;">${Utils.sanitizeHTML(n.message)}</div>
        <small class="text-muted" style="font-size:0.75rem;">${Utils.formatRelativeTime(n.created_at)}</small>
      </div>
      <div style="font-size:0.75rem;color:var(--text-muted);flex-shrink:0;text-transform:capitalize;">
        ${n.type?.replace(/_/g, " ") || ""}
      </div>
    </div>
  `).join("");
}

async function markRead(id, el) {
  try {
    await CropPulseAPI.notifications.markRead(id);
    el.style.borderLeft = "";
    el.querySelector(".unread-dot")?.remove();
    el.classList.remove("unread-notif");
    // Decrease badge
    const badge = document.getElementById("unread-badge");
    if (badge) {
      const count = parseInt(badge.textContent || "0") - 1;
      badge.textContent = Math.max(0, count);
    }
  } catch { /* silent */ }
}

async function markAllRead() {
  try {
    await CropPulseAPI.notifications.markAllRead();
    Utils.showToast("All notifications marked as read.", "success");
    loadNotifications();
  } catch {
    Utils.showToast("Failed to mark all as read.", "error");
  }
}
