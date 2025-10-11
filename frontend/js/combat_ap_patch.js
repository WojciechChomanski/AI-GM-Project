// frontend/js/combat_ap_patch.js
import { computeAPPerRound, ACTIONS } from './combat_rules.js';

const CombatAP = (() => {
  const state = {
    roundSeconds: 6,
    AGI: 8,
    encumbrance: 'light',
    staminaMax: 6,
    stamina: 6,
    apMax: 0,
    apLeft: 0,
  };

  function ensureStyles() {
    const css = `
      .ap-hud{border:1px solid #eee;border-radius:10px;padding:8px;margin-top:10px;background:#fafafa}
      .ap-row{margin-bottom:4px}
      .ap-hud .muted{color:#666;font-size:12px}
      .ap-bad{color:#b00020}
    `;
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
  }

  function recomputeApMax() {
    state.apMax = computeAPPerRound({ AGI: state.AGI, encumbrance: state.encumbrance });
    if (state.apLeft > state.apMax) state.apLeft = state.apMax;
  }

  function render() {
    const apEl  = document.getElementById('ap-val');
    const stEl  = document.getElementById('sta-val');
    if (apEl) apEl.textContent = `${state.apLeft}/${state.apMax}`;
    if (stEl) stEl.textContent = `${state.stamina}/${state.staminaMax}`;
  }

  function flash(el) {
    try {
      el.animate(
        [
          { transform: 'translateX(0)' },
          { transform: 'translateX(4px)' },
          { transform: 'translateX(-4px)' },
          { transform: 'translateX(0)' },
        ],
        { duration: 150 }
      );
    } catch {}
  }

  function getCost(actionId) {
    const a = ACTIONS[actionId];
    if (!a) return { ap: 0, stamina: 0 };
    return { ap: a.ap ?? a.ap_cost ?? 0, stamina: a.stamina ?? a.stamina_cost ?? 0 };
  }

  function canAfford(actionId) {
    const { ap, stamina } = getCost(actionId);
    return state.apLeft >= ap && state.stamina >= stamina;
  }

  function spend(actionId) {
    const { ap, stamina } = getCost(actionId);
    state.apLeft -= ap;
    state.stamina = Math.max(0, state.stamina - stamina);
    render();
    window.dispatchEvent(new CustomEvent('ap:action', { detail: { actionId, cost: { ap, stamina } } }));
  }

  function startTurn() {
    // Regen 1 stamina at start of your turn (per rules JSON)
    state.stamina = Math.min(state.staminaMax, state.stamina + 1);
    recomputeApMax();
    state.apLeft = state.apMax;
    render();
    window.dispatchEvent(new CustomEvent('ap:startTurn', { detail: { ...state } }));
  }

  function bindAction(selector, actionId) {
    const btn = document.querySelector(selector);
    if (!btn) return;
    btn.addEventListener(
      'click',
      (e) => {
        if (!canAfford(actionId)) {
          flash(btn);
          e.stopImmediatePropagation();
          e.preventDefault();
          return;
        }
        // Spend before the app's own listeners run
        spend(actionId);
      },
      { capture: true }
    );
  }

  function makeHud() {
    const panel = document.querySelector('.panel.combat .panel-body');
    if (!panel) return;
    const hud = document.createElement('div');
    hud.id = 'ap-hud';
    hud.className = 'ap-hud';
    hud.innerHTML = `
      <div class="ap-row"><strong>AP:</strong> <span id="ap-val">—</span></div>
      <div class="ap-row"><strong>STA:</strong> <span id="sta-val">—</span></div>
      <small class="muted">Round: ${state.roundSeconds}s • Costs: Move 1, Attack 3, Ability 2, Defend 1</small>
    `;
    panel.appendChild(hud);
  }

  function hookTurnButtons() {
    const startBtn = document.querySelector('#btn-start-combat');
    const nextBtn  = document.querySelector('#btn-next-turn');
    const endBtn   = document.querySelector('#act-end');

    if (startBtn) startBtn.addEventListener('click', () => setTimeout(startTurn, 0), { capture: true });
    if (nextBtn)  nextBtn.addEventListener('click',  () => setTimeout(startTurn, 0), { capture: true });
    if (endBtn)   endBtn.addEventListener('click',   () => setTimeout(startTurn, 0), { capture: true });
  }

  function init() {
    ensureStyles();
    makeHud();
    // Map your buttons to action IDs
    bindAction('#act-move',    'move');
    bindAction('#act-attack',  'melee_attack'); // change to 'ranged_attack' if you want
    bindAction('#act-ability', 'ability');
    bindAction('#act-defend',  'guard');

    hookTurnButtons();

    recomputeApMax();
    state.apLeft = state.apMax;
    render();
  }

  return {
    init,
    state,
    setActorStats({ AGI, encumbrance, staminaMax }) {
      if (typeof AGI === 'number') state.AGI = AGI;
      if (encumbrance) state.encumbrance = encumbrance;
      if (typeof staminaMax === 'number') {
        state.staminaMax = staminaMax;
        state.stamina = Math.min(state.stamina, staminaMax);
      }
      recomputeApMax();
      render();
    },
  };
})();

window.CombatAP = CombatAP;
document.addEventListener('DOMContentLoaded', () => CombatAP.init());
