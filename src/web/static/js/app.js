const fetchApi = async (url, opts = {}) => {
  const res = await fetch(url, { headers: { 'Accept': 'application/json' }, ...opts });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
};

// ─── Theme ────────────────────────────────────────
function initTheme() {
  const saved = localStorage.getItem('nemo_theme') || 'dark';
  document.documentElement.classList.toggle('dark', saved === 'dark');
}

function toggleTheme() {
  const isDark = document.documentElement.classList.toggle('dark');
  localStorage.setItem('nemo_theme', isDark ? 'dark' : 'light');
}

// ─── Language ──────────────────────────────────────
function toggleLang() {
  const next = getLang() === 'en' ? 'ru' : 'en';
  setLang(next);
  // Re-render page-specific
  if (typeof onPageLangChange === 'function') onPageLangChange();
}

// ─── Sidebar mobile ───────────────────────────────
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebarOverlay').classList.toggle('open');
}

function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebarOverlay').classList.remove('open');
}

// ─── Toast ─────────────────────────────────────────
function showToast(msg) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), 3000);
}

// ─── Chart helpers ─────────────────────────────────
const chartDefaults = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 800 },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: 'rgba(30,32,48,0.9)',
      titleFont: { family: 'Inter', size: 12 },
      bodyFont: { family: 'Inter', size: 13 },
      padding: 10,
      cornerRadius: 8,
      displayColors: false,
    }
  },
  scales: {
    x: {
      grid: { display: false },
      ticks: { font: { family: 'Inter', size: 11 }, color: getComputedStyle(document.documentElement).getPropertyValue('--text-3').trim() },
      border: { display: false },
    },
    y: {
      grid: { color: getComputedStyle(document.documentElement).getPropertyValue('--border').trim() },
      ticks: { font: { family: 'Inter', size: 11 }, color: getComputedStyle(document.documentElement).getPropertyValue('--text-3').trim() },
      border: { display: false },
    }
  }
};

function makeGradient(ctx, c1, c2) {
  const g = ctx.createLinearGradient(0, 0, 0, ctx.canvas.clientHeight);
  g.addColorStop(0, c1);
  g.addColorStop(1, c2);
  return g;
}

function getChartColors() {
  const isDark = document.documentElement.classList.contains('dark');
  return {
    primary: isDark ? '#a29bfe' : '#6c5ce7',
    green: isDark ? '#00d2a0' : '#00b894',
    red: isDark ? '#ff6b6b' : '#e74c3c',
    gridColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
    tickColor: isDark ? '#5a6474' : '#94a3b8',
  };
}

function scaleOpts() {
  const c = getChartColors();
  return {
    x: { grid: { display: false }, ticks: { font: { family: 'Inter', size: 11 }, color: c.tickColor }, border: { display: false } },
    y: { grid: { color: c.gridColor }, ticks: { font: { family: 'Inter', size: 11 }, color: c.tickColor }, border: { display: false } },
  };
}

// ─── WebSocket ─────────────────────────────────────
let ws;
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${location.host}/ws`);
  ws.onclose = () => setTimeout(connectWS, 5000);
  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      if (msg.event === 'dashboard_update' && typeof onDashboardUpdate === 'function') {
        onDashboardUpdate(msg.data);
      }
    } catch {}
  };
}

// ─── Init ──────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTheme();
  setLang(getLang());
  if (typeof onPageLoad === 'function') onPageLoad();
  connectWS();
});
