// frontend/js/token_overlay_patch.js
// Lightweight token overlay that does NOT touch your big app.js.
// Draws simple tokens on a canvas layered above #map-canvas and exposes a tiny API on window.BV.tokens.

(() => {
  const byId = (id) => document.getElementById(id);

  // Ensure global bag
  window.BV = window.BV || {};
  const S = window.BV;
  S.tokens = S.tokens || {};

  const stage = document.querySelector('main.stage') || document.body;
  const base = byId('map-canvas');

  // Build overlay canvas
  const overlay = document.createElement('canvas');
  overlay.id = 'overlay-canvas';
  Object.assign(overlay.style, {
    position: 'absolute',
    inset: '0',
    pointerEvents: 'none', // clicks still reach the base canvas
    zIndex: '5',
  });

  // Ensure the stage is positioned so absolute children overlay correctly
  const restorePos = stage.style.position;
  if (getComputedStyle(stage).position === 'static') stage.style.position = 'relative';
  stage.appendChild(overlay);

  // Internal state
  const DPR = Math.max(1, window.devicePixelRatio || 1);
  const TOKENS = []; // {id, name, team, x, y, r, hp, maxHp, color, down}
  let nextId = 1;
  let placingEnemy = false;

  function resize() {
    const rect = base.getBoundingClientRect();
    overlay.width = Math.floor(rect.width * DPR);
    overlay.height = Math.floor(rect.height * DPR);
    overlay.style.width = rect.width + 'px';
    overlay.style.height = rect.height + 'px';
    draw();
  }

  window.addEventListener('resize', resize);
  resize();

  function drawToken(ctx, t) {
    const x = t.x * DPR, y = t.y * DPR, r = t.r * DPR;

    // token
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = t.down ? '#700' : t.color;
    ctx.fill();
    ctx.lineWidth = 2 * DPR;
    ctx.strokeStyle = t.down ? '#d33' : '#222';
    ctx.stroke();

    // name
    ctx.font = `${12 * DPR}px system-ui, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    ctx.fillStyle = '#eee';
    ctx.fillText(t.name, x, y + (r + 3) * DPR);

    // hp
    ctx.font = `${11 * DPR}px system-ui, sans-serif`;
    ctx.textBaseline = 'bottom';
    ctx.fillStyle = '#9ef';
    ctx.fillText(`HP ${Math.max(0, t.hp)}/${t.maxHp}`, x, y - (r + 4) * DPR);

    if (t.down) {
      ctx.strokeStyle = '#f66';
      ctx.lineWidth = 3 * DPR;
      ctx.beginPath();
      ctx.moveTo(x - r * 0.7, y - r * 0.7);
      ctx.lineTo(x + r * 0.7, y + r * 0.7);
      ctx.moveTo(x + r * 0.7, y - r * 0.7);
      ctx.lineTo(x - r * 0.7, y + r * 0.7);
      ctx.stroke();
    }
  }

  function draw() {
    const ctx = overlay.getContext('2d');
    if (!ctx) return;
    ctx.clearRect(0, 0, overlay.width, overlay.height);

    for (const t of TOKENS) drawToken(ctx, t);
  }

  // Helpers
  function canvasPointFromEvent(ev) {
    const rect = base.getBoundingClientRect();
    return { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
  }

  function dist2(a, b) {
    const dx = a.x - b.x, dy = a.y - b.y;
    return dx * dx + dy * dy;
  }

  // Public API
  S.tokens.add = function addToken({ name, team = 'enemies', x, y, r = 12, hp = 12, color = '#e66' }) {
    const t = { id: String(nextId++), name, team, x, y, r, hp, maxHp: hp, color, down: false };
    TOKENS.push(t);
    draw();
    return t.id;
  };

  S.tokens.applyDamage = function applyDamage(id, dmg) {
    const t = TOKENS.find(o => o.id === id);
    if (!t) return;
    t.hp -= Math.max(0, dmg|0);
    if (t.hp <= 0) t.down = true;
    draw();
  };

  S.tokens.getNearest = function getNearest(pt, { team, maxDist = 28 } = {}) {
    let best = null;
    let bestD2 = (maxDist * maxDist);
    for (const t of TOKENS) {
      if (team && t.team !== team) continue;
      const d2 = dist2(pt, t);
      if (d2 <= bestD2) {
        best = t;
        bestD2 = d2;
      }
    }
    return best; // token or null
  };

  S.tokens.clearAll = function clearAll() {
    TOKENS.length = 0;
    draw();
  };

  // UI: Spawn Enemy button (you’ll add it in index.html)
  const btn = document.getElementById('btn-spawn-enemy');
  btn?.addEventListener('click', () => {
    placingEnemy = true;
    // Use chat log if present
    const chat = document.getElementById('chat-log');
    if (chat) {
      const row = document.createElement('div');
      row.className = 'bubble system';
      row.textContent = 'Click the map to place an enemy token.';
      chat.appendChild(row);
      chat.scrollTop = chat.scrollHeight;
    }
  });

  // Place on next click anywhere on base canvas
  base?.addEventListener('click', (ev) => {
    if (!placingEnemy) return;
    placingEnemy = false;
    const pt = canvasPointFromEvent(ev);
    const idx = TOKENS.filter(t => t.team === 'enemies').length + 1;
    S.tokens.add({ name: `Enemy ${idx}`, team: 'enemies', x: pt.x, y: pt.y, hp: 12, r: 12, color: '#e66' });
  }, true);

  // Safety: if this module is removed, restore original stage position
  window.addEventListener('beforeunload', () => {
    if (restorePos) stage.style.position = restorePos;
  });
})();
