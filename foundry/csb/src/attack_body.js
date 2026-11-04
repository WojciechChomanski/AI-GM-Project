// ===== Breath Attack (Breath and the Veil, combat v1) =====
// Attacker: your SELECTED token (else your character). Defender: your TARGETED token (T key).
// Resolves one attack with the Python engine (POST /combat/attack, scripts/combat_engine.py) through the local bridge
// (foundry/csb/COMBAT_BRIDGE.md). Foundry/CSB never re-implements the maneuver, damage-type or armour rules.
const num = (v, d = 0) => (Number.isFinite(Number(v)) ? Number(v) : d);
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const parse = (s, d) => { try { return s ? JSON.parse(s) : d; } catch (e) { return d; } };
const attacker = canvas.tokens?.controlled[0]?.actor ?? game.user.character;
const defender = [...game.user.targets][0]?.actor;
if (!attacker) return ui.notifications.warn('Breath Attack: select your token first.');
if (!defender) return ui.notifications.warn('Breath Attack: target the defender (hover + T).');
if (!game.user.isGM && !attacker.isOwner) return ui.notifications.warn('Breath Attack: you do not own the attacker.');
const A = attacker.system.props ?? {}, D = defender.system.props ?? {};
const weaponsOf = (act) => act.items.filter((i) => i.system?.props?.item_kind === 'Weapon');
const inHand = (act, P) => { const ws = weaponsOf(act); return ws.find((i) => i.system.props.weapon_id === P.weapon_in_hand) ?? ws[0]; };
const wItem = inHand(attacker, A);
if (!wItem) return ui.notifications.warn('Breath Attack: drag a Breath Weapon item onto the attacker (and set Weapon in hand).');
const W = wItem.system.props;
const twoHands = !num(A.shield_equipped) && (A.grip || 'two_hands') !== 'one_hand';
const guards = parse(twoHands && W.guards_two_hand_json ? W.guards_two_hand_json : W.guards_json, {});
const maneuvers = parse(twoHands && W.maneuvers_two_hand_json ? W.maneuvers_two_hand_json : W.maneuvers_json, []);
const guardIds = Object.keys(guards).length ? Object.keys(guards) : ['offensive', 'neutral', 'defensive'];
const curGuard = guardIds.includes(A.current_guard) ? A.current_guard : (guardIds.includes(W.default_guard) ? W.default_guard : guardIds[0]);
const ZONES = ['head', 'throat', 'chest', 'stomach', 'groin', 'left_upper_arm', 'right_upper_arm', 'left_lower_arm', 'right_lower_arm',
  'left_upper_leg', 'right_upper_leg', 'left_lower_leg', 'right_lower_leg'];
const TRIGGERS = ['always', 'after_parry', 'after_block', 'after_dodge'];
const types = String(W.damage_types || W.damage_type || 'blunt').split(',').map((s) => s.trim()).filter(Boolean);
const list = (v) => (Array.isArray(v) ? v : v ? [v] : []);
const manOpts = (g, trig) => maneuvers.filter((m) => list(m.stance_required).includes(g)
  && (list(m.trigger).includes('always') || list(m.trigger).includes(trig)));
const gLabel = (g) => { const x = guards[g]; return x ? `${x.name ?? g} (${x.type}, atk ${x.attack >= 0 ? '+' : ''}${x.attack}, def ${x.defense >= 0 ? '+' : ''}${x.defense})` : g; };
const content = `
<form class="bv-attack">
  <p><b>${esc(attacker.name)}</b> with <b>${esc(W.weapon_label)}</b>${W.two_hand_guard_set ? (twoHands ? ' (two hands)' : ' (one hand)') : ''} vs <b>${esc(defender.name)}</b>.
     Guard change costs ${num(W.guard_change_stamina, 1)} stamina.${num(W.armor_piercing) ? ' <i>Armour piercing.</i>' : ''}</p>
  <div class="form-group"><label>Guard</label><select name="guard">${guardIds.map((g) => `<option value="${g}"${g === curGuard ? ' selected' : ''}>${esc(gLabel(g))}</option>`).join('')}</select></div>
  <div class="form-group"><label>Situation</label><select name="trigger">${TRIGGERS.map((t) => `<option value="${t}">${t.replace('_', ' ')}</option>`).join('')}</select></div>
  <div class="form-group"><label>Maneuver</label><select name="maneuver"></select></div>
  <div class="form-group"><label>Target zone</label><select name="zone"><option value="">Normal hit (no aim)</option>${ZONES.map((z) => `<option value="${z}">Aimed: ${z.replace(/_/g, ' ')}</option>`).join('')}</select></div>
  <div class="form-group"><label>Damage type</label><select name="dtype"><option value="">Best against the armour</option>${types.map((t) => `<option value="${t}">${t}</option>`).join('')}</select></div>
  <div class="form-group"><label>Use my trick (once per fight)</label><input type="checkbox" name="trick"></div>
  <p class="bv-note bv-man-note"></p>
</form>`;
function fillManeuvers(root) {
  const f = root.querySelector('form.bv-attack');
  const opts = manOpts(f.guard.value, f.trigger.value);
  f.maneuver.innerHTML = `<option value="__best">Best valid maneuver (engine picks)</option><option value="__none">No maneuver</option>`
    + opts.map((m) => `<option value="${esc(m.name)}">${esc(m.name)}</option>`).join('');
  const sel = opts.find((m) => m.name === f.maneuver.value);
  root.querySelector('.bv-man-note').innerHTML = sel ? esc(sel.description) : `<i>${opts.length} maneuver(s) possible from this guard.</i>`;
}
const DialogV2 = foundry.applications.api.DialogV2;
const form = await DialogV2.wait({
  window: { title: `Breath Attack - ${attacker.name}` }, position: { width: 520 }, content, rejectClose: false,
  render: (event, dialog) => {
    const root = dialog.element ?? event?.target?.element;
    const f = root.querySelector('form.bv-attack');
    fillManeuvers(root);
    f.guard.addEventListener('change', () => fillManeuvers(root));
    f.trigger.addEventListener('change', () => fillManeuvers(root));
    f.maneuver.addEventListener('change', () => { const m = maneuvers.find((x) => x.name === f.maneuver.value); root.querySelector('.bv-man-note').innerHTML = m ? esc(m.description) : ''; });
  },
  buttons: [
    { action: 'attack', label: 'Attack', default: true, callback: (event, button, dialog) => {
      const f = (dialog.element ?? button.form).querySelector('form.bv-attack');
      return { guard: f.guard.value, trigger: f.trigger.value, maneuver: f.maneuver.value, zone: f.zone.value, dtype: f.dtype.value, trick: f.trick.checked };
    } },
    { action: 'cancel', label: 'Cancel', callback: () => null },
  ],
});
if (!form) return;
const armourKeys = (P) => String(P.armor_worn ?? '').split(',').map((s) => s.trim()).filter(Boolean);
function combatant(act, P, weaponId, extra) {
  return { name: act.name, race: P.race || 'Human', gender: P.gender || 'Male', class_name: P.class_name || '',
    total_hp: num(P.total_hp_max, 100), max_stamina: num(P.stamina_max, 100), armor_weight: 0, inventory_weight: 0,
    shield_equipped: !!num(P.shield_equipped), weapon_equipped: !!weaponId, weapon: weaponId || null, armor: armourKeys(P),
    strength: num(P.strength, 35), dexterity: num(P.dexterity, 30), weapon_skill: num(P.weapon_skill, 30),
    progression: parse(P.mastery_json, {}), conditions: parse(P.conditions_json, []), disarmed: !!num(P.disarmed),
    virtue: num(P.virtue), piety: num(P.piety), corruption_level: num(P.corruption_level), grip: P.grip || 'two_hands', ...extra };
}
const dW = inHand(defender, D)?.system.props;
const payload = {
  attacker: combatant(attacker, A, W.weapon_id, { stance: form.guard, previous_stance: A.current_guard || null,
    maneuver: form.maneuver === '__best' ? null : form.maneuver === '__none' ? false : form.maneuver,
    trigger: form.trigger, aimed_zone: form.zone || null, damage_type: form.dtype || null, use_trick: form.trick,
    fight_state: parse(A.fight_state_json, {}) }),
  defender: combatant(defender, D, dW?.weapon_id, { stance: D.current_guard || dW?.default_guard || 'neutral' }),
};
let res;
try {
  const r = await fetch(BREATH_BRIDGE.url, { method: 'POST', headers: { 'Content-Type': 'application/json',
    Authorization: 'Basic ' + btoa(`${BREATH_BRIDGE.user}:${BREATH_BRIDGE.password}`) }, body: JSON.stringify(payload) });
  if (!r.ok) throw new Error(`HTTP ${r.status} ${await r.text()}`);
  res = await r.json();
} catch (e) {
  return ui.notifications.error(`Breath Attack: the combat bridge did not answer (${e.message}). Is "python scripts/combat_engine.py" running? See COMBAT_BRIDGE.md.`);
}
// ---- store the stateless engine's state on the sheets (the caller's job)
const aUpd = { 'system.props.current_guard': res.stance ?? form.guard, 'system.props.previous_guard': A.current_guard || '',
  'system.props.fight_state_json': JSON.stringify(res.fight_state ?? {}), 'system.props.conditions_json': JSON.stringify(res.attacker_conditions ?? []) };
if (res.stamina_spent !== undefined && A.stamina !== undefined && A.stamina !== '') aUpd['system.props.stamina'] = Math.max(0, num(A.stamina) - num(res.stamina_spent));
await attacker.update(aUpd);
const dUpd = { 'system.props.conditions_json': JSON.stringify(res.defender_conditions ?? []) };
if (res.defender_disarmed) dUpd['system.props.disarmed'] = 1;
await defender.update(dUpd);
const wear = (res.armor_wear ?? []).map((w) => `${esc(w.armor)} -${w.durability_loss}`).join(', ');
const lines = [
  `<b>${esc(attacker.name)}</b> → <b>${esc(defender.name)}</b> with ${esc(W.weapon_label)} from <i>${esc(res.stance)}</i>`
    + `${res.guard_change_cost ? ` (guard change -${res.guard_change_cost} stamina)` : ''}.`,
  `Maneuver: <b>${esc(res.maneuver ?? 'none')}</b>${res.maneuver_note ? ` <i>(${esc(res.maneuver_note)})</i>` : ''}.`,
  `Attack ${res.atk_total ?? '?'} vs defence ${res.def_total ?? '?'}: <b>${res.hit ? 'HIT' : 'miss'}</b>.`,
  res.hit ? `Damage through armour: <b>${res.damage}</b> ${esc(res.damage_type)}${res.zone ? ` on ${esc(String(res.zone).replace(/_/g, ' '))}` : ''}`
    + `${res.armor_piercing ? ` (armour piercing ${res.armor_piercing})` : ''}.${wear ? ` Armour wear: ${wear}.` : ''}` : '',
  (res.effects ?? []).length ? `Effects: ${esc(JSON.stringify(res.effects))}` : '',
  `Stamina spent: ${res.stamina_spent ?? '?'}${res.trick ? `. Trick used: ${esc(res.trick)}` : ''}.`,
  (res.notes ?? []).length ? `<i>${esc(res.notes.join(' '))}</i>` : '',
].filter(Boolean);
await ChatMessage.create({ speaker: ChatMessage.getSpeaker({ actor: attacker }), content: `<div class="bv-chat">${lines.join('<br>')}</div>`,
  whisper: ChatMessage.getWhisperRecipients('GM') });
// ---- hand the hit to Apply Damage (zones, bleeding); armour is already off
if (res.hit && num(res.damage) > 0) {
  const apply = game.macros.getName('Apply Damage');
  if (!apply) return ui.notifications.warn('Breath Attack: no macro named "Apply Damage" - apply the damage by hand.');
  await apply.execute({ preset: { actorUuid: defender.uuid, amount: num(res.damage), type: res.damage_type,
    mode: res.zone && form.zone ? 'aimed' : 'normal', zone: res.zone || form.zone || 'chest', armourApplied: true } });
}
