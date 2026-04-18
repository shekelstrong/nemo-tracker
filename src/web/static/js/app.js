/**
 * Nemo Tracker — Main JS (WebSocket + utilities)
 */

// WebSocket for real-time dashboard updates
(function () {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  let ws;
  let retries = 0;

  function connect() {
    ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onopen = () => {
      retries = 0;
      const el = document.getElementById('ws-status');
      if (el) el.innerHTML = '<i class="fas fa-circle text-green-400"></i> Live';
    };
    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.event === 'dashboard_update') {
          // Dispatch custom event so pages can react
          window.dispatchEvent(new CustomEvent('nemo-dashboard', { detail: msg.data }));
        }
      } catch {}
    };
    ws.onclose = () => {
      const el = document.getElementById('ws-status');
      if (el) el.innerHTML = '<i class="fas fa-circle text-yellow-400"></i> Reconnecting';
      retries++;
      setTimeout(connect, Math.min(30000, 1000 * Math.pow(2, retries)));
    };
    ws.onerror = () => ws.close();
  }

  // Only connect if we're on the dashboard
  if (location.pathname === '/') connect();
})();
