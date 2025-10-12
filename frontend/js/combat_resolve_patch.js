// frontend/js/combat_resolve_patch.js
// Attack flow that targets the nearest enemy token from BV.tokens, applies damage, and logs a result.

(() => {
  const byId = (id) => document.getElementById(id);
  const chatLog = byId('chat-log');
  const canvas = byId('map-canvas');
  const attackBtn = byId('act-attack');
  const endBtn = byId('act-end');

  window.BV = window.BV || {};
  const S = window.BV;
  S.hp = S.hp || {};
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
    const t = byId('hud-char')?.textContent || '';
    const m = t.match(/Active:\s*([^|]+)/i);
    return (m ? m[1] : t || 'You').trim();
  }

  function d(n) { return 1 + Math.floor(Math.random() * n); }

  function canvasPointFromEvent(ev) {
    const rect = canvas.getBoundingClientRect();
    return { x: ev.clientX - rect.left, y: ev.clientY - rect.top };
  }

  function attackVs(targetToken, attacker) {
    const roll = d(20);
    const total = roll + S.rules.atkBonus;
    const hit = total >= S.rules.ac;
    let out = `<b>${attacker}</b> attacks <b>${targetToken.name}</b> — d20: <b>${roll}</b> + ${S.rules.atkBonus} = <b>${total}</b> vs AC ${S.rules.ac} → ${hit ? 'HIT' : 'MISS'}.`;

    if (hit) {
      const dmg = d(S.rules.dmgDie) + 2;
      if (S.tokens?.applyDamage) S.tokens.applyDamage(targetToken.id, dmg);
      out += ` Damage: <b>${dmg}</b>. ${targetToken.name} HP updated.`;
    }
    log(out);
  }

  let waitingForTarget = false;

  attackBtn?.addEventListener('click', () => {
    waitingForTarget = true;
    log('Attack armed: click a target (nearest enemy token will be used).');
  }, true);

  canvas?.addEventListener('click', (ev) => {
    if (!waitingForTarget) return;
    waitingForTarget = false;

    const pt = canvasPointFromEvent(ev);
    const tgt = S.tokens?.getNearest?.(pt, { team: 'enemies', maxDist: 28 }) || null;
    if (!tgt) {
      log('No enemy token near the click. (Use “Spawn Enemy” first.)');
      return;
    }
    const me = activeName() || 'You';
    attackVs(tgt, me);
  }, true);

  endBtn?.addEventListener('click', () => log('— End Turn —'), true);
})();

