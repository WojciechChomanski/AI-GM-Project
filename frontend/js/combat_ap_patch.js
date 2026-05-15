// frontend/js/combat_ap_patch.js
// Milestone A — AP/Stamina overlay + action spending (no edits to app.js)

(() => {
  // ---- Tunables (aligned with rules/combat/action_economy_v0_1.json) ----
  const ROUND_SECONDS = 6;

  // Base AP formula: 6 + floor((AGI - 8)/3) - encPenalty
  function computeAPPerRound({ AGI = 8, encumbrance = 'light' } = {}) {
    const base = 6;
    const agiBonus = Math.floor((AGI - 8) / 3);
    const encPenalty = encumbrance === 'medium' ? 1 : encumbrance === 'heavy' ? 2 : 0;
    return Math.max(0, base + agiBonus - encPenalty);
  }

  // Costs (subset for Milestone A)
  const ACTIONS = {
    move:          { ap: 1, stamina: 0 },
    melee_attack:  { ap: 3, stamina: 1 },
    ranged_attack: { ap: 3, stamina: 1 },
    guard:         { ap: 1, stamina: 0 }, // "Defend"
    ability:       { ap: 2, stamina: 1 },
  };

  const STAMINA_REGEN_PER_TURN = 1;
  const STAMINA_MAX = 6;   // simple soft cap for playtesting
  const STAMINA_MIN = 0;

  // ---- Local state (simple, per-current-actor only) ----
  const State = {
    round: 0,
    turn:  0,
    cur:   {
      AGI: 8,
      encumbrance: 'light',
      apMax: 0,
      ap: 0,
      stamina: STAMINA_MAX, // start topped up for now
    },
    ui: {
      hudAP: null,
      hudSTA: null,
      toastBox: null,
    },
    initialized: false,
  };

  // ---- DOM helpers ----
  function $(id) { return document.getElementById(id); }

  function ensureHUD() {
    const hud = document.querySelector('.overlay.hud');
    if (!hud) return;

    // AP badge
    if (!State.ui.hudAP) {
      const span = document.createElement('span');
      span.id = 'hud-ap';
      span.textContent = 'AP —/—';
      span.style.marginLeft = '8px';
      State.ui.hudAP = span;
      hud.appendChild(span);
    }
    // Stamina badge
    if (!State.ui.hudSTA) {
      const span = document.createElement('span');
      span.id = 'hud-stamina';
      span.textContent = 'STA —';
      span.style.marginLeft = '8px';
      State.ui.hudSTA = span;
      hud.appendChild(span);
    }

    // tiny toast box (non-intrusive)
    if (!State.ui.toastBox) {
      const tb = document.createElement('div');
      tb.id = 'ap-toasts';
      Object.assign(tb.style, {
        position: 'absolute',
        right: '16px',
        bottom: '16px',
        zIndex: 9999,
        fontFamily: 'system-ui, sans-serif',
        fontSize: '12px',
        maxWidth: '40ch',
      });
      document.body.appendChild(tb);
      State.ui.toastBox = tb;
    }
  }

  function toast(msg, ms = 1600) {
    if (!State.ui.toastBox) return;
    const box = document.createElement('div');
    Object.assign(box.style, {
      background: 'rgba(0,0,0,0.72)',
      color: 'white',
      padding: '6px 10px',
      borderRadius: '8px',
      marginTop: '6px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
    });
    box.textContent = msg;
    State.ui.toastBox.appendChild(box);
    setTimeout(() => box.remove(), ms);
  }

  function updateHUD() {
    ensureHUD();
    if (State.ui.hudAP)  State.ui.hudAP.textContent  = `AP ${State.cur.ap}/${State.cur.apMax}`;
    if (State.ui.hudSTA) State.ui.hudSTA.textContent = `STA ${State.cur.stamina}`;
  }

  // ---- Core logic ----
  function startCombat() {
    State.round = 1;
    State.turn  = 1;
    State.cur.apMax = computeAPPerRound({ AGI: State.cur.AGI, encumbrance: State.cur.encumbrance });
    State.cur.ap = State.cur.apMax;
    // Stamina stays as-is (topped for now)
    updateHUD();
    toast(`Combat started • Round ${State.round}, Turn ${State.turn}`);
  }

  function nextTurn() {
    State.turn += 1;
    // regen stamina a little each turn
    State.cur.stamina = Math.min(STAMINA_MAX, State.cur.stamina + STAMINA_REGEN_PER_TURN);
    // refresh AP
    State.cur.apMax = computeAPPerRound({ AGI: State.cur.AGI, encumbrance: State.cur.encumbrance });
    State.cur.ap = State.cur.apMax;
    updateHUD();
    toast(`Turn ${State.turn} • AP refreshed`);
  }

  function endCombat() {
    toast('Combat ended.');
    // keep numbers visible but don’t mutate further
  }

  function canSpend(apCost) {
    return State.cur.ap >= apCost;
  }

  function spendAction(actionId) {
    const a = ACTIONS[actionId];
    if (!a) { toast(`Unknown action: ${actionId}`); return false; }

    if (!canSpend(a.ap)) {
      toast(`Not enough AP: need ${a.ap}, have ${State.cur.ap}`);
      return false;
    }

    State.cur.ap -= a.ap;
    State.cur.stamina = Math.max(STAMINA_MIN, State.cur.stamina - (a.stamina || 0));
    updateHUD();
    return true;
  }

  // ---- Button wiring ----
  function wireButtons() {
    const byId = (id) => $(id) || null;

    const btnStart = byId('btn-start-combat');
    const btnNext  = byId('btn-next-turn');
    const btnEnd   = byId('btn-end-combat');

    const actMove    = byId('act-move');
    const actAttack  = byId('act-attack');
    const actAbility = byId('act-ability');
    const actDefend  = byId('act-defend');
    const actEnd     = byId('act-end');

    if (btnStart && !btnStart.__ap_wired) {
      btnStart.addEventListener('click', () => startCombat());
      btnStart.__ap_wired = true;
    }
    if (btnNext && !btnNext.__ap_wired) {
      btnNext.addEventListener('click', () => nextTurn());
      btnNext.__ap_wired = true;
    }
    if (btnEnd && !btnEnd.__ap_wired) {
      btnEnd.addEventListener('click', () => endCombat());
      btnEnd.__ap_wired = true;
    }

    if (actMove && !actMove.__ap_wired) {
      actMove.addEventListener('click', () => {
        if (spendAction('move')) {
          toast('Move: choose a destination on the map');
          // (Milestone B/C will integrate real capture on canvas)
        }
      });
      actMove.__ap_wired = true;
    }

    if (actAttack && !actAttack.__ap_wired) {
      actAttack.addEventListener('click', () => {
        // For now, treat as melee. If you want ranged, swap id to 'ranged_attack'.
        if (spendAction('melee_attack')) {
          toast('Attack: click a target token');
        }
      });
      actAttack.__ap_wired = true;
    }

    if (actAbility && !actAbility.__ap_wired) {
      actAbility.addEventListener('click', () => {
        if (spendAction('ability')) {
          toast('Ability: select a target or area');
        }
      });
      actAbility.__ap_wired = true;
    }

    if (actDefend && !actDefend.__ap_wired) {
      actDefend.addEventListener('click', () => {
        if (spendAction('guard')) {
          toast('Defend: guarding (reaction readied)');
        }
      });
      actDefend.__ap_wired = true;
    }

    if (actEnd && !actEnd.__ap_wired) {
      actEnd.addEventListener('click', () => nextTurn());
      actEnd.__ap_wired = true;
    }
  }

  function init() {
    if (State.initialized) return;
    ensureHUD();
    updateHUD();
    wireButtons();
    State.initialized = true;
  }

  // Kick off after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
  } else {
    init();
  }

  // Expose a tiny debug handle if needed
  window.CombatAP = {
    get state() { return JSON.parse(JSON.stringify(State)); },
    setStats({ AGI, encumbrance } = {}) {
      if (Number.isFinite(AGI)) State.cur.AGI = AGI;
      if (encumbrance) State.cur.encumbrance = encumbrance;
      State.cur.apMax = computeAPPerRound({ AGI: State.cur.AGI, encumbrance: State.cur.encumbrance });
      State.cur.ap = Math.min(State.cur.ap, State.cur.apMax);
      updateHUD();
    },
    reset() {
      State.round = 0; State.turn = 0;
      State.cur.apMax = 0; State.cur.ap = 0;
      State.cur.stamina = STAMINA_MAX;
      updateHUD();
    }
  };
})();
