// frontend/js/combat_resolve_patch.js
// Minimal attack resolution overlay that doesn't modify your big app.js.
// Flow: click "Attack" -> click the map -> we roll to-hit and damage and log to chat.

(() => {
  const byId = (id) => document.getElementById(id);
  const chatLog = byId('chat-log');
  const canvas = byId('map-canvas');
  const attackBtn = byId('act-attack');
  const endBtn = byId('act-end');

  // Global stash we can re-use without touching your big code
  window.BV = window.BV || {};
  const S = window.BV;
  S.hp = S.hp || {};
  // Very simple defaults for a proof-of-concept; we’ll replace with real stats later
  S.rules = S.rules || { defaultHP: 12, ac: 12, dmgDie: 8, atkBonus: 2 };

  function log(html) {
    if (!chatLog) return;
    const row = document.createElement('div');
    row.className = 'bubble system';
    row.innerHTML = html;
    chatLog.appendChild(row);
    chatLog.scrollTop = chatLog.scrollHeight;
  }

  function activeName() {
    // We try to read the HUD label. Your HUD shows "Active: NAME" during combat.
    const t = byId('hud-char')?.textContent || '';
    const m = t.match(/Active:\s*([^|]+)/i);
    return (m ? m[1] : t || 'You').trim();
  }

  function ensureChar(name) {
    if (!S.hp[name]) S.hp[name] = S.rules.defaultHP;
  }

  function d(n) {
    return 1 + Math.floor(Math.random() * n);
  }

  function doAttack(attacker, target) {
    ensureChar(attacker);
    ensureChar(target);

    const roll = d(20);
    const total = roll + S.rules.atkBonus;
    const hit = total >= S.rules.ac;

    let out = `<b>${attacker}</b> attacks <b>${target}</b> — d20: <b>${roll}</b> + ${S.rules.atkBonus} = <b>${total}</b> vs AC ${S.rules.ac} → ${hit ? 'HIT' : 'MISS'}.`;

    if (hit) {
      const dmg = d(S.rules.dmgDie) + 2; // placeholder STR/DEX bonus
      S.hp[target] -= dmg;
      out += ` Damage: <b>${dmg}</b>. ${target} HP: ${Math.max(0, S.hp[target])}.`;
      if (S.hp[target] <= 0) out += ` <i>${target} is down!</i>`;
    }

    log(out);
  }

  let waitingForTarget = false;

  // When you click Attack, we arm a one-shot target capture.
  // Your AP overlay will still enforce AP/stamina — we only add narration.
  attackBtn?.addEventListener(
    'click',
    () => {
      waitingForTarget = true;
      log('Select a target on the map (placeholder target will be used for now).');
    },
    true // capture so we arm early
  );

  // First click on the canvas after Attack performs the roll.
  canvas?.addEventListener(
    'click',
    () => {
      if (!waitingForTarget) return;
      waitingForTarget = false;

      const me = activeName() || 'You';
      const target = 'Target'; // placeholder until we integrate token selection
      doAttack(me, target);
    },
    true
  );

  // Optional: show a small divider on End Turn
  endBtn?.addEventListener(
    'click',
    () => {
      log('— End Turn —');
    },
    true
  );
})();
