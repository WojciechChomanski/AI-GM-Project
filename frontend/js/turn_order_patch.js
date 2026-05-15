// Light turn/round + "only act on your turn" guard.
// No edits to app.js. Hooks existing buttons and list DOM.

const qs  = (sel) => document.querySelector(sel);
const qsa = (sel) => Array.from(document.querySelectorAll(sel));

const els = {
  addSel:   qs('#btn-combat-add'),
  start:    qs('#btn-start-combat'),
  next:     qs('#btn-next-turn'),
  end:      qs('#btn-end-combat'),
  team:     qs('#sel-team'),
  orderUL:  qs('#turn-order'),
  info:     qs('#turn-info'),
  // action buttons
  actMove:   qs('#act-move'),
  actAtk:    qs('#act-attack'),
  actAbil:   qs('#act-ability'),
  actDef:    qs('#act-defend'),
  actEnd:    qs('#act-end'),
};

const state = {
  roster: [],       // [{id:'P1', team:'players'}, ...]
  idx: -1,          // current index in roster
  round: 0,
  started: false,
};

// --- helpers ---
function renderOrder() {
  els.orderUL.innerHTML = state.roster.map((u, i) => {
    const active = i === state.idx ? ' style="font-weight:600;"' : '';
    return `<li${active}>${u.id} <small class="muted">(${u.team})</small></li>`;
  }).join('') || `<li class="muted">— no participants —</li>`;
}

function updateInfo() {
  if (!state.started) {
    els.info.textContent = `Round — • Turn —`;
    return;
  }
  const who = state.roster[state.idx]?.id ?? '—';
  els.info.textContent = `Round ${state.round} • Turn ${who}`;
}

function toast(msg) {
  // reuse small HUD area (bottom-left) if available; otherwise alert
  const hud = document.querySelector('.overlay.hud');
  if (!hud) return alert(msg);
  let el = hud.querySelector('.ap-toast');
  if (!el) {
    el = document.createElement('div');
    el.className = 'ap-toast';
    el.style.cssText = 'position:absolute; left:16px; bottom:48px; font-size:12px; opacity:.9;';
    hud.appendChild(el);
  }
  el.textContent = msg;
  clearTimeout(el._t);
  el._t = setTimeout(() => (el.textContent = ''), 1400);
}

function enableActions(enabled) {
  [els.actMove, els.actAtk, els.actAbil, els.actDef, els.actEnd]
    .forEach(b => { if (b) b.disabled = !enabled; });
}

function startCombat() {
  if (state.roster.length === 0) {
    // auto add one player if empty
    state.roster.push({ id: 'P1', team: 'players' });
  }
  state.round = 1;
  state.idx   = 0;
  state.started = true;
  renderOrder();
  updateInfo();
  enableActions(true);
  // refresh AP/STA for the first turn
  if (window.CombatAP?.reset) window.CombatAP.reset();
}

function nextTurn() {
  if (!state.started || state.roster.length === 0) return;
  state.idx = (state.idx + 1) % state.roster.length;
  if (state.idx === 0) state.round += 1;
  renderOrder();
  updateInfo();
  enableActions(true);
  if (window.CombatAP?.reset) window.CombatAP.reset();
}

function endCombat() {
  state.started = false;
  state.idx = -1;
  state.round = 0;
  renderOrder();
  updateInfo();
  enableActions(false);
}

// --- wire roster building to your existing "Add Selected" ---
(function wireRoster() {
  if (!els.addSel) return;
  let pCount = 0, eCount = 0, nCount = 0;

  els.addSel.addEventListener('click', () => {
    const team = (els.team?.value || 'players').toLowerCase();
    let id;
    if (team === 'players') id = `P${++pCount}`;
    else if (team === 'enemies') id = `E${++eCount}`;
    else id = `N${++nCount}`;

    state.roster.push({ id, team });
    renderOrder();
  });
})();

// --- wire control buttons ---
els.start?.addEventListener('click', startCombat);
els.next?.addEventListener('click', nextTurn);
els.end?.addEventListener('click', endCombat);

// --- action guard: only active combatant may act ---
const actionButtons = [els.actMove, els.actAtk, els.actAbil, els.actDef];
actionButtons.forEach(btn => {
  if (!btn) return;
  // capture-phase listener runs before AP overlay’s handlers
  btn.addEventListener('click', (ev) => {
    if (!state.started || state.idx < 0) {
      ev.stopImmediatePropagation();
      ev.preventDefault();
      toast('Combat not started');
    }
    // (Optional) you could also block by team/ownership here
  }, true);
});

// initial paint
renderOrder();
updateInfo();
enableActions(false);

// Expose for quick debugging if needed
window.TurnOrder = { state, startCombat, nextTurn, endCombat };
