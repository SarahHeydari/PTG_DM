// frontend/static/frontend/js/auth.js

function dmGetToken() {
  return localStorage.getItem("access_token");
}

function dmSetToken(token) {
  localStorage.setItem("access_token", token);
}

function dmClearToken() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("dm_user"); // اگر ذخیره کرده باشی
}

function dmRedirectToLogin() {
  window.location.href = "/ui/login/";
}

function dmToast(message, type = "info") {
  const el = document.getElementById("dm-toast");
  if (!el) return alert(message);

  el.className = `dm-toast dm-toast-${type}`;
  el.textContent = message;
  el.style.opacity = "1";
  el.style.transform = "translateY(0)";
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transform = "translateY(12px)";
  }, 2200);
}

async function dmApiFetch(url, options = {}) {
  const token = dmGetToken();
  const headers = options.headers || {};

  headers["Content-Type"] = headers["Content-Type"] || "application/json";
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(url, { ...options, headers });

  if (res.status === 401) {
    dmToast("جلسه شما منقضی شده. دوباره وارد شوید.", "warn");
    dmClearToken();
    setTimeout(dmRedirectToLogin, 600);
    throw new Error("Unauthorized");
  }

  // 403 را هم می‌گیریم ولی ریدایرکت نمی‌کنیم؛ پیام می‌دهیم
  if (res.status === 403) {
    let data = {};
    try { data = await res.json(); } catch (e) {}
    dmToast(data?.detail || "شما دسترسی انجام این عملیات را ندارید.", "danger");
    throw new Error("Forbidden");
  }

  return res;
}

async function dmGetMyProfile() {
  const res = await dmApiFetch("/api/users/myprofile/");
  const data = await res.json();
  return data; // {id, username, role, email, ...}
}

function dmRequireLogin() {
  const token = dmGetToken();
  if (!token) dmRedirectToLogin();
}

function dmSetUserUI(user) {
  const username = user?.username || "کاربر";
  const role = user?.role || "—";

  const u1 = document.getElementById("ui-username");
  const r1 = document.getElementById("ui-role");
  const av = document.getElementById("ui-avatar");

  if (u1) u1.textContent = username;
  if (r1) r1.textContent = role;
  if (av) av.textContent = (username[0] || "U").toUpperCase();
}
